# Full-text search

```http
GET /v1/search
```

Searches indexed content using a full-text query. An API key is required.

## Request

### Query parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `q` | string | Yes | Full-text query. The value must not exceed 1,024 bytes. |
| `filter` | string | No | Restricts results using `field:value` syntax. Repeat the parameter to provide multiple filters. |
| `limit` | integer | No | Maximum number of hits to return. Must be from `1` through `100`. Defaults to `20`. |
| `cursor` | string | No | Opaque pagination cursor returned as `next_cursor` by the previous response. |
| `rank` | string | No | Ranking mode. Accepted values are `relevance` and `recency`. |

The query limit is measured in bytes, not characters. Multibyte characters can cause a query to exceed the limit before it reaches 1,024 characters.

### Filters

Each filter must contain a field and value separated by a colon:

```text
filter=field:value
```

Repeat `filter` to send more than one filter:

```text
filter=type:article&filter=status:published
```

Supported filter fields depend on the indexed content. A filter that does not follow `field:value` syntax results in `400 Bad Request`.

URL-encode query and filter values. With `curl`, use `--data-urlencode` to encode them safely.

### Example request

```bash
curl --get "https://api.example.com/v1/search" \
  --header "$API_AUTH_HEADER" \
  --data-urlencode "q=distributed systems" \
  --data-urlencode "filter=type:article" \
  --data-urlencode "filter=status:published" \
  --data-urlencode "limit=20" \
  --data-urlencode "rank=relevance"
```

`API_AUTH_HEADER` represents the complete API-key header required by your API authentication configuration.

## Response

### `200 OK`

A successful response contains the matching hits, a pagination cursor, and the request duration.

```json
{
  "hits": [],
  "next_cursor": "opaque-cursor-value",
  "took_ms": 14
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Search results for the current page. The fields in each hit depend on the indexed content. |
| `next_cursor` | string | Opaque cursor for requesting the next page, when one is returned. Do not inspect or modify it. |
| `took_ms` | number | Time spent processing the search, in milliseconds. |

## Pagination

To retrieve the next page, pass the previous response's `next_cursor` as the `cursor` parameter:

```bash
curl --get "https://api.example.com/v1/search" \
  --header "$API_AUTH_HEADER" \
  --data-urlencode "q=distributed systems" \
  --data-urlencode "cursor=opaque-cursor-value"
```

Treat cursors as opaque values. Do not decode, construct, or alter them. Preserve the original query, filters, ranking mode, and page limit while paging unless you intend to start a different search.

## Ranking

Set `rank` to one of the following values:

| Value | Behavior |
|---|---|
| `relevance` | Prioritizes hits that best match `q`. |
| `recency` | Prioritizes more recent hits. |

## Errors

| Status | Condition | Action |
|---|---|---|
| `400 Bad Request` | A `filter` value is malformed. | Ensure every filter uses `field:value` syntax and is URL-encoded. |
| `401 Unauthorized` | The API key is missing. | Include the required API-key header. |
| `413 Content Too Large` | `q` exceeds 1,024 bytes. | Shorten the query before retrying. |
| `429 Too Many Requests` | The 60-requests-per-minute limit has been exceeded. | Wait for the duration specified by the `Retry-After` response header before retrying. |

### Rate-limit response

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

Clients should honor `Retry-After` rather than retrying immediately.
