# fluxcache

fluxcache caches LLM responses by prompt similarity. It embeds each prompt, compares the embedding against cached prompt embeddings by cosine similarity, and returns the cached response when the best match scores at or above a threshold.

An exact-match cache misses on "Summarize this ticket" versus "Summarise this ticket". fluxcache returns the cached response for both at the default threshold of 0.92.

## Install

```bash
pip install fluxcache
```

Redis support is an extra:

```bash
pip install 'fluxcache[redis]'
```

## Use

```python
from fluxcache import Cache

cache = Cache(threshold=0.92, ttl=3600)

@cache.wrap
def ask(prompt: str) -> str:
    return my_llm_client.complete(prompt)

ask("Summarize this ticket")   # calls my_llm_client
ask("Summarise this ticket")   # cosine 0.97, returns the cached string
```

Call the cache directly when you do not want a decorator:

```python
hit = cache.get("Summarise this ticket")
if hit is None:
    response = my_llm_client.complete("Summarise this ticket")
    cache.set("Summarise this ticket", response)
else:
    response = hit.value
    print(hit.score, hit.matched_prompt)
```

`Cache.get` returns `None` on a miss, or a `Hit` with three fields: `value`, `score`, and `matched_prompt`.

## Configuration

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `threshold` | `float` | `0.92` | Minimum cosine similarity for a hit. Range 0.0 to 1.0. |
| `ttl` | `int \| None` | `None` | Entry lifetime in seconds. `None` keeps entries until eviction. |
| `namespace` | `str` | `"default"` | Isolates entries. A lookup only searches its own namespace. |
| `backend` | `Backend` | `MemoryBackend()` | Where entries live. |
| `scorer` | `Callable` | cosine similarity | Scores a candidate pair. |
| `embed` | `Callable` | `sentence-transformers/all-MiniLM-L6-v2` | Turns a prompt into a `list[float]`. |

Raise `threshold` to reduce wrong hits. Lower it to raise the hit rate.

## Namespaces

Give each model, prompt template, or tenant its own namespace. Two namespaces never read each other's entries.

```python
gpt = Cache(namespace="gpt-4o")
haiku = Cache(namespace="claude-haiku")
```

Clear one namespace without touching the others:

```python
gpt.clear()
```

## Backends

`MemoryBackend` holds entries in a dict in the calling process. Entries disappear when the process exits.

```python
from fluxcache import Cache, MemoryBackend

cache = Cache(backend=MemoryBackend(max_entries=10_000))
```

`RedisBackend` shares entries across processes and hosts. It stores each entry as a Redis hash and sets the Redis key TTL from the `ttl` parameter.

```python
from fluxcache import Cache, RedisBackend

cache = Cache(
    backend=RedisBackend(url="redis://localhost:6379/0"),
    ttl=86_400,
)
```

`RedisBackend` scans the namespace's embeddings on every lookup. Lookup cost grows with the number of entries in the namespace.

To write a third backend, implement the four methods of `fluxcache.Backend`: `put`, `candidates`, `delete`, and `clear`.

## Custom scoring

Pass `scorer` to replace cosine similarity. The callable receives the query embedding, a candidate embedding, and the candidate's stored metadata. It returns a float that fluxcache compares against `threshold`.

```python
def penalize_stale(query_vec, cand_vec, meta):
    base = fluxcache.cosine(query_vec, cand_vec)
    age_hours = (time.time() - meta["created_at"]) / 3600
    return base - 0.01 * age_hours

cache = Cache(scorer=penalize_stale, threshold=0.90)
```

fluxcache calls `scorer` once per candidate in the namespace and takes the highest score.

## Bring your own embeddings

Pass any callable that maps `str` to `list[float]`. All vectors in one namespace must have the same length; fluxcache raises `DimensionMismatch` when they do not.

```python
def embed(prompt: str) -> list[float]:
    return openai_client.embeddings.create(
        model="text-embedding-3-small", input=prompt
    ).data[0].embedding

cache = Cache(embed=embed, namespace="text-embedding-3-small")
```

## Exceptions

| Exception | Raised when |
| --- | --- |
| `DimensionMismatch` | A prompt embedding length differs from the namespace's stored length. |
| `BackendError` | The backend rejected a read or write. Wraps the backend's own exception. |

## Requirements

- Python 3.10 or later
- `redis` 5.0 or later for `RedisBackend`

## License

Apache-2.0
