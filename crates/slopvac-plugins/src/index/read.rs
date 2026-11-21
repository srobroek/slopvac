//! The streaming reader. It deserializes straight into [`IndexEntry`] values,
//! so no tree of the document is ever built. It counts entries while it reads
//! and stops at the first bad entry, and it skips `x-` values with
//! [`IgnoredAny`], which allocates nothing (threat model N11, CWE-770).
//!
//! `serde` errors carry no JSON Pointer, so the visitors record an
//! [`IndexError`] in a [`Ctx`] before they return an error. The first one wins.

use std::cell::RefCell;
use std::fmt;

use semver::Version;
use serde::Deserialize;
use serde::de::{self, DeserializeSeed, Deserializer, IgnoredAny, MapAccess, SeqAccess, Visitor};

use super::model::{IndexEntry, IndexError, MAX_ENTRIES, MAX_INDEX_BYTES, PackKind, PublisherKey};
use crate::messages::pyenv::{PyenvPhrase, PyenvText};

/// `RepeatedKey` for `key`.
fn repeated(key: &str) -> String {
    PyenvText::RepeatedKey {
        key: key.to_owned(),
    }
    .to_string()
}

/// `UnknownKey` for `key`.
fn unknown(key: &str) -> String {
    PyenvText::UnknownKey {
        key: key.to_owned(),
    }
    .to_string()
}

/// `MissingKey` for `key`.
fn missing_key(key: &str) -> String {
    PyenvText::MissingKey {
        key: key.to_owned(),
    }
    .to_string()
}

/// `KeyMustBe` for `key` and the type it must have.
fn key_must_be(key: &str, what: &str) -> String {
    PyenvText::KeyMustBe {
        key: key.to_owned(),
        what: what.to_owned(),
    }
    .to_string()
}

#[derive(Default)]
struct Ctx {
    error: RefCell<Option<IndexError>>,
}

impl Ctx {
    /// Records the error (unless one is already there) and returns a serde error.
    fn fail<E: de::Error>(&self, pointer: &str, message: impl AsRef<str>) -> E {
        let error = IndexError::new(pointer, message);
        let shown = error.message.clone();
        self.error.borrow_mut().get_or_insert(error);
        E::custom(shown)
    }

    /// Turns a serde error into a pointed one, unless a visitor already did.
    fn typed<E: de::Error>(&self, error: E, pointer: &str, message: impl AsRef<str>) -> E {
        if self.error.borrow().is_some() {
            error
        } else {
            self.fail(pointer, message)
        }
    }
}

/// Reads the entries of an index document. Checks the size limit first.
pub(super) fn read(bytes: &[u8]) -> Result<Vec<IndexEntry>, IndexError> {
    if bytes.len() > MAX_INDEX_BYTES {
        return Err(IndexError::new(
            "",
            PyenvText::IndexTooBig {
                size: bytes.len(),
                limit: MAX_INDEX_BYTES,
            }
            .to_string(),
        ));
    }
    let ctx = Ctx::default();
    let mut de = serde_json::Deserializer::from_slice(bytes);
    let result = RootSeed { ctx: &ctx }
        .deserialize(&mut de)
        .and_then(|packs| de.end().map(|()| packs));
    result.map_err(|e| {
        let recorded = ctx.error.borrow_mut().take();
        recorded.unwrap_or_else(|| {
            IndexError::new(
                "",
                PyenvText::NotJson {
                    reason: e.to_string(),
                }
                .to_string(),
            )
        })
    })
}

/// A non-negative whole number. JSON Schema calls `2.0` an integer, so the
/// reader does too.
struct Whole(u64);

impl<'de> Deserialize<'de> for Whole {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct V;
        impl Visitor<'_> for V {
            type Value = Whole;

            fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(PyenvPhrase::ExpectWhole.as_static())
            }

            fn visit_u64<E: de::Error>(self, v: u64) -> Result<Whole, E> {
                Ok(Whole(v))
            }

            fn visit_i64<E: de::Error>(self, v: i64) -> Result<Whole, E> {
                u64::try_from(v)
                    .map(Whole)
                    .map_err(|_| E::custom(PyenvPhrase::NegativeNumber.as_static()))
            }

            #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
            fn visit_f64<E: de::Error>(self, v: f64) -> Result<Whole, E> {
                // 2^53 is the largest bound below which every whole f64 is exact.
                if v.fract() == 0.0 && (0.0..=9_007_199_254_740_992.0).contains(&v) {
                    Ok(Whole(v as u64))
                } else {
                    Err(E::custom(PyenvPhrase::NotWholeNumber.as_static()))
                }
            }
        }
        deserializer.deserialize_any(V)
    }
}

struct RootSeed<'a> {
    ctx: &'a Ctx,
}

