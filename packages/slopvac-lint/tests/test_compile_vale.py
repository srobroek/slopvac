"""The compiler, and every claim it makes about Vale, proven by execution.

A COMPILED RULE THAT DOES NOT FIRE IS WORTHLESS, and worse than worthless: Vale
reports the file clean and exits 0, so a rule that silently stopped matching is
indistinguishable from prose that complies. Every test here that asserts a rule
compiles also runs Vale and asserts the finding, for the same reason `rules.py`
validates each regex against its own examples.

These tests need the `vale` binary and skip without it. That is deliberate: a
green suite on a machine with no Vale would assert only that we can write YAML.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from slopvac.analyze import count_words
from slopvac.compile_vale import (
    STE_WORD_TOKEN,
    CompileResult,
    _occurrence_bound,
    cache_root,
    compile_ruleset,
    resolved_checks,
    vocabulary_sequence_rules,
)
from slopvac.config import (
    CategorySettings,
    Config,
    Profile,
    RuleSettings,
    Severity,
    resolve_for,
)
from slopvac.model import RuleKind, TextType
from slopvac.rules import load_ruleset
from slopvac.vocabulary import load_blocklist

VALE = shutil.which("vale")
needs_vale = pytest.mark.skipif(VALE is None, reason="vale is not on PATH")


@pytest.fixture(scope="module")
def ruleset():
    return load_ruleset()


EXAMPLE_BLOCKLIST = Path(__file__).parent.parent / "examples" / "blocklist.toml"


@pytest.fixture(scope="module")
def vocabulary():
    """The shipped example blocklist.

    A real file rather than a fixture built in-test, so these tests exercise the
    path a user takes and the example stays honest: if it stops loading, this
    module fails. There is no packaged default wordlist to fall back on -- the
    dictionary that used to serve as one was deleted, because as an allowlist it
    made every unlisted word a finding.
    """
    return load_blocklist(EXAMPLE_BLOCKLIST)


@pytest.fixture(scope="module")
def compiled(ruleset, vocabulary, tmp_path_factory):
    """One compile for the whole module: it probes every rule through Vale, which
    is the slow part, and no test here mutates the output."""
    outdir = tmp_path_factory.mktemp("compiled")
    config = resolve_for(Config(), Path("README.md"))
    return compile_ruleset(
        ruleset, config, outdir=outdir, validate=VALE is not None, vocabulary=vocabulary, force=True
    )


def _lint(config_path: Path, text: str, tmp_path: Path, name: str = "probe.md") -> list[dict]:
    """Run Vale over `text` and return its alerts."""
    target = tmp_path / name
    target.write_text(text, encoding="utf-8")
    completed = subprocess.run(
        [VALE, f"--config={config_path}", "--output=JSON", "--no-exit", str(target)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined = completed.stdout + completed.stderr
    assert "E201" not in combined, f"a compiled rule failed to load: {combined[:400]}"
    if not completed.stdout.strip():
        return []
    data = json.loads(completed.stdout)
    return [alert for alerts in data.values() for alert in alerts]


def _checks(config_path: Path, text: str, tmp_path: Path) -> set[str]:
    return {alert["Check"] for alert in _lint(config_path, text, tmp_path)}


# --- routing ------------------------------------------------------------------


def test_every_rule_is_routed_exactly_once(compiled, ruleset):
    """No rule is silently dropped.

    The four buckets must partition the ruleset. A rule in none of them would
    load, never run, and never be reported as unrun -- the failure this project
    exists to prevent.
    """
    routed = (
        set(compiled.vale_rules)
        | {n.rule_id for n in compiled.native_rules}
        | set(compiled.judgement_rules)
        | set(compiled.disabled_rules)
    )
    # A generated rule reports under its owner, so it is not a ruleset id itself.
    routed -= set(compiled.aliases)
    routed |= set(compiled.aliases.values())

    expected = {rule.qualified_id for rule in ruleset.rules}
    assert routed == expected, f"unrouted: {expected - routed}, invented: {routed - expected}"


def test_each_kind_routes_to_the_expected_engine(compiled, ruleset):
    """Lexical and countable rules go to Vale; judgement goes nowhere."""
    by_id = {r.qualified_id: r for r in ruleset.rules}
    vale = set(compiled.vale_rules) - set(compiled.aliases)

    for kind in (RuleKind.TOKENS, RuleKind.SUBSTITUTION):
        ids = {r.qualified_id for r in ruleset.rules if r.kind is kind}
        assert ids <= vale, f"{kind.value} rules did not all compile: {ids - vale}"

    # Every judgement rule, and only judgement rules, is in that bucket.
    assert set(compiled.judgement_rules) == {
        r.qualified_id for r in ruleset.rules if r.kind is RuleKind.JUDGEMENT
    }
    for rule_id in compiled.judgement_rules:
        assert rule_id not in vale
        assert by_id[rule_id].kind is RuleKind.JUDGEMENT


def test_sentence_words_metric_compiles_to_vale(compiled, ruleset):
    """The correction that reversed the original design, now with its own limit.

    STE word counting was believed to be inexpressible in Vale. One ordered
    alternation reproduces it, so a word-count rule is Vale's -- UNLESS it is scoped
    to a text type. Vale counts a sentence's words but cannot ask whether that
    sentence is an instruction or an explanation, and a compiled `text_type` rule
    silently applies one type's cap to every sentence: a 35-word descriptive sentence
    drew both the 25-word descriptive finding (native, right) and the 20-word
    procedural one (Vale, wrong).
    """
    word_rules = {
        r.qualified_id
        for r in ruleset.rules
        if r.kind is RuleKind.METRIC and r.metric == "sentence_words"
    }
    assert word_rules
    typed = {
        r.qualified_id
        for r in ruleset.rules
        if r.kind is RuleKind.METRIC
        and r.metric == "sentence_words"
        and r.text_type is not TextType.ANY
    }
    assert typed, "expected at least one text-type-scoped word-count rule"
    # The untyped ones still go to Vale; the typed ones must not.
    assert (word_rules - typed) <= set(compiled.vale_rules)
    assert not (typed & set(compiled.vale_rules))
    native = {n.rule_id for n in compiled.native_rules}
    assert typed <= native, "a text-type-scoped rule must be routed native, not dropped"


def test_vocabulary_rules_compile_to_grouped_sequence_rules(compiled, ruleset):
    """A blocklist of any size becomes a handful of rules, not one per word."""
    owners = {r.qualified_id for r in ruleset.rules if r.kind is RuleKind.VOCABULARY}
    aliased = set(compiled.aliases.values())
    assert owners & aliased, "no vocabulary rule was compiled to a sequence rule"
    # Four parts of speech carry Penn tags, so one owner yields at most four rules.
    assert len(compiled.aliases) <= 4 * len(owners)


# --- the RE2 boundary ---------------------------------------------------------


@needs_vale
def test_lookbehind_pattern_stays_native_when_vale_rejects_it(ruleset, tmp_path, vocabulary):
    """A pattern Vale will not compile must be routed native, never emitted.

    One unloadable rule makes Vale abort and lint NOTHING, so emitting a rule that
    fails to compile turns the whole run into a false pass. The routing decision
    is made by asking Vale, so this asserts the mechanism on the real ruleset: the
    two `\\U`-escaped emoji patterns are rejected by Go's regexp and stay native.
    """
    config = resolve_for(Config(), Path("README.md"))
    result = compile_ruleset(
        ruleset, config, outdir=tmp_path / "out", validate=True, vocabulary=vocabulary, force=True
    )
    native = result.native_reasons()
    rejected = {
        rule_id for rule_id, reason in native.items() if "will not compile" in reason
    }
    assert rejected, "expected at least one pattern Vale refuses"
    for rule_id in rejected:
        assert rule_id not in result.vale_rules
        assert "error parsing regexp" in native[rule_id]


@needs_vale
def test_a_rejected_pattern_never_reaches_the_style_tree(compiled):
    """The written tree holds only what Vale accepted.

    A rejected rule left on disk would be picked up by a later run from the cache
    and would abort that run instead.
    """
    written = {
        f"{path.parent.name}.{path.stem}"
        for path in (compiled.outdir / "styles").rglob("*.yml")
    }
    assert written == set(compiled.vale_rules)


@needs_vale
def test_the_compiled_tree_loads_with_no_error(compiled, tmp_path):
    """Every emitted rule resolves. A rule absent from `ls-config` never runs."""
    actual = resolved_checks(compiled.config_path)
    assert actual is not None
    assert set(compiled.vale_rules) <= actual


# --- the generated ini --------------------------------------------------------


def test_ini_omits_rules_resolved_to_off(ruleset, vocabulary, tmp_path):
    """A disabled rule must be absent from the ini, not written as a level.

    This is the only path config layering has into Vale, so a rule the project
    turned off has to disappear here or it keeps firing.
    """
    config = Config()
    config.rules["prose-inflation.slop-lexicon"] = RuleSettings(severity=Severity.OFF)
    resolved = resolve_for(config, Path("README.md"))
    result = compile_ruleset(
        ruleset, resolved, outdir=tmp_path / "off", validate=False, vocabulary=vocabulary, force=True
    )

    assert "prose-inflation.slop-lexicon" not in result.vale_rules
    assert "prose-inflation.slop-lexicon" in result.disabled_rules
    text = result.config_path.read_text(encoding="utf-8")
    assert "prose-inflation.slop-lexicon" not in text


def test_ini_carries_our_resolved_severity(ruleset, vocabulary, tmp_path):
    """The level in the ini is the one our precedence chain produced.

    A category cap lowers a rule, so the ini has to show the lowered level rather
    than the rule's shipped one.
    """
    config = Config()
    config.categories["prose-inflation"] = CategorySettings(severity=Severity.SUGGESTION)
    resolved = resolve_for(config, Path("README.md"))
    result = compile_ruleset(
        ruleset, resolved, outdir=tmp_path / "cap", validate=False, vocabulary=vocabulary, force=True
    )

    lines = result.config_path.read_text(encoding="utf-8").splitlines()
    capped = [line for line in lines if line.startswith("prose-inflation.")]
    assert capped
    for line in capped:
        assert line.endswith("= suggestion"), line


def test_disabled_category_removes_every_rule_in_it(ruleset, vocabulary, tmp_path):
    config = Config()
    config.categories["orwell"] = CategorySettings(enabled=False)
    resolved = resolve_for(config, Path("README.md"))
    result = compile_ruleset(
        ruleset, resolved, outdir=tmp_path / "cat", validate=False, vocabulary=vocabulary, force=True
    )
    assert not [r for r in result.vale_rules if r.startswith("orwell.")]
    text = result.config_path.read_text(encoding="utf-8")
    assert "orwell." not in text


@needs_vale
def test_severity_in_the_ini_is_what_vale_reports(ruleset, vocabulary, tmp_path):
    """Our level reaches Vale's output, which is what makes the echo trustworthy."""
    config = Config()
    config.categories["prose-inflation"] = CategorySettings(severity=Severity.SUGGESTION)
    resolved = resolve_for(config, Path("README.md"))
    result = compile_ruleset(
        ruleset, resolved, outdir=tmp_path / "sev", validate=True, vocabulary=vocabulary, force=True
    )
    alerts = _lint(result.config_path, "We leverage the seamless approach.\n", tmp_path)
    inflation = [a for a in alerts if a["Check"].startswith("prose-inflation.")]
    assert inflation, "expected a prose-inflation finding"
    for alert in inflation:
        assert alert["Severity"] == "suggestion"


