# Runbook: Rotate TLS Certificate on Internal Ingress

## Context

This runbook replaces an expiring TLS certificate on a six-node internal ingress controller. The process stages the certificate to two nodes first, verifies functionality, then rolls it to the remaining four nodes.

**Warning:** Reloading a node disconnects all open connections to that node. Coordinate this rotation during a maintenance window or when client traffic is lowest.

## Prerequisites

- Access to the Kubernetes cluster and ingress namespace
- `kubectl`, `openssl`, and `jq` installed on your local machine
- The new TLS certificate and private key as files
- The name of the ingress resource and its TLS secret
- A second terminal to monitor traffic during the rotation

## Phase 1: Verify Expiry

1. Identify the current TLS secret name:

   ```bash
   kubectl get ingress -n <namespace> <ingress-name> -o jsonpath='{.spec.tls[0].secretName}'
   ```

2. Retrieve the certificate from the secret:

   ```bash
   kubectl get secret -n <namespace> <secret-name> -o jsonpath='{.data.tls\.crt}' | base64 -d > current-cert.pem
   ```

3. Check the expiry date:

   ```bash
   openssl x509 -in current-cert.pem -noout -enddate
   ```

   The output shows `notAfter=<date>`. If the expiry is more than 30 days away, stop and reschedule.

## Phase 2: Create the Staging Secret

1. Create a backup of the current secret:

   ```bash
   kubectl get secret -n <namespace> <secret-name> -o yaml > secret-backup.yaml
   ```

2. Verify the backup contains the full secret definition:

   ```bash
   grep -c "tls.crt:" secret-backup.yaml
   ```

   Output must be `1`. If output is `0`, the backup failed; retrieve it again.

3. Create a new secret with the replacement certificate and key:

   ```bash
   kubectl create secret tls <secret-name>-staging \
     --cert=<path-to-new-cert.pem> \
     --key=<path-to-new-key.pem> \
     -n <namespace>
   ```

4. Verify the secret was created:

   ```bash
   kubectl get secret -n <namespace> <secret-name>-staging
   ```

## Phase 3: Stage Certificate to Two Nodes

Pod restart order depends on your ingress controller; these steps apply to most controllers (Nginx, HAProxy, Traefik).

1. Identify the two nodes to start with. List all ingress pods:

   ```bash
   kubectl get pods -n <namespace> -l app=ingress-controller -o wide
   ```

   Select the first two pods from the output. Note their names and node names.

2. Edit the ingress resource to point to the staging secret:

   ```bash
   kubectl patch ingress -n <namespace> <ingress-name> \
     --type merge \
     -p '{"spec":{"tls":[{"hosts":["<host>"],"secretName":"<secret-name>-staging"}]}}'
   ```

   Replace `<host>` with the hostname in the ingress TLS spec. Get this from:

   ```bash
   kubectl get ingress -n <namespace> <ingress-name> -o jsonpath='{.spec.tls[0].hosts[0]}'
   ```

3. Delete the first pod to force a reload with the new secret:

   ```bash
   kubectl delete pod -n <namespace> <first-pod-name>
   ```

   Wait for the pod to be ready:

   ```bash
   kubectl wait --for=condition=Ready pod/<first-pod-name> -n <namespace> --timeout=60s
   ```

4. Delete the second pod:

   ```bash
   kubectl delete pod -n <namespace> <second-pod-name>
   ```

   Wait for it to be ready:

   ```bash
   kubectl wait --for=condition=Ready pod/<second-pod-name> -n <namespace> --timeout=60s
   ```

## Phase 4: Verify the Staging Certificate

1. Retrieve the IP address or hostname of one of the two reloaded nodes:

   ```bash
   kubectl get pod -n <namespace> <first-pod-name> -o jsonpath='{.status.podIP}'
   ```

2. Connect to that pod and verify the certificate in memory:

   ```bash
   openssl s_client -connect <pod-ip>:443 -servername <host> < /dev/null 2>/dev/null | openssl x509 -noout -enddate
   ```

   Compare the returned `notAfter` date to the new certificate expiry you expect. If the date matches the new certificate, verification passed.

3. Verify the certificate chain if your setup requires it:

   ```bash
   openssl s_client -connect <pod-ip>:443 -servername <host> < /dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
   ```

   Confirm the subject and issuer match the new certificate.

