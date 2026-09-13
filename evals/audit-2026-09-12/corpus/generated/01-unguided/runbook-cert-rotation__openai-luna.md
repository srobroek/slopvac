# Runbook: Rotate an Expiring TLS Certificate on a Six-Node Internal Ingress

## Purpose

Use this runbook to replace an expiring TLS certificate on a six-node internal ingress with minimal service disruption.

The procedure:

1. Checks the current certificate expiry.
2. Stages the replacement certificate on two nodes.
3. Verifies the replacement with `openssl s_client`.
4. Rolls the replacement certificate to the remaining four nodes.
5. Provides a rollback procedure that re-points the secret to the previous version.

> **Important:** Reloading an ingress node drops its open connections. Drain each node from the load balancer before reloading it, and allow existing traffic to move to the other nodes.

---

## Scope and assumptions

This runbook assumes:

- The ingress has six nodes.
- Each node serves the same TLS hostname.
- The certificate is stored in a versioned secret or secret manager.
- Nodes retrieve the current secret version when the ingress is reloaded.
- The load balancer supports draining or temporarily removing individual nodes.
- You can connect directly to each node for testing.
- The ingress listens on TCP port `443`.

Replace the example commands below with the approved commands for your environment. The placeholders are intentionally explicit so that they can be reviewed before execution.

---

## Required information

Set or record these values before starting:

```bash
export TLS_HOST="internal.example.com"
export TLS_PORT="443"

export NODE_1="ingress-01.example.net"
export NODE_2="ingress-02.example.net"
export NODE_3="ingress-03.example.net"
export NODE_4="ingress-04.example.net"
export NODE_5="ingress-05.example.net"
export NODE_6="ingress-06.example.net"

# The version currently used by the ingress.
export CURRENT_SECRET_VERSION="<current-version>"

# The new certificate version to deploy.
export NEW_SECRET_VERSION="<new-version>"

# The version to use if rollback is required.
export PREVIOUS_SECRET_VERSION="$CURRENT_SECRET_VERSION"

# Path to a local copy of the new leaf certificate.
export NEW_CERT_FILE="/secure/path/new-certificate.pem"

# Optional: path to the CA bundle used to validate the internal certificate.
export CA_FILE="/secure/path/internal-ca-bundle.pem"
```

Record the following in the change or incident ticket:

- Start time.
- Operator.
- TLS hostname.
- Current secret version.
- New secret version.
- Previous secret version for rollback.
- Six node names or addresses.
- Certificate serial number and SHA-256 fingerprint.
- Planned maintenance or drain window.

---

## Safety checks before changing anything

Do not start the rotation if any of the following is true:

- The new certificate is not approved for the required hostname.
- The new certificate is already expired or expires within the planned rollout window.
- The private key does not match the new certificate.
- The certificate chain is incomplete.
- Fewer than four ingress nodes are healthy.
- The load balancer cannot drain a node.
- You cannot identify the current secret version and rollback version.

Confirm the current ingress health:

```text
Approved health-check command:
<health-check-command>
```

The expected result is six healthy nodes and no active incident affecting the ingress or its dependencies.

---

## 1. Check the currently deployed certificate

### 1.1 Check the certificate presented by each node

Run the following against each node. Use the production TLS hostname as the SNI value even when connecting directly to a node.

```bash
check_node_cert() {
  node="$1"

  echo "===== $node ====="
  openssl s_client \
    -connect "${node}:${TLS_PORT}" \
    -servername "${TLS_HOST}" \
    -showcerts \
    </dev/null 2>/dev/null |
    openssl x509 \
      -noout \
      -subject \
      -issuer \
      -serial \
      -dates \
      -fingerprint -sha256
}

check_node_cert "$NODE_1"
check_node_cert "$NODE_2"
check_node_cert "$NODE_3"
check_node_cert "$NODE_4"
check_node_cert "$NODE_5"
check_node_cert "$NODE_6"
```

Confirm that:

- All six nodes present the same certificate, or that any difference is understood.
- The `notAfter` date is approaching and justifies the rotation.
- The certificate subject and SAN contain the required hostname.
- The issuer is the expected internal or public CA.
- The current serial number and fingerprint are recorded.

### 1.2 Check the expiry programmatically

The following command exits with status `0` if the certificate remains valid for at least 30 days and status `1` otherwise:

```bash
openssl s_client \
  -connect "${NODE_1}:${TLS_PORT}" \
  -servername "${TLS_HOST}" \
  </dev/null 2>/dev/null |
  openssl x509 -checkend $((30 * 24 * 60 * 60)) -noout
```

Repeat against a second node if the nodes did not all present the same certificate.

### 1.3 Confirm the secret pointer

Use the approved secret-management command to determine which version is currently referenced:

```text
Approved command:
<secret-read-current-version-command>
```

Confirm that the result matches:

```text
CURRENT_SECRET_VERSION=<current-version>
```

Do not overwrite the previous version. It is required for rollback.

---

## 2. Validate the new certificate before staging

Validate the new certificate file:

```bash
openssl x509 \
  -in "$NEW_CERT_FILE" \
  -noout \
  -subject \
  -issuer \
  -serial \
  -dates \
  -fingerprint -sha256 \
  -ext subjectAltName
```

Confirm:

- The `notBefore` date has passed.
- The `notAfter` date is after the planned rotation window.
- `DNS:${TLS_HOST}` appears in the Subject Alternative Name list.
- The issuer is approved.
- The serial number and SHA-256 fingerprint match the certificate approved for deployment.

Check that the certificate and private key match. Obtain the key through the approved secret-management process; do not copy it into shell history or an unprotected temporary file.

For an RSA key:

```bash
openssl x509 -noout -modulus -in "$NEW_CERT_FILE" | openssl sha256
openssl rsa  -noout -modulus -in "<protected-new-private-key-file>" | openssl sha256
```

For an EC key:

```bash
openssl x509 -in "$NEW_CERT_FILE" -pubkey -noout |
  openssl pkey -pubin -outform DER |
  openssl sha256

openssl pkey -in "<protected-new-private-key-file>" -pubout |
  openssl pkey -pubin -outform DER |
  openssl sha256
```

The corresponding hashes must match.

If the certificate is delivered with intermediates, validate the chain using the approved CA bundle:

```bash
openssl verify \
  -CAfile "$CA_FILE" \
  "<new-certificate-chain-file>"
```

Do not continue until the certificate, key, hostname, validity period, and chain are verified.

---

## 3. Stage the new certificate on two nodes

The first two nodes are the canary group:

```text
Canary nodes: NODE_1 and NODE_2
```

Keep the other four nodes serving the current certificate while the canary nodes are tested.

### 3.1 Confirm the new secret version

Use the approved secret-management command to verify that the new version contains the intended certificate:

```text
Approved command:
<secret-read-version-command> --version "$NEW_SECRET_VERSION"
```

Compare its certificate fingerprint with the local validation result from Section 2.

Do not re-point the production secret alias yet unless that is how your ingress stages a version on an individual node. If the secret alias is global, use the platform's node-specific staging mechanism or follow the approved change method that prevents the remaining four nodes from loading the new version.

### 3.2 Stage the new secret on `NODE_1`

Use the approved node-specific staging command:

```text
Approved command:
<stage-secret-on-node-command> \
  --node "$NODE_1" \
  --secret-version "$NEW_SECRET_VERSION"
```

Confirm that the command reports success.

Drain `NODE_1` from the load balancer:

```text
Approved command:
<load-balancer-drain-command> "$NODE_1"
```

Wait until the node is drained or until the approved drain timeout expires. Check the node's active connection count if available:

```text
Approved command:
<active-connection-check-command> "$NODE_1"
```

Reload the ingress on `NODE_1`:

```text
Approved command:
<ingress-reload-command> "$NODE_1"
```

