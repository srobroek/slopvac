# Full-text search

`GET /v1/search` returns paginated search results that match a query, optional filters, and a ranking preference.

## Request

Send a GET request to `/v1/search` with the following parameters.

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `q` | string | Yes | The search query. A maximum of 1,024 bytes. |
| `filter` | string | No | A field-value constraint in the form `field:value`. Repeat this parameter to add multiple filters. The API returns 400 if a filter is malformed. |
| `limit` | integer | No | The maximum number of results per page. A minimum of 1, a maximum of 100. Defaults to 20. |
| `cursor` | string | No | An opaque pagination token from a previous response. Use `next_cursor` to retrieve the next page. |
| `rank` | string | No | The ranking strategy. Either `relevance` (default) or `recency`. |

Authenticate with an API key in the `Authorization` header using the format `Bearer <key>`. The API returns 401 if the key is missing or invalid.

## Response

### 200 OK

The response body is a JSON object with the following fields.

| Field | Type | Description |
|-------|------|-------------|
| `hits` | array | An array of matching documents. Each hit includes the document ID, title, content, and score. |
| `next_cursor` | string or null | An opaque token to retrieve the next page. `null` if no more results exist. |
| `took_ms` | integer | The time in milliseconds that the search took to execute. |

### Error responses

| Status | Condition |
|--------|-----------|
| 400 | A filter parameter is malformed (for example, missing a colon or field name). |
| 401 | The `Authorization` header is missing, invalid, or revoked. |
| 413 | The `q` parameter exceeds 1,024 bytes. |
| 429 | The request rate exceeds 60 requests per minute. The response includes a `Retry-After` header that specifies the delay in seconds. |

## Rate limiting

The API permits 60 requests per minute, measured per API key. When the limit is exceeded, the API returns 429 and includes a `Retry-After` header indicating how many seconds to wait before retrying.

## Example

Retrieve the first page of results for `kubernetes logging`:

```
GET /v1/search?q=kubernetes%20logging&limit=10&rank=recency
Authorization: Bearer sk_live_abc123
```

The response:

```json
{
  "hits": [
    {
      "id": "doc_001",
      "title": "Logging in Kubernetes clusters",
      "content": "...",
      "score": 0.987
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOiAxMH0=",
  "took_ms": 45
}
```

Retrieve the next page by passing `next_cursor`:

```
GET /v1/search?q=kubernetes%20logging&limit=10&rank=recency&cursor=eyJvZmZzZXQiOiAxMH0=
Authorization: Bearer sk_live_abc123
```

Add a filter to narrow results to a specific category:

```
GET /v1/search?q=kubernetes%20logging&filter=category:infrastructure&limit=10
Authorization: Bearer sk_live_abc123
```
