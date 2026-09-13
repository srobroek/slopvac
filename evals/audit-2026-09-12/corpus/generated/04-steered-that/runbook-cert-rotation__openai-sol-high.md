# Rotate the internal ingress TLS certificate

## Scope

This runbook rotates the TLS certificate across six internal ingress nodes.

The rollout stages two canary nodes before changing the other four nodes.

> [!WARNING]
> Reloading the ingress service drops every open connection on the target node.
> Reload one node at a time, and verify that node before reloading another node.

## Stop conditions

Stop the rollout when any of these conditions occurs:

- Two nodes reference different previous secret versions.
- Two nodes present different previous certificate fingerprints.
- The new certificate does not match the private key.
- The new certificate fails the configured validity threshold.
- `openssl s_client` reports a certificate verification error.
- `systemctl reload` returns a nonzero exit code.
- `systemctl is-active` returns a nonzero exit code.

If a stop condition occurs after a reload, roll back every changed node before investigating.

## Required access and files

Confirm that the on-call account has these resources:

- SSH access with `sudo` privileges on all six ingress nodes.
- The new certificate chain in PEM format.
- The matching private key in PEM format.
- The internal certificate authority bundle in PEM format.
- The systemd unit name from the service inventory.
- The six node addresses from the service inventory.
- A maintenance window covering six connection-dropping reloads.

## Configure the shell

Run every Bash block in one shell so that variables and functions persist.

Replace each example value with the corresponding value from the service inventory.

```bash
set -euo pipefail

export INGRESS_HOST='ingress.example.internal'
export TLS_PORT='443'
export CA_FILE='/secure/path/internal-ca.pem'
export CERT_FILE='/secure/path/tls.crt'
export KEY_FILE='/secure/path/tls.key'
export NEW_VERSION='certificate-version'
export TLS_ROOT='/etc/internal-ingress/tls'
export INGRESS_GROUP='internal-ingress'
export INGRESS_UNIT='internal-ingress'

# Set this threshold from the certificate policy.
export MIN_NEW_VALIDITY_SECONDS='2592000'

NODES=(
  'ingress-01.example.internal'
  'ingress-02.example.internal'
  'ingress-03.example.internal'
  'ingress-04.example.internal'
  'ingress-05.example.internal'
  'ingress-06.example.internal'
)

CANARY_NODES=(
  "${NODES[0]}"
  "${NODES[1]}"
)

REMAINING_NODES=(
  "${NODES[2]}"
  "${NODES[3]}"
  "${NODES[4]}"
  "${NODES[5]}"
)

ROLLBACK_ORDER=(
  "${NODES[5]}"
  "${NODES[4]}"
  "${NODES[3]}"
  "${NODES[2]}"
  "${NODES[1]}"
  "${NODES[0]}"
)

WORKDIR="$(mktemp -d)"
chmod 0700 "$WORKDIR"

[[ "$NEW_VERSION" =~ ^[A-Za-z0-9._-]+$ ]]
test -r "$CA_FILE"
test -r "$CERT_FILE"
test -r "$KEY_FILE"
```

## Define the helper functions

