# GET /v1/search

Search the index by full-text query and optional filters.

## Request

```
GET /v1/search?q=<query>&filter=<field:value>&limit=<n>&cursor=<opaque>&rank=<mode>
```

### Query parameters

| Parameter | Type | Required | Constraints | Notes |
|-----------|------|----------|-------------|-------|
| `q` | string | yes | 1–1,024 bytes | The search query. |
| `filter` | string | no | Repeatable; format `field:value` | Restrict results to documents where `field` equals `value`. Pass multiple `filter` parameters to AND them. |
| `limit` | integer | no | 1–100; default 20 | Maximum hits to return in this response. |
| `cursor` | string | no | Opaque token | Pagination cursor from a previous response `next_cursor`. Omit for the first request. |
| `rank` | string | no | `relevance` (default) or `recency` | Sort by relevance score or document modification time. |

### Authentication

Provide your API key as a Bearer token in the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

## Response

### 200 OK

Success. The response body is a JSON object.

```json
{
  "hits": [
    {
      "id": "document_id",
      "score": 0.95,
      "fields": {}
    }
  ],
  "next_cursor": "opaque_token_or_null",
  "took_ms": 45
}
```

| Field | Type | Notes |
|-------|------|-------|
| `hits` | array of objects | Search results, ordered by rank. Each hit includes the document `id`, relevance `score` (0–1), and document `fields`. |
| `next_cursor` | string or null | Pagination cursor for the next batch. Null if no more results exist. |
| `took_ms` | integer | Milliseconds the search took to execute. |

### 400 Bad Request

The request syntax is invalid. Check the `filter` parameter format: each filter must be `field:value` with no whitespace around the colon.

### 401 Unauthorized

The `Authorization` header is missing or the API key is invalid. Provide a valid Bearer token.

### 413 Payload Too Large

The `q` parameter exceeds 1,024 bytes. Reduce the query length and retry.

### 429 Too Many Requests

The rate limit (60 requests per minute) has been exceeded. The response includes a `Retry-After` header with the number of seconds to wait before retrying.

## Examples

### Basic search

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=kubernetes"
```

### Search with filters and pagination

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=deployment&filter=status:published&filter=author:alice&limit=50"
```

Then fetch the next page using the `next_cursor` from the response:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=deployment&filter=status:published&filter=author:alice&limit=50&cursor=OPAQUE_CURSOR"
```

### Search sorted by recency

```bash
curl -H "Authorization: Bearer YOUR_KEY" \
  "https://api.example.com/v1/search?q=release&rank=recency"
```