impl<'de> DeserializeSeed<'de> for RootSeed<'_> {
    type Value = Vec<IndexEntry>;

    fn deserialize<D: Deserializer<'de>>(self, d: D) -> Result<Self::Value, D::Error> {
        d.deserialize_map(self)
    }
}

impl<'de> Visitor<'de> for RootSeed<'_> {
    type Value = Vec<IndexEntry>;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(PyenvPhrase::ExpectIndexDocument.as_static())
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
        let ctx = self.ctx;
        let mut schema_version = false;
        let mut packs = None;
        while let Some(key) = map.next_key::<String>()? {
            match key.as_str() {
                "schema_version" => {
                    if schema_version {
                        return Err(ctx.fail("", repeated("schema_version")));
                    }
                    let n = map.next_value::<Whole>().map_err(|e| {
                        ctx.typed(
                            e,
                            "/schema_version",
                            PyenvPhrase::SchemaVersionMustBe3.as_static(),
                        )
                    })?;
                    if n.0 != 3 {
                        return Err(ctx.fail(
                            "/schema_version",
                            PyenvPhrase::SchemaVersionMustBe3.as_static(),
                        ));
                    }
                    schema_version = true;
                }
                "plugins" => {
                    if packs.is_some() {
                        return Err(ctx.fail("", repeated("plugins")));
                    }
                    packs = Some(map.next_value_seed(PacksSeed { ctx }).map_err(|e| {
                        ctx.typed(e, "/plugins", PyenvPhrase::PluginsMustBeArray.as_static())
                    })?);
                }
                k if k.starts_with("x-") => {
                    map.next_value::<IgnoredAny>()?;
                }
                _ => return Err(ctx.fail("", unknown(&key))),
            }
        }
        if !schema_version {
            return Err(ctx.fail(
                "/schema_version",
                PyenvPhrase::SchemaVersionRequired.as_static(),
            ));
        }
        packs.ok_or_else(|| ctx.fail("/plugins", PyenvPhrase::PluginsRequired.as_static()))
    }
}

struct PacksSeed<'a> {
    ctx: &'a Ctx,
}

impl<'de> DeserializeSeed<'de> for PacksSeed<'_> {
    type Value = Vec<IndexEntry>;

    fn deserialize<D: Deserializer<'de>>(self, d: D) -> Result<Self::Value, D::Error> {
        d.deserialize_seq(self)
    }
}

impl<'de> Visitor<'de> for PacksSeed<'_> {
    type Value = Vec<IndexEntry>;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(PyenvPhrase::ExpectEntries.as_static())
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Self::Value, A::Error> {
        let ctx = self.ctx;
        let mut packs = Vec::new();
        loop {
            if packs.len() == MAX_ENTRIES {
                // One more element, skipped without allocating, proves an excess.
                if seq.next_element::<IgnoredAny>()?.is_some() {
                    return Err(ctx.fail(
                        "/plugins",
                        PyenvText::TooManyIndexEntries { max: MAX_ENTRIES }.to_string(),
                    ));
                }
                break;
            }
            let at = format!("/plugins/{}", packs.len());
            let next = seq
                .next_element_seed(EntrySeed { ctx, at: &at })
                .map_err(|e| ctx.typed(e, &at, PyenvPhrase::EntryMustBeObject.as_static()))?;
            match next {
                Some(entry) => packs.push(entry),
                None => break,
            }
        }
        Ok(packs)
    }
}

fn read_value<'de, A: MapAccess<'de>, T: Deserialize<'de>>(
    ctx: &Ctx,
    map: &mut A,
    slot: &mut Option<T>,
    at: &str,
    key: &str,
    what: &str,
) -> Result<(), A::Error> {
    if slot.is_some() {
        return Err(ctx.fail(at, repeated(key)));
    }
    let value = map
        .next_value::<T>()
        .map_err(|e| ctx.typed(e, &format!("{at}/{key}"), key_must_be(key, what)))?;
    *slot = Some(value);
    Ok(())
}

struct EntrySeed<'a> {
    ctx: &'a Ctx,
    at: &'a str,
}

impl<'de> DeserializeSeed<'de> for EntrySeed<'_> {
    type Value = IndexEntry;

    fn deserialize<D: Deserializer<'de>>(self, d: D) -> Result<Self::Value, D::Error> {
        d.deserialize_map(self)
    }
}

