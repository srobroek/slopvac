# Runbook: Rotate an Internal Ingress TLS Certificate

## Purpose

Rotate an expiring TLS certificate across a six-node internal ingress. Deploy to two canary nodes first, verify the certificate, and then roll through the remaining four nodes.

## Impact

Reloading an ingress node drops all open connections on that node.

Reload one node at a time. Wait for the node to become healthy before proceeding. Clients must reconnect; long-lived requests, streams, and WebSocket connections may be interrupted.

## Prerequisites

You need:

- Access to the certificate and secret-management systems.
- Permission to update the ingress secret version and reload nodes.
- The ingress hostname.
- The names or IP addresses of all six ingress nodes.
- The new certificate, private key, and intermediate certificate chain.
- The current secret version, retained for rollback.
- A maintenance window or approval appropriate for connection interruption.
- At least one other healthy node serving traffic whenever a node reloads.

Set these placeholders for use in the commands:

```sh
export INGRESS_HOST="<internal-ingress-hostname>"
export INGRESS_PORT="443"

export NODE_1="<node-1-ip-or-name>"
export NODE_2="<node-2-ip-or-name>"
export NODE_3="<node-3-ip-or-name>"
export NODE_4="<node-4-ip-or-name>"
export NODE_5="<node-5-ip-or-name>"
export NODE_6="<node-6-ip-or-name>"

export NEW_CERT="<path-to-new-certificate.pem>"
export NEW_KEY="<path-to-new-private-key.pem>"
export NEW_CHAIN="<path-to-intermediate-chain.pem>"

export PREVIOUS_SECRET_VERSION="<current-secret-version>"
export NEW_SECRET_VERSION="<new-secret-version>"
```

Replace the secret-management, health-check, and reload placeholders below with the commands used by your environment.

## Procedure

### 1. Record the current state

Record:

- Rotation start time.
- Engineer performing the rotation.
- Ingress hostname.
- Current secret version.
- New secret version.
- Certificate serial numbers and expiry dates.
- Node order.
- Relevant incident, maintenance, or change identifier.

Confirm that all six nodes are healthy before making changes:

```sh
<check-ingress-cluster-health>
```

Stop if any node is unhealthy or if the cluster cannot tolerate taking one node out of service.

### 2. Check the currently served certificate

Check the certificate through the normal ingress endpoint:

```sh
openssl s_client \
  -connect "${INGRESS_HOST}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  </dev/null 2>/dev/null |
openssl x509 -noout -subject -issuer -serial -dates
```

Confirm the `notAfter` value is the expected expiring date.

Check whether the certificate expires within the next 30 days:

```sh
openssl s_client \
  -connect "${INGRESS_HOST}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  </dev/null 2>/dev/null |
openssl x509 -checkend 2592000 -noout
```

Exit status `0` means the certificate remains valid for at least 30 days. Exit status `1` means it expires within 30 days.

### 3. Validate the new certificate before deployment

Inspect the new certificate:

```sh
openssl x509 \
  -in "${NEW_CERT}" \
  -noout -subject -issuer -serial -dates -ext subjectAltName
```

Confirm that:

- `notBefore` is not in the future.
- `notAfter` is later than the current certificate's expiry.
- The Subject Alternative Name list contains `${INGRESS_HOST}`.
- The issuer is expected.
- The serial number differs from the certificate currently served.

Verify that the certificate matches the private key:

```sh
cert_pubkey="$(
  openssl x509 -in "${NEW_CERT}" -pubkey -noout |
  openssl pkey -pubin -outform DER 2>/dev/null |
  openssl dgst -sha256
)"

key_pubkey="$(
  openssl pkey -in "${NEW_KEY}" -pubout -outform DER 2>/dev/null |
  openssl dgst -sha256
)"

printf 'Certificate: %s\nPrivate key: %s\n' \
  "${cert_pubkey}" "${key_pubkey}"

test "${cert_pubkey}" = "${key_pubkey}"
```

The final command must exit successfully.

Verify the chain using the trust bundle appropriate for your internal certificate authority:

```sh
openssl verify \
  -CAfile "<internal-root-ca-bundle.pem>" \
  -untrusted "${NEW_CHAIN}" \
  "${NEW_CERT}"
```

Expected result:

```text
<path-to-new-certificate.pem>: OK
```

Do not deploy if any validation fails.

### 4. Create the new secret version

Create a new immutable secret version containing:

- The new leaf certificate.
- The required intermediate chain.
- The matching private key.

Do not overwrite or delete the previous version.

```sh
<create-secret-version \
  --certificate "${NEW_CERT}" \
  --chain "${NEW_CHAIN}" \
  --private-key "${NEW_KEY}" \
  --version "${NEW_SECRET_VERSION}">
```