# --- occurrence bounds --------------------------------------------------------


def test_a_zero_bound_is_refused(ruleset):
    """`max: 0` reads as unset in Vale and the rule never fires.

    Measured: a rule with `max: 0` loads, resolves, reports nothing, and looks
    exactly like a clean document. The compiler raises rather than emit one.
    """
    rule = next(r for r in ruleset.rules if r.kind is RuleKind.METRIC and r.threshold)
    probe = rule.model_copy(update={"threshold": 0.0, "comparison": "gt"})
    with pytest.raises(ValueError, match="never fire"):
        _occurrence_bound(probe)


def test_comparison_maps_to_the_right_vale_bound(ruleset):
    """gt/gte become `max`; lt/lte become `min`."""
    rule = next(r for r in ruleset.rules if r.kind is RuleKind.METRIC and r.threshold)
    assert _occurrence_bound(rule.model_copy(update={"threshold": 20.0, "comparison": "gt"})) == ("max", 20)
    assert _occurrence_bound(rule.model_copy(update={"threshold": 20.0, "comparison": "gte"})) == ("max", 19)
    assert _occurrence_bound(rule.model_copy(update={"threshold": 9.0, "comparison": "lt"})) == ("min", 9)
    assert _occurrence_bound(rule.model_copy(update={"threshold": 8.0, "comparison": "lte"})) == ("min", 9)


