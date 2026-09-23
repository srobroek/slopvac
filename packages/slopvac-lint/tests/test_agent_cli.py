"""CLI setup must preserve the user's files and expose both review workflows."""
from __future__ import annotations

import json
import os

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.config import load_config
from slopvac.steering import BEGIN, END, Edit, SteeringError, apply_edits, snippet


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path, CliRunner()


def invoke(runner, *args, code=0):
    result = runner.invoke(main, list(args))
    assert result.exit_code == code, result.output
    return result


@pytest.mark.parametrize('harness,target', [
    ('generic', 'AGENTS.md'), ('claude', 'CLAUDE.md'), ('codex', 'AGENTS.md'),
    ('omp', 'AGENTS.md'), ('kiro', '.kiro/steering/slopvac.md'),
])
def test_init_for_each_harness(project, harness, target):
    root, runner = project
    invoke(runner, 'init', '--harness', harness)
    assert (root / target).read_text().endswith(snippet())
    assert load_config(root / 'slopvac.toml').profile.value == 'normal'
    invoke(runner, 'setup', harness, '--check')


def test_default_init_and_repeat_are_idempotent(project):
    root, runner = project
    invoke(runner, 'init')
    original = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    times = {p: p.stat().st_mtime_ns for p in original}
    result = invoke(runner, 'init')
    assert 'unchanged' in result.output
    assert all(p.read_bytes() == data and p.stat().st_mtime_ns == times[p]
               for p, data in original.items())


def test_existing_config_is_preserved_but_steering_is_installed(project):
    root, runner = project
    content = b'profile = "strict"\n[thresholds]\nmax_warnings = 3\n'
    (root / 'slopvac.toml').write_bytes(content)
    invoke(runner, 'init', '--profile', 'relaxed')
    assert (root / 'slopvac.toml').read_bytes() == content
    assert (root / 'AGENTS.md').is_file()
    invoke(runner, 'init', '--force', '--profile', 'relaxed')
    assert load_config(root / 'slopvac.toml').profile.value == 'relaxed'


def test_skip_agents_and_dry_run_do_not_write_steering(project):
    root, runner = project
    invoke(runner, 'init', '--dry-run')
    assert not list(root.iterdir())
    invoke(runner, 'init', '--skip-agents')
    assert not (root / 'AGENTS.md').exists()
    invoke(runner, 'init', '--skip-agents', '--harness', 'claude', code=2)


def test_path_is_root_for_initialization(project):
    root, runner = project
    invoke(runner, 'init', '--path', 'sub/slopvac.toml', '--harness', 'kiro')
    assert (root / 'sub/.kiro/steering/slopvac.md').read_text().startswith(
        '---\ninclusion: always\n---\n\n')
    assert not (root / 'slopvac.toml').exists()


def test_check_stale_refresh_remove_preserves_other_instructions(project):
    root, runner = project
    path = root / 'AGENTS.md'
    before = '# Project\n\nNever change licenses.\n\n'
    after = '\n## Tests\n\nRun pytest.\n'
    path.write_text(before + BEGIN + '\nold\n' + END + '\n' + after)
    invoke(runner, 'setup', 'generic', '--check', code=1)
    invoke(runner, 'setup', 'generic')
    assert path.read_text() == before + snippet() + after
    invoke(runner, 'setup', 'generic', '--check')
    invoke(runner, 'setup', 'generic', '--remove')
    assert path.read_text() == before + after
    invoke(runner, 'setup', 'generic', '--check', code=1)


def test_crlf_bom_file_permissions_and_fenced_markers(project):
    root, runner = project
    path = root / 'CLAUDE.md'
    original = ('\ufeff# Project\r\n\r\n```md\r\n' + BEGIN + '\r\n' + END
                + '\r\n```\r\n\r\n').encode('utf-8')
    path.write_bytes(original)
    path.chmod(0o640)
    invoke(runner, 'setup', 'claude')
    expected = original + snippet().replace('\n', '\r\n').encode()
    assert path.read_bytes() == expected
    if os.name != 'nt':
        assert path.stat().st_mode & 0o777 == 0o640
    invoke(runner, 'setup', 'claude')
    assert path.read_bytes() == expected
    invoke(runner, 'setup', 'claude', '--remove')
    assert path.read_bytes() == original


@pytest.mark.parametrize('text', [BEGIN, END, END+'\n'+BEGIN,
                                   BEGIN+'\n'+BEGIN+'\n'+END,
                                   BEGIN+'\n'+END+'\n'+BEGIN+'\n'+END])
