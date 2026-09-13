# Rotate the TLS certificate on the six-node internal ingress

## Scope

Use this runbook to replace the certificate served by a six-node internal ingress.

The procedure updates two canary nodes before updating the remaining four nodes.

A node reload drops its open connections.

Reload exactly one node at a time.

## Required access

You need access to these systems:

- The certificate and private-key files.
- The internal certificate authority bundle.
- The secret store that contains the TLS bundle.
- The load balancer that drains and restores nodes.
- The node administration system that reloads ingress processes.
- A shell with OpenSSL 1.1.1 or OpenSSL 3.

## Define the values

Replace every angle-bracket value before running a command.

| Variable | Value |
|---|---|
| `INGRESS_HOST` | DNS name clients use for the ingress |
| `CA_BUNDLE` | PEM bundle for the internal certificate authority |
| `TLS_SECRET` | Secret name that ingress nodes read |
| `NEW_CERT` | Path to the replacement certificate |
| `NEW_KEY` | Path to the replacement private key |
| `NEW_CHAIN` | Path to the replacement intermediate certificate chain |
| `NODE_1` and `NODE_2` | Two canary node names or IP addresses |
| `NODE_3` through `NODE_6` | Four remaining node names or IP addresses |
| `PREVIOUS_VERSION` | Secret version currently serving traffic |
| `NEW_VERSION` | Secret version containing the replacement TLS bundle |

```sh
export INGRESS_HOST="<internal-ingress.example>"
export CA_BUNDLE="<path-to-internal-ca-bundle.pem>"
export TLS_SECRET="<tls-secret-name>"
export NEW_CERT="<path-to-new-certificate.pem>"
export NEW_KEY="<path-to-new-private-key.pem>"
export NEW_CHAIN="<path-to-new-intermediate-chain.pem>"

export NODE_1="<node-1>"
export NODE_2="<node-2>"
export NODE_3="<node-3>"
export NODE_4="<node-4>"
export NODE_5="<node-5>"
export NODE_6="<node-6>"
```

## Record the current state

Record the secret version that the ingress serves before changing the secret pointer.

```text
<secret-cli> get-pointer --secret "$TLS_SECRET"
```

Set `PREVIOUS_VERSION` to the returned version.

List the available versions and confirm that `PREVIOUS_VERSION` remains available.

```text
<secret-cli> list-versions --secret "$TLS_SECRET"
```

Record the certificate serial number and expiry date from each node.

```sh
for node in "$NODE_1" "$NODE_2" "$NODE_3" "$NODE_4" "$NODE_5" "$NODE_6"; do
  echo "=== $node ==="
  openssl s_client \
    -connect "${node}:443" \
    -servername "$INGRESS_HOST" \
    -CAfile "$CA_BUNDLE" \
    -verify_return_error \
    </dev/null >/dev/null
  test "${PIPESTATUS[0]}" -eq 0

  openssl s_client \
    -connect "${node}:443" \
    -servername "$INGRESS_HOST" \
    -showcerts \
    </dev/null 2>/dev/null |
    openssl x509 \
      -noout \
      -serial \
      -dates \
      -subject \
      -issuer \
      -fingerprint -sha256
done
```

If any node fails certificate verification, stop and investigate before rotating the certificate.

If the six nodes do not serve the same current certificate, stop and identify the active secret version on each node.

## Check the replacement certificate

Display the replacement certificate identity and validity period.

```sh
openssl x509 \
  -in "$NEW_CERT" \
  -noout \
  -serial \
  -dates \
  -subject \
  -issuer \
  -fingerprint -sha256
```

Display the certificate subject alternative names.

```sh
openssl x509 \
  -in "$NEW_CERT" \
  -noout \
  -ext subjectAltName
```

Confirm that `INGRESS_HOST` appears in the subject alternative names.

Confirm that the replacement certificate has not expired.

```sh
openssl x509 \
  -in "$NEW_CERT" \
  -checkend 0 \
  -noout
```

Confirm that the replacement private key matches the replacement certificate.

```sh
CERT_PUBLIC_KEY_HASH="$(
  openssl x509 -in "$NEW_CERT" -pubkey -noout |
    openssl pkey -pubin -outform DER |
    openssl dgst -sha256
)"

KEY_PUBLIC_KEY_HASH="$(
  openssl pkey -in "$NEW_KEY" -pubout -outform DER |
    openssl dgst -sha256
)"

test "$CERT_PUBLIC_KEY_HASH" = "$KEY_PUBLIC_KEY_HASH"
```

Confirm that the replacement certificate validates against the internal certificate authority.

```sh
openssl verify \
  -CAfile "$CA_BUNDLE" \
  -untrusted "$NEW_CHAIN" \
  "$NEW_CERT"
```

Stop if any certificate check fails.

## Check the secret version

Publish the replacement certificate, private key, and chain as `NEW_VERSION`.

Use the secret store command for your platform.

```text
<secret-cli> create-version \
  --secret "$TLS_SECRET" \
  --certificate "$NEW_CERT" \
  --private-key "$NEW_KEY" \
  --chain "$NEW_CHAIN"
```

Set `NEW_VERSION` to the returned immutable version identifier.

Read `NEW_VERSION` from the secret store and confirm that it contains the replacement certificate.

```text
<secret-cli> get-version --secret "$TLS_SECRET" --version "$NEW_VERSION"
```

Do not delete or overwrite `PREVIOUS_VERSION`.

## Prepare node reloads

Confirm that the load balancer can drain one node and report zero active connections.

```text
<lb-cli> status --node "$NODE_1"
<lb-cli> drain --node "$NODE_1"
<lb-cli> wait-for-zero-connections --node "$NODE_1"
```

