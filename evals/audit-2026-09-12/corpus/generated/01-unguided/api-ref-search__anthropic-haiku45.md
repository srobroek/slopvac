# Full-Text Search

Search across indexed content with optional filtering, ranking, and pagination.

## Endpoint

```
GET /v1/search
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query. Maximum 1,024 bytes. |
| `filter` | string | No | Repeatable filter in the format `field:value`. Multiple filters are combined with AND logic. |
| `limit` | integer | No | Number of results to return. Range: 1–100. Default: 20. |
| `cursor` | string | No | Opaque pagination cursor from a previous response's `next_cursor`. Omit on the first request. |
| `rank` | string | No | Ranking strategy: `relevance` (default) or `recency`. |

### Query Format

The `q` parameter accepts free-text queries. Exact phrases can be quoted: `"exact phrase"`.

### Filter Format

Filters use the format `field:value`. Common fields include:

- `status:active` — Filter by status field
- `author:john` — Filter by author field
- `created:2024-01` — Filter by date (ISO 8601 prefix matching)

Repeat the `filter` parameter to apply multiple filters:

```
GET /v1/search?q=kubernetes&filter=status:published&filter=lang:en
```

## Response

### Success (200 OK)

```json
{
  "hits": [
    {
      "id": "doc-123",
      "title": "Kubernetes Deployment Guide",
      "excerpt": "A comprehensive guide to deploying applications on Kubernetes...",
      "score": 8.5,
      "url": "/docs/kubernetes-deployment"
    },
    {
      "id": "doc-124",
      "title": "Kubernetes Best Practices",
      "excerpt": "Follow these best practices when operating Kubernetes clusters...",
      "score": 7.2,
      "url": "/docs/kubernetes-best-practices"
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOiA0MCwgImtleWlkIjogMjM0NTZ9",
  "took_ms": 12
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `hits` | array | Array of search results. Empty array if no matches. |
| `hits[].id` | string | Unique identifier for the result. |
| `hits[].title` | string | Title of the result. |
| `hits[].excerpt` | string | Truncated excerpt showing context. |
| `hits[].score` | number | Relevance score (0–10 scale). Higher scores indicate better matches. |
| `hits[].url` | string | Relative URL to the result. |
| `next_cursor` | string | Opaque cursor for the next page. Null if no additional results. |
| `took_ms` | integer | Time in milliseconds to execute the search. |

### Errors

#### 400 Bad Request

Returned when a filter is malformed or a parameter value is invalid.

```json
{
  "error": "Invalid filter format",
  "message": "Filter must be in the format 'field:value', got 'status'",
  "code": "INVALID_FILTER"
}
```

#### 401 Unauthorized

Returned when the API key is missing or invalid.

```json
{
  "error": "Unauthorized",
  "message": "Missing or invalid API key",
  "code": "UNAUTHORIZED"
}
```

Include your API key in the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

#### 413 Payload Too Large

Returned when the `q` parameter exceeds 1,024 bytes.

```json
{
  "error": "Query too large",
  "message": "The 'q' parameter must not exceed 1,024 bytes",
  "code": "QUERY_TOO_LARGE",
  "max_bytes": 1024
}
```

#### 429 Too Many Requests

Returned when the rate limit (60 requests per minute) is exceeded.

```json
{
  "error": "Rate limited",
  "message": "Too many requests. Maximum 60 requests per minute.",
  "code": "RATE_LIMITED"
}
```

The response includes a `Retry-After` header indicating the number of seconds to wait before retrying:

```
Retry-After: 45
```

## Examples

### Basic Search

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=kubernetes"
```

### Search with Filters

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=kubernetes&filter=status:published&filter=lang:en&limit=10"
```

### Pagination

Use `next_cursor` from the previous response to fetch the next page:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=kubernetes&cursor=eyJvZmZzZXQiOiA0MCwgImtleWlkIjogMjM0NTZ9"
```

### Sort by Recency

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=kubernetes&rank=recency"
```

### Exact Phrase Search

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.example.com/v1/search?q=%22exact+phrase%22"
```

## Rate Limiting

The search endpoint enforces a rate limit of **60 requests per minute** per API key. When this limit is exceeded, the API returns a 429 response with the `Retry-After` header.

Implement exponential backoff with jitter to handle rate-limited responses gracefully:

```python
import time
import requests

def search_with_retry(query, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(
            "https://api.example.com/v1/search",
            params={"q": query},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            wait_time = retry_after * (2 ** attempt)  # Exponential backoff
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

## Best Practices

- **Use `limit` to paginate**: Avoid fetching large result sets. Use pagination with `cursor` for efficient data retrieval.
- **Combine filters**: Use multiple `filter` parameters to narrow results and reduce response size.
- **Handle `next_cursor` correctly**: Treat the cursor as an opaque value. Do not attempt to parse or modify it.
- **Set appropriate timeout**: Search queries may take 10–100ms. Set HTTP client timeouts to at least 5 seconds.
- **Cache results**: Consider caching frequently searched queries to reduce API calls.
- **Respect rate limits**: Monitor `Retry-After` headers and implement backoff strategies to avoid excessive retries.
