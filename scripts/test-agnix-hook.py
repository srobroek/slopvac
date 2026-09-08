#!/usr/bin/env python3
"""Exercise the staged agnix gate against staged and CI-style snapshots."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check-agnix-staged.sh"
CONFIG = ROOT / ".agnix.toml"
VALID_SKILL = """---
name: fixture
description: Validate the fixture skill
---

# Fixture

Use the tool.
"""
CHANGED_VALID_SKILL = VALID_SKILL.replace(
    "Validate the fixture skill", "Validate the changed fixture skill"
)
MALFORMED_SKILL = """---
name: fixture
---

# Fixture

Use the tool.
"""


def run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)


def git(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = run(["git", *args], cwd, env)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stdout}{result.stderr}")
    return result


def expect_status(
    label: str,
    result: subprocess.CompletedProcess[str],
    expected: int,
) -> None:
    if result.returncode == expected:
        return
    output = (result.stdout + result.stderr).strip()
    raise RuntimeError(
        f"{label}: expected exit {expected}, got {result.returncode}\n{output}"
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="agnix-hook-test-") as temporary:
        worktree = Path(temporary)
        env = os.environ.copy()
        for name in ("AGNIX_DIFF_BASE", "AGNIX_SOURCE_PREFIX", "AGNIX_USE_MISE", "GIT_INDEX_FILE"):
            env.pop(name, None)
        env.update(
            {
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "MISE_AUTO_INSTALL": "false",
            }
        )

        git("init", "--quiet", cwd=worktree, env=env)
        git("config", "user.email", "agnix-hook-test@example.invalid", cwd=worktree, env=env)
        git("config", "user.name", "agnix-hook-test", cwd=worktree, env=env)
        (worktree / "hooks").mkdir()
        git("config", "core.hooksPath", str(worktree / "hooks"), cwd=worktree, env=env)
        (worktree / ".agnix.toml").write_text(CONFIG.read_text())
        skill = worktree / "SKILL.md"
        skill.write_text(VALID_SKILL)
        git("add", ".agnix.toml", "SKILL.md", cwd=worktree, env=env)
        git("commit", "--quiet", "--no-verify", "-m", "base", cwd=worktree, env=env)
        base = git("rev-parse", "HEAD", cwd=worktree, env=env).stdout.strip()

        skill.write_text(CHANGED_VALID_SKILL)
        git("add", "SKILL.md", cwd=worktree, env=env)
        expect_status("valid staged input", run([str(CHECKER)], worktree, env), 0)
        git("commit", "--quiet", "--no-verify", "-m", "valid-change", cwd=worktree, env=env)
        git("reset", "--quiet", "--hard", base, cwd=worktree, env=env)

        skill.write_text(MALFORMED_SKILL)
        git("add", "SKILL.md", cwd=worktree, env=env)
        expect_status("malformed staged input", run([str(CHECKER)], worktree, env), 1)
        git("commit", "--quiet", "--no-verify", "-m", "malformed-change", cwd=worktree, env=env)

        ci_index = worktree / "ci-index"
        ci_env = dict(env, GIT_INDEX_FILE=str(ci_index), AGNIX_DIFF_BASE=base)
        git("read-tree", "HEAD", cwd=worktree, env=ci_env)
        expect_status("malformed CI baseline", run([str(CHECKER)], worktree, ci_env), 1)

        skill.write_text(CHANGED_VALID_SKILL)
        git("add", "SKILL.md", cwd=worktree, env=env)
        expect_status("valid repaired staged input", run([str(CHECKER)], worktree, env), 0)
        git("commit", "--quiet", "--no-verify", "-m", "valid-repair", cwd=worktree, env=env)
        git("read-tree", "HEAD", cwd=worktree, env=ci_env)
        expect_status("valid CI baseline", run([str(CHECKER)], worktree, ci_env), 0)

    print("agnix staged and CI baseline checks passed")


if __name__ == "__main__":
    main()
