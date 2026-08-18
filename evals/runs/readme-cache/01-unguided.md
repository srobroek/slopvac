# fluxcache

**Semantic caching for LLM applications — because your users don't phrase things the same way twice.**

Traditional caches miss constantly in LLM workloads. Users rarely ask the same question with identical wording, so an exact-match cache sits there with a near-zero hit rate while you pay for every single call. fluxcache solves this by embedding incoming prompts and matching them against previously cached queries within a configurable similarity threshold — unlocking the cost savings that exact-match caching promises but never delivers.

## Why fluxcache?

- 🚀 **Blazing fast** — sub-millisecond lookups on the in-memory backend
- 🎯 **Semantically aware** — catches paraphrases, typos, and reorderings that exact caches miss
- 🔧 **Highly configurable** — thresholds, TTLs, namespacing, and custom scoring
- 🏗️ **Production ready** — battle-tested Redis backend for distributed deployments
- 🪶 **Lightweight** — minimal dependencies, no vendor lock-in

## Installation

```bash
pip install fluxcache
```

## Quick Start

Getting started is dead simple. It ships with sensible defaults so you can have semantic caching running in just a few lines of code:

```python
from fluxcache import FluxCache

cache = FluxCache()

result = cache.get("What is the capital of France?")
if result is None:
    result = call_your_llm("What is the capital of France?")
    cache.set("What is the capital of France?", result)
```

That's it! The second time a user asks "What's France's capital city?" — a completely different string — fluxcache will recognize the semantic similarity and return your cached response.

## Configuration

While the defaults work great for most use cases, fluxcache exposes all the knobs that real applications need as they scale:

```python
cache = FluxCache(
    threshold=0.92,          # similarity threshold for a hit
    ttl=3600,                # seconds before an entry expires
    namespace="chat-v2",     # isolate cache domains
    backend="redis",         # or "memory"
    redis_url="redis://localhost:6379",
)
```

### Similarity Threshold

The threshold is arguably the most important knob you'll tune. Setting it too low means you may potentially serve semantically unrelated responses; setting it too high and you're essentially back to exact matching. Most teams find that somewhere in the 0.85–0.95 range tends to work reasonably well, though your results may vary depending on your domain.

### Custom Scoring

Need more control? You can leverage the custom scoring hook to implement your own similarity logic:

```python
def my_scorer(query_embedding, cached_embedding, metadata):
    base = cosine_similarity(query_embedding, cached_embedding)
    if metadata.get("user_id") != current_user_id:
        return 0.0
    return base

cache = FluxCache(scorer=my_scorer)
```

This is particularly useful for multi-tenant applications where cache isolation is mission-critical.

## Backends

| Backend | Best For | Persistence |
|---|---|---|
| `memory` | Development, single-process apps | ❌ |
| `redis` | Production, distributed deployments | ✅ |

The Redis backend was designed from the ground up to handle the demands of modern high-throughput applications, while the in-memory backend keeps local development effortless.

## How It Works

At its core, fluxcache is elegantly simple:

1. **Embed** — the incoming prompt is converted to a vector
2. **Search** — the vector is compared against cached entries
3. **Decide** — if the best match exceeds your threshold, it's a hit

Think of it like a librarian who understands what you *mean*, not just what you *said*.

## Contributing

Contributions are welcome! Whether you're fixing a typo or building a whole new backend, we'd love to have your help. Please open an issue first to discuss any significant changes.

## Roadmap

- [ ] Pluggable embedding providers (coming soon!)
- [ ] Async API support
- [ ] Prometheus metrics
- [ ] Cache warming utilities

## License

MIT

---

*Built with ❤️ for the LLM community*
