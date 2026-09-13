# Full-Text Search

Use `GET /v1/search` to search indexed content by text query.

## Request

```http
GET /v1/search?q=deployment&limit=20&rank=relevance HTTP/1.1
Host: api.example.com
```

### Query parameters

| Parameter | Required | Type | Default | Description |
|---|---:|---|---:|---|
| `q` | Yes | string | — | Search query. The endpoint rejects queries longer than 1,024 bytes. |
| `filter` | No | string, repeatable | — | Restricts results with `field:value` expressions. |
| `limit` | No | integer | `20` | Number of results to return. Use a value from `1` through `100`. |
| `cursor` | No | string | — | Opaque pagination cursor from the previous response. |
| `rank` | No | enum | `relevance` | Result ordering. Accepted values are `relevance` and `recency`. |

Encode query parameter values before sending the request.

### Repeatable filters

Send each filter as a separate `filter` parameter.

```http
GET /v1/search?q=deployment&filter=environment:production&filter=team:payments HTTP/1.1
```

Each filter must use the `field:value` format. The endpoint returns `400 Bad Request` when a filter does not use that format.

### Pagination

Send `next_cursor` from a response as the next request's `cursor` value.

```http
GET /v1/search?q=deployment&cursor=eyJvZmZzZXQiOjIwfQ HTTP/1.1
```

Treat the cursor as opaque. Do not parse, modify, or construct cursor values.

## Successful response

The endpoint returns `200 OK` with a JSON object.

```json
{
  "hits": [
    {
      "id": "result_123"
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjIwfQ",
  "took_ms": 12
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Matching search results. |
| `next_cursor` | string or `null` | Cursor for the next page. Use `null` when no next page exists. |
| `took_ms` | integer | Server-side search duration in milliseconds. |

When `next_cursor` contains a value, request another page with that value as `cursor`.

## Authentication

Provide the API key required by the service with every request.

The endpoint returns `401 Unauthorized` when the request does not include an API key.

## Errors

| Status | Condition | Response requirement |
|---:|---|---|
| `400` | A `filter` value is malformed. | Correct the filter to use `field:value`. |
| `401` | The API key is missing. | Provide the API key and retry the request. |
| `413` | `q` exceeds 1,024 bytes. | Shorten the query to 1,024 bytes or fewer. |
| `429` | The client exceeds 60 requests per minute. | Wait for the duration specified by `Retry-After` before retrying. |

The endpoint includes `Retry-After` in every `429 Too Many Requests` response. Use the header value to schedule the next request.
