# Ship on Friday. Sleep on Saturday.

**Flagpost is the hosted feature-flag service built for the people who own the platform, not just the feature.** Sub-millisecond evaluation at the edge, one control plane for every service, and an audit trail your compliance team will actually accept.

[Start free](#) · [Book a 20-minute demo](#)

---

## One flag registry. Every runtime you support.

Your Go services, your Python data jobs, your React apps, and that one Java monolith nobody names out loud — they all read the same flags from the same registry. Flagpost ships first-party SDKs for 11 languages plus an OpenFeature provider, so teams that already standardized on OpenFeature can point at us and change nothing else.

Flags are declared as code, reviewed in pull requests, and synced to the control plane on merge. Drift between what's in Git and what's live is impossible: the API rejects any mutation that doesn't originate from a signed manifest or an authorized runtime override.

- Local evaluation via streamed rulesets — no network hop in the request path
- Deterministic bucketing, so the same user lands in the same variant across services
- 100 ms p99 propagation to every connected SDK, worldwide

## Guardrails that make self-service safe

Platform teams get blamed for outages they didn't cause. Flagpost gives you the controls to hand flag ownership to product teams without handing over the blast radius.

Define policy once and let it apply everywhere: require two-person approval on production toggles, cap rollouts at 10% until an SLO window clears, force an expiry date on every temporary flag, and block changes during a freeze. When an SLO burns hot, automatic rollback flips the flag back and posts the reason to Slack before the pager fires.

Stale flags get found and killed. Flagpost tracks evaluation telemetry per flag, per service, and opens a cleanup PR when a flag has served one variant for 30 days.

## Built to be operated, not babysat

Terraform provider, full REST and gRPC APIs, OIDC and SCIM, and RBAC that maps to your existing groups. Every change — who, what, when, from where, and the diff — lands in an immutable log you can stream to S3, Splunk, or Datadog.

Choose managed multi-tenant, a single-tenant VPC, or a self-hosted relay that keeps user attributes inside your network and never sends them to us. 99.99% uptime SLA on the control plane; SDKs keep evaluating from cache even if we go dark.

---

## Teams that stopped writing their own flag service

> "We had a homegrown flag system with a Redis dependency and a 400-line YAML file. Flagpost replaced it in a sprint. The expiry policy alone deleted 180 dead flags from our codebase."
> — **Priya Raghunathan**, Staff Engineer, Platform, Verityx

> "The audit log passed SOC 2 review with zero follow-up questions. That has never happened to us before."
> — **Dan Oyelaran**, Head of Infrastructure, Northmoor Health

Trusted by platform teams at **Verityx**, **Northmoor Health**, **Cadence Rail**, **Brightlane**, and **Optera** — 4,200+ services evaluating 90 billion flags a month.

---

## Give your product teams the switch. Keep your hand on the breaker.

Free for 3 seats and 25 flags, forever. No credit card. Production-ready in an afternoon.

**[Create your workspace](#)** · [Read the docs](#) · [See pricing](#)
