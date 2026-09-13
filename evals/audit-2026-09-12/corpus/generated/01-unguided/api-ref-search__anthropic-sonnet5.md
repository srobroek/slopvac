# Search API

`GET /v1/search`

Performs a full-text search against the index and returns a page of matching results ranked by relevance or recency.

## Authentication

Requests must include a valid API key. Omitting the key returns `401 Unauthorized`.

## Rate limit

This endpoint is limited to **60 requests per minute** per API key. Requests beyond the limit return `429 Too Many Requests` with a `Retry-After` header indicating the number of seconds to wait before retrying.

## Query parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `q` | string | Yes | — | The search query. Maximum size is 1,024 bytes; larger values return `413`. |
| `filter` | string | No | — | A field-scoped filter in the form `field:value`. Repeat this parameter to apply multiple filters (combined with AND). Malformed filters return `400`. |
| `limit` | integer | No | `20` | Maximum number of hits to return per page. Must be between `1` and `100`. |
| `cursor` | string | No | — | An opaque pagination token copied from `next_cursor` in a previous response. Omit it to fetch the first page. |
| `rank` | string | No | `relevance` | Sort order for results. One of `relevance` or `recency`. |

### `filter` syntax

Each `filter` value must follow the `field:value` pattern, where `field` is a known indexed field name and `value` is the exact match to constrain results to. Examples:

```
filter=status:published
filter=author:jdoe
```

To apply multiple filters, repeat the parameter:

```
GET /v1/search?q=onboarding&filter=status:published&filter=author:jdoe
```

Any filter missing the `:` separator, referencing an unknown field, or containing an empty `field` or `value` is malformed and causes the request to fail with `400 Bad Request`.

### Pagination with `cursor`

Do not construct or modify `cursor` values yourself. Treat the token as opaque:

1. Make an initial request without `cursor`.
2. Read `next_cursor` from the response.
3. Pass that value as `cursor` on the next request, keeping all other parameters unchanged.
4. Stop paginating when `next_cursor` is absent or `null`.

## Request example

```
GET /v1/search?q=quarterly+report&filter=status:published&limit=50&rank=recency
Authorization: Bearer YOUR_API_KEY
```

## Response

### `200 OK`

```json
{
  "hits": [
    {
      "id": "doc_8f2a1c",
      "score": 0.92,
      "title": "Q3 Quarterly Report",
      "fields": {
        "status": "published",
        "author": "jdoe"
      }
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjUwfQ==",
  "took_ms": 14
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Matching documents for this page, ordered according to `rank`. May be empty if no documents match. |
| `next_cursor` | string \| null | Opaque token for retrieving the next page, or `null` if there are no more results. |
| `took_ms` | integer | Server-side processing time for the request, in milliseconds. |

The exact shape of each entry in `hits` (beyond `id` and `score`) depends on your index configuration.

## Error responses

| Status | Condition | Notes |
|---|---|---|
| `400 Bad Request` | A `filter` value does not match `field:value` or references an invalid field. | The response body describes which filter failed. |
| `401 Unauthorized` | The API key is missing. | Include a valid key in the `Authorization` header. |
| `413 Payload Too Large` | `q` exceeds 1,024 bytes. | Shorten the query. |
| `429 Too Many Requests` | The 60-requests-per-minute limit was exceeded. | The `Retry-After` header gives the number of seconds to wait before retrying. |

## Integration notes

- Always check `next_cursor` rather than assuming a fixed page count; result sets can change between requests.
- Cache or back off using the `Retry-After` value on `429` rather than retrying immediately.
- Keep `q` under the 1,024-byte limit on the client side to avoid unnecessary round trips that end in `413`.
- `rank=recency` is useful for time-sensitive content feeds; `rank=relevance` (the default) is best for general search UX.
