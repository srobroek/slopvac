"""The word blocklist: off by default, and loud when it is misconfigured.

THE DEFAULT IS THE MOST IMPORTANT ASSERTION HERE. This package shipped an
extracted ASD-STE100 dictionary and enforced it as an ALLOWLIST, so every word
outside 859 approved ones drew a finding: 51% of all findings at `strict` on an
8-document corpus, driving documents with zero errors to a score of 0.0. Half of
those hits were words with no dictionary entry at all, which no override could
reach. `test_no_configured_blocklist_means_no_words_are_refused` is the regression
test for that, and it is the reason there is no packaged wordlist to fall back on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from slopvac.config import Config, load_config
from slopvac.vocabulary import Pos, Vocabulary, VocabularyError, load_blocklist

EXAMPLE_BLOCKLIST = Path(__file__).parent.parent / "examples" / "blocklist.toml"


ENTRY = {"word": "utilize", "pos": "verb", "reason": "Use `use`.", "replacement": "use"}


def _write(path: Path, entries: list[dict]) -> Path:
    """Write `entries` in whichever format `path`'s suffix names."""
    if path.suffix == ".toml":
        lines = []
        for entry in entries:
            lines.append("[[entries]]")
            lines += [f"{k} = {json.dumps(v)}" for k, v in entry.items()]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif path.suffix in {".yml", ".yaml"}:
        path.write_text(yaml.safe_dump({"entries": entries}), encoding="utf-8")
    else:
        path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return path


# --- the default --------------------------------------------------------------


def test_no_configured_blocklist_means_no_words_are_refused():
    """The regression test for the allowlist that produced 828 false findings.

    `load_blocklist(None)` must be empty rather than falling back to a packaged
    wordlist. An empty blocklist refuses nothing, which is the correct default for
    a project that has not stated an editorial position.
    """
    vocabulary = load_blocklist(None)
    assert len(vocabulary) == 0
    assert not vocabulary
    assert vocabulary.blocked() == []
    # Whatever it is asked, the answer is no.
    for word in ("reviewer", "transaction", "threshold", "never", "already", "case"):
        assert not vocabulary.is_blocked(word, Pos.NOUN)
        assert not vocabulary.is_blocked(word, Pos.VERB)


def test_the_default_config_configures_no_blocklist():
    """Off unless asked for, at the config layer as well as the loader."""
    config = Config()
    assert config.vocabulary.path is None
    assert config.blocklist_path() is None


def test_absence_is_never_a_finding(tmp_path):
    """A word not in the blocklist is fine BY DEFINITION.

    This is the semantic reversal. Under the old allowlist a word absent from the
    dictionary was a finding, and there was no way to express "only these words are
    allowed" without that consequence. There is now no query that reports on a word
    the file does not mention.
    """
    vocabulary = load_blocklist(_write(tmp_path / "b.toml", [ENTRY]))
    assert vocabulary.is_blocked("utilize", Pos.VERB)
    assert not vocabulary.is_blocked("subprocessor", Pos.NOUN)
    assert not hasattr(vocabulary, "is_known"), (
        "is_known() answered the allowlist question and must not come back"
    )


def test_the_part_of_speech_is_part_of_the_key(tmp_path):
    """`deploy` is a good verb and a bad noun, and one entry says only the latter."""
    vocabulary = load_blocklist(
        _write(tmp_path / "b.toml", [{"word": "deploy", "pos": "noun", "reason": "verb-as-noun"}])
    )
    assert vocabulary.is_blocked("deploy", Pos.NOUN)
    assert not vocabulary.is_blocked("deploy", Pos.VERB)
    assert vocabulary.blocked_parts_of_speech("deploy") == {Pos.NOUN}


# --- formats ------------------------------------------------------------------


@pytest.mark.parametrize("suffix", [".toml", ".yml", ".yaml", ".json"])
def test_every_documented_format_loads_identically(tmp_path, suffix):
    """One entry, four syntaxes, one result.

    TOML is documented and JSON is accepted because a wordlist exported from
    another tool arrives that way. Refusing it would be gatekeeping over syntax.
    """
    vocabulary = load_blocklist(_write(tmp_path / f"b{suffix}", [ENTRY]))
    entry = vocabulary.lookup("utilize", Pos.VERB)
    assert entry is not None
    assert (entry.word, entry.pos, entry.replacement) == ("utilize", Pos.VERB, "use")
    assert entry.reason == "Use `use`."


