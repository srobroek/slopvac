# Rotate the internal ingress TLS certificate

## Scope

Use this runbook to rotate the TLS certificate across six ingress nodes.

Stage the certificate on `ingress-01` and `ingress-02` before updating the remaining four nodes.

Each ingress reload drops every open connection on that node.

## Variables

Set these values before running any command.

```bash
export INGRESS_HOST="internal.example.com"
export TLS_PORT="443"
export NEW_SECRET="/etc/internal-ingress/tls/versions/2026-09"
export SECRET_LINK="/etc/internal-ingress/tls/current"

export CANARY_NODES="ingress-01 ingress-02"
export REMAINING_NODES="ingress-03 ingress-04 ingress-05 ingress-06"
export ALL_NODES="$CANARY_NODES $REMAINING_NODES"
```

The new secret directory must contain these files:

```text
certificate.pem
private-key.pem
chain.pem
```

## Record the previous secret version

1. Read the secret target from every node.

   ```bash
   for node in $ALL_NODES; do
     printf '%s: ' "$node"
     ssh "$node" "readlink -f '$SECRET_LINK'"
   done
   ```

2. Stop if the six nodes do not reference one secret version.

3. Store the previous secret path.

   ```bash
   export PREVIOUS_SECRET="$(
     ssh ingress-01 "readlink -f '$SECRET_LINK'"
   )"
   ```

4. Confirm that the variable contains an absolute path.

   ```bash
   printf '%s\n' "$PREVIOUS_SECRET"
   ```

## Check the active certificate expiry

1. Retrieve the certificate from the ingress hostname.

   ```bash
   openssl s_client \
     -connect "${INGRESS_HOST}:${TLS_PORT}" \
     -servername "$INGRESS_HOST" \
     </dev/null 2>/dev/null |
     openssl x509 -noout -subject -issuer -serial -dates
   ```

2. Record the `notAfter` value in the incident or change record.

3. Check whether the certificate remains valid for 30 days.

   ```bash
   openssl s_client \
     -connect "${INGRESS_HOST}:${TLS_PORT}" \
     -servername "$INGRESS_HOST" \
     </dev/null 2>/dev/null |
     openssl x509 -checkend 2592000 -noout
   ```

4. Treat exit code `0` as valid beyond 30 days.

5. Treat exit code `1` as expiring within 30 days.

## Validate the new certificate

1. Inspect the new certificate.

   ```bash
   openssl x509 \
     -in certificate.pem \
     -noout \
     -subject \
     -issuer \
     -serial \
     -dates \
     -ext subjectAltName
   ```

2. Confirm that the subject alternative names contain `$INGRESS_HOST`.

3. Confirm that the `notAfter` value matches the approved certificate.

4. Compare the certificate and private-key public keys.

   ```bash
   cert_key="$(
     openssl x509 -in certificate.pem -pubkey -noout |
     openssl pkey -pubin -outform DER |
     openssl sha256
   )"

   private_key="$(
     openssl pkey -in private-key.pem -pubout -outform DER |
     openssl sha256
   )"

   test "$cert_key" = "$private_key"
   ```

5. Stop if the comparison exits with a nonzero status.

6. Verify the certificate chain.

   ```bash
   cat certificate.pem chain.pem > full-chain.pem
   openssl verify -untrusted chain.pem certificate.pem
   ```

7. Stop if `openssl verify` does not print `certificate.pem: OK`.

## Stage the certificate on two nodes

Run these steps on `ingress-01` before continuing to `ingress-02`.

1. Create the new secret directory.

   ```bash
   ssh ingress-01 "sudo install -d -m 0750 '$NEW_SECRET'"
   ```

2. Copy the certificate to the node.

   ```bash
   scp certificate.pem ingress-01:/tmp/certificate.pem
   ```

3. Copy the private key to the node.

   ```bash
   scp private-key.pem ingress-01:/tmp/private-key.pem
   ```

