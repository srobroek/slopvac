# Rotate the TLS Certificate on the Six-Node Internal Ingress

Use this runbook when the certificate served by a six-node internal ingress approaches its expiration date.

Reloading a node drops that node’s open connections. Reload one node at a time.

## Rotation requirements

Complete these checks before changing any node:

- Confirm the secret manager supports immutable certificate versions.
- Confirm each node references the secret independently.
- Confirm all six nodes reference the same previous version.
- Confirm the new version contains the certificate, private key, and required certificate chain.
- Confirm the load balancer can identify each node by address.
- Confirm `openssl` is installed on the operator workstation.
- Confirm the internal CA bundle path.

Stop if the secret manager changes all six node references with one command. This runbook requires node-scoped secret references.

## Set the rotation variables

Set these variables with the values for the ingress:

```sh
SECRET_ID='internal-ingress-tls'
PREVIOUS_VERSION='<immutable-previous-version-id>'
NEW_VERSION='<immutable-new-version-id>'

SNI_NAME='ingress.internal.example'
CAFILE='/path/to/internal-ca-bundle.pem'

NODE_1='ingress-01'
NODE_1_IP='<node-1-ip>'
NODE_2='ingress-02'
NODE_2_IP='<node-2-ip>'
NODE_3='ingress-03'
NODE_3_IP='<node-3-ip>'
NODE_4='ingress-04'
NODE_4_IP='<node-4-ip>'
NODE_5='ingress-05'
NODE_5_IP='<node-5-ip>'
NODE_6='ingress-06'
NODE_6_IP='<node-6-ip>'

NEW_CERT='/path/to/new-leaf-certificate.pem'
MIN_REMAINING_SECONDS=$((30 * 86400))
WORKDIR="$(mktemp -d)"
```

Use an immutable identifier for `NEW_VERSION`. Do not use a mutable label such as `latest`.

The command templates below use `secretctl`, `ingressctl`, and `lbctl` as placeholders. Replace each template with the approved command for the ingress environment before execution.

```sh
point_secret() {
  node="$1"
  version="$2"

  secretctl point \
    --node "$node" \
    --secret "$SECRET_ID" \
    --version "$version"
}

show_secret_reference() {
  node="$1"

  secretctl show-reference \
    --node "$node" \
    --secret "$SECRET_ID"
}

reload_node() {
  node="$1"

  ingressctl reload --node "$node"
}

wait_ready() {
  node="$1"

  ingressctl wait-ready \
    --node "$node" \
    --timeout 60
}

drain_node() {
  node="$1"

  lbctl drain --node "$node"
}

undrain_node() {
  node="$1"

  lbctl undrain --node "$node"
}
```

## Check the current certificate

Create a function that retrieves the certificate served by one node:

```sh
set -o pipefail

fetch_node_certificate() {
  node="$1"
  node_ip="$2"
  output="$WORKDIR/$node.pem"
  error_log="$WORKDIR/$node.s_client.err"

  if ! openssl s_client \
      -connect "${node_ip}:443" \
      -servername "$SNI_NAME" \
      -showcerts \
      -verify_return_error \
      -verify_hostname "$SNI_NAME" \
      -CAfile "$CAFILE" \
      </dev/null 2>"$error_log" |
      openssl x509 -out "$output"; then
    printf 'TLS check failed for %s\n' "$node" >&2
    cat "$error_log" >&2
    return 1
  fi

  openssl x509 \
    -in "$output" \
    -noout \
    -subject \
    -issuer \
    -serial \
    -dates \
    -fingerprint \
    -sha256
}
```

Run the function for all six nodes:

```sh
fetch_node_certificate "$NODE_1" "$NODE_1_IP"
fetch_node_certificate "$NODE_2" "$NODE_2_IP"
fetch_node_certificate "$NODE_3" "$NODE_3_IP"
fetch_node_certificate "$NODE_4" "$NODE_4_IP"
fetch_node_certificate "$NODE_5" "$NODE_5_IP"
fetch_node_certificate "$NODE_6" "$NODE_6_IP"
```

Record the following output for each node:

- `notAfter`
- `serial`
- `SHA256 Fingerprint`
- Secret version reported by `show_secret_reference`

Check the secret reference on every node:

```sh
show_secret_reference "$NODE_1"
show_secret_reference "$NODE_2"
show_secret_reference "$NODE_3"
show_secret_reference "$NODE_4"
show_secret_reference "$NODE_5"
show_secret_reference "$NODE_6"
```

Stop if any node reports a version other than `$PREVIOUS_VERSION`. Record each node’s actual version before continuing.

## Validate the new certificate

Confirm that the new certificate can be parsed:

```sh
openssl x509 \
  -in "$NEW_CERT" \
  -noout \
  -subject \
  -issuer \
  -serial \
  -dates \
  -fingerprint \
  -sha256
```

