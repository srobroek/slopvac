"""Regression cases from the post-release review threads."""

import json
import os
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from slopvac import ruleset_cache, vale_cache
from slopvac.analyze import parse
from slopvac.cli import main
from slopvac.config import Config, resolve_for
from slopvac.engine import Engine
from slopvac.rules import load_ruleset
from slopvac.suppression import scan_suppressions


@pytest.mark.parametrize(
    "platform,suffix",
    [
        ("linux", ".cache/slopvac"),
        ("darwin", "Library/Caches/slopvac"),
        ("win32", "AppData/Local/slopvac/Cache"),
    ],
)
def test_platform_private_default(monkeypatch, tmp_path, platform, suffix):
    for name in ("SLOPVAC_CACHE_DIR", "XDG_CACHE_HOME", "LOCALAPPDATA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert vale_cache.cache_root() == tmp_path / suffix


@pytest.mark.skipif(os.name != "posix", reason="POSIX trust boundary")
@pytest.mark.parametrize(
    "unsafe", ["shared-root", "shared-parent", "symlink", "file-mode"]
)
def test_forged_model_valid_cache_is_rejected(tmp_path, monkeypatch, unsafe):
    root = tmp_path / "cache"
    root.mkdir(mode=0o700)
    monkeypatch.setenv("SLOPVAC_CACHE_DIR", str(root))
    fresh = load_ruleset()
    path = ruleset_cache.entry_path([])
    header, _, body = path.read_bytes().partition(b"\n")
    documents = json.loads(body)
    # Selectively remove a real pattern while leaving the locale category valid.
    for _, groups in documents:
        for group in groups:
            group["rules"] = [
                r for r in group["rules"] if r["id"] != "negative-guarantee-core"
            ]
    key = json.loads(header)["key"]
    ruleset_cache.write(path, key, documents)
    assert ruleset_cache.read(path, key) is not None
    if unsafe == "shared-root":
        root.chmod(0o777)
    elif unsafe == "shared-parent":
        path.parent.chmod(0o777)
    elif unsafe == "file-mode":
        path.chmod(0o666)
    else:
        moved = tmp_path / "forged"
        path.rename(moved)
        path.symlink_to(moved)
    assert ruleset_cache.read(path, key) is None
    assert load_ruleset().categories == fresh.categories


def test_relative_cache_override_is_uncached(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SLOPVAC_CACHE_DIR", "relative-cache")
    assert load_ruleset().rules
    assert not (tmp_path / "relative-cache").exists()


def test_unsafe_compile_cache_uses_transient_private_output(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("leave this alone")
    blocker.chmod(0o600)
    monkeypatch.setenv("SLOPVAC_CACHE_DIR", str(blocker))
    actual = vale_cache.private_compile_root()
    assert actual != blocker and actual.is_dir()
    assert blocker.read_text() == "leave this alone"


@pytest.mark.skipif(os.name != "posix", reason="POSIX trust boundary")
def test_foreign_owned_entry_is_rejected(monkeypatch, tmp_path):
    from types import SimpleNamespace

    path = tmp_path / "entry.json"
    path.write_text("untrusted")
    path.chmod(0o600)
    real = Path.lstat

    def foreign(candidate):
        info = real(candidate)
        if candidate == path:
            return SimpleNamespace(st_uid=os.getuid() + 1, st_mode=info.st_mode)
        return info

    monkeypatch.setattr(Path, "lstat", foreign)
    assert not vale_cache.trusted_cache_path(path)


def test_dependency_versions_invalidate_proof(monkeypatch):
    import regex
    import yaml

    sources = [("rules.yml", "text")]
    before = ruleset_cache.content_key(sources)
    monkeypatch.setattr(regex, "__version__", "different")
    after = ruleset_cache.content_key(sources)
    assert before != after
    monkeypatch.setattr(yaml, "__version__", "different")
    assert ruleset_cache.content_key(sources) != after


def test_canonical_and_surrogate_origins(tmp_path, monkeypatch):
    source = tmp_path / "rule.yml"
    source.write_text("text")
    monkeypatch.chdir(tmp_path)
    from slopvac.rules import _read_sources

    assert _read_sources([Path(".")])[-1][0] == str(source.resolve())
    assert ruleset_cache.content_key([("rule-\udcff.yml", "text")])
    assert ruleset_cache.entry_path([tmp_path / "rules-\udcff"])


def test_cache_all_removes_ruleset_and_locale_slots():
    load_ruleset()
    root = vale_cache.cache_root()
    ruleset_cache.write(ruleset_cache.locale_entry_path("en-US"), "key", [])
    assert list((root / "rulesets").glob("*.json"))
    result = CliRunner().invoke(main, ["cache", "--all"])
    assert result.exit_code == 0, result.output
    assert not list((root / "rulesets").glob("*.json"))


@pytest.mark.parametrize("fence", ["```", "~~~"])
@pytest.mark.parametrize(
    "directive", ["disable", "disable-next-line", "allow: rule=unknown"]
)
def test_fenced_comment_directives_are_inert(fence, directive):
    document = parse(
        "comments.md",
        f"    {fence}md\n    <!-- slopvac-{directive} -->\n    {fence}\n\nText after.\n",
    )
    allowed, disabled, invalid = scan_suppressions(document, {}, comments=True)
    assert (allowed, disabled, invalid) == ({}, set(), [])


def test_punctuation_comment_is_next_block():
    document = parse("comments.md", "<!-- slopvac-disable-next-line -->\n—\n\nLater.\n")
    _, disabled, _ = scan_suppressions(document, {}, comments=True)
    assert disabled == {2}


@pytest.mark.parametrize("filename,marker", [("sample.py", "#"), ("sample.rs", "//")])
def test_quoted_source_directive_does_not_disable_later_comment(tmp_path, filename, marker):
    source = tmp_path / filename
    source.write_text(
        "\n".join(f"{marker} {line}" for line in [
            "```html", "<!-- slopvac-disable -->", "```", "",
            "Testing is not a phase. It is a habit.",
        ]),
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        main, ["lint", str(source), "--mode", "code-comments", "--no-vale", "--format", "json"]
    )
    assert result.exit_code in (1, 2), result.output
    findings = json.loads(result.output)["documents"][0]["findings"]
    assert any(f["rule_id"] == "ai-tells-structure.definitional-negation-pair" for f in findings)


def test_explicit_inspection_profile_ignores_file_overrides(tmp_path):
    config = tmp_path / "slopvac.toml"
    config.write_text('[[overrides]]\nfiles=["README.md"]\nprofile="relaxed"\n')
    runner = CliRunner()
    args = [
        "explain",
        "prose-craft.future-tense",
        "--profile",
        "strict",
        "--format",
        "json",
    ]
    baseline = runner.invoke(main, args)
    configured = runner.invoke(main, [*args, "--config", str(config)])
    assert baseline.exit_code == configured.exit_code == 0
    assert (
        json.loads(baseline.output)["effective_severity"]
        == json.loads(configured.output)["effective_severity"]
    )


@pytest.mark.parametrize(
    "text,rule",
    [
        ("The Harness Measures, It Does Not Judge", "contrastive-inversion-frames"),
        ("Slopvac never writes the config.", "negative-guarantee-core"),
    ],
)
def test_table_cell_matches_keep_their_start_and_end(text, rule):
    document = parse(
        "table.md",
        f"| Component name | Owner | Behavior |\n| --- | --- | --- |\n| Release agent | Ops | {text} |\n| next | row | continuation |\n",
    )
    rules = load_ruleset().rules
    engine = Engine(rules, resolve_for(Config(), Path("table.md")))
    findings = [f for f in engine.run(document) if f.rule_id.endswith("." + rule)]
    assert findings
    assert all(f.line == 3 and f.matched_text in text for f in findings)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The `deploy` helper never writes a file.", True),
        ("`slopvac` never writes the config.", True),
        ("The parser will not ever accept a duplicate key.", True),
        ("The parser will never accept a duplicate key.", True),
        ("The agent never drove the deployment during the incident.", False),
        ("The client never understood the response.", False),
    ],
)
def test_negative_guarantee_review_examples(text, expected):
    engine = Engine(load_ruleset().rules, resolve_for(Config(), Path("note.md")))
    findings = engine.run(parse("note.md", text))
    assert (
        any(f.rule_id.endswith(".negative-guarantee-core") for f in findings) == expected
    )


@pytest.mark.parametrize("marker", ["#", "//"])
def test_indented_comment_example_is_inert(marker):
    document = parse("comments.md", f"{marker}     <!-- slopvac-disable -->\n{marker}\n{marker} Later prose.\n")
    assert scan_suppressions(document, {}, comments=True) == ({}, set(), [])


def test_inline_code_subject_preserves_reported_source():
    text = "The `deploy` helper never writes a file."
    engine = Engine(load_ruleset().rules, resolve_for(Config(), Path("note.md")))
    findings = [f for f in engine.run(parse("note.md", text)) if f.rule_id.endswith(".negative-guarantee-core")]
    assert findings
    assert all("deploy" in f.matched_text and "\x00" not in f.message + f.matched_text for f in findings)
    assert all(f.matched_text in text for f in findings)


def test_ruleset_hit_refreshes_recency(tmp_path):
    slot = tmp_path / "cache" / "entry.json"
    ruleset_cache.write(slot, "key", [])
    os.utime(slot, (1, 1))
    assert ruleset_cache.read(slot, "key") == []
    assert slot.stat().st_mtime > 1


def test_packaged_cache_identity_ignores_cwd_collisions(tmp_path, monkeypatch):
    from slopvac.rules import _read_sources

    monkeypatch.chdir(tmp_path)
    sources = _read_sources([])
    before = ruleset_cache.content_key(sources)
    (tmp_path / sources[0][0]).write_text("unrelated local content")
    assert ruleset_cache.content_key(_read_sources([])) == before
