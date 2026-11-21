//! Request and result types for the hooks, with the host-side validation.
//!
//! A plugin result is never trusted: spans, ids, edits and paths are checked
//! here before any other code sees them (plugin-protocol.md sections 5 and 8).

use std::collections::{HashMap, HashSet};
use std::path::{Component, Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{PluginError, RpcError};
use crate::messages::host::{HostPhrase, HostText};

/// Most edits a fixer may return for one document (threat model section 5.5).
pub const MAX_EDITS_PER_DOCUMENT: usize = 1000;
/// Hard ceiling on inserted bytes per document.
pub const MAX_INSERTED_BYTES: usize = 1 << 20;

/// A half-open byte range into a document's text.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Span {
    /// First byte.
    pub start: u64,
    /// One past the last byte.
    pub end: u64,
}

/// Whether `offset` is a valid position in `text` (positions.md, "Valid
/// offsets"): on a code point boundary, outside a leading BOM and not between
/// the CR and LF of one CRLF.
fn offset_is_valid(text: &str, offset: usize) -> bool {
    let bytes = text.as_bytes();
    let inside_bom = text.starts_with('\u{feff}') && (1..3).contains(&offset);
    let inside_crlf =
        offset > 0 && bytes.get(offset - 1) == Some(&b'\r') && bytes.get(offset) == Some(&b'\n');
    text.is_char_boundary(offset) && !inside_bom && !inside_crlf
}

impl Span {
    /// Whether the span lies inside `text` on valid offsets: character
    /// boundaries, outside a leading BOM, not between the CR and LF of a CRLF.
    #[must_use]
    pub fn fits(&self, text: &str) -> bool {
        let (Ok(s), Ok(e)) = (usize::try_from(self.start), usize::try_from(self.end)) else {
            return false;
        };
        s <= e && e <= text.len() && offset_is_valid(text, s) && offset_is_valid(text, e)
    }

    /// Whether `inner` lies inside `self`, endpoints included.
    #[must_use]
    pub fn contains(&self, inner: &Span) -> bool {
        self.start <= inner.start && inner.end <= self.end && inner.start <= inner.end
    }
}

/// One document sent to a hook.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Document {
    /// Id unique inside the request.
    pub id: String,
    /// UTF-8 text.
    pub text: String,
    /// Media type, when known.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub media_type: Option<String>,
    /// Relative path. Sent only when `document-path` is granted.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
}

/// A finding sent to a fixer or scorer.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Finding {
    /// Qualified rule id.
    pub rule: String,
    /// `error`, `warning` or `suggestion`.
    pub severity: String,
    /// Where the finding sits.
    pub span: Span,
    /// Message text.
    pub message: String,
}

/// A document with the findings a fixer or scorer sees.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FindingsDocument {
    /// The document.
    #[serde(flatten)]
    pub document: Document,
    /// The selected findings.
    pub findings: Vec<Finding>,
}

/// A context tag from a tagger.
#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Tag {
    /// Context tag name.
    pub kind: String,
    /// Where it applies.
    pub span: Span,
    /// 0 to 1.
    pub confidence: f64,
    /// Why the tagger thinks so.
    pub evidence: String,
}

/// A prose segment from an extractor.
#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Segment {
    /// Source span.
    pub span: Span,
    /// Context of the segment.
    pub context: String,
    /// Converted text when it differs from the source.
    #[serde(default, deserialize_with = "present_string")]
    pub text: Option<String>,
}

/// An optional string field: absent is `None`, but a present `null` is an error.
fn present_string<'de, D: serde::Deserializer<'de>>(d: D) -> Result<Option<String>, D::Error> {
    String::deserialize(d).map(Some)
}

/// An edit from a fixer.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct FixEdit {
    /// Index into the findings sent for the document.
    pub finding: u64,
    /// Replaced range.
    pub span: Span,
    /// Replacement text.
    pub text: String,
}

/// What a recipe wants done to a file.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RecipeAction {
    /// Create or replace.
    Write,
    /// Merge into an existing file.
    Merge,
    /// Delete.
    Remove,
}

