"""Writing and review guidance: the rules command the topics delegate to,
`[guidance]` modes, and the `slopvac-prose` skill stub.

The topic assertions compare against the loaded catalogue rather than fixed
text: the topics list no rule, and the rules come from `slopvac rules`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.guidance import RULES_COMMAND
from slopvac.rules import load_ruleset
from slopvac.steering import SKILL_MARKER, SKILL_NAME, SKILL_STUB

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def ruleset():
    return load_ruleset()


def _prime(runner: CliRunner, *args: str):
    result = runner.invoke(main, ["prime", *args])
    assert result.exit_code == 0, result.output
    return result.output


def _guidance(**modes: str) -> None:
    body = "".join(f'{key} = "{value}"\n' for key, value in modes.items())
    Path("slopvac.toml").write_text(f"[guidance]\n{body}", encoding="utf-8")


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize(
    ("depth", "expected", "unexpected"),
    [
        ("self", "self (review_depth = self)", "fresh-context subagent"),
        ("subagent", "give one fresh-context subagent one pass", "Give each new round"),
        ("adversary", "Give each new round the findings you rebutted", "When the user asks"),
    ],
)
def test_review_depth_renders_its_reviewer_workflow(depth, expected, unexpected):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _guidance(review_depth=depth)
        review = _prime(runner, "review")
    assert expected in review
    assert unexpected not in review
    assert "<!-- slopvac-disable -->" in review
    assert "Reviewer:  " in review


def test_subagent_review_describes_no_subagent_fallback():
    runner = CliRunner()
    with runner.isolated_filesystem():
        review = _prime(runner, "review")
    assert '"self (no subagent available)"' in review


def test_base_prime_handoff_matches_configured_review_depth():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _guidance(review_depth="self")
        self_review = _prime(runner)
        _guidance(review_depth="subagent")
        subagent_review = _prime(runner)
        _guidance(review_depth="adversary")
        adversary = _prime(runner)
    assert "reviewer pass" not in self_review
    assert "verdict block" in self_review
    assert "including the reviewer pass" in subagent_review
    assert "including the adversary loop" in adversary


def test_lint_accepts_every_prime_output_at_strict_profile(tmp_path):
    """Base prime and writing, review, and reporting topics pass their strict gate."""
    runner = CliRunner()
    outputs = []
    cases = [
        ("default", {}, ([], ["write"], ["review"], ["report"])),
        ("ask", {"review": "ask"}, ([],)),
        ("adversary", {"review_depth": "adversary"}, ([], ["review"])),
        ("self", {"review_depth": "self"}, ([], ["review"])),
    ]
    with runner.isolated_filesystem():
        for name, modes, topics in cases:
            _guidance(**modes)
            for topic in topics:
                path = tmp_path / f"prime-{'-'.join(topic) or 'base'}-{name}.md"
                path.write_text(_prime(runner, *topic), encoding="utf-8")
                outputs.append(path)

    assert len(outputs) == 9
    for path in outputs:
        result = runner.invoke(
            main, ["lint", str(path), "--profile", "strict", "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["summary"]["errors"] == 0, path.name
        assert payload["summary"]["warnings"] == 0, path.name


# --- the topics delegate the rules to `slopvac rules` ---------------------------


@pytest.mark.parametrize("topic", ["write", "review"])
def test_topics_list_no_rule_and_print_the_rules_command(ruleset, topic):
    runner = CliRunner()
    with runner.isolated_filesystem():
        output = _prime(runner, topic)
    listed = [rule.qualified_id for rule in ruleset.all_rules if rule.qualified_id in output]
    assert not listed, listed
    assert f"\n```bash\n{RULES_COMMAND}\n```\n" in output
    assert "`--rules-dir <dir>`" in output, "house rules need the same option"


def test_topics_are_byte_stable():
    runner = CliRunner()
    with runner.isolated_filesystem():
        for topic in ("write", "review"):
            assert _prime(runner, topic) == _prime(runner, topic)


def test_review_genre_table_lists_the_categories_recommended_for_each_genre(ruleset):
    runner = CliRunner()
    with runner.isolated_filesystem():
        output = _prime(runner, "review")
    lines = output.splitlines()
    header = next(line for line in lines if line.startswith("| Genre |"))
    column = [cell.strip() for cell in header.split("|")].index("Checklist categories")
    row = next(line for line in lines if line.startswith("| `reference`"))
    expected = {
        rule.category
        for rule in ruleset.judgement_rules
        if "reference" in ruleset.categories[rule.category].recommended_for
    }
    listed = {cell.strip("` ") for cell in row.split("|")[column].split(",")}
    assert listed == expected


def test_a_house_judgement_rule_reaches_the_rules_listing(tmp_path):
    house = tmp_path / "house"
    house.mkdir()
    (house / "house.yml").write_text(
        "id: house\n"
        "title: House\n"
        "description: House rules.\n"
        "recommended_for: [consumer]\n"
        "rules:\n"
        "  - id: owner-named\n"
        "    name: Name the owner\n"
        "    kind: judgement\n"
        "    message: Name the team that owns this service.\n"
        "    judgement_question: Does the page name the team that owns it?\n"
        "    fix: Name the owning team in the first paragraph.\n"
        "    provenance:\n"
        "      source: house style\n",
        encoding="utf-8",
    )
    command = RULES_COMMAND.replace("<genre>", "consumer").replace("<profile>", "normal")
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, [*command.split()[1:], "--rules-dir", str(house)])
    assert result.exit_code == 0, result.output
    assert "### `house.owner-named`: Name the owner" in result.output
    assert "Does the page name the team that owns it?" in result.output
    assert "Name the owning team in the first paragraph." in result.output


# --- [guidance] modes ----------------------------------------------------------


def test_default_guidance_routes_to_both_topics():
    runner = CliRunner()
    with runner.isolated_filesystem():
        base = _prime(runner)
        write = _prime(runner, "write")
    assert "slopvac prime write" in base
    assert "slopvac prime review" in base
    assert "slopvac prime review" in write


def test_write_off_disables_the_topic_and_its_prime_line():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _guidance(write="off")
        base = _prime(runner)
        write = _prime(runner, "write")
    assert "slopvac prime write" not in base
    assert "slopvac prime review" in base
    assert write.count("\n") == 1, "the disabled topic prints one line"
    assert "disabled" in write and "slopvac.toml" in write


def test_review_off_disables_the_topic_and_every_hand_off_step():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _guidance(review="off")
        base = _prime(runner)
        write = _prime(runner, "write")
        review = _prime(runner, "review")
    assert "slopvac prime review" not in base
    assert "slopvac prime write" in base
    assert "slopvac prime review" not in write
    assert review.count("\n") == 1
    assert "disabled" in review


def test_review_ask_keeps_the_topic_and_marks_it_as_confirm_first():
    runner = CliRunner()
    with runner.isolated_filesystem():
        auto_review = _prime(runner, "review")
        _guidance(review="ask")
        base = _prime(runner)
        review = _prime(runner, "review")
    assert "slopvac prime review" in base
    assert 'review = "ask"' in review
    assert 'review = "ask"' not in auto_review
    assert "## Checklist" in review


def test_both_off_drops_the_whole_prime_section():
    runner = CliRunner()
    with runner.isolated_filesystem():
        default = _prime(runner)
        _guidance(write="off", review="off")
        base = _prime(runner)
    assert "slopvac prime" in default.split("## Writing and review")[1]
    assert "## Writing and review" not in base
    assert "slopvac lint" in base


def test_report_guidance_is_enabled_by_default_and_omitted_when_off():
    runner = CliRunner()
    with runner.isolated_filesystem():
        default = _prime(runner)
        _guidance(report="off")
        disabled = _prime(runner)
    assert "## Reporting slopvac problems" in default
    assert "## Reporting slopvac problems" not in disabled


def test_report_topic_off_prints_the_disabled_notice_without_ruleset_loading():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _guidance(report="off")
        result = runner.invoke(main, ["prime", "report"])
    assert result.exit_code == 0, result.output
    assert result.output.count("\n") == 1
    assert 'report = "off"' in result.output

def test_report_topic_contains_workflow_commands_and_category_skeletons():
    from slopvac.reporting import REPORT_CATEGORIES

    runner = CliRunner()
    with runner.isolated_filesystem():
        output = _prime(runner, "report")
    for expected in (
        "uvx --from slopvac@latest slopvac --version",
        "gh issue list -R srobroek/slopvac",
        "gh label list -R srobroek/slopvac --json name",
        "gh issue comment <N> -R srobroek/slopvac --body-file <file>",
        "gh issue create -R srobroek/slopvac --title",
        "When the latest version is not newer, do not rerun the command.",
        "When it is newer, rerun with `uvx --from slopvac@latest slopvac ...`.",
    ):
        assert expected in output
    assert "q=is%3Aissue+<url-encoded-rule-ID-or-generic-symptom>" in output
    assert "search includes open and closed issues" in output
    assert "When you have read the results, tick `I searched existing issues for duplicates`. Otherwise, wait for the user's confirmation." in output
    assert "no valid release cache is available; doctor does not fetch a release" in output
    assert output.index("slopvac lint --stdin --format json") < output.index("6. Search for duplicates")
    assert "repro.md" not in output
    assert output.index("5. When you need a reproduction") < output.index("6. Search for duplicates")
    for category in REPORT_CATEGORIES:
        category_skeleton = output.split(f"### `{category.key}`\n", 1)[1]
        category_skeleton = category_skeleton.split("### `", 1)[0]
        for field in category.fields:
            assert f"### {field.label}" in category_skeleton
            if field.type == "checkboxes":
                for label, _ in field.checkbox_options:
                    assert f"- [ ] {label}" in category_skeleton
            if field.description:
                assert field.description not in category_skeleton, (
                    "a submitted form never contains field descriptions"
                )


def test_report_skeletons_use_github_checkbox_markdown():
    from slopvac.guidance import _skeleton
    from slopvac.reporting import REPORT_CATEGORIES

    skeleton = "\n".join(_skeleton(REPORT_CATEGORIES[0]))
    assert "### Reporter\n\n- [ ] Reported by an AI agent" in skeleton
    assert "### Duplicate search\n\n- [ ] I searched existing issues for duplicates" in skeleton


def test_report_discloses_agents_in_forms_and_comments():
    from slopvac.reporting import REPORT_CATEGORIES

    runner = CliRunner()
    with runner.isolated_filesystem():
        output = _prime(runner, "report")
    disclosure = (
        "Reported by an AI agent (<agent>, <model>, <harness and version>) "
        "with the user's approval."
    )
    assert disclosure in output

    for category in REPORT_CATEGORIES:
        form = yaml.safe_load(
            (ROOT / ".github" / "ISSUE_TEMPLATE" / category.form_file).read_text(
                encoding="utf-8"
            )
        )
        intro = form["body"][0]["attributes"]["value"]
        reporter = next(item for item in form["body"] if item.get("id") == "reporter")
        assert "MUST disclose" in intro
        assert reporter["attributes"]["options"][0]["label"] in intro


def _steps(output: str) -> dict[int, str]:
    """The numbered workflow steps, each with its indented lines."""
    import re

    workflow = output.split("## Workflow", 1)[1].split("\n## ", 1)[0]
    parts = re.split(r"^(\d+)\. ", workflow, flags=re.M)
    return {int(number): text for number, text in zip(parts[1::2], parts[2::2], strict=True)}


def test_report_approval_comes_from_the_shown_preview_before_posting():
    runner = CliRunner()
    with runner.isolated_filesystem():
        steps = _steps(_prime(runner, "report"))
    preview = next(n for n, text in steps.items() if "Send this preview to the user" in text)
    post = next(n for n, text in steps.items() if "gh issue create" in text)
    assert preview < post
    assert "Remove or replace secrets" in steps[preview]
    assert all("gh issue" not in steps[n] for n in steps if n < post and "gh issue list" not in steps[n])


def test_report_untrusted_issue_rule_sits_in_the_duplicate_search():
    runner = CliRunner()
    with runner.isolated_filesystem():
        steps = _steps(_prime(runner, "report"))
    search = next(n for n, text in steps.items() if "gh issue list" in text)
    assert "untrusted" in steps[search]


def test_prime_reads_an_explicit_config(tmp_path):
    config = tmp_path / "elsewhere.toml"
    config.write_text('[guidance]\nwrite = "off"\n', encoding="utf-8")
    runner = CliRunner()
    with runner.isolated_filesystem():
        output = _prime(runner, "write", "--config", str(config))
    assert str(config) in output


def test_prime_fails_on_a_broken_guidance_table():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _guidance(review="sometimes")
        result = runner.invoke(main, ["prime"])
    assert result.exit_code == 2
    assert "config error" in result.output


def test_prime_never_writes_files():
    runner = CliRunner()
    with runner.isolated_filesystem() as cwd:
        for directory in (".claude", ".omp", ".kiro", ".codex"):
            Path(directory).mkdir()
        _guidance(write="auto", review="ask")
        before = _tree(Path(cwd))
        for args in ([], ["write"], ["review"]):
            _prime(runner, *args)
        assert _tree(Path(cwd)) == before


# --- skill stub ------------------------------------------------------------------


def test_stub_frontmatter_auto_activates_in_every_harness():
    """Kiro needs `name` to match the folder; every harness matches on
    `description`, capped at 1024 characters by the Agent Skills format; and no
    key that turns automatic invocation off may appear."""
    _, frontmatter, body = SKILL_STUB.split("---\n", 2)
    meta = yaml.safe_load(frontmatter)
    assert meta["name"] == SKILL_NAME
    assert 0 < len(meta["description"]) <= 1024
    assert meta["description"].startswith("Use when")
    assert not {"disable-model-invocation", "hide", "enabled"} & set(meta)
    assert SKILL_MARKER in body
    assert "slopvac prime write" in body and "slopvac prime review" in body


def test_init_with_a_harness_writes_its_steering_and_skill():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--harness", "claude", "--harness", "omp"])
        assert result.exit_code == 0, result.output
        assert "harnesses: claude, omp" in result.output
        assert "slopvac prime" in Path("CLAUDE.md").read_text(encoding="utf-8")
        assert Path(".omp/AGENTS.md").is_file()
        for directory in (".claude/skills", ".omp/skills"):
            stub = Path(directory) / SKILL_NAME / "SKILL.md"
            assert stub.read_text(encoding="utf-8") == SKILL_STUB
        assert not Path("AGENTS.md").exists()


def test_init_no_skills_writes_steering_only():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--harness", "claude", "--no-skills"])
        assert result.exit_code == 0, result.output
        assert Path("CLAUDE.md").is_file()
        assert not Path(".claude/skills").exists()


def test_init_without_a_harness_writes_no_skill_even_beside_harness_dirs():
    runner = CliRunner()
    with runner.isolated_filesystem() as cwd:
        Path(".claude").mkdir()
        Path(".omp").mkdir()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").is_file()
        assert not [path for path in Path(cwd).rglob("SKILL.md")]


def test_init_rejects_harness_with_skip_agents():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--skip-agents", "--harness", "omp"])
        assert result.exit_code == 2
        assert not Path("slopvac.toml").exists()


def test_agents_harness_has_no_skill():
    runner = CliRunner()
    with runner.isolated_filesystem() as cwd:
        result = runner.invoke(main, ["setup", "agents"])
        assert result.exit_code == 0, result.output
        assert not [path for path in Path(cwd).rglob("SKILL.md")]


def test_setup_installs_checks_and_removes_only_its_own_skill():
    runner = CliRunner()
    stub = Path(".omp/skills") / SKILL_NAME / "SKILL.md"
    with runner.isolated_filesystem():
        neighbour = Path(".omp/skills/other/SKILL.md")
        neighbour.parent.mkdir(parents=True)
        neighbour.write_text("---\nname: other\n---\n", encoding="utf-8")

        assert runner.invoke(main, ["setup", "omp"]).exit_code == 0
        assert stub.read_text(encoding="utf-8") == SKILL_STUB
        assert runner.invoke(main, ["setup", "omp", "--check"]).exit_code == 0

        stub.write_text(SKILL_STUB.replace("prime write", "prime old"), encoding="utf-8")
        stale = runner.invoke(main, ["setup", "omp", "--check"])
        assert stale.exit_code == 1
        assert f"stale {stub.resolve()}" in stale.output

        assert runner.invoke(main, ["setup", "omp"]).exit_code == 0
        assert stub.read_text(encoding="utf-8") == SKILL_STUB

        extra = stub.parent / "notes.md"
        extra.write_text("mine\n", encoding="utf-8")
        removed = runner.invoke(main, ["setup", "omp", "--remove"])
        assert removed.exit_code == 0, removed.output
        assert not stub.exists()
        assert extra.read_text(encoding="utf-8") == "mine\n"
        assert neighbour.is_file()

        extra.unlink()
        assert runner.invoke(main, ["setup", "omp"]).exit_code == 0
        assert runner.invoke(main, ["setup", "omp", "--remove"]).exit_code == 0
        assert not stub.parent.exists(), "an emptied stub directory is removed"
        assert neighbour.is_file()


def test_setup_refuses_a_hand_written_skill_at_the_stub_path():
    runner = CliRunner()
    stub = Path(".claude/skills") / SKILL_NAME / "SKILL.md"
    with runner.isolated_filesystem():
        stub.parent.mkdir(parents=True)
        stub.write_text("---\nname: slopvac-prose\n---\nmine\n", encoding="utf-8")

        installed = runner.invoke(main, ["setup", "claude"])
        assert installed.exit_code == 1
        assert "not a slopvac-managed skill" in installed.output
        assert runner.invoke(main, ["setup", "claude", "--check"]).exit_code == 2
        assert runner.invoke(main, ["setup", "claude", "--remove"]).exit_code == 1
        assert stub.read_text(encoding="utf-8") == "---\nname: slopvac-prose\n---\nmine\n"


@pytest.mark.parametrize(
    "text",
    [
        # A skill that documents slopvac and quotes the marker in its body.
        f"---\nname: slopvac-prose\n---\n# Notes\n\nOurs carry `{SKILL_MARKER}`.\n",
        # The marker line, but not directly after the frontmatter.
        f"---\nname: slopvac-prose\n---\n\n{SKILL_MARKER}\n",
        # No frontmatter at all.
        f"{SKILL_MARKER}\n",
    ],
)
def test_a_skill_that_only_mentions_the_marker_is_not_owned(text):
    runner = CliRunner()
    stub = Path(".omp/skills") / SKILL_NAME / "SKILL.md"
    with runner.isolated_filesystem():
        stub.parent.mkdir(parents=True)
        stub.write_text(text, encoding="utf-8")

        installed = runner.invoke(main, ["setup", "omp"])
        assert installed.exit_code == 1
        assert "not a slopvac-managed skill" in installed.output
        assert runner.invoke(main, ["setup", "omp", "--check"]).exit_code == 2
        assert runner.invoke(main, ["setup", "omp", "--remove"]).exit_code == 1
        assert stub.read_text(encoding="utf-8") == text


def test_a_skill_with_invalid_utf8_is_not_owned():
    runner = CliRunner()
    stub = Path(".claude/skills") / SKILL_NAME / "SKILL.md"
    with runner.isolated_filesystem():
        stub.parent.mkdir(parents=True)
        data = SKILL_STUB.encode("utf-8") + b"\xff\xfe"
        stub.write_bytes(data)
        installed = runner.invoke(main, ["setup", "claude"])
        assert installed.exit_code == 1
        assert stub.read_bytes() == data


def test_setup_refuses_a_skill_directory_symlinked_outside_the_project(tmp_path):
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    (root / ".claude").mkdir(parents=True)
    outside.mkdir()
    (root / ".claude" / "skills").symlink_to(outside, target_is_directory=True)

    result = CliRunner().invoke(main, ["setup", "claude", "--root", str(root)])
    assert result.exit_code == 1
    assert "unsafe steering target" in result.output
    assert not list(outside.rglob("*"))


def test_both_guidance_modes_off_skip_and_remove_the_stub():
    runner = CliRunner()
    stub = Path(".kiro/skills") / SKILL_NAME / "SKILL.md"
    with runner.isolated_filesystem():
        assert runner.invoke(main, ["setup", "kiro"]).exit_code == 0
        assert stub.is_file()

        _guidance(write="off", review="off")
        stale = runner.invoke(main, ["setup", "kiro", "--check"])
        assert stale.exit_code == 1, "setup would remove the stub"

        assert runner.invoke(main, ["setup", "kiro"]).exit_code == 0
        assert not stub.exists()
        assert Path(".kiro/steering/slopvac.md").is_file(), "steering stays"
        checked = runner.invoke(main, ["setup", "kiro", "--check"])
        assert checked.exit_code == 0
        assert "disabled " in checked.output


# --- judgement rules stay out of lint --------------------------------------------


def test_judgement_rules_never_produce_findings(ruleset):
    """Every judgement example's `bad` text, linted at every profile, yields no
    finding and no SARIF descriptor for a judgement rule."""
    judgement = {rule.qualified_id for rule in ruleset.judgement_rules}
    text = "\n\n".join(
        example.bad for rule in ruleset.judgement_rules for example in rule.examples
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("doc.md").write_text(text + "\n", encoding="utf-8")
        for profile in ("strict", "normal", "relaxed"):
            result = runner.invoke(
                main,
                ["lint", "doc.md", "--no-vale", "--profile", profile, "--format", "json"],
            )
            payload = json.loads(result.output)
            found = {
                finding["rule_id"]
                for document in payload["documents"]
                for finding in document["findings"]
            }
            assert found, "the corpus must exercise some checked rule"
            assert not found & judgement, profile

        sarif = runner.invoke(main, ["lint", "doc.md", "--no-vale", "--format", "sarif"])
        log = json.loads(sarif.output)
        descriptors = {rule["id"] for rule in log["runs"][0]["tool"]["driver"]["rules"]}
        results = {result["ruleId"] for result in log["runs"][0]["results"]}
        assert descriptors and not (descriptors | results) & judgement
