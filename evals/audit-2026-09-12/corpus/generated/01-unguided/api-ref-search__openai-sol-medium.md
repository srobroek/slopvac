# Search

Search indexed content using a full-text query.

```http
GET /v1/search
```

## Authentication

This endpoint requires an API key. A request without a key returns `401 Unauthorized`.

## Query parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `q` | string | Yes | Full-text search query. Maximum size: 1,024 bytes. |
| `filter` | string | No | Restricts results using `field:value` syntax. Repeat this parameter to provide multiple filters. |
| `limit` | integer | No | Maximum number of hits to return. Must be from `1` through `100`. Defaults to `20`. |
| `cursor` | string | No | Opaque pagination cursor returned as `next_cursor` by the previous response. |
| `rank` | string | No | Ranking mode. Accepted values are `relevance` and `recency`. |

URL-encode query parameter values. Do not parse, modify, or construct cursor values.

### Repeating filters

Specify each filter as a separate `filter` parameter:

```http
GET /v1/search?q=distributed%20systems&filter=status:published&filter=language:en
```

A filter that does not use valid `field:value` syntax causes a `400 Bad Request` response.

## Request example

```bash
curl --get "https://api.example.com/v1/search" \
  --header "Authorization: Bearer $API_KEY" \
  --data-urlencode "q=distributed systems" \
  --data-urlencode "filter=status:published" \
  --data-urlencode "filter=language:en" \
  --data-urlencode "limit=20" \
  --data-urlencode "rank=relevance"
```

## Response

### `200 OK`

The response contains the matching hits, an optional cursor for the next page, and the time spent processing the search.

```json
{
  "hits": [],
  "next_cursor": "opaque-cursor-value",
  "took_ms": 12
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Matching search results. |
| `next_cursor` | string or null | Cursor for the next page. A null or absent cursor indicates that no next page is available. |
| `took_ms` | number | Search processing time in milliseconds. |

## Pagination

To request the next page:

1. Read `next_cursor` from the current response.
2. Pass it unchanged as the next request's `cursor`.
3. Keep the other search parameters consistent while paging.

```bash
curl --get "https://api.example.com/v1/search" \
  --header "Authorization: Bearer $API_KEY" \
  --data-urlencode "q=distributed systems" \
  --data-urlencode "filter=status:published" \
  --data-urlencode "limit=20" \
  --data-urlencode "rank=relevance" \
  --data-urlencode "cursor=$NEXT_CURSOR"
```

Cursors are opaque. Do not decode, edit, or reuse them with a different search.

## Errors

| Status | Condition | Integrator action |
|---|---|---|
| `400 Bad Request` | A `filter` value is malformed. | Correct the filter so it uses `field:value` syntax. |
| `401 Unauthorized` | The API key is missing. | Include the API key and retry. |
| `413 Content Too Large` | `q` exceeds 1,024 bytes. | Shorten the query before retrying. |
| `429 Too Many Requests` | The rate limit of 60 requests per minute has been exceeded. | Wait for the duration specified by `Retry-After`, then retry. |

### Rate limiting

The endpoint allows 60 requests per minute. A rate-limited response includes the `Retry-After` header:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

Honor `Retry-After` before sending another request.
