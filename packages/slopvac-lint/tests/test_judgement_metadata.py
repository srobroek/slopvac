"""Rule taxonomy and the judgement contract.

`dimension` and `ownership` are required on every rule and `judgement_contract` on
every judgement rule, so the failures worth pinning are the ones that would
otherwise ship a rule that LOOKS configured and adjudicates nothing: a seed that
resolves to no rule, a seeded rule with no seed, a contract on a rule no reviewer
ever sees.

These tests load only the fixture directories they write, not the shipped catalog.
The subject is the schema and the loader, so the 230-rule ruleset would only
couple a schema failure to a catalog failure and report the wrong one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.model import (
    Category,
    Dimension,
    Example,
    JudgementContract,
    JudgementDimension,
    Ownership,
    Provenance,
    Rule,
    RuleKind,
    Severity,
)
from slopvac.reference import render_reference
from slopvac.rules import RuleLoadError, RuleSet, load_ruleset

_CONTRACT = """    judgement_contract:
      admission: The unit is a paragraph of at least two sentences.
      protects: A closing sentence that states a fact stated nowhere else.
      dims: [FIT, WARRANT]
      evidence_arity: 1
      judgement_ceiling: suggestion
      rewrite_exempt: false
"""


@pytest.fixture
def fixture_rules(monkeypatch):
    """Load from `extra_dirs` alone.

    `resources.files` on a package that does not exist raises, which `load_ruleset`
    already treats as "no packaged rules", so this is the supported no-catalog
    path rather than a hole punched in the loader.
    """
    monkeypatch.setattr("slopvac.rules.RULES_PACKAGE", "slopvac_no_such_package")

    def load(directory: Path):
        return load_ruleset(extra_dirs=[directory], verify=False)

    return load


def _write(directory: Path, name: str, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


def _category(rules: str, category_id: str = "custom") -> str:
    return (
        f"id: {category_id}\n"
        f"title: Custom\n"
        f"description: Fixture category.\n"
        f"rules:\n{rules}"
    )


def _pattern_rule(rule_id: str = "core", pattern: str = "xyzzy") -> str:
    return (
        f"  - id: {rule_id}\n"
        f"    name: Fixture pattern\n"
        f"    kind: pattern\n"
        f"    dimension: wording\n"
        f"    ownership: deterministic\n"
        f"    message: unused\n"
        f"    pattern: '{pattern}'\n"
        f"    provenance:\n"
        f"      source: test\n"
    )


def _judgement_rule(
    rule_id: str = "remainder",
    *,
    ownership: str = "document_probe",
    seeds: str | None = None,
    extra: str = "",
    contract: str = _CONTRACT,
) -> str:
    body = (
        f"  - id: {rule_id}\n"
        f"    name: Fixture judgement\n"
        f"    kind: judgement\n"
        f"    dimension: redundancy\n"
        f"    ownership: {ownership}\n"
        f"    message: Check it.\n"
        f"    judgement_question: Does this sentence add a fact?\n"
    )
    if seeds is not None:
        body += f"    seed_rule_ids: [{seeds}]\n"
    body += contract
    body += extra
    body += "    provenance:\n      source: test\n"
    return body


# --- exceptions on a judgement rule ------------------------------------------


def test_a_judgement_rule_may_carry_named_exceptions(tmp_path, fixture_rules):
    """The prohibition this replaces was true of a rule that emitted nothing. An
    adjudicated finding IS a finding, so an author must be able to cite a named
    reason against it rather than override it unnamed."""
    _write(
        tmp_path,
        "category.yml",
        _category(_judgement_rule(extra="    exceptions: [quotation, code-span]\n")),
    )
    ruleset = fixture_rules(tmp_path)
    rule = ruleset.by_id("custom.remainder")
    assert rule is not None
    assert rule.exceptions == ["quotation", "code-span"]


def test_a_judgement_rule_still_ships_at_suggestion(tmp_path, fixture_rules):
    """Allowing exceptions must not have promoted judgement rules into the
    mechanical severity band. The confirmable level lives on the contract."""
    _write(tmp_path, "category.yml", _category(_judgement_rule(extra="    severity: error\n")))
    rule = fixture_rules(tmp_path).by_id("custom.remainder")
    assert rule is not None
    assert rule.severity is Severity.SUGGESTION
    assert rule.judgement_contract is not None
    assert rule.judgement_contract.judgement_ceiling is Severity.SUGGESTION


# --- the contract is required exactly where it applies ------------------------


def test_a_judgement_rule_without_a_contract_does_not_load(tmp_path, fixture_rules):
    _write(tmp_path, "category.yml", _category(_judgement_rule(contract="")))
    with pytest.raises(RuleLoadError, match=r"requires `judgement_contract`"):
        fixture_rules(tmp_path)


def test_a_checked_rule_cannot_carry_a_contract(tmp_path, fixture_rules):
    """A rule no reviewer ever sees has nothing to promise one, and a contract
    sitting on it reads as though the reviewer will be called."""
    _write(tmp_path, "category.yml", _category(_pattern_rule() + _CONTRACT))
    with pytest.raises(
        RuleLoadError, match=r"`judgement_contract` is not valid for kind=pattern"
    ):
        fixture_rules(tmp_path)


@pytest.mark.parametrize(
    "rules,expected",
    [
        (
            _judgement_rule(ownership="deterministic"),
            r"kind=judgement cannot be ownership=deterministic",
        ),
        (
            _pattern_rule().replace("deterministic", "document_probe"),
            r"ownership must be deterministic, not document_probe",
        ),
    ],
    ids=["judgement-claims-deterministic", "pattern-claims-probe"],
)
def test_ownership_must_agree_with_kind(tmp_path, fixture_rules, rules, expected):
    _write(tmp_path, "category.yml", _category(rules))
    with pytest.raises(RuleLoadError, match=expected):
        fixture_rules(tmp_path)


def test_a_contract_scored_on_nothing_does_not_load(tmp_path, fixture_rules):
    _write(
        tmp_path,
        "category.yml",
        _category(_judgement_rule(contract=_CONTRACT.replace("[FIT, WARRANT]", "[]"))),
    )
    with pytest.raises(RuleLoadError, match=r"dims` must name at least one scored axis"):
        fixture_rules(tmp_path)


def test_a_repeated_scored_axis_does_not_load(tmp_path, fixture_rules):
    _write(
        tmp_path,
        "category.yml",
        _category(_judgement_rule(contract=_CONTRACT.replace("[FIT, WARRANT]", "[FIT, FIT]"))),
    )
    with pytest.raises(RuleLoadError, match=r"dims` repeats FIT"):
        fixture_rules(tmp_path)


def test_a_ceiling_of_off_does_not_load(tmp_path, fixture_rules):
    """`off` would make every confirm unreachable while the rule still advertised
    a question, which is the silent-pass shape this schema exists to stop.

    Quoted, because YAML 1.1 reads a bare `off` as the boolean False and the
    error would then be about a type rather than about the ceiling.
    """
    _write(
        tmp_path,
        "category.yml",
        _category(
            _judgement_rule(
                contract=_CONTRACT.replace(
                    "judgement_ceiling: suggestion", "judgement_ceiling: 'off'"
                )
            )
        ),
    )
    with pytest.raises(RuleLoadError, match=r"judgement_ceiling` cannot be `off`"):
        fixture_rules(tmp_path)


# --- seeds --------------------------------------------------------------------


def test_a_seed_may_point_into_a_file_loaded_later(tmp_path, fixture_rules):
    """The reason seeds resolve after the whole registry loads. Files are read in
    name order, so `a.yml` naming a rule in `b.yml` is a forward reference the
    catalog legitimately contains."""
    _write(tmp_path, "a.yml", _category(_judgement_rule(
        ownership="seeded_adjudication", seeds="'later.core'"
    )))
    _write(tmp_path, "b.yml", _category(_pattern_rule(), category_id="later"))
    ruleset = fixture_rules(tmp_path)
    rule = ruleset.by_id("custom.remainder")
    assert rule is not None
    assert rule.seed_rule_ids == ["later.core"]


def test_a_seed_that_names_no_rule_does_not_load(tmp_path, fixture_rules):
    _write(tmp_path, "category.yml", _category(_judgement_rule(
        ownership="seeded_adjudication", seeds="'custom.absent'"
    )))
    with pytest.raises(RuleLoadError, match=r"seed 'custom.absent' names no rule"):
        fixture_rules(tmp_path)


def test_a_rule_cannot_seed_itself(tmp_path, fixture_rules):
    _write(tmp_path, "category.yml", _category(_judgement_rule(
        ownership="seeded_adjudication", seeds="'custom.remainder'"
    )))
    with pytest.raises(RuleLoadError, match=r"seed 'custom.remainder' is the rule itself"):
        fixture_rules(tmp_path)


def test_a_seed_cannot_be_another_judgement_rule(tmp_path, fixture_rules):
    """A judgement rule produces no span, so seeding one gives the adjudicator
    nothing to be handed."""
    _write(
        tmp_path,
        "category.yml",
        _category(
            _judgement_rule(ownership="seeded_adjudication", seeds="'custom.probe'")
            + _judgement_rule(rule_id="probe")
        ),
    )
    with pytest.raises(RuleLoadError, match=r"seed 'custom.probe' is kind=judgement"):
        fixture_rules(tmp_path)


def test_a_seeded_rule_with_no_seed_does_not_load(tmp_path, fixture_rules):
    _write(tmp_path, "category.yml", _category(_judgement_rule(ownership="seeded_adjudication")))
    with pytest.raises(RuleLoadError, match=r"requires at least one `seed_rule_ids` entry"):
        fixture_rules(tmp_path)


def test_a_probe_cannot_declare_a_seed(tmp_path, fixture_rules):
    _write(tmp_path, "category.yml", _category(
        _pattern_rule() + _judgement_rule(seeds="'custom.core'")
    ))
    with pytest.raises(RuleLoadError, match=r"`seed_rule_ids` is not valid for ownership=document_probe"):
        fixture_rules(tmp_path)


def test_an_unqualified_seed_does_not_load(tmp_path, fixture_rules):
    _write(tmp_path, "category.yml", _category(_judgement_rule(
        ownership="seeded_adjudication", seeds="'core'"
    )))
    with pytest.raises(RuleLoadError, match=r"seed 'core' is not a qualified"):
        fixture_rules(tmp_path)


# --- export -------------------------------------------------------------------


def _seeded_ruleset() -> RuleSet:
    core = Rule(
        id="core",
        name="Fixture pattern",
        kind=RuleKind.PATTERN,
        dimension=Dimension.STALENESS,
        ownership=Ownership.DETERMINISTIC,
        pattern="xyzzy",
        message="unused",
        provenance=Provenance(source="test"),
    )
    remainder = Rule(
        id="remainder",
        name="Settle the rest",
        kind=RuleKind.JUDGEMENT,
        dimension=Dimension.VERACITY,
        ownership=Ownership.SEEDED_ADJUDICATION,
        seed_rule_ids=["probe.core"],
        message="Check it.",
        judgement_question="Does the sentence claim something checkable?",
        judgement_contract=JudgementContract(
            admission="The core rule already matched inside this unit.",
            protects="A quoted claim attributed to a named source.",
            dims=[JudgementDimension.FIT, JudgementDimension.WARRANT, JudgementDimension.HARM],
            evidence_arity=2,
            judgement_ceiling=Severity.ERROR,
            rewrite_exempt=True,
        ),
        examples=[Example(bad="Everyone agrees the cache is warm.")],
        provenance=Provenance(source="test"),
    )
    for rule in (core, remainder):
        object.__setattr__(rule, "category", "probe")
    return RuleSet(
        categories={
            "probe": Category(
                id="probe",
                title="Probe",
                description="Fixture category.",
                rules=[core, remainder],
            )
        }
    )


def test_the_reference_prints_the_whole_contract():
    """A reviewer held to these terms has to be able to read them. Summarising
    them here is how the two copies drift."""
    rendered = render_reference(_seeded_ruleset())

    assert "**Dimension.** staleness" in rendered
    assert "**Dimension.** veracity" in rendered
    assert "**Layer.** deterministic" in rendered
    assert "**Layer.** seeded_adjudication" in rendered
    assert "**Adjudicates matches of.** `probe.core`" in rendered
    assert "**Applies when.** The core rule already matched inside this unit." in rendered
    assert "**Must not flag.** A quoted claim attributed to a named source." in rendered
    assert "**Scored on.** FIT, WARRANT, HARM" in rendered
    assert "**Evidence.** 2 located spans" in rendered
    assert "**Confirms at most.** error" in rendered
    assert "**Rewrite may alter a protected token.** yes" in rendered


def test_the_reference_counts_rules_per_dimension_and_layer():
    rendered = render_reference(_seeded_ruleset())
    assert "| Dimension | Rules | Checked | Seeded adjudication | Document probe |" in rendered
    assert "| `staleness` | 1 | 1 | 0 | 0 |" in rendered
    assert "| `veracity` | 1 | 0 | 1 | 0 |" in rendered
    # A dimension no rule claims is omitted rather than printed as a zero row.
    assert "`inclusion`" not in rendered


def test_explain_json_carries_the_taxonomy_and_contract(tmp_path, monkeypatch):
    """`explain --format json` is what the review skill reads. A field it cannot
    see is a field the reviewer invents for itself."""
    monkeypatch.setattr("slopvac.rules.RULES_PACKAGE", "slopvac_no_such_package")
    _write(tmp_path, "a.yml", _category(_judgement_rule(
        ownership="seeded_adjudication", seeds="'custom.core'"
    ) + _pattern_rule()))

    result = CliRunner().invoke(
        main, ["explain", "custom.remainder", "--format", "json", "--rules-dir", str(tmp_path)]
    )
    payload = json.loads(result.output)

    assert payload["dimension"] == "redundancy"
    assert payload["ownership"] == "seeded_adjudication"
    assert payload["seed_rule_ids"] == ["custom.core"]
    assert payload["judgement_contract"] == {
        "admission": "The unit is a paragraph of at least two sentences.",
        "protects": "A closing sentence that states a fact stated nowhere else.",
        "dims": ["FIT", "WARRANT"],
        "evidence_arity": 1,
        "judgement_ceiling": "suggestion",
        "rewrite_exempt": False,
    }