```bash
presented_certificate()
{
  local node="$1"

  openssl s_client \
    -connect "${node}:${TLS_PORT}" \
    -servername "$INGRESS_HOST" \
    -showcerts \
    </dev/null 2>/dev/null |
    openssl x509 -outform PEM
}

presented_fingerprint()
{
  local node="$1"

  presented_certificate "$node" |
    openssl x509 -noout -fingerprint -sha256 |
    cut -d= -f2-
}

verify_node()
{
  local node="$1"
  local expected_fingerprint="$2"
  local required_validity_seconds="$3"
  local output_file
  local actual_fingerprint

  output_file="${WORKDIR}/${node//[^A-Za-z0-9._-]/_}.s_client.txt"

  if ! openssl s_client \
    -connect "${node}:${TLS_PORT}" \
    -servername "$INGRESS_HOST" \
    -CAfile "$CA_FILE" \
    -verify_hostname "$INGRESS_HOST" \
    -verify_return_error \
    </dev/null >"$output_file" 2>&1
  then
    cat "$output_file"
    return 1
  fi

  grep -F 'Verify return code: 0 (ok)' "$output_file"

  actual_fingerprint="$(presented_fingerprint "$node")"
  test "$actual_fingerprint" = "$expected_fingerprint"

  presented_certificate "$node" |
    openssl x509 -checkend "$required_validity_seconds" -noout

  printf '%s verified with fingerprint %s\n' \
    "$node" \
    "$actual_fingerprint"
}

stage_secret()
{
  local node="$1"
  local target="${TLS_ROOT}/versions/${NEW_VERSION}"
  local active_target
  local remote_cert_sha256
  local remote_key_sha256

  active_target="$(
    ssh "$node" "sudo readlink -f '$TLS_ROOT/current'"
  )"

  test "$active_target" != "$target"

  ssh "$node" \
    "sudo install -d -o root -g '$INGRESS_GROUP' -m 0750 '$target'"

  ssh "$node" \
    "sudo tee '$target/tls.crt' >/dev/null" <"$CERT_FILE"

  ssh "$node" \
    "sudo tee '$target/tls.key' >/dev/null" <"$KEY_FILE"

  ssh "$node" \
    "sudo chown root:'$INGRESS_GROUP' '$target/tls.crt' '$target/tls.key'"

  ssh "$node" \
    "sudo chmod 0644 '$target/tls.crt' && sudo chmod 0640 '$target/tls.key'"

  remote_cert_sha256="$(
    ssh "$node" "sudo openssl dgst -sha256 '$target/tls.crt'" |
      awk '{print $NF}'
  )"

  remote_key_sha256="$(
    ssh "$node" "sudo openssl dgst -sha256 '$target/tls.key'" |
      awk '{print $NF}'
  )"

  test "$remote_cert_sha256" = "$CERT_FILE_SHA256"
  test "$remote_key_sha256" = "$KEY_FILE_SHA256"

  printf '%s staged secret version %s\n' "$node" "$NEW_VERSION"
}

point_and_reload()
{
  local node="$1"
  local version="$2"
  local target="${TLS_ROOT}/versions/${version}"
  local pointer="${TLS_ROOT}/current"
  local temporary_pointer="${TLS_ROOT}/.current.next"

  ssh "$node" "
    set -eu
    sudo test -s '$target/tls.crt'
    sudo test -s '$target/tls.key'
    sudo rm -f '$temporary_pointer'
    sudo ln -s '$target' '$temporary_pointer'
    sudo mv -Tf '$temporary_pointer' '$pointer'
    test \"\$(sudo readlink -f '$pointer')\" = '$target'
    sudo systemctl reload '$INGRESS_UNIT'
    sudo systemctl is-active --quiet '$INGRESS_UNIT'
  "
}

rollback_node()
{
  local node="$1"

  point_and_reload "$node" "$PREVIOUS_VERSION"
  verify_node "$node" "$PREVIOUS_FINGERPRINT" 0

  printf '%s rolled back to secret version %s\n' \
    "$node" \
    "$PREVIOUS_VERSION"
}
```

## Check the presented certificate expiry

Capture the subject, issuer, serial number, validity dates, and SHA-256 fingerprint from every node.

```bash
for node in "${NODES[@]}"
do
  printf '\n=== %s ===\n' "$node"

  presented_certificate "$node" |
    openssl x509 \
      -noout \
      -subject \
      -issuer \
      -serial \
      -dates \
      -fingerprint \
      -sha256
done | tee "$WORKDIR/pre-rotation-certificates.txt"
```

Confirm that every `notAfter` value occurs after the planned rollback window.

Confirm that the previous certificate has not expired on any node.

```bash
for node in "${NODES[@]}"
do
  presented_certificate "$node" |
    openssl x509 -checkend 0 -noout
done
```

## Capture the rollback version

Read the secret version from the first node.

```bash
PREVIOUS_TARGET="$(
  ssh "${NODES[0]}" "sudo readlink -f '$TLS_ROOT/current'"
)"

PREVIOUS_VERSION="$(basename "$PREVIOUS_TARGET")"
PREVIOUS_FINGERPRINT="$(presented_fingerprint "${NODES[0]}")"

printf 'Previous version: %s\n' "$PREVIOUS_VERSION"
printf 'Previous fingerprint: %s\n' "$PREVIOUS_FINGERPRINT"
```

Confirm that all six nodes reference the same previous version and present the same fingerprint.