Verify that both versions are available:

```sh
<describe-secret-version "${PREVIOUS_SECRET_VERSION}">
<describe-secret-version "${NEW_SECRET_VERSION}">
```

Record the exact identifiers. Rollback depends on the previous version remaining available.

### 5. Stage the certificate to the first canary node

Perform these steps on `NODE_1`:

1. Remove the node from service or mark it unavailable in the load balancer.
2. Wait for the node to stop receiving new connections.
3. Point the node's certificate secret reference to `${NEW_SECRET_VERSION}`.
4. Reload the ingress process.
5. Wait for the process and node health checks to pass.
6. Return the node to service.

```sh
<remove-node-from-service "${NODE_1}">
<wait-until-node-is-drained "${NODE_1}">

<point-node-secret \
  "${NODE_1}" \
  "${NEW_SECRET_VERSION}">

<reload-ingress-node "${NODE_1}">

<wait-for-node-health "${NODE_1}">
<return-node-to-service "${NODE_1}">
```

The reload drops any open connections that remain on the node.

Stop and roll back `NODE_1` if:

- The reload fails.
- The node does not become healthy.
- The certificate cannot be retrieved.
- The served serial number or expiry is wrong.
- Hostname or chain verification fails.

### 6. Verify the first canary node

Connect directly to `NODE_1` while sending the ingress hostname through Server Name Indication:

```sh
openssl s_client \
  -connect "${NODE_1}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  -showcerts \
  -verify_return_error \
  </dev/null
```

The command must complete without a verification error when the internal CA is trusted by the local system. If it is not in the system trust store, specify the CA bundle:

```sh
openssl s_client \
  -connect "${NODE_1}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  -CAfile "<internal-root-ca-bundle.pem>" \
  -verify_hostname "${INGRESS_HOST}" \
  -verify_return_error \
  </dev/null
```

Expected output includes:

```text
Verify return code: 0 (ok)
```

Inspect the served leaf certificate:

```sh
openssl s_client \
  -connect "${NODE_1}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  </dev/null 2>/dev/null |
openssl x509 -noout -subject -issuer -serial -dates -ext subjectAltName
```

Confirm that:

- The serial number matches the new certificate.
- The expiry matches the new certificate.
- `${INGRESS_HOST}` appears in the Subject Alternative Name list.
- The issuer and chain are expected.

Send an application-level request directly to the node if the ingress exposes a health endpoint:

```sh
curl \
  --resolve "${INGRESS_HOST}:${INGRESS_PORT}:${NODE_1}" \
  --cacert "<internal-root-ca-bundle.pem>" \
  "https://${INGRESS_HOST}:${INGRESS_PORT}/<health-path>"
```

Confirm the expected status and response.

### 7. Stage and verify the second canary node

Repeat the drain, secret update, reload, health check, and return-to-service sequence for `NODE_2`:

```sh
<remove-node-from-service "${NODE_2}">
<wait-until-node-is-drained "${NODE_2}">

<point-node-secret \
  "${NODE_2}" \
  "${NEW_SECRET_VERSION}">

<reload-ingress-node "${NODE_2}">

<wait-for-node-health "${NODE_2}">
<return-node-to-service "${NODE_2}">
```

Verify `NODE_2` independently:

```sh
openssl s_client \
  -connect "${NODE_2}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  -CAfile "<internal-root-ca-bundle.pem>" \
  -verify_hostname "${INGRESS_HOST}" \
  -verify_return_error \
  </dev/null
```

Inspect the certificate:

```sh
openssl s_client \
  -connect "${NODE_2}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  </dev/null 2>/dev/null |
openssl x509 -noout -subject -issuer -serial -dates -ext subjectAltName
```

Confirm both canary nodes are healthy and serving the new certificate. Check ingress error rates, TLS handshake failures, latency, and connection resets before continuing.

Pause the rollout and investigate if metrics regress.

### 8. Roll out to the remaining four nodes

Update `NODE_3` through `NODE_6` one at a time. Do not reload nodes in parallel.

For each node:

1. Confirm the other five nodes are healthy.
2. Remove the node from service.
3. Wait for it to stop receiving new connections.
4. Point its secret reference to `${NEW_SECRET_VERSION}`.
5. Reload the ingress.
6. Wait for health checks to pass.
7. Verify the certificate directly with `openssl s_client`.
8. Return the node to service.
9. Check cluster health and service metrics before continuing.

Use this sequence for each node:

