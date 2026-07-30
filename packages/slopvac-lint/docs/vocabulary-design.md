# Controlled vocabulary: a two-layer design

The vocabulary has two layers.

| Layer | Source | Size | Who owns it |
|---|---|---|---|
| Base | `/tmp/ste100/dictionary.csv`, extracted from the published Issue 9 word list | 2,089 entries: 800 approved, 1,289 not approved | ASD, unmodified by us |
| Overlay | `vocabulary-overlay.yml` | Under 80 entries | Us, with a reason on every line |

The base layer is validated by 40 years of use in aerospace documentation and is traceable to
a page in a published specification. We do not curate it, re-rank it, or drop entries from it.
The overlay is the only place we deviate, it is small enough to read in one sitting, and every
entry states why it exists.

The alternative — hand-authoring a wordlist for software documentation — was rejected. A
hand-built list has no external validation, and a reader cannot check it: a JSON file
containing several hundred words that one team chose is not reviewable, while a 78-line overlay
against a published base is.

## Why the key is (word, part of speech)

A flat word list cannot express the rule that a word is permitted as one part of speech and
refused as another. This is not an edge case in the source data:

| Word | Approved | Not approved |
|---|---|---|
| `test` | noun | verb |
| `check` | noun | verb |
| `damage` | noun | verb |
| `fit` | noun | verb |
| `cover` | (noun, as a domain term) | verb |

124 headwords in the base CSV carry more than one part-of-speech row. `clean` and `set` are
approved as two parts of speech each; the five above are approved as one and refused as
another. A single-status-per-word structure has to pick one, and either choice is wrong.

This is a structural defect in the main third-party wordset in circulation, which stores one
status per word and therefore collapses `test`, `check`, `damage`, `fit`, and `cover` to a
single verdict. That set also disagrees with the primary text on 79 of 1,684 overlapping
headwords. We do not use it.

## Runtime schema

```jsonc
{
  "issue": 9,
  "generated_from": "ASD-STE100 Issue 9 dictionary, column 1",
  "entries": {
    "test|n":  { "status": "approved",   "replacement": null,  "note": null },
    "test|v":  { "status": "unapproved", "replacement": "do a test of",
                 "note": "Use the noun form." },
    "commit|n":{ "status": "approved",   "replacement": null,
                 "source": "overlay",    "reason": "Version-control object; no ASD entry." }
  }
}
```

The key is `word|pos`, lowercased. `status` is `approved` or `unapproved`. `replacement` is a
string or null. Overlay-sourced entries carry `source: "overlay"` and `reason`, so a reader can
diff our deltas from the base without reading the base.

`vocabulary-build.md` gives the exact transformation from the CSV.

## Which source categories transfer to software

The specification excludes domain terms from its word list entirely and instead defines 22
domain-noun categories and 4 domain-verb categories. A term is permitted if it belongs to a
category, whether or not it appears in any list. That mechanism transfers directly; the
category set does not. This analysis is what justifies each overlay entry.

### Domain-noun categories

**Transfer with a renamed scope (9 of 22).** These are the categories a software project
actually populates.

| Source category | Software reading |
|---|---|
| Systems, components, circuits, their functions and configurations | Services, modules, queues, caches, schedulers |
| Computer science, information and communication technology | Already software; the largest category by far |
| Mathematical, scientific, engineering terms and formulas | Algorithms, complexity terms, data structures |
| Numbers, units of measurement and time | Byte and time units, rates, percentiles |
| Quoted text | Error messages, log lines, UI strings |
| Official documents, parts of documentation, standards | RFCs, ADRs, API references, changelogs |
| Professional roles, groups, organizations | Operator, reviewer, on-call, tenant, vendor |
| Environmental and operational conditions | Load, degraded mode, cold start, partition |
| Law and regulations | Licences, data-residency terms, retention rules |

**Do not transfer (11 of 22).** Official parts information; vehicles and machines and locations
on them; tools and support equipment; materials and consumables; facilities and infrastructure
and logistic procedures; navigation and geographic terms; parts of the body; personal effects,
food, and beverages; medical terms; damage terms; animals and plants. Physical-artifact
categories with no software analogue. Note that the source's "facilities and infrastructure"
category is warehouses and hangars, not cloud infrastructure — the word collides, the category
does not.

