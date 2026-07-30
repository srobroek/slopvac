"""CLI contract.

The exit codes are what pre-commit, the GitHub Action, and the skill all branch
on, so they are tested as a contract rather than as behaviour. Exit 2 in
particular must never be reachable from prose alone: it means nothing was
checked, and a caller that treats it as a failure-to-pass reports a score for a
run that did not happen.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from slopvac.cli import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, main

SLOP = """\
# Getting Started

In today's rapidly evolving landscape, our robust and comprehensive platform
will supercharge your workflow. This is not just a tool, it is a paradigm shift.

The runner performs an analysis of the coverage report prior to the merge.
"""

CLEAN = """\
# fluxcache

fluxcache matches a prompt against prompts already in the cache.

## Install

```sh
uv tool install fluxcache
```

## Configure

| Option | Default | Effect |
| --- | --- | --- |
| `threshold` | 0.85 | Minimum similarity for a cache hit |
| `ttl` | 3600 | Seconds an entry stays valid |

The server returns the stored response when two prompts are close enough in
meaning. This lowers the number of calls to the model.

## License

Apache-2.0.
"""


@pytest.fixture
def runner():
    return CliRunner()


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# --- exit codes --------------------------------------------------------------


def test_findings_exit_1(runner, tmp_path):
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale"])
    assert result.exit_code == EXIT_FINDINGS
    assert "FAIL" in result.output


def test_clean_document_exits_0(runner, tmp_path):
    path = _write(tmp_path, "clean.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--no-vale", "--profile", "relaxed"]
    )
    assert result.exit_code == EXIT_OK, result.output


def test_bare_path_is_treated_as_lint(runner, tmp_path):
    """`slopvac README.md` has to work. Without the default-group shim click
    reports the filename as an unknown command and exits 2, which every caller
    reads as "the run could not be trusted"."""
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(main, [str(path), "--no-vale"])
    assert result.exit_code == EXIT_FINDINGS
    assert "unknown command" not in result.output.lower()


def test_missing_file_exits_2(runner):
    result = runner.invoke(main, ["lint", "nope.md", "--no-vale"])
    assert result.exit_code == EXIT_ERROR


def test_broken_config_exits_2(runner, tmp_path):
    _write(tmp_path, "slopvac.toml", "profile = not-valid-toml [[[")
    path = _write(tmp_path, "a.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--config", str(tmp_path / "slopvac.toml")]
    )
    assert result.exit_code == EXIT_ERROR
    assert "config" in result.output.lower()


def test_unknown_config_key_exits_2(runner, tmp_path):
    """A typo in a config key must fail loudly. Silently ignoring it means the
    project believes it configured a gate that is not running."""
    _write(tmp_path, "slopvac.toml", 'profile = "normal"\nmax_erors = 3\n')
    path = _write(tmp_path, "a.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--config", str(tmp_path / "slopvac.toml")]
    )
    assert result.exit_code == EXIT_ERROR


def test_unknown_category_exits_2(runner, tmp_path):
    path = _write(tmp_path, "a.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--category", "no-such-category", "--no-vale"]
    )
    assert result.exit_code == EXIT_ERROR
    assert "unknown category" in result.output.lower()


def test_no_lintable_files_exits_0(runner, tmp_path):
    (tmp_path / "sub").mkdir()
    result = runner.invoke(main, ["lint", str(tmp_path / "sub"), "--no-vale"])
    assert result.exit_code == EXIT_OK


# --- output formats ----------------------------------------------------------


def test_json_output_is_parseable_and_complete(runner, tmp_path):
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "json"])
    payload = json.loads(result.output)
    summary = payload["summary"]
    for key in (
        "score", "findings", "errors", "warnings", "per_100_words", "passed", "categories"
    ):
        assert key in summary, f"summary is missing {key}"
    assert payload["documents"]
    document = payload["documents"][0]
    assert document["findings"]
    assert document["failure_reasons"], "a failing run must name its reason"


def test_github_format_emits_annotations(runner, tmp_path):
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "github"])
    assert "::error file=" in result.output or "::warning file=" in result.output
    assert "::notice title=slopvac::" in result.output


def test_sarif_output_is_valid_shape(runner, tmp_path):
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "sarif"])
    payload = json.loads(result.output)
    assert payload["version"] == "2.1.0"
    run = payload["runs"][0]
    assert run["tool"]["driver"]["name"] == "slopvac"
    assert run["tool"]["driver"]["rules"]
    assert run["results"]
    # Every result's ruleId must be declared in the driver, or GitHub drops it.
    declared = {r["id"] for r in run["tool"]["driver"]["rules"]}
    for entry in run["results"]:
        assert entry["ruleId"] in declared, f"undeclared rule {entry['ruleId']}"


def test_sarif_fingerprints_are_unique_and_line_independent(runner, tmp_path):
    """Two alerts sharing a fingerprint collapse into one in code scanning.

    The fingerprint excludes the line so an edit above a finding does not close
    and re-open the alert, which means uniqueness has to come from an occurrence
    ordinal instead. Without it, one rule firing twice for the same reason loses
    an alert silently.
    """
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "sarif"])
    run = json.loads(result.output)["runs"][0]
    prints = [entry["partialFingerprints"]["slopvacFindingV1"] for entry in run["results"]]
    assert len(prints) == len(run["results"]), "every result needs a fingerprint"
    assert len(set(prints)) == len(prints), "fingerprints collide"

    # Prepend a paragraph: every finding shifts down, and every fingerprint must
    # survive it. Line-derived identity is what this asserts against.
    shifted = _write(tmp_path, "shifted.md", "An unrelated opening line.\n\n" + SLOP)
    again = runner.invoke(main, ["lint", str(shifted), "--no-vale", "--format", "sarif"])
    moved = json.loads(again.output)["runs"][0]["results"]
    lines = {entry["locations"][0]["physicalLocation"]["region"]["startLine"] for entry in moved}
    first_lines = {
        entry["locations"][0]["physicalLocation"]["region"]["startLine"]
        for entry in run["results"]
    }
    assert lines != first_lines, "the fixture did not actually shift; the test proves nothing"


def test_sarif_carries_the_context_an_alert_needs(runner, tmp_path):
    """An alert whose only content is the message cannot be acted on."""
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "sarif"])
    run = json.loads(result.output)["runs"][0]
    assert run["automationDetails"]["id"] == "slopvac/normal"
    for rule in run["tool"]["driver"]["rules"]:
        assert rule["help"]["markdown"].strip(), f"{rule['id']} has an empty help body"
        assert "**Source.**" in rule["help"]["markdown"]
        # A null-valued property is noise in the alert detail pane.
        assert None not in rule["properties"].values(), rule["id"]


# --- profiles and locale -----------------------------------------------------


def test_stricter_profile_finds_more(runner, tmp_path):
    path = _write(tmp_path, "a.md", CLEAN)

    def count(profile):
        result = runner.invoke(
            main, ["lint", str(path), "--no-vale", "--profile", profile, "--format", "json"]
        )
        return json.loads(result.output)["summary"]["findings"]

    assert count("strict") >= count("normal") >= count("relaxed")


@pytest.mark.parametrize(
    "locale,text,should_find",
    [
        ("en-US", "The parser normalises the colour value in the catalogue.", True),
        ("en-GB", "The parser normalises the colour value in the catalogue.", False),
        ("en-GB", "The parser normalizes the color value in the catalog.", True),
        ("und", "The parser normalises the colour value in the catalogue.", False),
    ],
)
def test_locale_flag(runner, tmp_path, locale, text, should_find):
    path = _write(tmp_path, "a.md", f"# Title\n\n{text}\n")
    result = runner.invoke(
        main,
        ["lint", str(path), "--no-vale", "--locale", locale,
         "--category", "ste-words", "--format", "json"],
    )
    findings = json.loads(result.output)["documents"][0]["findings"]
    spelling = [f for f in findings if f["rule_id"] == "ste-words.spelling"]
    assert bool(spelling) is should_find, spelling


def test_unknown_locale_reports_unchecked_and_still_lints(runner, tmp_path):
    """A typo in the locale must not stop the other rules running."""
    path = _write(tmp_path, "a.md", SLOP)
    result = runner.invoke(
        main, ["lint", str(path), "--no-vale", "--locale", "en-XX", "--format", "json"]
    )
    document = json.loads(result.output)["documents"][0]
    assert any("not known" in note for note in document["unchecked"])
    assert document["findings"], "the other rules still ran"


# --- config layering through the CLI ----------------------------------------


def test_project_config_is_discovered_by_walking_up(runner, tmp_path):
    _write(tmp_path, "slopvac.toml", 'profile = "relaxed"\n')
    nested = tmp_path / "docs"
    nested.mkdir()
    path = _write(nested, "a.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "json"])
    assert json.loads(result.output)["documents"][0]["profile"] == "relaxed"


def test_cli_profile_overrides_the_config_file(runner, tmp_path):
    _write(tmp_path, "slopvac.toml", 'profile = "relaxed"\n')
    path = _write(tmp_path, "a.md", SLOP)
    result = runner.invoke(
        main, ["lint", str(path), "--no-vale", "--profile", "strict", "--format", "json"]
    )
    assert json.loads(result.output)["documents"][0]["profile"] == "strict"


def test_glob_override_applies_per_path(runner, tmp_path):
    _write(
        tmp_path,
        "slopvac.toml",
        'profile = "relaxed"\n\n[[overrides]]\nfiles = ["docs/**"]\nprofile = "strict"\n',
    )
    (tmp_path / "docs").mkdir()
    root_doc = _write(tmp_path, "a.md", CLEAN)
    docs_doc = _write(tmp_path / "docs", "b.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(root_doc), str(docs_doc), "--no-vale", "--format", "json"]
    )
    profiles = {
        d["path"].rsplit("/", 1)[-1]: d["profile"]
        for d in json.loads(result.output)["documents"]
    }
    assert profiles["a.md"] == "relaxed"
    assert profiles["b.md"] == "strict"


def test_excluded_path_is_not_linted(runner, tmp_path):
    """CHANGELOG.md is excluded by default because release-please generates it."""
    path = _write(tmp_path, "CHANGELOG.md", SLOP)
    result = runner.invoke(main, ["lint", str(path), "--no-vale"])
    assert result.exit_code == EXIT_OK
    assert "no lintable files" in result.output.lower()


def test_disable_flag_silences_a_rule(runner, tmp_path):
    path = _write(tmp_path, "a.md", SLOP)

    def ids(*extra):
        result = runner.invoke(
            main, ["lint", str(path), "--no-vale", "--format", "json", *extra]
        )
        return {
            f["rule_id"] for f in json.loads(result.output)["documents"][0]["findings"]
        }

    assert "orwell.stale-figure" in ids()
    assert "orwell.stale-figure" not in ids("--disable", "orwell.stale-figure")
    assert not {i for i in ids("--disable", "orwell") if i.startswith("orwell.")}


def test_explain_config_reports_what_applies(runner, tmp_path):
    _write(
        tmp_path,
        "slopvac.toml",
        'profile = "normal"\n\n[[overrides]]\nfiles = ["*.md"]\nprofile = "strict"\n',
    )
    path = _write(tmp_path, "a.md", CLEAN)
    result = runner.invoke(main, ["lint", str(path), "--explain-config"])
    assert result.exit_code == EXIT_OK
    assert "strict" in result.output
    assert "*.md" in result.output


# --- introspection commands --------------------------------------------------


def test_rules_command_lists_the_ruleset(runner):
    result = runner.invoke(main, ["rules"])
    assert result.exit_code == EXIT_OK
    assert "rule(s) in" in result.output


def test_rules_json_carries_categories_and_tiers(runner):
    result = runner.invoke(main, ["rules", "--format", "json", "--profile", "strict"])
    payload = json.loads(result.output)
    assert payload["categories"]
    assert payload["rules"]
    assert all("tier" in rule for rule in payload["rules"])
    # The skill reads recommended_for to recommend a selection.
    assert any(c["recommended_for"] for c in payload["categories"])


def test_judgement_filter_returns_only_unmechanizable_rules(runner):
    """This is the agentic reviewer's input, so it must be selectable on its own."""
    result = runner.invoke(main, ["rules", "--judgement", "--format", "json"])
    rules = json.loads(result.output)["rules"]
    assert rules
    assert all(rule["kind"] == "judgement" for rule in rules)
    assert all(rule["judgement_question"] for rule in rules)


