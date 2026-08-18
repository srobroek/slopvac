# Webhook Delivery

## Introduction

Our webhook system is a powerful and flexible way to receive real-time notifications about events in your account. In this guide, we'll walk through everything you need to know to build a robust receiver.

## Overview

Webhooks are delivered as HTTP POST requests with a JSON body. Each delivery is cryptographically signed so that you can verify it genuinely came from us. Deliveries are retried on failure, and it's important to note that our delivery guarantee is *at-least-once* — meaning your receiver must be idempotent.

## Request Format

Every delivery includes the following headers:

| Header | Description |
|---|---|
| `Content-Type` | Always `application/json` |
| `X-Signature` | HMAC-SHA256 signature of the body |
| `X-Timestamp` | Unix timestamp of the delivery attempt |
| `X-Delivery-Id` | Unique identifier for this delivery |
| `X-Attempt` | Which retry attempt this is |

The body looks something like this:

```json
{
  "id": "evt_abc123",
  "type": "invoice.paid",
  "created": 1710000000,
  "data": { }
}
```

## Signature Verification

This is arguably the most important part of building a secure receiver. You should always verify the signature before processing a delivery.

```python
import hmac, hashlib

def verify(body, signature, secret):
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Note that you may want to use a constant-time comparison here, which the above does via `compare_digest`.

## Retry Schedule

If your endpoint doesn't respond successfully, we'll retry up to five times with exponential backoff:

| Attempt | Delay |
|---|---|
| 1 | immediate |
| 2 | 1 minute |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |

After the final attempt, the delivery is marked as failed and we'll stop trying.

## Response Codes

Your endpoint should return one of the following:

- **2xx** — Success. We consider the delivery complete.
- **410** — Gone. We'll disable the webhook permanently.
- **Anything else** — We'll retry according to the schedule above.

We recommend responding as quickly as possible and doing any heavy processing asynchronously. If your endpoint takes too long, the request may time out and be retried, which could potentially result in duplicate processing.

## Best Practices

- Always verify signatures
- Make your handler idempotent (deduplicate on `X-Delivery-Id`)
- Respond fast, process async
- Log everything

## Conclusion

That covers the essentials of our webhook system! With signature verification and idempotent handling in place, you should be well-equipped to build a reliable integration.
