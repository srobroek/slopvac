# Runbook: Rotate an Expiring TLS Certificate on a Six-Node Internal Ingress

## Purpose

Rotate an expiring TLS certificate across six ingress nodes using a two-node canary rollout, followed by the remaining four nodes.

## Impact and safety rules

- Reloading an ingress node terminates its open connections.
- Drain and reload only one node at a time.
- Wait for a reloaded node to become healthy before proceeding.
- Keep the previous secret version available until the rollout has been verified.
- Do not log, print, copy, or store the private key outside the approved secret-management system.
- Stop and roll back if TLS verification fails or ingress errors increase.

## Variables

Record these values before starting:

```text
HOSTNAME=<TLS hostname, such as service.internal.example.com>
PORT=443
CA_FILE=<path to the internal CA bundle>
HEALTH_PATH=<known ingress health or application path>

NODE_1=<node name and IP>
NODE_2=<node name and IP>
NODE_3=<node name and IP>
NODE_4=<node name and IP>
NODE_5=<node name and IP>
NODE_6=<node name and IP>

PREVIOUS_SECRET_VERSION=<currently active version>
NEW_SECRET_VERSION=<new immutable version>
EXPECTED_NEW_SERIAL=<new leaf certificate serial number>
EXPECTED_NEW_FINGERPRINT=<new leaf certificate SHA-256 fingerprint>
```

Use the node IP as the `-connect` target while retaining `$HOSTNAME` as the SNI and certificate hostname.

## Success criteria

The rotation is complete when:

- All six nodes serve the new certificate.
- The certificate serial number or SHA-256 fingerprint matches the new certificate.
- The certificate is valid for `$HOSTNAME`.
- The chain verifies against the internal CA.
- `openssl s_client` reports `Verify return code: 0 (ok)` on every node.
- All six nodes are serving traffic.
- TLS handshake, connection, and HTTP error metrics remain normal.
- The active secret reference points to `$NEW_SECRET_VERSION`.

## Pre-change checks

### 1. Confirm capacity and change readiness

Verify that:

- The other five nodes can handle traffic while one node is drained.
- There are no concurrent ingress deployments, node replacements, or autoscaling events.
- You can target secret versions and reload nodes individually.
- Changing the secret reference will not unexpectedly reload all six nodes.
- `$PREVIOUS_SECRET_VERSION` is known, retained, and still valid.
- You have access to ingress traffic, connection, TLS, and error metrics.

Do not proceed if individual nodes cannot be drained and reloaded safely.

### 2. Check the certificate currently served by the ingress

Check the load-balanced ingress endpoint:

```bash
openssl s_client \
  -connect "${HOSTNAME}:${PORT}" \
  -servername "$HOSTNAME" \
  -showcerts \
  </dev/null 2>/dev/null |
openssl x509 -noout \
  -subject \
  -issuer \
  -serial \
  -startdate \
  -enddate \
  -fingerprint -sha256
```

Record the current serial number, fingerprint, and expiration date.

### 3. Check all six nodes individually

Run the following for each node IP:

```bash
openssl s_client \
  -connect "<NODE_IP>:${PORT}" \
  -servername "$HOSTNAME" \
  -showcerts \
  </dev/null 2>/dev/null |
openssl x509 -noout \
  -subject \
  -issuer \
  -serial \
  -startdate \
  -enddate \
  -fingerprint -sha256
```

Confirm that all nodes initially serve the expected old certificate. Investigate any node that already serves a different certificate before continuing.

### 4. Validate the new certificate

Inspect the new leaf certificate through the approved secret-management workflow:

```bash
openssl x509 -in tls.crt -noout \
  -subject \
  -issuer \
  -serial \
  -startdate \
  -enddate \
  -ext subjectAltName \
  -fingerprint -sha256
```

Confirm that:

- The certificate is currently valid.
- The expiration date matches the expected renewal period.
- `$HOSTNAME` appears in the Subject Alternative Name extension.
- The issuer is the expected internal CA.
- The secret contains the required intermediate certificates.
- The certificate and private key match.

If the files are available through an approved secure workspace, compare their public keys:

