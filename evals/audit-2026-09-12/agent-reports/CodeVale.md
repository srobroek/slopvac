## Summary
Checked the Vale compiler/runner/cache, pipeline partition, verified-style fixture, and all requested failure modes against baseline 2.2.0 with Vale 3.21.0.
Normal routes 145/166 mechanical rules to Vale, 21 native, and 67 judgement; `--no-vale` runs only the 21 native rules and exits 2.
Highest-impact defects: five substitution rules lose their concrete replacement, Vale spans use the wrong end-column convention, and the documented Vale >=3.15 floor is not enforced or cached.
A source-line-anchored compiled rule changes meaning under Vale block parsing and misses a Markdown soft-break case the native regex catches.
Vale uniquely supplies POS-tagged `sequence` matching for a configured vocabulary; with the default empty blocklist it supplies no unique rule id.

## Findings

### F1: Preserve replacements for regex-ending substitution keys
- surface: `compile_vale.py:534-586`; `prose-craft.wordiness`
- kind: defect
- evidence: `_needs_existence_fallback` tests the final source character (`return any(not key[-1:].isalnum() and key[-1:] not in ")]}") ...)`). This mistakes regex syntax for the matched suffix: wordiness keys such as `ascertain(?:s|ed)?` end in `?` but every accepted match ends in a letter. It converts the entire rule to `existence` and hard-codes `a simpler word`. Generated styles show five affected rules: `prose-craft.directional-ref`, `prose-craft.latinisms`, `prose-craft.versions`, `prose-craft.wordiness`, and `ste-practices.latin-abbreviation`. Reproduction on `In conclusion, we will simply utilize ...`: direct `Engine(...).run(parse(...))` returned `wordy: use 'use' instead of 'utilize'`; `slopvac lint /tmp/codevale-probe.md --profile normal --format json --config /dev/null` returned `wordy: use 'a simpler word' instead of 'utilize'`.
- proposal: Decide fallback per substitution key from the regex's possible terminal character, or split punctuation-ending keys into a separate existence payload, rather than degrading a whole map based on `key[-1]`. Preserve the matched key's replacement.
- expected effect: correctness/actionability for five compiled rules. Baseline: `prose-craft.wordiness` fires 1.51/1k human words and 0.30/1k AI words.
- confidence: high

### F2: Convert Vale's inclusive span end to the shared exclusive convention
- surface: `vale.py:207-217`
- kind: code-bug
- evidence: native findings use `end_column=match.end()+1` (`engine.py:697-698`), an exclusive 1-based end; Vale returns inclusive `Span[1]`, but the runner copies it unchanged. Ten same-sentence probes all differed by one while line/start/match agreed:

  | rule | native end | Vale end |
  |---|---:|---:|
  | `ai-tells-structure.summary-closer-frames` | 14 | 13 |
  | `prose-craft.first-person-plural` | 19 | 18 |
  | `prose-craft.future-tense` | 24 | 23 |
  | `prose-inflation.borderline-hype` | 30 | 29 |
  | `prose-craft.wordiness` | 38 | 37 |
  | `orwell.unsupported-evaluative` (`robust`) | 47 | 46 |
  | `prose-inflation.slop-lexicon` (`robust`) | 47 | 46 |
  | `prose-format.no-unicode-dash` | 68 | 67 |
  | `prose-inflation.additive-hedge` | 101 | 100 |
  | `prose-craft.politeness` | 130 | 129 |

  Reproduction: direct native Engine over `/tmp/codevale-probe.md` versus `uv run --project /tmp/slopvac-baseline/packages/slopvac-lint slopvac lint /tmp/codevale-probe.md --profile normal --format json --config /dev/null`. `report.py:351-352` forwards this into SARIF `endColumn`, whose convention is exclusive.
- proposal: map Vale alerts with `end_column=span[1] + 1`; retain start unchanged.
- expected effect: correctness for every Vale finding (145 routed rule ids at normal), including editor/SARIF highlighting.
- confidence: high

