from pathlib import Path

from click.testing import CliRunner

from slopvac.cli import main
from slopvac.steering import (
    BEGIN,
    END,
    STEERING_BLOCK,
    harness_path,
    managed_block_state,
    remove_managed_block,
    update_managed_block,
)


def test_managed_block_preserves_existing_text_and_is_idempotent(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text("# Project instructions\n\nKeep this text.\n", encoding="utf-8")

    assert update_managed_block(path)
    first = path.read_text(encoding="utf-8")
    assert first.startswith("# Project instructions")
    assert "Keep this text." in first
    assert BEGIN in first and END in first

    assert not update_managed_block(path)
    assert path.read_text(encoding="utf-8") == first


def test_managed_block_can_be_removed_without_touching_surrounding_text(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(
        "# Before\n\n" + STEERING_BLOCK + "\n# After\n", encoding="utf-8"
    )
    assert remove_managed_block(path)
    text = path.read_text(encoding="utf-8")
    assert BEGIN not in text and END not in text
    assert "# Before" in text and "# After" in text


def test_harness_mapping():
    root = Path("/repo")
    assert harness_path(root, "agents") == root / "AGENTS.md"
    assert harness_path(root, "codex") == root / "AGENTS.md"
    assert harness_path(root, "claude") == root / "CLAUDE.md"
    assert harness_path(root, "omp") == root / ".omp" / "AGENTS.md"
    assert harness_path(root, "kiro") == root / ".kiro" / "steering" / "slopvac.md"


def test_managed_block_state_tracks_missing_current_stale_and_malformed(tmp_path):
    path = tmp_path / "AGENTS.md"
    assert managed_block_state(path) == "missing"

    update_managed_block(path)
    assert managed_block_state(path) == "current"

    path.write_text(path.read_text(encoding="utf-8").replace("slopvac prime", "slopvac old-prime"), encoding="utf-8")
    assert managed_block_state(path) == "stale"

    path.write_text(BEGIN + "\nmissing end\n", encoding="utf-8")
    assert managed_block_state(path) == "malformed"


def test_init_writes_config_and_agent_steering():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0, result.output
        assert Path("slopvac.toml").is_file()
        text = Path("AGENTS.md").read_text(encoding="utf-8")
        assert "slopvac prime" in text
        assert BEGIN in text


def test_init_can_skip_agent_steering():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--skip-agents"])
        assert result.exit_code == 0, result.output
        assert Path("slopvac.toml").is_file()
        assert not Path("AGENTS.md").exists()


def test_setup_claude_and_remove_preserves_existing_text():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("CLAUDE.md").write_text("# Local\n", encoding="utf-8")
        result = runner.invoke(main, ["setup", "claude"])
        assert result.exit_code == 0, result.output
        text = Path("CLAUDE.md").read_text(encoding="utf-8")
        assert "# Local" in text and "slopvac prime" in text

        result = runner.invoke(main, ["setup", "claude", "--remove"])
        assert result.exit_code == 0, result.output
        assert Path("CLAUDE.md").read_text(encoding="utf-8") == "# Local\n"


def test_prime_contains_lint_guidance_only():
    runner = CliRunner()
    result = runner.invoke(main, ["prime"])
    assert result.exit_code == 0
    assert "slopvac lint" in result.output
    assert "judgement" not in result.output.lower()

    extra = runner.invoke(main, ["prime", "judgement"])
    assert extra.exit_code == 2


def test_onboard_points_to_prime_without_duplicating_detailed_guidance():
    runner = CliRunner()
    result = runner.invoke(main, ["onboard"])
    assert result.exit_code == 0
    assert "slopvac prime" in result.output
    assert "slopvac setup --list" in result.output
    assert "Slopvac lint guidance" not in result.output
    assert "judgement" not in result.output.lower()


def test_setup_uses_native_omp_and_kiro_paths():
    runner = CliRunner()
    with runner.isolated_filesystem():
        omp = runner.invoke(main, ["setup", "omp"])
        assert omp.exit_code == 0, omp.output
        assert Path(".omp/AGENTS.md").is_file()

        kiro = runner.invoke(main, ["setup", "kiro"])
        assert kiro.exit_code == 0, kiro.output
        assert Path(".kiro/steering/slopvac.md").is_file()


def test_setup_check_reports_current_missing_stale_and_does_not_mutate():
    runner = CliRunner()
    with runner.isolated_filesystem():
        missing = runner.invoke(main, ["setup", "codex", "--check"])
        assert missing.exit_code == 1
        assert "missing " in missing.output
        assert missing.output.rstrip().endswith("AGENTS.md")
        assert not Path("AGENTS.md").exists()

        installed = runner.invoke(main, ["setup", "codex"])
        assert installed.exit_code == 0, installed.output
        before = Path("AGENTS.md").read_text(encoding="utf-8")

        current = runner.invoke(main, ["setup", "codex", "--check"])
        assert current.exit_code == 0
        assert "current " in current.output
        assert current.output.rstrip().endswith("AGENTS.md")
        assert Path("AGENTS.md").read_text(encoding="utf-8") == before

        Path("AGENTS.md").write_text(before.replace("slopvac prime", "slopvac old-prime"), encoding="utf-8")
        stale = runner.invoke(main, ["setup", "codex", "--check"])
        assert stale.exit_code == 1
        assert "stale " in stale.output
        assert stale.output.rstrip().endswith("AGENTS.md")


def test_duplicate_managed_markers_are_malformed(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(STEERING_BLOCK + "\n" + STEERING_BLOCK, encoding="utf-8")
    assert managed_block_state(path) == "malformed"

    try:
        update_managed_block(path)
    except ValueError as exc:
        assert "malformed" in str(exc)
    else:
        raise AssertionError("duplicate managed blocks must not be rewritten implicitly")


def test_setup_check_rejects_remove_combination():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["setup", "codex", "--check", "--remove"])
        assert result.exit_code == 2
        assert "--check and --remove cannot be used together" in result.output


def test_retired_integration_names_do_not_survive_in_live_sources():
    root = Path(__file__).resolve().parents[3]
    needles = (
        "slopvac@slopvac",
        "plugin marketplace add srobroek/slopvac",
        "packages/slopvac/",
        ".claude-plugin",
        ".codex-plugin",
        ".omp-plugin",
        "write-docs",
        "review-docs",
        "docs/research/",
        "research/rubric-",
        "orwell-derivation",
        "judgement-eval",
    )
    suffixes = {".md", ".py", ".toml", ".yaml", ".yml", ".json", ".sh"}
    excluded_records = (
        root / "CHANGELOG.md",
        root / "packages/slopvac-lint/CHANGELOG.md",
        root / ".beads",
        root / ".agents/skills/beads",
    )
    own_file = Path(__file__).resolve()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes or path.resolve() == own_file:
            continue
        if any(path == base or base in path.parents for base in excluded_records):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            assert needle not in text, f"{needle!r} remains in {path.relative_to(root)}"

def test_judgement_is_not_in_public_cli_surface():
    runner = CliRunner()

    assert "judgement" not in main.commands

    result = runner.invoke(main, ["rules", "--judgement"])
    assert result.exit_code == 2

    result = runner.invoke(main, ["rules", "--kind", "judgement"])
    assert result.exit_code == 2

    result = runner.invoke(main, ["explain", "orwell.concrete-floor"])
    assert result.exit_code == 2
    assert "unknown rule" in result.output


def test_removed_agent_packaging_has_no_live_paths_or_install_commands():
    root = Path(__file__).resolve().parents[3]
    for relative in (
        ".claude-plugin",
        ".codex-plugin",
        ".omp-plugin",
        "packages/slopvac",
        "packages/slopvac-lint/docs/research",
        "packages/slopvac-lint/docs/orwell-derivation.md",
    ):
        assert not (root / relative).exists(), relative

    live_docs = (
        root / "README.md",
        root / "packages/slopvac-lint/README.md",
        root / "AGENTS.md",
        root / "release-please-config.json",
        root / ".github/workflows/test.yml",
        root / ".github/workflows/lint.yml",
    )
    obsolete = (
        "omp plugin marketplace add srobroek/slopvac",
        "/plugin marketplace add srobroek/slopvac",
        "codex plugin marketplace add srobroek/slopvac",
        "slopvac@slopvac",
        "write-docs",
        "review-docs",
        "packages/slopvac/",
    )
    for path in live_docs:
        text = path.read_text(encoding="utf-8")
        for needle in obsolete:
            assert needle not in text, f"{needle!r} remains in {path.relative_to(root)}"


def test_init_places_agents_file_next_to_explicit_config(tmp_path):
    runner = CliRunner()
    config = tmp_path / "project" / "slopvac.toml"
    result = runner.invoke(main, ["init", "--path", str(config)])
    assert result.exit_code == 0, result.output
    assert config.is_file()
    assert (config.parent / "AGENTS.md").is_file()
    assert not (tmp_path / "AGENTS.md").exists()


def test_setup_list_respects_root(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["setup", "--list", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert str(tmp_path / "AGENTS.md") in result.output
    assert str(tmp_path / ".omp" / "AGENTS.md") in result.output


def test_reversed_managed_markers_are_malformed(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(END + "\ntext\n" + BEGIN + "\n", encoding="utf-8")
    assert managed_block_state(path) == "malformed"

    for operation in (update_managed_block, remove_managed_block):
        try:
            operation(path)
        except ValueError as exc:
            assert "malformed" in str(exc)
        else:
            raise AssertionError("reversed managed markers must be rejected")

def test_codex_prefers_existing_nonempty_override():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("AGENTS.override.md").write_text("# Local override\n", encoding="utf-8")

        installed = runner.invoke(main, ["setup", "codex"])
        assert installed.exit_code == 0, installed.output
        assert not Path("AGENTS.md").exists()
        text = Path("AGENTS.override.md").read_text(encoding="utf-8")
        assert "# Local override" in text
        assert BEGIN in text

        checked = runner.invoke(main, ["setup", "codex", "--check"])
        assert checked.exit_code == 0, checked.output

        removed = runner.invoke(main, ["setup", "codex", "--remove"])
        assert removed.exit_code == 0, removed.output
        assert Path("AGENTS.override.md").read_text(encoding="utf-8") == "# Local override\n"


def test_kiro_new_file_is_explicitly_always_included():
    runner = CliRunner()
    with runner.isolated_filesystem():
        installed = runner.invoke(main, ["setup", "kiro"])
        assert installed.exit_code == 0, installed.output
        text = Path(".kiro/steering/slopvac.md").read_text(encoding="utf-8")
        assert text.startswith("---\ninclusion: always\n---\n\n")
        assert BEGIN in text

        removed = runner.invoke(main, ["setup", "kiro", "--remove"])
        assert removed.exit_code == 0, removed.output
        assert (
            Path(".kiro/steering/slopvac.md").read_text(encoding="utf-8")
            == "---\ninclusion: always\n---\n"
        )


def test_setup_preserves_crlf_in_existing_instruction_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("AGENTS.md").write_bytes(b"# Local\r\n")
        result = runner.invoke(main, ["setup", "agents"])
        assert result.exit_code == 0, result.output
        data = Path("AGENTS.md").read_bytes()
        assert b"\r\n" in data
        assert b"\n" not in data.replace(b"\r\n", b"")


def test_fenced_marker_examples_do_not_conflict_with_managed_block():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("AGENTS.md").write_text(
            "# Example\n\n```md\n"
            + BEGIN
            + "\nexample\n"
            + END
            + "\n```\n",
            encoding="utf-8",
        )
        installed = runner.invoke(main, ["setup", "agents"])
        assert installed.exit_code == 0, installed.output
        assert managed_block_state(Path("AGENTS.md")) == "current"

        removed = runner.invoke(main, ["setup", "agents", "--remove"])
        assert removed.exit_code == 0, removed.output
        text = Path("AGENTS.md").read_text(encoding="utf-8")
        assert "```md" in text
        assert "example" in text
        assert text.count(BEGIN) == 1
        assert text.count(END) == 1


def test_setup_refuses_instruction_symlink_outside_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    (root / "AGENTS.md").symlink_to(outside)

    runner = CliRunner()
    result = runner.invoke(main, ["setup", "agents", "--root", str(root)])
    assert result.exit_code == 1
    assert "unsafe steering target" in result.output
    assert outside.read_text(encoding="utf-8") == "# Outside\n"
