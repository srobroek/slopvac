//! `plugins update`: resolve within config ranges and write a new lock (bead
//! 8l4.9.30; threat model K1-K3 rollback floor and key pins, K5 revocation;
//! policies.md offline mode and exit code 2).

mod oci_server;
mod revocations;
mod support;

use std::collections::{BTreeMap, HashMap};
use std::fmt::Write as _;
use std::fs;
use std::io::{Cursor, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, mpsc};
use std::time::Duration;

use flate2::Compression;
use flate2::write::GzEncoder;
use oci_server::{Response, Server};
use revocations::{ListServer, Root, Signed, list_json};
use slopvac_plugins::lock::{Lockfile, PackId, SourceKind, Version, VersionReq, parse_version_req};
use slopvac_plugins::oci::{Anonymous, Client, Descriptor, Digest, MEDIA_MANIFEST, Manifest};
use slopvac_plugins::revoke::Revocations;
use slopvac_plugins::sign::{
    ANNOTATION_ID, ANNOTATION_VERSION, KeyPolicy, MEDIA_MINISIG, MEDIA_STATEMENT, PublicKey,
    SignError, Statement,
};
use slopvac_plugins::sync::{
    ARTIFACT_TYPE_PACK, Change, MEDIA_PACK_LAYER, Network, Store, SyncError, Syncer,
};
use slopvac_plugins::update::{GUARD_PATH, Outcome, UpdateError, UpdateReport, Updater};

const FLOOR: &str = "2026-11-01T00:00:00Z";
const LATER: &str = "2026-11-10T00:00:00Z";
const EARLIER: &str = "2026-10-01T00:00:00Z";
const NOW: &str = "2026-11-14T00:00:00Z";

struct Key {
    pk: minisign::PublicKey,
    sk: minisign::SecretKey,
}

impl Key {
    fn new() -> Self {
        let kp = minisign::KeyPair::generate_unencrypted_keypair().unwrap();
        Self {
            pk: kp.pk,
            sk: kp.sk,
        }
    }
    fn public(&self) -> PublicKey {
        PublicKey::from_base64(&self.pk.to_base64()).unwrap()
    }
    fn sign(&self, bytes: &[u8]) -> String {
        minisign::sign(Some(&self.pk), &self.sk, Cursor::new(bytes), None, None)
            .unwrap()
            .to_string()
    }
}

fn targz(files: &[(&str, &[u8])]) -> Vec<u8> {
    let mut builder = tar::Builder::new(Vec::new());
    for (name, data) in files {
        let mut header = tar::Header::new_gnu();
        header.set_size(data.len() as u64);
        header.set_mode(0o644);
        header.set_entry_type(tar::EntryType::Regular);
        builder.append_data(&mut header, name, *data).unwrap();
    }
    let raw = builder.into_inner().unwrap();
    let mut gz = GzEncoder::new(Vec::new(), Compression::default());
    gz.write_all(&raw).unwrap();
    gz.finish().unwrap()
}

/// One signed version of a pack, ready to serve.
struct Release {
    tag: String,
    manifest: Vec<u8>,
    digest: String,
    blobs: HashMap<String, Vec<u8>>,
    key_id: String,
    not_before: String,
}

fn release(key: &Key, id: &str, version: &str, not_before: &str) -> Release {
    let layer = targz(&[("pack.toml", format!("version = \"{version}\"\n").as_bytes())]);
    let mut manifest = Manifest {
        schema_version: 2,
        media_type: Some(MEDIA_MANIFEST.into()),
        artifact_type: Some(ARTIFACT_TYPE_PACK.into()),
        config: Descriptor::for_bytes("application/vnd.oci.empty.v1+json", b"{}"),
        layers: vec![Descriptor::for_bytes(MEDIA_PACK_LAYER, &layer)],
        subject: None,
        annotations: BTreeMap::from([
            (ANNOTATION_ID.to_owned(), id.to_owned()),
            (ANNOTATION_VERSION.to_owned(), version.to_owned()),
        ]),
    };
    let key_id = key.public().key_id();
    let statement = Statement::for_manifest("acme", id, version, &key_id, not_before, &manifest)
        .canonical_bytes();
    let minisig = key.sign(&statement);
    manifest
        .layers
        .push(Descriptor::for_bytes(MEDIA_STATEMENT, &statement));
    manifest
        .layers
        .push(Descriptor::for_bytes(MEDIA_MINISIG, minisig.as_bytes()));
    let body = serde_json::to_vec(&manifest).unwrap();
    let mut blobs = HashMap::new();
    blobs.insert(Digest::of(&layer).to_string(), layer);
    blobs.insert(Digest::of(&statement).to_string(), statement);
    blobs.insert(
        Digest::of(minisig.as_bytes()).to_string(),
        minisig.into_bytes(),
    );
    blobs.insert(Digest::of(b"{}").to_string(), b"{}".to_vec());
    Release {
        tag: version.to_owned(),
        digest: Digest::of(&body).to_string(),
        manifest: body,
        blobs,
        key_id,
        not_before: not_before.to_owned(),
    }
}

/// A served repository: path prefix, (tag, digest, manifest) and blobs.
type Repo = (
    String,
    Vec<(String, String, Vec<u8>)>,
    HashMap<String, Vec<u8>>,
);

/// A registry with the repositories `acme/<name>`, each with its releases.
fn registry(repos: &[(&str, &[&Release])]) -> Server {
    registry_with(repos, || {})
}

