# GET /v1/search

Full-text search over the indexed corpus.

## Request

```
GET /v1/search
```

### Query parameters

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `q` | string | Yes | — | Search query. Maximum 1,024 bytes. |
| `filter` | string, repeatable | No | none | A `field:value` pair. Repeat the parameter to apply multiple filters; the API combines them with AND. |
| `limit` | integer | No | 20 | Number of hits to return. Range: 1–100. |
| `cursor` | string | No | none | Opaque pagination token from a previous response's `next_cursor`. |
| `rank` | enum: `relevance`, `recency` | No | `relevance` | Sort order for `hits[]`. |

### Example

```
GET /v1/search?q=payment+timeout&filter=status:open&filter=team:billing&limit=50&rank=recency
```

## Response

### 200 OK

```json
{
  "hits": [ ... ],
  "next_cursor": "string or null",
  "took_ms": 0
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Matching results, ordered by `rank`. |
| `next_cursor` | string or null | Pass to `cursor` to fetch the next page. `null` when no further results exist. |
| `took_ms` | integer | Server-side processing time in milliseconds. |

### 400 Bad Request

Returned when a `filter` value does not parse as `field:value`.

### 401 Unauthorized

Returned when the request omits an API key.

### 413 Payload Too Large

Returned when `q` exceeds 1,024 bytes.

### 429 Too Many Requests

Returned when the caller exceeds 60 requests per minute. The response includes a `Retry-After` header giving the number of seconds to wait before retrying.

## Rate limit

60 requests per minute per API key. Requests beyond the limit receive a 429 response; back off for the duration in `Retry-After`.

## Pagination

1. Send the initial request without `cursor`.
2. Read `next_cursor` from the response.
3. If `next_cursor` is not `null`, send the next request with `cursor` set to that value and the same `q`, `filter`, `limit`, and `rank`.
4. Stop when `next_cursor` is `null`.