def test_explain_shows_exceptions_and_the_annotation(runner):
    result = runner.invoke(main, ["explain", "orwell.stale-figure"])
    assert result.exit_code == EXIT_OK
    assert "slopvac-allow" in result.output
    assert "quotation" in result.output


def test_explain_unknown_rule_exits_2(runner):
    result = runner.invoke(main, ["explain", "no.such-rule"])
    assert result.exit_code == EXIT_ERROR


def test_every_reported_rule_can_be_explained(runner, tmp_path):
    """A rule the gate names must be one `explain` resolves.

    The spelling rule is generated from the locale rather than shipped as YAML, so
    it exists only in an injected ruleset. `lint` injected it and `rules`/`explain`
    did not, which made the gate report `ste-words.spelling` and `explain` call the
    same id unknown -- and the review skill routes every warning through `explain`
    to reach its exception list, so that finding could not be triaged at all.

    Asserting over the gate's own output rather than a fixed list, so any future
    generated rule is covered without editing this test.
    """
    path = _write(tmp_path, "slop.md", SLOP)
    lint = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "json"])
    reported = {
        finding["rule_id"]
        for document in json.loads(lint.output)["documents"]
        for finding in document["findings"]
    }
    assert reported, "the fixture reported nothing; the test proves nothing"
    for rule_id in sorted(reported):
        result = runner.invoke(main, ["explain", rule_id])
        assert result.exit_code == EXIT_OK, f"explain {rule_id}: {result.output}"