/// Like [`registry`]; `on_tags` runs at each tag-list request, before the answer.
fn registry_with(
    repos: &[(&str, &[&Release])],
    on_tags: impl Fn() + Send + Sync + 'static,
) -> Server {
    let repos: Vec<Repo> = repos
        .iter()
        .map(|(name, releases)| {
            let manifests = releases
                .iter()
                .map(|r| (r.tag.clone(), r.digest.clone(), r.manifest.clone()))
                .collect();
            let blobs = releases.iter().flat_map(|r| r.blobs.clone()).collect();
            (format!("/v2/acme/{name}/"), manifests, blobs)
        })
        .collect();
    Server::start(move |req| {
        let Some((prefix, manifests, blobs)) = repos
            .iter()
            .find(|(p, _, _)| req.path.starts_with(p.as_str()))
        else {
            return Response::new(404);
        };
        let rest = &req.path[prefix.len()..];
        if rest.starts_with("tags/list") {
            on_tags();
            let tags: Vec<&str> = manifests.iter().map(|(t, _, _)| t.as_str()).collect();
            return Response::new(200).json(&serde_json::json!({ "tags": tags }));
        }
        if let Some(reference) = rest.strip_prefix("manifests/") {
            return manifests
                .iter()
                .find(|(t, d, _)| t == reference || d == reference)
                .map_or_else(
                    || Response::new(404),
                    |(_, _, body)| {
                        Response::new(200)
                            .header("Content-Type", MEDIA_MANIFEST)
                            .body(body.clone())
                    },
                );
        }
        let digest = rest.rsplit('/').next().unwrap_or_default();
        blobs.get(digest).map_or_else(
            || Response::new(404),
            |b| Response::new(200).body(b.clone()),
        )
    })
}

fn client() -> Client {
    Client::with_loopback_http_for_tests(Box::new(Anonymous))
}

fn policy(keys: &[&Key]) -> KeyPolicy {
    KeyPolicy {
        pinned: BTreeMap::from([("acme".to_owned(), keys.iter().map(|k| k.public()).collect())]),
        ..KeyPolicy::default()
    }
}

fn pack_id(s: &str) -> PackId {
    s.parse().unwrap()
}

fn ranges(entries: &[(&str, &str)]) -> BTreeMap<PackId, VersionReq> {
    entries
        .iter()
        .map(|(id, req)| (pack_id(id), parse_version_req(req).unwrap()))
        .collect()
}

/// A lock entry for `current`, signed in the lock when `signed`.
fn entry(id: &str, registry: &str, current: &Release, signed: bool) -> String {
    let mut text = format!(
        "\n[[plugins]]\nid = \"{id}\"\nkind = \"data\"\nversion = \"{}\"\nslopvac_api = 1\n\
         source = \"oci://{registry}/acme/{id}:{}\"\ndigest = \"{}\"\n",
        current.tag, current.tag, current.digest
    );
    if signed {
        write!(
            text,
            "\n[plugins.signature]\nkey_id = \"{}\"\nnot_before = \"{}\"\n",
            current.key_id, current.not_before
        )
        .unwrap();
    }
    text
}

struct Env {
    dir: support::Scratch,
    root: Root,
    list: ListServer,
}

impl Env {
    /// The revocation source serves an empty list signed by the root.
    fn new() -> Self {
        let root = Root::new();
        let empty = Signed::by(
            &root,
            list_json("2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z", &[], &[]),
        );
        Self {
            dir: support::scratch(),
            root,
            list: ListServer::start(Some(empty)),
        }
    }
    fn lock_path(&self) -> PathBuf {
        self.dir.path().join(".slopvac/plugins.lock")
    }
    fn write_lock(&self, entries: &[String]) -> String {
        let mut text = String::from("schema_version = 3\n");
        for e in entries {
            text.push_str(e);
        }
        let canonical = Lockfile::parse(&text).unwrap().to_toml();
        fs::create_dir_all(self.dir.path().join(".slopvac")).unwrap();
        fs::write(self.lock_path(), &canonical).unwrap();
        canonical
    }
    fn lock(&self) -> Lockfile {
        Lockfile::parse(&fs::read_to_string(self.lock_path()).unwrap()).unwrap()
    }
    fn revoke(&self, keys: &[&str], digests: &[&str]) {
        self.list.serve(Some(Signed::by(
            &self.root,
            list_json(
                "2026-11-10T00:00:00Z",
                "2026-12-10T00:00:00Z",
                keys,
                digests,
            ),
        )));
    }
    fn revocations(&self) -> Revocations {
        Revocations::new(
            self.dir.path().join("state"),
            vec![self.root.public()],
            self.list.source(),
            NOW,
        )
        .unwrap()
    }
    fn update(
        &self,
        network: Network<'_>,
        policy: &KeyPolicy,
        ranges: &BTreeMap<PackId, VersionReq>,
        only: &[PackId],
    ) -> Result<UpdateReport, UpdateError> {
        self.update_at(self.dir.path(), network, policy, ranges, only)
    }
    fn update_at(
        &self,
        project: &Path,
        network: Network<'_>,
        policy: &KeyPolicy,
        ranges: &BTreeMap<PackId, VersionReq>,
        only: &[PackId],
    ) -> Result<UpdateReport, UpdateError> {
        let revocations = self.revocations();
        Updater::new(network, policy, &revocations).update(project, ranges, only)
    }
}

fn version(s: &str) -> Version {
    s.parse().unwrap()
}