def test_an_unrecognized_suffix_is_refused(tmp_path):
    """Suffix dispatch, so a parse error names the format the author intended."""
    path = tmp_path / "blocklist.txt"
    path.write_text("utilize\n", encoding="utf-8")
    with pytest.raises(VocabularyError, match="unrecognized suffix"):
        load_blocklist(path)


def test_word_is_matched_case_insensitively(tmp_path):
    vocabulary = load_blocklist(
        _write(tmp_path / "b.toml", [{"word": "Utilize", "pos": "VERB", "reason": "x"}])
    )
    assert vocabulary.is_blocked("UTILIZE", Pos.VERB)
    assert vocabulary.is_blocked("utilize", Pos.VERB)


# --- the loud failures --------------------------------------------------------
#
# Every one of these RAISES. A blocklist is opt-in, so the project named it: if it
# cannot be loaded, linting on with it silently empty would report every document
# clean, which is indistinguishable from a pass.


def test_a_missing_file_is_an_error_not_an_empty_blocklist(tmp_path):
    with pytest.raises(VocabularyError, match="cannot read"):
        load_blocklist(tmp_path / "does-not-exist.toml")


def test_an_entry_without_a_reason_is_refused(tmp_path):
    """The old dictionary's real defect: 1,275 of 1,282 refusals had no reason.

    Fatal rather than a warning. An undocumented refusal cannot be reviewed or
    argued with, and a warning in CI output is a refusal nobody removes.
    """
    with pytest.raises(VocabularyError, match="no `reason`"):
        load_blocklist(_write(tmp_path / "b.toml", [{"word": "utilize", "pos": "verb"}]))


def test_a_blank_reason_counts_as_no_reason(tmp_path):
    with pytest.raises(VocabularyError, match="no `reason`"):
        load_blocklist(
            _write(tmp_path / "b.toml", [{"word": "utilize", "pos": "verb", "reason": "   "}])
        )


def test_an_unrecognized_part_of_speech_is_refused(tmp_path):
    """Named rather than silently skipped: a typo'd `pos` is a rule that never runs."""
    with pytest.raises(VocabularyError, match="unrecognized `pos`"):
        load_blocklist(
            _write(tmp_path / "b.toml", [{"word": "utilize", "pos": "gerund", "reason": "x"}])
        )


def test_an_entry_without_a_word_is_refused(tmp_path):
    with pytest.raises(VocabularyError, match="no `word`"):
        load_blocklist(_write(tmp_path / "b.toml", [{"pos": "verb", "reason": "x"}]))


def test_malformed_syntax_is_refused(tmp_path):
    path = tmp_path / "b.toml"
    path.write_text("[[entries]\nword = ", encoding="utf-8")
    with pytest.raises(VocabularyError, match="cannot parse"):
        load_blocklist(path)


def test_entries_must_be_a_list(tmp_path):
    path = tmp_path / "b.json"
    path.write_text(json.dumps({"entries": {"word": "utilize"}}), encoding="utf-8")
    with pytest.raises(VocabularyError, match="must be an array"):
        load_blocklist(path)


# --- the config path ----------------------------------------------------------


def test_the_path_resolves_against_the_config_not_the_cwd(tmp_path, monkeypatch):
    """A relative path must mean the same file from any working directory.

    Otherwise a CI run from the repo root and a local run from a subdirectory
    disagree about what the gate is, and only one of them is enforcing it.
    """
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    blocklist = _write(project / "docs" / "words.toml", [ENTRY])
    (project / "slopvac.toml").write_text(
        '[vocabulary]\npath = "docs/words.toml"\n', encoding="utf-8"
    )

    config = load_config(project / "slopvac.toml", root=project)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert config.blocklist_path() == blocklist.resolve()
    assert len(load_blocklist(config.blocklist_path())) == 1


def test_an_absolute_path_is_left_alone(tmp_path):
    blocklist = _write(tmp_path / "words.toml", [ENTRY])
    config = Config.model_validate({"vocabulary": {"path": str(blocklist)}})
    assert config.blocklist_path() == blocklist


# --- the shipped example ------------------------------------------------------


