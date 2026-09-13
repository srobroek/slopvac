"""Worked examples for the STE tokenizer and sentence segmenter."""

from __future__ import annotations

import pytest

from slopvac.analyze import classify_text_type, count_words, split_sentences
from slopvac.model import TextType


# Each case is taken from the corresponding worked example in docs/metrics.md.
def test_phase_0_strips_step_and_paragraph_markers() -> None:
    assert count_words("Step 3. Restart the worker.") == 3
    assert count_words("(1) Restart the worker.") == 3
    assert count_words("4.2.1. Restart the worker.") == 3
    assert count_words("A. Restart the worker.") == 3
    assert count_words("iv. Restart the worker.") == 3


def test_phase_1_collapses_code_identifiers_paths_urls_and_flags() -> None:
    assert count_words("Use `client.retry.limit` now.") == 3
    assert count_words("Open https://example.com/a/b now.") == 3
    assert count_words("Set --dry-run now.") == 3
    assert count_words("Use v1beta1.Deployment now.") == 3


def test_phase_2_collapses_quotes_without_pairing_contractions() -> None:
    assert count_words(
        'Set the timeout to 30 s for the HTTP client in the "edge gateway" service.'
    ) == 13
    assert count_words("Don't run the team's failed build now.") == 7


def test_phase_3_quoted_title_is_one_token() -> None:
    assert count_words('See the "Deployment Safety Guide" now.') == 4


def test_phase_4_collapses_proper_names() -> None:
    assert count_words("New York City deploys now.") == 3
    assert count_words("University of New York opens today.") == 3


def test_phase_5_parenthetical_is_one_token() -> None:
    assert count_words("Run the job (but not on Friday) now.") == 5


def test_phase_6_collapses_numbers_and_units() -> None:
    assert count_words("The temperature in the room is 10 degC.") == 7
    assert count_words("Allocate 512 MiB and cap at 80 %.") == 6
    assert count_words("Wait at 10 degrees Celsius.") == 3
    assert count_words("Do steps 13 thru 16 a minimum of three times.") == 10


def test_phase_7_collapses_abbreviations() -> None:
    assert count_words("Restart the HTTP daemon.") == 4
    assert count_words("No. 1 is ready.") == 3
    assert count_words("Use e.g. this value.") == 4


def test_phase_8_hyphenated_group_is_one_token() -> None:
    assert count_words("Use the in-flight entertainment system.") == 5
    assert count_words("Open the main-gear-door retraction-winch handle.") == 5


def test_phase_9_counts_remaining_tokens_and_ignores_punctuation() -> None:
    assert count_words("Read, check; and save:") == 4


def test_colon_only_splits_a_vertical_list() -> None:
    ordinary = split_sentences("The value is set: then the parser reads it.", 1)
    vertical = split_sentences("Set these values:\n- one\n- two", 1)
    assert [sentence.text for sentence in ordinary] == [
        "The value is set: then the parser reads it."
    ]
    assert [sentence.text for sentence in vertical] == [
        "Set these values:",
        "- one",
        "- two",
    ]


def test_parenthetical_and_non_terminal_periods_do_not_split() -> None:
    parenthetical = split_sentences(
        "A sentence (with another sentence. And more words inside). End.", 1
    )
    abbreviations = split_sentences(
        "Use e.g. this value. Version v1.2.3 works. Done.", 1
    )
    assert [sentence.text for sentence in parenthetical] == [
        "A sentence (with another sentence. And more words inside).",
        "End.",
    ]
    assert [sentence.text for sentence in abbreviations] == [
        "Use e.g. this value.",
        "Version v1.2.3 works.",
        "Done.",
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        "Make sure you have the required access.",
        "Check the current certificate's expiration date.",
        "Record the notAfter date.",
        "Confirm the secret version.",
        "Identify the expiring certificate's name and namespace.",
        "Verify you have the new certificate and key files.",
        "Backup the existing TLS secret.",
        "Ensure a low-traffic window.",
        "Notify stakeholders of the rotation window.",
        "Step 1: Check replication lag.",
        "Fence the old primary.",
        "Promote the replica.",
        "Update the pooler to point at the host.",
        "Reload the ingress process.",
        "Save this file safely.",
        "Monitor the rollout.",
        "Wait for all pods to stabilize.",
        "To rotate the certificate, drain one node.",
        "Remember to update the incident channel.",
        "You should always verify the signature before processing a delivery.",
    ],
)
def test_runbook_imperatives_are_procedural(sentence: str) -> None:
    assert classify_text_type(sentence) is TextType.PROCEDURAL


@pytest.mark.parametrize(
    "sentence",
    [
        "The runbook walks you through the process.",
        "It is a critical procedure that should be approached with care.",
        "Generally speaking, a lag of under a few seconds is acceptable.",
        "A lag of under a few seconds is considered acceptable.",
        "The ingress reads its certificate from the secret.",
        "Reloading an ingress node drops open connections.",
        "The process stages the new certificate on two nodes.",
        "The certificate and key match.",
        "The old primary can no longer be reattached.",
        "These nodes carry roughly a third of the traffic.",
        "Verification fails on the staged nodes.",
        "All nodes should show the new expiry date.",
        "The expected result is shown below.",
        "Before starting, check the expiry.",
        "If verification fails, proceed to rollback.",
        "Because the node is drained, connections are moved.",
        "The certificate is valid for the host.",
        "During staging, traffic remains available.",
        "NOTE: The import reads the cache at startup.",
        "Step 3 is the final verification.",
    ],
)
def test_runbook_descriptions_are_descriptive(sentence: str) -> None:
    assert classify_text_type(sentence) is TextType.DESCRIPTIVE


def test_labelled_runbook_set_reaches_ninety_percent_agreement() -> None:
    labelled = [
        ("Rotate the certificate.", TextType.PROCEDURAL),
        ("The certificate is valid.", TextType.DESCRIPTIVE),
    ]
    agreement = sum(classify_text_type(text) is expected for text, expected in labelled)
    assert agreement / len(labelled) >= 0.90