```bash
openssl x509 -in tls.crt -pubkey -noout |
openssl pkey -pubin -outform DER |
openssl dgst -sha256

openssl pkey -in tls.key -pubout -outform DER |
openssl dgst -sha256
```

The two hashes must match. Do not display or copy the private key itself.

Record the new certificate serial number and SHA-256 fingerprint.

### 5. Establish the monitoring baseline

Record normal values for:

- Active connections by node
- TLS handshake failures
- Connection resets
- HTTP 5xx responses
- Request latency
- Ingress health-check failures

## Rollout

### Node tracking

| Node | Drained | New version loaded | TLS verified | Traffic restored |
|---|---:|---:|---:|---:|
| Node 1 | [ ] | [ ] | [ ] | [ ] |
| Node 2 | [ ] | [ ] | [ ] | [ ] |
| Node 3 | [ ] | [ ] | [ ] | [ ] |
| Node 4 | [ ] | [ ] | [ ] | [ ] |
| Node 5 | [ ] | [ ] | [ ] | [ ] |
| Node 6 | [ ] | [ ] | [ ] | [ ] |

### 1. Stage the new secret version

Create or publish `$NEW_SECRET_VERSION` using the approved secret-management system.

- Keep `$PREVIOUS_SECRET_VERSION`.
- Do not overwrite the previous version.
- Do not move the fleet-wide secret reference yet if the platform supports canary-specific version selection.
- Make the new version available to Nodes 1 and 2 only through the approved deployment mechanism.

### 2. Rotate canary Node 1

1. Remove Node 1 from load balancing.
2. Confirm that new connections are no longer routed to it.
3. Wait for active connections to drain according to the approved drain timeout.
4. Record any connections that remain. Reloading will terminate them.
5. Configure Node 1 to read `$NEW_SECRET_VERSION`.
6. Reload Node 1.
7. Wait for its local readiness and health checks to pass.
8. Verify the certificate directly:

   ```bash
   openssl s_client \
     -connect "<NODE_1_IP>:${PORT}" \
     -servername "$HOSTNAME" \
     -verify_hostname "$HOSTNAME" \
     -verify_return_error \
     -CAfile "$CA_FILE" \
     </dev/null
   ```

9. Confirm that the output includes:

   ```text
   Verification: OK
   Verify return code: 0 (ok)
   ```

10. Confirm the served certificate metadata:

    ```bash
    openssl s_client \
      -connect "<NODE_1_IP>:${PORT}" \
      -servername "$HOSTNAME" \
      -showcerts \
      </dev/null 2>/dev/null |
    openssl x509 -noout \
      -serial \
      -startdate \
      -enddate \
      -fingerprint -sha256
    ```

11. Verify that the serial number or fingerprint matches the new certificate.
12. If a health path is available, test it directly:

    ```bash
    curl --fail --show-error --silent \
      --cacert "$CA_FILE" \
      --resolve "${HOSTNAME}:${PORT}:<NODE_1_IP>" \
      "https://${HOSTNAME}:${PORT}${HEALTH_PATH}"
    ```

13. Return Node 1 to load balancing.
14. Confirm that it receives traffic without increased TLS, connection, or HTTP errors.

Do not continue if any check fails.

### 3. Rotate canary Node 2

Repeat the Node 1 procedure for Node 2:

1. Drain Node 2.
2. Wait for connections to drain.
3. Configure it to read `$NEW_SECRET_VERSION`.
4. Reload it.
5. Verify TLS with `openssl s_client`.
6. Confirm the new serial number or fingerprint.
7. Run the direct health check.
8. Return it to load balancing.
9. Confirm healthy traffic and metrics.

Do not drain Node 2 until Node 1 is healthy and serving traffic.

### 4. Observe the canaries

Observe Nodes 1 and 2 for the approved canary interval.

Confirm that:

- Both nodes continue to serve the new certificate.
- TLS handshake failures remain at baseline.
- Connection resets are not elevated after the reloads.
- HTTP 5xx responses and latency remain normal.
- Health checks remain successful.
- Both nodes are receiving traffic.

If any condition fails, stop and follow the rollback procedure.

### 5. Move the ingress secret reference

After the canaries pass, re-point the ingress secret reference from `$PREVIOUS_SECRET_VERSION` to `$NEW_SECRET_VERSION`.

