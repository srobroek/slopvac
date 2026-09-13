# Rotating an Expiring TLS Certificate on the Internal Ingress

This runbook covers replacing the TLS certificate served by the internal ingress. The ingress runs on six nodes (`ingress-01` through `ingress-06`). You will stage the new certificate on two nodes, verify it, then roll the remaining four.

**Reloading a node drops its open connections.** Every reload in this runbook terminates in-flight requests on that node. This is why the roll happens in batches and never touches all six nodes at once.

Expect 45–60 minutes end to end, most of it spent waiting between batches.

## Before you start

You need:

- `kubectl` access to the `ingress` namespace with permission to patch secrets and delete pods
- The new certificate and private key, PEM-encoded, with the full chain in the certificate file
- `openssl` on your workstation
- The load balancer dashboard open, so you can watch per-node connection counts and 5xx rates

Confirm two things before touching anything:

1. **The new certificate is the one you think it is.** Check its subject, SANs, and validity window:

   ```
   openssl x509 -in newcert.pem -noout -subject -ext subjectAltName -dates
   ```

   The SANs must cover every hostname the ingress currently serves. A certificate missing one SAN will pass the checks in this runbook for the hostname you test and fail for everything else.

2. **The key matches the certificate.** These two commands must print the same hash:

   ```
   openssl x509 -in newcert.pem -noout -modulus | openssl sha256
   openssl rsa -in newkey.pem -noout -modulus | openssl sha256
   ```

   If they differ, stop. Get a matching pair before continuing.

## Step 1: Check the current expiry and record the rollback target

Read the expiry from a live node rather than from a file, so you know what is actually being served:

```
openssl s_client -connect ingress-01.internal:443 -servername app.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -dates -fingerprint -sha256
```

Write down the `notAfter` date and the SHA-256 fingerprint. The fingerprint is how you will tell the old certificate from the new one during verification.

Now record the rollback target. The ingress reads its certificate from the secret `ingress-tls` in the `ingress` namespace, and that secret is versioned. List the versions:

```
kubectl -n ingress get secret ingress-tls -o jsonpath='{.metadata.annotations.cert-version}'
kubectl -n ingress get secrets -l app=ingress-tls --sort-by=.metadata.creationTimestamp
```

**Write the current version identifier into your incident channel or notes now.** Rollback in Step 5 depends on knowing this value, and it is much harder to recover once the new version is in place.

## Step 2: Stage the new certificate as a new secret version

Create the new version as a separate secret. Do not overwrite the existing one — that is what makes rollback a pointer change rather than a restore.

```
kubectl -n ingress create secret tls ingress-tls-v2 \
  --cert=newcert.pem --key=newkey.pem \
  --dry-run=client -o yaml \
  | kubectl label -f - --local -o yaml app=ingress-tls \
  | kubectl apply -f -
```

Nothing is serving this certificate yet. No connections have been affected.

## Step 3: Roll the first two nodes

Point `ingress-01` and `ingress-02` at the new secret version. These nodes carry roughly a third of the traffic, so the blast radius of a bad certificate is bounded, and you get a real signal before committing the rest.

Patch the per-node configuration for the first two nodes only:

```
kubectl -n ingress patch ingressnode ingress-01 \
  --type merge -p '{"spec":{"tlsSecret":"ingress-tls-v2"}}'
kubectl -n ingress patch ingressnode ingress-02 \
  --type merge -p '{"spec":{"tlsSecret":"ingress-tls-v2"}}'
```

Reload each node one at a time, waiting for the first to come back before reloading the second:

```
kubectl -n ingress rollout restart deployment/ingress-01
kubectl -n ingress rollout status deployment/ingress-01 --timeout=120s
```

Then repeat for `ingress-02`.

**Both reloads drop the open connections on that node.** Clients that retry will land on the four untouched nodes. Watch the 5xx rate on the load balancer dashboard: a brief spike as connections drop is expected; a sustained elevated rate is not.

## Step 4: Verify the staged nodes

Verify against the staged nodes directly, bypassing the load balancer, so you know which node answered.

Check the fingerprint and dates on `ingress-01`:

```
openssl s_client -connect ingress-01.internal:443 -servername app.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -dates -fingerprint -sha256
```

The fingerprint must differ from the one you recorded in Step 1, and `notAfter` must show the new expiry. Repeat for `ingress-02`.

