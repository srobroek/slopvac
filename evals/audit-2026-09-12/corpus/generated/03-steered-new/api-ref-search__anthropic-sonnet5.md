# GET /v1/search

Full-text search over indexed documents.

## Request

`GET /v1/search`

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `q` | string | Yes | Query text. Maximum 1,024 bytes. |
| `filter` | string | No | `field:value`. Repeat the parameter for multiple filters. |
| `limit` | integer | No | Range 1-100. Default 20. |
| `cursor` | string | No | Opaque token from a previous response's `next_cursor`. |
| `rank` | string | No | `relevance` or `recency`. |

### Filters

Each `filter` value has the form `field:value`. Send one `filter` parameter per field-value pair.

Example: `filter=status:open&filter=owner:jdoe`

### Pagination

Send the `next_cursor` value from a response as the `cursor` parameter of the next request. Omit `cursor` to start from the first page.

## Response: 200

```json
{
  "hits": [ { "...": "..." } ],
  "next_cursor": "opaque-token-or-null",
  "took_ms": 12
}
```

| Field | Type | Notes |
|---|---|---|
| `hits` | array | Matching documents. |
| `next_cursor` | string or null | Pass to `cursor` for the next page. `null` when no more results exist. |
| `took_ms` | integer | Server-side query time in milliseconds. |

## Errors

| Status | Condition |
|---|---|
| 400 | A `filter` value is not in `field:value` form. |
| 401 | The request has no API key. |
| 413 | `q` exceeds 1,024 bytes. |
| 429 | The caller exceeded 60 requests per minute. The response carries a `Retry-After` header giving the number of seconds to wait. |

## Rate limit

60 requests per minute per API key. A request over the limit receives a 429 with `Retry-After`.

## Example

```
GET /v1/search?q=quarterly+report&filter=status:open&limit=50&rank=recency
```

```json
{
  "hits": [
    { "id": "doc_123", "title": "Q3 quarterly report", "status": "open" }
  ],
  "next_cursor": "eyJvZmZzZXQiOjUwfQ",
  "took_ms": 8
}
```
