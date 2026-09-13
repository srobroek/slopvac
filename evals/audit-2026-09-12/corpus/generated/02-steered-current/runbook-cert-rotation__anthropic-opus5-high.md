# Runbook: Rotate the internal ingress TLS certificate

Applies to the six-node internal ingress: `ingress-01` through `ingress-06`. Each reload drops that node's open connections, so this procedure moves two nodes first and the remaining four after verification.

## Prerequisites

- `kubectl` context set to the `ingress` cluster, with edit access to the `ingress-tls` secret in namespace `ingress`.
- SSH access to `ingress-01` through `ingress-06`.
- `openssl` 1.1.1 or later on your workstation.
- The replacement certificate chain and private key, PEM-encoded.
- A load balancer that removes an unhealthy node from rotation within 10 seconds.

## 1. Check the current expiry

Read the expiry from the live listener, not from a file on disk:

```
echo | openssl s_client -connect ingress-01.internal:443 -servername ingress.internal 2>/dev/null \
  | openssl x509 -noout -enddate -fingerprint -sha256
```

Record the `notAfter` date and the SHA-256 fingerprint. The fingerprint identifies the old certificate during verification and rollback.

Repeat the command against `ingress-02` through `ingress-06`. If any node serves a different fingerprint, stop and escalate to the platform on-call: the nodes are already out of sync, and this runbook assumes a single active certificate.

## 2. Record the current secret version

```
kubectl -n ingress get secret ingress-tls -o jsonpath='{.metadata.annotations.cert\.version}'
```

Write the returned version string in the incident channel. Rollback in step 6 re-points the secret to this version.

## 3. Load the new certificate

Verify the new material before it reaches any node.

1. Confirm the key matches the certificate. Both commands must print the same hash:
   ```
   openssl x509 -noout -modulus -in new.crt | openssl sha256
   openssl rsa  -noout -modulus -in new.key | openssl sha256
   ```
2. Confirm the chain validates against the internal CA:
   ```
   openssl verify -CAfile /etc/ssl/internal-ca.pem new.crt
   ```
3. Confirm the SAN list contains `ingress.internal`:
   ```
   openssl x509 -noout -text -in new.crt | grep -A1 'Subject Alternative Name'
   ```
4. Create a new secret version:
   ```
   kubectl -n ingress create secret tls ingress-tls-next \
     --cert=new.crt --key=new.key
   ```

If any of the three checks fails, stop. Do not proceed with a mismatched key, an unverifiable chain, or a missing SAN.

## 4. Stage to two nodes

Move `ingress-01` and `ingress-02` one at a time.

1. Drain the node from the load balancer:
   ```
   ssh ingress-01.internal 'sudo touch /etc/ingress/drain'
   ```
2. Wait 15 seconds for the load balancer to mark the node unhealthy.
3. Confirm the node receives no new requests:
   ```
   ssh ingress-01.internal 'sudo ss -tn state established "( sport = :443 )" | wc -l'
   ```
   Wait until the count stops decreasing, up to 60 seconds.
4. Point the node at the new secret and reload:
   ```
   ssh ingress-01.internal 'sudo ingressctl set-tls ingress-tls-next && sudo ingressctl reload'
   ```
5. Verify the served certificate, bypassing the load balancer:
   ```
   echo | openssl s_client -connect ingress-01.internal:443 -servername ingress.internal 2>/dev/null \
     | openssl x509 -noout -enddate -fingerprint -sha256
   ```
   The fingerprint must differ from the one recorded in step 1, and `notAfter` must be the new expiry.
6. Return the node to rotation:
   ```
   ssh ingress-01.internal 'sudo rm /etc/ingress/drain'
   ```
7. Repeat steps 1 through 6 for `ingress-02`.

## 5. Observe, then roll the remaining four

Wait 15 minutes with `ingress-01` and `ingress-02` serving the new certificate. Watch two signals:

| Signal | Threshold for continuing |
|---|---|
| TLS handshake errors on `ingress-01`, `ingress-02` | No increase over the pre-rotation rate |
| HTTP 5xx rate through the load balancer | No increase over the pre-rotation rate |

If either signal rises, go to step 6.

If both hold, promote the secret and roll the rest:

1. Point the shared secret at the new material:
   ```
   kubectl -n ingress annotate secret ingress-tls cert.version=<new-version> --overwrite
   ```
2. Apply steps 4.1 through 4.6 to `ingress-03`, then `ingress-04`, then `ingress-05`, then `ingress-06`. Complete one node before starting the next; two drained nodes leave four serving traffic, and three leave three.
3. Confirm all six nodes serve the new fingerprint:
   ```
   for n in 01 02 03 04 05 06; do
     echo -n "ingress-$n "
     echo | openssl s_client -connect ingress-$n.internal:443 -servername ingress.internal 2>/dev/null \
       | openssl x509 -noout -fingerprint -sha256
   done
   ```

## 6. Roll back

Rollback re-points the secret to the version recorded in step 2 and reloads every node that received the new certificate.

1. Restore the secret version:
   ```
   kubectl -n ingress annotate secret ingress-tls cert.version=<old-version> --overwrite
   ```
2. For each node already reloaded, run steps 4.1 through 4.3, then:
   ```
   ssh ingress-<n>.internal 'sudo ingressctl set-tls ingress-tls && sudo ingressctl reload'
   ```
3. Verify the node serves the fingerprint recorded in step 1, then run step 4.6 to return it to rotation.
4. Delete the rejected secret:
   ```
   kubectl -n ingress delete secret ingress-tls-next
   ```

Rollback reloads each node, so it drops open connections a second time. The old certificate remains valid until the `notAfter` date recorded in step 1; that date bounds how long the rolled-back state can hold.

## Escalate

Escalate to the platform on-call when any of these hold:

- Nodes serve different fingerprints before step 4 begins.
- The old certificate expires within 24 hours and verification in step 4.5 fails.
- A node fails to return to a healthy state in the load balancer within 60 seconds of step 4.6.
