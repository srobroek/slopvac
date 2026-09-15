"""Focused proof for Git hunk scopes and their public CLI behavior."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.config import Severity
from slopvac.diff_scope import (
    DiffScope,
    DiffScopeError,
    _parse_patch,
    apply_replacements,
    filter_findings,
    finding_fixable,
    finding_in_scope,
)
from slopvac.model import Finding, Rule, RuleKind, Scope, Tier


def _finding(
    *,
    path: str = "doc.md",
    line: int = 1,
    column: int = 1,
    matched_text: str = "bad",
    replacement: str | None = None,
    rule_id: str = "fixture.replace",
) -> Finding:
    return Finding(
        path=path,
        line=line,
        column=column,
        rule_id=rule_id,
        category="fixture",
        severity=Severity.ERROR,
        message="replace it",
        matched_text=matched_text,
        replacement=replacement,
    )


def _rule(*, rule_id: str = "replace", scope: Scope = Scope.PROSE) -> Rule:
    return Rule(
        id=rule_id,
        name="Replace fixture text",
        kind=RuleKind.SUBSTITUTION,
        severity=Severity.ERROR,
        message="replace {match}",
        scope=scope,
        substitutions={"bad": "good"},
        tiers={
            "strict": Tier.ENFORCED,
            "normal": Tier.ENFORCED,
            "relaxed": Tier.ENFORCED,
        },
        provenance={"source": "tests/test_diff_scope.py"},
        category="fixture",
    )


def _patch(*lines: str) -> str:
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize(
    ("name", "patch", "expected"),
    [
        (
            "modified",
            _patch(
                "diff --git a/doc.md b/doc.md",
                "index 1111111..2222222 100644",
                "--- a/doc.md",
                "+++ b/doc.md",
                "@@ -3,1 +3,2 @@ heading",
                "+new",
                "+second",
            ),
            {"doc.md": ((3, 4),)},
        ),
        (
            "added",
            _patch(
                "diff --git a/new.md b/new.md",
                "new file mode 100644",
                "index 0000000..2222222",
                "--- /dev/null",
                "+++ b/new.md",
                "@@ -0,0 +1,3 @@",
                "+one",
                "+two",
                "+three",
            ),
            {"new.md": ((1, 3),)},
        ),
        (
            "deleted",
            _patch(
                "diff --git a/old.md b/old.md",
                "deleted file mode 100644",
                "index 2222222..0000000",
                "--- a/old.md",
                "+++ /dev/null",
                "@@ -1,2 +0,0 @@",
                "-old",
                "-text",
            ),
            {},
        ),
        (
            "rename",
            _patch(
                "diff --git a/old.md b/new.md",
                "similarity index 98%",
                "rename from old.md",
                "rename to new.md",
                "--- a/old.md",
                "+++ b/new.md",
                "@@ -2 +2 @@",
                "-old",
                "+new",
            ),
            {"new.md": ((2, 2),)},
        ),
        (
            "binary",
            _patch(
                "diff --git a/image.bin b/image.bin",
                "new file mode 100644",
                "index 0000000..2222222",
                "Binary files /dev/null and b/image.bin differ",
            ),
            {},
        ),
        (
            "path with spaces",
            _patch(
                "diff --git a/docs/release notes.md b/docs/release notes.md",
                "index 1111111..2222222 100644",
                "--- a/docs/release notes.md",
                "+++ b/docs/release notes.md",
                "@@ -1 +1 @@",
                "-old",
                "+new",
            ),
            {"docs/release notes.md": ((1, 1),)},
        ),
        (
            "multiple hunks",
            _patch(
                "diff --git a/doc.md b/doc.md",
                "index 1111111..2222222 100644",
                "--- a/doc.md",
                "+++ b/doc.md",
                "@@ -2 +2 @@",
                "-old",
                "+new",
                "@@ -8,1 +9,2 @@",
                "+one",
                "+two",
            ),
            {"doc.md": ((2, 2), (9, 10))},
        ),
        (
            "no newline marker",
            _patch(
                "diff --git a/doc.md b/doc.md",
                "index 1111111..2222222 100644",
                "--- a/doc.md",
                "+++ b/doc.md",
                "@@ -1 +1 @@",
                "-old",
                "\\ No newline at end of file",
                "+new",
                "\\ No newline at end of file",
            ),
            {"doc.md": ((1, 1),)},
        ),
    ],
)
def test_parse_git_patch_variants(name, patch, expected, tmp_path: Path) -> None:
    parsed = _parse_patch(patch, tmp_path)
    assert {
        str(path.relative_to(tmp_path)): changed.ranges
        for path, changed in parsed.items()
    } == expected, name


@pytest.mark.parametrize(
    "patch",
    [
        "+++ b/doc.md\n@@ -1 +1 @@\n+new\n",
        "diff --git a/doc.md b/doc.md\n--- a/doc.md\n+++ b/doc.md\n@@ nope\n",
        "diff --git a/doc.md b/doc.md\n+++ b/doc.md\n",
        "diff --git a/doc.md b/doc.md\n--- a/doc.md\n+++ b/doc.md\n@@ -1 +1 @@\n",
        "diff --git a/doc.md b/doc.md\n--- a/doc.md\n+++ b/doc.md\n+++ b/other.md\n",
        "diff --git a/doc.md b/doc.md\n--- a/doc.md\n+++ c/doc.md\n@@ -1 +1 @@\n",
        "diff --git a/doc.md b/doc.md\n@@ -1 +1 @@\n",
        "diff --git a/doc.md b/doc.md\n\\ No newline at end of file\n",
    ],
)
def test_parse_git_patch_rejects_malformed_or_ambiguous_output(
    patch, tmp_path: Path
) -> None:
    with pytest.raises(DiffScopeError):
        _parse_patch(patch, tmp_path)


def test_parse_rename_only_has_no_added_ranges(tmp_path: Path) -> None:
    patch = _patch(
        "diff --git a/old.md b/new.md",
        "similarity index 100%",
        "rename from old.md",
        "rename to new.md",
    )
    assert _parse_patch(patch, tmp_path) == {}


def test_filter_contract_suppresses_unchanged_unlocated_and_document_findings() -> None:
    rules = {
        "fixture.replace": _rule(),
        "fixture.document": _rule(rule_id="document", scope=Scope.DOCUMENT),
    }
    findings = [
        _finding(line=1),
        _finding(line=8),
        _finding(line=0, matched_text=""),
        _finding(line=2, rule_id="fixture.document"),
    ]
    assert [finding.line for finding in filter_findings(findings, rules, ((2, 2),))] == []
    assert finding_in_scope(_finding(line=2), rules["fixture.replace"], ((2, 2),))
    assert not finding_in_scope(
        _finding(line=0, matched_text=""), rules["fixture.replace"], ((2, 2),)
    )
    assert not finding_in_scope(
        _finding(line=2, rule_id="fixture.document"), rules["fixture.document"], ((2, 2),)
    )


def test_multiline_changed_span_is_reported_but_not_fixable_across_unchanged_line() -> (
    None
):
    rule = _rule()
    finding = _finding(line=2, matched_text="bad\nold", replacement="good\nnew")
    ranges = ((2, 2),)
    assert finding_in_scope(finding, rule, ranges)
    assert not finding_fixable(finding, rule, ranges)


def test_bottom_up_replacements_keep_untouched_lines_stable(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text("bad one\nuntouched\nbad two\n", encoding="utf-8")
    scope = DiffScope(
        root=tmp_path,
        files={path: type("Changed", (), {"ranges": ((1, 1), (3, 3))})()},
        mode="fixture",
    )
    score = type(
        "Score",
        (),
        {
            "path": str(path),
            "findings": [
                _finding(path=str(path), line=1, matched_text="bad", replacement="good"),
                _finding(path=str(path), line=3, matched_text="bad", replacement="clean"),
            ],
        },
    )()
    assert apply_replacements([score], {"fixture.replace": _rule()}, scope) == 2
    assert path.read_text(encoding="utf-8") == "good one\nuntouched\nclean two\n"


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Slopvac Tests")
    return repo, ""


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "--all")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def test_working_tree_scope_unions_staged_and_unstaged_changes(
    tmp_path, monkeypatch
) -> None:
    from slopvac.diff_scope import changed_scope

    repo, _ = _repo(tmp_path)
    (repo / "staged.md").write_text("base\n", encoding="utf-8")
    (repo / "unstaged.md").write_text("base\n", encoding="utf-8")
    _commit(repo, "base")
    (repo / "staged.md").write_text("changed staged\n", encoding="utf-8")
    _git(repo, "add", "staged.md")
    (repo / "unstaged.md").write_text("changed unstaged\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    scope = changed_scope(working_tree=True)
    assert {path.name for path in scope.paths()} == {"staged.md", "unstaged.md"}
    assert scope.ranges_for(repo / "staged.md") == ((1, 1),)
    assert scope.ranges_for(repo / "unstaged.md") == ((1, 1),)


def _run_diff_cli(
    repo: Path,
    base: str,
    target: Path,
    *extra: str,
    monkeypatch,
    category: str = "prose-format",
) -> dict:
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(
        main,
        [
            "lint",
            str(target),
            "--category",
            category,
            "--no-vale",
            "--diff-base",
            base,
            "--format",
            "json",
            *extra,
        ],
    )
    assert result.exit_code in (0, 1, 2), result.output
    assert result.output, result.exception
    payload = json.loads(result.output)
    assert isinstance(payload.get("documents"), list), result.output
    return payload


def test_cli_hunk_mode_reports_changed_and_suppresses_unchanged(
    tmp_path, monkeypatch
) -> None:
    repo, _ = _repo(tmp_path)
    doc = repo / "doc.md"
    doc.write_text("The loader retries — twice.\nclean base\n", encoding="utf-8")
    base = _commit(repo, "base")
    doc.write_text(
        "The loader retries — twice.\nThe new path retries — twice.\n",
        encoding="utf-8",
    )
    _commit(repo, "changed document")
    payload = _run_diff_cli(repo, base, doc, monkeypatch=monkeypatch)
    document = payload["documents"][0]
    assert document["findings"], payload
    assert all(finding["line"] == 2 for finding in document["findings"])
    assert payload["summary"]["findings"] == len(document["findings"])


def test_cli_hunk_mode_new_document_scopes_all_added_lines(tmp_path, monkeypatch) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "existing.md").write_text("clean\n", encoding="utf-8")
    base = _commit(repo, "base")
    new_doc = repo / "new.md"
    new_doc.write_text("The loader retries — twice.\n", encoding="utf-8")
    _commit(repo, "new document")
    payload = _run_diff_cli(repo, base, new_doc, monkeypatch=monkeypatch)
    assert payload["summary"]["findings"] > 0
    assert payload["documents"][0]["findings"][0]["line"] == 1


def test_first_party_no_option_remains_whole_document(tmp_path, monkeypatch) -> None:
    repo, _ = _repo(tmp_path)
    doc = repo / "doc.md"
    doc.write_text("The loader retries — twice.\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(
        main,
        ["lint", str(doc), "--category", "prose-format", "--no-vale", "--format", "json"],
    )
    assert result.exit_code in (0, 1, 2)
    payload = json.loads(result.output)
    assert payload["summary"]["findings"] > 0


def test_conflicting_or_invalid_diff_flags_are_incomplete(tmp_path, monkeypatch) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("clean\n", encoding="utf-8")
    runner = CliRunner()
    both = runner.invoke(
        main, ["lint", str(doc), "--diff-base", "HEAD", "--diff-working-tree"]
    )
    assert both.exit_code == 2
    monkeypatch.chdir(tmp_path)
    invalid = runner.invoke(main, ["lint", str(doc), "--diff-base", "HEAD"])
    assert invalid.exit_code == 2
    assert "incomplete check" in invalid.output


def test_git_failure_exits_incomplete(tmp_path, monkeypatch) -> None:
    from slopvac import diff_scope

    repo, _ = _repo(tmp_path)
    doc = repo / "doc.md"
    doc.write_text("clean\n", encoding="utf-8")
    monkeypatch.chdir(repo)

    def failed_git(args, *, cwd=None):
        if args == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args, 0, stdout=str(repo), stderr="")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="git exploded")

    monkeypatch.setattr(diff_scope, "_run_git", failed_git)
    result = CliRunner().invoke(
        main, ["lint", str(doc), "--diff-working-tree", "--format", "json"]
    )
    assert result.exit_code == 2
    assert "incomplete check" in result.output
    assert "git exploded" in result.output


def test_comments_mode_filters_source_comments_to_changed_hunks(
    tmp_path, monkeypatch
) -> None:
    repo, _ = _repo(tmp_path)
    source = repo / "worker.py"
    source.write_text("# old comment —\nvalue = 1\n", encoding="utf-8")
    base = _commit(repo, "base")
    source.write_text(
        "# old comment —\n# changed comment —\nvalue = 1\n", encoding="utf-8"
    )
    _commit(repo, "comment change")
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(
        main,
        [
            "lint",
            str(source),
            "--comments",
            "--category",
            "prose-format",
            "--no-vale",
            "--diff-base",
            base,
            "--format",
            "json",
        ],
    )
    assert result.exit_code in (0, 1, 2), result.output
    findings = json.loads(result.output)["documents"][0]["findings"]
    assert findings
    assert {finding["line"] for finding in findings} == {2}


@pytest.mark.skipif(shutil.which("vale") is None, reason="Vale is not installed")
def test_cli_hunk_mode_keeps_changed_vale_finding(tmp_path, monkeypatch) -> None:
    repo, _ = _repo(tmp_path)
    doc = repo / "doc.md"
    doc.write_text("The loader retries twice.\nclean base\n", encoding="utf-8")
    base = _commit(repo, "base")
    doc.write_text(
        "The loader retries twice.\nThe loader will retry twice.\n",
        encoding="utf-8",
    )
    _commit(repo, "changed document")
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(
        main,
        [
            "lint",
            str(doc),
            "--category",
            "prose-craft",
            "--diff-base",
            base,
            "--format",
            "json",
        ],
    )
    assert result.exit_code in (0, 1), result.output
    document = json.loads(result.output)["documents"][0]
    assert any(
        finding["rule_id"] == "prose-craft.future-tense" and finding["line"] == 2
        for finding in document["findings"]
    )
    assert document["unchecked"] == []


def test_working_tree_scope_includes_untracked_document_as_all_lines(
    tmp_path, monkeypatch
) -> None:
    from slopvac.diff_scope import changed_scope

    repo, _ = _repo(tmp_path)
    (repo / "tracked.md").write_text("base\n", encoding="utf-8")
    _commit(repo, "base")
    new_doc = repo / "new.md"
    new_doc.write_text("bad first\nsecond\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    scope = changed_scope(working_tree=True)
    assert scope.all_lines_for(new_doc)
    assert scope.ranges_for(new_doc) == ((1, 2**31 - 1),)


def test_changed_symlink_fails_closed_instead_of_following_external_file(
    tmp_path, monkeypatch
) -> None:
    from slopvac.diff_scope import DiffScopeError, changed_scope

    repo, _ = _repo(tmp_path)
    doc = repo / "doc.md"
    doc.write_text("base\n", encoding="utf-8")
    _commit(repo, "base")
    external = tmp_path / "external.md"
    external.write_text("outside —\n", encoding="utf-8")
    doc.unlink()
    doc.symlink_to(external)
    monkeypatch.chdir(repo)
    with pytest.raises(DiffScopeError, match="symlink"):
        changed_scope(working_tree=True)


def test_fixes_preserve_crlf_and_missing_final_newline(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_bytes(b"bad\r\nuntouched\r\nbad")
    scope = DiffScope(
        root=tmp_path,
        files={path.resolve(): type("Changed", (), {"ranges": ((1, 1), (3, 3))})()},
        mode="fixture",
    )
    score = type(
        "Score",
        (),
        {
            "path": str(path),
            "findings": [
                _finding(path=str(path), line=1, matched_text="bad", replacement="good"),
                _finding(path=str(path), line=3, matched_text="bad", replacement="clean"),
            ],
        },
    )()
    assert apply_replacements([score], {"fixture.replace": _rule()}, scope) == 2
    assert path.read_bytes() == b"good\r\nuntouched\r\nclean"


def test_comment_projection_ignores_strings_and_masks_code_after_blocks() -> None:
    from slopvac.pipeline import _comment_projection

    source = (
        'const url = "// not a comment"; // real\n'
        'const escaped = "quote \\" // still string"; // real two\n'
        "/* block start\n"
        " * block end */ const value = 1; // trailing\n"
    )
    projected = _comment_projection(Path("sample.js"), source)
    assert "// not a comment" not in projected
    assert "// real" in projected
    assert "// still string" not in projected
    assert "/* block start" in projected
    assert "block end */" in projected
    assert "const value" not in projected
    assert "// trailing" in projected


def test_comments_directory_selection_excludes_build_vendor_and_binary(tmp_path) -> None:
    from slopvac.pipeline import _expand_paths

    (tmp_path / "src").mkdir()
    (tmp_path / "vendor").mkdir()
    (tmp_path / "build").mkdir()
    (tmp_path / "src" / "main.py").write_text("# comment\n", encoding="utf-8")
    (tmp_path / "vendor" / "third.py").write_text("# vendor\n", encoding="utf-8")
    (tmp_path / "build" / "generated.py").write_text("# generated\n", encoding="utf-8")
    (tmp_path / "image.bin").write_bytes(b"\x00\x01")
    paths = _expand_paths((str(tmp_path),), comments=True)
    assert paths == [tmp_path / "src" / "main.py"]


def test_normalized_cross_line_match_fails_closed_for_scope_and_fix() -> None:
    finding = _finding(line=1, matched_text="in order to", replacement="to")
    rule = _rule()
    source = "in order\nto validate\n"
    assert not finding_in_scope(finding, rule, ((1, 1),), source)
    assert not finding_fixable(finding, rule, ((1, 1),), source)


def test_hardlinked_file_is_not_automatically_fixed(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    alias = tmp_path / "alias.md"
    path.write_bytes(b"bad\n")
    alias.hardlink_to(path)
    score = type(
        "Score",
        (),
        {
            "path": str(path),
            "findings": [
                _finding(path=str(path), line=1, matched_text="bad", replacement="good"),
            ],
        },
    )()
    assert apply_replacements([score], {"fixture.replace": _rule()}) == 0
    assert path.read_bytes() == b"bad\n"
    assert alias.read_bytes() == b"bad\n"


def test_sql_projection_respects_strings_and_line_comments() -> None:
    from slopvac.pipeline import _comment_projection

    source = (
        "SELECT '-- not a comment' AS value; -- real\n/* block */ SELECT 1; -- trailing\n"
    )
    projected = _comment_projection(Path("query.sql"), source)
    assert "-- not a comment" not in projected
    assert "-- real" in projected
    assert "/* block */" in projected
    assert "SELECT 1" not in projected
    assert "-- trailing" in projected


def test_comments_directory_excludes_markdown_documents(tmp_path) -> None:
    from slopvac.pipeline import _expand_paths

    (tmp_path / "README.md").write_text("# heading\n", encoding="utf-8")
    (tmp_path / "source.py").write_text("# comment\n", encoding="utf-8")

    assert _expand_paths((str(tmp_path),), comments=True) == [tmp_path / "source.py"]


@pytest.mark.skipif(shutil.which("vale") is None, reason="Vale is not installed")
def test_cli_soft_break_span_fails_closed_before_unchanged_line(
    tmp_path, monkeypatch
) -> None:
    positive, _ = _repo(tmp_path)
    positive_doc = positive / "doc.md"
    positive_doc.write_text("clean\n", encoding="utf-8")
    positive_base = _commit(positive, "base")
    positive_doc.write_text("The process is in order to validate.\n", encoding="utf-8")
    _commit(positive, "whole phrase change")
    monkeypatch.chdir(positive)
    reported = CliRunner().invoke(
        main,
        [
            "lint",
            str(positive_doc),
            "--category",
            "prose-craft",
            "--diff-base",
            positive_base,
            "--format",
            "json",
        ],
    )
    assert reported.exit_code in (0, 1), reported.output
    report = json.loads(reported.output)
    assert any(
        "wordiness" in finding["rule_id"]
        for finding in report["documents"][0]["findings"]
    )
    fixed = CliRunner().invoke(
        main,
        [
            "lint",
            str(positive_doc),
            "--category",
            "prose-craft",
            "--diff-base",
            positive_base,
            "--fix",
            "--format",
            "json",
        ],
    )
    assert fixed.exit_code in (0, 1), fixed.output
    assert b"in order to" not in positive_doc.read_bytes()

    (tmp_path / "mixed").mkdir()
    mixed, _ = _repo(tmp_path / "mixed")
    mixed_doc = mixed / "doc.md"
    mixed_doc.write_text("The process is in order\nto validate.\n", encoding="utf-8")
    mixed_base = _commit(mixed, "base")
    mixed_doc.write_text(
        "The updated process is in order\nto validate.\n", encoding="utf-8"
    )
    _commit(mixed, "soft break change")
    monkeypatch.chdir(mixed)
    result = CliRunner().invoke(
        main,
        [
            "lint",
            str(mixed_doc),
            "--category",
            "prose-craft",
            "--diff-base",
            mixed_base,
            "--format",
            "json",
        ],
    )
    assert result.exit_code in (0, 1), result.output
    assert json.loads(result.output)["documents"][0]["findings"] == []
    before = mixed_doc.read_bytes()
    result = CliRunner().invoke(
        main,
        [
            "lint",
            str(mixed_doc),
            "--category",
            "prose-craft",
            "--diff-base",
            mixed_base,
            "--fix",
            "--format",
            "json",
        ],
    )
    assert result.exit_code in (0, 1), result.output
    assert mixed_doc.read_bytes() == before
