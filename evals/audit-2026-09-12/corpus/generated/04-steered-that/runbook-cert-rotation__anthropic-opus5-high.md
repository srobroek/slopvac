# Runbook: Rotate an expiring TLS certificate on internal ingress

Audience: on-call engineer performing this rotation for the first time.

## Scope

The internal ingress runs on six nodes: `ing-01` through `ing-06`. All six terminate TLS with the certificate stored in the Kubernetes secret `ingress-tls` in namespace `ingress`. Rotation stages the new certificate to `ing-01` and `ing-02`, verifies both, then rolls to `ing-03` through `ing-06`.

Reloading a node drops every open connection on that node. Clients see a connection reset and must retry. Reload at most two of the six nodes at a time.

## Prerequisites

- `kubectl` context set to the cluster running namespace `ingress`.
- Member of the `ingress-operators` group, which grants `patch` on secrets in namespace `ingress`.
- The new certificate chain and private key as PEM files.
- `openssl` 1.1.1 or later on the host you run verification from.

## 1. Check the current expiry

Read the certificate the ingress is serving now:

```
openssl s_client -connect ing-01.internal:443 -servername ingress.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -enddate -fingerprint -sha256
```

Record the `notAfter` date and the SHA-256 fingerprint. The fingerprint identifies the old certificate during verification and rollback.

Confirm that the secret matches what the node serves:

```
kubectl -n ingress get secret ingress-tls -o jsonpath='{.data.tls\.crt}' \
  | base64 -d | openssl x509 -noout -enddate -fingerprint -sha256
```

If the two fingerprints differ, stop and escalate to the ingress owner. A node serving a certificate that is not in the secret means that a previous rotation did not complete.

## 2. Validate the new certificate before staging

Run all four checks. Each failure has a fix, so do not proceed past a failure.

```
openssl x509 -in new-tls.crt -noout -subject -enddate -ext subjectAltName
openssl x509 -in new-tls.crt -noout -modulus | openssl sha256
openssl rsa -in new-tls.key -noout -modulus | openssl sha256
openssl verify -untrusted new-chain.pem new-tls.crt
```

- The `subjectAltName` list must contain `ingress.internal`.
- The two modulus hashes must be identical. Different hashes mean that the key does not match the certificate.
- `notAfter` must be at least 30 days ahead of today.
- `openssl verify` must print `new-tls.crt: OK`.

## 3. Record the current secret version for rollback

```
kubectl -n ingress get secret ingress-tls -o yaml > /tmp/ingress-tls-previous.yaml
kubectl -n ingress get secret ingress-tls -o jsonpath='{.metadata.resourceVersion}'
```

Keep `/tmp/ingress-tls-previous.yaml` until step 6 completes. Rollback reads this file.

## 4. Stage to ing-01 and ing-02

1. Announce the rotation in `#ingress-oncall`, naming the two nodes and the expected connection drop.
2. Remove `ing-01` and `ing-02` from the load balancer pool.
3. Wait 30 seconds for in-flight requests to finish.
4. Write the new certificate into the secret:

   ```
   kubectl -n ingress create secret tls ingress-tls \
     --cert=new-tls.crt --key=new-tls.key \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

5. Reload `ing-01` and `ing-02`:

   ```
   kubectl -n ingress exec ing-01 -- nginx -s reload
   kubectl -n ingress exec ing-02 -- nginx -s reload
   ```

Nodes `ing-03` through `ing-06` keep serving the old certificate from their loaded copy until you reload them in step 6.

## 5. Verify the two staged nodes

Run this against `ing-01`, then against `ing-02`:

```
openssl s_client -connect ing-01.internal:443 -servername ingress.internal \
  -showcerts </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -fingerprint -sha256
```

Verification passes when all three hold:

- The fingerprint matches the new certificate from step 2.
- The `notAfter` date matches the new certificate.
- The handshake returns `Verify return code: 0 (ok)`, visible in the full `s_client` output.

Then check that a real client path works:

```
curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' \
  --resolve ingress.internal:443:$(dig +short ing-01.internal) \
  https://ingress.internal/healthz
```

Expect `200 0`.

Return `ing-01` and `ing-02` to the load balancer pool. Watch the ingress error-rate dashboard for 10 minutes. If the 5xx rate on either node exceeds its pre-rotation baseline, go to section "Roll back".

## 6. Roll to the remaining four nodes

Reload in two pairs so that four nodes stay in the pool throughout.

Pair one:

1. Remove `ing-03` and `ing-04` from the pool.
2. Wait 30 seconds.
3. Reload both: `kubectl -n ingress exec ing-03 -- nginx -s reload`, then the same for `ing-04`.
4. Verify both with the `s_client` command from step 5.
5. Return both to the pool.

Pair two: repeat the five steps for `ing-05` and `ing-06`.

Confirm all six nodes serve the new fingerprint:

```
for n in 01 02 03 04 05 06; do
  echo -n "ing-$n "
  openssl s_client -connect ing-$n.internal:443 -servername ingress.internal </dev/null 2>/dev/null \
    | openssl x509 -noout -fingerprint -sha256
done
```

Six identical fingerprints, each matching the new certificate, ends the rotation.

## Roll back

Roll back when a staged node returns a nonzero `Verify return code`, serves an unexpected fingerprint, or raises its 5xx rate above the pre-rotation baseline.

1. Remove every reloaded node from the load balancer pool.
2. Re-point the secret to the previous version:

   ```
   kubectl -n ingress apply -f /tmp/ingress-tls-previous.yaml
   ```

3. Confirm that the secret holds the old fingerprint from step 1:

   ```
   kubectl -n ingress get secret ingress-tls -o jsonpath='{.data.tls\.crt}' \
     | base64 -d | openssl x509 -noout -fingerprint -sha256
   ```

4. Reload each node you reloaded during rotation. This drops open connections on those nodes a second time.
5. Verify each rolled-back node with the `s_client` command from step 5. The fingerprint must match the old certificate.
6. Return the nodes to the pool.
7. Open an issue against the ingress repository. Include the failing node, the `s_client` output, and the new certificate's fingerprint.

Nodes never reloaded during rotation need no action. They still hold the old certificate in memory.

## Failure modes

| Symptom | Cause | Action |
| --- | --- | --- |
| `Verify return code: 21 (unable to verify the first certificate)` | The secret's `tls.crt` omits an intermediate | Concatenate leaf then intermediates into `new-tls.crt`, re-apply, reload |
| Reloaded node still serves the old fingerprint | The kubelet has not projected the updated secret to the pod's volume | Wait 60 seconds, then reload again |
| `curl` reports `ssl_verify_result` other than `0` | The client trust store lacks the new issuing CA | Roll back, then distribute the CA before retrying |
| `nginx -s reload` exits nonzero | The staged PEM fails nginx's parse | Roll back, then re-run the step 2 checks on the PEM files |

## Post-rotation

- Delete `/tmp/ingress-tls-previous.yaml`.
- Set a calendar reminder 30 days before the new `notAfter` date.
- Record the new fingerprint and `notAfter` date in the ingress runbook log.
