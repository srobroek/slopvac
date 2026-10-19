# Writing guidance and semantic review

Lint checks rules decided by patterns. Readers judge other rules. Prime topics
turn those judgement rules into instructions for writing and review.

Slopvac makes no model calls. The agent that reads the guidance does the
semantic review.

## Commands

| Command | Prints |
| --- | --- |
| `slopvac prime` | The lint workflow, plus when to run the two topics below |
| `slopvac prime write` | Genre table, documentation contract, and one rewrite per judgement rule |
| `slopvac prime review` | Review workflow, verdict format, genre selection, and one question per judgement rule |

All three only print. Each reads `[guidance]` from the nearest slopvac config
in or above the working directory; `--config PATH` names another file, and
`--rules-dir DIR` adds house rules to the topics.

The judgement lists come from the loaded rule catalogue, grouped by category
and sorted by rule id. A house rule with `kind: judgement` in a `--rules-dir`
directory appears in both topics. `slopvac explain <rule_id>` shows a rule's
question, fix, and worked examples. `slopvac rules --kind judgement` lists them
all.

## When an agent runs them

The base `slopvac prime` output directs the agent to run `slopvac prime write`
before drafting and `slopvac prime review` before hand-off. When
`[guidance] review = "ask"`, it asks the user before the review.

The managed steering block in `AGENTS.md` or a harness file points agents to
`slopvac prime`. Harnesses with project skill support also get the thin
`slopvac-prose` skill.

## Review workflow

`slopvac prime review` prints these steps:

1. Classify the document by genre. Note its profile and checklist categories.
2. Run `slopvac lint --profile <profile>` first. Fix errors, triage warnings,
   and report unchecked rules. Exit 1 means a gate failed; exit 2 means the run
   is incomplete.
3. Ask the enforced and advisory checklist questions for the profile, and skip
   excluded ones. Quote each failure and propose a rewrite.
4. Mark wording that changes no reader action or contract fact. List the
   original facts and confirm each one survived or was wrong.
5. Check claims against the code. Flag claims stronger than their source.
6. Run the configured reviewer pass.
7. Fix or rebut each finding, lint again after edits, and report `PASS` or
   `REVISE`.

The default pass uses one fresh-context subagent. Give it the document and the
`slopvac prime review` output, plus the original and any source or brief. The
subagent runs steps 1 to 5, edits nothing, and does not start another reviewer.
It reports each finding once: rule id, quoted text, proposed rewrite, lost facts,
and claims stronger than the source. The author fixes or rebuts every finding.
The pass does not repeat by default.

Set `review_depth = "self"` for an author-run pass; steps 3 to 5 are the review.
If subagents are unavailable, the author runs the pass and reports
`self (no subagent available)`. Set `review_depth = "adversary"` for repeated
rounds: each round gets the earlier rebuttals, and the loop stops when a round
reports no finding the author accepts. A user can request the loop without
changing the default.

## Configuration

```toml
[guidance]
write = "auto"             # auto | off
review = "auto"            # auto | ask | off
review_depth = "subagent"  # self | subagent | adversary
```

| Key | Value | Effect |
| --- | --- | --- |
| `write` | `auto` (default) | `slopvac prime` directs the agent to run `slopvac prime write` |
| `write` | `off` | Omits the base step; `slopvac prime write` prints a notice and exits 0 |
| `review` | `auto` (default) | `slopvac prime` and `slopvac prime write` direct the agent to review before hand-off |
| `review` | `ask` | The agent asks the user before review |
| `review` | `off` | Omits the step; `slopvac prime review` prints a notice and exits 0 |
| `review_depth` | `subagent` (default) | One fresh-context reviewer pass |
| `review_depth` | `self` | The author applies the reviewer pass |
| `review_depth` | `adversary` | Repeated reviewer rounds until a round reports no finding the author accepts |

`review = "off"` disables review regardless of `review_depth`. Guidance is
project-wide; `[[overrides]]` cannot set it. When both `write` and `review` are
`off`, `slopvac init --harness` and `slopvac setup` install no skill and remove
one they installed earlier.

## The `slopvac-prose` skill

The skill holds only its triggers and the two commands. Its `description`
starts with writing and reviewing READMEs, docs, Markdown, PR or MR text, commit
or release text, and specifications, so each harness can load it without the
user naming it.

| Harness | Skill file |
| --- | --- |
| Codex | `.agents/skills/slopvac-prose/SKILL.md` |
| Claude Code | `.claude/skills/slopvac-prose/SKILL.md` |
| Oh My Pi | `.omp/skills/slopvac-prose/SKILL.md` |
| Kiro | `.kiro/skills/slopvac-prose/SKILL.md` |
| Generic `agents` | none |

Install it with harness steering:

```sh
slopvac init --harness claude --harness omp
slopvac setup codex
```

`slopvac init` without `--harness` writes generic `AGENTS.md` steering and no
skill. Each `--harness` writes that harness's steering and skill;
`--no-skills` writes steering only. `--skip-agents` writes neither and cannot
be combined with `--harness`.

`slopvac setup <harness> --check` reports the skill as `current`, `missing`,
`stale`, `malformed`, or `disabled`. Disabled means both guidance modes are off
and no skill is present. `--remove` deletes the skill and its directory when
empty. Other files in that directory stay.

The skill carries a `slopvac:managed` marker. Setup refuses to overwrite or
delete a skill without that marker, refuses a skill directory that resolves
outside the project, and writes each file atomically.

