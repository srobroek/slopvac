# Clean-room README experiment

An eval corpus, not source. Nothing here ships. Nothing imports it. No test reads
it. It stays in the repository because it holds measured evidence for the findings
below. One rule fix exists only because it ran.

`make-diffs.sh` generates `DIFFS.md`, the report. After you run the experiment
again, run the script again. Do not hand-edit the report.

## The question

A prose linter may change what an agent writes. It may instead change only what
the agent says about what it wrote. To tell the two apart, someone must write a
document with no knowledge of the ruleset. That condition is harder to arrange than
it sounds. An agent in this repository absorbs the rules from ambient context and
writes to them pre-emptively.

Every run therefore used `claude -p --bare`, which strips:

- hooks
- CLAUDE.md discovery
- plugin sync
- skills

Each prompt also forbade the agent to read:

- the existing README
- the rule YAML
- the profile tables
- the generated rules reference
- any writing-style guidance

## The chain

| file | what it is |
| --- | --- |
| `README.v1.md` | written from the package source alone |
| `README.v2.md` | v1 rewritten from the mechanical findings |
| `v3/subject.md` | byte-identical copy of `README.v2.md`, the input to the judges |
| `v3/README.v3.md` | v2 rewritten from 62 judgment findings |
| `v3/README.v4.md` | v3 edited again, from the mechanical findings only |
| `README.contaminated.md` | control: the same task without `--bare` |
| `README.human.md` | a snapshot of the hand-written README, which has since moved on |

Each rewriter saw the finding messages and nothing else. That restriction is what
makes the diffs mean something. Each diff shows what a finding *message* changes,
which is all a real user gets.

## The judgment pass

67 of the rules are `kind: judgement`. Each states a question a reviewer answers
and no pattern decides, so nothing in v1 or v2 measured them.

Four read-only judges took `v3/subject.md` and produced 62 findings. Each judge
held one scope:

- sentence
- paragraph
- document
- prose

Splitting the scopes keeps one reviewer from holding all 67 questions at once, and
the split earned itself. The document-scope pass found 11 whole-text shape problems
that no other scope reported.

The judge and the rewriter are separate agents by design. A reviewer that then
fixes its own findings has an incentive to find what it knows how to fix.

## What it found

`DIFFS.md` holds the scores. The result worth stating is the v3 dip: **75.9,
against the 87.3 of the document it replaced.** An editor that sees only the
judgment half fixes what it sees and buys what it cannot see. Nobody told it about
the patterns. v4 supplies the missing half and reaches 93.0. Excluding the
`## Findings not applied` appendix that the prompt required, it reaches 95.7.

That appendix is the other deliberate mechanism. A rewriter may decline a finding.
If a rewriter declines, it records the reason against the rule id and the line.
Every decline v3 made was of one kind: the finding demanded a number the document
did not contain. Nobody can audit a silent non-fix. A recorded one is open to
challenge.

This run also reported a ruleset bug that no test caught.
`ste-sentences.complex-text-not-in-vertical-list` orders the author to turn a
series into a vertical list. Every list needs a stem that says what it enumerates,
and a stem is short by construction, so `emphasis-paragraph-metric` reported it.

Obeying the first rule 15 times took the second from 1 finding to 7. Two shipped
rules, and no move that satisfied both. The exclusion that fixes it, and its two
tests, exist because of this run.

## Reproducing

The prompts survive verbatim:

- `prompt-v1.txt`
- `prompt-v2.txt`
- `v3/prompt-*.txt`
- `v3/prompt-rewrite.txt`
- `v3/prompt-rewrite2.txt`

The agent logs sit beside them. One defect in the prompts limits what the judge
findings prove. The judge prompts originally asserted that "a mechanical
linter has ALREADY passed this document with zero findings". A poisoned compile
cache made Vale lint nothing while it exited 0, which is the only reason that
assertion looked true.

So the judges held a false belief about the document. The prompts now state
the real figure. The 62 findings predate the correction, and nobody regenerated
them.

`.gitignore` covers the rule JSON dumps (`judgement-rules.json`,
`v3/rules-*.json`). They are `slopvac rules --judgement --format json` output at
528K, and the first rule edit takes them stale against the YAML while they still
look authoritative. If you rerun the judges, regenerate them.
