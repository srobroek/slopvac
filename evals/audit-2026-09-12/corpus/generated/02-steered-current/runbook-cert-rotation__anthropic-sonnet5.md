# Rotate the TLS Certificate on the Internal Ingress

## Scope

This runbook rotates the TLS certificate served by the six-node internal ingress at `ingress.internal.corp`. Use it after a certificate-expiry alert fires for this ingress. It covers checking the current certificate, staging the new certificate to two nodes, verifying the staged certificate with `openssl s_client`, rolling the remaining four nodes, and rolling back to the previous certificate version.

## Architecture

Six nodes, `ingress-node-01` through `ingress-node-06`, sit behind a load balancer at the VIP `ingress.internal.corp:443`. Each node serves the certificate stored in Vault KV v2 at `secret/ingress/tls-cert`. Vault keeps every write to that path as a new numbered version. Each node reads a version number from `/etc/ingress/cert-version` and fetches that version with `/usr/local/bin/cert-sync.sh`. Reloading nginx on a node drops that node's open connections. Clients reconnect through the load balancer to the other five nodes.

## Prerequisites

- Vault read and write access to `secret/ingress/tls-cert`.
- SSH access to `ingress-node-01` through `ingress-node-06` with sudo.
- `openssl` installed on your workstation.
- The new certificate and key files, `new-ingress.crt` and `new-ingress.key`, from the certificate authority.

## Nodes and batches

| Node | Batch | Order |
|---|---|---|
| `ingress-node-01` | staging | 1 |
| `ingress-node-02` | staging | 2 |
| `ingress-node-03` | rollout | 3 |
| `ingress-node-04` | rollout | 4 |
| `ingress-node-05` | rollout | 5 |
| `ingress-node-06` | rollout | 6 |

## Step 1: Check the current certificate

1. Query the VIP for the current certificate's serial number and expiry date:
   ```
   echo | openssl s_client -connect ingress.internal.corp:443 -servername ingress.internal.corp 2>/dev/null \
     | openssl x509 -noout -serial -enddate
   ```
2. Record the serial number as `old-serial`. You compare it against `old-serial` in the Rollback section if a rollback is needed.
3. Confirm the serial number matches the one named in the expiry alert. If it does not match, stop and escalate to the ingress team lead before proceeding.

## Step 2: Record the current Vault version

1. Get the current version number of the secret in Vault:
   ```
   vault kv metadata get secret/ingress/tls-cert
   ```
2. Record the `current_version` field as `previous-version`. You use `previous-version` for rollback in the Rollback section.

## Step 3: Write the new certificate to Vault

1. Get the new certificate's serial number:
   ```
   openssl x509 -noout -serial -in new-ingress.crt
   ```
   Record this value as `new-serial`.
2. Write the new certificate and key to the secret:
   ```
   vault kv put secret/ingress/tls-cert cert=@new-ingress.crt key=@new-ingress.key
   ```
3. Record the `version` field from the command output as `new-version`.

## Step 4: Stage the new certificate to two nodes

Stage the certificate to `ingress-node-01` and `ingress-node-02` before touching the other four nodes.

1. Pin `ingress-node-01` to `new-version` and reload:
   ```
   ssh ingress-node-01 'sudo /usr/local/bin/cert-sync.sh --version <new-version> && sudo nginx -s reload'
   ```
2. Reloading nginx drops `ingress-node-01`'s open connections. Clients reconnect through the load balancer to the other five nodes.
3. Repeat steps 1-2 for `ingress-node-02`.

## Step 5: Verify the staged certificate

1. Query `ingress-node-01` directly, bypassing the load balancer:
   ```
   echo | openssl s_client -connect ingress-node-01:443 -servername ingress.internal.corp 2>/dev/null \
     | openssl x509 -noout -serial -enddate
   ```
2. Confirm the returned serial number matches `new-serial`.
3. Repeat steps 1-2 for `ingress-node-02`.
4. If either node returns `old-serial` or the TLS handshake fails, go to the Rollback section for that node before continuing.

## Step 6: Roll to the remaining four nodes

Roll `ingress-node-03` through `ingress-node-06` one node at a time, in that order.

1. Pin the node to `new-version` and reload:
   ```
   ssh ingress-node-0X 'sudo /usr/local/bin/cert-sync.sh --version <new-version> && sudo nginx -s reload'
   ```
2. Reloading nginx drops that node's open connections. Clients reconnect through the load balancer to the remaining nodes.
3. Verify the node directly with the command from Step 5. Confirm the serial number matches `new-serial`.
4. Move to the next node in the batch only after the current node's serial number matches `new-serial`.
5. If a node fails verification, go to the Rollback section for that node before continuing to the next node.

## Step 7: Confirm the rollout

1. Query the VIP five times, spaced a few seconds apart:
   ```
   echo | openssl s_client -connect ingress.internal.corp:443 -servername ingress.internal.corp 2>/dev/null \
     | openssl x509 -noout -serial
   ```
2. Confirm every response returns `new-serial`.
3. Confirm `current_version` equals `new-version` in Vault:
   ```
   vault kv metadata get secret/ingress/tls-cert
   ```

## Rollback

Roll back a node if Step 5 or Step 6 verification fails for that node, or the on-call engineer decides to abort the rotation.

1. Re-point the node to `previous-version` and reload:
   ```
   ssh ingress-node-0X 'sudo /usr/local/bin/cert-sync.sh --version <previous-version> && sudo nginx -s reload'
   ```
2. Reloading nginx drops that node's open connections again. Clients reconnect through the load balancer to the remaining nodes.
3. Verify the rollback with the command from Step 5. Confirm the serial number matches `old-serial`.
4. Repeat steps 1-3 for every node already rolled to `new-version`.
5. After all affected nodes return `old-serial`, escalate to the ingress team lead with the recorded `old-serial`, `new-serial`, `previous-version`, and `new-version` values.
