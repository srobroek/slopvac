# Runbook: Rotate an internal ingress TLS certificate

## Scope

This runbook rotates one TLS certificate across six internal ingress nodes.

Deploy the new version to two canary nodes before deploying it to the remaining four nodes.

## Service impact

> **Warning:** Reloading a node closes every open connection on that node.

Drain each node before reloading it. Reload only one node at a time.

## Required information

Record these values in the change record before starting:

| Value | Description |
|---|---|
| `INGRESS_HOST` | Hostname covered by the certificate |
| `INGRESS_PORT` | TLS port, normally `443` |
| `HEALTH_PATH` | HTTPS health endpoint |
| `CA_FILE` | Internal CA bundle path |
| `NEW_CERT_FILE` | New leaf certificate path |
| `NEW_CHAIN_FILE` | New intermediate certificate bundle path |
| `NEW_KEY_FILE` | New private key path |
| `TLS_SECRET` | Ingress TLS secret name |
| `PREVIOUS_VERSION` | Immutable secret version used before rotation |
| `NEW_VERSION` | Immutable secret version containing the new certificate |
| `ROTATION_END_UTC` | Scheduled completion timestamp |
| `DRAIN_TIMEOUT` | Approved connection drain timeout |
| `CANARY_NODE_1` | First canary node name |
| `CANARY_ADDRESS_1` | First canary node address |
| `CANARY_NODE_2` | Second canary node name |
| `CANARY_ADDRESS_2` | Second canary node address |
| `REMAINING_NODE_1` | First remaining node name |
| `REMAINING_ADDRESS_1` | First remaining node address |
| `REMAINING_NODE_2` | Second remaining node name |
| `REMAINING_ADDRESS_2` | Second remaining node address |
| `REMAINING_NODE_3` | Third remaining node name |
| `REMAINING_ADDRESS_3` | Third remaining node address |
| `REMAINING_NODE_4` | Fourth remaining node name |
| `REMAINING_ADDRESS_4` | Fourth remaining node address |

Record the exact service commands for these operations:

| Operation | Required result |
|---|---|
| `GET_POINTER <node>` | Print the TLS secret version referenced by one node |
| `DRAIN <node>` | Remove one node from ingress traffic |
| `CONNECTION_COUNT <node>` | Print the number of open connections |
| `POINT <node> <version>` | Point one node at an immutable TLS secret version |
| `RELOAD <node>` | Reload the ingress process on one node |
| `HEALTH <node>` | Print the node health state |
| `UNDRAIN <node>` | Return one node to ingress traffic |
| `ALERTS` | Print firing alerts for the ingress service |

Do not start without an exact command for each operation.

## Preconditions

- Confirm that all six nodes report a healthy state.
- Confirm that the load balancer can drain one node.
- Confirm that the operator account can update the TLS secret pointer.
- Confirm that the operator account can reload each ingress node.
- Confirm that `PREVIOUS_VERSION` remains available throughout the rotation.
- Confirm that the change record identifies the ingress service owner.
- Confirm that the change record identifies an escalation contact.
- If draining is unavailable, use an approved outage window before reloading any node.

## Prepare the shell

Export the recorded values:

```bash
export INGRESS_HOST='ingress.internal.example'
export INGRESS_PORT='443'
export HEALTH_PATH='/health'
export CA_FILE='/secure/path/internal-ca-bundle.pem'

export NEW_CERT_FILE='/secure/path/new-tls.crt'
export NEW_CHAIN_FILE='/secure/path/new-chain.crt'
export NEW_KEY_FILE='/secure/path/new-tls.key'

export TLS_SECRET='internal-ingress-tls'
export PREVIOUS_VERSION='previous-version'
export NEW_VERSION='new-version'
export ROTATION_END_UTC='YYYY-MM-DDTHH:MM:SSZ'
export DRAIN_TIMEOUT='service-approved-timeout'

export CANARY_NODE_1='node-name'
export CANARY_ADDRESS_1='node-address'
export CANARY_NODE_2='node-name'
export CANARY_ADDRESS_2='node-address'

export REMAINING_NODE_1='node-name'
export REMAINING_ADDRESS_1='node-address'
export REMAINING_NODE_2='node-name'
export REMAINING_ADDRESS_2='node-address'
export REMAINING_NODE_3='node-name'
export REMAINING_ADDRESS_3='node-address'
export REMAINING_NODE_4='node-name'
export REMAINING_ADDRESS_4='node-address'
```

