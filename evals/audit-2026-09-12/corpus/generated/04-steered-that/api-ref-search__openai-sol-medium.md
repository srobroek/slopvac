# Full-text search

`GET /v1/search` searches indexed content and returns one page of ranked matches.

The endpoint requires an API key. A request without an API key returns `401 Unauthorized`.

## Request

```http
GET /v1/search
```

### Query parameters

| Parameter | Required | Description |
|---|---:|---|
| `q` | Yes | Search query with a maximum length of 1,024 bytes. |
| `filter` | No | Filter in `field:value` format. Repeat this parameter to send multiple filters. |
| `limit` | No | Number of hits to return, from `1` through `100`. The default is `20`. |
| `cursor` | No | Opaque pagination cursor from the preceding response. |
| `rank` | No | Ranking mode. Accepted values are `relevance` and `recency`. |

Do not parse or modify a `cursor` value. Pass the returned `next_cursor` value as the next request's `cursor`.

## Response

### `200 OK`

The endpoint returns a JSON object with these fields:

| Field | Description |
|---|---|
| `hits[]` | Array of search hits for the requested page. |
| `next_cursor` | Opaque cursor for requesting the next page. |
| `took_ms` | Search processing time in milliseconds. |

## Errors

| Status | Condition | Response details |
|---|---|---|
| `400 Bad Request` | A `filter` value does not follow `field:value` format. | Correct the malformed filter before retrying. |
| `401 Unauthorized` | The request does not include an API key. | Add the API key before retrying. |
| `413 Content Too Large` | `q` exceeds 1,024 bytes. | Shorten `q` to 1,024 bytes or fewer. |
| `429 Too Many Requests` | The client exceeds 60 requests per minute. | Wait for the duration specified by the `Retry-After` response header. |