### F3: Enforce the Vale version floor and include it in cache routing
- surface: `vale_probe.py:77-113`; `vale_cache.py:106-144`
- kind: code-bug
- evidence: README says “Vale 3.15 or later”, but probe/runner never invokes `vale --version`. The fingerprint hashes compiler sources, rules, levels, profile, and vocabulary, but not Vale binary/version even though probe acceptance determines routing. Wrapper `/tmp/codevale-old` reports `vale version 3.14.0` and delegates other calls. With a tree primed in `SLOPVAC_CACHE_DIR=/tmp/codevale-cache`, lint returned `exit 1 findings 16 unchecked []`; no version warning or exit 2 occurred. A tree compiled by one Vale release is reused by another without re-probing.
- proposal: parse the resolved binary's version before cache lookup, reject `<3.15` as unchecked/exit 2, and include Vale semantic version (preferably resolved binary identity plus version) in the fingerprint/manifest.
- expected effect: correctness across developer/CI upgrades and downgrades.
- confidence: high

### F4: Keep source-line-anchored patterns out of block-scoped Vale checks
- surface: `ai-tells-agentic.yml:303-312`; `compile_vale.py:557-568`
- kind: fn-gap
- evidence: `ai-tells-structure.rhetorical-question-transition` is documented as anchored to a question occupying a whole line and uses `(?m)^...?$` at `scope: prose`. `/tmp/codevale-softbreak.md` contained `What is the TTL?\nIt is 60 seconds.` Direct native Engine returned `('ai-tells-structure.rhetorical-question-transition', 1, 1, 16, 'What is the TTL?')`; Vale lint returned `[]`. `_vale_pattern` preserves `(?m)`, but Vale removes the Markdown soft break before applying the text-scope regex, silently changing source-line semantics to block semantics.
- proposal: keep source-line-anchored prose rules native, or compile them to a raw mechanism that masks fences and preserves line boundaries. Keep this soft-break case as the routing oracle.
- expected effect: FN down for this rule; baseline AI density 0.10/1k, human 0.14/1k.
- confidence: high

### F5: Remove stale claims that upstream Vale ai-tells styles stay enabled
- surface: `ai-tells-agentic.yml:44-52` and similar provenance notes
- kind: steering-drift
- evidence: the note says upstream `ai-tells.ContrastiveNegation` and `ai-tells.ContrastiveFormulas` “stay enabled”, but generated `.vale.ini` enumerates only slopvac ids, the manifest contains no `ai-tells.*`, and `pyproject.toml:62-64` says `vale/styles-verified/` is a test fixture, not runtime data. That fixture contains only 12 `hedge`/`mos` files. Actual semantic duplicates observed: `prose-craft.wordiness` + `ste-words.approved-word-substitution` on `utilize`; `orwell.unsupported-evaluative` + `prose-inflation.slop-lexicon` on `robust` and `seamless`.
- proposal: delete “stay enabled/expect duplicate findings” claims for absent upstream styles. Elect one owner for exact shipped lexical overlaps or exclude the other owner's tokens.
- expected effect: documentation correctness and duplicate findings down. Baseline AI density: `unsupported-evaluative` 0.71/1k and `slop-lexicon` 1.52/1k.
- confidence: high

## Engine division and architecture

- `uv run --project /tmp/slopvac-baseline/packages/slopvac-lint slopvac compile --outdir /tmp/codevale-compiled --profile normal --config /dev/null --format json` produced 145 Vale rules, 21 native, 67 judgement, 0 disabled, and 145 generated YAML files.
- The 21 native routes are: `ai-tells-structure.emphasis-paragraph-metric`, `ai-tells-register.uniform-paragraph-mass`, `ai-tells-formatting.em-dash-density`, `ai-tells-formatting.bold-spray`, `ai-tells-formatting.inline-header-list`, `ai-tells-content-shape.adjective-per-noun-spray`, `prose-format.prose-block`, `ste-descriptive.sentence-too-long-descriptive`, `ste-nouns.multiword-noun-too-long`, `ste-practices.inconsistent-wording-for-same-step`, `ste-procedural.sentence-too-long-procedural`, `ste-punctuation.colon-terminates-sentence-for-count`, `ste-safety.safety-block-missing-consequence`, `ste-sentences.complex-text-not-in-vertical-list`, `ste-sentences.vertical-list-lead-in-missing-colon`, `ste-sentences.vertical-list-item-punctuation`, `ste-words.inconsistent-term-for-same-thing`, and vocabulary routes `ste-verbs.verb-form-not-listed`, `ste-words.word-used-in-wrong-part-of-speech`, `ste-words.verb-or-adjective-form-not-permitted`, `ste-words.word-outside-controlled-vocabulary`.
- `--no-vale` does not fall back to native execution for Vale-owned rules. Output: `--no-vale skipped ... 145 of the 166 mechanical rules ... only the 21 rules that stayed native`; exit 2. It found 2 native density findings on the 22-word probe versus 16 with Vale.
- Direct Engine can execute all active token/pattern/substitution/metric/structure rules (`engine_rules 165`, `unimplemented_metrics []`) but has no `RuleKind.VOCABULARY` dispatch. Vale's unique shipped capability is POS-tagged `sequence` evaluation of a configured blocklist under owner `ste-words.word-outside-controlled-vocabulary` (plus generated POS aliases). With default `/dev/null` config there is no blocklist and no uniquely Vale-provided rule id. Vale supplies its own markup scoping and Tengo, but every current deterministic metric/structure rule has a native implementation.
- Removing Vale while running all 165 native mechanical rules would remove the external binary, 47,929-byte compiler, and 20,549 bytes of runner/cache/probe plus current semantic divergence. It needs a replacement for configured POS vocabulary and a deliberate native parser contract. Making the current path opt-in without changing pipeline partition would leave 145 rules unchecked and default to exit 2, so it is not a viable cutover.

