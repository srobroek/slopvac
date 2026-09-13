# Rotate an internal ingress TLS certificate

## Scope

Use this runbook to rotate one TLS certificate across six internal ingress nodes.

The procedure updates two canary nodes before updating the remaining four nodes. Reloading a node closes its open connections.

## Required values

Collect these values from the ingress service record:

| Variable | Description |
|---|---|
| `INGRESS_HOST` | DNS name covered by the certificate |
| `INGRESS_PORT` | TLS port, normally `443` |
| `CA_FILE` | Trusted internal CA bundle |
| `NEW_SECRET_VERSION` | New certificate secret version |
| `PREVIOUS_SECRET_VERSION` | Previous certificate secret version |
| `DRAIN_TIMEOUT` | Maximum drain period in seconds |
| `CANARY_OBSERVATION_SECONDS` | Canary observation period in seconds |
| `NODE_1` through `NODE_6` | Resolvable node names or IP addresses |

Set the shell variables:

```bash
export INGRESS_HOST="<internal-ingress.example>"
export INGRESS_PORT="443"
export CA_FILE="<path-to-internal-ca.pem>"
export NEW_SECRET_VERSION="<new-secret-version>"
export PREVIOUS_SECRET_VERSION="<previous-secret-version>"
export DRAIN_TIMEOUT="600"
export CANARY_OBSERVATION_SECONDS="600"

export NODE_1="<node-1>"
export NODE_2="<node-2>"
export NODE_3="<node-3>"
export NODE_4="<node-4>"
export NODE_5="<node-5>"
export NODE_6="<node-6>"

export CANARY_NODES="$NODE_1 $NODE_2"
export REMAINING_NODES="$NODE_3 $NODE_4 $NODE_5 $NODE_6"
export ALL_NODES="$CANARY_NODES $REMAINING_NODES"
```

## Create the working directory

Create one run-specific working directory:

```bash
set -o pipefail

WORK_DIR="$(mktemp -d)" || exit 1
export WORK_DIR
readonly WORK_DIR

chmod 700 "$WORK_DIR"

export NEW_CERT_FILE="${WORK_DIR}/new.pem"
export PREVIOUS_CERT_FILE="${WORK_DIR}/previous.pem"
```

Define cleanup for that directory:

```bash
cleanup_tls_rotation() {
  if [ -n "${WORK_DIR:-}" ] && [ -d "$WORK_DIR" ]; then
    rm -rf -- "$WORK_DIR"
  fi
}
```

Install cleanup traps:

```bash
trap cleanup_tls_rotation EXIT
trap 'exit 1' HUP INT TERM
```

Confirm that `mktemp` created the directory:

```bash
test -d "$WORK_DIR"
test ! -L "$WORK_DIR"
```

Stop if either check returns a nonzero exit code.

Store every extracted or captured certificate under `$WORK_DIR`. Do not create certificate files outside that directory.

## Required platform commands

Locate the environment-specific command for each operation:

- List the six ingress nodes.
- Extract a leaf certificate from a secret version.
- Show one node’s assigned secret version.
- Point one node at a specified secret version.
- Drain one node from the load balancer.
- Show one node’s open connection count.
- Reload one node.
- Return one node to the load balancer.
- Show one node’s readiness and health.
- Show ingress TLS, connection, and HTTP error alerts.

Do not start the rotation without commands for all ten operations.

## Safety requirements

> **Warning:** Reloading a node closes every open connection on that node.

Drain each node before changing its secret reference. Wait until the node reports zero open connections before reloading it.

If a node retains open connections after `$DRAIN_TIMEOUT` seconds, stop without reloading that node. Escalate through the ingress service’s on-call procedure.

Update one node at a time. Keep the other five nodes available while each node drains and reloads.

Do not delete `$PREVIOUS_SECRET_VERSION` during this procedure. Do not extract either private key.

A secret version identifies a stored secret. Certificate verification must compare live metadata with the extracted leaf certificate’s `EXPECTED_*` values.

## Record expected certificate metadata

### Extract the leaf certificates

Use the secret-management command to extract only the leaf certificate from `$PREVIOUS_SECRET_VERSION`.

Write the previous leaf certificate to `$PREVIOUS_CERT_FILE`.

Use the secret-management command to extract only the leaf certificate from `$NEW_SECRET_VERSION`.

Write the new leaf certificate to `$NEW_CERT_FILE`.