# --- the word-count contract --------------------------------------------------

# The oracle corpus. `count_words` implements `docs/metrics.md`, so Vale agreeing
# with it on every one of these is what stops the generated regex drifting from
# the specification. The first is the specification's own worked example.
WORD_COUNT_CORPUS = [
    "Do steps 13 thru 16 a minimum of three times.",
    'Set the timeout to 30 s for the HTTP client in the "edge gateway" service.',
    "Close the valve.",
    "The in-flight request count reached 512 MiB of buffered data.",
    "Wait 10 ms (or longer if the link is slow) before you retry.",
    'Refer to the "Installation and Setup Guide" for more information.',
    "The temperature must not be more than 30 degC during the test.",
    "Make sure that the SHA256 checksum of the file is correct.",
    "This sentence has exactly eight words in it.",
    "Use the --dry-run flag to preview the change before you apply it.",
    "The value 36L7 is a serial number.",
    "Do not touch the high-voltage terminal.",
    "The API returned 404 for that request.",
    "You must set client.retry.limit before the service starts.",
    "It took 2.5 hrs to finish the upgrade.",
    'The engineer said "this will not work at all" and left.',
    "Remove 15 mm of insulation from each wire end.",
    "The spar box has twenty-one ribs.",
    "Allocate 512 MiB and cap at 80 %.",
    "Restart the HTTP daemon.",
]


