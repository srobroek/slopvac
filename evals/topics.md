# Eval topics

Eight documents across four genres and four subject domains, so a result cannot be
an artifact of one register or one kind of subject matter.

Each is generated four times:

| Run | Condition |
|---|---|
| `01-unguided` | no rules at all |
| `02-current-writedocs` | the write-docs skill as it was before this change |
| `03-new-writedocs` | the new skill plus the always-on steering |
| `04-regenerated` | 03 rewritten after reading its own lint report |

Every run is scored twice: by the old Vale-only gate and by `slopvac-lint`.

## Why these eight

The blog experiment this work started from used 6 prompts, one generation each, no
repetition, and normalized per 100 words on outputs as short as 17 words. Its own
notes say "directional, not proof" while every headline restates the percentages.
So: more subjects, a length floor on the short ones, and the raw counts published
beside the densities.

Two topics are deliberately hostile to the ruleset. `error-message` is short
enough that density is meaningless, which is where the blog's methodology broke.
`adr` is a genre where the rules that ban rationale elsewhere must invert, so a
gate that fires on it is wrong rather than strict.

## The prompts

Each prompt names the artifact and the audience and nothing about style. A prompt
that asked for "clear writing" would contaminate the unguided condition, which
exists to measure what a model does by default.

### 1. `readme-cache` -- README, infrastructure

Write the README for `fluxcache`, a Python library that caches LLM responses by
embedding the prompt and matching it against cached prompts above a similarity
threshold. It has a configurable threshold, a TTL, namespacing, and a custom
scoring hook. It supports Redis and in-memory backends. Audience: a Python
developer who has not seen it before.

### 2. `readme-parser` -- README, developer tooling

Write the README for `xisf-header`, a Rust crate that reads the XML header out of
an XISF astronomical image file without decoding the image data. It exposes the
header as a typed struct, handles both the monolithic and distributed XISF forms,
and returns a parse error naming the byte offset. Audience: a Rust developer.

### 3. `api-docs-webhook` -- reference documentation, backend

Write the reference documentation for a webhook delivery endpoint. It accepts
POST with a JSON body, signs each delivery with an HMAC-SHA256 header, retries
five times with exponential backoff, and delivers at least once so a consumer
must be idempotent. Document the request shape, the signature verification, the
retry schedule, and every response code. Audience: an integrator writing a
receiver.

### 4. `runbook-failover` -- runbook, operations

Write the runbook for failing a Postgres primary over to its replica. It covers
checking replication lag, fencing the old primary, promoting the replica,
repointing the connection pooler, and verifying writes. There is a destructive
step that cannot be undone. Audience: an on-call engineer at 03:00 who has not
done this before.

### 5. `pr-description` -- change communication

Write the pull request description for a change that replaces a per-request
database connection with a pooled one, adds a 30-second checkout timeout, and
fixes a leak where a failed transaction never returned its connection. It touches
four files and adds two tests. Audience: a reviewer.

### 6. `adr-queue` -- internal decision record

Write the architecture decision record for choosing a managed queue over
self-hosting one. The constraints were a two-person team, an existing cloud
account, and a requirement to survive a zone outage. Self-hosting was rejected on
operational load; a second managed option was rejected on cost at the expected
volume. Audience: a contributor in a year's time.

### 7. `error-message` -- product copy, short form

Write the user-facing error message for a rate limit. The limit is 100 requests
per minute per account, the window rolls, and the response carries a
`Retry-After` header. Say what happened, why, and what to do. Audience: a
developer who just hit it.

### 8. `guide-migration` -- guide, data

Write the migration guide for moving a project from v1 to v2 of a config file
format. Three keys were renamed, one was removed, and nested tables replaced a
flat namespace. There is an automated converter for the renames but not for the
nesting. Audience: an existing user upgrading.