## Inspect the certificate files

1. Print the new certificate identity and validity period.

   ```bash
   openssl x509 \
     -in "$NEW_CERT_FILE" \
     -noout \
     -subject \
     -issuer \
     -serial \
     -startdate \
     -enddate \
     -ext subjectAltName
   ```

2. Confirm that the new certificate is valid at execution time.

   ```bash
   openssl x509 -in "$NEW_CERT_FILE" -noout -checkend 0
   ```

3. Confirm that the command exits with status `0`.

4. Confirm that `notAfter` falls after `ROTATION_END_UTC`.

5. Verify the certificate hostname and chain.

   ```bash
   openssl verify \
     -CAfile "$CA_FILE" \
     -untrusted "$NEW_CHAIN_FILE" \
     -verify_hostname "$INGRESS_HOST" \
     "$NEW_CERT_FILE"
   ```

6. Confirm that the output ends with `OK`.

7. Compare the certificate and private-key public keys.

   ```bash
   cert_key_sha256="$(
     openssl x509 -in "$NEW_CERT_FILE" -pubkey -noout |
     openssl pkey -pubin -outform DER |
     openssl dgst -sha256
   )"

   private_key_sha256="$(
     openssl pkey -in "$NEW_KEY_FILE" -pubout -outform DER |
     openssl dgst -sha256
   )"

   printf 'Certificate: %s\nPrivate key: %s\n' \
     "$cert_key_sha256" \
     "$private_key_sha256"

   test "$cert_key_sha256" = "$private_key_sha256"
   ```

8. Confirm that `test` exits with status `0`.

9. Record the new certificate serial number.

   ```bash
   export NEW_SERIAL="$(
     openssl x509 -in "$NEW_CERT_FILE" -noout -serial |
     cut -d= -f2 |
     tr '[:lower:]' '[:upper:]'
   )"

   printf '%s\n' "$NEW_SERIAL"
   ```

## Define the node verification function

Run this function in the prepared shell:

```bash
verify_node() {
  local node_name="$1"
  local node_address="$2"
  local expected_serial="$3"
  local certificate_file
  local verification_log
  local actual_serial

  certificate_file="$(mktemp)"
  verification_log="$(mktemp)"

  if ! openssl s_client \
    -connect "${node_address}:${INGRESS_PORT}" \
    -servername "$INGRESS_HOST" \
    -verify_hostname "$INGRESS_HOST" \
    -verify_return_error \
    -CAfile "$CA_FILE" \
    </dev/null >"$verification_log" 2>&1
  then
    cat "$verification_log"
    rm -f "$certificate_file" "$verification_log"
    return 1
  fi

  if ! grep -Fq 'Verify return code: 0 (ok)' "$verification_log"
  then
    cat "$verification_log"
    rm -f "$certificate_file" "$verification_log"
    return 1
  fi

  openssl s_client \
    -connect "${node_address}:${INGRESS_PORT}" \
    -servername "$INGRESS_HOST" \
    -showcerts \
    </dev/null 2>/dev/null |
  awk '
    /-----BEGIN CERTIFICATE-----/ { capture=1 }
    capture { print }
    /-----END CERTIFICATE-----/ { exit }
  ' >"$certificate_file"

  if ! test -s "$certificate_file"
  then
    rm -f "$certificate_file" "$verification_log"
    return 1
  fi

  actual_serial="$(
    openssl x509 -in "$certificate_file" -noout -serial |
    cut -d= -f2 |
    tr '[:lower:]' '[:upper:]'
  )"

  openssl x509 \
    -in "$certificate_file" \
    -noout \
    -subject \
    -issuer \
    -serial \
    -startdate \
    -enddate

  if ! test "$actual_serial" = "$expected_serial"
  then
    printf 'Expected serial: %s\nActual serial: %s\n' \
      "$expected_serial" \
      "$actual_serial"
    rm -f "$certificate_file" "$verification_log"
    return 1
  fi

  if ! openssl x509 -in "$certificate_file" -noout -checkend 0
  then
    rm -f "$certificate_file" "$verification_log"
    return 1
  fi

  printf '%s passed TLS verification.\n' "$node_name"
  rm -f "$certificate_file" "$verification_log"
}
```

