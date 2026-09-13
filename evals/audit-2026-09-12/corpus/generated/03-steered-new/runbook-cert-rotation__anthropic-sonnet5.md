# Runbook: Rotate an Expiring TLS Certificate on the Internal Ingress

## Scope

This runbook applies to the internal ingress cluster with six nodes. It covers checking certificate expiry, staging a new certificate to two nodes, verifying the staged certificate, rolling the certificate to the remaining four nodes, and rolling back by re-pointing the secret to the previous version.

## Before you start

- Reloading a node drops its open connections. Roll nodes one at a time to limit impact.
- Identify the six node names or addresses before you begin. This runbook refers to them as `node-1` through `node-6`.
- Confirm you hold the new certificate and key, and that the previous certificate version is still available in the secret store for rollback.

## Step 1: Check the certificate expiry

1. Run `openssl s_client -connect <ingress-host>:443 -servername <ingress-host> </dev/null 2>/dev/null | openssl x509 -noout -dates` against the ingress virtual IP.
2. Read the `notAfter` field from the output.
3. If `notAfter` is more than 7 days away, stop. Escalate per your team's severity policy instead of rotating early.
4. If `notAfter` is 7 days away or less, proceed to Step 2.

## Step 2: Stage the new certificate to two nodes

1. Pick two nodes, for example `node-1` and `node-2`. Leave the other four nodes on the current certificate.
2. Update the TLS secret on `node-1` to point to the new certificate version.
3. Reload `node-1`. This drops `node-1`'s open connections.
4. Update the TLS secret on `node-2` to point to the new certificate version.
5. Reload `node-2`. This drops `node-2`'s open connections.

## Step 3: Verify the staged certificate

1. Run `openssl s_client -connect node-1:443 -servername <ingress-host> </dev/null 2>/dev/null | openssl x509 -noout -dates -subject -issuer` against `node-1` directly.
2. Confirm the `notAfter` date matches the new certificate's expiry.
3. Confirm the `subject` and `issuer` fields match the new certificate.
4. Repeat steps 1–3 against `node-2`.
5. If either node fails verification, go to the Rollback section for that node before proceeding.
6. If both nodes pass verification, proceed to Step 4.

## Step 4: Roll the certificate to the remaining four nodes

Roll one node at a time. Reloading a node drops its open connections, so rolling nodes serially limits the connection loss to one node at a time.

For each of `node-3`, `node-4`, `node-5`, `node-6`, in order:

1. Update the TLS secret on the node to point to the new certificate version.
2. Reload the node. This drops the node's open connections.
3. Run `openssl s_client -connect <node>:443 -servername <ingress-host> </dev/null 2>/dev/null | openssl x509 -noout -dates` against the node.
4. Confirm the `notAfter` date matches the new certificate's expiry.
5. If verification fails, go to the Rollback section for that node before continuing to the next node.
6. If verification passes, proceed to the next node in the list.

## Step 5: Confirm the rotation

1. Run `openssl s_client -connect <ingress-host>:443 -servername <ingress-host> </dev/null 2>/dev/null | openssl x509 -noout -dates` against the ingress virtual IP.
2. Confirm the `notAfter` date matches the new certificate's expiry.
3. Record the completion time and the new certificate's expiry date in your team's incident or change log.

## Rollback

Roll back a node if it fails verification in Step 3 or Step 4, or if you observe TLS handshake failures on a node after reload.

1. Update the TLS secret on the affected node to point to the previous certificate version.
2. Reload the node. This drops the node's open connections.
3. Run `openssl s_client -connect <node>:443 -servername <ingress-host> </dev/null 2>/dev/null | openssl x509 -noout -dates` against the node.
4. Confirm the `notAfter` date matches the previous certificate's expiry.
5. Stop rolling forward to additional nodes until you identify the cause of the failure.
6. Escalate per your team's severity policy.