Expect existing connections to be dropped during this reload. Confirm that the node returns a healthy status:

```text
Approved command:
<node-health-check-command> "$NODE_1"
```

### 3.3 Verify `NODE_1` with `openssl s_client`

```bash
openssl s_client \
  -connect "${NODE_1}:${TLS_PORT}" \
  -servername "${TLS_HOST}" \
  -verify_return_error \
  -CAfile "$CA_FILE" \
  </dev/null
```

Review the output for:

- `Verify return code: 0 (ok)`.
- The new certificate's serial number.
- The new certificate's SHA-256 fingerprint.
- The expected Subject Alternative Name.
- A future `notAfter` date.

For a concise certificate summary:

```bash
openssl s_client \
  -connect "${NODE_1}:${TLS_PORT}" \
  -servername "${TLS_HOST}" \
  -showcerts \
  </dev/null 2>/dev/null |
  openssl x509 \
    -noout \
    -subject \
    -issuer \
    -serial \
    -dates \
    -fingerprint -sha256 \
    -ext subjectAltName
```

Re-add `NODE_1` to the load balancer only after:

- The TLS check succeeds.
- The ingress health check succeeds.
- The node is ready to accept traffic.

```text
Approved command:
<load-balancer-enable-command> "$NODE_1"
```

### 3.4 Stage and verify `NODE_2`

Repeat the same process for `NODE_2`:

1. Stage `NEW_SECRET_VERSION`.
2. Drain `NODE_2`.
3. Reload the ingress.
4. Confirm node health.
5. Verify the new certificate with `openssl s_client`.
6. Re-add the node to the load balancer.

```text
<stage-secret-on-node-command> \
  --node "$NODE_2" \
  --secret-version "$NEW_SECRET_VERSION"

<load-balancer-drain-command> "$NODE_2"

<ingress-reload-command> "$NODE_2"

<node-health-check-command> "$NODE_2"

<load-balancer-enable-command> "$NODE_2"
```

Verify:

```bash
for node in "$NODE_1" "$NODE_2"; do
  echo "===== $node ====="
  openssl s_client \
    -connect "${node}:${TLS_PORT}" \
    -servername "${TLS_HOST}" \
    -showcerts \
    </dev/null 2>/dev/null |
    openssl x509 \
      -noout \
      -subject \
      -issuer \
      -serial \
      -dates \
      -fingerprint -sha256
done
```

The two canary nodes must present the new certificate before continuing.

---

## 4. Observe the canary nodes

Observe the canary nodes for the approved observation period, or at least long enough to exercise representative internal traffic.

Check:

- TLS handshake failures.
- Ingress error rates.
- 4xx and 5xx rates.
- Upstream connection failures.
- Health-check failures.
- Application logs for certificate or trust errors.
- Load-balancer traffic distribution.
- Client reports of connection resets.

```text
Approved monitoring command or dashboard:
<monitoring-command-or-dashboard>
```

Continue only if both canary nodes are healthy and no certificate-related errors are present.

If either canary node fails, stop the rollout and follow the rollback procedure.

---

## 5. Roll the new certificate to the remaining four nodes

Roll the nodes one at a time:

```text
NODE_3 → NODE_4 → NODE_5 → NODE_6
```

Do not reload multiple nodes concurrently unless the ingress platform's approved procedure explicitly supports it. A reload drops open connections, so serial replacement limits the number of simultaneous disruptions and preserves capacity.

For each node:

### 5.1 Stage the new secret

```text
<stage-secret-on-node-command> \
  --node "<node>" \
  --secret-version "$NEW_SECRET_VERSION"
```

### 5.2 Drain the node

```text
<load-balancer-drain-command> "<node>"
```

Wait for the node to drain. Confirm that the remaining nodes are healthy before proceeding.

### 5.3 Reload the ingress

```text
<ingress-reload-command> "<node>"
```

Expect existing connections to be dropped.

### 5.4 Check node health

```text
<node-health-check-command> "<node>"
```

Do not re-add an unhealthy node to the load balancer.

