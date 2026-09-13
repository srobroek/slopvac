# GET /v1/search

Full-text search over indexed documents. Returns ranked hits with an opaque cursor for pagination.

## Request

```
GET /v1/search?q=invoice&filter=status:open&limit=50&rank=recency
Authorization: Bearer <api-key>
```

### Query parameters

| Parameter | Type | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `q` | string | yes | — | 1–1,024 bytes, UTF-8 |
| `filter` | string | no | none | `field:value`, repeatable |
| `limit` | integer | no | `20` | 1–100 |
| `cursor` | string | no | none | Opaque value from `next_cursor` |
| `rank` | string | no | `relevance` | `relevance` or `recency` |

The server measures `q` in bytes after UTF-8 encoding, not in characters. A 400-character string of 3-byte characters is 1,200 bytes and exceeds the limit.

### Filters

Each `filter` value has the form `field:value`, split at the first colon. A value may contain further colons.

Repeat the parameter to apply more than one filter:

```
?q=invoice&filter=status:open&filter=region:eu-west
```

The server combines repeated filters with AND. Two filters on the same field also combine with AND, so `filter=status:open&filter=status:paid` matches nothing.

### Ranking

- `relevance` orders hits by descending `score`.
- `recency` orders hits by descending document timestamp. The `score` field remains populated and does not control the order.

## Response

`200 OK`:

```json
{
  "hits": [
    {
      "id": "doc_8f2a1c",
      "score": 4.812,
      "title": "Invoice 2026-0114",
      "snippet": "…balance on <em>invoice</em> 2026-0114 is…",
      "fields": {
        "status": "open",
        "region": "eu-west"
      }
    }
  ],
  "next_cursor": "eyJvIjoyMCwiciI6InIifQ",
  "took_ms": 17
}
```

| Field | Type | Description |
| --- | --- | --- |
| `hits` | array | Matching documents, at most `limit` entries. Empty when nothing matches. |
| `hits[].id` | string | Document identifier. |
| `hits[].score` | number | Relevance score for this query. Not comparable across queries. |
| `hits[].snippet` | string | Matched text with `<em>` around the matched terms. |
| `hits[].fields` | object | Indexed field values available to `filter`. |
| `next_cursor` | string \| null | Cursor for the next page. `null` on the last page. |
| `took_ms` | integer | Server-side search time in milliseconds, excluding network transfer. |

## Pagination

1. Send the first request without `cursor`.
2. Read `next_cursor` from the response.
3. Send the next request with the same `q`, `filter`, `limit`, and `rank`, plus `cursor=<next_cursor>`.
4. Stop when `next_cursor` is `null`.

Treat the cursor as opaque. Do not parse it, construct it, or modify it. A cursor encodes the query it came from: changing `q`, `filter`, or `rank` while reusing a cursor returns `400`.

An empty `hits` array with a non-null `next_cursor` does not occur. Stop on `next_cursor: null`, not on an empty page.

## Errors

Every error returns a JSON body:

```json
{
  "error": {
    "code": "malformed_filter",
    "message": "filter \"status\" is missing a colon separator"
  }
}
```

| Status | `code` | Cause |
| --- | --- | --- |
| 400 | `malformed_filter` | A `filter` value has no colon, an empty field, or an unindexed field. |
| 400 | `invalid_parameter` | `limit` is outside 1–100, `rank` is not `relevance` or `recency`, `q` is absent or empty, or `cursor` does not match the other parameters. |
| 401 | `missing_credentials` | No `Authorization` header. |
| 413 | `query_too_large` | `q` exceeds 1,024 bytes. |
| 429 | `rate_limited` | More than 60 requests in the current minute. |

### Rate limit

The limit is 60 requests per minute per API key. A `429` response carries `Retry-After` with the number of seconds to wait:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 23
Content-Type: application/json
```

Wait for the interval in `Retry-After` before retrying. Do not retry `400`, `401`, or `413` without changing the request.