#[test]
fn an_in_range_update_writes_the_newest_version_to_the_lock() {
    let key = Key::new();
    let (v120, v130, v140) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
        release(&key, "style", "1.4.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130, &v140])]);
    let reg = server.registry();
    let env = Env::new();
    env.write_lock(&[entry("style", &reg, &v120, true)]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap();

    assert_eq!(report.exit_code(), 0);
    assert!(report.wrote_lock);
    assert!(
        matches!(&report.packs[0].outcome, Outcome::Updated { to } if *to == version("1.4.0")),
        "{:?}",
        report.packs[0]
    );
    let lock = env.lock();
    let pack = lock.get(&pack_id("style")).unwrap();
    assert_eq!(pack.version, version("1.4.0"));
    assert_eq!(pack.digest.as_str(), v140.digest);
    assert_eq!(
        pack.source.to_string(),
        format!("oci://{reg}/acme/style:1.4.0")
    );
    assert!(matches!(pack.source.kind(), SourceKind::Oci(_)));
    let sig = pack.signature.as_ref().unwrap();
    assert_eq!(sig.key_id.as_str(), v140.key_id);
    assert_eq!(sig.not_before.as_str(), LATER);
    // Canonical text on disk.
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), lock.to_toml());
}

#[test]
fn a_newer_version_outside_the_range_is_reported_and_not_taken() {
    let key = Key::new();
    let (v120, v130, v200) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
        release(&key, "style", "2.0.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130, &v200])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap();

    assert_eq!(report.packs[0].outside_range, Some(version("2.0.0")));
    assert!(matches!(report.packs[0].outcome, Outcome::Updated { .. }));
    assert_eq!(env.lock().packs()[0].version, version("1.3.0"));
}

#[test]
fn only_a_newer_version_outside_the_range_leaves_the_lock_alone() {
    let key = Key::new();
    let (v120, v200) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "2.0.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v200])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap();

    assert!(matches!(report.packs[0].outcome, Outcome::Unchanged));
    assert_eq!(report.packs[0].outside_range, Some(version("2.0.0")));
    assert!(!report.wrote_lock);
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_prerelease_is_not_taken_unless_the_range_names_it() {
    let key = Key::new();
    let (v130, rc) = (
        release(&key, "style", "1.3.0", FLOOR),
        release(&key, "style", "1.4.0-rc.1", LATER),
    );
    let server = registry(&[("style", &[&v130, &rc])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &v130, true)]);
    let c = client();

    let plain = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.3")]),
            &[],
        )
        .unwrap();
    assert!(matches!(plain.packs[0].outcome, Outcome::Unchanged));
    assert_eq!(
        plain.packs[0].outside_range, None,
        "never advertises a prerelease"
    );
    assert_eq!(env.lock().packs()[0].version, version("1.3.0"));

    let named = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", ">=1.3.0, <=1.4.0-rc.1")]),
            &[],
        )
        .unwrap();
    assert!(matches!(named.packs[0].outcome, Outcome::Updated { .. }));
    assert_eq!(env.lock().packs()[0].version, version("1.4.0-rc.1"));
}