### 5.5 Verify the certificate

```bash
openssl s_client \
  -connect "<node>:${TLS_PORT}" \
  -servername "${TLS_HOST}" \
  -verify_return_error \
  -CAfile "$CA_FILE" \
  </dev/null
```

Confirm:

- `Verify return code: 0 (ok)`.
- The serial number matches the new certificate.
- The SHA-256 fingerprint matches the new certificate.
- The SAN contains `TLS_HOST`.
- The certificate is not expired.

### 5.6 Re-add the node

```text
<load-balancer-enable-command> "<node>"
```

Confirm that the node is healthy and receiving traffic before moving to the next node.

Repeat Sections 5.1–5.6 for `NODE_3`, `NODE_4`, `NODE_5`, and `NODE_6`.

---

## 6. Verify all six nodes

After all six nodes have been rolled, verify each node directly:

```bash
for node in \
  "$NODE_1" "$NODE_2" "$NODE_3" \
  "$NODE_4" "$NODE_5" "$NODE_6"; do
  echo "===== $node ====="

  openssl s_client \
    -connect "${node}:${TLS_PORT}" \
    -servername "${TLS_HOST}" \
    -verify_return_error \
    -CAfile "$CA_FILE" \
    </dev/null 2>&1 |
    sed -n '/Certificate chain/,$p' |
    tail -n 20

  openssl s_client \
    -connect "${node}:${TLS_PORT}" \
    -servername "${TLS_HOST}" \
    -showcerts \
    </dev/null 2>/dev/null |
    openssl x509 \
      -noout \
      -subject \
      -issuer \
      -serial \
      -dates \
      -fingerprint -sha256
done
```

All six nodes must:

- Be healthy in the load balancer.
- Present the new certificate.
- Pass certificate-chain validation.
- Present the expected hostname in the SAN.
- Have the expected new expiry date.
- Have no abnormal TLS or upstream error rate.

Also test through the normal ingress name:

```bash
openssl s_client \
  -connect "${TLS_HOST}:${TLS_PORT}" \
  -servername "${TLS_HOST}" \
  -verify_return_error \
  -CAfile "$CA_FILE" \
  </dev/null
```

If the ingress supports an application health endpoint, test it through the normal hostname:

```bash
curl --fail --show-error --silent \
  --cacert "$CA_FILE" \
  "https://${TLS_HOST}/<health-endpoint>"
```

---

## 7. Re-point the secret after the rollout

If the platform uses a shared secret alias or pointer, update it to the new version after the node-by-node rollout is complete:

```text
<secret-repoint-command> \
  --secret "<ingress-tls-secret>" \
  --version "$NEW_SECRET_VERSION"
```

Confirm the pointer:

```text
<secret-read-current-version-command>
```

The result must be:

```text
NEW_SECRET_VERSION=<new-version>
```

Do not delete or revoke the previous version yet. Retain it for the approved rollback period.

If the platform requires nodes to reload after the shared pointer changes, confirm whether the node-specific staging already performed that reload. Reload only nodes that still need to fetch the new pointer, using the same drain, reload, health-check, and verification sequence.

---

## Rollback procedure

Use rollback if any node fails health checks, presents the wrong certificate, produces certificate-chain errors, or causes unacceptable traffic or application failures.

Rollback means re-pointing the TLS secret to the previous version and reloading affected nodes.

### Rollback principles

- Stop the forward rollout immediately.
- Do not delete the new secret version.
- Preserve the previous secret version.
- Drain before every reload because reloads drop open connections.
- Roll back the canary or affected nodes first.
- If all six nodes have been changed, roll back all six nodes.

### 1. Stop and assess

Record:

- Which nodes have the new certificate.
- Which nodes are healthy.
- The observed error or failure.
- Whether the issue affects only the new certificate or the ingress configuration generally.

Keep enough healthy nodes serving traffic to maintain capacity. If necessary, leave failed nodes drained while rollback proceeds.

