# Full-text search

Search indexed content with a text query and optional field filters.

```http
GET /v1/search
```

## Request

The endpoint requires an API key.

### Query parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `q` | string | Yes | Full-text query. The request fails when the query exceeds 1,024 bytes. |
| `filter` | string | No | Field filter in `field:value` format. Repeat this parameter to apply multiple filters. |
| `limit` | integer | No | Number of hits to return. The range is 1 through 100. The default is 20. |
| `cursor` | string | No | Opaque pagination cursor from the preceding response. |
| `rank` | string | No | Ranking mode. Accepted values are `relevance` and `recency`. |

Encode query parameter names and values according to URL encoding rules.

### Example request

```http
GET /v1/search?q=distributed%20systems&filter=type:article&filter=language:en&limit=20&rank=relevance
```

## Response

### `200 OK`

The endpoint returns matching hits, an optional pagination cursor, and the search duration.

```json
{
  "hits": [],
  "next_cursor": null,
  "took_ms": 12
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Search hits for the requested page. |
| `next_cursor` | string or `null` | Cursor for the next page. A `null` value indicates that no next page exists. |
| `took_ms` | number | Search duration in milliseconds. |

## Pagination

1. Send the first request without `cursor`.
2. Read `next_cursor` from the response.
3. If `next_cursor` is not `null`, pass its value as `cursor` in the next request.
4. Treat the cursor as opaque, and do not parse or modify it.

```http
GET /v1/search?q=distributed%20systems&cursor=eyJwYWdlIjoyfQ
```

## Filters

Each `filter` value must use the `field:value` format.

Repeat `filter` to submit more than one field constraint.

```http
GET /v1/search?q=database&filter=type:article&filter=language:en
```

The endpoint returns `400 Bad Request` when any filter is malformed.

## Ranking

Set `rank=relevance` to order hits by their match to `q`.

Set `rank=recency` to order hits by recency.

## Errors

| Status | Condition | Response details |
|---|---|---|
| `400 Bad Request` | A `filter` value does not use valid `field:value` syntax. | Correct the malformed filter before retrying. |
| `401 Unauthorized` | The request does not include an API key. | Add the API key before retrying. |
| `413 Content Too Large` | `q` exceeds 1,024 bytes. | Reduce the query to 1,024 bytes or fewer. |
| `429 Too Many Requests` | The client exceeds 60 requests per minute. | Read the `Retry-After` header before retrying. |

### Rate-limit response

The endpoint permits 60 requests per minute.

After a `429 Too Many Requests` response, wait for the interval specified by `Retry-After`.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```
