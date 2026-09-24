from pathlib import Path

from click.testing import CliRunner

from slopvac.cli import main
from slopvac.steering import (
    BEGIN,
    END,
    STEERING_BLOCK,
    harness_path,
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
    assert harness_path(root, "claude") == root / "CLAUDE.md"
    for harness in ("agents", "codex", "omp", "kiro"):
        assert harness_path(root, harness) == root / "AGENTS.md"


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
