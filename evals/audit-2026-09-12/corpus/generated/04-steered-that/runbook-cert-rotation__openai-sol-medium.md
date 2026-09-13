# Rotate an internal ingress TLS certificate

## Scope

Use this runbook to rotate one TLS certificate across six internal ingress nodes.

Deploy the new secret version to two canary nodes before updating the remaining four nodes.

Reloading a node terminates its open connections.

## Required values

Replace each angle-bracketed value before running a command.

| Value | Description |
|---|---|
| `<tls-hostname>` | Hostname listed in the certificate |
| `<port>` | TLS listener port |
| `<ca-file>` | PEM file containing the trusted internal certificate authority |
| `<new-certificate-file>` | PEM file containing the new leaf certificate |
| `<new-private-key-file>` | PEM file containing the new private key |
| `<new-secret-version>` | Secret version containing the new certificate and private key |
| `<node-1>` through `<node-6>` | Six ingress node names |
| `<node-1-ip>` through `<node-6-ip>` | Direct addresses for the six nodes |
| `<minimum-days>` | Required remaining lifetime for the new certificate |
| `<drain-timeout-seconds>` | Approved maximum wait for open connections to reach zero |
| `<drain-poll-interval-seconds>` | Approved delay between connection-count checks |
| `<secret-pointer-command>` | Platform command that changes one node’s secret version |
| `<secret-query-command>` | Platform command that reports one node’s secret version |
| `<drain-command>` | Platform command that removes one node from service |
| `<connection-count-command>` | Platform command that prints one nonnegative integer |
| `<reload-command>` | Platform command that reloads one node |
| `<health-command>` | Platform command that checks one node’s health |
| `<restore-command>` | Platform command that returns one node to service |

Assign `<node-1>` and `<node-2>` as the canary nodes.

Assign `<node-3>` through `<node-6>` as the remaining nodes.

## Rollout stop conditions

These stop conditions apply while deploying `<new-secret-version>`.

Stop the rollout and begin rollback when one condition occurs:

- A node retains open connections for `<drain-timeout-seconds>`.
- A platform command exits with a nonzero status.
- `openssl s_client` reports a certificate verification error.
- A changed node presents a fingerprint other than `NEW_FINGERPRINT`.
- A changed node presents a certificate for a hostname other than `<tls-hostname>`.
- A changed node fails `<health-command>` after the reload.
- The internal ingress fails a TLS request after a node returns to service.

## Set the operating values

```bash
TLS_HOST='<tls-hostname>'
TLS_PORT='<port>'
CA_FILE='<ca-file>'
NEW_CERTIFICATE_FILE='<new-certificate-file>'
NEW_PRIVATE_KEY_FILE='<new-private-key-file>'
NEW_SECRET_VERSION='<new-secret-version>'
DRAIN_TIMEOUT_SECONDS='<drain-timeout-seconds>'
DRAIN_POLL_INTERVAL_SECONDS='<drain-poll-interval-seconds>'
```

Confirm that both drain values contain positive integers:

```bash
case "${DRAIN_TIMEOUT_SECONDS}" in
  ''|*[!0-9]*|0)
    printf 'Invalid drain timeout: %s\n' "${DRAIN_TIMEOUT_SECONDS}" >&2
    return 1 2>/dev/null || exit 1
    ;;
esac

case "${DRAIN_POLL_INTERVAL_SECONDS}" in
  ''|*[!0-9]*|0)
    printf 'Invalid poll interval: %s\n' \
      "${DRAIN_POLL_INTERVAL_SECONDS}" >&2
    return 1 2>/dev/null || exit 1
    ;;
esac

test "${DRAIN_POLL_INTERVAL_SECONDS}" -le "${DRAIN_TIMEOUT_SECONDS}"
```

## Check the deployed certificate expiry

Run this command through the internal ingress address:

```bash
openssl s_client \
  -connect "${TLS_HOST}:${TLS_PORT}" \
  -servername "${TLS_HOST}" \
  </dev/null 2>/dev/null |
openssl x509 \
  -noout \
  -subject \
  -issuer \
  -serial \
  -dates \
  -fingerprint \
  -sha256
```

Record the `notAfter` value, serial number, and SHA-256 fingerprint.

## Validate the new certificate

Check the hostname:

```bash
openssl x509 \
  -in "${NEW_CERTIFICATE_FILE}" \
  -noout \
  -checkhost "${TLS_HOST}"
```

Check the remaining lifetime:

```bash
MINIMUM_DAYS='<minimum-days>'
MINIMUM_SECONDS=$((MINIMUM_DAYS * 24 * 60 * 60))

openssl x509 \
  -in "${NEW_CERTIFICATE_FILE}" \
  -noout \
  -checkend "${MINIMUM_SECONDS}"
```

Continue only when both commands exit with status `0`.

Calculate the certificate public-key hash:

```bash
openssl x509 \
  -in "${NEW_CERTIFICATE_FILE}" \
  -pubkey \
  -noout |
openssl pkey \
  -pubin \
  -outform DER |
openssl dgst -sha256
```

Calculate the private-key public-key hash:

```bash
openssl pkey \
  -in "${NEW_PRIVATE_KEY_FILE}" \
  -pubout \
  -outform DER |
openssl dgst -sha256
```

Continue only when both hashes match.

Do not copy private-key contents into the change record.

Record the new certificate fingerprint:

```bash
NEW_FINGERPRINT=$(
  openssl x509 \
    -in "${NEW_CERTIFICATE_FILE}" \
    -noout \
    -fingerprint \
    -sha256 |
  cut -d= -f2-
)

printf 'New fingerprint: %s\n' "${NEW_FINGERPRINT}"
```

## Record each node’s previous state

Complete this section before changing any secret pointer.

Enable pipeline failure detection:

```bash
set -o pipefail
```

Define a function that verifies one node and returns its fingerprint:

```bash
get_node_fingerprint() {
  local node_ip="$1"
  local output_file
  local leaf_file
  local fingerprint

  output_file="$(mktemp)"
  leaf_file="$(mktemp)"

  if ! openssl s_client \
    -connect "${node_ip}:${TLS_PORT}" \
    -servername "${TLS_HOST}" \
    -verify_hostname "${TLS_HOST}" \
    -verify_return_error \
    -showcerts \
    -CAfile "${CA_FILE}" \
    </dev/null >"${output_file}" 2>&1
  then
    printf 'TLS verification failed for %s\n' "${node_ip}" >&2
    cat "${output_file}" >&2
    rm -f "${output_file}" "${leaf_file}"
    return 1
  fi

  awk '
    /-----BEGIN CERTIFICATE-----/ { capture = 1 }
    capture { print }
    /-----END CERTIFICATE-----/ { exit }
  ' "${output_file}" >"${leaf_file}"

  if ! fingerprint=$(
    openssl x509 \
      -in "${leaf_file}" \
      -noout \
      -fingerprint \
      -sha256 |
    cut -d= -f2-
  )
  then
    printf 'Certificate inspection failed for %s\n' "${node_ip}" >&2
    rm -f "${output_file}" "${leaf_file}"
    return 1
  fi

  rm -f "${output_file}" "${leaf_file}"

  if [ -z "${fingerprint}" ]
  then
    printf 'Certificate fingerprint is empty for %s\n' "${node_ip}" >&2
    return 1
  fi

  printf '%s\n' "${fingerprint}"
}
```

Capture each fingerprint and check every function status:

```bash
if ! PREVIOUS_NODE_1_FINGERPRINT=$(get_node_fingerprint '<node-1-ip>')
then
  printf 'Stop: verification failed for <node-1>\n' >&2
  return 1 2>/dev/null || exit 1
fi

if ! PREVIOUS_NODE_2_FINGERPRINT=$(get_node_fingerprint '<node-2-ip>')
then
  printf 'Stop: verification failed for <node-2>\n' >&2
  return 1 2>/dev/null || exit 1
fi

if ! PREVIOUS_NODE_3_FINGERPRINT=$(get_node_fingerprint '<node-3-ip>')
then
  printf 'Stop: verification failed for <node-3>\n' >&2
  return 1 2>/dev/null || exit 1
fi

if ! PREVIOUS_NODE_4_FINGERPRINT=$(get_node_fingerprint '<node-4-ip>')
then
  printf 'Stop: verification failed for <node-4>\n' >&2
  return 1 2>/dev/null || exit 1
fi

if ! PREVIOUS_NODE_5_FINGERPRINT=$(get_node_fingerprint '<node-5-ip>')
then
  printf 'Stop: verification failed for <node-5>\n' >&2
  return 1 2>/dev/null || exit 1
fi

if ! PREVIOUS_NODE_6_FINGERPRINT=$(get_node_fingerprint '<node-6-ip>')
then
  printf 'Stop: verification failed for <node-6>\n' >&2
  return 1 2>/dev/null || exit 1
fi
```

Confirm that the six fingerprints match:

