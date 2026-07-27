"""Behavioural tests for the PostToolUse prose-gate hook.

Drives the real script with real payloads from each supported harness. The hook
shells out to slop-lint.sh, so tests that assert on findings skip without vale.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "prose-gate-advisory.py"
SLOPPY = "# Guide\n\nThe library leverages a robust parser. The complaint becomes a fix.\n"
CLEAN = "# Title\n\nThe parser rejects malformed input at startup.\n"

needs_vale = pytest.mark.skipif(
    shutil.which("vale") is None, reason="vale not installed"
)


@pytest.fixture
def repo(tmp_path):
    """A git repo, because the hook resolves a root and consults .gitignore."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "doc.md").write_text(SLOPPY, encoding="utf-8")
    return tmp_path


def run_hook(payload: dict, *, env: dict | None = None) -> str:
    """The hook's additionalContext, or "" when it stayed silent."""
    environ = {
        **os.environ,
        # Fire on the first edit; accumulation is tested separately.
        "WRITE_DOCS_ADVISORY_LINES": "1",
        "WRITE_DOCS_ADVISORY_FILES": "1",
        "WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS": "0",
        **(env or {}),
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True,
        env=environ, timeout=90,
    )
    # A PostToolUse advisory must never fail the tool call it follows.
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    if not proc.stdout.strip():
        return ""
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


# --- Harness payload shapes --------------------------------------------------
# Claude sends file_path, Kiro sends path, Codex sends an apply_patch body. All
# three must reach the same file list.


@needs_vale
def test_claude_write_payload(repo):
    out = run_hook({"cwd": str(repo), "tool_name": "Write",
                    "tool_input": {"file_path": str(repo / "doc.md"), "content": "x"}})
    assert "PROSE GATE" in out
    assert "prose-agency.FalseAgency" in out


@needs_vale
def test_kiro_fswrite_payload_uses_path_key(repo):
    out = run_hook({"cwd": str(repo), "tool_name": "fsWrite",
                    "tool_input": {"path": str(repo / "doc.md"), "content": "x"}})
    assert "PROSE GATE" in out


@needs_vale
def test_codex_apply_patch_payload(repo):
    patch = (f"*** Begin Patch\n*** Update File: {repo / 'doc.md'}\n"
             f"+leverages a robust parser\n*** End Patch")
    out = run_hook({"cwd": str(repo), "tool_name": "apply_patch",
                    "tool_input": {"command": patch}})
    assert "PROSE GATE" in out


@needs_vale
def test_multiedit_payload_reads_the_edits_array(repo):
    out = run_hook({"cwd": str(repo), "tool_name": "MultiEdit", "tool_input": {
        "edits": [{"file_path": str(repo / "doc.md"), "new_string": "y"}]}})
    assert "PROSE GATE" in out


def test_legacy_string_tool_input_does_not_crash(repo):
    patch = f"*** Begin Patch\n*** Update File: {repo / 'doc.md'}\n+x\n*** End Patch"
    run_hook({"cwd": str(repo), "tool_name": "apply_patch", "tool_input": patch})


# --- Silence -----------------------------------------------------------------


