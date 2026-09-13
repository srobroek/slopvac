# Search

Full-text search across indexed documents. Returns ranked matches with an opaque cursor for pagination.

```
GET /v1/search
```

## Authentication

Send your API key as a bearer token:

```
Authorization: Bearer sk_live_...
```

Requests without this header return `401`.

## Query parameters

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `q` | string | yes | — | The search query. Maximum 1,024 bytes after UTF-8 encoding. |
| `filter` | string | no | — | Restricts results to documents matching `field:value`. Repeatable. |
| `limit` | integer | no | `20` | Number of hits to return. Between 1 and 100 inclusive. |
| `cursor` | string | no | — | Opaque pagination token taken from `next_cursor` in a previous response. |
| `rank` | string | no | `relevance` | Result ordering. Either `relevance` or `recency`. |

### `q`

The query is matched against the full text of each indexed document. The 1,024-byte
limit applies to the encoded bytes, not the character count, so multi-byte
characters consume more of the budget than ASCII. A query of 400 emoji exceeds the
limit. Queries over the limit return `413`.

### `filter`

Each `filter` value is a single `field:value` pair. The field name must be an
indexed attribute, and the value is matched exactly — filters do not tokenize or
stem.

Repeat the parameter to apply several filters. Filters on different fields are
combined with AND; filters on the same field are combined with OR:

```
?q=turbine&filter=lang:en&filter=lang=de&filter=status:published
```

That request matches published documents whose language is English or German.

A value containing a colon needs no escaping — only the first colon is treated as
the separator, so `filter=url:https://example.com` is valid. A filter with no
colon, an empty field name, or an unknown field returns `400`.

### `limit` and `cursor`

A response includes `next_cursor` when more hits are available. Pass it back
unchanged to fetch the following page, holding `q`, `filter`, and `rank`
constant. Changing any of those alongside a cursor returns `400`.

Cursors are opaque: do not parse, construct, or store them as long-lived
references. They expire five minutes after issue, after which requests using them
return `400`. Restart the pagination from the first page.

When `next_cursor` is absent from the response, you have reached the last page.

### `rank`

`relevance` scores each document against `q` and orders by descending score.
`recency` orders by the document's `indexed_at` timestamp, newest first, ignoring
relevance score except to break ties. Any other value returns `400`.

## Response

`200 OK` with a JSON body:

```json
{
  "hits": [
    {
      "id": "doc_01H8XG9K",
      "score": 8.412,
      "title": "Turbine maintenance schedule",
      "snippet": "quarterly <em>turbine</em> inspection covers blade wear",
      "fields": {
        "lang": "en",
        "status": "published"
      },
      "indexed_at": "2026-08-30T14:22:01Z"
    }
  ],
  "next_cursor": "eyJvIjoyMCwic2lkIjoiYTk0Zj",
  "took_ms": 37
}
```

| Field | Type | Description |
| --- | --- | --- |
| `hits` | array | Matching documents, ordered per `rank`. Empty when nothing matches. |
| `hits[].id` | string | Document identifier. |
| `hits[].score` | number | Relevance score. Comparable only within one response. |
| `hits[].title` | string | Document title, or `null` if the document has none. |
| `hits[].snippet` | string | Excerpt with matched terms wrapped in `<em>`. HTML in the source text is escaped. |
| `hits[].fields` | object | Indexed attributes available for filtering. |
| `hits[].indexed_at` | string | RFC 3339 timestamp of the last index update. |
| `next_cursor` | string | Token for the next page. Omitted on the last page. |
| `took_ms` | integer | Server-side search time in milliseconds, excluding network transit. |

An empty result set is a `200` with `hits: []` and no `next_cursor`, not a `404`.

## Rate limit

60 requests per minute per API key, measured over a sliding window. Every response
carries the current state:

| Header | Description |
| --- | --- |
| `X-RateLimit-Limit` | Requests permitted per window (`60`). |
| `X-RateLimit-Remaining` | Requests left in the current window. |
| `X-RateLimit-Reset` | Unix timestamp when the window refills. |

Exceeding the limit returns `429` with a `Retry-After` header giving the seconds to
wait. Honor that value rather than retrying on a fixed interval.

## Errors

Errors return a JSON body:

```json
{
  "error": {
    "code": "invalid_filter",
    "message": "filter \"lang\" is missing a ':' separator",
    "param": "filter"
  }
}
```

| Status | `code` | Cause |
| --- | --- | --- |
| `400` | `invalid_filter` | A `filter` value is not a well-formed `field:value` pair, or names a field that is not indexed. |
| `400` | `invalid_cursor` | The `cursor` is expired, malformed, or paired with changed search parameters. |
| `400` | `invalid_parameter` | `q` is missing or empty, `limit` is outside 1–100, or `rank` is an unrecognized value. |
| `401` | `unauthorized` | The `Authorization` header is missing, malformed, or the key is revoked. |
| `413` | `query_too_large` | `q` exceeds 1,024 bytes. |
| `429` | `rate_limited` | More than 60 requests in the current window. See `Retry-After`. |

Retry `429` and `5xx` responses with exponential backoff. The `400`, `401`, and
`413` responses are deterministic — retrying an unchanged request produces the same
result.

## Examples

Search with two filters and a larger page size:

```bash
curl -G https://api.example.com/v1/search \
  -H "Authorization: Bearer $API_KEY" \
  --data-urlencode "q=turbine maintenance" \
  --data-urlencode "filter=lang:en" \
  --data-urlencode "filter=status:published" \
  --data-urlencode "limit=50"
```

Page through every result, newest first:

```python
params = {"q": "turbine maintenance", "rank": "recency", "limit": 100}

while True:
    r = requests.get(
        "https://api.example.com/v1/search",
        headers={"Authorization": f"Bearer {api_key}"},
        params=params,
        timeout=10,
    )
    r.raise_for_status()
    body = r.json()

    for hit in body["hits"]:
        process(hit)

    cursor = body.get("next_cursor")
    if not cursor:
        break
    params["cursor"] = cursor
```

Because cursors expire after five minutes, keep per-page work short or collect the
identifiers first and process them after pagination finishes.
