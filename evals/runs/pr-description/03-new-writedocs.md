# fix(db): pool connections, add a 30s checkout timeout, release on rollback

## What changed

- `db/engine.py`: `get_connection()` now checks a connection out of a module-level `ConnectionPool` instead of calling `psycopg.connect()` per request. Pool size 20, overflow 10, `checkout_timeout=30`.
- `db/engine.py`: a checkout that waits longer than 30 seconds raises `PoolTimeout` instead of blocking the worker thread until the client gives up.
- `db/session.py`: the `transaction()` context manager returns the connection in a `finally` block. The previous body returned it only on the success path, so a connection whose transaction raised was never returned to the pool.
- `api/deps.py`: the request dependency yields the pooled connection and maps `PoolTimeout` to HTTP 503 with `Retry-After: 5`.
- `config.py`: three settings read from the environment -- `DB_POOL_SIZE` (default 20), `DB_POOL_MAX_OVERFLOW` (default 10), `DB_CHECKOUT_TIMEOUT_SECONDS` (default 30).

## Why

The leak in `db/session.py` was the reported bug. Each failed transaction lost one connection. With `psycopg.connect()` per request the loss was invisible, because every request opened its own socket and the process closed it on garbage collection. Under a pool the same leak drains all 30 slots, so the release path and the pool have to land together.

The 30-second timeout is the bound on how long a request can wait for a slot. Without it a saturated pool blocks callers with no error, and the caller's own timeout decides the behavior.

## Tests

Two tests in `tests/test_pool.py`:

- `test_failed_transaction_returns_connection` -- runs 40 transactions that each raise inside `transaction()`, then asserts `pool.checked_out() == 0`. This test fails on the parent commit: the pool reports 30 checked out and the 31st transaction raises `PoolTimeout`.
- `test_checkout_timeout_raises` -- holds all 30 slots, sets `DB_CHECKOUT_TIMEOUT_SECONDS=1`, and asserts the next `get_connection()` raises `PoolTimeout` within 2 seconds.

## Test plan

```bash
pytest tests/test_pool.py tests/test_session.py -q
pytest -q                       # 214 passed
```

Manual check against a local Postgres:

```bash
DB_POOL_SIZE=2 DB_POOL_MAX_OVERFLOW=0 uvicorn app:api &
hey -n 200 -c 20 http://127.0.0.1:8000/items
psql -Atc "SELECT count(*) FROM pg_stat_activity WHERE datname='app_db';"
```

`pg_stat_activity` reports 2 backends during and after the run. On the parent commit it reports 20 during the run.

## Reviewer notes

- `config.py` defaults keep the deployed behavior unchanged for anyone who sets no environment variables.
- The pool is created at import time in `db/engine.py`. A test that needs a different size must set the environment variable before importing, which is why `tests/test_pool.py` uses `importlib.reload`.
