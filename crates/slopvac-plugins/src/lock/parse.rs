use semver::Version;
use toml::{Table, Value};

use crate::messages::sync::{self as messages, SyncPhrase};

use super::model::{
    Digest, KeyId, LockError, LockedPack, Lockfile, MAX_LOCK_BYTES, NotBefore, PackId, PackKind,
    Signature, Source, ValueError,
};

fn err(pointer: &str, message: impl AsRef<str>) -> LockError {
    LockError::new(pointer, message)
}

/// A TOML table with its JSON Pointer, read under the unknown-key policy.
struct Obj<'a> {
    table: &'a Table,
    pointer: String,
}

impl<'a> Obj<'a> {
    fn new(table: &'a Table, pointer: String, allowed: &[&str]) -> Result<Self, LockError> {
        if let Some(key) = table
            .keys()
            .find(|k| !k.starts_with("x-") && !allowed.contains(&k.as_str()))
        {
            return Err(err(&pointer, messages::unknown_key(key)));
        }
        Ok(Self { table, pointer })
    }

    fn at(&self, key: &str) -> String {
        format!("{}/{key}", self.pointer)
    }

    fn required(&self, key: &str) -> Result<&'a Value, LockError> {
        self.table
            .get(key)
            .ok_or_else(|| err(&self.pointer, messages::missing_key(key)))
    }

    fn string(&self, key: &str) -> Result<&'a str, LockError> {
        self.required(key)?
            .as_str()
            .ok_or_else(|| err(&self.at(key), SyncPhrase::MustBeString.as_static()))
    }

    fn parsed<T: std::str::FromStr<Err = ValueError>>(&self, key: &str) -> Result<T, LockError> {
        self.string(key)?
            .parse()
            .map_err(|e: ValueError| err(&self.at(key), e.raw()))
    }
}

/// The only `schema_version` of a packs lockfile this crate reads and writes.
pub const LOCK_SCHEMA_VERSION: i64 = 3;

pub(super) fn parse(text: &str) -> Result<Lockfile, LockError> {
    if text.len() > MAX_LOCK_BYTES {
        return Err(err("", messages::lock_too_large(MAX_LOCK_BYTES)));
    }
    let table: Table = toml::from_str(text).map_err(|e| {
        err(
            "",
            messages::toml_invalid(e.span().map(|s| s.start), e.message()),
        )
    })?;
    let root = Obj::new(&table, String::new(), &["schema_version", "plugins"])?;
    match root.required("schema_version")? {
        Value::Integer(LOCK_SCHEMA_VERSION) => {}
        _ => {
            return Err(err(
                "/schema_version",
                SyncPhrase::SchemaVersion.as_static(),
            ));
        }
    }
    let items = root
        .required("plugins")?
        .as_array()
        .ok_or_else(|| err("/plugins", SyncPhrase::PluginsArray.as_static()))?;
    let packs = items
        .iter()
        .enumerate()
        .map(|(i, item)| {
            let pointer = format!("/plugins/{i}");
            let table = item
                .as_table()
                .ok_or_else(|| err(&pointer, SyncPhrase::MustBeTable.as_static()))?;
            pack(table, pointer)
        })
        .collect::<Result<Vec<_>, _>>()?;
    Lockfile::new(packs)
}

fn pack(table: &Table, pointer: String) -> Result<LockedPack, LockError> {
    let obj = Obj::new(
        table,
        pointer,
        &[
            "id",
            "kind",
            "version",
            "slopvac_api",
            "source",
            "digest",
            "signature",
            "requires",
        ],
    )?;
    // Report a missing required key before inspecting any value.
    for key in ["id", "kind", "version", "slopvac_api", "source", "digest"] {
        obj.required(key)?;
    }
    let version_text = obj.string("version")?;
    let version = Version::parse(version_text)
        .map_err(|_| err(&obj.at("version"), messages::version_invalid(version_text)))?;
    let slopvac_api = obj
        .required("slopvac_api")?
        .as_integer()
        .and_then(|n| u64::try_from(n).ok())
        .filter(|&n| n >= 1)
        .ok_or_else(|| err(&obj.at("slopvac_api"), SyncPhrase::ApiInteger.as_static()))?;
    Ok(LockedPack {
        id: obj.parsed::<PackId>("id")?,
        kind: obj.parsed::<PackKind>("kind")?,
        version,
        slopvac_api,
        source: obj.parsed::<Source>("source")?,
        digest: obj.parsed::<Digest>("digest")?,
        signature: obj
            .table
            .get("signature")
            .map(|v| signature(v, obj.at("signature")))
            .transpose()?,
        requires: requires(&obj)?,
    })
}

fn signature(value: &Value, pointer: String) -> Result<Signature, LockError> {
    let table = value
        .as_table()
        .ok_or_else(|| err(&pointer, SyncPhrase::MustBeTable.as_static()))?;
    let obj = Obj::new(table, pointer, &["key_id", "not_before"])?;
    for key in ["key_id", "not_before"] {
        obj.required(key)?;
    }
    Ok(Signature {
        key_id: obj.parsed::<KeyId>("key_id")?,
        not_before: obj.parsed::<NotBefore>("not_before")?,
    })
}

fn requires(obj: &Obj<'_>) -> Result<Vec<PackId>, LockError> {
    let Some(value) = obj.table.get("requires") else {
        return Ok(Vec::new());
    };
    let pointer = obj.at("requires");
    let items = value
        .as_array()
        .ok_or_else(|| err(&pointer, SyncPhrase::RequiresArray.as_static()))?;
    items
        .iter()
        .enumerate()
        .map(|(i, item)| {
            let at = format!("{pointer}/{i}");
            item.as_str()
                .ok_or_else(|| err(&at, SyncPhrase::MustBeString.as_static()))?
                .parse()
                .map_err(|e: ValueError| err(&at, e.raw()))
        })
        .collect()
}