```bash
for node in "${NODES[@]}"
do
  node_target="$(
    ssh "$node" "sudo readlink -f '$TLS_ROOT/current'"
  )"

  node_fingerprint="$(presented_fingerprint "$node")"

  test "$node_target" = "$PREVIOUS_TARGET"
  test "$node_fingerprint" = "$PREVIOUS_FINGERPRINT"

  printf '%s uses version %s with fingerprint %s\n' \
    "$node" \
    "$PREVIOUS_VERSION" \
    "$node_fingerprint"
done
```

## Validate the new certificate

Display the new certificate identity and validity period.

```bash
openssl x509 \
  -in "$CERT_FILE" \
  -noout \
  -subject \
  -issuer \
  -serial \
  -dates \
  -fingerprint \
  -sha256
```

Confirm that the certificate remains valid for the configured threshold.

```bash
openssl x509 \
  -in "$CERT_FILE" \
  -checkend "$MIN_NEW_VALIDITY_SECONDS" \
  -noout
```

Confirm that the certificate covers the ingress hostname.

```bash
openssl x509 \
  -in "$CERT_FILE" \
  -noout \
  -checkhost "$INGRESS_HOST"
```

Confirm that the certificate and private key contain the same public key.

```bash
CERT_PUBLIC_KEY_SHA256="$(
  openssl x509 -in "$CERT_FILE" -pubkey -noout |
    openssl pkey -pubin -outform DER 2>/dev/null |
    openssl dgst -sha256 |
    awk '{print $NF}'
)"

KEY_PUBLIC_KEY_SHA256="$(
  openssl pkey -in "$KEY_FILE" -pubout -outform DER 2>/dev/null |
    openssl dgst -sha256 |
    awk '{print $NF}'
)"

test "$CERT_PUBLIC_KEY_SHA256" = "$KEY_PUBLIC_KEY_SHA256"

printf 'Matching public-key SHA-256: %s\n' \
  "$CERT_PUBLIC_KEY_SHA256"
```

Calculate the values used to verify each staged file.

```bash
CERT_FILE_SHA256="$(
  openssl dgst -sha256 "$CERT_FILE" |
    awk '{print $NF}'
)"

KEY_FILE_SHA256="$(
  openssl dgst -sha256 "$KEY_FILE" |
    awk '{print $NF}'
)"

NEW_FINGERPRINT="$(
  openssl x509 -in "$CERT_FILE" -noout -fingerprint -sha256 |
    cut -d= -f2-
)"

printf 'Certificate file SHA-256: %s\n' "$CERT_FILE_SHA256"
printf 'Private-key file SHA-256: %s\n' "$KEY_FILE_SHA256"
printf 'New certificate fingerprint: %s\n' "$NEW_FINGERPRINT"
```

## Stage the two canary nodes

Copy the new secret version to both canary nodes without changing either secret pointer.

```bash
stage_secret "${CANARY_NODES[0]}"
stage_secret "${CANARY_NODES[1]}"
```

Confirm that both canary nodes still present the previous certificate.

```bash
verify_node "${CANARY_NODES[0]}" "$PREVIOUS_FINGERPRINT" 0
verify_node "${CANARY_NODES[1]}" "$PREVIOUS_FINGERPRINT" 0
```

## Reload the first canary node

Notify the maintenance channel before running the reload command.

```bash
point_and_reload "${CANARY_NODES[0]}" "$NEW_VERSION"
```

Verify the first canary immediately after the reload.

```bash
verify_node \
  "${CANARY_NODES[0]}" \
  "$NEW_FINGERPRINT" \
  "$MIN_NEW_VALIDITY_SECONDS"
```

If verification fails, run this command and stop the rollout:

```bash
rollback_node "${CANARY_NODES[0]}"
```

## Reload the second canary node

Reload the second canary only after the first canary passes verification.

```bash
point_and_reload "${CANARY_NODES[1]}" "$NEW_VERSION"
```

Verify the second canary immediately after the reload.

```bash
verify_node \
  "${CANARY_NODES[1]}" \
  "$NEW_FINGERPRINT" \
  "$MIN_NEW_VALIDITY_SECONDS"
```

If verification fails, run these commands and stop the rollout:

```bash
rollback_node "${CANARY_NODES[1]}"
rollback_node "${CANARY_NODES[0]}"
```

## Observe the canary nodes

Probe both canary nodes once per minute for ten minutes.

