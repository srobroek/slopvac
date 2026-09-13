# Full-text search

```http
GET /v1/search
```

Searches indexed content and returns a page of matching results. The endpoint requires an API key.

## Query parameters

| Parameter | Type | Required | Default | Description |
|---|---|---:|---:|---|
| `q` | string | Yes | — | Full-text query. The value must not exceed 1,024 bytes. |
| `filter` | string | No | — | Filter in `field:value` format. Repeat the parameter to send multiple filters. |
| `limit` | integer | No | `20` | Maximum number of hits to return. Accepted values range from `1` through `100`. |
| `cursor` | string | No | — | Opaque pagination cursor from the preceding response. |
| `rank` | string | No | — | Result ordering. Accepted values are `relevance` and `recency`. |

Each `filter` value must contain a field and value separated by a colon.

```text
filter=status:published
```

Repeat `filter` to submit multiple conditions.

```text
filter=status:published&filter=language:en
```

Percent-encode reserved characters in query parameter values.

```http
GET /v1/search?q=distributed%20systems&filter=status%3Apublished&filter=language%3Aen&limit=20&rank=relevance
```

## Pagination

1. Send the first request without `cursor`.
2. Read `next_cursor` from the response.
3. Pass that value unchanged as `cursor` in the next request.

```http
GET /v1/search?q=distributed%20systems&cursor=eyJwYWdlIjoyfQ
```

## Successful response

The endpoint returns `200 OK` with a JSON object.

```json
{
  "hits": [],
  "next_cursor": "eyJwYWdlIjoyfQ",
  "took_ms": 12
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Matching search results for the requested page. |
| `next_cursor` | string | Opaque cursor for the next page. |
| `took_ms` | number | Search processing time in milliseconds. |

## Errors

| Status | Condition | Response details |
|---:|---|---|
| `400 Bad Request` | A `filter` value does not follow `field:value` format. | Correct the malformed filter before retrying. |
| `401 Unauthorized` | The request does not include an API key. | Add the required API key before retrying. |
| `413 Content Too Large` | `q` exceeds 1,024 bytes. | Reduce the query to 1,024 bytes or fewer. |
| `429 Too Many Requests` | The client exceeds 60 requests per minute. | The response includes a `Retry-After` header. |

When the endpoint returns `429`, wait until the `Retry-After` value permits another request.
