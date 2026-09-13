# GET /v1/search

Full-text search over indexed documents.

## Request

```
GET /v1/search
```

### Query parameters

| Parameter | Type | Required | Constraints |
|---|---|---|---|
| `q` | string | yes | 1,024 bytes maximum |
| `filter` | string | no | Repeatable. Format `field:value`. |
| `limit` | integer | no | 1-100. Default 20. |
| `cursor` | string | no | Opaque token from a previous response's `next_cursor`. |
| `rank` | string | no | `relevance` or `recency`. Default `relevance`. |

`q` holds the search query. Pass `filter` once per field to constrain; repeat the parameter for multiple filters, for example `filter=status:open&filter=lang:en`. `limit` sets the number of hits per page. `cursor` requests the page that follows the response it came from; omit it for the first page. `rank` orders hits by match score (`relevance`) or by document timestamp (`recency`).

### Authentication

Send the API key in the request header required by your account. A request without the key returns `401`.

## Response

### 200 OK

```json
{
  "hits": [
    {
      "id": "doc_123",
      "score": 0.87,
      "fields": { "...": "..." }
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjIwfQ",
  "took_ms": 42
}
```

| Field | Type | Description |
|---|---|---|
| `hits` | array | Matched documents for this page, ordered by `rank`. |
| `next_cursor` | string or null | Pass to `cursor` to fetch the next page. `null` on the last page. |
| `took_ms` | integer | Server-side query time in milliseconds. |

### 400 Bad Request

Returned when a `filter` value does not match the `field:value` format.

### 401 Unauthorized

Returned when the request omits the API key.

### 413 Payload Too Large

Returned when `q` exceeds 1,024 bytes.

### 429 Too Many Requests

Returned when the key exceeds 60 requests per minute. The response includes a `Retry-After` header giving the number of seconds to wait before retrying.

## Pagination

Read `next_cursor` from each response and send it as `cursor` on the following request. Stop when `next_cursor` is `null`.

## Examples

Search with a filter and a page size of 10:

```
GET /v1/search?q=invoice+reminder&filter=status:open&limit=10
```

Fetch the next page:

```
GET /v1/search?q=invoice+reminder&filter=status:open&limit=10&cursor=eyJvZmZzZXQiOjEwfQ
```

Order by recency:

```
GET /v1/search?q=incident&rank=recency
```
