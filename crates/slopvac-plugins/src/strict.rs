//! Strict JSON parsing for plugin messages.
//!
//! Rejects what plugin-protocol.md section 2.2 calls invalid in v1: duplicate
//! object keys, nesting deeper than 64 and integers outside ±(2^53-1).
//! Whether a number must be an integer is left to the typed layer: `serde`
//! refuses `1.0` and `1e2` for an integer field.

use std::collections::HashSet;
use std::fmt;

use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Number, Value};

use crate::messages::trust::{self as messages, StrictPhrase};

/// Largest integer that every JSON reader keeps exact.
pub const MAX_SAFE_INTEGER: u64 = (1 << 53) - 1;
/// Deepest container nesting a reader accepts.
pub const MAX_DEPTH: usize = 64;

/// Parse `bytes` as one strict JSON value.
///
/// # Errors
/// Returns the reason as text when the body is not valid JSON or breaks a v1 rule.
pub fn parse(bytes: &[u8]) -> Result<Value, String> {
    let mut de = serde_json::Deserializer::from_slice(bytes);
    let value = Strict { depth: 0 }
        .deserialize(&mut de)
        .map_err(|e| e.to_string())?;
    de.end().map_err(|e| e.to_string())?;
    check_integer_literals(bytes)?;
    Ok(value)
}

/// Reject integer literals outside ±(2^53-1) by their text.
///
/// `serde_json` turns an integer past the 64-bit range into a rounded `f64`,
/// so the visitor cannot tell it from a float. The scan runs on text that
/// already parsed, so every token is well formed.
fn check_integer_literals(bytes: &[u8]) -> Result<(), String> {
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'"' => {
                i += 1;
                while i < bytes.len() && bytes[i] != b'"' {
                    i += if bytes[i] == b'\\' { 2 } else { 1 };
                }
                i += 1;
            }
            b'-' | b'0'..=b'9' => {
                let start = i;
                while i < bytes.len()
                    && matches!(bytes[i], b'0'..=b'9' | b'-' | b'+' | b'.' | b'e' | b'E')
                {
                    i += 1;
                }
                let token = &bytes[start..i];
                if token.iter().any(|b| matches!(b, b'.' | b'e' | b'E')) {
                    continue;
                }
                let digits = token.strip_prefix(b"-").unwrap_or(token);
                let safe = digits.len() <= 16
                    && std::str::from_utf8(digits)
                        .ok()
                        .and_then(|d| d.parse::<u64>().ok())
                        .is_some_and(|v| v <= MAX_SAFE_INTEGER);
                if !safe {
                    let text = String::from_utf8_lossy(token);
                    return Err(messages::strict_integer_range(&text));
                }
            }
            _ => i += 1,
        }
    }
    Ok(())
}

struct Strict {
    depth: usize,
}

impl<'de> DeserializeSeed<'de> for Strict {
    type Value = Value;

    fn deserialize<D: de::Deserializer<'de>>(self, d: D) -> Result<Value, D::Error> {
        d.deserialize_any(StrictVisitor { depth: self.depth })
    }
}

struct StrictVisitor {
    depth: usize,
}

impl StrictVisitor {
    fn enter<E: de::Error>(&self) -> Result<usize, E> {
        let depth = self.depth + 1;
        if depth > MAX_DEPTH {
            return Err(E::custom(messages::strict_nesting(MAX_DEPTH)));
        }
        Ok(depth)
    }
}

