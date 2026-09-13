# gatekeep

`gatekeep` applies token-bucket rate limits per key through memory, Redis, or `net/http` middleware.

## Usage

Create a `Limiter` with a store and these settings:

```go
limiter := gatekeep.New(
	gatekeep.Limiter{
		Rate:  10,
		Burst: 20,
		TTL:   15 * time.Minute,
	},
	gatekeep.NewMemoryStore(),
)
```

Each key receives an independent bucket with the configured rate and burst capacity.

### Check without waiting

`Allow` consumes one token when the key has capacity.

```go
if !limiter.Allow("account-42") {
	return errors.New("rate limit exceeded")
}
```

`Allow` returns immediately when the bucket has no available token.

### Wait for capacity

`Wait` blocks until the key receives a token or the context ends.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "account-42"); err != nil {
	return err
}
```

Use a context deadline to limit how long the caller waits.

## Stores

### In-memory store

Use the in-memory store when one process owns the rate-limit state.

```go
store := gatekeep.NewMemoryStore()

limiter := gatekeep.New(
	gatekeep.Limiter{
		Rate:  25,
		Burst: 50,
		TTL:   10 * time.Minute,
	},
	store,
)
```

Each process maintains separate buckets when multiple processes use in-memory stores.

### Redis store

Use the Redis store when multiple processes must share bucket state.

```go
client := redis.NewClient(&redis.Options{
	Addr: "localhost:6379",
})

store := gatekeep.NewRedisStore(client)

limiter := gatekeep.New(
	gatekeep.Limiter{
		Rate:  25,
		Burst: 50,
		TTL:   10 * time.Minute,
	},
	store,
)
```

The Redis client controls connection addresses, authentication, database selection, and connection pooling.

## HTTP middleware

The `net/http` middleware derives a key from each request and checks its bucket before calling the next handler.

```go
key := func(r *http.Request) string {
	return r.Header.Get("X-API-Key")
}

handler := gatekeep.Middleware(limiter, key)(
	http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}),
)

if err := http.ListenAndServe(":8080", handler); err != nil {
	log.Fatal(err)
}
```

The middleware returns HTTP status `429 Too Many Requests` when the selected bucket has no available token.

Choose a key that represents the protected boundary, such as an account ID, API key, or client address.

## Configuration

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | numeric | `0` | Sets the number of tokens added to each bucket per second. |
| `Burst` | `int` | `0` | Sets the maximum number of tokens that each bucket can hold. |
| `TTL` | `time.Duration` | `0s` | Sets how long the store retains an inactive bucket. |

A successful request consumes one token from its key’s bucket. New buckets can accept up to `Burst` requests before replenishment limits their rate.