impl<'de> Visitor<'de> for EntrySeed<'_> {
    type Value = IndexEntry;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(PyenvPhrase::ExpectEntry.as_static())
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<IndexEntry, A::Error> {
        let (ctx, at) = (self.ctx, self.at);
        let (mut id, mut namespace, mut name, mut description) = (
            None::<String>,
            None::<String>,
            None::<String>,
            None::<String>,
        );
        let (mut version, mut kind, mut source) = (None::<String>, None::<String>, None::<String>);
        let (mut api, mut publisher_key) = (None::<Whole>, None);
        while let Some(key) = map.next_key::<String>()? {
            let string = PyenvPhrase::AString.as_static();
            match key.as_str() {
                "id" => read_value(ctx, &mut map, &mut id, at, "id", string)?,
                "namespace" => read_value(ctx, &mut map, &mut namespace, at, "namespace", string)?,
                "name" => read_value(ctx, &mut map, &mut name, at, "name", string)?,
                "description" => {
                    read_value(ctx, &mut map, &mut description, at, "description", string)?;
                }
                "version" => read_value(ctx, &mut map, &mut version, at, "version", string)?,
                "kind" => read_value(ctx, &mut map, &mut kind, at, "kind", string)?,
                "source" => read_value(ctx, &mut map, &mut source, at, "source", string)?,
                "slopvac_api" => read_value(
                    ctx,
                    &mut map,
                    &mut api,
                    at,
                    "slopvac_api",
                    PyenvPhrase::APositiveWhole.as_static(),
                )?,
                "publisher_key" => {
                    if publisher_key.is_some() {
                        return Err(ctx.fail(at, repeated("publisher_key")));
                    }
                    let key_at = format!("{at}/publisher_key");
                    publisher_key = Some(
                        map.next_value_seed(KeySeed { ctx, at: &key_at })
                            .map_err(|e| {
                                ctx.typed(
                                    e,
                                    &key_at,
                                    PyenvPhrase::PublisherKeyMustBeObject.as_static(),
                                )
                            })?,
                    );
                }
                k if k.starts_with("x-") => {
                    map.next_value::<IgnoredAny>()?;
                }
                _ => return Err(ctx.fail(at, unknown(&key))),
            }
        }
        let missing = |key: &str| ctx.fail(at, missing_key(key));
        let version_text = version.ok_or_else(|| missing("version"))?;
        let kind_text = kind.ok_or_else(|| missing("kind"))?;
        let entry = IndexEntry {
            id: id.ok_or_else(|| missing("id"))?,
            namespace: namespace.ok_or_else(|| missing("namespace"))?,
            name: name.ok_or_else(|| missing("name"))?,
            description: description.ok_or_else(|| missing("description"))?,
            version: Version::parse(&version_text).map_err(|e| {
                ctx.fail(
                    &format!("{at}/version"),
                    PyenvText::VersionInvalid {
                        version: version_text.clone(),
                        reason: e.to_string(),
                    }
                    .to_string(),
                )
            })?,
            kind: match kind_text.as_str() {
                "data" => PackKind::Data,
                "code" => PackKind::Code,
                other => {
                    return Err(ctx.fail(
                        &format!("{at}/kind"),
                        PyenvText::KindInvalid {
                            kind: other.to_owned(),
                        }
                        .to_string(),
                    ));
                }
            },
            slopvac_api: api.ok_or_else(|| missing("slopvac_api"))?.0,
            source: source.ok_or_else(|| missing("source"))?,
            publisher_key: publisher_key.ok_or_else(|| missing("publisher_key"))?,
        };
        Ok(entry)
    }
}

struct KeySeed<'a> {
    ctx: &'a Ctx,
    at: &'a str,
}

impl<'de> DeserializeSeed<'de> for KeySeed<'_> {
    type Value = PublisherKey;

    fn deserialize<D: Deserializer<'de>>(self, d: D) -> Result<Self::Value, D::Error> {
        d.deserialize_map(self)
    }
}

impl<'de> Visitor<'de> for KeySeed<'_> {
    type Value = PublisherKey;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(PyenvPhrase::ExpectPublisherKey.as_static())
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<PublisherKey, A::Error> {
        let (ctx, at) = (self.ctx, self.at);
        let (mut key_id, mut fingerprint) = (None::<String>, None::<String>);
        while let Some(key) = map.next_key::<String>()? {
            match key.as_str() {
                "key_id" => read_value(
                    ctx,
                    &mut map,
                    &mut key_id,
                    at,
                    "key_id",
                    PyenvPhrase::AString.as_static(),
                )?,
                "fingerprint" => {
                    read_value(
                        ctx,
                        &mut map,
                        &mut fingerprint,
                        at,
                        "fingerprint",
                        PyenvPhrase::AString.as_static(),
                    )?;
                }
                k if k.starts_with("x-") => {
                    map.next_value::<IgnoredAny>()?;
                }
                _ => return Err(ctx.fail(at, unknown(&key))),
            }
        }
        let missing = |key: &str| ctx.fail(at, missing_key(key));
        Ok(PublisherKey {
            key_id: key_id.ok_or_else(|| missing("key_id"))?,
            fingerprint: fingerprint.ok_or_else(|| missing("fingerprint"))?,
        })
    }
}