The function checks the certificate chain, hostname, serial number, and expiry.

## Check the served certificate expiry

1. Retrieve the certificate from the load-balanced endpoint.

   ```bash
   openssl s_client \
     -connect "${INGRESS_HOST}:${INGRESS_PORT}" \
     -servername "$INGRESS_HOST" \
     -showcerts \
     </dev/null 2>/dev/null |
   awk '
     /-----BEGIN CERTIFICATE-----/ { capture=1 }
     capture { print }
     /-----END CERTIFICATE-----/ { exit }
   ' > /tmp/ingress-before-rotation.pem
   ```

2. Print the served certificate expiry and serial number.

   ```bash
   openssl x509 \
     -in /tmp/ingress-before-rotation.pem \
     -noout \
     -serial \
     -startdate \
     -enddate
   ```

3. Record `notAfter` in the change record.

4. Record the previous certificate serial number.

   ```bash
   export PREVIOUS_SERIAL="$(
     openssl x509 \
       -in /tmp/ingress-before-rotation.pem \
       -noout \
       -serial |
     cut -d= -f2 |
     tr '[:lower:]' '[:upper:]'
   )"

   printf '%s\n' "$PREVIOUS_SERIAL"
   ```

5. Verify the previous certificate on each canary node.

   ```bash
   verify_node "$CANARY_NODE_1" "$CANARY_ADDRESS_1" "$PREVIOUS_SERIAL"
   verify_node "$CANARY_NODE_2" "$CANARY_ADDRESS_2" "$PREVIOUS_SERIAL"
   ```

6. Verify the previous certificate on each remaining node.

   ```bash
   verify_node "$REMAINING_NODE_1" "$REMAINING_ADDRESS_1" "$PREVIOUS_SERIAL"
   verify_node "$REMAINING_NODE_2" "$REMAINING_ADDRESS_2" "$PREVIOUS_SERIAL"
   verify_node "$REMAINING_NODE_3" "$REMAINING_ADDRESS_3" "$PREVIOUS_SERIAL"
   verify_node "$REMAINING_NODE_4" "$REMAINING_ADDRESS_4" "$PREVIOUS_SERIAL"
   ```

7. Stop the rotation if any node serves a different serial number.

## Rotate one node

Apply this procedure to one node before starting another node.

1. Run the mapped `HEALTH` command for the node.

2. Stop if the node does not report a healthy state.

3. Run the mapped `GET_POINTER` command for the node.

4. Confirm that the pointer matches the expected pre-rotation version.

5. Run the mapped `DRAIN` command for the node.

6. Poll the mapped `CONNECTION_COUNT` command until it reports `0`.

7. If `DRAIN_TIMEOUT` expires above `0`, run the mapped `UNDRAIN` command.

8. If `DRAIN_TIMEOUT` expires above `0`, stop the rotation.

9. Run the mapped `POINT` command with `NEW_VERSION`.

10. Run the mapped `GET_POINTER` command for the node.

11. Confirm that the pointer matches `NEW_VERSION`.

12. Run the mapped `RELOAD` command for the node.

13. Run the mapped `HEALTH` command for the node.

14. Run the node verification function with `NEW_SERIAL`.

    ```bash
    verify_node "$NODE_NAME" "$NODE_ADDRESS" "$NEW_SERIAL"
    ```

15. If verification fails, keep the node drained.

16. If verification fails, start the rollback procedure.

17. Run the mapped `UNDRAIN` command after verification passes.

18. Run the mapped `HEALTH` command after returning the node to traffic.

19. Record the pointer, serial number, expiry, and reload timestamp.

## Stage the two canary nodes