@needs_vale
def test_vale_word_count_matches_the_specification_oracle(tmp_path):
    """Vale's count equals `count_words` on every sentence in the corpus.

    THIS IS THE TEST THAT KEEPS THE CONTRACT. `count_words` is no longer the
    runtime path for the sentence-length rules; it is the oracle. If the generated
    alternation drifts, one of these disagrees and names the sentence.

    A `max: 1` rule reports the count for every sentence with two or more words,
    which turns Vale into a word counter rather than a threshold check.
    """
    style = tmp_path / "styles" / "probe"
    style.mkdir(parents=True)
    (style / "Count.yml").write_text(
        "extends: occurrence\n"
        'message: "WORDS=%d"\n'
        "level: error\n"
        "scope: sentence\n"
        "max: 1\n"
        f"token: {json.dumps(STE_WORD_TOKEN)}\n",
        encoding="utf-8",
    )
    config = tmp_path / ".vale.ini"
    config.write_text(
        "StylesPath = styles\nMinAlertLevel = suggestion\n[*.md]\nBasedOnStyles = probe\n",
        encoding="utf-8",
    )

    # One sentence per paragraph, so each is its own Vale scope and its line
    # number identifies it.
    body = "\n\n".join(WORD_COUNT_CORPUS) + "\n"
    alerts = _lint(config, body, tmp_path, name="corpus.md")
    by_line = {a["Line"]: int(a["Message"].split("=")[1]) for a in alerts}

    disagreements = []
    for index, sentence in enumerate(WORD_COUNT_CORPUS):
        expected = count_words(sentence)
        actual = by_line.get(1 + 2 * index)
        if actual != expected:
            disagreements.append(f"{sentence!r}: vale={actual} oracle={expected}")
    assert not disagreements, "Vale's word count drifted from docs/metrics.md:\n" + "\n".join(
        disagreements
    )


@needs_vale
def test_worked_example_counts_ten(tmp_path):
    """The specification's own example, called out because it is the one number a
    reader can check against the source document."""
    style = tmp_path / "styles" / "probe"
    style.mkdir(parents=True)
    (style / "Count.yml").write_text(
        "extends: occurrence\n"
        'message: "WORDS=%d"\n'
        "level: error\nscope: sentence\nmax: 1\n"
        f"token: {json.dumps(STE_WORD_TOKEN)}\n",
        encoding="utf-8",
    )
    config = tmp_path / ".vale.ini"
    config.write_text(
        "StylesPath = styles\nMinAlertLevel = suggestion\n[*.md]\nBasedOnStyles = probe\n",
        encoding="utf-8",
    )
    alerts = _lint(config, "Do steps 13 thru 16 a minimum of three times.\n", tmp_path)
    assert alerts, "the word counter did not fire"
    assert "WORDS=10" in alerts[0]["Message"]


