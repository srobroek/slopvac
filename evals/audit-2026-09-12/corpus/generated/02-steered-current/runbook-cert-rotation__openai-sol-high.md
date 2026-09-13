# Rotate an internal ingress TLS certificate

## Scope

This runbook rotates one TLS certificate across six ingress nodes.

The rollout activates the new secret version on two canary nodes before activating it on the remaining four nodes.

> **Connection impact:** Reloading one ingress node terminates every open connection on that node. Drain the node and reach zero open connections before reloading it.

Never reload more than one node at a time.

## Required information

Record these values from the ingress service entry and certificate request.

| Value | Description |
|---|---|
| `INGRESS_HOST` | Hostname listed in the certificate |
| `INGRESS_PORT` | TLS listener port, normally `443` |
| `CA_FILE` | PEM file containing the trusted internal CA certificates |
| `NEW_CERT_PEM` | PEM file containing the new leaf certificate |
| `INTERMEDIATE_CHAIN_PEM` | PEM file containing the new certificate’s intermediate certificates |
| `NEW_SECRET_VERSION` | Secret version containing the new certificate and private key |
| `PREVIOUS_SECRET_VERSION` | Secret version active before this rotation |
| `CANARY_OBSERVATION_SECONDS` | Canary observation interval from the service entry |
| `CANARY_NODES` | Two direct node addresses |
| `REMAINING_NODES` | Four direct node addresses |

Obtain the platform commands described below before starting the rotation.

| Command token | Required behavior |
|---|---|
| `<get-secret-version NODE>` | Print the secret version referenced by one node |
| `<validate-secret-version VERSION>` | Validate the certificate, private key, and intermediate chain |
| `<drain-node NODE>` | Remove one node from load-balancer selection |
| `<open-connection-count NODE>` | Print the node’s open connection count |
| `<point-secret NODE VERSION>` | Point one node at a specified secret version |
| `<reload-node NODE>` | Reload the ingress process on one node |
| `<readiness-check NODE>` | Return success when the node can serve requests |
| `<undrain-node NODE>` | Restore one node to load-balancer selection |
| `<monitor-ingress>` | Display TLS handshake errors, HTTP 5xx responses, and active alerts |

Do not start until every command token maps to an executable platform command.

## Configure the verification shell

Use Bash for the commands in this runbook.

```bash
INGRESS_HOST='ingress.internal.example'
INGRESS_PORT='443'
CA_FILE='/path/to/internal-ca.pem'
NEW_CERT_PEM='/path/to/new-certificate.pem'
INTERMEDIATE_CHAIN_PEM='/path/to/intermediate-chain.pem'
NEW_SECRET_VERSION='version-id'
PREVIOUS_SECRET_VERSION='version-id'
CANARY_OBSERVATION_SECONDS='service-defined-seconds'

CANARY_NODES=(
  'ingress-node-1.internal'
  'ingress-node-2.internal'
)

REMAINING_NODES=(
  'ingress-node-3.internal'
  'ingress-node-4.internal'
  'ingress-node-5.internal'
  'ingress-node-6.internal'
)

ALL_NODES=("${CANARY_NODES[@]}" "${REMAINING_NODES[@]}")

test "${#CANARY_NODES[@]}" -eq 2
test "${#REMAINING_NODES[@]}" -eq 4
test "${#ALL_NODES[@]}" -eq 6
test "$(printf '%s\n' "${ALL_NODES[@]}" | sort -u | wc -l | tr -d ' ')" -eq 6

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
```

Stop if any node address appears more than once.

## Define the node verification command

This function checks trust, hostname coverage, validity dates, and the expected SHA-256 fingerprint.

```bash
verify_node() {
  local node="$1"
  local expected_fingerprint="$2"
  local output_file="$WORK_DIR/${node}.s_client.txt"
  local certificate_file="$WORK_DIR/${node}.served.pem"
  local actual_fingerprint

  if ! openssl s_client \
    -connect "${node}:${INGRESS_PORT}" \
    -servername "$INGRESS_HOST" \
    -CAfile "$CA_FILE" \
    -verify_return_error \
    -showcerts \
    </dev/null >"$output_file" 2>&1
  then
    cat "$output_file"
    return 1
  fi

  grep -Fq 'Verify return code: 0 (ok)' "$output_file" || {
    cat "$output_file"
    return 1
  }

  openssl x509 \
    -in "$output_file" \
    -outform PEM \
    >"$certificate_file"

  openssl x509 \
    -in "$certificate_file" \
    -noout \
    -checkhost "$INGRESS_HOST"

  openssl x509 \
    -in "$certificate_file" \
    -noout \
    -checkend 0

  actual_fingerprint="$(
    openssl x509 \
      -in "$certificate_file" \
      -noout \
      -fingerprint \
      -sha256 |
    sed 's/.*=//'
  )"

  test "$actual_fingerprint" = "$expected_fingerprint"

  openssl x509 \
    -in "$certificate_file" \
    -noout \
    -subject \
    -issuer \
    -serial \
    -startdate \
    -enddate \
    -fingerprint \
    -sha256
}
```

