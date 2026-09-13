# Runbook: Rotate the internal ingress TLS certificate

Audience: on-call engineer, first rotation. Scope: the six-node internal ingress cluster (`ingress-01` through `ingress-06`).

Reloading a node drops every open connection on that node. Stage the rotation in two waves so at most two nodes drop connections at once.

## Prerequisites

- `kubectl` access to the `ingress` namespace with `get`, `patch`, and `create secret` permissions.
- SSH access to `ingress-01` through `ingress-06`.
- The new certificate chain (`fullchain.pem`) and private key (`privkey.pem`) on your workstation.
- `openssl` 1.1.1 or later on your workstation.

## 1. Check the current expiry

Read the expiry from the live endpoint:

```
openssl s_client -connect ingress.internal:443 -servername ingress.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -subject -fingerprint -sha256
```

Record the `notAfter` date and the SHA-256 fingerprint. You compare the fingerprint against the new certificate in step 4.

Confirm all six nodes serve the same certificate:

```
for n in 01 02 03 04 05 06; do
  echo "ingress-$n"
  openssl s_client -connect ingress-$n.internal:443 -servername ingress.internal </dev/null 2>/dev/null \
    | openssl x509 -noout -enddate -fingerprint -sha256
done
```

If a node reports a different fingerprint, stop and escalate to the platform on-call. A split fingerprint means an earlier rotation did not finish.

## 2. Record the current secret version

The ingress reads its certificate from the `ingress-tls` secret. Capture the version you roll back to:

```
kubectl -n ingress get secret ingress-tls -o jsonpath='{.metadata.annotations.cert\.version}'
```

Write that value in the incident channel before you change anything. Rollback in step 7 needs it.

## 3. Validate the new certificate offline

Confirm the key matches the certificate. Both commands print the same modulus hash:

```
openssl x509 -noout -modulus -in fullchain.pem | openssl sha256
openssl rsa  -noout -modulus -in privkey.pem   | openssl sha256
```

Confirm the hostname and the new expiry:

```
openssl x509 -noout -text -in fullchain.pem | grep -A1 'Subject Alternative Name'
openssl x509 -noout -enddate -fingerprint -sha256 -in fullchain.pem
```

If the modulus hashes differ, stop. A mismatched key makes every node fail its TLS handshake after reload.

## 4. Stage to two nodes

Create the new secret version and pin the first wave to it.

1. Create the versioned secret:

```
kubectl -n ingress create secret tls ingress-tls-v2 \
  --cert=fullchain.pem --key=privkey.pem
```

2. Drain `ingress-01`:

```
kubectl -n ingress annotate node ingress-01 ingress.internal/drain=true --overwrite
```

3. Wait 30 seconds for the load balancer to stop sending new connections.

4. Point the node at the new secret and reload:

```
ssh ingress-01 'sudo ingressctl set-tls-secret ingress-tls-v2 && sudo ingressctl reload'
```

5. Verify the served certificate on that node:

```
openssl s_client -connect ingress-01.internal:443 -servername ingress.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -fingerprint -sha256
```

6. Confirm the fingerprint matches the one you recorded from `fullchain.pem` in step 3.

7. Verify chain validation against the internal root:

```
openssl s_client -connect ingress-01.internal:443 -servername ingress.internal \
  -CAfile /etc/ssl/certs/internal-root.pem </dev/null 2>&1 | grep 'Verify return code'
```

8. Confirm the output reads `Verify return code: 0 (ok)`.

9. Return `ingress-01` to service:

```
kubectl -n ingress annotate node ingress-01 ingress.internal/drain=false --overwrite
```

10. Repeat steps 2 through 9 for `ingress-02`.

## 5. Watch the first wave for 15 minutes

Check the two staged nodes against the four unstaged nodes:

```
kubectl -n ingress logs -l app=ingress --since=15m | grep -c 'tls handshake error'
```

If the handshake error count on `ingress-01` or `ingress-02` exceeds the count on `ingress-03`, go to step 7 and roll back. Do not proceed to the second wave.

If both staged nodes serve the new fingerprint with no excess handshake errors after 15 minutes, continue.

## 6. Roll to the remaining four nodes

Process `ingress-03`, `ingress-04`, `ingress-05`, and `ingress-06` one at a time. For each node, run steps 2 through 9 from section 4.

Wait for the verification in step 8 to return code `0` before you start the next node. One node at a time keeps five of six nodes serving traffic.

After the sixth node, re-run the six-node fingerprint loop from step 1. All six must report the new fingerprint and the new `notAfter` date.

## 7. Roll back

Rollback re-points each node at the previous secret. The old certificate is still valid until the `notAfter` date you recorded in step 1.

For each node already moved to `ingress-tls-v2`, in reverse order of rotation:

1. Drain the node:

```
kubectl -n ingress annotate node ingress-0N ingress.internal/drain=true --overwrite
```

2. Wait 30 seconds.

3. Re-point and reload:

```
ssh ingress-0N 'sudo ingressctl set-tls-secret ingress-tls && sudo ingressctl reload'
```

4. Confirm the node serves the fingerprint you recorded in step 1.

5. Return the node to service.

Delete `ingress-tls-v2` only after every node reports the old fingerprint:

```
kubectl -n ingress delete secret ingress-tls-v2
```

If the old certificate expires within 24 hours, rollback buys you less than a day. Escalate to the platform on-call instead of rolling back, and fix forward.

## Escalation

Page the platform on-call if any of these hold:

- A node fails `Verify return code: 0 (ok)` after reload and re-pointing the secret does not fix it.
- The six-node fingerprint check reports two different fingerprints after section 6 completes.
- The certificate expires within 24 hours and the new certificate fails verification.