Confirm that the new certificate remains valid for at least 30 days:

```sh
openssl x509 \
  -in "$NEW_CERT" \
  -checkend "$MIN_REMAINING_SECONDS" \
  -noout
```

Confirm that the new certificate chains to the internal CA bundle:

```sh
openssl verify \
  -CAfile "$CAFILE" \
  "$NEW_CERT"
```

Save the new certificate fingerprint:

```sh
EXPECTED_FINGERPRINT="$(
  openssl x509 \
    -in "$NEW_CERT" \
    -noout \
    -fingerprint \
    -sha256 |
    cut -d= -f2
)"

printf 'Expected SHA256 fingerprint: %s\n' "$EXPECTED_FINGERPRINT"
```

Stop if any validation command returns a nonzero exit status.

## Define the post-reload verification

Create a function that verifies the new certificate on one node:

```sh
verify_new_certificate() {
  node="$1"
  node_ip="$2"

  fetch_node_certificate "$node" "$node_ip"

  actual_fingerprint="$(
    openssl x509 \
      -in "$WORKDIR/$node.pem" \
      -noout \
      -fingerprint \
      -sha256 |
      cut -d= -f2
  )"

  if [ "$actual_fingerprint" != "$EXPECTED_FINGERPRINT" ]; then
    printf '%s served fingerprint %s, expected %s\n' \
      "$node" \
      "$actual_fingerprint" \
      "$EXPECTED_FINGERPRINT" >&2
    return 1
  fi

  openssl x509 \
    -in "$WORKDIR/$node.pem" \
    -checkend "$MIN_REMAINING_SECONDS" \
    -noout
}
```

The function checks the SNI name, certificate chain, certificate expiry, and certificate fingerprint.

## Stage the certificate on the first two nodes

Stage `$NEW_VERSION` on `NODE_1`:

```sh
point_secret "$NODE_1" "$NEW_VERSION"
show_secret_reference "$NODE_1"
```

Continue only when the reference command reports `$NEW_VERSION`.

If the load balancer supports node draining, drain `NODE_1`:

```sh
drain_node "$NODE_1"
```

Reload `NODE_1`:

```sh
reload_node "$NODE_1"
wait_ready "$NODE_1"
```

Verify `NODE_1`:

```sh
verify_new_certificate "$NODE_1" "$NODE_1_IP"
```

If `NODE_1` passes verification, restore it to service:

```sh
undrain_node "$NODE_1"
```

Stage `$NEW_VERSION` on `NODE_2`:

```sh
point_secret "$NODE_2" "$NEW_VERSION"
show_secret_reference "$NODE_2"
```

Continue only when the reference command reports `$NEW_VERSION`.

If the load balancer supports node draining, drain `NODE_2`:

```sh
drain_node "$NODE_2"
```

Reload `NODE_2`:

```sh
reload_node "$NODE_2"
wait_ready "$NODE_2"
```

Verify `NODE_2`:

```sh
verify_new_certificate "$NODE_2" "$NODE_2_IP"
```

If `NODE_2` passes verification, restore it to service:

```sh
undrain_node "$NODE_2"
```

Stop the rollout if either staged node fails readiness or certificate verification.

## Roll the certificate to the remaining four nodes

Roll the remaining nodes in this order:

1. `NODE_3`
2. `NODE_4`
3. `NODE_5`
4. `NODE_6`

Process one node completely before starting the next node.

For each node, run the following sequence:

```sh
node="$NODE_3"
node_ip="$NODE_3_IP"

point_secret "$node" "$NEW_VERSION"
show_secret_reference "$node"

drain_node "$node"
reload_node "$node"
wait_ready "$node"
verify_new_certificate "$node" "$node_ip"
undrain_node "$node"
```

Repeat the sequence for `NODE_4`:

```sh
node="$NODE_4"
node_ip="$NODE_4_IP"

point_secret "$node" "$NEW_VERSION"
show_secret_reference "$node"

drain_node "$node"
reload_node "$node"
wait_ready "$node"
verify_new_certificate "$node" "$node_ip"
undrain_node "$node"
```

Repeat the sequence for `NODE_5`:

```sh
node="$NODE_5"
node_ip="$NODE_5_IP"

point_secret "$node" "$NEW_VERSION"
show_secret_reference "$node"

drain_node "$node"
reload_node "$node"
wait_ready "$node"
verify_new_certificate "$node" "$node_ip"
undrain_node "$node"
```

Repeat the sequence for `NODE_6`:

```sh
node="$NODE_6"
node_ip="$NODE_6_IP"

point_secret "$node" "$NEW_VERSION"
show_secret_reference "$node"

drain_node "$node"
reload_node "$node"
wait_ready "$node"
verify_new_certificate "$node" "$node_ip"
undrain_node "$node"
```