## Check the active certificate expiry

Fetch the leaf certificate directly from each of the six nodes.

```bash
for node in "${ALL_NODES[@]}"; do
  certificate_file="$WORK_DIR/${node}.before.pem"

  openssl s_client \
    -connect "${node}:${INGRESS_PORT}" \
    -servername "$INGRESS_HOST" \
    -showcerts \
    </dev/null 2>"$WORK_DIR/${node}.before.log" |
  openssl x509 -outform PEM >"$certificate_file"

  echo "=== $node ==="

  openssl x509 \
    -in "$certificate_file" \
    -noout \
    -subject \
    -issuer \
    -serial \
    -startdate \
    -enddate \
    -fingerprint \
    -sha256

  if openssl x509 -in "$certificate_file" -noout -checkend 0; then
    echo "$node serves an unexpired certificate."
  else
    echo "$node serves an expired certificate."
  fi
done
```

Confirm that all six nodes report the expected expiring certificate.

Calculate the active certificate fingerprints.

```bash
for node in "${ALL_NODES[@]}"; do
  openssl x509 \
    -in "$WORK_DIR/${node}.before.pem" \
    -noout \
    -fingerprint \
    -sha256 |
  sed 's/.*=//'
done | sort -u
```

Stop if the command prints more than one fingerprint.

Record the single value as the rollback fingerprint.

```bash
PREVIOUS_FINGERPRINT="$(
  openssl x509 \
    -in "$WORK_DIR/${CANARY_NODES[0]}.before.pem" \
    -noout \
    -fingerprint \
    -sha256 |
  sed 's/.*=//'
)"

printf 'Previous fingerprint: %s\n' "$PREVIOUS_FINGERPRINT"
```

If the active certificate has expired, mark the previous secret version as unavailable for rollback.

## Validate the new certificate

Inspect the new certificate.

```bash
openssl x509 \
  -in "$NEW_CERT_PEM" \
  -noout \
  -subject \
  -issuer \
  -serial \
  -startdate \
  -enddate \
  -fingerprint \
  -sha256
```

Confirm that the certificate covers the ingress hostname.

```bash
openssl x509 \
  -in "$NEW_CERT_PEM" \
  -noout \
  -checkhost "$INGRESS_HOST"
```

Confirm that the certificate is valid at the system clock’s UTC time.

```bash
date -u
openssl x509 -in "$NEW_CERT_PEM" -noout -checkend 0
```

Validate the certificate chain against the internal CA bundle.

```bash
openssl verify \
  -CAfile "$CA_FILE" \
  -untrusted "$INTERMEDIATE_CHAIN_PEM" \
  "$NEW_CERT_PEM"
```

Run the platform command that validates the new secret version.

```text
<validate-secret-version NEW_SECRET_VERSION>
```

Stop if the platform command reports a certificate and private-key mismatch.

Calculate the fingerprint expected after each reload.

```bash
NEW_FINGERPRINT="$(
  openssl x509 \
    -in "$NEW_CERT_PEM" \
    -noout \
    -fingerprint \
    -sha256 |
  sed 's/.*=//'
)"

printf 'New fingerprint: %s\n' "$NEW_FINGERPRINT"
```

## Confirm the previous secret version

Run `<get-secret-version NODE>` for each of the six nodes.

Confirm that every node points to `PREVIOUS_SECRET_VERSION`.

Stop if the six nodes reference different secret versions.

Do not delete or modify `PREVIOUS_SECRET_VERSION` during this procedure.

## Check the pre-rotation service state

Run `<readiness-check NODE>` for each of the six nodes.

Run `<monitor-ingress>` before changing the first node.

Stop if any node fails its readiness check.

Stop if a TLS or HTTP alert is firing before the rotation.

## Rotate the two canary nodes

Process the two canary nodes sequentially.

For each node in `CANARY_NODES`, complete these steps:

1. Run `<drain-node NODE>` to remove the node from load-balancer selection.
2. Run `<open-connection-count NODE>` until the command reports `0`.
3. Stop if the platform’s configured drain timeout expires before the count reaches `0`.
4. Run `<point-secret NODE NEW_SECRET_VERSION>` to change the node’s secret pointer.
5. Run `<get-secret-version NODE>` and confirm that it prints `NEW_SECRET_VERSION`.
6. Run `<reload-node NODE>` to load the new certificate.
7. Run `<readiness-check NODE>` and require a successful result.
8. Run `verify_node "NODE" "$NEW_FINGERPRINT"` against the node’s direct address.
9. Run `<undrain-node NODE>` after every verification succeeds.
10. Run `<monitor-ingress>` and confirm that no configured alert enters the firing state.

