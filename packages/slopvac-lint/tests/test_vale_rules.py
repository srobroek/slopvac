"""Adversarial verification of the compiled Vale rules.

WHY THIS TEST EXISTS. A Vale rule can fail in three ways that all look like a
clean document, and every one of them was hit while authoring these five rules:

  1. Multiple `raw:` list entries are concatenated WITH NO SEPARATOR, so two
     alternatives become one pattern requiring the first to be immediately
     followed by the second. Matches nothing. No error.
  2. `nonword: true` on a `raw:` rule silently stops it matching.
  3. A pattern spanning a clause boundary needs `scope: raw`, because the default
     scope splits the text and cuts the pattern in half.

None of the three produces a Vale error. So the only defence is executing every
rule against a fixture that must fire and a fixture that must not.

THE THIRD FIXTURE IS THE IMPORTANT ONE. `hard.md` holds sentences written
specifically to defeat the patterns after they already passed `must-not-fire.md`.
That pass caught four false positives in `HedgedHedge` that the first negative
fixture missed, because the same person wrote the rule and its negatives. A rule
that passes only fixtures written alongside it has been checked against its
author's assumptions, not against prose.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "vale"
STYLES = Path(__file__).parent.parent / "vale" / "styles-verified"

# Lines in must-fire.md that no pattern reaches, with the reason. Recorded rather
# than deleted: a known miss is a design decision, and an undocumented one is a
# defect. `may avoid certain failures` is the cost of tightening HedgedHedge to
# kill four false positives -- the right trade, because a false positive gets the
# whole rule disabled while a miss falls through to the judgement layer.
KNOWN_MISSES = {
    "The flag may avoid certain failures here.": (
        "one hedge plus a quantified object, which is indistinguishable by pattern "
        "from 'you may need several retries'. Falls to "
        "prose-discipline.hedged-into-uselessness."
    ),
    "This approach is simply better.": (
        "no baseline and no number, so BaselinelessComparative's punctuation "
        "anchor cannot separate it from 'the parser is faster than v1'. Falls to "
        "orwell.unsupported-evaluative."
    ),
}

# Lines in a negative fixture that DO fire, with the reason each is accepted.
# Every entry is a deliberate trade recorded rather than hidden: a rule tuned
# until its fixture passes has been tuned to the fixture, not to prose.
ACCEPTED_SOFT_HITS = {
    "You may need several retries.": (
        "VagueQuantifier on 'several'. A real quantity, so the finding is soft -- "
        "but 'several' is the single commonest evasion in generated prose and the "
        "rule is a warning, so the prompt to name a number is worth the noise."
    ),
    "This might affect various consumers.": (
        "VagueQuantifier on 'various'. Same trade as 'several'."
    ),
    "Various may-flags exist.": (
        "VagueQuantifier on 'Various'. Same trade."
    ),
}

pytestmark = pytest.mark.skipif(
    shutil.which("vale") is None, reason="vale is not on PATH"
)


def _config(tmp_path: Path) -> Path:
    """A Vale config pointing at the verified styles.

    Written per-test rather than committed, because StylesPath must be an absolute
    or config-relative path and the repo checkout location is not fixed.
    """
    styles = tmp_path / "styles"
    shutil.copytree(STYLES, styles)
    config = tmp_path / ".vale.ini"
    config.write_text(
        "StylesPath = styles\n"
        "MinAlertLevel = suggestion\n"
        "\n"
        "[*.md]\n"
        "BasedOnStyles = hedge, mos\n",
        encoding="utf-8",
    )
    return config


def _run(config: Path, target: Path) -> dict[int, list[tuple[str, str]]]:
    """Vale's findings for one file, as {line: [(rule, match)]}."""
    result = subprocess.run(
        ["vale", f"--config={config}", "--output=JSON", "--no-exit", str(target)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    raw = result.stdout.strip()
    if not raw or not raw.startswith("{"):
        # An unparseable payload means Vale itself failed. Never treat that as a
        # clean document.
        raise AssertionError(f"vale produced no JSON: {result.stdout}{result.stderr}")
    data = json.loads(raw)
    findings: dict[int, list[tuple[str, str]]] = {}
    for alerts in data.values():
        for alert in alerts:
            findings.setdefault(alert["Line"], []).append(
                (alert["Check"].split(".", 1)[-1], alert.get("Match", ""))
            )
    return findings


def _lines(path: Path) -> list[tuple[int, str]]:
    return [
        (index, line)
        for index, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1)
        if line.strip()
    ]


def test_every_rule_loads(tmp_path):
    """A rule that fails to load reports every file clean, which is
    indistinguishable from a pass. Vale reports E201 on stdout rather than
    failing, so the payload has to be inspected."""
    config = _config(tmp_path)
    probe = tmp_path / "probe.md"
    probe.write_text("Nothing here.\n", encoding="utf-8")
    result = subprocess.run(
        ["vale", f"--config={config}", "--output=JSON", "--no-exit", str(probe)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "E201" not in result.stdout + result.stderr, (
        f"a rule failed to load: {result.stdout}{result.stderr}"
    )


def test_positive_fixture_fires(tmp_path):
    """Every line in must-fire.md carries a defect one of the rules must catch."""
    config = _config(tmp_path)
    findings = _run(config, FIXTURES / "must-fire.md")

    missed = [
        line
        for number, line in _lines(FIXTURES / "must-fire.md")
        if number not in findings and line not in KNOWN_MISSES
    ]
    assert not missed, f"no rule fired on: {missed}"


def test_weasel_fixture_fires(tmp_path):
    """Wikipedia's weasel-word classes: vague quantifiers, unsupported
    attributions, and comparatives with no baseline. The three have different
    fixes -- a count, a source, and a reference point -- so they are three rules
    rather than one token list."""
    config = _config(tmp_path)
    findings = _run(config, FIXTURES / "weasel-fire.md")
    missed = [
        line
        for number, line in _lines(FIXTURES / "weasel-fire.md")
        if number not in findings and line not in KNOWN_MISSES
    ]
    assert not missed, f"no rule fired on: {missed}"


def test_mos_fixture_fires(tmp_path):
    """Wikipedia's Manual of Style: Words to watch, plus the Vocabulary section.

    Four classes with four different fixes: puffery needs the fact that earns the
    adjective, editorializing and presumptuous language need deletion, an
    expression of doubt needs the status, and a relative time reference needs a
    date. Token lists taken verbatim from the raw wikitext.
    """
    config = _config(tmp_path)
    findings = _run(config, FIXTURES / "mos-fire.md")
    missed = [
        line
        for number, line in _lines(FIXTURES / "mos-fire.md")
        if number not in findings
        and line not in KNOWN_MISSES
        and not line.startswith("#")
    ]
    assert not missed, f"no rule fired on: {missed}"


def test_every_rule_is_a_warning_or_below():
    """No hedging rule errors.

    An ERROR makes an agent rewrite the passage. These patterns are new and
    unproven against a real corpus, so a false error would make an agent "fix"
    correct prose -- worse than a missed finding, because the damage is silent and
    lands in the document.
    """
    import yaml

    for path in sorted(STYLES.rglob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data.get("level") in {"warning", "suggestion"}, (
            f"{path.name} is level={data.get('level')}. Until these are measured "
            f"against a real corpus they stay advisory."
        )


def test_literal_percent_is_escaped():
    """TRAP: Vale runs a pattern through a printf-style formatter, so a literal
    `%` is consumed as a format directive and the rule silently matches nothing.
    Proven: `20 ?% faster` matched nothing where `20 ?%% faster` matched both
    probes."""
    import yaml

    for path in sorted(STYLES.rglob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for pattern in data.get("raw") or []:
            bare = pattern.replace("%%", "")
            assert "%" not in bare, (
                f"{path.name} has an unescaped `%` in its pattern. Write `%%`, or "
                f"the rule matches nothing with no error."
            )


def test_no_lookaround_in_vale_patterns():
    """TRAP: Go RE2 has no lookbehind and no negative lookahead. A pattern using
    either LOADS WITHOUT AN ERROR and matches nothing."""
    import yaml

    for path in sorted(STYLES.rglob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for pattern in data.get("raw") or []:
            for construct in ("(?<", "(?!"):
                assert construct not in pattern, (
                    f"{path.name} uses `{construct}`, which Go RE2 does not "
                    f"support. The rule will load and match nothing."
                )


def test_known_misses_are_still_missed(tmp_path):
    """A known miss that starts firing is good news, and this test failing is the
    signal to delete the entry rather than to widen the rule back."""
    config = _config(tmp_path)
    findings = _run(config, FIXTURES / "must-fire.md")
    for number, line in _lines(FIXTURES / "must-fire.md"):
        if line in KNOWN_MISSES and number in findings:
            pytest.fail(
                f"{line!r} now fires ({findings[number]}). Remove it from "
                f"KNOWN_MISSES."
            )


@pytest.mark.parametrize(
    "fixture", ["must-not-fire.md", "hard.md", "weasel-clean.md", "mos-clean.md"]
)
def test_negative_fixtures_are_clean(tmp_path, fixture):
    """Zero false positives, on both negative fixtures.

    `hard.md` is the one that matters: it was written to defeat the patterns
    after they already passed `must-not-fire.md`, and it caught four false
    positives that the first negative set did not.
    """
    config = _config(tmp_path)
    findings = _run(config, FIXTURES / fixture)
    lines = dict(_lines(FIXTURES / fixture))
    positives = [
        f"L{number} {lines.get(number, '')!r} -> {hits}"
        for number, hits in sorted(findings.items())
        if lines.get(number, "") not in ACCEPTED_SOFT_HITS
    ]
    assert not positives, "false positives:\n  " + "\n  ".join(positives)


def test_multi_entry_raw_list_is_never_used(tmp_path):
    """TRAP 1, enforced structurally.

    Vale concatenates multiple `raw:` entries with no separator, producing one
    pattern that matches nothing. A rule must therefore carry ONE entry holding
    its own alternation.
    """
    import yaml

    for path in sorted(STYLES.rglob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw = data.get("raw")
        if raw is None:
            continue
        assert len(raw) == 1, (
            f"{path.name} has {len(raw)} `raw:` entries. Vale joins them with no "
            f"separator, so the rule matches nothing. Use one entry with `|`."
        )


def test_nonword_is_never_used(tmp_path):
    """TRAP 2, enforced structurally. `nonword: true` silently stops a `raw:` rule
    matching."""
    import yaml

    for path in sorted(STYLES.rglob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("raw") is not None:
            assert not data.get("nonword"), (
                f"{path.name} sets `nonword: true` on a `raw:` rule, which stops "
                f"it matching."
            )


def test_clause_spanning_rules_use_raw_scope():
    """TRAP 3, enforced structurally. A pattern containing a clause join needs
    `scope: raw`, or the default scope splits the text and halves the pattern."""
    import yaml

    joins = ("but", "though", "although", "however", "whereas")
    for path in sorted(STYLES.rglob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw = data.get("raw")
        if not raw:
            continue
        pattern = raw[0]
        if any(f"|{join}|" in pattern or f":{join}|" in pattern for join in joins):
            assert data.get("scope") == "raw", (
                f"{path.name} spans a clause boundary but does not set "
                f"`scope: raw`, so it will silently never fire."
            )
