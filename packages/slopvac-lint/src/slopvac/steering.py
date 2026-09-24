"""Project-local agent steering for slopvac.

The managed block stays small. Detailed lint and judgement guidance comes from
the installed CLI through slopvac prime, so harness instructions do not duplicate
the rule catalogue or drift with the implementation.
"""

from __future__ import annotations

from pathlib import Path

BEGIN = "<!-- slopvac:begin -->"
END = "<!-- slopvac:end -->"

_HARNESS_PATHS = {
    "agents": "AGENTS.md",
    "codex": "AGENTS.md",
    "omp": ".omp/AGENTS.md",
    "kiro": ".kiro/steering/slopvac.md",
    "claude": "CLAUDE.md",
}

STEERING_BLOCK = """\
<!-- slopvac:begin -->
## Slopvac

Before writing or reviewing prose, run `slopvac prime` and follow the current
CLI guidance. Use `slopvac prime judgement` for contextual model review.
Use `slopvac rules` and `slopvac explain <rule_id>` for rule details and
named exceptions.

Treat lint exit 2 as incomplete. Vale 3.15 or later is optional but highly
recommended for full deterministic coverage.
<!-- slopvac:end -->
"""

LINT_PRIME = """\
# Slopvac lint guidance

- Run `slopvac lint <paths> --format json` against the project configuration.
- Treat exit 0 as a completed pass, exit 1 as a threshold failure, and exit 2 as
  an incomplete or invalid run. Do not report exit 2 as clean.
- Vale 3.15 or later is optional but highly recommended because most checked
  rules route through Vale. Inspect `documents[].unchecked` in JSON output.
- Use `slopvac rules` to inspect the active catalogue and
  `slopvac explain <rule_id>` for rationale, examples, fixes, and named
  suppression reasons.
- Fix prose before changing policy. Use only suppression reasons listed by
  `slopvac explain`; report unexplained false positives instead of inventing
  exceptions.
- `slopvac --fix <paths>` applies only deterministic, unambiguous
  replacements. Review the resulting diff.
- Linting does not prove factual correctness. Verify commands, paths, defaults,
  versions, and behavioral claims against the implementation or another
  authoritative source.
- For consumer documentation, describe shipped behavior and reader actions.
  Remove superseded features, implementation chronology, repository archaeology,
  rejected alternatives, and internal tradeoffs unless the reader needs one to
  operate or verify the artifact. Keep deltas in change communications and
  rationale in decision records.
- Apply a deletion test before polishing: if a paragraph, list item, table row,
  or sentence changes no reader action or understanding of the current contract,
  remove it.
- Use `strict` for reference/procedural material, `normal` for READMEs,
  guides, internal docs, and change communications, and `relaxed` for informal
  prose. These profiles do not replace factual verification.
"""

JUDGEMENT_PRIME = """\
# Slopvac judgement guidance

Judgement rules are contextual and do not change deterministic lint pass/fail.
The CLI prepares and validates the work; the harness or provider makes model
calls. Contextual review still depends on available evidence. A provider prompt
cannot fetch repository files, citations, or external sources by itself: verify
those claims with the harness's tools, or abstain when the required evidence is
not present.

1. Prepare an agent-readable run:
   `slopvac judgement brief <paths> --out .slopvac-judgement --packs fired`
   Use `--packs all` when contextual review must not depend on deterministic
   findings.
2. Dispatch each call from `brief.json` or `prompts.jsonl` using the supplied
   system prompt, user payload, and response schema.
3. Validate every response before appending it:
   `slopvac judgement validate --run .slopvac-judgement --file response.json`
4. Aggregate responses:
   `slopvac judgement finish --out .slopvac-judgement --responses .slopvac-judgement/responses.jsonl`
5. Compare deterministic and judgement results:
   `slopvac judgement compare --out .slopvac-judgement`

`validate` checks response structure and expected results. `finish` performs
host evidence checks and coverage accounting. Check failed, truncated, and
not-run units before interpreting a report with no confirms.
"""


def harness_path(root: Path, harness: str) -> Path:
    """Return the steering file for a supported harness."""
    try:
        name = _HARNESS_PATHS[harness]
    except KeyError as exc:
        raise ValueError(f"unknown harness: {harness}") from exc
    return root / name


def harnesses() -> tuple[str, ...]:
    return tuple(_HARNESS_PATHS)


def managed_block_state(path: Path, block: str = STEERING_BLOCK) -> str:
    """Return missing, current, stale, or malformed for one managed block."""
    if not path.exists():
        return "missing"
    original = path.read_text(encoding="utf-8")
    begin_count = original.count(BEGIN)
    end_count = original.count(END)
    if begin_count != end_count or begin_count > 1:
        return "malformed"
    if begin_count == 0:
        return "missing"
    start = original.index(BEGIN)
    end = original.index(END, start) + len(END)
    installed = original[start:end].strip()
    expected = block.strip()
    return "current" if installed == expected else "stale"


def update_managed_block(path: Path, block: str = STEERING_BLOCK) -> bool:
    """Insert or replace the managed block without touching surrounding text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    begin_count = original.count(BEGIN)
    end_count = original.count(END)
    if begin_count != end_count or begin_count > 1:
        raise ValueError(f"{path} contains malformed slopvac managed markers")

    block = block.rstrip() + "\n"
    if begin_count:
        start = original.index(BEGIN)
        end = original.index(END, start) + len(END)
        updated = original[:start] + block.rstrip("\n") + original[end:]
    else:
        prefix = original.rstrip()
        updated = (prefix + "\n\n" if prefix else "") + block

    if not updated.endswith("\n"):
        updated += "\n"
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def remove_managed_block(path: Path) -> bool:
    """Remove only the slopvac block and preserve the rest of the file."""
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    begin_count = original.count(BEGIN)
    end_count = original.count(END)
    if begin_count == 0 and end_count == 0:
        return False
    if begin_count != end_count or begin_count > 1:
        raise ValueError(f"{path} contains malformed slopvac managed markers")

    start = original.index(BEGIN)
    end = original.index(END, start) + len(END)
    before = original[:start].rstrip()
    after = original[end:].lstrip()
    if before and after:
        updated = before + "\n\n" + after
    else:
        updated = before or after
    if updated and not updated.endswith("\n"):
        updated += "\n"
    path.write_text(updated, encoding="utf-8")
    return True


ONBOARD_TEXT = """\
# Slopvac agent setup

Run `slopvac init` for generic `AGENTS.md` steering, or
`slopvac setup --list` and `slopvac setup <harness>` for a harness-specific
target. The managed block stays intentionally small.

Run `slopvac prime` whenever you need the current detailed lint and judgement
workflow. Use `slopvac prime lint` or `slopvac prime judgement` for one layer.
"""

def prime_text(topic: str) -> str:
    if topic == "lint":
        return LINT_PRIME
    if topic == "judgement":
        return JUDGEMENT_PRIME
    if topic == "all":
        return LINT_PRIME.rstrip() + "\n\n" + JUDGEMENT_PRIME
    raise ValueError(f"unknown prime topic: {topic}")