Keep the node drained if its readiness check or `verify_node` command fails.

Rollback that node before processing the second canary node.

## Observe the canary nodes

After both canary nodes return to service, run `<monitor-ingress>` for `CANARY_OBSERVATION_SECONDS`.

Confirm that no configured TLS handshake or HTTP 5xx alert enters the firing state.

Run the direct verification again for both canary nodes.

```bash
for node in "${CANARY_NODES[@]}"; do
  verify_node "$node" "$NEW_FINGERPRINT"
done
```

Rollback both canary nodes if either verification fails.

Do not process the remaining four nodes until the canary observation completes.

## Rotate the remaining four nodes

Process the four remaining nodes sequentially.

For each node in `REMAINING_NODES`, complete these steps:

1. Run `<drain-node NODE>` to remove the node from load-balancer selection.
2. Run `<open-connection-count NODE>` until the command reports `0`.
3. Stop if the platform’s configured drain timeout expires before the count reaches `0`.
4. Run `<point-secret NODE NEW_SECRET_VERSION>` to change the node’s secret pointer.
5. Run `<get-secret-version NODE>` and confirm that it prints `NEW_SECRET_VERSION`.
6. Run `<reload-node NODE>` to load the new certificate.
7. Run `<readiness-check NODE>` and require a successful result.
8. Run `verify_node "NODE" "$NEW_FINGERPRINT"` against the node’s direct address.
9. Run `<undrain-node NODE>` after every verification succeeds.
10. Run `<monitor-ingress>` and confirm that no configured alert enters the firing state.

Stop the rollout after the first failed readiness check, certificate verification, or ingress alert.

Rollback every node already changed during this rotation.

## Verify the completed rotation

Confirm that all six nodes reference the new secret version.

Run `<get-secret-version NODE>` for each node and require `NEW_SECRET_VERSION`.

Verify the served certificate on all six nodes.

```bash
for node in "${ALL_NODES[@]}"; do
  verify_node "$node" "$NEW_FINGERPRINT"
done
```

Run `<readiness-check NODE>` for all six nodes.

Run `<monitor-ingress>` for `CANARY_OBSERVATION_SECONDS`.

Complete the rotation only when all six nodes satisfy these conditions:

- The secret pointer equals `NEW_SECRET_VERSION`.
- The SHA-256 leaf fingerprint equals `NEW_FINGERPRINT`.
- `openssl s_client` reports `Verify return code: 0 (ok)`.
- `openssl x509 -checkhost` accepts `INGRESS_HOST`.
- `openssl x509 -checkend 0` reports an unexpired certificate.
- The readiness check succeeds.
- No configured TLS handshake or HTTP 5xx alert is firing.

## Roll back the rotation

Rollback restores each changed node by pointing its secret to `PREVIOUS_SECRET_VERSION`.

Do not rollback to `PREVIOUS_SECRET_VERSION` if its certificate has expired.

If rollback is unavailable, keep the affected node drained and escalate through the ingress service’s incident path.

Process changed nodes in reverse rollout order.

For each changed node, complete these steps:

1. Run `<drain-node NODE>` if the node remains in load-balancer selection.
2. Run `<open-connection-count NODE>` until the command reports `0`.
3. Stop if the platform’s configured drain timeout expires before the count reaches `0`.
4. Run `<point-secret NODE PREVIOUS_SECRET_VERSION>` to restore the previous secret pointer.
5. Run `<get-secret-version NODE>` and confirm that it prints `PREVIOUS_SECRET_VERSION`.
6. Run `<reload-node NODE>` to load the previous certificate.
7. Run `<readiness-check NODE>` and require a successful result.
8. Run `verify_node "NODE" "$PREVIOUS_FINGERPRINT"` against the node’s direct address.
9. Run `<undrain-node NODE>` after every rollback verification succeeds.
10. Run `<monitor-ingress>` and confirm that no configured alert enters the firing state.

After rolling back every changed node, verify each restored node again.

```bash
for node in "${ALL_NODES[@]}"; do
  if [ "$(<get-secret-version "$node">)" = "$PREVIOUS_SECRET_VERSION" ]; then
    verify_node "$node" "$PREVIOUS_FINGERPRINT"
  fi
done
```

Replace the placeholder inside the command substitution with the platform’s executable `<get-secret-version NODE>` command.