/// One file in a recipe plan.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct RecipeFile {
    /// Path relative to the project root.
    pub path: String,
    /// What to do.
    pub action: RecipeAction,
    /// New content for write and merge.
    #[serde(default, deserialize_with = "present_string")]
    pub content: Option<String>,
}

/// A rendered report.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct Rendered {
    /// The text. Callers sanitise it before a terminal write.
    pub output: String,
    /// Its media type.
    pub media_type: String,
}

/// One provider answer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Completion {
    /// Echoed item id.
    pub item: String,
    /// Model output. Untrusted.
    pub text: String,
    /// Model name the provider reports.
    pub model: String,
}

/// An item sent to a provider.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CompleteItem {
    /// Id unique inside the request.
    pub id: String,
    /// Text to review.
    pub text: String,
    /// Extra instruction.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub instruction: Option<String>,
}

fn invalid(msg: impl Into<String>) -> PluginError {
    PluginError::OutputInvalid(msg.into())
}

/// Whether `s` matches `^[a-z][a-z0-9-]*$`.
#[must_use]
pub fn is_kebab(s: &str) -> bool {
    let mut chars = s.chars();
    chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
}

/// Parse a JSON-RPC error object (also used for per-entry errors).
///
/// # Errors
/// [`PluginError::OutputInvalid`] when a required field is missing or mistyped.
pub fn parse_error_object(v: &Value) -> Result<RpcError, PluginError> {
    let code = v
        .get("code")
        .and_then(Value::as_i64)
        .ok_or_else(|| invalid(HostPhrase::ErrorCodeMissing.as_static()))?;
    let message = v
        .get("message")
        .and_then(Value::as_str)
        .ok_or_else(|| invalid(HostPhrase::ErrorMessageMissing.as_static()))?;
    let slopvac_code = v
        .pointer("/data/slopvac_code")
        .and_then(Value::as_str)
        .filter(|s| is_slopvac_code(s))
        .ok_or_else(|| invalid(HostPhrase::ErrorPluginCode.as_static()))?;
    Ok(RpcError {
        code,
        message: message.to_owned(),
        plugin_code: slopvac_code.to_owned(),
        data: v.get("data").cloned().unwrap_or(Value::Null),
    })
}

fn is_slopvac_code(s: &str) -> bool {
    let mut parts = s.split('-');
    parts.next().is_some_and(|p| {
        p.starts_with(|c: char| c.is_ascii_lowercase())
            && p.chars()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
    }) && parts.all(|p| {
        !p.is_empty()
            && p.chars()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
    })
}

/// Match `results` entries to the sent document ids, by `key`.
///
/// Returns the entries in sent order. A missing, extra or duplicate entry
/// invalidates the whole result.
///
/// # Errors
/// [`PluginError::OutputInvalid`] on any mismatch.
pub fn match_entries<'a>(
    result: &'a Value,
    key: &str,
    sent: &[&str],
) -> Result<Vec<&'a Value>, PluginError> {
    let entries = result
        .get("results")
        .and_then(Value::as_array)
        .ok_or_else(|| invalid(HostPhrase::ResultsMissing.as_static()))?;
    let mut by_id: HashMap<&str, &Value> = HashMap::new();
    for e in entries {
        let id = e.get(key).and_then(Value::as_str).ok_or_else(|| {
            invalid(
                HostText::EntryKeyMissing {
                    key: key.to_owned(),
                }
                .to_string(),
            )
        })?;
        if !sent.contains(&id) {
            return Err(invalid(
                HostText::ResultNotRequested { id: id.to_owned() }.to_string(),
            ));
        }
        if by_id.insert(id, e).is_some() {
            return Err(invalid(
                HostText::ResultDuplicate { id: id.to_owned() }.to_string(),
            ));
        }
    }
    sent.iter()
        .map(|id| {
            by_id.get(id).copied().ok_or_else(|| {
                invalid(
                    HostText::ResultMissing {
                        id: (*id).to_owned(),
                    }
                    .to_string(),
                )
            })
        })
        .collect()
}