def test_malformed_markers_fail_before_creating_config(project, text):
    root, runner = project
    path = root / 'AGENTS.md'
    path.write_text(text)
    invoke(runner, 'init', code=2)
    assert path.read_text() == text
    assert not (root / 'slopvac.toml').exists()


def test_all_targets_are_preflighted_before_any_write(project):
    root, runner = project
    (root / 'CLAUDE.md').write_text(END)
    invoke(runner, 'init', '--harness', 'generic', '--harness', 'claude', code=2)
    assert not (root / 'AGENTS.md').exists()
    assert not (root / 'slopvac.toml').exists()


def test_internal_symlink_is_preserved_and_deduplicated(project):
    root, runner = project
    (root / 'AGENTS.md').write_text('# Shared\n')
    (root / 'CLAUDE.md').symlink_to('AGENTS.md')
    invoke(runner, 'init', '--harness', 'generic', '--harness', 'claude', '--harness', 'codex')
    assert (root / 'CLAUDE.md').is_symlink()
    assert (root / 'AGENTS.md').read_text().count(BEGIN) == 1


def test_external_symlink_is_rejected(project, tmp_path_factory):
    root, runner = project
    outside = tmp_path_factory.mktemp('outside') / 'AGENTS.md'
    outside.write_text('Private instructions\n')
    (root / 'CLAUDE.md').symlink_to(outside)
    invoke(runner, 'init', '--harness', 'claude', code=2)
    assert outside.read_text() == 'Private instructions\n'
    assert not (root / 'slopvac.toml').exists()


def test_external_config_symlink_is_rejected(project, tmp_path_factory):
    root, runner = project
    outside = tmp_path_factory.mktemp('config') / 'slopvac.toml'
    outside.write_text('profile = "strict"\n')
    (root / 'slopvac.toml').symlink_to(outside)
    invoke(runner, 'init', '--force', code=2)
    assert outside.read_text() == 'profile = "strict"\n'
    assert not (root / 'AGENTS.md').exists()


def test_invalid_utf8_and_directory_fail(project):
    root, runner = project
    path = root / 'CLAUDE.md'
    path.write_bytes(b'\xff')
    invoke(runner, 'setup', 'claude', code=2)
    assert path.read_bytes() == b'\xff'
    path.unlink()
    path.mkdir()
    invoke(runner, 'setup', 'claude', code=2)


@pytest.mark.parametrize('harness,alternative', [
    ('codex', 'AGENTS.override.md'), ('omp', '.omp/AGENTS.md'),
])
def test_existing_harness_override_is_updated(project, harness, alternative):
    root, runner = project
    active = root / alternative
    active.parent.mkdir(exist_ok=True)
    active.write_text('# Active\n')
    (root / 'AGENTS.md').write_text('# Shared\n')
    invoke(runner, 'setup', harness)
    assert BEGIN in active.read_text()
    assert (root / 'AGENTS.md').read_text() == '# Shared\n'
    invoke(runner, 'setup', harness, '--check')


def test_setup_operations_do_not_write_config(project):
    root, runner = project
    invoke(runner, 'setup', '--list')
    invoke(runner, 'setup', 'claude', '--check', code=1)
    invoke(runner, 'setup', 'claude', '--dry-run')
    invoke(runner, 'setup', 'claude', '--remove')
    assert not list(root.iterdir())
    invoke(runner, 'setup', 'claude', '--root', 'nested')
    assert (root / 'nested/CLAUDE.md').is_file()
    assert not (root / 'nested/slopvac.toml').exists()


def test_onboard_and_prime_are_read_only_without_vale(project, monkeypatch):
    root, runner = project
    monkeypatch.setenv('PATH', '')
    assert invoke(runner, 'onboard').output == snippet()
    for topic in ('all', 'overview', 'lint', 'judgement'):
        data = json.loads(invoke(runner, 'prime', topic, '--format', 'json').output)
        assert data['schema_version'] == 1 and data['topic'] == topic
        assert data['guidance'] and len(data['categories']) == 26
    assert not list(root.iterdir())


def test_prime_genre_uses_catalog_metadata(project):
    _, runner = project
    data = json.loads(invoke(runner, 'prime', '--genre', 'consumer', '--format', 'json').output)
    assert data['categories']
    assert all('consumer' in c['recommended_for'] for c in data['categories'])


def test_race_is_detected_before_write(tmp_path):
    path = tmp_path / 'AGENTS.md'
    path.write_bytes(b'changed')
    with pytest.raises(SteeringError, match='changed during setup'):
        apply_edits([Edit(path, b'original', b'new')])
    assert path.read_bytes() == b'changed'
