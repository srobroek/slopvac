//! Every `Error` maps to one stable code of the message registry.

use slopvac_context::{Error, MAX_PATTERN_BYTES};

#[test]
fn a_tagger_pattern_over_the_cap_has_its_own_code_and_unchanged_text() {
    let error = Error::PatternTooLong {
        len: 9000,
        max: MAX_PATTERN_BYTES,
    };
    assert_eq!(error.code(), "tagger-pattern-too-long");
    assert_eq!(
        error.to_string(),
        "pattern is 9000 bytes, over the 8192-byte limit"
    );
}
