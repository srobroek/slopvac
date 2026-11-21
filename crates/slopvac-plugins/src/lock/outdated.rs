use std::collections::BTreeMap;

use semver::{Version, VersionReq};

use crate::messages::sync as messages;

use super::model::{LockError, Lockfile, PackId};

/// A locked pack with a newer version available.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutdatedPack {
    /// Pack id.
    pub id: PackId,
    /// The locked version.
    pub locked: Version,
    /// The highest available version above `locked` that the config range
    /// allows. `update` moves to it.
    pub update: Option<Version>,
    /// The highest stable available version above `locked`, in range or not.
    /// When it differs from `update`, a newer release needs a config change.
    pub newest: Option<Version>,
}

/// Parses a config version requirement under the contract grammar
/// (`VersionReq` in `plugin-manifest.schema.json`): comma-separated comparators,
/// each an optional operator (`^ ~ = > >= < <=`) and a version with one to
/// three numeric parts. Wildcards are not part of the grammar.
pub fn parse_version_req(text: &str) -> Result<VersionReq, LockError> {
    let fail = |message: String| LockError::new("", message);
    for comparator in text.split(',') {
        let comparator = comparator.trim();
        let after_op = comparator.trim_start_matches(['^', '~', '=', '>', '<']);
        let op_len = comparator.len() - after_op.len();
        let version = after_op.trim_start();
        let (numbers, pre) = version
            .split_once('-')
            .map_or((version, None), |(n, p)| (n, Some(p)));
        let parts: Vec<&str> = numbers.split('.').collect();
        let numeric = |p: &&str| !p.is_empty() && p.bytes().all(|b| b.is_ascii_digit());
        let pre_ok = pre.is_none_or(|p| {
            !p.is_empty()
                && p.bytes()
                    .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'-'))
        });
        if op_len > 2 || !(1..=3).contains(&parts.len()) || !parts.iter().all(numeric) || !pre_ok {
            return Err(fail(messages::comparator_invalid(comparator, text)));
        }
    }
    VersionReq::parse(text).map_err(|e| fail(messages::req_invalid(text, &e)))
}

/// Finds locked packs that have a newer version available.
///
/// Only packs with an entry in `ranges` are checked. `available` maps a pack id
/// to the versions a registry offers. The function does no I/O.
///
/// A prerelease version satisfies a range only when a comparator in the range
/// names a prerelease of the same `major.minor.patch` (the `semver` crate
/// rule, which follows Cargo). `newest` never reports a prerelease.
/// The result is sorted by id.
#[must_use]
pub fn outdated(
    lock: &Lockfile,
    ranges: &BTreeMap<PackId, VersionReq>,
    available: &BTreeMap<PackId, Vec<Version>>,
) -> Vec<OutdatedPack> {
    lock.packs()
        .iter()
        .filter_map(|locked| {
            let req = ranges.get(&locked.id)?;
            let versions = available.get(&locked.id)?;
            let newer = || versions.iter().filter(|v| **v > locked.version);
            let update = newer().filter(|v| req.matches(v)).max().cloned();
            let newest = newer().filter(|v| v.pre.is_empty()).max().cloned();
            (update.is_some() || newest.is_some()).then(|| OutdatedPack {
                id: locked.id.clone(),
                locked: locked.version.clone(),
                update,
                newest,
            })
        })
        .collect()
}
