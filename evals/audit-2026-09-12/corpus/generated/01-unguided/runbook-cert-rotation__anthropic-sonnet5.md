# Runbook: Rotating an Expiring TLS Certificate on the Internal Ingress

**Audience:** On-call engineer performing this rotation for the first time.
**Scope:** Six-node internal ingress cluster (`node1`–`node6`) fronting internal services with a shared TLS certificate.
**Estimated time:** 30–45 minutes, plus certificate issuance lead time if a new cert must be requested.

## 1. Before You Start

### 1.1 What this runbook does

You will:

1. Confirm the certificate is actually expiring and grab the replacement.
2. Stage the new certificate to two nodes only (a canary pair).
3. Verify the canary pair is serving the new certificate correctly.
4. Roll the remaining four nodes.
5. Roll back by re-pointing the certificate secret to the previous version, if anything goes wrong at any stage.

### 1.2 Impact you need to know about

**Reloading a node to pick up a new certificate drops that node's open connections.** There is no in-place hot-swap on this ingress — a reload closes existing TCP/TLS sessions on that node. Clients reconnect and land on a healthy node via the load balancer, but any long-lived connection (streaming responses, websockets, long-poll requests) terminated on the reloaded node will be cut.

This is the reason for the staged rollout:

- Only 2 of 6 nodes (≈33% of capacity) are affected during staging.
- The remaining 4 nodes absorb traffic while you verify.
- The final rollout to the last 4 nodes is done **one at a time**, not all at once, so you never drop more than 1/6 of capacity simultaneously.

If the service behind this ingress is latency-sensitive or carries long-lived connections, consider doing the rollout in a low-traffic window. This runbook does not require a maintenance window for a routine rotation, but use your judgment if traffic is unusually high.

### 1.3 Prerequisites

- SSH/exec access to `node1`–`node6`.
- Access to the secret store holding the certificate (referred to below as `<SECRET_NAME>`, with versions `<OLD_VERSION>` and `<NEW_VERSION>`).
- `openssl` available locally (for verification).
- Know the ingress hostname you'll test against — referred to below as `<HOSTNAME>`.
- Know how to reload the ingress process on a single node without restarting the whole node (e.g., a config-reload command, not a full service restart, unless your ingress requires the latter).

If you don't know the exact reload command for this ingress, find it now — do not guess mid-rotation. Check the ingress's own operational docs or ask in the on-call channel before proceeding.

---

## 2. Step 1 — Check the Certificate Expiry

Confirm there's a real, current problem before touching anything.

```bash
# Check expiry as seen from a live node (most trustworthy — this is what's actually served)
openssl s_client -connect node1:443 -servername <HOSTNAME> </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate
```

Expected output looks like:

```
notAfter=Sep 20 23:59:59 2026 GMT
```

Also check the certificate file/secret directly, to confirm the currently-deployed cert matches what's being served (it should):

```bash
openssl x509 -in <CERT_PATH> -noout -enddate -subject -issuer
```

**Sanity checks before proceeding:**

- Does the `notAfter` date match what triggered this on-call task (e.g., an expiry alert)? If the cert has plenty of validity left, stop and confirm you're looking at the right ingress/hostname before doing anything else.
- Note the current secret version (`<OLD_VERSION>`) from your secret store. You will need this exact value for rollback. Write it down now, not later.

```bash
# Example: record the current version before changing anything
secretstore describe <SECRET_NAME> | tee /tmp/cert-rotation-old-version.txt
```

## 3. Step 2 — Get the New Certificate Ready

- Confirm the new certificate/key pair (or new secret version `<NEW_VERSION>`) is already issued and available in the secret store. If it isn't, this is a separate task (certificate issuance) — do not proceed with staging until `<NEW_VERSION>` exists and is valid.
- Sanity-check the new certificate before deploying it anywhere:

```bash
openssl x509 -in <NEW_CERT_PATH> -noout -enddate -subject -issuer -checkend 86400
```

`-checkend 86400` exits non-zero if the cert is *already* within 24 hours of expiring — if that happens, you've been handed a bad/expired replacement. Stop and get a valid one.

- Confirm the new certificate's subject/SAN list matches `<HOSTNAME>` (and any other hostnames this ingress serves):

```bash
openssl x509 -in <NEW_CERT_PATH> -noout -text | grep -A1 "Subject Alternative Name"
```

## 4. Step 3 — Stage to Two Canary Nodes

Pick two nodes as canaries — `node1` and `node2` for this runbook. This limits blast radius to roughly a third of capacity while you confirm the new cert works.

For each canary node:

1. **Point that node's config at the new secret version.**

   ```bash
   # On node1
   secretstore point <SECRET_NAME> --node node1 --version <NEW_VERSION>
   ```

2. **Reload the ingress process on that node only.** This is the step that drops open connections on that node — expected and fine for one node at a time.

   ```bash
   ssh node1 'ingressctl reload'
   ```

3. **Confirm the process came back healthy** (process running, listening on the TLS port, passing its own health check) before moving to the second canary node.

   ```bash
   ssh node1 'ingressctl status'
   ```

4. Repeat steps 1–3 for `node2`.

