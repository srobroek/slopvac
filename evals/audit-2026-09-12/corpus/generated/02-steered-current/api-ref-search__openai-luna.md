# Full-text search

Search indexed content with a query string and optional filters.

```http
GET /v1/search
```

## Authentication

Provide an API key with the request.

The endpoint returns `401 Unauthorized` when the API key is missing.

## Query parameters

| Parameter | Required | Description |
|---|---:|---|
| `q` | Yes | Full-text search query. The endpoint returns `413 Payload Too Large` when `q` exceeds 1,024 bytes. |
| `filter` | No | Field filter in `field:value` format. Repeat this parameter for multiple filters. |
| `limit` | No | Number of results to request. Accepts values from `1` through `100`. The default is `20`. |
| `cursor` | No | Opaque cursor returned by the previous response. |
| `rank` | No | Result ordering mode. Accepts `relevance` or `recency`. |

### Example request

```http
GET /v1/search?q=database&filter=type:guide&filter=status:published&limit=20&rank=relevance HTTP/1.1
Host: api.example.com
```

Encode query parameter values according to standard URL rules.

Repeat `filter` once for each field filter.

```text
/v1/search?q=database&filter=type%3Aguide&filter=status%3Apublished
```

Use the `next_cursor` value from a response as the `cursor` value in the next request.

Treat `cursor` as an opaque value.

## Successful response

The endpoint returns `200 OK` with a JSON object containing `hits`, `next_cursor`, and `took_ms`.

```json
{
  "hits": [],
  "next_cursor": "opaque-cursor-value",
  "took_ms": 12
}
```

| Field | Description |
|---|---|
| `hits` | Array of matching search results. |
| `next_cursor` | Opaque cursor for the next page of results. |
| `took_ms` | Search execution time in milliseconds. |

## Errors

| Status | Condition | Response requirement |
|---:|---|---|
| `400 Bad Request` | A `filter` value does not use `field:value` format. | Correct the filter syntax before retrying. |
| `401 Unauthorized` | The request does not include an API key. | Provide the required API key. |
| `413 Payload Too Large` | The `q` value exceeds 1,024 bytes. | Shorten `q` to 1,024 bytes or fewer. |
| `429 Too Many Requests` | The request rate exceeds 60 requests per minute. | Wait for the interval specified by the `Retry-After` response header before retrying. |

### Malformed filter

```http
GET /v1/search?q=database&filter=published HTTP/1.1
```

The endpoint returns `400 Bad Request` because `published` does not contain a `field:value` pair.

### Query too large

The endpoint returns `413 Payload Too Large` when the UTF-8 encoded `q` value exceeds 1,024 bytes.

### Rate limit

The endpoint permits 60 requests per minute.

A rate-limited response includes the `Retry-After` header.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

Retry after the number of seconds specified by `Retry-After`.
