# Writing guidance and semantic review

Lint checks the rules a pattern can decide. The 65 judgement rules in the
catalogue need a reader. One asks whether a negative statement changes what the
reader can do; another asks whether a rationale defends an implementation
nobody asked about. Lint never reports these rules.
`slopvac prime write` and `slopvac prime review` turn them into instructions an
agent follows while it writes and before it hands prose off.

Slopvac makes no model calls. The agent that reads the guidance does the
semantic work.

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

The base `slopvac prime` output tells the agent:

- Before drafting or editing a README, docs, a PR or MR description, commit or
  release text, or a specification, run `slopvac prime write`.
- Before handing that prose off, run `slopvac prime review`, or ask the user
  first when `[guidance] review = "ask"`.

The managed steering block in `AGENTS.md` (or the harness file) already tells
agents to run `slopvac prime`, so a harness without skill support still reaches
both topics. Harnesses that load project skills also get the `slopvac-prose`
skill, described below.

## Review workflow

`slopvac prime review` prints these steps:

1. Classify the document by genre: `consumer`, `reference`, `change-comms`,
   `internal`, or `informal`. The genre sets the lint profile and selects the
   checklist categories whose `recommended_for` names it.
2. Run `slopvac lint` first and act on its findings. Exit 2 means the run is
   incomplete.
3. Answer each selected checklist question against the text. Quote the
   offending text and propose a rewrite for every failure.
4. Apply the deletion test to every sentence, list item, table row, and
   paragraph.
5. Verify every factual claim against the code: commands, paths, flags,
   defaults, versions, and behavior.
6. Run the adversary review.
7. Report a `PASS` or `REVISE` verdict in the printed format.

### Adversary review

The author hands the document and the `slopvac prime review` output to a
separate reviewer with fresh context: a subagent, or a second person. The
reviewer looks for failures only and cites each as a rule id, the quoted text,
and a proposed rewrite. The author fixes each confirmed finding or rebuts it
with evidence. The loop repeats until the reviewer reports no confirmed
findings, and the verdict records the rounds and their outcome.

## Configuration

```toml
[guidance]
write = "auto"   # auto | off
review = "auto"  # auto | ask | off
```

| Key | Value | Effect |
| --- | --- | --- |
| `write` | `auto` (default) | `slopvac prime` tells the agent to run `slopvac prime write` |
| `write` | `off` | The line is omitted; `slopvac prime write` prints a one-line notice and exits 0 |
| `review` | `auto` (default) | `slopvac prime` and `slopvac prime write` tell the agent to run `slopvac prime review` before a hand-off |
| `review` | `ask` | The agent asks the user before it runs the review |
| `review` | `off` | The step is omitted; `slopvac prime review` prints a one-line notice and exits 0 |

`[guidance]` is project-wide: a `[[overrides]]` block that sets it fails to
load. With both keys `off`, `slopvac init --harness` and `slopvac setup`
install no `slopvac-prose` skill and remove one they installed earlier.

## The `slopvac-prose` skill

The skill holds only its triggers and the two commands. Its `description`
starts with the use case, writing or reviewing READMEs, docs, Markdown, PR or MR
text, commit or release text, and specifications, so each harness can load it
without the user naming it.

| Harness | Skill file |
| --- | --- |
| Codex | `.agents/skills/slopvac-prose/SKILL.md` |
| Claude Code | `.claude/skills/slopvac-prose/SKILL.md` |
| Oh My Pi | `.omp/skills/slopvac-prose/SKILL.md` |
| Kiro | `.kiro/skills/slopvac-prose/SKILL.md` |
| Generic `agents` | none |

Install it with the harness steering:

```sh
slopvac init --harness claude --harness omp
slopvac setup codex
```

`slopvac init` without `--harness` writes only the generic `AGENTS.md` block
and no skill. Each `--harness` writes that harness's steering block and its
skill; `--no-skills` writes the blocks only. `--skip-agents` writes neither and
cannot be combined with `--harness`.

`slopvac setup <harness> --check` reports the skill on its own line as
`current`, `missing`, `stale`, `malformed`, or `disabled` (both guidance modes
off and no skill present). `--remove` deletes the skill file and its
`slopvac-prose` directory when that directory is left empty. Files beside it
stay.

The skill carries a `slopvac:managed` marker. Setup refuses to overwrite or
delete a `slopvac-prose/SKILL.md` without the marker, refuses a skill
directory that resolves outside the project, and writes each file atomically.
