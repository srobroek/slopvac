# Full-Text Search

Search indexed content with `GET /v1/search`.

## Request

```http
GET /v1/search?q={query}&filter={field:value}&limit={limit}&cursor={cursor}&rank={rank}
```

Send an API key with every request.

### Query parameters

| Parameter | Type | Required | Default | Description |
|---|---|---:|---:|---|
| `q` | string | Yes | — | Full-text query. The UTF-8 value cannot exceed 1,024 bytes. |
| `filter` | string | No | — | Restricts results with `field:value`. Repeat this parameter for multiple filters. |
| `limit` | integer | No | `20` | Number of results to return. The value must range from `1` through `100`. |
| `cursor` | string | No | — | Opaque pagination cursor from the previous response. |
| `rank` | string | No | — | Ranking mode. Accepted values are `relevance` and `recency`. |

URL-encode query parameter values before sending the request.

### Filter syntax

Each `filter` value must use this format:

```text
field:value
```

Repeat `filter` for multiple conditions:

```text
/v1/search?q=database&filter=type:guide&filter=lang:en
```

The service returns `400 Bad Request` when a filter does not use the `field:value` format.

### Pagination

Use `next_cursor` from a response as the `cursor` value in the next request.

Treat the cursor as opaque data.

Do not parse, modify, or construct cursor values.

## Example request

```bash
curl --request GET \
  --get 'https://api.example.com/v1/search' \
  --data-urlencode 'q=database indexing' \
  --data-urlencode 'filter=type:guide' \
  --data-urlencode 'filter=lang:en' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'rank=relevance'
```

## Success response

The service returns `200 OK` with a JSON object containing `hits`, `next_cursor`, and `took_ms`.

```json
{
  "hits": [],
  "next_cursor": "opaque-cursor-value",
  "took_ms": 12
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Search results returned for the request. |
| `next_cursor` | string | Opaque cursor for the next page. |
| `took_ms` | integer | Search execution time in milliseconds. |

Send another request with `cursor` set to `next_cursor` when you need the next page.

## Rate limits

The endpoint allows 60 requests per minute.

The service returns `429 Too Many Requests` after the request limit is exceeded.

Read the `Retry-After` response header before retrying:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

Wait for the number of seconds specified by `Retry-After`.

## Errors

| Status | Condition | Response handling |
|---:|---|---|
| `400` | A `filter` value is malformed. | Correct each filter to use `field:value`. |
| `401` | The request does not include an API key. | Add the API key and retry the request. |
| `413` | The UTF-8 encoded `q` value exceeds 1,024 bytes. | Shorten the query before retrying. |
| `429` | The client exceeds 60 requests per minute. | Wait for the `Retry-After` duration before retrying. |

## Request examples

### Search by relevance

```text
GET /v1/search?q=connection+pool&rank=relevance
```

### Search by recency with a result limit

```text
GET /v1/search?q=connection+pool&limit=50&rank=recency
```

### Request the next page

```text
GET /v1/search?q=connection+pool&cursor=opaque-cursor-value
```