```sh
for node in \
  "${NODE_3}" \
  "${NODE_4}" \
  "${NODE_5}" \
  "${NODE_6}"
do
  printf 'Rotating %s\n' "${node}"

  <check-ingress-cluster-health>
  <remove-node-from-service "${node}">
  <wait-until-node-is-drained "${node}">

  <point-node-secret \
    "${node}" \
    "${NEW_SECRET_VERSION}">

  <reload-ingress-node "${node}">
  <wait-for-node-health "${node}">

  openssl s_client \
    -connect "${node}:${INGRESS_PORT}" \
    -servername "${INGRESS_HOST}" \
    -CAfile "<internal-root-ca-bundle.pem>" \
    -verify_hostname "${INGRESS_HOST}" \
    -verify_return_error \
    </dev/null

  <return-node-to-service "${node}">
  <check-ingress-cluster-health>
done
```

If the environment's placeholder commands cannot be used inside a shell loop, execute the sequence manually for each node.

Stop immediately if any node fails verification. Do not proceed to the next node.

### 9. Verify the completed rotation

Inspect all six nodes directly:

```sh
for node in \
  "${NODE_1}" \
  "${NODE_2}" \
  "${NODE_3}" \
  "${NODE_4}" \
  "${NODE_5}" \
  "${NODE_6}"
do
  printf '\n=== %s ===\n' "${node}"

  openssl s_client \
    -connect "${node}:${INGRESS_PORT}" \
    -servername "${INGRESS_HOST}" \
    </dev/null 2>/dev/null |
  openssl x509 -noout -serial -dates
done
```

All nodes must report the new serial number and expiry date.

Verify hostname and chain validation on each node:

```sh
for node in \
  "${NODE_1}" \
  "${NODE_2}" \
  "${NODE_3}" \
  "${NODE_4}" \
  "${NODE_5}" \
  "${NODE_6}"
do
  openssl s_client \
    -connect "${node}:${INGRESS_PORT}" \
    -servername "${INGRESS_HOST}" \
    -CAfile "<internal-root-ca-bundle.pem>" \
    -verify_hostname "${INGRESS_HOST}" \
    -verify_return_error \
    </dev/null |
  grep 'Verify return code'
done
```

Each node must report:

```text
Verify return code: 0 (ok)
```

Finally, verify through the normal ingress endpoint:

```sh
openssl s_client \
  -connect "${INGRESS_HOST}:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  -CAfile "<internal-root-ca-bundle.pem>" \
  -verify_hostname "${INGRESS_HOST}" \
  -verify_return_error \
  </dev/null
```

Monitor the following after completion:

- Node and cluster health.
- TLS handshake failures.
- Ingress error rate.
- Upstream error rate.
- Connection resets.
- Request latency.
- Client or service alerts.

## Rollback

Rollback by re-pointing each affected node to `${PREVIOUS_SECRET_VERSION}` and reloading it.

A rollback reload also drops the node's open connections. Roll back one node at a time.

### Roll back a node

For each affected node:

```sh
<remove-node-from-service "<node>">
<wait-until-node-is-drained "<node>">

<point-node-secret \
  "<node>" \
  "${PREVIOUS_SECRET_VERSION}">

<reload-ingress-node "<node>">

<wait-for-node-health "<node>">
<return-node-to-service "<node>">
```

Verify that the node serves the previous certificate:

```sh
openssl s_client \
  -connect "<node>:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  -CAfile "<internal-root-ca-bundle.pem>" \
  -verify_hostname "${INGRESS_HOST}" \
  -verify_return_error \
  </dev/null
```

Inspect the serial number and dates:

```sh
openssl s_client \
  -connect "<node>:${INGRESS_PORT}" \
  -servername "${INGRESS_HOST}" \
  </dev/null 2>/dev/null |
openssl x509 -noout -subject -issuer -serial -dates
```

Confirm that the serial number matches `${PREVIOUS_SECRET_VERSION}` and that verification succeeds.

### Rollback order

- If a canary fails, roll back only the affected canary nodes.
- If a failure appears after the broader rollout begins, stop the rollout and roll back every node using `${NEW_SECRET_VERSION}`.
- Keep unaffected nodes on the previous version until the cause is understood.
- Continue one node at a time, checking cluster health after each reload.

Escalate if the previous version also fails, is unavailable, or expires before the issue can be resolved.

## Completion Checklist

- [ ] New certificate, key, and chain were validated before deployment.
- [ ] Previous secret version was recorded and retained.
- [ ] Two canary nodes were updated and verified first.
- [ ] Remaining four nodes were updated one at a time.
- [ ] All six nodes serve the new certificate serial number.
- [ ] All six nodes report the expected expiry date.
- [ ] Hostname and chain verification succeed on every node.
- [ ] Verification through the normal ingress endpoint succeeds.
- [ ] Cluster health and service metrics are normal.
- [ ] Change record contains timestamps, versions, results, and any observed connection impact.
- [ ] Previous secret version remains available for the required rollback period.
