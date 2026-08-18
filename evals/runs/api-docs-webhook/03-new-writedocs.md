# Webhook delivery

The delivery service sends each event to the endpoint URL you register. Every delivery is an HTTP POST with a JSON body and an HMAC-SHA256 signature header.

Deliveries are at-least-once. The same event can arrive more than once, so your receiver must be idempotent. Deduplicate on the `id` field of the body.

## Request

```http
POST /your/endpoint HTTP/1.1
Host: receiver.example.com
Content-Type: application/json
User-Agent: Deliveries/1.0
X-Webhook-Id: 4f2a1c90-3f5e-4c1b-9f77-2b0e8a6d1c33
X-Webhook-Event: invoice.paid
X-Webhook-Timestamp: 1770000000
X-Webhook-Attempt: 1
X-Webhook-Signature: v1=6c1f...9ab2
Content-Length: 214

{
  "id": "4f2a1c90-3f5e-4c1b-9f77-2b0e8a6d1c33",
  "type": "invoice.paid",
  "created_at": "2026-02-01T12:00:00Z",
  "api_version": "2026-01-15",
  "data": {
    "invoice_id": "inv_9812",
    "amount_cents": 4900,
    "currency": "EUR"
  }
}
```

### Headers

| Header | Value |
| --- | --- |
| `Content-Type` | Always `application/json`. |
| `X-Webhook-Id` | UUIDv4. Identical across all retries of one event. Use it as the idempotency key. |
| `X-Webhook-Event` | The event type, equal to the body's `type`. |
| `X-Webhook-Timestamp` | Unix seconds when the service built this attempt. Changes on each retry. |
| `X-Webhook-Attempt` | `1` through `6`. `1` is the first delivery, `6` is the last retry. |
| `X-Webhook-Signature` | Signature over the timestamp and body. See below. |

### Body fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | UUIDv4, equal to `X-Webhook-Id`. |
| `type` | string | Event type, for example `invoice.paid`. |
| `created_at` | string | RFC 3339 UTC time the event occurred, not the time of the attempt. |
| `api_version` | string | Schema version of `data`, as `YYYY-MM-DD`. |
| `data` | object | Event payload. Fields depend on `type`. |

The service adds fields to `data` without changing `api_version`. Ignore fields you do not recognize.

## Verify the signature

`X-Webhook-Signature` holds one or more space-separated versioned signatures, for example `v1=6c1f...9ab2`. Read the `v1` value.

The signed message is the timestamp, a `.`, and the raw request body:

```
message = X-Webhook-Timestamp + "." + raw_body
v1      = hex(HMAC-SHA256(key = signing_secret, message))
```

Sign the raw bytes of the body. Re-serializing parsed JSON changes the bytes and produces a different signature.

```python
import hashlib, hmac, time

def verify(raw_body: bytes, timestamp: str, header: str, secret: str) -> bool:
    if abs(time.time() - int(timestamp)) > 300:
        return False
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256
    ).hexdigest()
    for part in header.split():
        version, _, value = part.partition("=")
        if version == "v1" and hmac.compare_digest(value, expected):
            return True
    return False
```

Compare with a constant-time function such as `hmac.compare_digest`. Reject any attempt whose `X-Webhook-Timestamp` is more than 300 seconds from your clock; that rejects a replayed body captured earlier.

During a secret rotation the service sends two signatures in one header, one per active secret:

```
X-Webhook-Signature: v1=6c1f...9ab2 v1=d40e...117c
```

Accept the delivery when either value matches one of your secrets.

## Respond

Return a 2xx status within 10 seconds. The service reads the status code only and discards the response body.

Acknowledge first, process after. Write the event to your own queue or table, then return 200; do not hold the connection open for downstream work.

## Retry schedule

The service retries after a connection failure, a TLS failure, a timeout past 10 seconds, or any response outside 2xx. One event gets 6 attempts: the first delivery plus 5 retries.

| Attempt | Delay after the previous attempt | Elapsed since the event |
| --- | --- | --- |
| 1 | none | 0 s |
| 2 | 10 s | 10 s |
| 3 | 60 s | 1 m 10 s |
| 4 | 5 m | 6 m 10 s |
| 5 | 30 m | 36 m 10 s |
| 6 | 2 h | 2 h 36 m 10 s |

Each delay carries jitter of up to 20%, so two events queued together do not arrive together.

After attempt 6 fails, the service marks the delivery `failed` and stops. Fetch a failed delivery with `GET /deliveries?status=failed` and resend it with `POST /deliveries/{id}/redeliver`. A redelivery reuses the original `id` and starts a new attempt sequence at `X-Webhook-Attempt: 1`.

Deliveries for one endpoint run in parallel. Attempt 3 of an earlier event can arrive after attempt 1 of a later one, so order by `created_at` rather than by arrival.

## Response codes the service acts on

Your receiver returns these; the table gives the service's reaction.

| Status you return | Service reaction |
| --- | --- |
| 200, 201, 202, 204 | Delivery recorded as `succeeded`. No retry. |
| 301, 302, 307, 308 | No redirect is followed. Counted as a failure and retried. |
| 400, 422 | Retried on the full schedule. Return 2xx for a body you will never accept. |
| 401, 403 | Retried on the full schedule. Check your signature verification. |
| 404, 410 | Retried on the full schedule. After 6 failures with 410 the endpoint is disabled and you get an email. |
| 408, 429 | Retried on the full schedule. `Retry-After` is ignored. |
| 5xx | Retried on the full schedule. |
| No response within 10 s | Timeout. Retried on the full schedule. |

## Endpoint requirements

- HTTPS with a certificate from a public CA. Plain HTTP and self-signed certificates are rejected.
- TLS 1.2 or TLS 1.3.
- A public DNS name. Private ranges such as `10.0.0.0/8` and `127.0.0.0/8` are rejected at registration.
- Source addresses are published at `GET /meta/ips` as CIDR blocks. The list changes; re-read it before you pin a firewall rule.