fn array_of<'a>(entry: &'a Value, field: &str) -> Result<&'a [Value], PluginError> {
    match entry.get(field) {
        None => Ok(&[]),
        Some(Value::Array(a)) => Ok(a),
        Some(_) => Err(invalid(
            HostText::FieldNotArray {
                field: field.to_owned(),
            }
            .to_string(),
        )),
    }
}

fn from<T: for<'de> Deserialize<'de>>(v: &Value, what: &str) -> Result<T, PluginError> {
    T::deserialize(v).map_err(|e| {
        invalid(
            HostText::ParseFailed {
                what: what.to_owned(),
                error: e.to_string(),
            }
            .to_string(),
        )
    })
}

/// Parse and check the tags of one document entry.
///
/// # Errors
/// [`PluginError::OutputInvalid`] for a bad span, confidence or tag name.
pub fn parse_tags(entry: &Value, text: &str) -> Result<Vec<Tag>, PluginError> {
    array_of(entry, "tags")?
        .iter()
        .map(|v| {
            let tag: Tag = from(v, "tag")?;
            if !is_kebab(&tag.kind) {
                return Err(invalid(
                    HostText::TagKind {
                        kind: tag.kind.clone(),
                    }
                    .to_string(),
                ));
            }
            if !tag.span.fits(text) {
                return Err(invalid(HostPhrase::TagSpan.as_static()));
            }
            if !(0.0..=1.0).contains(&tag.confidence) {
                return Err(invalid(HostPhrase::TagConfidence.as_static()));
            }
            Ok(tag)
        })
        .collect()
}

/// Parse and check the segments of one document entry.
///
/// # Errors
/// [`PluginError::OutputInvalid`] for a bad span or context.
pub fn parse_segments(entry: &Value, text: &str) -> Result<Vec<Segment>, PluginError> {
    array_of(entry, "segments")?
        .iter()
        .map(|v| {
            let seg: Segment = from(v, "segment")?;
            if !is_kebab(&seg.context) {
                return Err(invalid(HostPhrase::SegmentContext.as_static()));
            }
            if !seg.span.fits(text) {
                return Err(invalid(HostPhrase::SegmentSpan.as_static()));
            }
            Ok(seg)
        })
        .collect()
}

/// Parse a score entry. A missing score is `None`.
///
/// # Errors
/// [`PluginError::OutputInvalid`] for a negative or non-finite score.
pub fn parse_score(entry: &Value) -> Result<Option<f64>, PluginError> {
    match entry.get("score") {
        None => Ok(None),
        Some(v) => {
            let s = v
                .as_f64()
                .ok_or_else(|| invalid(HostPhrase::ScoreNotNumber.as_static()))?;
            if s.is_finite() && s >= 0.0 {
                Ok(Some(s))
            } else {
                Err(invalid(HostPhrase::ScoreNegative.as_static()))
            }
        }
    }
}

/// Parse and check the edits of one fixer entry against the sent document.
///
/// Every edit must name a sent finding and lie inside that finding's span,
/// endpoints included. Edits must not overlap; zero-width inserts at one
/// offset do not, and keep array order (the sort is stable). The count and inserted bytes
/// are capped. Any violation rejects every edit of the document.
///
/// # Errors
/// [`PluginError::OutputInvalid`] naming the first violation.
pub fn parse_edits(
    entry: &Value,
    text: &str,
    findings: &[Finding],
) -> Result<Vec<FixEdit>, PluginError> {
    let raw = array_of(entry, "edits")?;
    if raw.len() > MAX_EDITS_PER_DOCUMENT {
        return Err(invalid(
            HostText::EditsExceed {
                count: raw.len(),
                max: MAX_EDITS_PER_DOCUMENT,
            }
            .to_string(),
        ));
    }
    let edits: Vec<FixEdit> = raw
        .iter()
        .map(|v| from(v, "edit"))
        .collect::<Result<_, _>>()?;
    for e in &edits {
        let idx = usize::try_from(e.finding)
            .ok()
            .filter(|&i| i < findings.len());
        let Some(idx) = idx else {
            return Err(invalid(
                HostText::EditMissingFinding { finding: e.finding }.to_string(),
            ));
        };
        if !e.span.fits(text) {
            return Err(invalid(HostPhrase::EditSpan.as_static()));
        }
        if !findings[idx].span.contains(&e.span) {
            return Err(invalid(
                HostText::EditOutsideFinding { index: idx }.to_string(),
            ));
        }
    }
    let mut order: Vec<&FixEdit> = edits.iter().collect();
    order.sort_by_key(|e| (e.span.start, e.span.end));
    for pair in order.windows(2) {
        let (a, b) = (pair[0].span, pair[1].span);
        if a.end > b.start {
            return Err(invalid(HostPhrase::EditsOverlap.as_static()));
        }
    }
    let span_bytes: u64 = findings
        .iter()
        .map(|f| f.span.end.saturating_sub(f.span.start))
        .sum();
    let cap = usize::try_from(span_bytes)
        .unwrap_or(usize::MAX)
        .saturating_mul(4)
        .saturating_add(4096)
        .min(MAX_INSERTED_BYTES);
    let inserted: usize = edits.iter().map(|e| e.text.len()).sum();
    if inserted > cap {
        return Err(invalid(
            HostText::InsertedExceed { inserted, cap }.to_string(),
        ));
    }
    Ok(edits)
}