def test_rules_lists_the_generated_spelling_rule(runner):
    """`rules` is how a project sees its gate, so an absent rule misrepresents it."""
    result = runner.invoke(main, ["rules", "--format", "json"])
    ids = {rule["id"] for rule in json.loads(result.output)["rules"]}
    assert "spelling" in ids


def test_explain_json_carries_what_a_triage_needs(runner):
    """The review skill reads the exception list to pick a suppression reason.

    Scraping that out of Rich-rendered text is the alternative, so the qualified id
    and a ready suppression comment are part of the payload: a reason absent from
    the closed list is reported as an invalid suppression rather than honoured.
    """
    result = runner.invoke(main, ["explain", "orwell.stale-figure", "--format", "json"])
    assert result.exit_code == EXIT_OK
    payload = json.loads(result.output)
    assert payload["id"] == "orwell.stale-figure"
    assert payload["exceptions"]
    assert payload["fix"]
    # The rendered annotation has to name the rule and a reason from its own list.
    assert "rule=orwell.stale-figure" in payload["suppression"]
    assert payload["exceptions"][0] in payload["suppression"]
    # Every profile's disposition, so a caller can tell enforced from advisory.
    assert set(payload["tiers"]) == {"strict", "normal", "relaxed"}


def test_init_writes_a_config_and_refuses_to_clobber(runner, tmp_path):
    target = tmp_path / "slopvac.toml"
    first = runner.invoke(main, ["init", "--path", str(target)])
    assert first.exit_code == EXIT_OK
    assert target.is_file()
    body = target.read_text()
    assert "[locale]" in body, "the starter config documents the locale setting"
    assert "profile" in body

    second = runner.invoke(main, ["init", "--path", str(target)])
    assert "exists" in second.output.lower()