#[test]
fn a_key_that_is_not_pinned_is_refused_and_the_lock_stays() {
    let (pinned, rogue) = (Key::new(), Key::new());
    let v120 = release(&pinned, "style", "1.2.0", FLOOR);
    let v130 = release(&rogue, "style", "1.3.0", LATER);
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&pinned]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap();

    assert!(
        matches!(
            &report.packs[0].outcome,
            Outcome::Refused(SyncError::Sign {
                source: SignError::KeyNotPinned { .. },
                ..
            })
        ),
        "{:?}",
        report.packs[0]
    );
    assert_eq!(report.exit_code(), 2);
    assert!(!report.wrote_lock);
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_revoked_artifact_is_refused() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    env.revoke(&[], &[&v130.digest]);
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap();

    assert!(
        matches!(
            &report.packs[0].outcome,
            Outcome::Refused(SyncError::Revoked { .. })
        ),
        "{:?}",
        report.packs[0]
    );
    assert_eq!(report.exit_code(), 2);
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_revoked_signing_key_is_refused() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    env.revoke(&[&v130.key_id], &[]);
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap();

    assert!(
        matches!(
            &report.packs[0].outcome,
            Outcome::Refused(SyncError::Revoked { .. })
        ),
        "{:?}",
        report.packs[0]
    );
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_statement_older_than_the_locks_floor_is_refused() {
    let key = Key::new();
    let v120 = release(&key, "style", "1.2.0", FLOOR);
    // A higher version whose signed notBefore predates the lock's floor.
    let stale = release(&key, "style", "1.3.0", EARLIER);
    let server = registry(&[("style", &[&v120, &stale])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap();

    assert!(
        matches!(
            &report.packs[0].outcome,
            Outcome::Refused(SyncError::Sign {
                source: SignError::Rollback(_),
                ..
            })
        ),
        "{:?}",
        report.packs[0]
    );
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn offline_update_is_refused_with_exit_2_and_touches_nothing() {
    let key = Key::new();
    let v120 = release(&key, "style", "1.2.0", FLOOR);
    let server = registry(&[("style", &[&v120])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);

    let err = env
        .update(
            Network::Offline,
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert!(matches!(err, UpdateError::Offline), "{err:?}");
    assert_eq!(err.exit_code(), 2);
    assert_eq!(err.code(), "offline-network-needed");
    assert_eq!(err.to_string(), "offline: plugins update needs the network");
    assert!(server.requests().is_empty());
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_second_update_changes_nothing() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();
    let pol = policy(&[&key]);
    let wanted = ranges(&[("style", "^1.2")]);

    let first = env.update(Network::Online(&c), &pol, &wanted, &[]).unwrap();
    let after_first = fs::read_to_string(env.lock_path()).unwrap();
    let second = env.update(Network::Online(&c), &pol, &wanted, &[]).unwrap();

    assert!(first.wrote_lock);
    assert!(!second.wrote_lock);
    assert!(matches!(second.packs[0].outcome, Outcome::Unchanged));
    assert_eq!(second.exit_code(), 0);
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), after_first);
}

#[test]
fn a_named_pack_updates_alone() {
    let key = Key::new();
    let (s120, s130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let (o100, o110) = (
        release(&key, "other", "1.0.0", FLOOR),
        release(&key, "other", "1.1.0", LATER),
    );
    let server = registry(&[("style", &[&s120, &s130]), ("other", &[&o100, &o110])]);
    let reg = server.registry();
    let env = Env::new();
    env.write_lock(&[
        entry("style", &reg, &s120, true),
        entry("other", &reg, &o100, true),
    ]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2"), ("other", "^1.0")]),
            &[pack_id("style")],
        )
        .unwrap();

    assert_eq!(report.packs.len(), 1);
    let lock = env.lock();
    assert_eq!(
        lock.get(&pack_id("style")).unwrap().version,
        version("1.3.0")
    );
    assert_eq!(
        lock.get(&pack_id("other")).unwrap().version,
        version("1.0.0")
    );
}

#[test]
fn a_refused_pack_does_not_block_the_others() {
    let (key, rogue) = (Key::new(), Key::new());
    let (s120, s130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&rogue, "style", "1.3.0", LATER),
    );
    let (o100, o110) = (
        release(&key, "other", "1.0.0", FLOOR),
        release(&key, "other", "1.1.0", LATER),
    );
    let server = registry(&[("style", &[&s120, &s130]), ("other", &[&o100, &o110])]);
    let reg = server.registry();
    let env = Env::new();
    env.write_lock(&[
        entry("style", &reg, &s120, true),
        entry("other", &reg, &o100, true),
    ]);
    let c = client();

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2"), ("other", "^1.0")]),
            &[],
        )
        .unwrap();

    assert_eq!(report.exit_code(), 2);
    let lock = env.lock();
    assert_eq!(
        lock.get(&pack_id("style")).unwrap().version,
        version("1.2.0")
    );
    assert_eq!(
        lock.get(&pack_id("other")).unwrap().version,
        version("1.1.0")
    );
}

#[test]
fn a_plugin_not_in_the_lock_reports_update_plugin_unknown() {
    let key = Key::new();
    let v120 = release(&key, "style", "1.2.0", FLOOR);
    let server = registry(&[("style", &[&v120])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[pack_id("ghost")],
        )
        .unwrap_err();

    assert_eq!(err.code(), "update-plugin-unknown");
    assert_eq!(err.exit_code(), 2);
}

#[test]
fn an_invalid_lock_still_reports_update_failed() {
    let key = Key::new();
    let env = Env::new();
    fs::create_dir_all(env.dir.path().join(".slopvac")).unwrap();
    fs::write(env.lock_path(), "this is not a lock\n").unwrap();
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert!(matches!(err, UpdateError::Lock { .. }), "{err:?}");
    assert_eq!(err.code(), "update-failed");
}

#[test]
fn a_pack_not_in_the_lock_is_an_error() {
    let key = Key::new();
    let v120 = release(&key, "style", "1.2.0", FLOOR);
    let server = registry(&[("style", &[&v120])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[pack_id("ghost")],
        )
        .unwrap_err();

    assert!(matches!(err, UpdateError::UnknownPlugin(ref id) if id.as_str() == "ghost"));
}

#[test]
fn an_unsigned_entry_is_signed_by_update_once_the_key_is_pinned() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &v120, false)]);
    let c = client();

    env.update(
        Network::Online(&c),
        &policy(&[&key]),
        &ranges(&[("style", "^1.2")]),
        &[],
    )
    .unwrap();

    let lock = env.lock();
    let sig = lock.packs()[0].signature.as_ref().unwrap();
    assert_eq!(sig.key_id.as_str(), v130.key_id);
    assert_eq!(sig.not_before.as_str(), LATER);
}

#[test]
fn a_pack_without_a_range_is_left_alone() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();

    let report = env
        .update(Network::Online(&c), &policy(&[&key]), &BTreeMap::new(), &[])
        .unwrap();

    assert!(matches!(report.packs[0].outcome, Outcome::Unchanged));
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

fn assert_refused_lock(err: &UpdateError) {
    assert!(matches!(err, UpdateError::Lock { .. }), "{err:?}");
    assert_eq!(err.exit_code(), 2);
}

#[cfg(unix)]
#[test]
fn a_symlinked_lock_directory_is_refused_and_the_target_lock_is_untouched() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    // Another project holds a valid lock; this checkout's `.slopvac` links to it.
    let other = Env::new();
    let before = other.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let env = Env::new();
    std::os::unix::fs::symlink(
        other.dir.path().join(".slopvac"),
        env.dir.path().join(".slopvac"),
    )
    .unwrap();
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert_refused_lock(&err);
    assert_eq!(fs::read_to_string(other.lock_path()).unwrap(), before);
}

#[cfg(unix)]
#[test]
fn a_symlinked_lock_file_is_refused_and_its_target_is_untouched() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let real = env.dir.path().join("real.lock");
    fs::rename(env.lock_path(), &real).unwrap();
    std::os::unix::fs::symlink(&real, env.lock_path()).unwrap();
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert_refused_lock(&err);
    assert_eq!(fs::read_to_string(&real).unwrap(), before);
}

#[cfg(unix)]
#[test]
fn a_lock_that_links_to_an_endless_device_is_refused_without_reading_it() {
    let env = Env::new();
    fs::create_dir_all(env.dir.path().join(".slopvac")).unwrap();
    std::os::unix::fs::symlink("/dev/zero", env.lock_path()).unwrap();
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert_refused_lock(&err);
}

#[test]
fn a_lock_over_the_size_limit_is_refused_and_left_alone() {
    let env = Env::new();
    fs::create_dir_all(env.dir.path().join(".slopvac")).unwrap();
    let huge = vec![b'#'; 1024 * 1024 + 1];
    fs::write(env.lock_path(), &huge).unwrap();
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert_refused_lock(&err);
    assert!(err.to_string().contains("size limit"), "{err}");
    assert_eq!(fs::read(env.lock_path()).unwrap(), huge);
}