/// Parse the result of a renderer.
///
/// # Errors
/// [`PluginError::OutputInvalid`] when `output` or `media_type` is missing.
pub fn parse_rendered(result: &Value) -> Result<Rendered, PluginError> {
    from(result, "render result")
}

/// Parse and check the result of a provider against the sent item ids.
///
/// # Errors
/// [`PluginError::OutputInvalid`] for a missing, extra or duplicate item.
pub fn parse_completions(
    result: &Value,
    sent: &[&str],
) -> Result<Vec<Result<Completion, RpcError>>, PluginError> {
    let entries = match_entries(result, "item", sent)?;
    entries
        .into_iter()
        .map(|e| {
            if let Some(err) = e.get("error") {
                return Ok(Err(parse_error_object(err)?));
            }
            let text = e.get("text").and_then(Value::as_str);
            let model = e
                .get("model")
                .and_then(Value::as_str)
                .filter(|m| !m.is_empty());
            let (Some(text), Some(model)) = (text, model) else {
                return Err(invalid(HostPhrase::ProviderEntry.as_static()));
            };
            let item = e.get("item").and_then(Value::as_str).unwrap_or_default();
            Ok(Ok(Completion {
                item: item.to_owned(),
                text: text.to_owned(),
                model: model.to_owned(),
            }))
        })
        .collect()
}

const WINDOWS_RESERVED: [&str; 28] = [
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
    // Superscript digits are device names too (U+00B9, U+00B2, U+00B3).
    "com\u{b9}",
    "com\u{b2}",
    "com\u{b3}",
    "lpt\u{b9}",
    "lpt\u{b2}",
    "lpt\u{b3}",
];

/// Check a recipe path as text: relative, normal segments, no Windows tricks.
///
/// # Errors
/// The reason the path is refused.
pub fn check_relative_path(p: &str) -> Result<(), String> {
    if p.is_empty() {
        return Err(HostPhrase::PathEmpty.as_static().into());
    }
    if p.len() > 1024 {
        return Err(HostPhrase::PathTooLong.as_static().into());
    }
    if p.starts_with('/') || p.contains('\\') {
        return Err(HostPhrase::PathAbsolute.as_static().into());
    }
    if p.chars().any(char::is_control) {
        return Err(HostPhrase::PathControl.as_static().into());
    }
    let bytes = p.as_bytes();
    if bytes.len() >= 2 && bytes[0].is_ascii_alphabetic() && bytes[1] == b':' {
        return Err(HostPhrase::PathDrive.as_static().into());
    }
    if let Some(c) = p
        .chars()
        .find(|c| matches!(c, ':' | '<' | '>' | '"' | '|' | '?' | '*'))
    {
        return Err(HostText::PathReservedChar {
            character: c.to_string(),
        }
        .to_string());
    }
    let segments: Vec<&str> = p.split('/').collect();
    if segments.len() > 32 {
        return Err(HostPhrase::PathSegments.as_static().into());
    }
    for seg in segments {
        if seg.is_empty() || seg == "." || seg == ".." {
            return Err(HostText::SegmentNotNormal {
                segment: seg.to_owned(),
            }
            .to_string());
        }
        if seg.ends_with('.') || seg.ends_with(' ') {
            return Err(HostPhrase::SegmentDotSpace.as_static().into());
        }
        let stem = seg.split('.').next().unwrap_or(seg).to_ascii_lowercase();
        if WINDOWS_RESERVED.contains(&stem.as_str()) {
            return Err(HostText::ReservedName {
                segment: seg.to_owned(),
            }
            .to_string());
        }
    }
    Ok(())
}

