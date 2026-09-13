# TLS Certificate Rotation Runbook

## Overview

This runbook guides you through rotating an expiring TLS certificate on an internal ingress cluster with six nodes. The procedure stages the new certificate to two nodes for verification, rolls it to the remaining four nodes, and provides a rollback path.

When a node reloads its ingress configuration, it drops all open connections on that node. Plan the rotation for a maintenance window or during low-traffic periods if possible.

## Prerequisites

- SSH access to all six ingress nodes.
- `kubectl` access to the cluster and the namespace where the ingress secret lives.
- The new certificate and private key files on your local machine or on a jump host.
- The node names or labels that identify the six nodes in your environment.

## Procedure

### Check the current certificate expiry

1. Identify the name of the secret that holds the ingress certificate: ask the ingress team or check the ingress resource definition with `kubectl get ingress -o yaml` and find the `tls.secretName` field.

2. Retrieve the certificate from the secret:

   ```
   kubectl get secret <SECRET_NAME> -o jsonpath='{.data.tls\.crt}' | base64 -d > current.crt
   ```

3. Check the expiry date:

   ```
   openssl x509 -in current.crt -noout -enddate
   ```

4. Record the expiry date in your incident ticket or change request.

### Prepare the new certificate

1. Verify that the new certificate file and private key are present on your local machine or a jump host.

2. Check that the new certificate is valid and has not yet expired:

   ```
   openssl x509 -in new.crt -noout -startdate -enddate
   ```

3. Verify that the certificate Subject or Subject Alternative Name (SAN) matches the ingress hostname:

   ```
   openssl x509 -in new.crt -noout -text | grep -A 1 "Subject Alternative Name"
   ```

### Stage the certificate to two nodes

1. Identify the names of two of the six ingress nodes. These are your stage nodes.

2. Copy the new certificate and private key to the first stage node:

   ```
   scp new.crt <USER>@<NODE1>:/tmp/
   scp new.key <USER>@<NODE1>:/tmp/
   ```

3. SSH into the first stage node:

   ```
   ssh <USER>@<NODE1>
   ```

4. Place the new certificate and key in the location where the ingress controller expects them. This path depends on your ingress controller and cluster configuration. Common paths are `/etc/ingress/certs/` or a mounted volume at `/etc/kubernetes/ingress/secrets/`. Ask your platform team if you do not know the path.

5. Set the correct file permissions:

   ```
   sudo chmod 644 /path/to/new.crt
   sudo chmod 600 /path/to/new.key
   ```

6. Create a backup of the current certificate:

   ```
   sudo cp /path/to/tls.crt /path/to/tls.crt.backup.<DATE>
   sudo cp /path/to/tls.key /path/to/tls.key.backup.<DATE>
   ```

7. Replace the current certificate with the new one:

   ```
   sudo cp /tmp/new.crt /path/to/tls.crt
   sudo cp /tmp/new.key /path/to/tls.key
   ```

8. Reload or restart the ingress controller process on this node. The command depends on your setup:

   ```
   sudo systemctl restart <INGRESS_SERVICE_NAME>
   ```

   Or if running in a container:

   ```
   sudo docker exec <CONTAINER_ID> nginx -s reload
   ```

9. Exit the SSH session.

10. Repeat steps 2–9 for the second stage node.

### Verify the staged certificate

1. Note the hostname or IP address of the ingress service.

2. For each of the two stage nodes, connect with `openssl s_client` to verify the certificate:

   ```
   openssl s_client -connect <INGRESS_HOSTNAME>:443 -servername <INGRESS_HOSTNAME> < /dev/null
   ```

3. In the output, verify that the certificate subject matches your ingress hostname and that the expiry date matches the new certificate.

4. If the certificate does not match, do not proceed to the remaining nodes. Proceed to the Rollback section.

### Roll the certificate to the remaining four nodes

1. For each of the remaining four nodes, repeat the stage procedure: copy the files, place them, back up the originals, replace them, and reload the service.

### Verify the final state

1. Connect to the ingress endpoint from your local machine:

   ```
   openssl s_client -connect <INGRESS_HOSTNAME>:443 -servername <INGRESS_HOSTNAME> < /dev/null
   ```

2. Verify that the certificate is the new one and has not expired.

3. Test application traffic to the ingress to confirm that clients can establish connections.

## Rollback

If verification fails or you encounter errors, you can roll back to the previous certificate version.

### Rollback procedure

1. Identify which nodes have the new certificate and which still have the old one.

2. For each node that has the new certificate, SSH into the node:

   ```
   ssh <USER>@<NODE>
   ```

3. Restore the backup certificate and key:

   ```
   sudo cp /path/to/tls.crt.backup.<DATE> /path/to/tls.crt
   sudo cp /path/to/tls.key.backup.<DATE> /path/to/tls.key
   ```

4. Reload the ingress service:

   ```
   sudo systemctl restart <INGRESS_SERVICE_NAME>
   ```

5. Verify the rollback with `openssl s_client`:

   ```
   openssl s_client -connect <INGRESS_HOSTNAME>:443 -servername <INGRESS_HOSTNAME> < /dev/null
   ```

6. Exit the SSH session and move to the next node.

7. After rolling back all nodes, contact the ingress team to troubleshoot why the new certificate failed.