def test_non_prose_edit_is_silent(repo):
    (repo / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
    assert run_hook({"cwd": str(repo), "tool_name": "Write", "tool_input": {
        "file_path": str(repo / "main.rs"), "content": "x"}}) == ""


@needs_vale
def test_clean_prose_is_silent(repo):
    (repo / "clean.md").write_text(CLEAN, encoding="utf-8")
    assert run_hook({"cwd": str(repo), "tool_name": "Write", "tool_input": {
        "file_path": str(repo / "clean.md"), "content": "x"}}) == ""


@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_malformed_payload_is_silent(payload):
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload,
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_vendored_paths_are_skipped(repo):
    vendored = repo / "node_modules" / "pkg"
    vendored.mkdir(parents=True)
    (vendored / "README.md").write_text(SLOPPY, encoding="utf-8")
    assert run_hook({"cwd": str(repo), "tool_name": "Write", "tool_input": {
        "file_path": str(vendored / "README.md"), "content": "x"}}) == ""


# --- gitignore ---------------------------------------------------------------


@needs_vale
def test_gitignored_files_are_not_gated(repo):
    (repo / ".gitignore").write_text("generated.md\nbuilt/\n", encoding="utf-8")
    (repo / "generated.md").write_text(SLOPPY, encoding="utf-8")
    built = repo / "built"
    built.mkdir()
    (built / "out.md").write_text(SLOPPY, encoding="utf-8")

    for path in (repo / "generated.md", built / "out.md"):
        assert run_hook({"cwd": str(repo), "tool_name": "Write", "tool_input": {
            "file_path": str(path), "content": "x"}}) == "", f"{path} was gated"

    # The control: a tracked file in the same repo still gates.
    assert "PROSE GATE" in run_hook({"cwd": str(repo), "tool_name": "Write",
        "tool_input": {"file_path": str(repo / "doc.md"), "content": "x"}})


# --- Loud failure ------------------------------------------------------------


def test_missing_vale_is_loud(repo):
    # A silent skip would leave prose ungated while the hook reports success.
    out = run_hook(
        {"cwd": str(repo), "tool_name": "Write",
         "tool_input": {"file_path": str(repo / "doc.md"), "content": "x"}},
        env={"PATH": "/usr/bin:/bin"},
    )
    assert "UNAVAILABLE" in out
    assert "NOT being checked" in out
    assert "mise use -g vale" in out


# --- Throttle ----------------------------------------------------------------


def test_small_edit_is_throttled_at_default_thresholds(repo):
    out = run_hook(
        {"cwd": str(repo), "tool_name": "Write",
         "tool_input": {"file_path": str(repo / "doc.md"), "content": "one line"}},
        env={"WRITE_DOCS_ADVISORY_LINES": "120",
             "WRITE_DOCS_ADVISORY_FILES": "5",
             "WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS": "300"},
    )
    assert out == ""


@needs_vale
def test_cooldown_suppresses_the_second_advisory(repo):
    payload = {"cwd": str(repo), "tool_name": "Write", "tool_input": {
        "file_path": str(repo / "doc.md"), "content": "line\n" * 200}}
    env = {"WRITE_DOCS_ADVISORY_LINES": "120", "WRITE_DOCS_ADVISORY_FILES": "5",
           "WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS": "300"}
    assert "PROSE GATE" in run_hook(payload, env=env)
    assert run_hook(payload, env=env) == "", "cooldown did not suppress"


# --- Deployment layouts ------------------------------------------------------


def test_finds_the_gate_in_the_installed_layout(repo, tmp_path):
    """APM installs the hook and the skill into sibling trees, not neighbours.

    Regression: the first implementation guessed a fixed set of `..` hops and
    reported PROSE GATE UNAVAILABLE on every real install, because the deployed
    shape is <root>/hooks/write-docs/scripts -> <root>/skills/review-docs/scripts.
    """
    root = tmp_path / "deployed"
    hook_dir = root / "hooks" / "write-docs" / "scripts"
    skill_dir = root / "skills" / "review-docs" / "scripts"
    hook_dir.mkdir(parents=True)
    skill_dir.mkdir(parents=True)
    shutil.copy(HOOK, hook_dir / HOOK.name)
    # A stub gate: this test is about path resolution, not linting.
    stub = skill_dir / "slop-lint.sh"
    stub.write_text('#!/usr/bin/env bash\necho "stub ERROR finding"\n', encoding="utf-8")
    stub.chmod(0o755)
    for style in ("ai-tells", "ai-residue", "prose-agency", "prose-inflation",
                  "docs-discipline", "prose-format"):
        (root / "skills" / "review-docs" / "vale" / "styles" / style).mkdir(parents=True)

    proc = subprocess.run(
        [sys.executable, str(hook_dir / HOOK.name)],
        input=json.dumps({"cwd": str(repo), "tool_name": "Write", "tool_input": {
            "file_path": str(repo / "doc.md"), "content": "x"}}),
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "WRITE_DOCS_ADVISORY_LINES": "1",
             "WRITE_DOCS_ADVISORY_FILES": "1",
             "WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS": "0"},
    )
    assert proc.returncode == 0
    out = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "UNAVAILABLE" not in out, f"gate not found from installed layout: {out}"
    assert "stub ERROR finding" in out


# --- Project config discovery and overrides ----------------------------------

INIT = HOOK.parent.parent / ".apm" / "skills" / "review-docs" / "scripts" / "init-vale.sh"
LINT = HOOK.parent.parent / ".apm" / "skills" / "review-docs" / "scripts" / "slop-lint.sh"
TEMPLATE = INIT.parent.parent / "vale" / "vale.ini.template"


def test_init_check_reports_a_missing_config(tmp_path):
    proc = subprocess.run(["bash", str(INIT), "--check", str(tmp_path)],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 2
    assert ".vale.ini" in proc.stdout


def test_init_does_not_overwrite_an_existing_config(tmp_path):
    config = tmp_path / ".vale.ini"
    config.write_text("# mine\n", encoding="utf-8")
    subprocess.run(["bash", str(INIT), str(tmp_path)],
                   capture_output=True, text=True, timeout=60)
    assert config.read_text() == "# mine\n"


def test_init_check_detects_a_partial_sync(tmp_path):
    # Vale reports a clean file for a style it cannot resolve, so a sync that
    # failed partway looks exactly like a passing run.
    shutil.copy(TEMPLATE, tmp_path / ".vale.ini")
    (tmp_path / ".vale-styles" / "ai-tells").mkdir(parents=True)
    proc = subprocess.run(["bash", str(INIT), "--check", str(tmp_path)],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    assert "prose-agency" in proc.stdout, proc.stdout


@needs_vale
def test_a_project_config_overrides_the_packaged_one(tmp_path):
    """A rule turned off in the project config must stop firing.

    Regression: slop-lint.sh passes --config, which suppresses Vale's own upward
    search, so a project .vale.ini sat there being ignored.
    """
    packaged_styles = LINT.parent.parent / "vale" / "styles"
    if not (packaged_styles / "prose-scope").is_dir():
        pytest.skip("styles not synced")

    doc = tmp_path / "doc.md"
    doc.write_text("The parser takes 212 ms per call.\n", encoding="utf-8")
    (tmp_path / ".vale.ini").write_text(
        f"StylesPath = {packaged_styles}\n"
        "MinAlertLevel = warning\n"
        "[*.md]\n"
        "BasedOnStyles = prose-scope\n"
        "prose-scope.ImplementationLeak = NO\n",
        encoding="utf-8",
    )
    proc = subprocess.run(["bash", str(LINT), "--genre", "consumer", str(doc)],
                          capture_output=True, text=True, timeout=60)
    assert "ImplementationLeak" not in proc.stdout, proc.stdout
    assert proc.returncode == 0
