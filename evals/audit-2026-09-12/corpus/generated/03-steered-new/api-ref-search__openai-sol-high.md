# Full-text search

`GET /v1/search` searches indexed content and returns ranked hits.

## Request

```http
GET /v1/search
```

Include the API key assigned to your integration. The endpoint returns `401 Unauthorized` when the request omits the key.

### Query parameters

| Parameter | Required | Description |
| --- | --- | --- |
| `q` | Yes | Search query with a maximum size of 1,024 bytes. |
| `filter` | No | Repeatable filter in `field:value` format. |
| `limit` | No | Number of hits to return, from `1` through `100`. The default is `20`. |
| `cursor` | No | Opaque pagination cursor from the preceding response. |
| `rank` | No | Ranking method. Accepts `relevance` or `recency`. |

### Example request

```http
GET /v1/search?q=distributed%20systems&filter=status%3Apublished&filter=language%3Aen&limit=20&rank=relevance
```

Each `filter` parameter must use the `field:value` format. Repeat the parameter to submit more than one filter.

```http
GET /v1/search?q=database&filter=status%3Apublished&filter=language%3Aen
```

## Response

A successful request returns `200 OK` with a JSON object.

| Field | Type | Description |
| --- | --- | --- |
| `hits` | array | Search hits ordered by the selected `rank` value. |
| `next_cursor` | string | Opaque cursor for the next request. |
| `took_ms` | number | Search processing time in milliseconds. |

```json
{
  "hits": [],
  "next_cursor": "opaque-cursor-value",
  "took_ms": 12
}
```

## Pagination

1. Send the first request without `cursor`.
2. Read `next_cursor` from the response.
3. Send the returned value as `cursor` in the next request.
4. Keep the other query parameters unchanged.

```http
GET /v1/search?q=database&limit=20&cursor=opaque-cursor-value
```

Do not parse, modify, or construct cursor values.

## Rate limit

The endpoint accepts 60 requests per minute. A request above that limit returns `429 Too Many Requests`.

Read the `Retry-After` response header before sending another request.

## Status codes

| Status | Meaning |
| --- | --- |
| `200 OK` | The endpoint completed the search. |
| `400 Bad Request` | A `filter` parameter does not use valid `field:value` syntax. |
| `401 Unauthorized` | The request does not include an API key. |
| `413 Content Too Large` | The `q` value exceeds 1,024 bytes. |
| `429 Too Many Requests` | The integration exceeded 60 requests per minute. The response includes `Retry-After`. |
