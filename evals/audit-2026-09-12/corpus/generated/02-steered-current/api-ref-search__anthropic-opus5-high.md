# GET /v1/search

Full-text search over indexed documents. Returns ranked hits with an opaque cursor for pagination.

## Request

```
GET /v1/search?q=quarterly+report&limit=50&rank=recency
Authorization: Bearer <api-key>
```

### Query parameters

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `q` | string | yes | — | Search terms. Maximum 1,024 bytes after UTF-8 encoding. |
| `filter` | string | no | — | Restricts results to documents matching `field:value`. Repeat the parameter to apply more than one filter. |
| `limit` | integer | no | `20` | Maximum hits in the response. Accepts `1` through `100`. |
| `cursor` | string | no | — | Opaque token copied from `next_cursor` in the previous response. |
| `rank` | string | no | `relevance` | Sort order. Accepts `relevance` or `recency`. |

### Filters

Each `filter` value is one `field:value` pair. The field name and the value are separated by the first colon; later colons belong to the value.

Repeated filters combine with AND:

```
GET /v1/search?q=invoice&filter=status:open&filter=owner:acct-1183
```

A value containing a space or an ampersand must be percent-encoded:

```
GET /v1/search?q=invoice&filter=owner%3AJane%20Doe
```

### Pagination

Send `cursor` with the value of `next_cursor` from the previous response. Keep `q`, `filter`, and `rank` identical across a cursor sequence; the cursor encodes them, and the server rejects a mismatch with `400`. A response omits `next_cursor` when no further hits exist.

## Response

`200 OK`

```json
{
  "hits": [
    {
      "id": "doc_9f21c4",
      "score": 0.8412,
      "title": "Quarterly report Q3",
      "snippet": "…the <em>quarterly report</em> closed at 4.2M…",
      "fields": {
        "status": "open",
        "owner": "acct-1183",
        "updated_at": "2026-08-30T11:04:22Z"
      }
    }
  ],
  "next_cursor": "eyJvIjo1MCwicSI6Imludm9pY2UifQ",
  "took_ms": 37
}
```

### Fields

| Field | Type | Description |
| --- | --- | --- |
| `hits` | array | Matching documents, ordered by `rank`. Empty when nothing matches. |
| `hits[].id` | string | Document identifier. |
| `hits[].score` | number | Relevance score between `0` and `1`. Present under both `rank` values. |
| `hits[].title` | string | Indexed document title. |
| `hits[].snippet` | string | Matched text with each match wrapped in `<em>`. |
| `hits[].fields` | object | Indexed fields available to `filter`. |
| `next_cursor` | string | Token for the next page. Absent on the last page. |
| `took_ms` | integer | Server-side query time in milliseconds, excluding network transfer. |

## Errors

| Status | Condition | Body `code` |
| --- | --- | --- |
| `400` | A `filter` value has no colon, names an unindexed field, or contradicts the cursor. Also returned for `limit` outside 1–100 and for an unrecognized `rank`. | `invalid_request` |
| `401` | The `Authorization` header is absent, or the key is revoked. | `unauthorized` |
| `413` | `q` exceeds 1,024 bytes. | `query_too_large` |
| `429` | The key exceeded 60 requests per minute. | `rate_limited` |

Error bodies carry `code` and `message`:

```json
{
  "code": "invalid_request",
  "message": "filter \"status\" is missing a ':' separator"
}
```

### Rate limit

The limit is 60 requests per minute per API key. A `429` response includes `Retry-After` with the number of seconds until the next request is accepted:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 12
```

Wait for that interval before retrying. A retry sent earlier returns `429` again and does not extend the window.