```bash
test "${PREVIOUS_NODE_1_FINGERPRINT}" = "${PREVIOUS_NODE_2_FINGERPRINT}" &&
test "${PREVIOUS_NODE_1_FINGERPRINT}" = "${PREVIOUS_NODE_3_FINGERPRINT}" &&
test "${PREVIOUS_NODE_1_FINGERPRINT}" = "${PREVIOUS_NODE_4_FINGERPRINT}" &&
test "${PREVIOUS_NODE_1_FINGERPRINT}" = "${PREVIOUS_NODE_5_FINGERPRINT}" &&
test "${PREVIOUS_NODE_1_FINGERPRINT}" = "${PREVIOUS_NODE_6_FINGERPRINT}"
```

Stop if the comparison exits with a nonzero status.

Run `<secret-query-command>` separately for each node.

Record the results before changing any pointer:

| Node | Group | Previous secret version | Previous SHA-256 fingerprint |
|---|---|---|---|
| `<node-1>` | Canary |  | `${PREVIOUS_NODE_1_FINGERPRINT}` |
| `<node-2>` | Canary |  | `${PREVIOUS_NODE_2_FINGERPRINT}` |
| `<node-3>` | Remaining |  | `${PREVIOUS_NODE_3_FINGERPRINT}` |
| `<node-4>` | Remaining |  | `${PREVIOUS_NODE_4_FINGERPRINT}` |
| `<node-5>` | Remaining |  | `${PREVIOUS_NODE_5_FINGERPRINT}` |
| `<node-6>` | Remaining |  | `${PREVIOUS_NODE_6_FINGERPRINT}` |

Confirm that the table contains six secret versions and six fingerprints.

Confirm that `${NEW_SECRET_VERSION}` exists before draining `<node-1>`.

## Define the drain functions

Replace the placeholder inside `connection_count` with the platform command.

The platform command must print only one nonnegative integer.

```bash
connection_count() {
  local node_name="$1"

  <connection-count-command> "${node_name}"
}
```

Define the bounded polling function:

```bash
wait_for_zero_connections() {
  local node_name="$1"
  local deadline
  local checked_at
  local count

  deadline=$(($(date +%s) + DRAIN_TIMEOUT_SECONDS))

  while true
  do
    if ! count=$(connection_count "${node_name}")
    then
      printf 'Connection-count command failed for %s\n' "${node_name}" >&2
      return 2
    fi

    case "${count}" in
      ''|*[!0-9]*)
        printf 'Invalid connection count for %s: %s\n' \
          "${node_name}" "${count}" >&2
        return 2
        ;;
    esac

    printf '%s open connections on %s\n' "${count}" "${node_name}"

    if [ "${count}" -eq 0 ]
    then
      return 0
    fi

    checked_at=$(date +%s)

    if [ "${checked_at}" -ge "${deadline}" ]
    then
      printf 'Drain timeout reached for %s after %s seconds\n' \
        "${node_name}" "${DRAIN_TIMEOUT_SECONDS}" >&2
      return 1
    fi

    sleep "${DRAIN_POLL_INTERVAL_SECONDS}"
  done
}
```

## Handle a rollout drain failure

The rollout changes a secret pointer only after the node reaches zero connections.

If `wait_for_zero_connections` fails:

1. Do not change the timed-out node’s secret pointer.
2. Do not reload the timed-out node.
3. Run `<restore-command>` for the timed-out node.
4. Stop deploying `${NEW_SECRET_VERSION}`.
5. Roll back every node already changed during this rollout.
6. Record the node, last connection count, and timeout.
7. Escalate according to the ingress service procedure.

## Define the node verification function

The function accepts a node IP address and an expected fingerprint.

```bash
verify_node() {
  local node_ip="$1"
  local expected_fingerprint="$2"
  local actual_fingerprint

  if ! actual_fingerprint=$(get_node_fingerprint "${node_ip}")
  then
    return 1
  fi

  printf 'Expected fingerprint: %s\n' "${expected_fingerprint}"
  printf 'Actual fingerprint:   %s\n' "${actual_fingerprint}"

  test "${actual_fingerprint}" = "${expected_fingerprint}"
}
```

Use `NEW_FINGERPRINT` as the expected fingerprint during rollout.

Use the recorded per-node fingerprint during rollback.

## Deploy to the two canary nodes

Process these assignments in order:

```bash
NODE_NAME='<node-1>'
NODE_IP='<node-1-ip>'
```

```bash
NODE_NAME='<node-2>'
NODE_IP='<node-2-ip>'
```

For each assignment:

1. Run `<drain-command>` with `"${NODE_NAME}"`.
2. Run `wait_for_zero_connections "${NODE_NAME}"`.
3. Apply the rollout drain-failure procedure when the function fails.
4. Run `<secret-pointer-command>` with `"${NODE_NAME}"` and `${NEW_SECRET_VERSION}`.
5. Run `<secret-query-command>` with `"${NODE_NAME}"`.
6. Confirm that the reported version equals `${NEW_SECRET_VERSION}`.
7. Run `<reload-command>` with `"${NODE_NAME}"`.
8. Run `verify_node "${NODE_IP}" "${NEW_FINGERPRINT}"`.
9. Run `<health-command>` with `"${NODE_NAME}"`.
10. Run `<restore-command>` with `"${NODE_NAME}"`.
11. Send one TLS request through the internal ingress address.
12. Record the node, secret version, fingerprint, and completion time.

Complete `<node-1>` before starting `<node-2>`.

Stop if either canary node fails a check.

Confirm that both canary nodes remain in service before starting `<node-3>`.

## Deploy to the remaining four nodes

Process these assignments in order:

```bash
NODE_NAME='<node-3>'
NODE_IP='<node-3-ip>'
```

```bash
NODE_NAME='<node-4>'
NODE_IP='<node-4-ip>'
```

```bash
NODE_NAME='<node-5>'
NODE_IP='<node-5-ip>'
```

```bash
NODE_NAME='<node-6>'
NODE_IP='<node-6-ip>'
```

For each assignment, complete the rollout procedure before using the next assignment.

Keep five nodes in service while reloading one remaining node.

## Verify all six nodes

Verify each node against the new fingerprint:

```bash
verify_node '<node-1-ip>' "${NEW_FINGERPRINT}"
verify_node '<node-2-ip>' "${NEW_FINGERPRINT}"
verify_node '<node-3-ip>' "${NEW_FINGERPRINT}"
verify_node '<node-4-ip>' "${NEW_FINGERPRINT}"
verify_node '<node-5-ip>' "${NEW_FINGERPRINT}"
verify_node '<node-6-ip>' "${NEW_FINGERPRINT}"
```

Confirm that all six commands exit with status `0`.

Confirm that every node points to `${NEW_SECRET_VERSION}`.

Run `<health-command>` for all six nodes.

Run the expiry check through the internal ingress address.

Record the final serial number, fingerprint, and `notAfter` value.

## Roll back

Roll back every node that points to `${NEW_SECRET_VERSION}`.

Process changed nodes in reverse deployment order.

Use the corresponding values from this table:

| Node | Address | Expected rollback fingerprint |
|---|---|---|
| `<node-6>` | `<node-6-ip>` | `${PREVIOUS_NODE_6_FINGERPRINT}` |
| `<node-5>` | `<node-5-ip>` | `${PREVIOUS_NODE_5_FINGERPRINT}` |
| `<node-4>` | `<node-4-ip>` | `${PREVIOUS_NODE_4_FINGERPRINT}` |
| `<node-3>` | `<node-3-ip>` | `${PREVIOUS_NODE_3_FINGERPRINT}` |
| `<node-2>` | `<node-2-ip>` | `${PREVIOUS_NODE_2_FINGERPRINT}` |
| `<node-1>` | `<node-1-ip>` | `${PREVIOUS_NODE_1_FINGERPRINT}` |

For each changed node:

1. Set `NODE_NAME` to the corresponding node name.
2. Set `NODE_IP` to the corresponding node address.
3. Set `PREVIOUS_FINGERPRINT` to the corresponding recorded fingerprint.
4. Read the node’s previous secret version from the change record.
5. Run `<drain-command>` with `"${NODE_NAME}"`.
6. Run `wait_for_zero_connections "${NODE_NAME}"`.
7. Keep the node drained when the function fails.
8. Do not change the node’s secret pointer when the function fails.
9. Escalate a failed drain according to the ingress service procedure.
10. Run `<secret-pointer-command>` with `"${NODE_NAME}"` and the previous version.
11. Run `<secret-query-command>` with `"${NODE_NAME}"`.
12. Confirm that the reported version equals the recorded previous version.
13. Run `<reload-command>` with `"${NODE_NAME}"`.
14. Run `verify_node "${NODE_IP}" "${PREVIOUS_FINGERPRINT}"`.
15. Run `<health-command>` with `"${NODE_NAME}"`.
16. Run `<restore-command>` with `"${NODE_NAME}"`.
17. Send one TLS request through the internal ingress address.
18. Record the rollback result and completion time.

Keep a node drained when its rollback verification fails.

Escalate the failed verification according to the ingress service procedure.

After rollback, verify each restored node against its recorded previous fingerprint.

Do not use `NEW_FINGERPRINT` for rollback verification.