**Do not reload `node1` and `node2` simultaneously.** Do them sequentially so you always have at least 5 of 6 nodes serving traffic while any single reload is in flight.

## 5. Step 4 — Verify the Canary Nodes with `openssl s_client`

Connect directly to each canary node (bypassing the load balancer, so you know exactly which node answered) and confirm the new certificate is being served.

```bash
openssl s_client -connect node1:443 -servername <HOSTNAME> </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -subject -issuer -fingerprint -sha256
```

Repeat for `node2`.

**Checklist — all of these must pass on both canary nodes before proceeding:**

- [ ] `-enddate` shows the new expiry date, not the old one.
- [ ] `-fingerprint -sha256` matches the fingerprint of `<NEW_CERT_PATH>` computed locally:
      ```bash
      openssl x509 -in <NEW_CERT_PATH> -noout -fingerprint -sha256
      ```
- [ ] The full TLS handshake completes without error (no `verify error`, no `handshake failure` in the `s_client` output).
- [ ] The certificate chain is complete — check for `Verify return code: 0 (ok)` at the bottom of the `s_client` output. If you see a non-zero verify code, the intermediate chain may be missing from the deployed bundle; do not proceed to the remaining nodes.
- [ ] A real request through each canary node succeeds (a simple `curl -v https://<HOSTNAME>/ --resolve <HOSTNAME>:443:<node1-ip>` or equivalent health endpoint check).

If any check fails, **do not roll to the remaining four nodes.** Go to [Section 7 — Rollback](#7-rollback-procedure) and roll back the two canary nodes, then investigate.

## 6. Step 5 — Roll to the Remaining Four Nodes

Only proceed once both canary nodes have passed every check in Section 5.

Roll `node3`, `node4`, `node5`, `node6` **one at a time**, repeating the same three-part cycle used for the canaries:

For each node in turn:

```bash
# 1. Point the node at the new version
secretstore point <SECRET_NAME> --node <node> --version <NEW_VERSION>

# 2. Reload just that node
ssh <node> 'ingressctl reload'

# 3. Confirm it's healthy before touching the next node
ssh <node> 'ingressctl status'

# 4. Quick verify (lighter check than the full canary verification —
#    the cert itself is already proven; you're just confirming this
#    node picked it up correctly)
openssl s_client -connect <node>:443 -servername <HOSTNAME> </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -fingerprint -sha256
```

Move to the next node only after the current one reports healthy and shows the new certificate. Doing them one at a time means at most one node's connections are ever dropped at once, and you catch a bad rollout after affecting only one node instead of four.

After all six nodes are on `<NEW_VERSION>`, do one final round of full verification (repeat every check from Section 5) against each of the six nodes directly, plus a check through the load balancer / normal client path to confirm end users see the new cert:

```bash
openssl s_client -connect <HOSTNAME>:443 -servername <HOSTNAME> </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -subject -fingerprint -sha256
```

Once this passes, the rotation is complete. Update the secret store's default/global pointer (if it has one separate from per-node pointers) to `<NEW_VERSION>` so future provisioning of nodes picks up the new cert automatically, and record the completion (ticket, incident channel, or your team's rotation log).

## 7. Rollback Procedure

Use this if verification fails at any point — during canary staging, during the four-node rollout, or after full rollout if a problem surfaces later.

Rollback is the same operation as the forward rotation, just pointing at `<OLD_VERSION>` instead of `<NEW_VERSION>`. Only roll back the nodes that were actually changed.

For each affected node, one at a time:

```bash
# 1. Re-point the secret to the previous version
secretstore point <SECRET_NAME> --node <node> --version <OLD_VERSION>

# 2. Reload that node (this drops its connections, same as before)
ssh <node> 'ingressctl reload'

# 3. Confirm health and that the old certificate is back
ssh <node> 'ingressctl status'
openssl s_client -connect <node>:443 -servername <HOSTNAME> </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -fingerprint -sha256
```

**Important:** `<OLD_VERSION>` is the value you recorded in Section 2 before making any changes. If you didn't record it, retrieve it from the secret store's version history — do not guess or reconstruct it from the currently-installed cert file, which may already be inconsistent across nodes mid-rollout.

After rolling back every affected node, verify all six nodes are consistently back on the old certificate (same fingerprint everywhere) before declaring rollback complete. Inconsistent state across nodes — some on old, some on new — is worse than being fully on either version, so don't stop halfway.

Once rolled back, do not retry the forward rotation until you've identified why verification failed (common causes: incomplete certificate chain/missing intermediate, mismatched private key, wrong SAN list, or a secret store propagation delay where the node read a stale value).

## 8. Quick Reference

| Stage | Nodes | Reload pattern | Verify with |
|---|---|---|---|
| Check expiry | — | — | `openssl x509 -noout -enddate` |
| Stage canary | `node1`, `node2` | Sequential, one at a time | Full `s_client` checklist (Section 5) on each |
| Roll remaining | `node3`, `node4`, `node5`, `node6` | Sequential, one at a time | Lightweight `s_client` check per node, full check at end |
| Rollback | Only affected nodes | Sequential, one at a time | Fingerprint matches `<OLD_VERSION>` on every affected node |

**Golden rule throughout:** never reload more than one node at a time. That is what keeps this rotation from turning into an outage.