```bash
for attempt in $(seq 1 10)
do
  printf 'Canary probe %s of 10\n' "$attempt"

  verify_node \
    "${CANARY_NODES[0]}" \
    "$NEW_FINGERPRINT" \
    "$MIN_NEW_VALIDITY_SECONDS"

  verify_node \
    "${CANARY_NODES[1]}" \
    "$NEW_FINGERPRINT" \
    "$MIN_NEW_VALIDITY_SECONDS"

  sleep 60
done
```

If any probe fails, roll back both canary nodes and stop the rollout.

```bash
rollback_node "${CANARY_NODES[1]}"
rollback_node "${CANARY_NODES[0]}"
```

## Stage the other four nodes

Stage the same certificate and private key on the four unchanged nodes.

```bash
for node in "${REMAINING_NODES[@]}"
do
  stage_secret "$node"
done
```

Confirm that the four nodes still present the previous certificate.

```bash
for node in "${REMAINING_NODES[@]}"
do
  verify_node "$node" "$PREVIOUS_FINGERPRINT" 0
done
```

## Roll the other four nodes

The following loop reloads and verifies one node before processing the next node.

```bash
for node in "${REMAINING_NODES[@]}"
do
  printf 'Reloading %s\n' "$node"

  if ! point_and_reload "$node" "$NEW_VERSION"
  then
    rollback_node "$node"
    exit 1
  fi

  if ! verify_node \
    "$node" \
    "$NEW_FINGERPRINT" \
    "$MIN_NEW_VALIDITY_SECONDS"
  then
    rollback_node "$node"
    exit 1
  fi

  printf '%s completed at %s\n' \
    "$node" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
done
```

## Verify the six-node fleet

Confirm that every secret pointer references the new version.

```bash
for node in "${NODES[@]}"
do
  target="$(
    ssh "$node" "sudo readlink -f '$TLS_ROOT/current'"
  )"

  test "$target" = "${TLS_ROOT}/versions/${NEW_VERSION}"

  printf '%s points to %s\n' "$node" "$target"
done
```

Verify the TLS chain, hostname, fingerprint, and validity threshold on all six nodes.

```bash
for node in "${NODES[@]}"
do
  verify_node \
    "$node" \
    "$NEW_FINGERPRINT" \
    "$MIN_NEW_VALIDITY_SECONDS"
done
```

Confirm that the ingress service remains active on all six nodes.

```bash
for node in "${NODES[@]}"
do
  ssh "$node" \
    "sudo systemctl is-active '$INGRESS_UNIT'"
done
```

Do not delete the previous secret version during this procedure.

## Roll back the fleet

Use this procedure when the new certificate causes verification or client connection failures.

Re-point and reload one changed node at a time because each reload drops that node's open connections.

```bash
for node in "${ROLLBACK_ORDER[@]}"
do
  target="$(
    ssh "$node" "sudo readlink -f '$TLS_ROOT/current'"
  )"

  if test "$target" = "${TLS_ROOT}/versions/${NEW_VERSION}"
  then
    rollback_node "$node"
  fi
done
```

Confirm that all six nodes reference and present the previous secret version.

```bash
for node in "${NODES[@]}"
do
  target="$(
    ssh "$node" "sudo readlink -f '$TLS_ROOT/current'"
  )"

  test "$target" = "${TLS_ROOT}/versions/${PREVIOUS_VERSION}"
  verify_node "$node" "$PREVIOUS_FINGERPRINT" 0
done
```

## Record the execution

Record one row immediately after verifying each reload.

| Node | Previous version | New version | Reload time in UTC | Presented fingerprint | Result |
|---|---|---|---|---|---|
| Node 1 |  |  |  |  |  |
| Node 2 |  |  |  |  |  |
| Node 3 |  |  |  |  |  |
| Node 4 |  |  |  |  |  |
| Node 5 |  |  |  |  |  |
| Node 6 |  |  |  |  |  |

## Completion criteria

Complete the change only when all criteria pass:

- All six secret pointers reference `$NEW_VERSION`.
- All six services return `active` from `systemctl is-active`.
- All six `openssl s_client` checks report `Verify return code: 0 (ok)`.
- All six nodes present `$NEW_FINGERPRINT`.
- All six certificates pass `$MIN_NEW_VALIDITY_SECONDS`.
- The previous secret version remains available for rollback.
- The execution record contains six completed rows.
