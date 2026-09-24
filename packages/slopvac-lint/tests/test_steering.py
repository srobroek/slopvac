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


def test_prime_contains_lint_and_judgement_commands():
    runner = CliRunner()
    result = runner.invoke(main, ["prime"])
    assert result.exit_code == 0
    assert "slopvac lint" in result.output
    assert "slopvac judgement brief" in result.output
    assert "slopvac judgement finish" in result.output

    judgement = runner.invoke(main, ["prime", "judgement"])
    assert judgement.exit_code == 0
    assert "slopvac judgement validate" in judgement.output


def test_onboard_prints_prime_guidance():
    runner = CliRunner()
    result = runner.invoke(main, ["onboard"])
    assert result.exit_code == 0
    assert "Slopvac lint guidance" in result.output
    assert "Slopvac judgement guidance" in result.output


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
        assert "missing AGENTS.md" in missing.output
        assert not Path("AGENTS.md").exists()

        installed = runner.invoke(main, ["setup", "codex"])
        assert installed.exit_code == 0, installed.output
        before = Path("AGENTS.md").read_text(encoding="utf-8")

        current = runner.invoke(main, ["setup", "codex", "--check"])
        assert current.exit_code == 0
        assert "current AGENTS.md" in current.output
        assert Path("AGENTS.md").read_text(encoding="utf-8") == before

        Path("AGENTS.md").write_text(before.replace("slopvac prime", "slopvac old-prime"), encoding="utf-8")
        stale = runner.invoke(main, ["setup", "codex", "--check"])
        assert stale.exit_code == 1
        assert "stale AGENTS.md" in stale.output


def test_setup_check_rejects_remove_combination():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["setup", "codex", "--check", "--remove"])
        assert result.exit_code == 2
        assert "--check and --remove cannot be used together" in result.output