fn two_packs(key: &Key) -> (Vec<Release>, Vec<Release>) {
    (
        vec![
            release(key, "style", "1.2.0", FLOOR),
            release(key, "style", "1.3.0", LATER),
        ],
        vec![
            release(key, "other", "1.0.0", FLOOR),
            release(key, "other", "1.1.0", LATER),
        ],
    )
}

fn open_guard(env: &Env) -> fs::File {
    fs::File::open(env.dir.path().join(GUARD_PATH)).unwrap()
}

#[test]
fn an_update_gives_up_when_another_holds_the_guard() {
    let key = Key::new();
    let (style, _) = two_packs(&key);
    let server = registry(&[("style", &[&style[0], &style[1]])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &style[0], true)]);
    let mut open = fs::OpenOptions::new();
    open.create(true).truncate(false).write(true);
    #[cfg(unix)]
    std::os::unix::fs::OpenOptionsExt::mode(&mut open, 0o600);
    let holder = open.open(env.dir.path().join(GUARD_PATH)).unwrap();
    holder.lock().unwrap();
    let c = client();
    let revocations = env.revocations();
    let pol = policy(&[&key]);

    let err = Updater::new(Network::Online(&c), &pol, &revocations)
        .with_guard_timeout(Duration::from_millis(200))
        .update(env.dir.path(), &ranges(&[("style", "^1.2")]), &[])
        .unwrap_err();

    assert!(matches!(err, UpdateError::Busy { .. }), "{err:?}");
    assert_eq!(err.exit_code(), 2);
    assert_eq!(err.code(), "update-lock-busy");
    assert!(
        server.requests().is_empty(),
        "nothing is resolved without the lock"
    );
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_second_update_cannot_run_while_the_first_is_resolving() {
    let key = Key::new();
    let (style, other) = two_packs(&key);
    // The first tag-list request announces itself, then waits to be released.
    let (reached_tx, reached_rx) = mpsc::channel::<()>();
    let (release_tx, release_rx) = mpsc::channel::<()>();
    let gate = Mutex::new(Some((reached_tx, release_rx)));
    let server = registry_with(
        &[
            ("style", &[&style[0], &style[1]]),
            ("other", &[&other[0], &other[1]]),
        ],
        move || {
            if let Some((reached, release)) = gate.lock().unwrap().take() {
                reached.send(()).unwrap();
                release.recv().unwrap();
            }
        },
    );
    let reg = server.registry();
    let env = Env::new();
    env.write_lock(&[
        entry("style", &reg, &style[0], true),
        entry("other", &reg, &other[0], true),
    ]);
    let c = client();
    let pol = policy(&[&key]);

    std::thread::scope(|scope| {
        let first = scope.spawn(|| {
            env.update(
                Network::Online(&c),
                &pol,
                &ranges(&[("style", "^1.2")]),
                &[pack_id("style")],
            )
        });
        reached_rx.recv().unwrap();
        // The first update is inside resolution: it must hold the guard.
        let probe = open_guard(&env).try_lock();
        assert!(
            matches!(probe, Err(std::fs::TryLockError::WouldBlock)),
            "the guard is free while an update resolves: {probe:?}"
        );
        // A second update cannot start meanwhile.
        let revocations = env.revocations();
        let second = Updater::new(Network::Online(&c), &pol, &revocations)
            .with_guard_timeout(Duration::from_millis(200))
            .update(
                env.dir.path(),
                &ranges(&[("other", "^1.0")]),
                &[pack_id("other")],
            );
        assert!(
            matches!(second, Err(UpdateError::Busy { .. })),
            "{second:?}"
        );
        release_tx.send(()).unwrap();
        first.join().unwrap().unwrap();
    });

    let lock = env.lock();
    assert_eq!(
        lock.get(&pack_id("style")).unwrap().version,
        version("1.3.0")
    );
    assert_eq!(
        lock.get(&pack_id("other")).unwrap().version,
        version("1.0.0")
    );
}

#[test]
fn a_second_update_waits_for_the_first_and_both_changes_survive() {
    let key = Key::new();
    let (style, other) = two_packs(&key);
    let (reached_tx, reached_rx) = mpsc::channel::<()>();
    let (release_tx, release_rx) = mpsc::channel::<()>();
    let gate = Mutex::new(Some((reached_tx, release_rx)));
    let server = registry_with(
        &[
            ("style", &[&style[0], &style[1]]),
            ("other", &[&other[0], &other[1]]),
        ],
        move || {
            if let Some((reached, release)) = gate.lock().unwrap().take() {
                reached.send(()).unwrap();
                release.recv().unwrap();
            }
        },
    );
    let reg = server.registry();
    let env = Env::new();
    env.write_lock(&[
        entry("style", &reg, &style[0], true),
        entry("other", &reg, &other[0], true),
    ]);
    let c = client();
    let pol = policy(&[&key]);
    let (waiting_tx, waiting_rx) = mpsc::channel::<()>();
    let waiting_tx = Mutex::new(waiting_tx);

    std::thread::scope(|scope| {
        let first = scope.spawn(|| {
            env.update(
                Network::Online(&c),
                &pol,
                &ranges(&[("style", "^1.2")]),
                &[pack_id("style")],
            )
        });
        // The first update is inside resolution and holds the guard.
        reached_rx.recv().unwrap();
        let second = scope.spawn(|| {
            let revocations = env.revocations();
            Updater::new(Network::Online(&c), &pol, &revocations)
                .with_guard_timeout(Duration::from_secs(60))
                .with_guard_wait_hook(move || {
                    let _ = waiting_tx.lock().unwrap().send(());
                })
                .update(
                    env.dir.path(),
                    &ranges(&[("other", "^1.0")]),
                    &[pack_id("other")],
                )
        });
        // The second update has found the guard held and is waiting on it.
        waiting_rx.recv().unwrap();
        release_tx.send(()).unwrap();
        first.join().unwrap().unwrap();
        let report = second.join().unwrap().unwrap();
        assert!(report.wrote_lock);
    });

    let lock = env.lock();
    assert_eq!(
        lock.get(&pack_id("style")).unwrap().version,
        version("1.3.0")
    );
    assert_eq!(
        lock.get(&pack_id("other")).unwrap().version,
        version("1.1.0")
    );
}

