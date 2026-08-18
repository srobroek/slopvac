# Active listening

The parser reads the manifest at startup.
The cache is optional; set `cache.enabled = false` to skip it.
The retry path handles a 429 by waiting for Retry-After.
NOTE: this requires a restart.
You need credentials with the `write` scope.
The fix landed in 2.4.1.
Pooling was added in 2.3.0.
The API changed in the 2026-03 release.
It supports Redis and Postgres.
Only the first match is replaced.
The leading slash is stripped.
A cache hit returns the stored response.

## Configure the pool