4. Copy the chain to the node.

   ```bash
   scp chain.pem ingress-01:/tmp/chain.pem
   ```

5. Install the certificate files.

   ```bash
   ssh ingress-01 "
     sudo install -m 0644 /tmp/certificate.pem '$NEW_SECRET/certificate.pem'
     sudo install -m 0600 /tmp/private-key.pem '$NEW_SECRET/private-key.pem'
     sudo install -m 0644 /tmp/chain.pem '$NEW_SECRET/chain.pem'
   "
   ```

6. Remove the temporary files.

   ```bash
   ssh ingress-01 \
     "rm -f /tmp/certificate.pem /tmp/private-key.pem /tmp/chain.pem"
   ```

7. Point the secret link to the new version.

   ```bash
   ssh ingress-01 \
     "sudo ln -sfn '$NEW_SECRET' '${SECRET_LINK}.next' &&
      sudo mv -Tf '${SECRET_LINK}.next' '$SECRET_LINK'"
   ```

8. Confirm that the secret link points to the new version.

   ```bash
   ssh ingress-01 "readlink -f '$SECRET_LINK'"
   ```

9. Remove the node from the load balancer.

   ```bash
   ingress-lb disable ingress-01
   ```

10. Reload the ingress service.

    ```bash
    ssh ingress-01 "sudo systemctl reload internal-ingress"
    ```

11. Confirm that the service reports `active`.

    ```bash
    ssh ingress-01 "systemctl is-active internal-ingress"
    ```

12. Verify the certificate directly against the node.

    ```bash
    openssl s_client \
      -connect "ingress-01:${TLS_PORT}" \
      -servername "$INGRESS_HOST" \
      -verify_return_error \
      </dev/null 2>/dev/null |
      openssl x509 -noout -subject -issuer -serial -dates
    ```

13. Confirm that the serial and `notAfter` values match the new certificate.

14. Return the node to the load balancer.

    ```bash
    ingress-lb enable ingress-01
    ```

15. Repeat this section with `ingress-02`.

## Verify the staged nodes

1. Verify `ingress-01` through `openssl s_client`.

   ```bash
   openssl s_client \
     -connect "ingress-01:${TLS_PORT}" \
     -servername "$INGRESS_HOST" \
     -verify_return_error \
     </dev/null 2>/dev/null |
     openssl x509 -noout -serial -dates
   ```

2. Verify `ingress-02` through `openssl s_client`.

   ```bash
   openssl s_client \
     -connect "ingress-02:${TLS_PORT}" \
     -servername "$INGRESS_HOST" \
     -verify_return_error \
     </dev/null 2>/dev/null |
     openssl x509 -noout -serial -dates
   ```

3. Confirm that both nodes present the new serial number.

4. Confirm that both commands complete without certificate verification errors.

5. Stop the rollout if either node presents the previous certificate.

6. Start the rollback if either node fails its health check.

## Roll to the remaining four nodes

Update one node at a time in this order:

1. `ingress-03`
2. `ingress-04`
3. `ingress-05`
4. `ingress-06`

For each node, set the node variable.

```bash
export NODE="ingress-03"
```

1. Create the new secret directory.

   ```bash
   ssh "$NODE" "sudo install -d -m 0750 '$NEW_SECRET'"
   ```

2. Copy the three secret files.

   ```bash
   scp certificate.pem private-key.pem chain.pem "$NODE":/tmp/
   ```

3. Install the three secret files.

   ```bash
   ssh "$NODE" "
     sudo install -m 0644 /tmp/certificate.pem '$NEW_SECRET/certificate.pem'
     sudo install -m 0600 /tmp/private-key.pem '$NEW_SECRET/private-key.pem'
     sudo install -m 0644 /tmp/chain.pem '$NEW_SECRET/chain.pem'
   "
   ```

4. Remove the temporary files.

   ```bash
   ssh "$NODE" \
     "rm -f /tmp/certificate.pem /tmp/private-key.pem /tmp/chain.pem"
   ```

