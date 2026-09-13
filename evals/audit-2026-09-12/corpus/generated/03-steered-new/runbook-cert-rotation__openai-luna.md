# Runbook: Rotate the TLS Certificate on the Six-Node Internal Ingress

## Scope

Use this runbook to replace an expiring TLS certificate on an internal ingress with six nodes.

The runbook stages the new certificate on two canary nodes before updating the remaining four nodes.

Reloading a node drops all open connections to that node.

## Required access

You need access to these resources:

- The ingress control plane.
- The certificate secret store.
- All six ingress nodes.
- `openssl` version 1.1.1 or later.
- The internal CA bundle that validates the certificate chain.
- The approved change window.

The ingress platform determines the command that stages a secret version and reloads a node.

## Define the rotation values

Replace each placeholder with the value for this ingress.

```bash
export INGRESS_HOST='internal.example.net'
export PORT='443'
export CA_FILE='/path/to/internal-ca-bundle.pem'
export NEW_CERT_FILE='/path/to/new-certificate.pem'
export SECRET_REF='namespace/ingress-tls'
export PREVIOUS_VERSION='previous-secret-version'
export NEW_VERSION='new-secret-version'

export NODE_01='ingress-01.internal'
export NODE_02='ingress-02.internal'
export NODE_03='ingress-03.internal'
export NODE_04='ingress-04.internal'
export NODE_05='ingress-05.internal'
export NODE_06='ingress-06.internal'

export NODES=(
  "$NODE_01"
  "$NODE_02"
  "$NODE_03"
  "$NODE_04"
  "$NODE_05"
  "$NODE_06"
)

export CANARIES=(
  "$NODE_01"
  "$NODE_02"
)
```

Record `SECRET_REF`, `PREVIOUS_VERSION`, and `NEW_VERSION` in the change record.

Record the six node names in the change record.

## Check the new certificate

Run this command when `$NEW_CERT_FILE` contains the new leaf certificate.

```bash
openssl x509 \
  -in "$NEW_CERT_FILE" \
  -noout \
  -dates \
  -subject \
  -issuer \
  -serial \
  -fingerprint \
  -sha256
```

Run this command to display the certificate's DNS names.

```bash
openssl x509 \
  -in "$NEW_CERT_FILE" \
  -noout \
  -ext subjectAltName
```

Proceed only when the `subjectAltName` extension contains `$INGRESS_HOST`.

Proceed only when the new certificate's `notAfter` value is later than the current certificate's `notAfter` value.

Stop and contact the certificate owner when the new certificate lacks `$INGRESS_HOST` or has an invalid `notAfter` value.

Save the new certificate fingerprint.

```bash
export NEW_FINGERPRINT="$(
  openssl x509 \
    -in "$NEW_CERT_FILE" \
    -noout \
    -fingerprint \
    -sha256 |
  cut -d= -f2
)"

printf 'New certificate fingerprint: %s\n' "$NEW_FINGERPRINT"
```

## Define the endpoint check

Run this function for every ingress node.

```bash
set -o pipefail

check_node() {
  local node="$1"
  local report="/tmp/tls-${node}.txt"
  local verify_report="/tmp/tls-${node}.verify.txt"

  openssl s_client \
    -connect "${node}:${PORT}" \
    -servername "$INGRESS_HOST" \
    -CAfile "$CA_FILE" \
    -verify_return_error \
    -showcerts \
    </dev/null \
    2>"$verify_report" |
  openssl x509 \
    -noout \
    -dates \
    -subject \
    -issuer \
    -serial \
    -fingerprint \
    -sha256 |
  tee "$report"

  grep -F 'Verify return code: 0 (ok)' "$verify_report"
}
```

The function records certificate details in `/tmp/tls-<node>.txt`.

The function records chain verification output in `/tmp/tls-<node>.verify.txt`.

A valid endpoint check prints `Verify return code: 0 (ok)`.

## Record the current certificate

Run the endpoint check against all six nodes before changing the secret.

```bash
for node in "${NODES[@]}"; do
  check_node "$node"
done
```

Record the `notAfter` value, serial number, and SHA-256 fingerprint for each node.

Confirm that all six nodes serve the same current certificate fingerprint.

Stop when a node fails chain verification or serves a different certificate unexpectedly.

Record the current certificate fingerprint as the rollback fingerprint.

```bash
export PREVIOUS_FINGERPRINT='replace-with-recorded-fingerprint'
```

## Stage the new certificate on two nodes

Use the ingress platform's secret operation to assign `$NEW_VERSION` to `$NODE_01` and `$NODE_02`.

Record the platform command and its output in the change record.

Confirm that the control plane reports `$NEW_VERSION` for both canary nodes.

If the platform requires a node reload after secret assignment, reload `$NODE_01` first.

Wait for `$NODE_01` to report healthy before reloading `$NODE_02`.

If the platform reloads both nodes automatically, wait for both nodes to report healthy.

Reloading either canary node drops all open connections to that node.

## Verify the two canary nodes

Run the endpoint check against both canary nodes.

```bash
for node in "${CANARIES[@]}"; do
  check_node "$node"
done
```

