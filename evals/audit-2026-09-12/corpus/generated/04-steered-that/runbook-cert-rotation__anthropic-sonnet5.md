# Runbook: Rotate an Expiring TLS Certificate on the Ingress Fleet

## Scope

This runbook rotates the TLS certificate served by the internal ingress fleet of six nodes: `ingress-01` through `ingress-06`. It covers checking the expiry, staging the new certificate to two canary nodes, verifying the staged certificate with `openssl s_client`, rolling to the remaining four nodes, and rolling back by re-pointing the secret to the previous version.

## Prerequisites

Confirm the following before starting.

- You have Vault access with write permission on `secret/data/ingress/tls-cert`.
- You have SSH access to `ingress-01` through `ingress-06`.
- You have the new certificate and key files, and their SHA-256 fingerprints.
- You have the ingress error-rate dashboard open in a second window.

## Node inventory

| Node | Role during rotation |
|---|---|
| `ingress-01` | Canary |
| `ingress-02` | Canary |
| `ingress-03` | Remaining fleet |
| `ingress-04` | Remaining fleet |
| `ingress-05` | Remaining fleet |
| `ingress-06` | Remaining fleet |

## Step 1: Check the certificate expiry

1. Query the live certificate on any node:
   ```
   openssl s_client -connect ingress-01.internal:8443 -servername ingress.internal.example.com </dev/null 2>/dev/null \
     | openssl x509 -noout -enddate
   ```
2. Compare `notAfter` to today's date, 2026-09-13.
3. If `notAfter` is more than 14 days out, stop this runbook; the certificate does not need rotation yet.
4. If `notAfter` is 14 days out or less, or the connection fails with a certificate error, continue to Step 2.

## Step 2: Stage the new certificate to two nodes

Staging writes the new certificate to Vault and applies it to `ingress-01` and `ingress-02` only. The remaining four nodes keep serving the old certificate during this step.

1. Write the new certificate and key to Vault:
   ```
   vault kv put secret/ingress/tls-cert cert=@new-cert.pem key=@new-key.pem
   ```
2. Read back the version number Vault assigned:
   ```
   vault kv get -field=version secret/ingress/tls-cert
   ```
3. Record this version number. You need it for rollback in Step 5.
4. On `ingress-01`, pin the agent template to the new version and re-render:
   ```
   ssh ingress-01 'vault-agent-ctl set-version ingress-tls-cert <new-version> && vault-agent-ctl render'
   ```
5. Repeat step 4 on `ingress-02`.
6. Reload nginx on `ingress-01` and `ingress-02`:
   ```
   ssh ingress-01 'systemctl reload nginx'
   ssh ingress-02 'systemctl reload nginx'
   ```

A reload on a node drops the open connections on that node. Run the reload during the on-call low-traffic window if the certificate has more than 24 hours of validity left; otherwise run it now.

## Step 3: Verify the staged certificate

1. Query `ingress-01` directly:
   ```
   openssl s_client -connect ingress-01.internal:8443 -servername ingress.internal.example.com -showcerts </dev/null 2>/dev/null \
     | openssl x509 -noout -enddate -fingerprint -sha256
   ```
2. Check that `notAfter` matches the new certificate's expiry date.
3. Check that the SHA-256 fingerprint matches the fingerprint of `new-cert.pem` recorded in your prerequisites.
4. Repeat steps 1 through 3 against `ingress-02.internal:8443`.
5. Check the ingress error-rate dashboard for a spike on `ingress-01` or `ingress-02` in the two minutes after each reload.

Do not continue to Step 4 if any of the following is true: the fingerprint does not match, `notAfter` shows the old expiry, or the error rate on a canary node rises above its pre-rotation baseline. Go to Step 5 instead.

## Step 4: Roll to the remaining four nodes

1. For each of `ingress-03`, `ingress-04`, `ingress-05`, and `ingress-06`, in order, one node at a time:
   ```
   ssh <node> 'vault-agent-ctl set-version ingress-tls-cert <new-version> && vault-agent-ctl render'
   ssh <node> 'systemctl reload nginx'
   ```
2. After each reload, check the error-rate dashboard for a spike on that node before moving to the next.
3. After the fourth node reloads, run the Step 3 verification command against `ingress-06.internal:8443` to confirm the fleet-wide result.

A reload drops the open connections on that node, the same as in Step 2.

## Step 5: Roll back

Roll back when Step 3 or Step 4 fails its check on any node, or when the error-rate dashboard shows a sustained spike after a reload.

1. Confirm the previous version number in Vault:
   ```
   vault kv metadata get secret/ingress/tls-cert
   ```
2. Re-point each affected node's agent template to the previous version:
   ```
   ssh <node> 'vault-agent-ctl set-version ingress-tls-cert <previous-version> && vault-agent-ctl render'
   ```
3. Reload nginx on each affected node:
   ```
   ssh <node> 'systemctl reload nginx'
   ```
4. Run the Step 3 verification command against each rolled-back node to confirm `notAfter` and the fingerprint match the previous certificate.
5. Check the error-rate dashboard returns to its pre-rotation baseline on each rolled-back node.

A rollback reload drops the open connections on that node, the same as a forward reload.