1. Set the node variables for the first canary node.

   ```bash
   export NODE_NAME="$CANARY_NODE_1"
   export NODE_ADDRESS="$CANARY_ADDRESS_1"
   ```

2. Apply the **Rotate one node** procedure.

3. Set the node variables for the second canary node.

   ```bash
   export NODE_NAME="$CANARY_NODE_2"
   export NODE_ADDRESS="$CANARY_ADDRESS_2"
   ```

4. Apply the **Rotate one node** procedure.

5. Verify both canary nodes again.

   ```bash
   verify_node "$CANARY_NODE_1" "$CANARY_ADDRESS_1" "$NEW_SERIAL"
   verify_node "$CANARY_NODE_2" "$CANARY_ADDRESS_2" "$NEW_SERIAL"
   ```

6. Run ten HTTPS requests through the load-balanced endpoint.

   ```bash
   for request in {1..10}; do
     curl \
       --fail \
       --silent \
       --show-error \
       --cacert "$CA_FILE" \
       "https://${INGRESS_HOST}:${INGRESS_PORT}${HEALTH_PATH}" \
       >/dev/null || exit 1
   done
   ```

7. Monitor the mapped `ALERTS` command for 10 minutes.

8. Confirm that no ingress TLS alert enters a firing state.

9. Confirm that no ingress availability alert enters a firing state.

10. If any canary check fails, start the rollback procedure.

## Rotate the remaining four nodes

Rotate the remaining nodes in the listed order.

1. Set the variables for the first remaining node.

   ```bash
   export NODE_NAME="$REMAINING_NODE_1"
   export NODE_ADDRESS="$REMAINING_ADDRESS_1"
   ```

2. Apply the **Rotate one node** procedure.

3. Set the variables for the second remaining node.

   ```bash
   export NODE_NAME="$REMAINING_NODE_2"
   export NODE_ADDRESS="$REMAINING_ADDRESS_2"
   ```

4. Apply the **Rotate one node** procedure.

5. Set the variables for the third remaining node.

   ```bash
   export NODE_NAME="$REMAINING_NODE_3"
   export NODE_ADDRESS="$REMAINING_ADDRESS_3"
   ```

6. Apply the **Rotate one node** procedure.

7. Set the variables for the fourth remaining node.

   ```bash
   export NODE_NAME="$REMAINING_NODE_4"
   export NODE_ADDRESS="$REMAINING_ADDRESS_4"
   ```

8. Apply the **Rotate one node** procedure.

## Verify the completed rotation

1. Verify the new certificate on all six nodes.

   ```bash
   verify_node "$CANARY_NODE_1" "$CANARY_ADDRESS_1" "$NEW_SERIAL"
   verify_node "$CANARY_NODE_2" "$CANARY_ADDRESS_2" "$NEW_SERIAL"
   verify_node "$REMAINING_NODE_1" "$REMAINING_ADDRESS_1" "$NEW_SERIAL"
   verify_node "$REMAINING_NODE_2" "$REMAINING_ADDRESS_2" "$NEW_SERIAL"
   verify_node "$REMAINING_NODE_3" "$REMAINING_ADDRESS_3" "$NEW_SERIAL"
   verify_node "$REMAINING_NODE_4" "$REMAINING_ADDRESS_4" "$NEW_SERIAL"
   ```

2. Verify the new certificate through the load-balanced endpoint.

   ```bash
   verify_node "load-balanced endpoint" "$INGRESS_HOST" "$NEW_SERIAL"
   ```

3. Run ten HTTPS requests through the load-balanced endpoint.

   ```bash
   for request in {1..10}; do
     curl \
       --fail \
       --silent \
       --show-error \
       --cacert "$CA_FILE" \
       "https://${INGRESS_HOST}:${INGRESS_PORT}${HEALTH_PATH}" \
       >/dev/null || exit 1
   done
   ```

4. Run the mapped `GET_POINTER` command for each node.

5. Confirm that all six pointers match `NEW_VERSION`.

6. Run the mapped `HEALTH` command for each node.

7. Confirm that all six nodes report a healthy state.