def test_starter_config_is_valid(runner, tmp_path):
    """The config `init` writes must load. A starter file that fails validation is
    worse than none."""
    target = tmp_path / "slopvac.toml"
    runner.invoke(main, ["init", "--path", str(target)])
    path = _write(tmp_path, "a.md", CLEAN)
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--config", str(target)])
    assert result.exit_code in (EXIT_OK, EXIT_FINDINGS), result.output


# --- Vale sub-gate -----------------------------------------------------------


def test_missing_vale_is_reported_not_silent(runner, tmp_path):
    """An unsynced or absent Vale makes it report every file clean, which is
    indistinguishable from a pass. It has to say so."""
    _write(tmp_path, "slopvac.toml", '[vale]\nenabled = true\nbinary = "vale-not-installed"\n')
    path = _write(tmp_path, "a.md", SLOP)
    result = runner.invoke(
        main,
        ["lint", str(path), "--config", str(tmp_path / "slopvac.toml"), "--format", "json"],
    )
    document = json.loads(result.output)["documents"][0]
    assert any("not on PATH" in note for note in document["unchecked"])


def test_starter_config_keys_land_where_intended():
    """Regression, and the reason `exclude` sits at the top of the template.

    A TOML table captures every key that follows it until the next header, so
    `exclude` written lower down silently became `thresholds.exclude` and the
    starter config failed to load. Assert the parsed shape, not the text.
    """
    import tomllib

    from slopvac.templates import STARTER_CONFIG

    data = tomllib.loads(STARTER_CONFIG.format(profile="normal"))
    scalars = {k for k, v in data.items() if not isinstance(v, dict)}
    assert scalars == {"profile", "exclude"}
    assert set(data) - scalars == {"thresholds", "locale", "vale"}
    assert "**/CHANGELOG.md" in data["exclude"]


# --- the Vale routing reaches the report -------------------------------------


