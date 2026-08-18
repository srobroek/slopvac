# fluxcache

Caches LLM responses and returns a cached response when a new prompt is semantically similar to a stored one.

fluxcache embeds each prompt and compares that embedding against stored prompt embeddings by cosine similarity. A match at or above the threshold is a hit, and the stored response is returned. A miss calls your function and stores the result under the new prompt.

## Install

```bash
pip install fluxcache
```

Redis backend:

```bash
pip install "fluxcache[redis]"
```

## Quickstart

```python
from fluxcache import Cache

cache = Cache(threshold=0.92, ttl=3600)

@cache.wrap
def ask(prompt: str) -> str:
    return call_your_model(prompt)

ask("What is the capital of France?")   # miss, calls the model
ask("what's the capital of france?")    # hit, returns the stored response
```

`cache.wrap` keys on the first positional argument. Pass `key=` to key on something else:

```python
@cache.wrap(key=lambda messages: messages[-1]["content"])
def chat(messages: list[dict]) -> str:
    return call_your_model(messages)
```

## Threshold

`threshold` is the minimum cosine similarity for a hit, in the range `0.0` to `1.0`. Default is `0.95`.

| Threshold | Effect |
| --- | --- |
| 1.0 | Exact-embedding matches only |
| 0.95 | Paraphrases and punctuation or case differences |
| 0.85 | Same topic, different question |
| Below 0.8 | Unrelated prompts return each other's responses |

Inspect a lookup before trusting a threshold:

```python
result = cache.lookup("what's the capital of france?")
print(result.hit, result.score, result.matched_prompt)
```

## TTL

`ttl` is the lifetime of an entry in seconds. `ttl=None` stores entries without expiry.

```python
cache = Cache(ttl=86400)                 # one day
cache = Cache(ttl=None)                  # no expiry
```

Per-entry override:

```python
cache.set("What is the capital of France?", "Paris", ttl=60)
```

## Namespaces

A namespace isolates entries. A lookup in one namespace never matches an entry in another. Use one per model, per tenant, or per prompt template version.

```python
gpt = Cache(namespace="gpt-4o")
claude = Cache(namespace="claude-opus")

gpt.set("ping", "pong")
claude.lookup("ping").hit    # False
```

Clear one namespace without touching the others:

```python
gpt.clear()
```

## Backends

### In-memory

The default. Entries live in the process and disappear when it exits. Similarity search is a linear scan over stored embeddings.

```python
from fluxcache import Cache, MemoryBackend

cache = Cache(backend=MemoryBackend(max_entries=10_000))
```

`max_entries` evicts least-recently-used entries once exceeded. `max_entries=None` stores without a bound.

### Redis

Entries are shared across processes and survive restarts. Requires Redis 6.2 or later.

```python
from fluxcache import Cache, RedisBackend

cache = Cache(backend=RedisBackend(url="redis://localhost:6379/0"))
```

`RedisBackend` writes one hash per entry and one embedding index per namespace, all under the key prefix `fluxcache:`. TTL is enforced by Redis key expiry.

## Custom scoring

`scorer` replaces cosine similarity. It receives the query embedding and a candidate embedding as `list[float]` and returns a float compared against `threshold`.

```python
import numpy as np
from fluxcache import Cache

def dot(query, candidate):
    return float(np.dot(query, candidate))

cache = Cache(scorer=dot, threshold=0.9)
```

## Embeddings

The default embedder calls OpenAI `text-embedding-3-small` and reads `OPENAI_API_KEY` from the environment. Supply any callable that maps a string to `list[float]`:

```python
from sentence_transformers import SentenceTransformer
from fluxcache import Cache

model = SentenceTransformer("all-MiniLM-L6-v2")
cache = Cache(embedder=lambda text: model.encode(text).tolist())
```

Embeddings from different models are not comparable. Change the namespace when you change the embedder.

## API

| Member | Description |
| --- | --- |
| `Cache(threshold, ttl, namespace, backend, embedder, scorer)` | Constructs a cache |
| `Cache.wrap(fn)` / `Cache.wrap(key=...)` | Decorator that caches a function's return value |
| `Cache.lookup(prompt)` | Returns `Result(hit, score, response, matched_prompt)` |
| `Cache.set(prompt, response, ttl=None)` | Stores an entry |
| `Cache.delete(prompt)` | Removes the exact-prompt entry |
| `Cache.clear()` | Removes every entry in the namespace |
| `Cache.stats()` | Returns `Stats(hits, misses, entries)` |

## Async

`AsyncCache` mirrors the `Cache` API with awaitable methods and an `await`-able embedder.

```python
from fluxcache import AsyncCache

cache = AsyncCache(threshold=0.92)

@cache.wrap
async def ask(prompt: str) -> str:
    return await call_your_model(prompt)
```

## License

MPL-2.0