### 2. Re-point the secret to the previous version

```text
<secret-repoint-command> \
  --secret "<ingress-tls-secret>" \
  --version "$PREVIOUS_SECRET_VERSION"
```

Verify the pointer:

```text
<secret-read-current-version-command>
```

It must report:

```text
PREVIOUS_SECRET_VERSION=<previous-version>
```

### 3. Roll back each affected node

For every node that loaded the new certificate:

```text
<load-balancer-drain-command> "<node>"

<ingress-reload-command> "<node>"

<node-health-check-command> "<node>"
```

After the node is healthy, verify that it presents the previous certificate:

```bash
openssl s_client \
  -connect "<node>:${TLS_PORT}" \
  -servername "${TLS_HOST}" \
  -verify_return_error \
  -CAfile "$CA_FILE" \
  </dev/null
```

Confirm the serial number and fingerprint match the recorded previous certificate.

Re-add the node only after verification succeeds:

```text
<load-balancer-enable-command> "<node>"
```

Roll back one node at a time. If the previous certificate is known to be healthy, the affected nodes may be rolled back in the order needed to restore capacity, but do not reload multiple nodes simultaneously unless explicitly approved.

### 4. Verify the rollback

Check every node that was affected:

```bash
for node in "<affected-node-1>" "<affected-node-2>"; do
  echo "===== $node ====="
  openssl s_client \
    -connect "${node}:${TLS_PORT}" \
    -servername "${TLS_HOST}" \
    -showcerts \
    </dev/null 2>/dev/null |
    openssl x509 \
      -noout \
      -subject \
      -issuer \
      -serial \
      -dates \
      -fingerprint -sha256
done
```

Confirm:

- The previous certificate is presented.
- Certificate validation succeeds.
- The node is healthy.
- The load balancer has restored the expected capacity.
- TLS and application error rates have returned to normal.

---

## Troubleshooting

### `openssl s_client` shows the old certificate

Possible causes:

- The node was not reloaded.
- The node loaded a cached secret.
- The secret was staged on the wrong node.
- The SNI hostname was omitted or incorrect.
- The load balancer or proxy in front of the node is terminating TLS.

Check the node directly by address and include:

```bash
-servername "$TLS_HOST"
```

Confirm the node's configured secret version and reload status.

### Certificate validation fails

Check:

- The internal CA bundle passed with `-CAfile`.
- The intermediate certificates are installed and served.
- The certificate SAN contains the requested hostname.
- The node is serving the complete certificate chain.
- The certificate was not issued by an untrusted or unexpected CA.

### The node is unhealthy after reload

Keep it drained. Check:

- Ingress logs.
- Secret retrieval logs.
- Private-key permissions.
- Certificate and key matching.
- Ingress configuration syntax.
- Port binding and process status.
- Health-check output.

Do not re-add the node until it passes the normal health checks.

### Traffic or connections fail during the rollout

Confirm that the node was drained before reload. Because reloads drop open connections, clients may need to retry. If failures exceed the approved threshold:

1. Stop the rollout.
2. Keep the affected node drained.
3. Roll it back using the procedure above.
4. Escalate if the previous certificate also fails.

---

## Completion checklist

- [ ] The original certificate expiry was recorded.
- [ ] The new certificate hostname, chain, key, and expiry were validated.
- [ ] The current and previous secret versions were recorded.
- [ ] `NODE_1` was staged, drained, reloaded, verified, and restored.
- [ ] `NODE_2` was staged, drained, reloaded, verified, and restored.
- [ ] Canary nodes were observed without certificate-related errors.
- [ ] `NODE_3` through `NODE_6` were rolled one at a time.
- [ ] All six nodes present the new certificate.
- [ ] All six nodes pass `openssl s_client` verification.
- [ ] The normal ingress hostname passes TLS and application health checks.
- [ ] The secret pointer references the new version.
- [ ] The previous secret version remains available for the rollback period.
- [ ] The change record includes fingerprints, timestamps, node results, and any connection impact.
