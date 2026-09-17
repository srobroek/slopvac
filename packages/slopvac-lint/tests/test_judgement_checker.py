from slopvac.judgement.checker import check_rewrite


def check(before, after, **kwargs):
    return check_rewrite(before, after, document_text="A document mentions worker.", rule_id="test", **kwargs)


def test_protected_fact_changes_are_rejected():
    assert not check("It is not safe.", "It is safe.").ok
    assert not check("You MUST stop.", "You should stop.").ok
    assert not check("Use CAUTION.", "Use WARNING.").ok
    assert check("Use CAUTION.", "Use WARNING.", allowed_transitions=[{"class": "modality", "from": "CAUTION", "to": "WARNING"}]).ok


def test_number_normalisation_is_allowed_but_fact_change_is_not():
    assert check("Wait three seconds.", "Wait 3 seconds.").ok
    assert not check("Wait 3 seconds.", "Wait 4 seconds.").ok


def test_plain_digits_percentages_and_large_number_words_are_protected():
    assert not check("The value is 42.", "The value is 43.").ok
    assert not check("Coverage is 12%.", "Coverage is 13%.").ok
    assert check("Wait twenty-one seconds.", "Wait 21 seconds.").ok
    assert not check("Wait one hundred seconds.", "Wait two hundred seconds.").ok
    assert check("Release on 2025/1/2.", "Release on 2025-01-02.").ok


def test_prefix_polarity_requires_a_real_negated_form():
    assert check("The unit is kept.", "The kept value is kept.").ok
    assert not check("An unclear result is reported.", "A clear result is reported.").ok


def test_referent_authorisation_uses_exact_token_boundaries():
    result = check(
        "Start the job.",
        "Start the work.",
        defined_terms=("work",),
        referent_quotes=("workflow",),
    )
    assert not result.ok


def test_configured_single_token_product_names_are_protected():
    assert not check(
        "Use OpenAI.",
        "Use Anthropic.",
        defined_terms=("OpenAI", "Anthropic"),
    ).ok


def test_condition_command_attachment_is_preserved_per_sentence():
    result = check(
        "If ready, run the command. If blocked, wait.",
        "If ready, wait. If blocked, run the command.",
    )
    assert not result.ok
    assert any(v.token_class == "procedure_dependency" for v in result.violations)


def test_trailing_condition_remains_attached_to_command():
    result = check("Run the command if ready.", "Stop the command if ready.")
    assert not result.ok
    assert any(v.token_class == "procedure_dependency" for v in result.violations)

def test_checker_result_retains_attempted_rewrite():
    rewrite = "The value is 43."
    result = check("The value is 42.", rewrite)
    assert result.attempted_rewrite == rewrite
    assert result.rewrite == rewrite
    assert result.violations


def test_referent_quote_is_the_only_authority_for_added_term():
    assert not check("Start the job.", "Start the worker job.", defined_terms=("worker",)).ok
    assert check("Start the job.", "Start the worker job.", referent_quotes=("worker",), defined_terms=("worker",)).ok


def test_ordered_steps_are_preserved():
    result = check("Step 1: prepare. Step 2: run.", "Step 2: run. Step 1: prepare.")
    assert not result.ok
    assert any(v.token_class == "procedure_dependency" for v in result.violations)


def test_unprotected_parenthetical_can_be_removed_and_unicode_punctuation_normalises():
    assert check("Run the task (as usual).", "Run the task.").ok
    assert check("Use — carefully.", "Use - carefully.").ok


def test_code_and_url_occurrences_are_locked():
    assert not check("Run `tool --safe` at https://example.test/a.", "Run `tool --saFe` at https://example.test/a.").ok
    assert not check("Read https://example.test/a.", "Read the page.").ok
