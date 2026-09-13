# Full-text search

`GET /v1/search` returns full-text search results.

## Request

```http
GET /v1/search
```

The request requires an API key. The endpoint returns `401` when the request omits the key.

### Query parameters

| Parameter | Required | Description |
|---|---:|---|
| `q` | Yes | Search query with a maximum encoded length of 1,024 bytes. |
| `filter` | No | Filter in `field:value` format. Repeat this parameter to apply multiple filters. |
| `limit` | No | Number of hits from `1` through `100`. The default is `20`. |
| `cursor` | No | Opaque pagination cursor from the previous response. |
| `rank` | No | Ranking method: `relevance` or `recency`. |

Do not parse or modify a `cursor` value.

### Example request

```http
GET /v1/search?q=distributed%20systems&filter=status%3Apublished&filter=language%3Aen&limit=20&rank=relevance
```

## Response

A successful request returns `200` with a JSON object.

```json
{
  "hits": [],
  "next_cursor": "opaque-cursor-value",
  "took_ms": 14
}
```

| Field | Description |
|---|---|
| `hits` | Array of matching search results. |
| `next_cursor` | Opaque cursor for the next request. |
| `took_ms` | Search execution time in milliseconds. |

Pass `next_cursor` as the next request's `cursor` value.

```http
GET /v1/search?q=distributed%20systems&cursor=opaque-cursor-value
```

## Errors

| Status | Condition | Response details |
|---:|---|---|
| `400` | A `filter` value does not use `field:value` format. | The request fails without search results. |
| `401` | The request omits the API key. | The request fails without search results. |
| `413` | `q` exceeds 1,024 bytes. | Reduce the query length before retrying. |
| `429` | The request rate exceeds 60 requests per minute. | Read `Retry-After` before retrying. |

For a `429` response, wait for the interval specified by the `Retry-After` response header.