Check that the chain validates and the hostname matches:

```
openssl s_client -connect ingress-01.internal:443 -servername app.internal \
  -verify_return_error -verify_hostname app.internal </dev/null
```

Look for `Verify return code: 0 (ok)` near the end of the output. Any nonzero code means the chain is incomplete or the hostname does not match — go to Step 5.

Check every hostname the ingress serves, not just one. Change `-servername` and `-verify_hostname` together for each:

```
openssl s_client -connect ingress-01.internal:443 -servername api.internal \
  -verify_return_error -verify_hostname api.internal </dev/null
```

A missing intermediate certificate is the most common failure here, and it often shows up on one hostname and not another.

Before moving on, confirm all four of these:

- Fingerprint on both staged nodes differs from the Step 1 value
- `Verify return code: 0 (ok)` for every hostname on both staged nodes
- `notAfter` shows the expected new expiry
- 5xx rate on the dashboard has returned to its pre-rotation baseline

If any check fails, go to Step 5. Do not roll the remaining nodes to "see if it clears up."

## Step 5: Roll the remaining four nodes

Let the staged nodes serve real traffic for at least 10 minutes before continuing. Some failures — session resumption problems, client-side pinning, OCSP stapling gaps — only appear once a variety of clients have connected.

Roll `ingress-03` through `ingress-06` in two batches of two, not all four at once. Rolling all four leaves only the two staged nodes online, and if the new certificate has a problem those two are the ones carrying everything.

Batch one:

```
kubectl -n ingress patch ingressnode ingress-03 \
  --type merge -p '{"spec":{"tlsSecret":"ingress-tls-v2"}}'
kubectl -n ingress patch ingressnode ingress-04 \
  --type merge -p '{"spec":{"tlsSecret":"ingress-tls-v2"}}'
kubectl -n ingress rollout restart deployment/ingress-03
kubectl -n ingress rollout status deployment/ingress-03 --timeout=120s
kubectl -n ingress rollout restart deployment/ingress-04
kubectl -n ingress rollout status deployment/ingress-04 --timeout=120s
```

Verify both nodes with the Step 4 commands, then repeat for `ingress-05` and `ingress-06`.

When all six are done, verify through the load balancer as well. Run this several times so you hit different backends:

```
for i in $(seq 1 12); do
  openssl s_client -connect app.internal:443 -servername app.internal </dev/null 2>/dev/null \
    | openssl x509 -noout -fingerprint -sha256
done
```

Every line must show the new fingerprint. If any line shows the old one, a node did not pick up the new secret — find it by checking each node directly and reload it.

## Rolling back

Rollback re-points the secret reference to the previous version. It requires the same reloads as rolling forward, and **those reloads drop connections again**.

Roll back the affected nodes only. If you are in Step 4 and the staged nodes failed verification, roll back `ingress-01` and `ingress-02` and leave the other four alone — they are still serving the old certificate and are healthy.

Point the nodes back at the previous secret, using the version identifier you recorded in Step 1:

```
kubectl -n ingress patch ingressnode ingress-01 \
  --type merge -p '{"spec":{"tlsSecret":"ingress-tls"}}'
kubectl -n ingress patch ingressnode ingress-02 \
  --type merge -p '{"spec":{"tlsSecret":"ingress-tls"}}'
```

Reload one node at a time, waiting for each to come back:

```
kubectl -n ingress rollout restart deployment/ingress-01
kubectl -n ingress rollout status deployment/ingress-01 --timeout=120s
```

Confirm the rollback by checking that the fingerprint matches the Step 1 value:

```
openssl s_client -connect ingress-01.internal:443 -servername app.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -dates -fingerprint -sha256
```

Do not delete `ingress-tls-v2`. Leave it in place for whoever investigates the failure.

**If the old certificate has already expired, rollback is not a safe option.** You will be moving from a broken new certificate to an expired old one. In that case, escalate rather than rolling back, and fix the new certificate forward.

## After the rotation

- Confirm the new expiry appears in certificate monitoring and that the expiry alert has cleared
- Note the new `notAfter` date and schedule the next rotation well ahead of it
- Keep the previous secret version for one week, then delete it
- If you hit anything this runbook did not cover, add it — the next person on call will not have done this before either
