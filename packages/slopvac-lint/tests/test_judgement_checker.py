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