Restrict both files to the current account:

```bash
chmod 600 "$PREVIOUS_CERT_FILE" "$NEW_CERT_FILE"
```

Confirm that OpenSSL can parse both files:

```bash
openssl x509 -in "$PREVIOUS_CERT_FILE" -noout
openssl x509 -in "$NEW_CERT_FILE" -noout
```

Stop if either command returns a nonzero exit code.

### Set the expected previous values

Extract the expected metadata from the previous leaf certificate:

```bash
export EXPECTED_PREVIOUS_SERIAL="$(
  openssl x509 -in "$PREVIOUS_CERT_FILE" -noout -serial |
  cut -d= -f2
)"

export EXPECTED_PREVIOUS_FINGERPRINT="$(
  openssl x509 -in "$PREVIOUS_CERT_FILE" -noout -fingerprint -sha256 |
  cut -d= -f2
)"

export EXPECTED_PREVIOUS_NOT_AFTER="$(
  openssl x509 -in "$PREVIOUS_CERT_FILE" -noout -enddate |
  cut -d= -f2-
)"
```

Display the expected previous values:

```bash
printf 'Expected previous serial: %s\n' \
  "$EXPECTED_PREVIOUS_SERIAL"

printf 'Expected previous SHA-256 fingerprint: %s\n' \
  "$EXPECTED_PREVIOUS_FINGERPRINT"

printf 'Expected previous expiry: %s\n' \
  "$EXPECTED_PREVIOUS_NOT_AFTER"
```

### Set the expected new values

Extract the expected metadata from the new leaf certificate:

```bash
export EXPECTED_NEW_SERIAL="$(
  openssl x509 -in "$NEW_CERT_FILE" -noout -serial |
  cut -d= -f2
)"

export EXPECTED_NEW_FINGERPRINT="$(
  openssl x509 -in "$NEW_CERT_FILE" -noout -fingerprint -sha256 |
  cut -d= -f2
)"

export EXPECTED_NEW_NOT_AFTER="$(
  openssl x509 -in "$NEW_CERT_FILE" -noout -enddate |
  cut -d= -f2-
)"
```

Display the expected new values:

```bash
printf 'Expected new serial: %s\n' \
  "$EXPECTED_NEW_SERIAL"

printf 'Expected new SHA-256 fingerprint: %s\n' \
  "$EXPECTED_NEW_FINGERPRINT"

printf 'Expected new expiry: %s\n' \
  "$EXPECTED_NEW_NOT_AFTER"
```

Record all six `EXPECTED_*` values in the change record.

## Validate the certificate secrets

Inspect `$PREVIOUS_SECRET_VERSION` and `$NEW_SECRET_VERSION` with the secret-management command.

Confirm that each secret contains:

- One leaf certificate.
- The matching private key.
- Each required intermediate certificate.

Confirm that the new leaf certificate contains `$INGRESS_HOST` in its Subject Alternative Name extension:

```bash
openssl x509 \
  -in "$NEW_CERT_FILE" \
  -noout \
  -checkhost "$INGRESS_HOST"
```

Confirm that the internal CA verifies the new leaf certificate and its intermediate chain. Use the extracted intermediate certificates with `openssl verify`.

Stop if any validation command returns a nonzero exit code.

## Check the existing deployment

### Confirm the node inventory

List the ingress nodes with the platform inventory command.

Confirm that the inventory contains exactly the six nodes assigned to `NODE_1` through `NODE_6`. Stop if the inventory contains a different node count.

### Confirm the assigned secret versions

For each node, run the platform command that shows its assigned secret version.

| Node | Assigned secret version |
|---|---|
| `NODE_1` | |
| `NODE_2` | |
| `NODE_3` | |
| `NODE_4` | |
| `NODE_5` | |
| `NODE_6` | |

Confirm that every node references `$PREVIOUS_SECRET_VERSION`. Stop if any node references another secret version.

### Confirm the live previous certificate

Run this command across all six nodes:

