# GET /v1/search

Full-text search over indexed documents. Returns ranked hits with an opaque cursor for pagination.

## Request

```http
GET /v1/search?q=invoice&limit=50&rank=recency HTTP/1.1
Host: api.example.com
Authorization: Bearer sk_live_...
```

### Authentication

Send an API key in the `Authorization` header as a bearer token. A request without this header returns 401.

### Query parameters

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `q` | string | yes | — | The search query. The UTF-8 encoding of the value must not exceed 1,024 bytes. |
| `filter` | string | no | — | Restricts hits to documents matching `field:value`. Repeat the parameter to apply more than one filter. |
| `limit` | integer | no | `20` | Maximum number of hits in the response. Accepts 1 through 100. |
| `cursor` | string | no | — | An opaque token. Pass the `next_cursor` value from the previous response. |
| `rank` | string | no | `relevance` | Sort order. Accepts `relevance` or `recency`. |

### Filters

Each `filter` value uses the form `field:value`. Repeated filters combine with AND, so a document must match every filter to appear in `hits[]`.

```
GET /v1/search?q=invoice&filter=status:open&filter=region:emea
```

A value containing a colon or a space must be percent-encoded. A `filter` value without a colon returns 400.

### Pagination

The first request omits `cursor`. Each response carries `next_cursor`; pass that value unchanged in the next request to fetch the following page. When `next_cursor` is `null`, the result set is exhausted.

Treat the cursor as opaque: do not parse it, and do not construct one. Send `q`, `filter`, `limit`, and `rank` with the same values you used for the first page, because the cursor is bound to those parameters.

## Response

`200 OK` with a JSON body.

```json
{
  "hits": [
    {
      "id": "doc_8f21ab",
      "score": 4.812,
      "title": "Invoice 2026-0114",
      "snippet": "…balance due on <em>invoice</em> 2026-0114…",
      "updated_at": "2026-01-14T09:22:41Z"
    }
  ],
  "next_cursor": "eyJvIjoyMH0",
  "took_ms": 18
}
```

| Field | Type | Description |
| --- | --- | --- |
| `hits` | array | Matching documents, ordered by the `rank` parameter. Contains at most `limit` elements, and is empty when nothing matches. |
| `hits[].id` | string | Document identifier. |
| `hits[].score` | number | Relevance score for the query. Comparable only within one response. |
| `hits[].title` | string | Document title. |
| `hits[].snippet` | string | Matched text with each match wrapped in `<em>`. Escape this value before rendering it as HTML. |
| `hits[].updated_at` | string | Last modification time, RFC 3339 in UTC. |
| `next_cursor` | string or null | Token for the next page. `null` on the last page. |
| `took_ms` | integer | Server-side search time in milliseconds, excluding network transfer. |

An empty `hits` array with `next_cursor` set to `null` means that the query matched no documents. This is a 200, not an error.

## Rate limit

The endpoint allows 60 requests per minute per API key. Request 61 within the same window returns 429 with a `Retry-After` header giving the number of seconds to wait.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 17
```

Wait for the interval in `Retry-After` before retrying. Do not retry 400, 401, or 413, because a repeat of the same request produces the same status.

## Errors

Every error returns a JSON body with `error.code` and `error.message`.

| Status | `error.code` | Cause |
| --- | --- | --- |
| 400 | `invalid_filter` | A `filter` value is not in `field:value` form, or names an unindexed field. |
| 400 | `invalid_parameter` | `limit` is outside 1–100, `rank` is not `relevance` or `recency`, `cursor` is unreadable, or `q` is absent. |
| 401 | `missing_credentials` | The `Authorization` header is absent or malformed. |
| 413 | `query_too_large` | `q` exceeds 1,024 bytes when encoded as UTF-8. |
| 429 | `rate_limited` | The caller exceeded 60 requests per minute. See [Rate limit](#rate-limit). |

```json
{
  "error": {
    "code": "invalid_filter",
    "message": "filter \"status open\" is missing a ':' separator"
  }
}
```