Compare each canary's fingerprint with `$NEW_FINGERPRINT`.

```bash
for node in "${CANARIES[@]}"; do
  fingerprint="$(
    awk -F= '/SHA256 Fingerprint/ {print $2}' \
      "/tmp/tls-${node}.txt"
  )"

  test "$fingerprint" = "$NEW_FINGERPRINT" ||
    printf 'Fingerprint mismatch on %s\n' "$node"
done
```

Check the hostname on each canary certificate.

```bash
for node in "${CANARIES[@]}"; do
  openssl s_client \
    -connect "${node}:${PORT}" \
    -servername "$INGRESS_HOST" \
    -CAfile "$CA_FILE" \
    -verify_return_error \
    </dev/null 2>/dev/null |
  openssl x509 \
    -noout \
    -checkhost "$INGRESS_HOST"
done
```

Proceed only when both canaries meet all three conditions:

1. Each canary serves `$NEW_FINGERPRINT`.
2. Each canary prints `Verify return code: 0 (ok)`.
3. Each canary reports a hostname match for `$INGRESS_HOST`.

Stop the rollout when either canary fails one condition.

## Roll back the canaries when validation fails

Use this procedure when either canary fails validation.

Assign `$PREVIOUS_VERSION` to `$NODE_01` and `$NODE_02` through the ingress platform.

Record the platform command and its output in the change record.

Reload `$NODE_01` and `$NODE_02` one at a time.

Reloading each node drops all open connections to that node.

Run the endpoint check against both nodes.

```bash
for node in "${CANARIES[@]}"; do
  check_node "$node"
done
```

Confirm that both canaries serve `$PREVIOUS_FINGERPRINT`.

Page the platform owner when either canary does not return `$PREVIOUS_FINGERPRINT`.

## Roll the new certificate to the remaining four nodes

Roll the remaining nodes one at a time.

### Node 03

Assign `$NEW_VERSION` to `$NODE_03` through the ingress platform.

Reload `$NODE_03` after the platform reports the new version.

Run the endpoint check.

```bash
check_node "$NODE_03"
```

Proceed only when `$NODE_03` serves `$NEW_FINGERPRINT`, passes chain verification, and matches `$INGRESS_HOST`.

### Node 04

Assign `$NEW_VERSION` to `$NODE_04` through the ingress platform.

Reload `$NODE_04` after the platform reports the new version.

Run the endpoint check.

```bash
check_node "$NODE_04"
```

Proceed only when `$NODE_04` serves `$NEW_FINGERPRINT`, passes chain verification, and matches `$INGRESS_HOST`.

### Node 05

Assign `$NEW_VERSION` to `$NODE_05` through the ingress platform.

Reload `$NODE_05` after the platform reports the new version.

Run the endpoint check.

```bash
check_node "$NODE_05"
```

Proceed only when `$NODE_05` serves `$NEW_FINGERPRINT`, passes chain verification, and matches `$INGRESS_HOST`.

### Node 06

Assign `$NEW_VERSION` to `$NODE_06` through the ingress platform.

Reload `$NODE_06` after the platform reports the new version.

Run the endpoint check.

```bash
check_node "$NODE_06"
```

Proceed only when `$NODE_06` serves `$NEW_FINGERPRINT`, passes chain verification, and matches `$INGRESS_HOST`.

## Roll back after the full rollout

Use this procedure when any node fails after the rollout begins.

Record every node that received `$NEW_VERSION`.

Set the affected-node list before starting the rollback.

```bash
export UPDATED_NODES=(
  "$NODE_01"
  "$NODE_02"
  "$NODE_03"
  "$NODE_04"
  "$NODE_05"
  "$NODE_06"
)
```

Assign `$PREVIOUS_VERSION` to every node in `$UPDATED_NODES` through the ingress platform.

Confirm that the control plane reports `$PREVIOUS_VERSION` for every affected node.

Reload each affected node one at a time.

```bash
for node in "${UPDATED_NODES[@]}"; do
  echo "Reload $node through the ingress platform."
  read -r
done
```

Replace the loop body with the platform's node-reload command before execution.

Reloading each affected node drops all open connections to that node.

Run the endpoint check against every affected node.

```bash
for node in "${UPDATED_NODES[@]}"; do
  check_node "$node"
done
```

Confirm that every affected node serves `$PREVIOUS_FINGERPRINT`.

Page the platform owner when any affected node fails chain verification or serves another fingerprint.

## Complete the rotation

Run the endpoint check against all six nodes after successful rollout.

```bash
for node in "${NODES[@]}"; do
  check_node "$node"
done
```

Confirm that all six nodes serve `$NEW_FINGERPRINT`.

Confirm that all six nodes pass `Verify return code: 0 (ok)`.

Confirm that all six nodes match `$INGRESS_HOST`.

Record these values in the change record:

- `NEW_VERSION`.
- The new certificate `notAfter` value.
- The new certificate serial number.
- `$NEW_FINGERPRINT`.
- The validation result for each node.
- The reload time for each node.
- Any dropped-connection event reported by the ingress platform.

Retain `$PREVIOUS_VERSION` for the rollback period defined by the certificate owner.