## Cache and concurrency

- Root: `SLOPVAC_CACHE_DIR`, then `$XDG_CACHE_HOME/slopvac`, then `/tmp/slopvac-cache`.
- Key: compiler source digest (`compile_vale.py`, `vale_cache.py`, `vale_probe.py`), serialized rules, resolved levels, profile, normalized blocklist. Locale injection changes rule content, so locale invalidates. Slopvac version does not; Vale binary/version does not (F3).
- Publication uses private staging, manifest-last, rename, and `fcntl.flock` around publication/pruning. Two Python `subprocess.Popen` lints sharing an empty `/tmp/codevale-race` returned `[(1, ''), (1, '')]`, then `manifests 1 building 0 replaced 0`: the inter-process race fix holds.
- Stale edit: first `--rules-dir /tmp/codevale-rules` compile used key `d3c2096b4e887f8d`; after changing only the `slop-lexicon` message, the next used `eb78b4a214aca4d7`. Rule content invalidation works.

## Failure modes

- Missing Vale: 2 native findings + unchecked “145 rules ... did NOT run”; exit 2. Correct.
- `--no-vale`: 2 native findings + explicit 145/166 unchecked; exit 2. Correct.
- Too old: wrapper reported 3.14.0; lint produced 16 findings, no unchecked, exit 1. Incorrect (F3).
- Crash mid-run: wrapper exit 9, `simulated-crash`; 2 native findings + unchecked `Vale failed (9)...`; exit 2. Correct.
- Timeout: direct runner with `TIMEOUT_SECONDS=0.1` and sleeping binary returned `Vale timed out after 0.1s; its rules did NOT run.` Unchecked means CLI exit 2. Correct.
- Runtime rejected regex: simulated E201 after successful `ls-config` returned `Vale rejected a compiled rule (E201) and therefore linted NOTHING`; unchecked/exit 2. Compile probe routes rejected payloads native before publication.
- Non-UTF8: `The \xff robust cache` made Vale 3.21.0 panic (`runtime error: index out of range`); slopvac retained native output, reported unchecked, exited 2. Correct containment.

## Decommission candidates

- Default Vale execution: candidate after replacing configured POS-vocabulary matching; it uniquely owns no rule in the default configuration while imposing 68,478 bytes and observed semantic drift.
- `vale/styles-verified/`: test-only. Retain only if its 12 historical upstream probes justify a separate surface; otherwise migrate probes to generated rules.
- Stale upstream-overlap provenance notes: remove now.
- Exact lexical overlaps: elect one owner or exclude duplicate tokens.

## Checked and fine

- Judgement rules stay out of deterministic engines.
- Pipeline partitions engines, so one qualified rule id is not executed twice.
- `resolved_checks` makes missing loaded checks loud.
- E201/regex errors are inspected on stderr only.
- Rule, level/profile, blocklist, compiler-source, and locale changes invalidate cache.
- Locked atomic publication survived the requested empty-cache race.
- Missing/skip/crash/timeout/runtime rejection/non-UTF8 panic become unchecked and exit 2.
- Installed Vale accepted shipped lookbehind, backreference, and inline-flag payloads; Vale is not stock RE2 here. `_vale_pattern` only translates Python `\UXXXXXXXX` escapes and preserves escaped literal `\\U` forms.