Stop the rollout when a node fails any of these checks:

- The secret reference does not report `$NEW_VERSION`.
- The node does not become ready within 60 seconds.
- The TLS handshake fails.
- The SNI name does not match.
- The certificate chain does not verify against `$CAFILE`.
- The SHA256 fingerprint differs from `$EXPECTED_FINGERPRINT`.
- The certificate has fewer than 30 days remaining.

## Verify all six nodes

Run the final verification for every node:

```sh
verify_new_certificate "$NODE_1" "$NODE_1_IP"
verify_new_certificate "$NODE_2" "$NODE_2_IP"
verify_new_certificate "$NODE_3" "$NODE_3_IP"
verify_new_certificate "$NODE_4" "$NODE_4_IP"
verify_new_certificate "$NODE_5" "$NODE_5_IP"
verify_new_certificate "$NODE_6" "$NODE_6_IP"
```

Check the secret reference on every node:

```sh
show_secret_reference "$NODE_1"
show_secret_reference "$NODE_2"
show_secret_reference "$NODE_3"
show_secret_reference "$NODE_4"
show_secret_reference "$NODE_5"
show_secret_reference "$NODE_6"
```

Complete the rotation only when all six nodes report `$NEW_VERSION` and `$EXPECTED_FINGERPRINT`.

Keep `$PREVIOUS_VERSION` available until the certificate has passed the organization’s rollback-retention period.

## Roll back to the previous certificate

Start rollback when any rotated node fails readiness, TLS verification, or certificate fingerprint validation.

Rollback only nodes that already received `$NEW_VERSION`. Use reverse rollout order.

For each affected node, point the node to `$PREVIOUS_VERSION`, reload it, verify the previous certificate, and restore traffic:

```sh
rollback_node() {
  node="$1"
  node_ip="$2"
  expected_previous_fingerprint="$3"

  point_secret "$node" "$PREVIOUS_VERSION"
  show_secret_reference "$node"

  drain_node "$node"
  reload_node "$node"
  wait_ready "$node"

  fetch_node_certificate "$node" "$node_ip"

  actual_fingerprint="$(
    openssl x509 \
      -in "$WORKDIR/$node.pem" \
      -noout \
      -fingerprint \
      -sha256 |
      cut -d= -f2
  )"

  if [ "$actual_fingerprint" != "$expected_previous_fingerprint" ]; then
    printf '%s served fingerprint %s, expected %s\n' \
      "$node" \
      "$actual_fingerprint" \
      "$expected_previous_fingerprint" >&2
    return 1
  fi

  undrain_node "$node"
}
```

Set `EXPECTED_PREVIOUS_FINGERPRINT` to the fingerprint recorded during the pre-rotation check:

```sh
EXPECTED_PREVIOUS_FINGERPRINT='<recorded-previous-certificate-sha256-fingerprint>'
```

Roll back `NODE_6`, `NODE_5`, `NODE_4`, `NODE_3`, `NODE_2`, and `NODE_1` only when each node received `$NEW_VERSION`:

```sh
rollback_node "$NODE_6" "$NODE_6_IP" "$EXPECTED_PREVIOUS_FINGERPRINT"
rollback_node "$NODE_5" "$NODE_5_IP" "$EXPECTED_PREVIOUS_FINGERPRINT"
rollback_node "$NODE_4" "$NODE_4_IP" "$EXPECTED_PREVIOUS_FINGERPRINT"
rollback_node "$NODE_3" "$NODE_3_IP" "$EXPECTED_PREVIOUS_FINGERPRINT"
rollback_node "$NODE_2" "$NODE_2_IP" "$EXPECTED_PREVIOUS_FINGERPRINT"
rollback_node "$NODE_1" "$NODE_1_IP" "$EXPECTED_PREVIOUS_FINGERPRINT"
```

Verify that every rolled-back node reports `$PREVIOUS_VERSION`:

```sh
show_secret_reference "$NODE_1"
show_secret_reference "$NODE_2"
show_secret_reference "$NODE_3"
show_secret_reference "$NODE_4"
show_secret_reference "$NODE_5"
show_secret_reference "$NODE_6"
```

Verify that every rolled-back node serves `$EXPECTED_PREVIOUS_FINGERPRINT`:

```sh
fetch_node_certificate "$NODE_1" "$NODE_1_IP"
fetch_node_certificate "$NODE_2" "$NODE_2_IP"
fetch_node_certificate "$NODE_3" "$NODE_3_IP"
fetch_node_certificate "$NODE_4" "$NODE_4_IP"
fetch_node_certificate "$NODE_5" "$NODE_5_IP"
fetch_node_certificate "$NODE_6" "$NODE_6_IP"
```

Escalate if a node does not become ready after rollback or does not serve the previous fingerprint.
