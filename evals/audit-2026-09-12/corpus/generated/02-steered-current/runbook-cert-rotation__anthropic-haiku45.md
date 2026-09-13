# Rotate an Expiring TLS Certificate on the Internal Ingress

## Prerequisites

You need `kubectl` access to the cluster where the ingress runs and the `openssl` command on your local machine.

Reloading a node to apply a new certificate terminates all open connections to that node.

## Overview

This runbook describes replacing an expiring TLS certificate on an ingress with six nodes.
The process stages the new certificate to two nodes first, verifies connectivity with `openssl s_client`, then rolls to the remaining four nodes.
You can roll back by re-pointing the ingress secret to its previous certificate version.

## Check certificate expiry

1. Identify the secret name that stores the ingress TLS certificate.
   ```bash
   kubectl get ingress <INGRESS_NAME> -o jsonpath='{.spec.tls[0].secretName}'
   ```

2. Decode the certificate from the secret.
   ```bash
   kubectl get secret <SECRET_NAME> -o jsonpath='{.data.tls\.crt}' | base64 -d > cert.pem
   ```

3. Display the expiry date.
   ```bash
   openssl x509 -in cert.pem -noout -enddate
   ```

4. If the expiry is more than 30 days away, stop here; certificate rotation is not urgent.

## Obtain the new certificate and key

Receive the new certificate and private key from your certificate authority as PEM-encoded files.
Store these files locally as `new-cert.pem` and `new-key.pem`.

## Stage the new certificate to two nodes

1. Create a new secret with the new certificate and key.
   ```bash
   kubectl create secret tls <SECRET_NAME>-new --cert=new-cert.pem --key=new-key.pem --dry-run=client -o yaml | kubectl apply -f -
   ```

2. Patch the first node's ingress-controller pod to use the new secret.
   ```bash
   kubectl set env pod/<POD_NAME_1> -n ingress-nginx TLS_SECRET=<SECRET_NAME>-new
   ```

3. Restart the first node's ingress-controller pod to load the new certificate.
   ```bash
   kubectl delete pod <POD_NAME_1> -n ingress-nginx
   ```

4. Repeat steps 2 and 3 for the second node.

5. Wait 30 seconds for the pods to become ready.
   ```bash
   kubectl wait --for=condition=ready pod <POD_NAME_1> <POD_NAME_2> -n ingress-nginx --timeout=60s
   ```

## Verify the new certificate

1. Obtain the IP address or hostname of the first node.
   ```bash
   kubectl get node <NODE_NAME_1> -o jsonpath='{.status.addresses[?(@.type=="ExternalIP")].address}'
   ```

2. Verify the certificate on the first node.
   ```bash
   echo | openssl s_client -connect <IP_OR_HOSTNAME>:443 -servername <INGRESS_HOSTNAME> | grep -A5 "subject="
   ```

3. Confirm that the certificate subject and issuer match your expectations.

4. Check that the `Not After` date matches the new certificate expiry.

5. Repeat steps 1 through 4 for the second node.

## Roll to the remaining four nodes

1. Update the ingress to point to the new secret.
   ```bash
   kubectl patch ingress <INGRESS_NAME> --type='json' -p='[{"op": "replace", "path": "/spec/tls/0/secretName", "value":"<SECRET_NAME>-new"}]'
   ```

2. Restart each of the remaining four nodes' ingress-controller pods one at a time.
   ```bash
   kubectl delete pod <POD_NAME_3> -n ingress-nginx
   kubectl wait --for=condition=ready pod <POD_NAME_3> -n ingress-nginx --timeout=60s
   ```

3. Repeat step 2 for nodes 4, 5, and 6.

4. After each restart, observe the pod logs for errors.
   ```bash
   kubectl logs <POD_NAME> -n ingress-nginx --tail=50
   ```

## Verify all nodes are running the new certificate

1. Get the IP address for each remaining node.

2. Run `openssl s_client` against each node to confirm it returns the new certificate.

3. Record the serial number of the new certificate for future reference.
   ```bash
   echo | openssl s_client -connect <IP_OR_HOSTNAME>:443 -servername <INGRESS_HOSTNAME> | openssl x509 -noout -serial
   ```

## Archive the old secret and verify cleanup

1. Rename the old secret to preserve it for rollback.
   ```bash
   kubectl patch secret <SECRET_NAME> -p '{"metadata":{"name":"<SECRET_NAME>-expired-YYYY-MM-DD"}}'
   ```

2. Confirm the new secret is in use by the ingress.
   ```bash
   kubectl get ingress <INGRESS_NAME> -o jsonpath='{.spec.tls[0].secretName}'
   ```

## Rollback procedure

If any node fails to load the new certificate or traffic errors occur, perform these steps.

1. Restore the old secret.
   ```bash
   kubectl patch secret <SECRET_NAME>-expired-YYYY-MM-DD -p '{"metadata":{"name":"<SECRET_NAME>"}}'
   ```

2. Revert the ingress to point to the old secret.
   ```bash
   kubectl patch ingress <INGRESS_NAME> --type='json' -p='[{"op": "replace", "path": "/spec/tls/0/secretName", "value":"<SECRET_NAME>"}]'
   ```

3. Restart all six ingress-controller pods in sequence to load the old certificate.

4. Verify connectivity with `openssl s_client` as described above.

## Post-completion

1. Document the expiry date of the new certificate in your team calendar or runbook.

2. Delete the new secret if rollback is no longer needed.
   ```bash
   kubectl delete secret <SECRET_NAME>-new
   ```

3. Delete the old secret after you have confirmed the new certificate is stable for at least one week.
