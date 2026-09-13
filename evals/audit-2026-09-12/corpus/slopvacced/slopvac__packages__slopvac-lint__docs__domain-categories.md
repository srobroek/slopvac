# Domain-term categories for software prose

Three rules ask whether a term belongs to a domain category rather than whether it appears on a
list: `domain-noun-category-membership`, `unapproved-word-not-a-domain-noun`, and
`domain-verb-category-membership`. All three are `kind: judgement`, so a reviewer answers them.
This file is the taxonomy they answer against.

The source specification excludes domain terms from its word list entirely and instead defines 22
domain-noun categories and 4 domain-verb categories. A term is permitted if it belongs to a
category, even where no list names it. That mechanism transfers to software directly. The
category set does not, and this is the mapping.

The same reasoning decides whether a term of your own belongs in prose or in a blocklist entry.
A word that names a member of one of these categories is doing its job; a word that does not is
a candidate for the blocklist, with a reason.

## Why the key is a word plus a part of speech

A term is permitted as one part of speech and refused as another, which a flat word list cannot
express:

| Word | Works as | Does not work as |
|---|---|---|
| `test` | noun | verb |
| `check` | noun | verb |
| `deploy` | verb | noun |
| `return` | verb | noun |
| `cover` | noun, as a domain term | verb |

124 headwords in the source carried more than one part-of-speech row, and software prose has the
same shape. A single-status-per-word structure has to pick one, and either choice is wrong.

That constraint is why `pos` is a required field on a blocklist entry, and why the generated
Vale rules are grouped by part of speech. Vale's `sequence` extension point matches only where
the Penn Treebank tag agrees, so an entry scoped to `verb` flags `close` as a verb and leaves
"close to the limit" alone.

## Domain-noun categories

**Transfer with a renamed scope (9 of 22).** The categories a software project actually
populates.

| Source category | Software reading |
|---|---|
| Systems, components, circuits, their functions and configurations | Services, modules, queues, caches, schedulers |
| Computer science, information and communication technology | Already software; the largest category by far |
| Mathematical, scientific, engineering terms and formulas | Algorithms, complexity terms, data structures |
| Numbers, units of measurement and time | Byte and time units, rates, percentiles |
| Quoted text | Error messages, log lines, UI strings |
| Official documents, parts of documentation, standards | RFCs, decision records, API references, changelogs |
| Professional roles, groups, organizations | Operator, reviewer, on-call, tenant, vendor |
| Environmental and operational conditions | Load, degraded mode, cold start, partition |
| Law and regulations | Licences, data-residency terms, retention rules |

**Do not transfer (11 of 22).** Physical-artifact categories with no software analogue:

- official parts information
- vehicles and machines, and locations on them
- tools and support equipment
- materials and consumables
- facilities, infrastructure, and logistic procedures
- navigation and geographic terms
- parts of the body
- personal effects, food, and beverages
- medical terms
- damage terms
- animals and plants

The source's "facilities and infrastructure" category is warehouses and hangars, not cloud
infrastructure: the word collides, the category does not.

**Transfer in a narrowed form (2 of 22).** Colors, for UI and status-badge documentation only.
Civil and military operations, only for projects that document them.

**Missing, and needed for software (4 new).** Aerospace has no equivalent, so no source category
covers these:

1. **Version-control and change-management objects**: commit, branch, tag, merge, rebase, pull
   request, diff, patch, revision.
2. **Interface and protocol surfaces**: endpoint, route, header, payload, token, claim, scope,
   webhook, socket, stream.
3. **Data and storage structures**: schema, index, key, field, record, blob, bucket, shard,
   partition, snapshot, migration.
4. **Runtime and deployment topology**: container, pod, node, cluster, replica, region, zone,
   environment, tenant, namespace.

## Domain-verb categories

**Transfers directly (1 of 4).** "Computer processes and applications". The specification
already divides it into input and output, user-interface, and system operations. Its examples
name `click`, `enter`, `install`, `download`, `reboot`, `update`, `upload`, `debug`, and
`format`. This category alone covers a large share of software prose.

**Transfers for a narrow slice (1 of 4).** "Law and regulations", for licence and compliance
documentation.

**Does not transfer (2 of 4).** "Manufacturing processes", whose six sub-categories are all
physical material. "Instructions for applicable subject fields": of its six sub-fields, only the
engineering and mathematical one has any software reading, and medical, civil and military,
navigation, automotive and railway, and energy and oil and gas do not.

**Missing, and needed (2 new).** No source category covers:

1. **Build and release actions**: build, compile, lint, test, package, publish, deploy, promote,
   roll back, tag.
2. **Concurrency and lifecycle actions**: spawn, schedule, drain, throttle, retry, back off,
   fail over, reconcile, expire, evict.

The source leaves eight of these verbs unapproved: `build`, `run`, `log`, `execute`, `enable`,
`call`, `compile`, and `branch`. That reflects an aerospace context where the words were
ambiguous. In software prose `build` and `compile` name specified processes, which is the
domain-verb test, so all eight are permitted here.

## Copyright position

Rule numbers and numeric limits are facts and are cited as such. The category names above are
paraphrased, and the software readings are ours. No word list, approved-or-not status, gloss,
rule text, or example sentence from the specification is shipped or read by this package. The
trademark is separate: naming a product after the specification, or implying its endorsement, is
its own risk regardless of what a package contains.
