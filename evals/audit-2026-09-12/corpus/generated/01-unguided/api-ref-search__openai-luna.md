# Full-Text Search

Search indexed content using a query string, optional field filters, and configurable ranking.

```http
GET /v1/search
```

## Authentication

Authentication is required. Include your API key with the request.

Requests without an API key return `401 Unauthorized`.

## Query parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `q` | string | Yes | Full-text search query. The UTF-8 encoded value must not exceed 1,024 bytes. |
| `filter` | string | No | Repeatable field filter in the format `field:value`. |
| `limit` | integer | No | Maximum number of hits to return. Must be between `1` and `100`. Defaults to `20`. |
| `cursor` | string | No | Opaque pagination cursor returned in `next_cursor` from a previous response. |
| `rank` | string | No | Result ordering. Allowed values are `relevance` and `recency`. |

### Filters

Pass `filter` once for each condition:

```text
filter=type:article&filter=status:published
```

The complete filter expression must use the `field:value` format. A malformed filter returns `400 Bad Request`.

Do not parse, modify, or construct a cursor. Treat `next_cursor` as opaque and pass it unchanged in the next request.

## Example request

```bash
curl --request GET \
  --url 'https://api.example.com/v1/search?q=distributed+systems&filter=type%3Aarticle&filter=status%3Apublished&limit=20&rank=relevance' \
  --header 'Authorization: Bearer YOUR_API_KEY'
```

## Response

### `200 OK`

Returns the matching hits, the cursor for the next page, and the search duration.

```json
{
  "hits": [
    {
      "id": "doc_123",
      "title": "Introduction to Distributed Systems",
      "snippet": "Distributed systems coordinate independent computers...",
      "score": 0.9821
    },
    {
      "id": "doc_456",
      "title": "Reliable Service Design",
      "snippet": "Reliable services account for failure across components...",
      "score": 0.9147
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjIwfQ",
  "took_ms": 14
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Search results for the current page. |
| `next_cursor` | string or `null` | Opaque cursor for the next page. A `null` value indicates that there are no more results. |
| `took_ms` | integer | Time spent processing the search request, in milliseconds. |

The fields inside each `hits` item depend on the indexed resource returned by the endpoint. A hit commonly includes an identifier, title, matching text snippet, and relevance score.

## Pagination

Use `next_cursor` to retrieve subsequent pages:

```bash
curl --request GET \
  --url 'https://api.example.com/v1/search?q=distributed+systems&limit=20&cursor=eyJvZmZzZXQiOjIwfQ' \
  --header 'Authorization: Bearer YOUR_API_KEY'
```

Use the same search parameters when following a cursor. The cursor is valid only for the search that produced it.

Stop requesting pages when `next_cursor` is `null`.

## Ranking

Set `rank` to control result ordering:

- `relevance` — orders results by their match quality.
- `recency` — orders results by how recently they were updated.

If `rank` is omitted, the endpoint uses its default ranking behavior.

## Errors

### `400 Bad Request`

A supplied `filter` is malformed.

```json
{
  "error": {
    "code": "invalid_filter",
    "message": "Filter must use the field:value format."
  }
}
```

Correct the filter syntax and retry the request.

### `401 Unauthorized`

The request does not include an API key.

```json
{
  "error": {
    "code": "missing_api_key",
    "message": "An API key is required."
  }
}
```

Provide the required API key and retry the request.

### `413 Payload Too Large`

The `q` value exceeds 1,024 bytes.

```json
{
  "error": {
    "code": "query_too_large",
    "message": "The q parameter must not exceed 1024 bytes."
  }
}
```

Shorten the query before retrying. The limit is measured in bytes, not characters.

### `429 Too Many Requests`

The request rate exceeds 60 requests per minute.

The response includes a `Retry-After` header indicating how many seconds to wait before retrying:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 42
Content-Type: application/json
```

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Search rate limit exceeded."
  }
}
```

Wait for the duration specified by `Retry-After` before retrying. Implement exponential backoff and avoid issuing concurrent retries that could extend rate limiting.