5. Point the secret link to the new version.

   ```bash
   ssh "$NODE" \
     "sudo ln -sfn '$NEW_SECRET' '${SECRET_LINK}.next' &&
      sudo mv -Tf '${SECRET_LINK}.next' '$SECRET_LINK'"
   ```

6. Remove the node from the load balancer.

   ```bash
   ingress-lb disable "$NODE"
   ```

7. Reload the ingress service.

   ```bash
   ssh "$NODE" "sudo systemctl reload internal-ingress"
   ```

8. Confirm that the service reports `active`.

   ```bash
   ssh "$NODE" "systemctl is-active internal-ingress"
   ```

9. Verify the certificate directly against the node.

   ```bash
   openssl s_client \
     -connect "${NODE}:${TLS_PORT}" \
     -servername "$INGRESS_HOST" \
     -verify_return_error \
     </dev/null 2>/dev/null |
     openssl x509 -noout -serial -dates
   ```

10. Stop the rollout if the node does not present the new serial number.

11. Return the verified node to the load balancer.

    ```bash
    ingress-lb enable "$NODE"
    ```

12. Repeat these steps for the next node.

## Verify the completed rotation

1. Check the certificate on all six nodes.

   ```bash
   for node in $ALL_NODES; do
     printf '\n%s\n' "$node"
     openssl s_client \
       -connect "${node}:${TLS_PORT}" \
       -servername "$INGRESS_HOST" \
       -verify_return_error \
       </dev/null 2>/dev/null |
       openssl x509 -noout -serial -dates
   done
   ```

2. Confirm that all six nodes present one new serial number.

3. Confirm that all six nodes show the approved `notAfter` value.

4. Verify the load-balanced hostname.

   ```bash
   openssl s_client \
     -connect "${INGRESS_HOST}:${TLS_PORT}" \
     -servername "$INGRESS_HOST" \
     -verify_return_error \
     </dev/null 2>/dev/null |
     openssl x509 -noout -subject -issuer -serial -dates
   ```

5. Confirm that the hostname presents the new certificate.

6. Record the new serial number and expiry in the change record.

## Roll back

Roll back any node that fails certificate verification or its service health check.

For each affected node, set the node variable.

```bash
export NODE="ingress-01"
```

1. Remove the node from the load balancer.

   ```bash
   ingress-lb disable "$NODE"
   ```

2. Point the secret link to the previous version.

   ```bash
   ssh "$NODE" \
     "sudo ln -sfn '$PREVIOUS_SECRET' '${SECRET_LINK}.previous' &&
      sudo mv -Tf '${SECRET_LINK}.previous' '$SECRET_LINK'"
   ```

3. Confirm that the secret link points to the previous version.

   ```bash
   ssh "$NODE" "readlink -f '$SECRET_LINK'"
   ```

4. Reload the ingress service.

   ```bash
   ssh "$NODE" "sudo systemctl reload internal-ingress"
   ```

5. Confirm that the service reports `active`.

   ```bash
   ssh "$NODE" "systemctl is-active internal-ingress"
   ```

6. Verify that the node presents the previous certificate.

   ```bash
   openssl s_client \
     -connect "${NODE}:${TLS_PORT}" \
     -servername "$INGRESS_HOST" \
     -verify_return_error \
     </dev/null 2>/dev/null |
     openssl x509 -noout -serial -dates
   ```

7. Return the verified node to the load balancer.

   ```bash
   ingress-lb enable "$NODE"
   ```

8. Repeat the rollback for every node that points to `$NEW_SECRET`.

9. Verify all six nodes after a full rollback.

   ```bash
   for node in $ALL_NODES; do
     printf '\n%s\n' "$node"
     ssh "$node" "readlink -f '$SECRET_LINK'"
   done
   ```

10. Confirm that all six nodes point to `$PREVIOUS_SECRET`.