# --- the extension points, each proved by execution ---------------------------


@needs_vale
@pytest.mark.parametrize(
    "rule_id,text",
    [
        # existence / tokens
        ("prose-inflation.slop-lexicon", "We leverage the seamless approach here."),
        # occurrence over the STE word token.
        #
        # `prose-craft.sentence-length` and NOT one of the two STE caps, which used to
        # stand here: those are `text_type`-scoped and are now deliberately native,
        # because Vale cannot tell an instruction from an explanation and applied one
        # type's cap to every sentence. This rule is `text_type: any`, so it exercises
        # the same extension point without asserting behaviour that was a defect. The
        # native path for the STE caps is covered in `test_engine.py`.
        (
            "prose-craft.sentence-length",
            "The service reads the configuration file and then it validates every "
            "single entry before it writes the resulting merged output back to the "
            "destination directory somewhere, and then it reports the outcome to the "
            "caller so that the operator can decide what the next step should be.",
        ),
        # occurrence over a sentence terminator, scope: paragraph
        (
            "ste-descriptive.paragraph-too-many-sentences",
            "One here. Two here. Three here. Four here. Five here. Six here. Seven here.",
        ),
        # occurrence over a clause-join alternation
        (
            "prose-discipline.run-on",
            "We read it, and we parse it, but the writer fails, which breaks it, "
            "however the logs persist, therefore we retry.",
        ),
        # script, scope: raw -- heading hierarchy, which needs cross-block state
        ("ai-tells-formatting.heading-hierarchy", "# One\n\nBody text here.\n\n#### Four\n\nMore body.\n"),
    ],
)
def test_extension_point_fires(compiled, rule_id, text, tmp_path):
    """Each extension point produces the finding on a probe document.

    Parametrized by RULE rather than by extension point, so the assertion is that
    a real shipped rule fires -- not that a synthetic example of the same shape
    would.
    """
    assert rule_id in compiled.vale_rules, f"{rule_id} was not compiled to Vale"
    assert rule_id in _checks(compiled.config_path, text, tmp_path)


@needs_vale
def test_script_rule_is_silent_on_compliant_text(compiled, tmp_path):
    """The negative half of the script fixture.

    A Tengo script that always fires is as broken as one that never does, and only
    a negative fixture separates the two.
    """
    clean = "# One\n\nBody text here.\n\n## Two\n\nMore body text.\n\n### Three\n\nEnd.\n"
    assert "ai-tells-formatting.heading-hierarchy" not in _checks(
        compiled.config_path, clean, tmp_path
    )


@needs_vale
def test_word_count_rule_is_silent_on_a_short_sentence(compiled, tmp_path):
    """A compliant sentence produces no length finding."""
    checks = _checks(compiled.config_path, "Close the valve.\n", tmp_path)
    assert "ste-procedural.sentence-too-long-procedural" not in checks
    assert "ste-descriptive.sentence-too-long-descriptive" not in checks


@needs_vale
def test_every_compiled_lexical_rule_fires_on_its_own_example(compiled, ruleset, tmp_path):
    """The compiler-wide version of the check `rules.py` already runs natively.

    A rule whose example stopped matching after compilation is a rule that reports
    every document clean. Asserted for all of them at once, because the failure is
    silent per rule and only a sweep finds it.
    """
    lexical = (RuleKind.TOKENS, RuleKind.PATTERN, RuleKind.SUBSTITUTION)
    lines: list[str] = []
    expected: dict[int, str] = {}
    for rule in ruleset.rules:
        if rule.kind not in lexical or rule.qualified_id not in compiled.vale_rules:
            continue
        for example in rule.examples[:1]:
            text = " ".join(example.bad.split())
            if not text:
                continue
            # A heading-scoped rule only sees heading text, so the fixture has to
            # be a heading or the rule cannot match its own example.
            if rule.scope.value == "heading":
                text = f"# {text}"
            expected[len(lines) + 1] = rule.qualified_id
            lines.extend([text, ""])

    alerts = _lint(compiled.config_path, "\n".join(lines) + "\n", tmp_path, name="examples.md")
    fired: dict[int, set[str]] = {}
    for alert in alerts:
        fired.setdefault(alert["Line"], set()).add(alert["Check"])

    missing = [
        rule_id for line, rule_id in expected.items() if rule_id not in fired.get(line, set())
    ]
    assert not missing, f"compiled rules that no longer fire on their own example: {missing}"


