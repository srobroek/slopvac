# TLS Certificate Rotation Runbook for Internal Ingress (6-Node Cluster)

## Overview

This runbook guides you through safely rotating an expiring TLS certificate on a six-node internal ingress without downtime. The process stages the new certificate on two nodes for validation before rolling out to the remaining four nodes, allowing quick rollback if verification fails.

**Important:** Reloading an ingress node will drop all open connections on that node. Plan rotations during maintenance windows or low-traffic periods if possible.

## Prerequisites

- Access to your Kubernetes cluster via `kubectl`
- Current certificate and private key files (PEM format)
- SSH or shell access to ingress nodes (if manual verification is required)
- `openssl` CLI tool installed locally
- Backup of the existing TLS secret (`kubectl get secret <secret-name> -o yaml`)

## Pre-Flight Checklist

- [ ] Identify the expiring certificate's name and namespace
- [ ] Confirm the six-node layout and node names
- [ ] Verify you have the new certificate and key files
- [ ] Backup the existing TLS secret
- [ ] Ensure low-traffic or scheduled downtime window
- [ ] Notify stakeholders of the rotation window

## Step 1: Verify Certificate Expiry

Check the current certificate's expiration date:

```bash
# If stored locally
openssl x509 -in /path/to/current-cert.crt -noout -dates

# If stored as a Kubernetes secret
kubectl get secret <secret-name> -n <namespace> -o jsonpath='{.data.tls\.crt}' | \
  base64 -d | openssl x509 -noout -dates
```

**Expected output:**
```
notBefore=...
notAfter=YYYY-MM-DD HH:MM:SS GMT
```

Record the `notAfter` date. If it shows more than 30 days remaining, confirm this rotation is necessary.

## Step 2: Backup the Existing TLS Secret

Save the current secret in case rollback is needed:

```bash
kubectl get secret <secret-name> -n <namespace> -o yaml > \
  tls-secret-backup-$(date +%Y%m%d_%H%M%S).yaml
```

Keep this file safe for the duration of the rotation.

## Step 3: Create the New TLS Secret

Create a Kubernetes TLS secret with the new certificate and key:

```bash
kubectl create secret tls <secret-name>-new \
  --cert=/path/to/new-cert.crt \
  --key=/path/to/new-key.key \
  -n <namespace> \
  --dry-run=client \
  -o yaml | kubectl apply -f -
```

Verify the secret was created:

```bash
kubectl get secret <secret-name>-new -n <namespace>
```

## Step 4: Stage Certificate on First Two Nodes

The six ingress nodes are typically labeled or named (e.g., `ingress-1` through `ingress-6`). Update the ingress resource or node configuration to point **only the first two nodes** to the new secret.

For a typical Kubernetes ingress, edit the ingress resource:

```bash
kubectl edit ingress <ingress-name> -n <namespace>
```

In the `spec.tls` section, update the `secretName` to point to the new secret:

```yaml
spec:
  tls:
  - hosts:
    - "your.internal.domain"
    secretName: <secret-name>-new
```

**Save and close the editor.** Kubernetes will begin rolling out the new secret.

Monitor the ingress controller pods:

```bash
kubectl get pods -n ingress-controller -o wide | grep ingress

# Watch for pod restarts
kubectl get pods -n ingress-controller -w
```

Wait for all pods on the first two nodes to stabilize (2–3 minutes).

## Step 5: Verify New Certificate on First Two Nodes

Verify that the new certificate is correctly loaded. For each of the first two ingress nodes, connect using `openssl s_client`:

```bash
openssl s_client -connect <ingress-node-ip>:443 \
  -servername your.internal.domain \
  </dev/null 2>/dev/null | openssl x509 -noout -dates
```

**Expected output:**
```
notBefore=...
notAfter=<new expiry date>
```

Confirm the `notAfter` date matches your new certificate.

Also check the certificate subject and issuer to ensure it's the correct certificate:

```bash
openssl s_client -connect <ingress-node-ip>:443 \
  -servername your.internal.domain \
  </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
```

**Perform this verification on both of the first two nodes.** If any verification fails, proceed to **Rollback** (Step 7) immediately.

## Step 6: Roll Out Certificate to Remaining Four Nodes

Once verification succeeds on the first two nodes, update all six nodes to use the new secret. Edit the ingress again:

```bash
kubectl edit ingress <ingress-name> -n <namespace>
```

Ensure the `secretName` is still set to `<secret-name>-new`, then save.

Monitor the rollout:

```bash
kubectl get pods -n ingress-controller -w
```

Allow 2–3 minutes for all pods to restart and stabilize.

## Step 7: Final Verification on All Nodes

Verify the new certificate is loaded on all six nodes:

```bash
for node in ingress-{1..6}; do
  echo "=== $node ==="
  openssl s_client -connect <node-ip>:443 \
    -servername your.internal.domain \
    </dev/null 2>/dev/null | openssl x509 -noout -dates
done
```

All nodes should show the new expiry date.

## Step 8: Clean Up and Document

Once all verifications pass:

1. Rename the new secret to the original name (optional, for cleaner state):

   ```bash
   # Create a copy with the original name
   kubectl get secret <secret-name>-new -n <namespace> -o yaml | \
     sed 's/<secret-name>-new/<secret-name>/g' | \
     kubectl apply -f -
   ```

2. Update the ingress to point to the original secret name (if you renamed):

   ```bash
   kubectl edit ingress <ingress-name> -n <namespace>
   # Change secretName to <secret-name>
   ```

3. Delete the old secret (only after confirming no fallback is needed):

   ```bash
   kubectl delete secret <secret-name>-old -n <namespace>
   ```

4. Document the rotation in your runbook log:

   ```
   Date: YYYY-MM-DD
   Certificate: <domain>
   Old Expiry: YYYY-MM-DD
   New Expiry: YYYY-MM-DD
   Performed by: <your-name>
   Status: SUCCESS
   ```

## Rollback Procedure

If verification fails on the first two nodes, or if issues are detected later:

1. **Immediately stop further rollout:**

   ```bash
   kubectl edit ingress <ingress-name> -n <namespace>
   ```

   Change the `secretName` back to the original secret name.

2. **Restore from backup (if the original secret was deleted):**

   ```bash
   kubectl apply -f tls-secret-backup-<timestamp>.yaml
   ```

3. **Wait for all nodes to stabilize:**

   ```bash
   kubectl get pods -n ingress-controller -w
   ```

4. **Verify the original certificate is restored:**

   ```bash
   openssl s_client -connect <ingress-node-ip>:443 \
     -servername your.internal.domain \
     </dev/null 2>/dev/null | openssl x509 -noout -dates
   ```

5. **Investigate the failure** with the certificate provider or security team before reattempting the rotation.

## Troubleshooting

### Issue: `openssl s_client` connection refused

- Confirm the node IP and port are correct
- Check that the ingress controller pod is running on the node
- Verify network connectivity to the node

### Issue: Certificate shows old expiry date after update

- The pod may not have fully restarted; wait another minute and retry
- Check pod logs for errors:
  ```bash
  kubectl logs -n ingress-controller <pod-name> --tail=50
  ```

### Issue: High latency or failed requests during rollout

- This is expected as connections are dropped during node reloads
- Ensure clients have retry logic with backoff
- Consider reducing traffic manually if possible

## Notes for Future Rotations

- Schedule rotations at least 30 days before expiry
- Perform rotations during a maintenance window if possible
- Keep DNS TTLs low (< 5 minutes) for rapid failover if needed
- Test the new certificate locally before uploading to Kubernetes
- Consider automating this runbook with a shell script for repeated use
