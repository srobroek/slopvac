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

from slopvac_lint.cli import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, main

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
    """`slopvac-lint README.md` has to work. Without the default-group shim click
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
    assert run["tool"]["driver"]["name"] == "slopvac-lint"
    assert run["tool"]["driver"]["rules"]
    assert run["results"]
    # Every result's ruleId must be declared in the driver, or GitHub drops it.
    declared = {r["id"] for r in run["tool"]["driver"]["rules"]}
    for entry in run["results"]:
        assert entry["ruleId"] in declared, f"undeclared rule {entry['ruleId']}"


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

    from slopvac_lint.templates import STARTER_CONFIG

    data = tomllib.loads(STARTER_CONFIG.format(profile="normal"))
    scalars = {k for k, v in data.items() if not isinstance(v, dict)}
    assert scalars == {"profile", "exclude"}
    assert set(data) - scalars == {"thresholds", "locale", "vale"}
    assert "**/CHANGELOG.md" in data["exclude"]