```bash
node_index=0

for node in $ALL_NODES; do
  node_index=$((node_index + 1))
  live_file="${WORK_DIR}/node-${node_index}-before.pem"

  openssl s_client \
    -connect "${node}:${INGRESS_PORT}" \
    -servername "$INGRESS_HOST" \
    </dev/null 2>/dev/null |
    openssl x509 -out "$live_file" || exit 1

  live_serial="$(
    openssl x509 -in "$live_file" -noout -serial |
    cut -d= -f2
  )"

  live_fingerprint="$(
    openssl x509 -in "$live_file" -noout -fingerprint -sha256 |
    cut -d= -f2
  )"

  live_not_after="$(
    openssl x509 -in "$live_file" -noout -enddate |
    cut -d= -f2-
  )"

  printf '%s serial: %s\n' "$node" "$live_serial"
  printf '%s SHA-256 fingerprint: %s\n' \
    "$node" "$live_fingerprint"
  printf '%s expiry: %s\n' "$node" "$live_not_after"

  test "$live_serial" = "$EXPECTED_PREVIOUS_SERIAL" || exit 1
  test "$live_fingerprint" = \
    "$EXPECTED_PREVIOUS_FINGERPRINT" || exit 1
  test "$live_not_after" = \
    "$EXPECTED_PREVIOUS_NOT_AFTER" || exit 1
done
```

Stop if the loop returns a nonzero exit code. Resolve the certificate mismatch before continuing.

## Stage the certificate on two nodes

Perform this sequence on `$NODE_1`, then repeat it on `$NODE_2`:

