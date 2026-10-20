# Writing guidance and semantic review

Lint checks rules decided by patterns. Readers judge other rules. Prime topics
turn those judgement rules into instructions for writing and review.

Slopvac makes no model calls. The agent that reads the guidance does the
semantic review.

## Commands

| Command | Prints |
| --- | --- |
| `slopvac prime` | How to run each command, the genre and profile tables, report keys, exit codes, directives and exclusions, and when to run the two topics below |
| `slopvac prime write` | The genre and profile tables, the documentation contract, a writing workflow, the order for excluding content, and one fix per judgement rule |
| `slopvac prime review` | The genre and profile tables, the review workflow, the suppression checks, the verdict format, and one question per judgement rule |

All three only print. Each reads `[guidance]` from the nearest slopvac config
in or above the working directory; `--config PATH` names another file, and
`--rules-dir DIR` adds house rules to the topics.

The judgement lists come from the loaded rule catalogue, grouped by category
and sorted by rule id. A house rule with `kind: judgement` in a `--rules-dir`
`slopvac explain <rule_id>` shows a rule's question, fix, and worked examples
when those fields are defined. `slopvac rules --kind judgement` lists all
judgement rules.

## When an agent runs them

The base `slopvac prime` output directs the agent to run `slopvac prime write`
before drafting and `slopvac prime review` before hand-off. When
`[guidance] review = "ask"`, it asks the user before the review.

The managed steering block in `AGENTS.md` or a harness file points agents to
`slopvac prime`. Harnesses with project skill support also get the thin
`slopvac-prose` skill.

## What each topic prints

`slopvac prime` prints these sections, in order:

- Core rules and the writing and review steps that `[guidance]` turns on.
- The commands, grouped by purpose.
- The genre table and the profile table.
- Inputs, results, Vale, fixes and suppressions, configuration, and agent setup.
- Common workflows as one shell block.
- A command reference that gives the usage of each command and lists each
  argument and option with its values, default, and help.

The command reference comes from the installed command tree. The genre table
comes from `genres.py`. The profile gates and the categories each profile turns
off come from the profile defaults in `config.py` and `profiles.py`. Report keys
and exit codes come from the report models and the pipeline.

`slopvac prime write` and `slopvac prime review` open with the same genre and
profile tables. Their genre table adds the checklist categories for each genre.
The write topic then prints the documentation contract, a writing workflow, and
the order in which to exclude text that is not authored prose. The review topic
prints the review workflow, which audits each directive, and the verdict block,
which has a `Suppressions` line. It includes a reviewer pass for
`review_depth = "subagent"` or `"adversary"`; at `"self"`, the author applies
the review steps without a separate reviewer pass. An unjustified suppression
makes the verdict REVISE.

`slopvac explain <rule_id>` lists the named exceptions that an allow directive
can cite. [Suppressions and exclusions](suppressions.md) gives the full
directive grammar and the config controls.

Each topic ends with one entry per judgement rule, grouped by category. Each
category heading names the genres it suits. [The rules reference](rules.md)
gives the current number of judgement rules.

| Topic | Entry format |
| --- | --- |
| `slopvac prime write` | `` `<category>.<rule-id>` (<scope>): <fix> `` |
| `slopvac prime review` | `` `<category>.<rule-id>` (<scope>): <question> `` |

The scope is the unit the rule judges: a sentence, a paragraph, or the whole
document. Before the entries, each topic explains the scopes and the three
tiers, `enforced`, `advisory`, and `excluded`. It also names the two commands
that give more detail on a rule:

- `slopvac explain <rule_id>` prints the question, the fix, and worked examples.
- `slopvac rules --kind judgement --profile <profile> --format json` gives each
  rule's `tier` at that profile.

An excerpt of the review checklist:

```text
### AI tells -- content shape (`ai-tells-content-shape`), recommended for: consumer, internal, change-comms

- `ai-tells-content-shape.elegant-variation` (document): Does this document refer to one thing by two or more different names without saying they are the same thing?
```

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

`slopvac init` creates `slopvac.toml` when absent and keeps it unless `--force`
is set. Without `--harness`, it writes generic `AGENTS.md` steering and no
skill. Each `--harness` writes that harness's steering and replaces the generic
default; add `--harness agents` to keep it. The `agents` harness has no skill.
`--no-skills` writes steering only. `--skip-agents` writes only the config and
cannot be combined with `--harness` or `--no-skills`.

`slopvac setup <harness>` writes, checks, or removes steering for one harness.
It never writes the config and uses default `[guidance]` settings when no config
exists. `--check` exits 0 when all items are current or disabled, 1 when any are
missing or stale, and 2 for a malformed file. `--remove` deletes the managed
steering block and skill. It deletes the skill directory only when empty.
`--list` prints harness names and their steering and skill paths.

The skill carries a `slopvac:managed` marker. Setup refuses to overwrite or
delete a skill without that marker, refuses a skill directory that resolves
outside the project, and writes each file atomically.