Confirm that this action does not reload multiple nodes simultaneously. Nodes 3 through 6 should continue serving the old in-memory certificate until each is deliberately drained and reloaded.

### 6. Rotate Nodes 3 through 6

Rotate Nodes 3, 4, 5, and 6 one at a time.

For each node:

1. Confirm all previously rotated nodes are healthy.
2. Drain the node from load balancing.
3. Wait for active connections to drain.
4. Reload the node so it reads `$NEW_SECRET_VERSION`.
5. Wait for readiness and health checks.
6. Run `openssl s_client` against the node IP with `$HOSTNAME` as SNI.
7. Confirm `Verify return code: 0 (ok)`.
8. Confirm the new serial number or SHA-256 fingerprint.
9. Run the direct health check.
10. Return the node to load balancing.
11. Confirm normal traffic and metrics before proceeding.

Never reload two nodes concurrently.

## Final verification

### 1. Verify every node

Run the TLS verification against each node:

```bash
openssl s_client \
  -connect "<NODE_IP>:${PORT}" \
  -servername "$HOSTNAME" \
  -verify_hostname "$HOSTNAME" \
  -verify_return_error \
  -CAfile "$CA_FILE" \
  </dev/null
```

Then confirm the certificate identity:

```bash
openssl s_client \
  -connect "<NODE_IP>:${PORT}" \
  -servername "$HOSTNAME" \
  -showcerts \
  </dev/null 2>/dev/null |
openssl x509 -noout \
  -serial \
  -enddate \
  -fingerprint -sha256
```

All six nodes must report the same new serial number or fingerprint.

### 2. Verify the load-balanced endpoint

```bash
openssl s_client \
  -connect "${HOSTNAME}:${PORT}" \
  -servername "$HOSTNAME" \
  -verify_hostname "$HOSTNAME" \
  -verify_return_error \
  -CAfile "$CA_FILE" \
  </dev/null
```

Repeat this check enough times to exercise multiple backend nodes if the load balancer distributes new TCP connections.

### 3. Complete the change record

Record:

- Previous and new secret versions
- Old and new certificate fingerprints
- New expiration date
- Nodes rotated
- Start and completion times
- Number of connections terminated during each reload
- Verification results
- Any errors or unusual metrics

Retain `$PREVIOUS_SECRET_VERSION` according to the rollback and secret-retention policy.

## Rollback

### Rollback triggers

Roll back if any of the following occurs:

- `openssl s_client` reports a nonzero verification result.
- The certificate does not cover `$HOSTNAME`.
- A node serves the wrong certificate or an incomplete chain.
- TLS handshake failures, connection resets, or HTTP 5xx responses increase materially.
- A reloaded node fails readiness or health checks.
- The two canary nodes behave differently.
- Traffic capacity becomes unsafe.

### Rollback procedure

1. Stop the rollout. Do not reload additional nodes.
2. Keep healthy nodes in service.
3. Re-point the ingress secret reference from `$NEW_SECRET_VERSION` to `$PREVIOUS_SECRET_VERSION`.
4. Identify every node that has loaded the new certificate.
5. Roll back those nodes one at a time, preferably in reverse rollout order:
   1. Drain the node.
   2. Wait for active connections to drain.
   3. Reload the node so it reads `$PREVIOUS_SECRET_VERSION`.
   4. Verify it serves the previous certificate.
   5. Confirm TLS verification succeeds.
   6. Return it to load balancing.
   7. Confirm normal traffic and metrics.
6. Verify that all six nodes serve the previous certificate:

   ```bash
   openssl s_client \
     -connect "<NODE_IP>:${PORT}" \
     -servername "$HOSTNAME" \
     -verify_hostname "$HOSTNAME" \
     -verify_return_error \
     -CAfile "$CA_FILE" \
     </dev/null
   ```

7. Confirm that the active secret reference is `$PREVIOUS_SECRET_VERSION`.
8. Continue monitoring until TLS, connection, and HTTP metrics return to baseline.

Re-pointing the secret does not necessarily change the certificate already held in a node's memory. Unless the platform performs an automatic reload, every node that loaded the new version must be drained and reloaded to complete the rollback.