impl<'de> Visitor<'de> for StrictVisitor {
    type Value = Value;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(StrictPhrase::Expecting.as_static())
    }

    fn visit_bool<E>(self, v: bool) -> Result<Value, E> {
        Ok(Value::Bool(v))
    }

    fn visit_i64<E: de::Error>(self, v: i64) -> Result<Value, E> {
        if v.unsigned_abs() > MAX_SAFE_INTEGER {
            return Err(E::custom(messages::strict_integer_range(&v.to_string())));
        }
        Ok(Value::Number(v.into()))
    }

    fn visit_u64<E: de::Error>(self, v: u64) -> Result<Value, E> {
        if v > MAX_SAFE_INTEGER {
            return Err(E::custom(messages::strict_integer_range(&v.to_string())));
        }
        Ok(Value::Number(v.into()))
    }

    fn visit_f64<E: de::Error>(self, v: f64) -> Result<Value, E> {
        Number::from_f64(v)
            .map(Value::Number)
            .ok_or_else(|| E::custom(StrictPhrase::NonFinite.as_static()))
    }

    fn visit_str<E>(self, v: &str) -> Result<Value, E> {
        Ok(Value::String(v.to_owned()))
    }

    fn visit_string<E>(self, v: String) -> Result<Value, E> {
        Ok(Value::String(v))
    }

    fn visit_unit<E>(self) -> Result<Value, E> {
        Ok(Value::Null)
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Value, A::Error> {
        let depth = self.enter()?;
        let mut items = Vec::new();
        while let Some(item) = seq.next_element_seed(Strict { depth })? {
            items.push(item);
        }
        Ok(Value::Array(items))
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Value, A::Error> {
        let depth = self.enter()?;
        let mut seen = HashSet::new();
        let mut out = Map::new();
        while let Some(key) = map.next_key::<String>()? {
            if !seen.insert(key.clone()) {
                return Err(de::Error::custom(messages::strict_duplicate_key(&key)));
            }
            out.insert(key, map.next_value_seed(Strict { depth })?);
        }
        Ok(Value::Object(out))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_plain_object() {
        let v = parse(br#"{"a":[1,2.5,"x",null,true]}"#).unwrap();
        assert_eq!(v["a"][0], 1);
        assert_eq!(v["a"][1], 2.5);
    }

    #[test]
    fn rejects_duplicate_keys_at_any_depth() {
        assert!(
            parse(br#"{"a":1,"a":2}"#)
                .unwrap_err()
                .contains("duplicate")
        );
        assert!(
            parse(br#"{"x":{"a":1,"a":1}}"#)
                .unwrap_err()
                .contains("duplicate")
        );
    }

    #[test]
    fn depth_64_passes_and_65_fails() {
        let ok = format!("{}{}", "[".repeat(64), "]".repeat(64));
        let bad = format!("{}{}", "[".repeat(65), "]".repeat(65));
        assert!(parse(ok.as_bytes()).is_ok());
        assert!(parse(bad.as_bytes()).unwrap_err().contains("nesting"));
    }

    #[test]
    fn integer_bounds_are_2_pow_53_minus_1() {
        assert!(parse(b"9007199254740991").is_ok());
        assert!(parse(b"-9007199254740991").is_ok());
        assert!(parse(b"9007199254740992").is_err());
        assert!(parse(b"-9007199254740992").is_err());
    }

    #[test]
    fn integer_literals_past_the_64_bit_range_are_rejected_not_rounded() {
        // Past u64 and i64, serde_json hands these over as a rounded f64.
        for text in [
            "18446744073709551616",
            "-9223372036854775809",
            "100000000000000000000000",
            r#"{"score":[1,-100000000000000000000000]}"#,
        ] {
            let err = parse(text.as_bytes()).unwrap_err();
            assert!(err.contains("outside"), "{text}: {err}");
        }
    }

    #[test]
    fn large_floats_and_digits_inside_strings_are_not_integer_literals() {
        for text in [
            "100000000000000000000000.0",
            "1e300",
            r#""100000000000000000000000""#,
            r#"{"a\"100000000000000000000000":1}"#,
        ] {
            assert!(parse(text.as_bytes()).is_ok(), "{text}");
        }
    }

    #[test]
    fn a_top_level_array_parses_and_is_left_to_the_envelope_check() {
        assert!(parse(b"[]").unwrap().is_array());
    }

    #[test]
    fn fractional_and_exponent_forms_are_not_integers() {
        for text in ["1.0", "1e2", "-1.0", "1E2"] {
            let v = parse(text.as_bytes()).unwrap();
            assert_eq!(v.as_u64(), None, "{text}");
            assert_eq!(v.as_i64(), None, "{text}");
            assert!(serde_json::from_value::<u64>(v).is_err(), "{text}");
        }
    }

    #[test]
    fn rejects_trailing_data_and_bad_json() {
        assert!(parse(b"{} x").is_err());
        assert!(parse(b"{").is_err());
    }
}