8. Run the mapped `ALERTS` command.

9. Confirm that no ingress TLS or availability alert is firing.

10. Record the completion timestamp in the change record.

11. Do not delete `PREVIOUS_VERSION` during this procedure.

## Rollback triggers

Start rollback after any of these results:

- `openssl s_client` reports a verification error.
- A node serves a serial number other than `NEW_SERIAL`.
- A node serves an expired certificate.
- The certificate does not cover `INGRESS_HOST`.
- The new secret pointer does not survive a reload.
- An ingress TLS alert enters a firing state.
- An ingress availability alert enters a firing state.
- A reloaded node does not return to a healthy state.

## Roll back one node

> **Warning:** Rollback reloads also close every open connection on the affected node.

1. Run the mapped `DRAIN` command unless the node remains drained.

2. Poll the mapped `CONNECTION_COUNT` command until it reports `0`.

3. If `DRAIN_TIMEOUT` expires above `0`, keep the node drained.

4. If `DRAIN_TIMEOUT` expires above `0`, page the ingress service owner.

5. Run the mapped `POINT` command with `PREVIOUS_VERSION`.

6. Run the mapped `GET_POINTER` command for the node.

7. Confirm that the pointer matches `PREVIOUS_VERSION`.

8. Run the mapped `RELOAD` command for the node.

9. Run the mapped `HEALTH` command for the node.

10. Verify the previous certificate with `openssl s_client`.

    ```bash
    verify_node "$NODE_NAME" "$NODE_ADDRESS" "$PREVIOUS_SERIAL"
    ```

11. If verification fails, keep the node drained.

12. If verification fails, page the ingress service owner.

13. Run the mapped `UNDRAIN` command after verification passes.

14. Record the rollback timestamp and result.

## Rollback sequence

1. Confirm that the previous certificate remains unexpired.

   ```bash
   openssl x509 \
     -in /tmp/ingress-before-rotation.pem \
     -noout \
     -checkend 0
   ```

2. If the previous certificate is expired, keep the failed node drained.

3. If the previous certificate is expired, page the ingress service owner.

4. Identify every node whose pointer matches `NEW_VERSION`.

5. Roll back each identified node in reverse deployment order.

6. Apply the **Roll back one node** procedure to only one node at a time.

7. Verify the previous certificate on all six nodes after rollback.

   ```bash
   verify_node "$CANARY_NODE_1" "$CANARY_ADDRESS_1" "$PREVIOUS_SERIAL"
   verify_node "$CANARY_NODE_2" "$CANARY_ADDRESS_2" "$PREVIOUS_SERIAL"
   verify_node "$REMAINING_NODE_1" "$REMAINING_ADDRESS_1" "$PREVIOUS_SERIAL"
   verify_node "$REMAINING_NODE_2" "$REMAINING_ADDRESS_2" "$PREVIOUS_SERIAL"
   verify_node "$REMAINING_NODE_3" "$REMAINING_ADDRESS_3" "$PREVIOUS_SERIAL"
   verify_node "$REMAINING_NODE_4" "$REMAINING_ADDRESS_4" "$PREVIOUS_SERIAL"
   ```

8. Verify the previous certificate through the load-balanced endpoint.

   ```bash
   verify_node "load-balanced endpoint" "$INGRESS_HOST" "$PREVIOUS_SERIAL"
   ```

9. Run the mapped `GET_POINTER` command for each node.

10. Confirm that all six pointers match `PREVIOUS_VERSION`.

11. Run the mapped `ALERTS` command.

12. Record the rollback result in the change record.

## Rotation record

Complete one row after processing each node:

| Node | Group | Pointer before | Pointer after | Serial after | `notAfter` | Reload UTC | Verification |
|---|---|---|---|---|---|---|---|
| 1 | Canary |  |  |  |  |  |  |
| 2 | Canary |  |  |  |  |  |  |
| 3 | Remaining |  |  |  |  |  |  |
| 4 | Remaining |  |  |  |  |  |  |
| 5 | Remaining |  |  |  |  |  |  |
| 6 | Remaining |  |  |  |  |  |  |
