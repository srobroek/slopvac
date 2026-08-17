# fix(db): pool connections, bound checkout at 30s, release on rollback

## What changed

- `db/session.py`: `get_connection()` returns a connection from a module-level `ConnectionPool` instead of calling `psycopg.connect()` per request. Pool size is 5 minimum, 20 maximum.
- `db/session.py`: `pool.connection(timeout=30)` raises `PoolTimeout` when no connection is free within 30 seconds. The previous per-request connect had no timeout and blocked on the server's `max_connections`.
- `db/session.py`: the `transaction()` context manager releases the connection in a `finally` block. The rollback path returned before releasing, so a connection was leaked on every failed transaction.
- `app/config.py`: adds `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_TIMEOUT` with the defaults above.
- `app/lifespan.py`: opens the pool on startup and calls `pool.close()` on shutdown.
- `api/errors.py`: maps `PoolTimeout` to HTTP 503 with `Retry-After: 5`.

## Why

The leak is the load-bearing part. `transaction()` looked like this:

```python
except Exception:
    conn.rollback()
    raise          # connection never returned
```

Under an error rate above roughly 1%, the process climbed to the server's connection ceiling and then refused all further work until a restart. The 30-second timeout turns the remaining exhaustion case into a 503 rather than an unbounded hang.

## Test plan

Added in `tests/test_session.py`:

- `test_failed_transaction_releases_connection`: runs 50 transactions that raise inside the block, asserts `pool.get_stats()["pool_size"]` is unchanged and `connections_num` did not grow. Fails on `main` at iteration 20 with the pool exhausted.
- `test_checkout_timeout_raises_pool_timeout`: holds `max_size` connections, asserts the next checkout raises `PoolTimeout`, and asserts elapsed time is between 30 and 31 seconds.

Existing suite passes: `pytest` — 214 passed. `test_concurrent_reads` previously opened 40 connections and now runs through the pool of 20.

Manual check against a local Postgres with `max_connections=25`: 200 requests at 50% induced failure, `pg_stat_activity` steady at 20 backends. On `main` the same run exhausted connections after 31 requests.

## Review notes

- `pool.close()` in `app/lifespan.py` waits for in-flight checkouts. A worker with a stuck query will delay shutdown up to the container's grace period.
- `DB_POOL_MAX_SIZE` times the worker count must stay under the server's `max_connections`. At 4 workers this is 80 against a server configured for 100.
- No migration and no API contract change. The 503 on `PoolTimeout` is a new response code on every database-backed route.