def test_no_vale_reports_the_skipped_rules_as_unchecked(tmp_path):
    """--no-vale must ACCOUNT for what it skipped.

    Most of the ruleset runs in Vale now, so skipping it silently would print a
    score derived from a dozen rules while looking identical to a full run. That
    is the exact failure mode this project refuses to ship, so the skipped count
    is reported as `unchecked`.
    """
    path = tmp_path / "doc.md"
    path.write_text("We leverage the seamless approach in order to win.\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "json"])
    payload = json.loads(result.output)
    unchecked = " ".join(payload["documents"][0]["unchecked"])

    assert "--no-vale" in unchecked
    assert "did NOT run" in unchecked


def test_unimplemented_metrics_are_reported_not_skipped(tmp_path):
    """A metric rule with no implementation must not read as compliant prose.

    Nine metric names in the shipped ruleset have no native branch. Those rules
    load and match nothing, so without this note a document with a 4,000-word
    paragraph would report clean on `paragraph_words_stdev` and nobody could tell
    the check had never run.
    """
    path = tmp_path / "doc.md"
    path.write_text("A short document.\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "json"])
    payload = json.loads(result.output)
    unchecked = " ".join(payload["documents"][0]["unchecked"])

    assert "no implementation" in unchecked


def test_compile_prints_the_routing_table(tmp_path):
    """`compile` is how a user inspects the routing or runs Vale by hand."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["compile", "--outdir", str(tmp_path / "styles"), "--no-validate"]
    )
    assert result.exit_code == 0, result.output
    assert "routing" in result.output
    assert (tmp_path / "styles" / ".vale.ini").is_file()


def test_compile_json_lists_every_bucket(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["compile", "--outdir", str(tmp_path / "s"), "--no-validate", "--format", "json"],
    )
    payload = json.loads(result.output)
    assert payload["vale"]
    assert payload["judgement"]
    # Every native entry names its reason, which is what --explain-config prints.
    for entry in payload["native"]:
        assert entry["reason"]


def test_missing_vale_binary_is_reported_not_swallowed(tmp_path, monkeypatch):
    """An absent binary must degrade loudly.

    Vale now runs most of the ruleset, so a machine without it checks a fraction
    of what the report implies. The run still completes on the native rules --
    refusing to start would be worse -- but it says what did not run.
    """
    path = tmp_path / "doc.md"
    path.write_text("We leverage the seamless approach.\n", encoding="utf-8")
    monkeypatch.setenv("SLOPVAC_CACHE_DIR", str(tmp_path / "cache"))
    # `which` is how both the compiler and the runner locate the binary.
    monkeypatch.setattr("shutil.which", lambda name, *a, **k: None)

    runner = CliRunner()
    result = runner.invoke(main, ["lint", str(path), "--format", "json"])
    payload = json.loads(result.output)
    unchecked = " ".join(payload["documents"][0]["unchecked"])

    assert "not on PATH" in unchecked
    assert "did NOT run" in unchecked


# --- the implicit `lint` subcommand --------------------------------------------


@pytest.mark.parametrize(
    "argv, why",
    [
        (["--profile", "relaxed", "{path}", "--no-vale"], "the documented form"),
        (["--no-vale", "{path}"], "option before the path"),
        (["{path}", "--no-vale"], "option after the path"),
        (["lint", "--profile", "relaxed", "{path}", "--no-vale"], "explicit still works"),
    ],
)
def test_options_reach_lint_without_naming_it(runner, tmp_path, argv, why):
    """`slopvac --profile relaxed FILE` is what the skill and the README tell
    people to run, and it exited 2 with "No such option: --profile".

    `resolve_command` inserts the implicit `lint` too late -- click has already
    rejected the unknown group option by then -- so the insertion has to happen in
    `parse_args`. An advertised invocation that fails is worse than no default
    subcommand at all.
    """
    path = tmp_path / "doc.md"
    path.write_text("The parser reads the file at /etc/hosts in 12 ms.\n")
    result = runner.invoke(main, [a.format(path=str(path)) for a in argv])
    assert result.exit_code in (EXIT_OK, EXIT_FINDINGS), f"{why}: {result.output}"
    assert "No such option" not in result.output, why


@pytest.mark.parametrize("argv", [["--help"], ["--version"], []])
def test_group_options_still_belong_to_the_group(runner, argv):
    """The insertion must not swallow the group's own options: `--help` has to
    print the group's help, not lint a file named `--help`."""
    result = runner.invoke(main, argv)
    assert result.exit_code == EXIT_OK
    assert "Usage:" in result.output or "version" in result.output


# --- config name validation ---------------------------------------------------
#
# The silent no-op these close: `extra="forbid"` guards the FIELD names inside a
# settings table and never guarded the MAP KEY, so a mistyped rule id validated
# cleanly and did nothing. The failure mode is the worst available -- "I disabled
# it and the gate still fails" -- and it lands in the one place a reader hand-types
# a forty-character string.


def test_mistyped_rule_id_is_an_error_not_a_no_op(runner, tmp_path):
    config = _write(
        tmp_path,
        "slopvac.toml",
        '[rules]\n"prose-format.no-unicode-dashes" = "off"\n',
    )
    path = _write(tmp_path, "doc.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--config", str(config), "--no-vale"]
    )
    assert result.exit_code == EXIT_ERROR, result.output
    # Naming the near miss is the whole value: the id is long and hand-typed.
    assert "prose-format.no-unicode-dash" in result.output
    assert "Did you mean" in result.output


def test_bare_rule_name_names_the_qualified_form(runner, tmp_path):
    """A bare rule name is the likeliest mistake, so it is answered, not just refused."""
    config = _write(tmp_path, "slopvac.toml", '[rules]\n"no-unicode-dash" = "off"\n')
    path = _write(tmp_path, "doc.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--config", str(config), "--no-vale"]
    )
    assert result.exit_code == EXIT_ERROR
    assert "prose-format.no-unicode-dash" in result.output