Use the equivalent commands for the remaining nodes.

If the load balancer cannot drain a node, schedule the reload for an approved interruption window.

## Stage the replacement on the two canary nodes

Re-point the secret to `NEW_VERSION`.

```text
<secret-cli> point \
  --secret "$TLS_SECRET" \
  --version "$NEW_VERSION"
```

Reload `NODE_1` only after its connections reach zero.

```text
<node-cli> reload-ingress --node "$NODE_1"
```

Restore `NODE_1` to service after the reload completes.

```text
<lb-cli> undrain --node "$NODE_1"
```

Verify `NODE_1` with `openssl s_client`.

```sh
openssl s_client \
  -connect "${NODE_1}:443" \
  -servername "$INGRESS_HOST" \
  -CAfile "$CA_BUNDLE" \
  -verify_return_error \
  </dev/null >/dev/null
```

Inspect the certificate served by `NODE_1`.

```sh
openssl s_client \
  -connect "${NODE_1}:443" \
  -servername "$INGRESS_HOST" \
  -showcerts \
  </dev/null 2>/dev/null |
  openssl x509 \
    -noout \
    -serial \
    -dates \
    -subject \
    -issuer \
    -fingerprint -sha256
```

Confirm that the serial number and SHA-256 fingerprint match `NEW_VERSION`.

If `NODE_1` passes, repeat the same sequence for `NODE_2`.

```text
<lb-cli> drain --node "$NODE_2"
<lb-cli> wait-for-zero-connections --node "$NODE_2"
<node-cli> reload-ingress --node "$NODE_2"
<lb-cli> undrain --node "$NODE_2"
```

Verify `NODE_2` with the same `openssl s_client` commands.

Do not continue if either canary node fails verification.

## Roll the replacement to the remaining four nodes

Process `NODE_3` through `NODE_6` one at a time.

For each node, drain connections before reloading the ingress process.

```text
<lb-cli> drain --node "<node>"
<lb-cli> wait-for-zero-connections --node "<node>"
<node-cli> reload-ingress --node "<node>"
<lb-cli> undrain --node "<node>"
```

Verify each node before processing the next node.

```sh
openssl s_client \
  -connect "<node>:443" \
  -servername "$INGRESS_HOST" \
  -CAfile "$CA_BUNDLE" \
  -verify_return_error \
  </dev/null >/dev/null

openssl s_client \
  -connect "<node>:443" \
  -servername "$INGRESS_HOST" \
  -showcerts \
  </dev/null 2>/dev/null |
  openssl x509 \
    -noout \
    -serial \
    -dates \
    -subject \
    -issuer \
    -fingerprint -sha256
```

Confirm that each node serves the serial number and fingerprint from `NEW_VERSION`.

Stop the rollout if a node fails to reload, fails certificate verification, or serves `PREVIOUS_VERSION` after reload.

## Verify all six nodes

Run the verification against all six nodes after the rollout.

```sh
for node in "$NODE_1" "$NODE_2" "$NODE_3" "$NODE_4" "$NODE_5" "$NODE_6"; do
  echo "=== $node ==="

  openssl s_client \
    -connect "${node}:443" \
    -servername "$INGRESS_HOST" \
    -CAfile "$CA_BUNDLE" \
    -verify_return_error \
    </dev/null >/dev/null

  openssl s_client \
    -connect "${node}:443" \
    -servername "$INGRESS_HOST" \
    -showcerts \
    </dev/null 2>/dev/null |
    openssl x509 \
      -noout \
      -serial \
      -dates \
      -subject \
      -issuer \
      -fingerprint -sha256
done
```

Confirm that all six nodes meet these conditions:

- `openssl s_client` exits successfully.
- The certificate contains `INGRESS_HOST`.
- The certificate serial number matches `NEW_VERSION`.
- The certificate SHA-256 fingerprint matches `NEW_VERSION`.
- The certificate expiry date is later than the previous certificate expiry date.
- The load balancer reports each node as healthy.

Confirm that the secret pointer still references `NEW_VERSION`.

```text
<secret-cli> get-pointer --secret "$TLS_SECRET"
```

## Roll back to the previous version

Roll back if any node fails certificate verification or serves the wrong certificate.

Re-point the secret to `PREVIOUS_VERSION`.

```text
<secret-cli> point \
  --secret "$TLS_SECRET" \
  --version "$PREVIOUS_VERSION"
```

Identify every node that was reloaded after the replacement became active.

Reload each affected node one at a time.

```text
<lb-cli> drain --node "<node>"
<lb-cli> wait-for-zero-connections --node "<node>"
<node-cli> reload-ingress --node "<node>"
<lb-cli> undrain --node "<node>"
```

Verify each reloaded node with `openssl s_client`.

```sh
openssl s_client \
  -connect "<node>:443" \
  -servername "$INGRESS_HOST" \
  -CAfile "$CA_BUNDLE" \
  -verify_return_error \
  </dev/null >/dev/null
```

Inspect the certificate served by each reloaded node.

```sh
openssl s_client \
  -connect "<node>:443" \
  -servername "$INGRESS_HOST" \
  -showcerts \
  </dev/null 2>/dev/null |
  openssl x509 \
    -noout \
    -serial \
    -dates \
    -subject \
    -issuer \
    -fingerprint -sha256
```

Confirm that each reloaded node serves the serial number and fingerprint recorded for `PREVIOUS_VERSION`.

Verify all six nodes after the rollback.

If `PREVIOUS_VERSION` fails certificate verification or has expired, keep the affected node out of service and escalate to the certificate owner.