4. Monitor your application logs or metrics during this time. Open a second terminal and watch:

   ```bash
   kubectl logs -n <namespace> -l app=ingress-controller -f --tail=20
   ```

   Look for errors related to certificate loading or TLS handshakes. If you see certificate errors, go to **Rollback** immediately.

## Phase 5: Roll Certificate to Remaining Four Nodes

1. List all remaining ingress pods:

   ```bash
   kubectl get pods -n <namespace> -l app=ingress-controller -o wide
   ```

2. Delete the remaining four pods one at a time. For each pod:

   ```bash
   kubectl delete pod -n <namespace> <pod-name>
   kubectl wait --for=condition=Ready pod/<pod-name> -n <namespace> --timeout=60s
   ```

   Delete all four pods in sequence, waiting after each one.

3. Verify all pods are ready:

   ```bash
   kubectl get pods -n <namespace> -l app=ingress-controller
   ```

   Output must show six pods with status `Running`. If any pod is `Pending`, `CrashLoopBackOff`, or another non-ready state, investigate its logs:

   ```bash
   kubectl logs -n <namespace> <pod-name> --tail=50
   ```

## Phase 6: Verify Full Rollout

1. Test the certificate from an external client:

   ```bash
   openssl s_client -connect <ingress-endpoint>:443 -servername <host> < /dev/null 2>/dev/null | openssl x509 -noout -enddate -subject
   ```

2. Confirm the endpoint is resolvable and responds:

   ```bash
   curl -I --cacert <path-to-ca.pem> https://<host>
   ```

   Expected: HTTP 200 or 3xx response. If connection refused or certificate errors appear, go to **Rollback**.

3. Run your application smoke tests or health checks. Wait for at least two minutes of traffic to validate no errors are occurring.

## Phase 7: Clean Up

1. Delete the staging secret:

   ```bash
   kubectl delete secret -n <namespace> <secret-name>-staging
   ```

2. Archive the backup for your records:

   ```bash
   tar czf tls-rotation-$(date +%Y%m%d).tar.gz secret-backup.yaml current-cert.pem
   ```

3. Delete the temporary certificate files:

   ```bash
   rm -f current-cert.pem <path-to-new-cert.pem> <path-to-new-key.pem>
   ```

## Rollback

If certificate errors occur at any point, revert to the previous certificate immediately.

1. Edit the ingress resource back to the original secret:

   ```bash
   kubectl patch ingress -n <namespace> <ingress-name> \
     --type merge \
     -p '{"spec":{"tls":[{"hosts":["<host>"],"secretName":"<secret-name>"}]}}'
   ```

2. Delete all ingress pods to force a reload:

   ```bash
   kubectl delete pods -n <namespace> -l app=ingress-controller
   ```

3. Wait for all pods to be ready:

   ```bash
   kubectl get pods -n <namespace> -l app=ingress-controller -w
   ```

   Press Ctrl+C when all six pods show `Running`.

4. Verify the certificate has reverted:

   ```bash
   openssl s_client -connect <ingress-endpoint>:443 -servername <host> < /dev/null 2>/dev/null | openssl x509 -noout -enddate
   ```

5. Restore normal operations and investigate the failure. Review the pod logs and certificate files.

## Troubleshooting

**Pod stuck in `CrashLoopBackOff`**

The new secret format is invalid or the ingress controller cannot mount it. Verify the secret exists:

```bash
kubectl get secret -n <namespace> <secret-name>-staging -o yaml
```

Check for `tls.crt` and `tls.key` keys in the data block. If missing, recreate the secret with correct files.

**Certificate verification fails**

The certificate on the pod does not match expectations. Verify the secret was correctly updated:

```bash
kubectl get secret -n <namespace> <secret-name>-staging -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -enddate
```

If the certificate is wrong, delete the secret and recreate it with the correct files.

**Clients report certificate errors**

This occurs if the intermediate or root certificate chain is missing. Retrieve the current certificate chain:

```bash
openssl s_client -connect <pod-ip>:443 -servername <host> -showcerts < /dev/null 2>/dev/null
```

Verify the chain includes all required intermediates. Recreate the secret with the full chain if needed.