/// Parse and check a recipe plan.
///
/// # Errors
/// [`PluginError::OutputInvalid`] for a bad path, action or missing content.
pub fn parse_recipe(result: &Value) -> Result<Vec<RecipeFile>, PluginError> {
    let files = result
        .get("files")
        .and_then(Value::as_array)
        .ok_or_else(|| invalid(HostPhrase::FilesMissing.as_static()))?;
    let mut seen = HashSet::new();
    files
        .iter()
        .map(|v| {
            let f: RecipeFile = from(v, "recipe file")?;
            check_relative_path(&f.path).map_err(|e| {
                invalid(
                    HostText::RecipePath {
                        path: f.path.clone(),
                        reason: e,
                    }
                    .to_string(),
                )
            })?;
            if matches!(f.action, RecipeAction::Write | RecipeAction::Merge) && f.content.is_none()
            {
                return Err(invalid(
                    HostText::RecipeNoContent {
                        path: f.path.clone(),
                    }
                    .to_string(),
                ));
            }
            if !seen.insert(f.path.to_lowercase()) {
                return Err(invalid(
                    HostText::RecipePathTwice {
                        path: f.path.clone(),
                    }
                    .to_string(),
                ));
            }
            Ok(f)
        })
        .collect()
}

/// Resolve a recipe path under `root`, refusing any route that leaves it.
///
/// Every existing component is checked: a symlink must resolve inside the
/// canonical root. This is a check at one moment. Applying the plan needs the
/// no-follow writes described in the threat model (O6).
///
/// # Errors
/// The reason the target is refused.
pub fn resolve_in_root(root: &Path, rel: &str) -> Result<PathBuf, String> {
    check_relative_path(rel)?;
    let root = root.canonicalize().map_err(|e| {
        HostText::ProjectRoot {
            error: e.to_string(),
        }
        .to_string()
    })?;
    let mut cur = root.clone();
    let mut rest = rel.split('/');
    for seg in rest.by_ref() {
        cur.push(seg);
        match std::fs::symlink_metadata(&cur) {
            Ok(m) if m.file_type().is_symlink() => {
                let resolved = cur.canonicalize().map_err(|e| {
                    HostText::Symlink {
                        path: cur.display().to_string(),
                        error: e.to_string(),
                    }
                    .to_string()
                })?;
                if !resolved.starts_with(&root) {
                    return Err(HostText::LeavesRoot {
                        path: rel.to_owned(),
                    }
                    .to_string());
                }
                cur = resolved;
            }
            Ok(_) => {}
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                cur.extend(rest);
                break;
            }
            Err(e) => {
                return Err(HostText::PathError {
                    path: cur.display().to_string(),
                    error: e.to_string(),
                }
                .to_string());
            }
        }
    }
    Ok(cur)
}