# --- vocabulary ---------------------------------------------------------------


def test_vocabulary_groups_by_part_of_speech(vocabulary):
    """A handful of rules, not one per entry."""
    rules = vocabulary_sequence_rules(vocabulary)
    assert 0 < len(rules) <= 4
    for payload in rules.values():
        assert payload["extends"] == "sequence"
        token = payload["tokens"][0]
        assert "tag" in token and "|" in token["tag"]


@needs_vale
def test_vocabulary_sequence_rule_respects_the_part_of_speech(vocabulary, tmp_path):
    """The reason the hand-rolled tagger could go.

    A blocklist entry scoped to `verb` must flag `close` as a verb and leave "close
    to the limit" alone. A flat word list cannot tell them apart, which is why the
    part of speech is a required field rather than a refinement.
    """
    style = tmp_path / "styles" / "ste-words"
    style.mkdir(parents=True)
    (style / "vocab.yml").write_text(
        "extends: sequence\n"
        'message: "%s is not approved as a verb"\n'
        "level: warning\nignorecase: true\n"
        "tokens:\n"
        "  - pattern: '(?:close|abort)'\n"
        "    tag: 'VB|VBD|VBG|VBN|VBP|VBZ'\n",
        encoding="utf-8",
    )
    config = tmp_path / ".vale.ini"
    config.write_text(
        "StylesPath = styles\nMinAlertLevel = suggestion\n[*.md]\nBasedOnStyles = ste-words\n",
        encoding="utf-8",
    )

    assert _checks(config, "He closed the socket yesterday.\n", tmp_path)
    assert not _checks(config, "The value is close to the limit.\n", tmp_path)


@needs_vale
def test_generated_vocabulary_rules_load_and_fire(vocabulary, tmp_path):
    """The shipped example blocklist, compiled and executed rather than inspected."""
    rules = vocabulary_sequence_rules(vocabulary)
    style = tmp_path / "styles" / "ste-words"
    style.mkdir(parents=True)
    import yaml

    for name, payload in rules.items():
        (style / f"{name}.yml").write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=10**6),
            encoding="utf-8",
        )
    config = tmp_path / ".vale.ini"
    config.write_text(
        "StylesPath = styles\nMinAlertLevel = suggestion\n[*.md]\nBasedOnStyles = ste-words\n",
        encoding="utf-8",
    )

    verb = next(
        e.word for e in vocabulary.blocked() if e.pos.value == "verb" and e.word.isalpha()
    )
    assert _checks(config, f"He {verb}ed the system yesterday.\n", tmp_path) or _checks(
        config, f"They {verb} the system today.\n", tmp_path
    )


# --- the cache ----------------------------------------------------------------


def test_cache_dir_is_overridable(monkeypatch, tmp_path):
    monkeypatch.setenv("SLOPVAC_CACHE_DIR", str(tmp_path / "custom"))
    assert cache_root() == tmp_path / "custom"