#[test]
fn repeated_sources_list_the_repository_once() {
    let key = Key::new();
    let (style, _) = two_packs(&key);
    let server = registry(&[("style", &[&style[0], &style[1]])]);
    let reg = server.registry();
    let env = Env::new();
    // Four packs, one repository.
    let many: Vec<String> = ["a", "b", "c", "d"]
        .iter()
        .map(|id| entry(id, &reg, &style[0], true).replace(&format!("acme/{id}:"), "acme/style:"))
        .collect();
    env.write_lock(&many);
    let c = client();
    let wanted = ranges(&[("a", "^1.2"), ("b", "^1.2"), ("c", "^1.2"), ("d", "^1.2")]);

    let _ = env.update(Network::Online(&c), &policy(&[&key]), &wanted, &[]);

    assert_eq!(server.count("/v2/acme/style/tags/list"), 1);
}

#[test]
fn oversized_tags_are_ignored_before_they_reach_semver() {
    let key = Key::new();
    let v120 = release(&key, "style", "1.2.0", FLOOR);
    let long = format!("1.9.0-{}", "a".repeat(200));
    let mut huge = release(&key, "style", "1.9.0", LATER);
    huge.tag = long.clone();
    let server = registry(&[("style", &[&v120, &huge])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();
    // The range names the oversized prerelease, so semver alone would take it.
    let req = format!(">=1.2.0, <={long}");

    let report = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", req.as_str())]),
            &[],
        )
        .unwrap();

    assert!(matches!(report.packs[0].outcome, Outcome::Unchanged));
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn the_listing_budget_is_shared_across_repositories() {
    let key = Key::new();
    let (style, other) = two_packs(&key);
    let server = registry(&[
        ("style", &[&style[0], &style[1]]),
        ("other", &[&other[0], &other[1]]),
    ]);
    let reg = server.registry();
    let env = Env::new();
    env.write_lock(&[
        entry("style", &reg, &style[0], true),
        entry("other", &reg, &other[0], true),
    ]);
    let c = client();
    let revocations = env.revocations();
    let pol = policy(&[&key]);

    // Each list is `{"tags":["1.2.0","1.3.0"]}`, 27 bytes. 40 bytes cover one
    // list and not two. Repositories are listed in name order: `other` first.
    let report = Updater::new(Network::Online(&c), &pol, &revocations)
        .with_listing_budget(40)
        .update(
            env.dir.path(),
            &ranges(&[("style", "^1.2"), ("other", "^1.0")]),
            &[],
        )
        .unwrap();

    assert_eq!(report.exit_code(), 2);
    let by_id = |id: &str| report.packs.iter().find(|p| p.id.as_str() == id).unwrap();
    assert!(matches!(by_id("other").outcome, Outcome::Updated { .. }));
    assert!(matches!(by_id("style").outcome, Outcome::Refused(_)));
    let lock = env.lock();
    assert_eq!(
        lock.get(&pack_id("other")).unwrap().version,
        version("1.1.0")
    );
    assert_eq!(
        lock.get(&pack_id("style")).unwrap().version,
        version("1.2.0")
    );
}

/// A registry whose answer to every request is written by `serve`. It counts
/// the requests per path.
fn scripted_registry(
    serve: impl Fn(&mut std::net::TcpStream) + Send + Sync + 'static,
) -> (u16, Arc<Mutex<Vec<String>>>) {
    use std::io::Read as _;
    use std::net::TcpListener;
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let seen = Arc::new(Mutex::new(Vec::new()));
    let log = Arc::clone(&seen);
    let serve = Arc::new(serve);
    std::thread::spawn(move || {
        for mut conn in listener.incoming().flatten() {
            let (log, serve) = (Arc::clone(&log), Arc::clone(&serve));
            std::thread::spawn(move || {
                let mut head = Vec::new();
                let mut byte = [0u8; 1];
                while !head.ends_with(b"\r\n\r\n") {
                    if conn.read(&mut byte).unwrap_or(0) == 0 {
                        return;
                    }
                    head.push(byte[0]);
                }
                let text = String::from_utf8_lossy(&head).into_owned();
                log.lock()
                    .unwrap()
                    .push(text.split(' ').nth(1).unwrap_or_default().to_owned());
                serve(&mut conn);
            });
        }
    });
    (port, seen)
}

/// A small chunked tag list followed by an endless trailer.
fn serve_trailer_flood(conn: &mut std::net::TcpStream) {
    let body = br#"{"tags":["1.2.0","1.3.0"]}"#;
    let reply = format!(
        "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n{:x}\r\n",
        body.len()
    );
    let batch = format!("X-Flood: {}\r\n", "a".repeat(1000)).repeat(64);
    let mut ok = conn.write_all(reply.as_bytes()).is_ok()
        && conn.write_all(body).is_ok()
        && conn.write_all(b"\r\n0\r\n").is_ok();
    for _ in 0..(64 << 20) / batch.len() {
        if !ok {
            return;
        }
        ok = conn.write_all(batch.as_bytes()).is_ok();
    }
}

/// A redirect without a `Location`, padded with 60 KiB of headers.
fn serve_padded_redirect(conn: &mut std::net::TcpStream) {
    let pad = format!("X-Pad: {}\r\n", "a".repeat(1000)).repeat(60);
    let reply = format!("HTTP/1.1 302 Found\r\nContent-Length: 0\r\n{pad}\r\n");
    let _ = conn.write_all(reply.as_bytes());
}

/// Two repositories on a registry whose first listing is padded. The first
/// listing alone uses up `budget`, so the second is refused without a request.
fn assert_one_listing_uses_up_the_budget(
    serve: impl Fn(&mut std::net::TcpStream) + Send + Sync + 'static,
    budget: u64,
) {
    let key = Key::new();
    let (style, other) = two_packs(&key);
    let (port, seen) = scripted_registry(serve);
    let reg = format!("127.0.0.1:{port}");
    let env = Env::new();
    let before = env.write_lock(&[
        entry("style", &reg, &style[0], true),
        entry("other", &reg, &other[0], true),
    ]);
    let c = client();
    let revocations = env.revocations();
    let pol = policy(&[&key]);

    // Repositories are listed in name order: `other` first.
    let report = Updater::new(Network::Online(&c), &pol, &revocations)
        .with_listing_budget(budget)
        .update(
            env.dir.path(),
            &ranges(&[("style", "^1.2"), ("other", "^1.0")]),
            &[],
        )
        .unwrap();

    assert_eq!(report.exit_code(), 2);
    assert!(
        report
            .packs
            .iter()
            .all(|p| matches!(p.outcome, Outcome::Refused(_))),
        "{report:?}"
    );
    let paths = seen.lock().unwrap().clone();
    assert_eq!(
        paths.iter().filter(|p| p.contains("/acme/other/")).count(),
        1,
        "{paths:?}"
    );
    assert!(
        !paths.iter().any(|p| p.contains("/acme/style/")),
        "the second repository was listed: {paths:?}"
    );
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn trailer_bytes_of_one_listing_use_up_the_budget_for_the_next_repository() {
    // The decoded tag list is 27 bytes, far under the 1 MiB budget. Its trailer
    // is not: the raw bytes cut off at the cap use the whole budget.
    assert_one_listing_uses_up_the_budget(serve_trailer_flood, 1 << 20);
}

#[test]
fn bytes_of_a_refused_redirect_use_up_the_budget_for_the_next_repository() {
    // The redirect has no body and is refused, but its 60 KiB of headers were
    // read: more than the 40 KiB budget.
    assert_one_listing_uses_up_the_budget(serve_padded_redirect, 40 << 10);
}

#[test]
fn bytes_read_before_a_late_page_failure_still_count_against_the_budget() {
    let key = Key::new();
    let releases: Vec<Release> = ["r1", "r2", "r3"]
        .iter()
        .map(|id| release(&key, id, "1.2.0", FLOOR))
        .collect();
    // Page one is about 1.5 KiB and links to a page two that is not JSON.
    let padding: Vec<String> = (0..12)
        .map(|i| format!("1.0.{i}-{}", "a".repeat(100)))
        .collect();
    let page_one = serde_json::json!({ "tags": padding }).to_string();
    let server = Server::start(move |req| {
        if !req.path.contains("/tags/list") {
            return Response::new(404);
        }
        if req.path.contains("page=2") {
            return Response::new(200).body("{ not json");
        }
        let repo = req
            .path
            .split("/tags/list")
            .next()
            .unwrap_or_default()
            .to_owned();
        Response::new(200)
            .header("Content-Type", "application/json")
            .header(
                "Link",
                &format!("<{repo}/tags/list?n=1000&page=2>; rel=\"next\""),
            )
            .body(page_one.clone())
    });
    let reg = server.registry();
    let env = Env::new();
    let entries: Vec<String> = releases
        .iter()
        .zip(["r1", "r2", "r3"])
        .map(|(r, id)| entry(id, &reg, r, true))
        .collect();
    let before = env.write_lock(&entries);
    let c = client();
    let revocations = env.revocations();
    let pol = policy(&[&key]);

    // One first page and its failing second page use most of the budget; the second repository runs out, so the third gets no request.
    let report = Updater::new(Network::Online(&c), &pol, &revocations)
        .with_listing_budget(1500)
        .update(
            env.dir.path(),
            &ranges(&[("r1", "^1.2"), ("r2", "^1.2"), ("r3", "^1.2")]),
            &[],
        )
        .unwrap();

    assert_eq!(report.exit_code(), 2);
    assert!(
        report
            .packs
            .iter()
            .all(|p| matches!(p.outcome, Outcome::Refused(_))),
        "{report:?}"
    );
    assert_eq!(server.count("/v2/acme/r3/tags/list"), 0);
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_lock_that_grows_during_resolution_is_refused_without_reading_it_whole() {
    let key = Key::new();
    let (style, _) = two_packs(&key);
    let env = Env::new();
    let lock_path = env.lock_path();
    let server = registry_with(&[("style", &[&style[0], &style[1]])], move || {
        // A project writer enlarges the lock after update has read it.
        let mut f = fs::OpenOptions::new()
            .append(true)
            .open(&lock_path)
            .unwrap();
        f.write_all(&vec![b'#'; 4 * 1024 * 1024]).unwrap();
    });
    env.write_lock(&[entry("style", &server.registry(), &style[0], true)]);
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert!(matches!(err, UpdateError::Write { .. }), "{err:?}");
    assert!(err.to_string().contains("size limit"), "{err}");
}

/// An update that would change the lock, run through `run`.
fn windows_refusal(
    run: impl FnOnce(&Env, &Client, &KeyPolicy) -> Result<UpdateReport, UpdateError>,
) {
    let key = Key::new();
    let (style, _) = two_packs(&key);
    let server = registry(&[("style", &[&style[0], &style[1]])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &style[0], true)]);
    let c = client();

    let err = run(&env, &c, &policy(&[&key])).unwrap_err();

    assert!(
        matches!(err, UpdateError::UnsupportedOnWindows(_)),
        "{err:?}"
    );
    assert_eq!(err.exit_code(), 2);
    assert_eq!(err.code(), "unsupported-on-windows");
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn on_windows_a_lock_write_is_refused_and_the_lock_stays() {
    windows_refusal(|env, c, pol| {
        let revocations = env.revocations();
        Updater::new(Network::Online(c), pol, &revocations).update_seam(
            env.dir.path(),
            &ranges(&[("style", "^1.2")]),
            &[],
            true,
        )
    });
}

#[cfg(windows)]
#[test]
fn native_windows_update_refuses_to_write_the_lock() {
    windows_refusal(|env, c, pol| {
        env.update(Network::Online(c), pol, &ranges(&[("style", "^1.2")]), &[])
    });
}

#[test]
fn off_windows_the_same_update_writes_the_lock() {
    let key = Key::new();
    let (style, _) = two_packs(&key);
    let server = registry(&[("style", &[&style[0], &style[1]])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &style[0], true)]);
    let c = client();
    let revocations = env.revocations();
    let pol = policy(&[&key]);

    let report = Updater::new(Network::Online(&c), &pol, &revocations)
        .update_seam(env.dir.path(), &ranges(&[("style", "^1.2")]), &[], false)
        .unwrap();

    assert!(report.wrote_lock);
}

#[cfg(unix)]
#[test]
fn the_guard_file_is_created_private() {
    use std::os::unix::fs::PermissionsExt;
    let key = Key::new();
    let (style, _) = two_packs(&key);
    let server = registry(&[("style", &[&style[0]])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &style[0], true)]);
    let c = client();

    env.update(
        Network::Online(&c),
        &policy(&[&key]),
        &ranges(&[("style", "^1.2")]),
        &[],
    )
    .unwrap();

    let mode = fs::metadata(env.dir.path().join(GUARD_PATH))
        .unwrap()
        .permissions()
        .mode();
    assert_eq!(mode & 0o777, 0o600);
}

#[cfg(unix)]
#[test]
fn a_guard_file_that_others_can_open_is_refused() {
    use std::os::unix::fs::PermissionsExt;
    let key = Key::new();
    let (style, _) = two_packs(&key);
    let server = registry(&[("style", &[&style[0], &style[1]])]);
    let env = Env::new();
    let before = env.write_lock(&[entry("style", &server.registry(), &style[0], true)]);
    let guard = env.dir.path().join(GUARD_PATH);
    fs::write(&guard, b"").unwrap();
    fs::set_permissions(&guard, fs::Permissions::from_mode(0o644)).unwrap();
    let c = client();

    let err = env
        .update(
            Network::Online(&c),
            &policy(&[&key]),
            &ranges(&[("style", "^1.2")]),
            &[],
        )
        .unwrap_err();

    assert_refused_lock(&err);
    assert!(err.to_string().contains("private"), "{err}");
    assert_eq!(fs::read_to_string(env.lock_path()).unwrap(), before);
}

#[test]
fn a_synced_updated_lock_installs_the_new_content_and_stays_unchanged() {
    let key = Key::new();
    let (v120, v130) = (
        release(&key, "style", "1.2.0", FLOOR),
        release(&key, "style", "1.3.0", LATER),
    );
    let server = registry(&[("style", &[&v120, &v130])]);
    let env = Env::new();
    env.write_lock(&[entry("style", &server.registry(), &v120, true)]);
    let c = client();
    let pol = policy(&[&key]);
    env.update(
        Network::Online(&c),
        &pol,
        &ranges(&[("style", "^1.2")]),
        &[],
    )
    .unwrap();
    let written = fs::read(env.lock_path()).unwrap();

    let lock = env.lock();
    let store = Store::new(env.dir.path().join("slopvac"));
    let revocations = env.revocations();
    let report = Syncer::new(
        &store,
        Network::Online(&c),
        &pol,
        env.dir.path(),
        &revocations,
    )
    .sync(&lock)
    .unwrap();

    assert_eq!(report.packs[0].change, Change::Installed);
    assert_eq!(report.packs[0].version, version("1.3.0"));
    assert_eq!(
        fs::read(report.packs[0].tree.join("pack.toml")).unwrap(),
        b"version = \"1.3.0\"\n"
    );
    assert_eq!(fs::read(env.lock_path()).unwrap(), written);
}

#[test]
fn hostile_path_characters_are_escaped_in_error_text() {
    let hostile = "evil\u{1b}[31m\n\u{202e}";
    let err = UpdateError::Write {
        path: format!("/p/{hostile}/.slopvac/plugins.lock"),
        source: std::io::Error::other("disk"),
    };
    let text = err.to_string();
    assert!(!text.chars().any(char::is_control), "{text:?}");
    assert!(!text.contains('\u{202e}'), "{text:?}");
    assert!(text.contains("\\u{1b}[31m\\u{a}"), "{text}");
}

#[cfg(unix)]
#[test]
fn a_hostile_project_directory_name_is_escaped_in_a_real_failure() {
    let env = Env::new();
    let root = env.dir.path().join("a\u{1b}[31mb\nc");
    fs::create_dir_all(&root).unwrap();
    let c = client();
    let err = env
        .update_at(
            &root,
            Network::Online(&c),
            &policy(&[]),
            &BTreeMap::new(),
            &[],
        )
        .unwrap_err();
    let text = err.to_string();
    assert!(!text.chars().any(char::is_control), "{text:?}");
    assert!(text.contains("\\u{1b}"), "{text}");
}