1. Drain the node from the load balancer.
2. Poll the node’s open connection count.
3. Continue only after the connection count reaches zero.
4. Stop if draining exceeds `$DRAIN_TIMEOUT` seconds.
5. Point the node’s secret reference to `$NEW_SECRET_VERSION`.
6. Confirm that the assigned secret version equals `$NEW_SECRET_VERSION`.
7. Reload the node.
8. Wait until the node reports ready.
9. Verify the node with [Verify one node](#verify-one-node).
10. Return the node to the load balancer.
11. Confirm that the node reports healthy.

## Verify one node

Set `NODE` and its numeric position:

```bash
export NODE="<node-name-or-ip>"
export NODE_INDEX="<1-through-6>"
export LIVE_CERT_FILE="${WORK_DIR}/node-${NODE_INDEX}-live.pem"
```

Capture the live leaf certificate:

```bash
openssl s_client \
  -connect "${NODE}:${INGRESS_PORT}" \
  -servername "$INGRESS_HOST" \
  </dev/null 2>/dev/null |
  openssl x509 -out "$LIVE_CERT_FILE"
```

Stop if the command returns a nonzero exit code.

Extract the live metadata:

```bash
LIVE_SERIAL="$(
  openssl x509 -in "$LIVE_CERT_FILE" -noout -serial |
  cut -d= -f2
)"

LIVE_FINGERPRINT="$(
  openssl x509 -in "$LIVE_CERT_FILE" -noout -fingerprint -sha256 |
  cut -d= -f2
)"

LIVE_NOT_AFTER="$(
  openssl x509 -in "$LIVE_CERT_FILE" -noout -enddate |
  cut -d= -f2-
)"
```

Compare the live metadata with the expected new metadata:

```bash
test "$LIVE_SERIAL" = "$EXPECTED_NEW_SERIAL"
test "$LIVE_FINGERPRINT" = "$EXPECTED_NEW_FINGERPRINT"
test "$LIVE_NOT_AFTER" = "$EXPECTED_NEW_NOT_AFTER"
```

Stop if any comparison returns a nonzero exit code.

Verify the trust chain and hostname:

```bash
openssl s_client \
  -connect "${NODE}:${INGRESS_PORT}" \
  -servername "$INGRESS_HOST" \
  -verify_hostname "$INGRESS_HOST" \
  -verify_return_error \
  -CAfile "$CA_FILE" \
  </dev/null
```

Confirm that OpenSSL prints:

```text
Verify return code: 0 (ok)
```

Stop if OpenSSL reports a hostname, expiry, chain, signature, or trust failure.

## Observe the canary nodes

Observe ingress monitoring for `$CANARY_OBSERVATION_SECONDS` seconds after both canary nodes return to service.

Confirm these conditions:

- Both canary nodes remain ready and healthy.
- Both canary nodes reference `$NEW_SECRET_VERSION`.
- Both canary nodes serve `$EXPECTED_NEW_SERIAL`.
- Both canary nodes serve `$EXPECTED_NEW_FINGERPRINT`.
- Both canary nodes serve `$EXPECTED_NEW_NOT_AFTER`.
- The monitoring system reports no TLS alert.
- The monitoring system reports no connection alert.
- The monitoring system reports no HTTP error-rate alert.

If any condition fails, execute [Roll back changed nodes](#roll-back-changed-nodes).

## Roll to the remaining four nodes

Process `$NODE_3`, `$NODE_4`, `$NODE_5`, and `$NODE_6` in that order.

For each node:

1. Drain the node from the load balancer.
2. Poll the node’s open connection count.
3. Continue only after the connection count reaches zero.
4. Stop if draining exceeds `$DRAIN_TIMEOUT` seconds.
5. Point the node’s secret reference to `$NEW_SECRET_VERSION`.
6. Confirm that the assigned secret version equals `$NEW_SECRET_VERSION`.
7. Reload the node.
8. Wait until the node reports ready.
9. Verify the node with [Verify one node](#verify-one-node).
10. Return the node to the load balancer.
11. Confirm that the node reports healthy.
12. Confirm that monitoring reports no TLS, connection, or HTTP error-rate alert.

If a node fails verification, leave that node drained. Execute [Roll back changed nodes](#roll-back-changed-nodes).

## Verify the completed rotation

Run this check across all six nodes:

```bash
node_index=0

for node in $ALL_NODES; do
  node_index=$((node_index + 1))
  live_file="${WORK_DIR}/node-${node_index}-after.pem"

  openssl s_client \
    -connect "${node}:${INGRESS_PORT}" \
    -servername "$INGRESS_HOST" \
    </dev/null 2>/dev/null |
    openssl x509 -out "$live_file" || exit 1

  live_serial="$(
    openssl x509 -in "$live_file" -noout -serial |
    cut -d= -f2
  )"

  live_fingerprint="$(
    openssl x509 -in "$live_file" -noout -fingerprint -sha256 |
    cut -d= -f2
  )"

  live_not_after="$(
    openssl x509 -in "$live_file" -noout -enddate |
    cut -d= -f2-
  )"

  printf '%s serial: %s\n' "$node" "$live_serial"
  printf '%s SHA-256 fingerprint: %s\n' \
    "$node" "$live_fingerprint"
  printf '%s expiry: %s\n' "$node" "$live_not_after"

  test "$live_serial" = "$EXPECTED_NEW_SERIAL" || exit 1
  test "$live_fingerprint" = \
    "$EXPECTED_NEW_FINGERPRINT" || exit 1
  test "$live_not_after" = "$EXPECTED_NEW_NOT_AFTER" || exit 1
done
```

Confirm these results:

- All six nodes reference `$NEW_SECRET_VERSION`.
- All six nodes report ready and healthy.
- All six nodes participate in the load balancer.
- The monitoring system reports no TLS alert.
- The monitoring system reports no connection alert.
- The monitoring system reports no HTTP error-rate alert.

Record the six secret assignments and final verification output in the change record.

## Roll back changed nodes

Rollback re-points each changed node to `$PREVIOUS_SECRET_VERSION`. Each rollback reload closes that node’s open connections.

Identify every node assigned to `$NEW_SECRET_VERSION`.

For each identified node:

1. Drain the node from the load balancer.
2. Poll the node’s open connection count.
3. Continue only after the connection count reaches zero.
4. Stop if draining exceeds `$DRAIN_TIMEOUT` seconds.
5. Point the node’s secret reference to `$PREVIOUS_SECRET_VERSION`.
6. Confirm that the assigned secret version equals `$PREVIOUS_SECRET_VERSION`.
7. Reload the node.
8. Wait until the node reports ready.
9. Capture the live leaf certificate under `$WORK_DIR`.
10. Compare its serial number with `$EXPECTED_PREVIOUS_SERIAL`.
11. Compare its SHA-256 fingerprint with `$EXPECTED_PREVIOUS_FINGERPRINT`.
12. Compare its expiry with `$EXPECTED_PREVIOUS_NOT_AFTER`.
13. Verify the trust chain and hostname with `openssl s_client`.
14. Return the node to the load balancer.
15. Confirm that the node reports healthy.

After rollback, run the six-node live certificate check against the three `EXPECTED_PREVIOUS_*` values.

Confirm that all six nodes serve `$EXPECTED_PREVIOUS_FINGERPRINT`. Record the rollback trigger and verification results in the change record.

## Remove the working directory

After the rotation or rollback succeeds, remove only `$WORK_DIR`:

```bash
cleanup_tls_rotation
trap - EXIT HUP INT TERM
```

Confirm that the directory no longer exists:

```bash
test ! -e "$WORK_DIR"
```