def test_cache_falls_back_to_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("SLOPVAC_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert cache_root() == tmp_path / "xdg" / "slopvac"


def test_second_compile_reuses_the_cache(ruleset, vocabulary, tmp_path):
    """A repeated run must not recompile, and must report the same routing."""
    config = resolve_for(Config(), Path("README.md"))
    first = compile_ruleset(
        ruleset, config, outdir=tmp_path / "c", validate=False, vocabulary=vocabulary, force=True
    )
    marker = first.outdir / "styles" / ".cache-marker"
    marker.write_text("kept", encoding="utf-8")

    second = compile_ruleset(
        ruleset, config, outdir=tmp_path / "c", validate=False, vocabulary=vocabulary
    )
    assert marker.exists(), "the tree was rewritten instead of reused"
    assert second.vale_rules == first.vale_rules
    assert second.native_reasons() == first.native_reasons()


def test_a_reader_never_sees_a_half_built_cache_tree(ruleset, vocabulary, tmp_path):
    """The tree is published by one rename, so it is complete or absent.

    The old compiler cleared `outdir` and then wrote ~200 rule files into it, which
    left a window in which a concurrent run resolved a config naming rules that were
    not on disk yet. Vale rejects such a config (E201) and then lints NOTHING while
    still exiting 0, so every file reads clean and the score silently drops to
    native-rules-only. This asserts the window is closed: at the moment the
    directory exists at all, its ini and every rule the ini names exist too.
    """
    config = resolve_for(Config(), Path("README.md"))
    outdir = tmp_path / "c"
    compile_ruleset(
        ruleset, config, outdir=outdir, validate=False, vocabulary=vocabulary, force=True
    )
    # Recompile over the published tree. Nothing may be missing at any point, so the
    # check runs against the result rather than racing it: a partial publish would
    # leave the ini naming a file the rename never carried over.
    compile_ruleset(
        ruleset, config, outdir=outdir, validate=False, vocabulary=vocabulary, force=True
    )
    # Read the ini by line rather than with configparser: Vale's format opens with
    # header-less global keys, which configparser rejects outright.
    named = re.findall(
        r"^([\w-]+\.[\w-]+)\s*=",
        (outdir / ".vale.ini").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert named, "the generated ini names no rules, so this asserts nothing"
    for rule in named:
        category, name = rule.split(".", 1)
        assert (outdir / "styles" / category / f"{name}.yml").is_file(), (
            f"the ini enables {rule} but the file is absent -- Vale would E201 and "
            f"then lint nothing"
        )


def test_a_failed_compile_leaves_no_cache_entry(ruleset, vocabulary, tmp_path, monkeypatch):
    """A crash mid-write must not leave a directory that reads as cached.

    The manifest is what the fingerprint check looks for, and it is now written
    inside the staging tree, so a run that dies before the rename publishes nothing.
    """
    import slopvac.compile_vale as module

    config = resolve_for(Config(), Path("README.md"))
    outdir = tmp_path / "c"

    def explode(*args, **kwargs):
        raise RuntimeError("killed mid-write")

    monkeypatch.setattr(module.os, "replace", explode)
    with pytest.raises(RuntimeError):
        compile_ruleset(
            ruleset, config, outdir=outdir, validate=False, vocabulary=vocabulary, force=True
        )
    assert not (outdir / "manifest.json").is_file()
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".c.")]
    assert not leftovers or all("building" in n for n in leftovers), leftovers


def test_changing_a_severity_invalidates_the_cache(ruleset, vocabulary, tmp_path):
    """The fingerprint covers the resolved config, not just the rules.

    A cache keyed on rules alone would serve a stale ini after a project lowered a
    severity, so the gate would keep blocking on the old level.
    """
    plain = resolve_for(Config(), Path("README.md"))
    first = compile_ruleset(
        ruleset, plain, outdir=None, validate=True, vocabulary=vocabulary, force=True
    )

    changed = Config()
    changed.categories["prose-inflation"] = CategorySettings(severity=Severity.SUGGESTION)
    second = compile_ruleset(
        ruleset,
        resolve_for(changed, Path("README.md")),
        outdir=None,
        validate=True,
        vocabulary=vocabulary,
    )
    assert first.outdir != second.outdir


def test_an_unvalidated_tree_is_never_cached(ruleset, vocabulary):
    """The cache is shared, so only a probed tree may enter it.

    An unvalidated compile writes every payload, including any Vale refuses to
    load, and one such rule makes Vale lint NOTHING while exiting 0. A cached entry
    like that reports every file clean, which is the failure this project exists to
    prevent, and it persists because the fingerprint check only looks for a
    manifest.
    """
    config = resolve_for(Config(), Path("README.md"))
    with pytest.raises(ValueError, match="unvalidated compile cannot be cached"):
        compile_ruleset(ruleset, config, validate=False, vocabulary=vocabulary)