def test_mistyped_category_is_an_error(runner, tmp_path):
    config = _write(tmp_path, "slopvac.toml", '[categories]\nprose-scop = "warning"\n')
    path = _write(tmp_path, "doc.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--config", str(config), "--no-vale"]
    )
    assert result.exit_code == EXIT_ERROR
    assert "prose-scope" in result.output


def test_a_typo_inside_an_override_is_caught_too(runner, tmp_path):
    """An override is no more visible than the top level, so it is checked the same."""
    config = _write(
        tmp_path,
        "slopvac.toml",
        '[[overrides]]\nfiles = ["**/*.md"]\n[overrides.rules]\n'
        '"orwell.stale-figures" = "off"\n',
    )
    path = _write(tmp_path, "doc.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--config", str(config), "--no-vale"]
    )
    assert result.exit_code == EXIT_ERROR
    # The block is named, because a config with ten overrides needs to know which.
    assert "overrides[0]" in result.output
    assert "orwell.stale-figure" in result.output


def test_the_generated_spelling_rule_counts_as_known(runner, tmp_path):
    """Validation runs against the INJECTED ruleset.

    The spelling rule is generated from the locale rather than shipped as YAML, so
    validating before injection would reject the one rule id a project is most
    likely to want to turn off.
    """
    config = _write(
        tmp_path, "slopvac.toml", '[rules]\n"ste-words.spelling" = "off"\n'
    )
    path = _write(tmp_path, "doc.md", CLEAN)
    result = runner.invoke(
        main, ["lint", str(path), "--config", str(config), "--no-vale"]
    )
    assert result.exit_code != EXIT_ERROR, result.output


# --- the bare-severity shorthand ---------------------------------------------


def test_bare_severity_string_disables_a_rule(runner, tmp_path):
    """`rules."x.y" = "off"` is the same decision as the two-line table form.

    Asserted by behaviour rather than by parsing the config: the point of the
    shorthand is that it reaches the gate, not that it validates.
    """
    text = "A sentence with an em dash — right here.\n"
    path = _write(tmp_path, "doc.md", text)

    plain = runner.invoke(main, ["lint", str(path), "--no-vale", "--format", "json"])
    before = len(json.loads(plain.output)["documents"][0]["findings"])
    assert before, "the fixture reported nothing; the test proves nothing"

    config = _write(
        tmp_path,
        "slopvac.toml",
        '[rules]\n"prose-format.no-unicode-dash" = "off"\n',
    )
    result = runner.invoke(
        main,
        ["lint", str(path), "--config", str(config), "--no-vale", "--format", "json"],
    )
    after = json.loads(result.output)["documents"][0]["findings"]
    assert not [f for f in after if f["rule_id"] == "prose-format.no-unicode-dash"]


def test_bare_severity_string_works_for_a_category(runner, tmp_path):
    config = _write(tmp_path, "slopvac.toml", '[categories]\norwell = "off"\n')
    path = _write(tmp_path, "slop.md", SLOP)
    result = runner.invoke(
        main,
        ["lint", str(path), "--config", str(config), "--no-vale", "--format", "json"],
    )
    findings = json.loads(result.output)["documents"][0]["findings"]
    assert not [f for f in findings if f["category"] == "orwell"]