/// The path a plugin sees for a document (section 8.1).
///
/// `None` is standard input and gives `<stdin>`. A path under `root` becomes
/// root-relative with `/` separators. Any other path becomes
/// `<external>/<file name>`.
#[must_use]
pub fn plugin_path(root: &Path, path: Option<&Path>) -> String {
    let Some(path) = path else {
        return "<stdin>".to_owned();
    };
    if let Ok(rel) = path.strip_prefix(root) {
        let parts: Vec<String> = rel
            .components()
            .filter_map(|c| match c {
                Component::Normal(s) => Some(s.to_string_lossy().into_owned()),
                _ => None,
            })
            .collect();
        if !parts.is_empty() && !rel.components().any(|c| matches!(c, Component::ParentDir)) {
            return parts.join("/");
        }
    }
    let name = path
        .file_name()
        .map_or_else(|| "file".to_owned(), |n| n.to_string_lossy().into_owned());
    format!("<external>/{name}")
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;

    fn finding(start: u64, end: u64) -> Finding {
        Finding {
            rule: "core:x".into(),
            severity: "warning".into(),
            span: Span { start, end },
            message: "m".into(),
        }
    }

    #[test]
    fn an_explicit_null_is_invalid_where_an_absent_field_is_empty() {
        let f = [finding(0, 2)];
        assert_eq!(parse_tags(&json!({}), "ab").unwrap(), vec![]);
        assert_eq!(parse_segments(&json!({}), "ab").unwrap(), vec![]);
        assert_eq!(parse_edits(&json!({}), "ab", &f).unwrap(), vec![]);
        assert_eq!(parse_score(&json!({})).unwrap(), None);
        let null = |k: &str| json!({ k: null });
        assert!(parse_tags(&null("tags"), "ab").is_err());
        assert!(parse_segments(&null("segments"), "ab").is_err());
        assert!(parse_edits(&null("edits"), "ab", &f).is_err());
        assert!(parse_score(&null("score")).is_err());
    }

    #[test]
    fn an_explicit_null_segment_text_or_recipe_content_is_invalid() {
        let seg = |extra: Value| {
            let mut s = json!({"span": {"start": 0, "end": 2}, "context": "prose"});
            s.as_object_mut()
                .unwrap()
                .extend(extra.as_object().unwrap().clone());
            parse_segments(&json!({ "segments": [s] }), "ab")
        };
        assert_eq!(seg(json!({})).unwrap()[0].text, None);
        assert_eq!(
            seg(json!({"text": "AB"})).unwrap()[0].text.as_deref(),
            Some("AB")
        );
        assert!(seg(json!({"text": null})).is_err());
        let recipe = |file: Value| parse_recipe(&json!({ "files": [file] }));
        assert_eq!(
            recipe(json!({"path": "a", "action": "remove"})).unwrap()[0].content,
            None
        );
        assert!(recipe(json!({"path": "a", "action": "remove", "content": null})).is_err());
    }

    #[test]
    fn spans_must_sit_on_character_boundaries_inside_the_text() {
        let text = "aé"; // bytes: a, 0xC3, 0xA9
        let ok = |s, e| Span { start: s, end: e }.fits(text);
        assert!(ok(0, 3));
        assert!(ok(1, 3));
        assert!(ok(3, 3));
        assert!(!ok(0, 4));
        assert!(!ok(2, 3), "inside the two-byte character");
        assert!(!ok(3, 1), "reversed");
    }

    #[test]
    fn tags_with_bad_spans_or_confidence_are_invalid() {
        let good = json!({"tags": [{"kind":"code-fence","span":{"start":0,"end":2},"confidence":1,"evidence":"e"}]});
        assert_eq!(parse_tags(&good, "ab").unwrap().len(), 1);
        for bad in [
            json!({"tags": [{"kind":"code-fence","span":{"start":0,"end":9},"confidence":1,"evidence":"e"}]}),
            json!({"tags": [{"kind":"code-fence","span":{"start":0,"end":1},"confidence":1.5,"evidence":"e"}]}),
            json!({"tags": [{"kind":"Code","span":{"start":0,"end":1},"confidence":1,"evidence":"e"}]}),
            json!({"tags": [{"kind":"code-fence","span":{"start":-1,"end":1},"confidence":1,"evidence":"e"}]}),
            json!({"tags": [{"kind":"code-fence","span":{"start":0,"end":1},"confidence":1}]}),
        ] {
            assert_eq!(
                parse_tags(&bad, "ab").unwrap_err().slopvac_code(),
                "plugin-output-invalid"
            );
        }
    }

    #[test]
    fn unknown_and_extension_fields_are_ignored() {
        let v = json!({"tags": [{"kind":"code-fence","span":{"start":0,"end":1,"x-a":1},"confidence":0.5,"evidence":"e","x-b":{}, "new":1}], "extra": 1});
        assert_eq!(parse_tags(&v, "ab").unwrap().len(), 1);
    }

    #[test]
    fn entries_must_match_the_sent_ids_exactly() {
        let sent = ["a", "b"];
        let ok = json!({"results": [{"document":"b"},{"document":"a"}]});
        assert_eq!(match_entries(&ok, "document", &sent).unwrap().len(), 2);
        for bad in [
            json!({"results": [{"document":"a"}]}),
            json!({"results": [{"document":"a"},{"document":"b"},{"document":"c"}]}),
            json!({"results": [{"document":"a"},{"document":"a"},{"document":"b"}]}),
            json!({"results": [{"document":"a"},{"nope":"b"}]}),
            json!({}),
        ] {
            assert!(match_entries(&bad, "document", &sent).is_err(), "{bad}");
        }
    }

    #[test]
    fn edits_inside_the_finding_span_are_accepted_including_endpoints() {
        let text = "0123456789";
        let findings = [finding(2, 6)];
        for (s, e) in [(2, 2), (6, 6), (2, 6), (3, 4)] {
            let v = json!({"edits": [{"finding":0,"span":{"start":s,"end":e},"text":"x"}]});
            assert!(parse_edits(&v, text, &findings).is_ok(), "{s}..{e}");
        }
    }

    #[test]
    fn edits_outside_the_finding_or_naming_nothing_reject_the_document() {
        let text = "0123456789";
        let findings = [finding(2, 6)];
        for (f, s, e) in [
            (0, 1, 1),
            (0, 7, 7),
            (0, 1, 3),
            (0, 0, 10),
            (1, 2, 3),
            (-1i64, 2, 3),
        ] {
            let v = json!({"edits": [{"finding":f,"span":{"start":s,"end":e},"text":"x"}]});
            assert!(parse_edits(&v, text, &findings).is_err(), "{f} {s}..{e}");
        }
    }

    #[test]
    fn overlapping_edits_are_rejected_and_touching_ones_are_not() {
        let text = "0123456789";
        let findings = [finding(0, 10)];
        let edit = |s: u64, e: u64| json!({"finding":0,"span":{"start":s,"end":e},"text":"x"});
        let ok = json!({"edits": [edit(0, 3), edit(3, 5), edit(5, 5)]});
        assert!(parse_edits(&ok, text, &findings).is_ok());
        for bad in [
            json!({"edits": [edit(0, 4), edit(3, 5)]}),
            json!({"edits": [edit(0, 4), edit(2, 2)]}),
        ] {
            assert!(parse_edits(&bad, text, &findings).is_err(), "{bad}");
        }
    }

    #[test]
    fn edit_count_and_inserted_bytes_are_capped() {
        let text = "x".repeat(10);
        let findings = [finding(0, 10)];
        let one = |t: &str, s: u64| json!({"finding":0,"span":{"start":s,"end":s},"text":t});
        // 4 * 10 + 4096 = 4136 byte cap.
        assert!(
            parse_edits(
                &json!({"edits":[one(&"y".repeat(4136), 0)]}),
                &text,
                &findings
            )
            .is_ok()
        );
        assert!(
            parse_edits(
                &json!({"edits":[one(&"y".repeat(4137), 0)]}),
                &text,
                &findings
            )
            .is_err()
        );
        let many: Vec<Value> = (0..1001).map(|_| one("", 0)).collect();
        let err = parse_edits(&json!({ "edits": many }), &text, &findings).unwrap_err();
        assert!(err.to_string().contains("1001"), "{err}");
    }

    #[test]
    fn provider_entries_must_match_and_carry_text_and_model() {
        let sent = ["i1", "i2"];
        let ok = json!({"results":[
            {"item":"i1","text":"t","model":"m"},
            {"item":"i2","error":{"code":-32007,"message":"off","data":{"slopvac_code":"offline"}}}]});
        let out = parse_completions(&ok, &sent).unwrap();
        assert!(out[0].is_ok() && out[1].is_err());
        for bad in [
            json!({"results":[{"item":"i1","text":"t","model":"m"}]}),
            json!({"results":[{"item":"i1","text":"t","model":"m"},{"item":"i2","text":"t","model":"m"},{"item":"i3","text":"t","model":"m"}]}),
            json!({"results":[{"item":"i1","text":"t","model":"m"},{"item":"i1","text":"t","model":"m"},{"item":"i2","text":"t","model":"m"}]}),
            json!({"results":[{"item":"i1","text":"t"},{"item":"i2","text":"t","model":"m"}]}),
        ] {
            assert!(parse_completions(&bad, &sent).is_err(), "{bad}");
        }
    }

    #[test]
    fn recipe_paths_that_escape_or_hide_are_refused() {
        for bad in [
            "/etc/passwd",
            "../x",
            "a/../x",
            "C:/x",
            "c:x",
            "a\\b",
            "",
            "a//b",
            "./a",
            "a/.",
            "con",
            "dir/NUL.txt",
            "trail.",
            "sp ace ",
            "nul\0",
            "a:b",
            "file.txt:stream",
            "dir/a:$DATA",
            "a<b",
            "a>b",
            "a\"b",
            "a|b",
            "a?b",
            "a*b",
            "com\u{b9}",
            "COM\u{b2}",
            "dir/com\u{b3}.txt",
            "LPT\u{b9}",
            "lpt\u{b2}.log",
            "Lpt\u{b3}",
        ] {
            assert!(check_relative_path(bad).is_err(), "{bad:?}");
            let plan = json!({"files": [{"path": bad, "action": "remove"}]});
            let err = parse_recipe(&plan).unwrap_err();
            assert!(
                matches!(err, PluginError::OutputInvalid(_)),
                "{bad:?}: {err}"
            );
        }
        for good in ["AGENTS.md", ".claude/settings.json", "a/b/c.txt"] {
            assert!(check_relative_path(good).is_ok(), "{good}");
        }
    }

    #[test]
    fn recipe_needs_content_for_write_and_a_known_action() {
        assert!(parse_recipe(&json!({"files":[{"path":"a","action":"write","content":"x"},{"path":"b","action":"remove"}]})).is_ok());
        assert!(parse_recipe(&json!({"files":[{"path":"a","action":"write"}]})).is_err());
        assert!(parse_recipe(&json!({"files":[{"path":"a","action":"chmod"}]})).is_err());
        assert!(
            parse_recipe(
                &json!({"files":[{"path":"a","action":"remove"},{"path":"A","action":"remove"}]})
            )
            .is_err()
        );
    }

    #[test]
    fn plugin_path_forms() {
        let root = Path::new("/proj");
        assert_eq!(plugin_path(root, None), "<stdin>");
        assert_eq!(
            plugin_path(root, Some(Path::new("/proj/docs/a.md"))),
            "docs/a.md"
        );
        assert_eq!(
            plugin_path(root, Some(Path::new("/home/me/x/b.md"))),
            "<external>/b.md"
        );
        assert_eq!(
            plugin_path(root, Some(Path::new("/proj"))),
            "<external>/proj"
        );
    }

    #[cfg(unix)]
    #[test]
    fn symlink_leaving_the_root_is_refused() {
        let base = std::env::temp_dir().join(format!("slopvac-resolve-{}", std::process::id()));
        let root = base.join("root");
        let outside = base.join("outside");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::create_dir_all(&outside).unwrap();
        std::os::unix::fs::symlink(&outside, root.join("link")).unwrap();
        std::fs::create_dir_all(root.join("real")).unwrap();
        std::os::unix::fs::symlink(root.join("real"), root.join("inner")).unwrap();
        let refused = resolve_in_root(&root, "link/file.txt");
        let inside = resolve_in_root(&root, "inner/file.txt");
        let new_path = resolve_in_root(&root, "new/dir/file.txt");
        std::fs::remove_dir_all(&base).unwrap();
        assert!(refused.unwrap_err().contains("leaves the project root"));
        assert!(inside.unwrap().ends_with("real/file.txt"));
        assert!(new_path.is_ok());
    }
}