def test_relaxed_profile_compiles_fewer_rules(ruleset, vocabulary, tmp_path):
    """Tier exclusion reaches Vale, because it reaches the ini."""
    strict = Config()
    object.__setattr__(strict, "profile", Profile.STRICT)
    relaxed = Config()
    object.__setattr__(relaxed, "profile", Profile.RELAXED)

    a = compile_ruleset(
        ruleset,
        resolve_for(strict, Path("README.md")),
        outdir=tmp_path / "s",
        validate=False,
        vocabulary=vocabulary,
        force=True,
    )
    b = compile_ruleset(
        ruleset,
        resolve_for(relaxed, Path("README.md")),
        outdir=tmp_path / "r",
        validate=False,
        vocabulary=vocabulary,
        force=True,
    )
    assert len(b.vale_rules) < len(a.vale_rules)
    assert b.disabled_rules


# --- the substitution fallback ------------------------------------------------


@needs_vale
def test_trailing_punctuation_key_still_fires(compiled, tmp_path):
    """A swap key ending in punctuation needs the `existence` fallback.

    Vale wraps every `substitution` key in `\\b...\\b`, so `e\\.g\\.` can never
    match: there is no word boundary after the final period. Measured -- the rule
    reported nothing as a substitution and fires correctly as an `existence`.
    """
    checks = _checks(
        compiled.config_path, "Discard the temporary files (e.g. lock files).\n", tmp_path
    )
    assert "ste-practices.latin-abbreviation" in checks


@needs_vale
def test_the_fallback_does_not_match_inside_a_word(compiled, tmp_path):
    """Regression: the fallback lost the boundaries `substitution` had supplied.

    A swap key like `e.g.` is a REGEX whose dots match any character, so a bare
    alternation matched "ice" inside "service" and "ile" inside "file". Vale's own
    `\\b` wrapper had been hiding it, so the fallback has to restore the boundary
    itself.
    """
    alerts = _lint(
        compiled.config_path,
        "The service reads the file and writes the merged output to the directory.\n",
        tmp_path,
    )
    latin = [a for a in alerts if a["Check"] == "ste-practices.latin-abbreviation"]
    assert not latin, f"matched inside a word: {[a['Match'] for a in latin]}"


@needs_vale
def test_no_finding_message_has_a_go_format_error(compiled, tmp_path):
    """`%!s(MISSING)` and `%!d(string=...)` are messages nobody can act on.

    Vale supplies a fixed number of arguments per extension point -- one for
    `existence`, two for `substitution`, an integer for `occurrence`, none for
    `script` -- so a template with the wrong verb count renders a Go format error
    into the finding a writer reads.
    """
    sample = (
        "# Testing The Loader\n\n"
        "We leverage a seamless approach in order to fix the blind spot.\n\n"
        "In conclusion, the service reads the configuration file and then it "
        "validates every single entry before it writes the resulting merged output "
        "back to the destination directory.\n\n"
        "#### Skipped Heading\n\n"
        "He closed the socket. It's not a linter, it's a review partner.\n\n"
        "Discard the temporary files (e.g. lock files and partial downloads).\n"
    )
    bad = [a for a in _lint(compiled.config_path, sample, tmp_path) if "%!" in a["Message"]]
    assert not bad, "format errors in: " + ", ".join(
        f"{a['Check']}: {a['Message']}" for a in bad
    )


@needs_vale
def test_only_one_rule_owns_the_vocabulary_sweep(compiled, tmp_path):
    """Several vocabulary rules over one wordlist reported every word several times.

    They cite different STE clauses, but a `(word, part-of-speech)` blocklist
    answers one question, so one rule owns the sweep and the rest are reported as
    native with the reason.
    """
    owners = {compiled.aliases[check] for check in compiled.aliases}
    assert len(owners) == 1, f"more than one vocabulary rule compiled: {owners}"

    alerts = _lint(compiled.config_path, "We leverage the seamless approach.\n", tmp_path)
    per_word: dict[tuple[int, str], list[str]] = {}
    for alert in alerts:
        if alert["Check"] in compiled.aliases:
            per_word.setdefault((alert["Line"], alert["Match"]), []).append(alert["Check"])
    for key, checks in per_word.items():
        assert len(checks) == 1, f"{key} reported by {checks}"
