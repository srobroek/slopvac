# Full-text search

`GET /v1/search` searches indexed content and returns ranked hits.

## Request

```http
GET /v1/search
```

### Query parameters

| Parameter | Required | Description |
|---|---:|---|
| `q` | Yes | Search query. The UTF-8 encoded value must not exceed 1,024 bytes. |
| `filter` | No | Filter in `field:value` format. Repeat this parameter to submit multiple filters. |
| `limit` | No | Number of hits to return. Accepts `1` through `100`. Defaults to `20`. |
| `cursor` | No | Opaque cursor returned as `next_cursor` by the previous response. |
| `rank` | No | Ranking method. Accepts `relevance` or `recency`. |

Encode parameter names and values according to URL query-string rules.

### Example request

```http
GET /v1/search?q=distributed%20systems&filter=status:published&filter=language:en&limit=20&rank=relevance
```

## Response

### `200 OK`

The response contains the search hits, pagination cursor, and search duration.

```json
{
  "hits": [],
  "next_cursor": "opaque-cursor-value",
  "took_ms": 12
}
```

| Field | Description |
|---|---|
| `hits` | Array containing the matching search results. |
| `next_cursor` | Opaque cursor to pass as `cursor` in the next request. |
| `took_ms` | Search duration in milliseconds. |

Do not parse, modify, or construct cursor values.

## Pagination

1. Send the first request without `cursor`.
2. Read `next_cursor` from the response.
3. Pass that value as `cursor` in the next request.

```http
GET /v1/search?q=distributed%20systems&cursor=opaque-cursor-value
```

## Errors

| Status | Condition |
|---|---|
| `400 Bad Request` | A `filter` value does not follow the `field:value` format. |
| `401 Unauthorized` | The request does not include an API key. |
| `413 Content Too Large` | The UTF-8 encoded `q` value exceeds 1,024 bytes. |
| `429 Too Many Requests` | The request exceeds the limit of 60 requests per minute. |

A `429 Too Many Requests` response includes a `Retry-After` header. Wait for the specified interval before sending another request.
