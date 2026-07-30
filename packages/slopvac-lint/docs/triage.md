# Warning triage

A warning marks a candidate. The linter reports the shape it matched;
whether that shape is a defect in THIS sentence is often a judgement, and making
that judgement is cheap when the sentence is already in hand.

So a warning carries what a reviewer needs to settle it, and the skill settles
warnings rather than re-reading the whole document. An error still means fix it.

## The two failures triage avoids

Making every rule an error corrupts correct prose. An error makes an agent rewrite
the passage, and a false one lands silently in the document. That is worse than a missed finding, which is why the
hedging and weasel-word rules ship as warnings.

Making every review agentic burns a model pass over text that has nothing wrong
with it. Scanning a clean 4,000-word guide to confirm it is clean is the common
case and the expensive one.

Triage resolves both: the pattern narrows the document to a handful of spans, and
judgement runs only on those spans.

## What a warning carries

`--format json` gives each finding the fields a triage decision needs:

| Field | Use |
| --- | --- |
| `rule_id` | which check, so its question and exceptions can be looked up |
| `line`, `column`, `end_column` | the span, so only that sentence is read |
| `matched_text` | what fired, so a decision does not need the source |
| `replacement` | the fix, where the rule knows it |
| `severity` | `error` is not triaged; `warning` and `suggestion` are |

`slopvac-lint explain <rule_id>` adds the decision question, the closed exception
list, and worked examples.

## The triage question

Every triageable rule answers one question, and the answer is one of three
verdicts:

| Verdict | Means | Action |
| --- | --- | --- |
| `defect` | the shape is a real defect here | apply the fix |
| `exception` | an exception on the rule's list applies | annotate with that reason |
| `false-positive` | neither: the rule matched correct prose | report it, change nothing |

The third verdict is the valuable one. A `false-positive` is evidence about the
RULE rather than the document, and a rule that collects them is a rule to tighten
or demote. Without a verdict for it, a reviewer either edits correct prose or
silently ignores the finding, and neither leaves a trace.

## What triage must not do

MUST NOT Suppress a finding it judged `false-positive`. A suppression annotation
claims a named exception applies, and "the rule is wrong" is not an exception. The
finding stays; the rule gets fixed.

MUST NOT Invent an exception. A reason must appear in that rule's own
`exceptions` list, or the annotation is reported as
`meta.invalid-suppression` rather than honoured.

MUST NOT Triage an error. An error is a rule the project has decided is
never a false positive. Demote it in config if that is wrong.

## Cost

Triage reads the matched span and its sentence, not the document. On the eval
corpus the unguided baseline produced 12.70 to 23.77 findings per 100 words, so a
300-word document yields 40-70 findings, of which the warnings are the triage set.
A clean document yields nothing and costs nothing, which is the point: the
expensive pass runs in proportion to what the cheap pass found.

The document-scope judgement rules are separate and always run, because a ratio
across the whole document is exactly what a per-span pattern cannot see. There are
about 20 of them.

## Recording a false positive

A `false-positive` verdict is only useful if it survives the session. The verdict
report names the rule, the matched text, and the sentence, which is what a rule
change needs. Three of these on one rule from different documents is the signal to
tighten the pattern or drop the token.

The rules already carry two precedents for recording this rather than tuning it
away: `KNOWN_MISSES` holds the true positives given up to remove false
ones, and `ACCEPTED_SOFT_HITS` holds the false positives kept deliberately because
the prompt is worth the noise. Both live in `tests/test_vale_rules.py` with the
reason for each.
