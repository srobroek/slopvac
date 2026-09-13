## Summary

This PR represents a significant step forward in our database connection handling. It's not just a performance optimization — it's a fundamental rethinking of how we manage our most critical resource.

Previously, we were creating a brand new database connection on every single request, which as you can imagine was extremely wasteful and didn't scale well at all. This change leverages a connection pool instead, which should dramatically improve throughput while also laying the groundwork for future scalability improvements we have planned.

## What Changed

- **Connection pooling** — replaced the per-request connection with a pooled implementation
- **Checkout timeout** — added a 30 second timeout so requests fail fast rather than hanging indefinitely
- **Leak fix** — fixed an issue where a failed transaction would never return its connection to the pool

The leak was particularly insidious. Because the connection was never returned, the pool would slowly become exhausted over time, and the symptoms wouldn't manifest until well after the original error had occurred — making it quite difficult to diagnose.

## Files Touched

- `db/pool.py` — new pooled connection manager
- `db/session.py` — updated to use the pool
- `api/middleware.py` — wires the pool into the request lifecycle
- `config.py` — new pool configuration options

## Testing

Two new tests were added to cover the changes. The tests should give us reasonable confidence that the leak is genuinely fixed, though it's worth noting that connection leaks can be notoriously tricky to test comprehensively.

I also did some manual testing locally and things seem to be working well.

## Notes for Reviewers

Happy to discuss any of the design decisions here! I went back and forth on whether the timeout should be configurable per-request versus globally, and ultimately decided that a global setting was cleaner for now — though we could revisit this if there's demand.

This is a first step towards a broader effort to improve our data layer. More to come!
