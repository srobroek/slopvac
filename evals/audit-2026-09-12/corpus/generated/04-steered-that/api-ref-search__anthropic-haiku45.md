# Full-text search

The `/v1/search` endpoint searches indexed content and returns ranked results.

## Request

**Method and path**

```
GET /v1/search
```

**Authentication**

Include your API key in the `Authorization` header.

```
Authorization: Bearer your-api-key
```

**Parameters**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `q` | string | Yes | Search query. Maximum 1,024 bytes. |
| `filter` | string | No | Repeatable. Format: `field:value`. Example: `filter=status:published&filter=author:jane` |
| `limit` | integer | No | Results per page. Range: 1–100. Default: 20. |
| `cursor` | string | No | Opaque token from `next_cursor` in the previous response. Omit for the first page. |
| `rank` | string | No | Ranking strategy: `relevance` or `recency`. Default: `relevance`. |

## Response

**Status 200**

The server returns matched documents and pagination state.

```json
{
  "hits": [
    {
      "id": "doc-1",
      "title": "Getting started",
      "url": "/docs/getting-started",
      "snippet": "Learn the basics of our platform..."
    }
  ],
  "next_cursor": "opaque-cursor-string",
  "took_ms": 45
}
```

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `hits` | array | Matched documents. Empty if no results. |
| `hits[].id` | string | Document identifier. |
| `hits[].title` | string | Document title. |
| `hits[].url` | string | Document URL. |
| `hits[].snippet` | string | Text excerpt from the document. |
| `next_cursor` | string | Cursor for the next page. Null when no further results exist. |
| `took_ms` | integer | Query execution time in milliseconds. |

## Errors

**Status 400: Malformed filter**

The `filter` parameter does not match the `field:value` format.

```json
{
  "error": "invalid_filter",
  "message": "filter must be formatted as field:value"
}
```

**Status 401: Unauthorized**

The `Authorization` header is missing or invalid.

```json
{
  "error": "unauthorized",
  "message": "valid API key required"
}
```

**Status 413: Query too large**

The `q` parameter exceeds 1,024 bytes.

```json
{
  "error": "request_entity_too_large",
  "message": "search query must not exceed 1024 bytes"
}
```

**Status 429: Rate limit exceeded**

The request count exceeds 60 per minute. The `Retry-After` header specifies seconds until the next request is accepted.

```json
{
  "error": "rate_limited",
  "message": "too many requests"
}
```

Include the `Retry-After` header in your retry logic.

```
Retry-After: 60
```

## Examples

**Basic search**

```bash
curl -H "Authorization: Bearer YOUR_KEY" \
  "https://api.example.com/v1/search?q=authentication"
```

**Search with filter and ranking**

```bash
curl -H "Authorization: Bearer YOUR_KEY" \
  "https://api.example.com/v1/search?q=caching&filter=category:performance&rank=recency"
```

**Pagination**

Use the `next_cursor` value to fetch the next page.

```bash
curl -H "Authorization: Bearer YOUR_KEY" \
  "https://api.example.com/v1/search?q=database&limit=50&cursor=eyJvZmZzZXQiOjUwfQ=="
```

**Multiple filters**

```bash
curl -H "Authorization: Bearer YOUR_KEY" \
  "https://api.example.com/v1/search?q=deploy&filter=status:published&filter=author:team-a"
```