def test_the_shipped_example_loads():
    """The example is documentation, and documentation that does not run rots.

    Asserted here rather than only in the compiler tests so a broken example fails
    without Vale installed.
    """
    vocabulary = load_blocklist(EXAMPLE_BLOCKLIST)
    assert len(vocabulary) >= 10
    for entry in vocabulary.blocked():
        assert entry.reason, f"{entry.word} ({entry.pos.value}) has no reason"
        assert entry.pos is not Pos.UNKNOWN


def test_the_shipped_example_refuses_only_the_part_of_speech_it_names():
    """`deploy` the verb is fine; `deploy` the noun is not. The example must show it."""
    vocabulary = load_blocklist(EXAMPLE_BLOCKLIST)
    assert vocabulary.is_blocked("deploy", Pos.NOUN)
    assert not vocabulary.is_blocked("deploy", Pos.VERB)


def test_a_wrong_top_level_key_is_an_error_not_an_empty_wordlist(tmp_path):
    """`[[words]]` -- the obvious guess -- used to load as zero entries.

    Every vocabulary rule then reported the document clean while announcing
    nothing, which is exactly the outcome `VocabularyError` exists to prevent: the
    project asked for the gate by name, so an empty gate must not be silent.
    """
    path = tmp_path / "blocklist.toml"
    path.write_text(
        '[[words]]\nword = "widget"\npos = "noun"\nreason = "no"\n', encoding="utf-8"
    )
    with pytest.raises(VocabularyError) as excinfo:
        load_blocklist(path)
    # The message names what the file DOES define, so the fix is one edit away.
    assert "entries" in str(excinfo.value)
    assert "words" in str(excinfo.value)


def test_fingerprint_keys_on_content_not_identity(tmp_path):
    """`lint` groups files by this to compile one Vale style per wordlist.

    Two files with the same words must share a compile, and an empty wordlist is
    an empty wordlist however it was reached.
    """
    entry = '[[entries]]\nword = "widget"\npos = "noun"\nreason = "no"\n'
    first = tmp_path / "a.toml"
    second = tmp_path / "b.toml"
    first.write_text(entry, encoding="utf-8")
    second.write_text(f"# a comment changes nothing\n{entry}", encoding="utf-8")

    assert load_blocklist(first).fingerprint() == load_blocklist(second).fingerprint()
    assert load_blocklist(None).fingerprint() == Vocabulary().fingerprint()

    third = tmp_path / "c.toml"
    third.write_text(entry.replace("widget", "gizmo"), encoding="utf-8")
    assert load_blocklist(third).fingerprint() != load_blocklist(first).fingerprint()


def test_an_override_gives_a_subtree_its_own_wordlist(tmp_path):
    """A blocklist is an editorial position, and a vendored subtree does not share it.

    Without a per-path `[vocabulary]` the only choices were one wordlist for the
    whole repository or none, which is why this is overridable and `exclude` is not.
    """
    (tmp_path / "vendor").mkdir()
    (tmp_path / "root.toml").write_text(
        '[[entries]]\nword = "widget"\npos = "noun"\nreason = "root"\n', encoding="utf-8"
    )
    (tmp_path / "vendor" / "list.toml").write_text(
        '[[entries]]\nword = "gizmo"\npos = "noun"\nreason = "vendor"\n',
        encoding="utf-8",
    )
    config_path = tmp_path / "slopvac.toml"
    config_path.write_text(
        '[vocabulary]\npath = "root.toml"\n\n'
        '[[overrides]]\nfiles = ["vendor/**"]\n'
        '[overrides.vocabulary]\npath = "vendor/list.toml"\n',
        encoding="utf-8",
    )

    from slopvac.config import resolve_blocklist_path, resolve_for

    config = load_config(config_path, root=tmp_path)
    outside = resolve_for(config, tmp_path / "doc.md")
    inside = resolve_for(config, tmp_path / "vendor" / "doc.md")

    # Resolved against the CONFIG's directory, not the working directory, so a run
    # from the repo root and a run from a subdirectory agree about the gate.
    assert resolve_blocklist_path(outside.vocabulary, tmp_path) == tmp_path / "root.toml"
    assert (
        resolve_blocklist_path(inside.vocabulary, tmp_path)
        == tmp_path / "vendor" / "list.toml"
    )
    assert load_blocklist(resolve_blocklist_path(inside.vocabulary, tmp_path)).is_blocked(
        "gizmo", Pos.NOUN
    )
    assert not load_blocklist(
        resolve_blocklist_path(outside.vocabulary, tmp_path)
    ).is_blocked("gizmo", Pos.NOUN)