**Transfer in a narrowed form (2 of 22).** Colors, for UI and status-badge documentation only.
Civil and military operations, only for projects that document them.

**Missing, and needed for software (4 new).** Aerospace has no equivalent, so no source
category covers these and the overlay must:

1. **Version-control and change-management objects** — commit, branch, tag, merge, rebase,
   pull request, diff, patch, revision.
2. **Interface and protocol surfaces** — endpoint, route, header, payload, token, claim, scope,
   webhook, socket, stream.
3. **Data and storage structures** — schema, index, key, field, record, blob, bucket, shard,
   partition, snapshot, migration.
4. **Runtime and deployment topology** — container, pod, node, cluster, replica, region, zone,
   environment, tenant, namespace.

### Domain-verb categories

**Transfers directly (1 of 4).** "Computer processes and applications", which the specification
already divides into input and output, user-interface, and system operations, and which names
`click`, `enter`, `install`, `download`, `reboot`, `update`, `upload`, `debug`, and `format`
among its examples. This category alone covers a large share of software prose.

**Transfers for a narrow slice (1 of 4).** "Law and regulations", for licence and compliance
documentation.

**Does not transfer (2 of 4).** "Manufacturing processes" (six sub-categories, all physical
material). "Instructions for applicable subject fields" — of its six sub-fields, only the
engineering and mathematical one has any software reading; medical, civil and military,
navigation, automotive and railway, and energy and oil and gas do not.

**Missing, and needed (2 new).** No source category covers:

1. **Build and release actions** — build, compile, lint, test, package, publish, deploy,
   promote, roll back, tag.
2. **Concurrency and lifecycle actions** — spawn, schedule, drain, throttle, retry, back off,
   fail over, reconcile, expire, evict.

Note that some of these verbs are explicitly not approved in the base layer — `build`, `run`,
`log`, `execute`, `enable`, `call`, `compile`, `branch` all appear in the CSV as unapproved
verbs. That is not an error in the base; it is the base reflecting an aerospace context where
those words were ambiguous. In software prose `build` and `compile` name specified processes,
which is exactly the domain-verb test. Each such reversal is one overlay entry with a reason.

## The overlay's two directions

Most overlay entries approve something the base refuses or omits. A few go the other way, where
the base is more permissive than we want for software prose — chiefly words the base approves
that read as vague in a technical document. `vocabulary-overlay.yml` marks the direction on each
entry.

The overlay's size limit is a design constraint, not a budget. If the overlay grows past about
80 entries, the project has started re-curating the base, and the reviewability argument for the
two-layer split is gone.

## Residual copyright position

Phase-1 analysis established that the source specification's usage grant runs to eight
enumerated categories of aerospace and defence organization and does not cover a general
software package. That governs what we ship. The position is:

**Facts, and citable.** A rule number. A numeric limit (20, 25, 6, 3). A word, its part of
speech, and its approved-or-not status — a three-field factual assertion about a word, of the
same kind a dictionary headword is.

**Not shipped.** Verbatim rule prose. The specification's example sentences. The
approved-meaning glosses, which are authored prose rather than facts.

**Where the risk actually sits.** Not in any individual triple, but in the compilation. The
selection of which 2,089 words to judge, and how to judge them, is the specification's editorial
work, and a database-style claim attaches to a selection even where the individual facts are
free. Two consequences follow. First, the base layer must be attributed, versioned, and
identified as ASD's selection rather than presented as ours. Second, the overlay exists partly
for this reason: it makes our editorial contribution explicit and separable, so no reader
mistakes ASD's selection for our own work, and so the two can be licensed and reviewed
differently.

**Still open, and a human decision.** Whether the base layer ships inside the package at all,
or is fetched at install time from the extraction and cached locally. Fetching moves the
compilation out of our distribution. This is a legal and packaging call, not a technical one,
and phase 1 already flagged it for a human gate. The trademark is separate: naming a product
after the specification, or implying its endorsement, is its own risk regardless of what the
package contains.
