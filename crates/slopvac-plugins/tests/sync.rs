//! Sync, status, offline cache and CI lock check (bead 8l4.9.3; threat model
//! TM-22, TM-39, TM-46, TM-48; policies.md N2, N4, N7).

mod common;
mod oci_server;
mod revocations;
mod support;

use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::io::{Cursor, Write};
use std::path::{Path, PathBuf};

use flate2::Compression;
use flate2::write::GzEncoder;
use oci_server::{Response, Server};
use revocations::{ListServer, Root, Signed, list_json};
use rstest::rstest;
use slopvac_plugins::lock::{
    Lockfile, PackId, ResolvedPack, Source, Version, VersionReq, parse_version_req,
};
use slopvac_plugins::oci::{
    Anonymous, Client, Descriptor, Digest, MEDIA_MANIFEST, Manifest, OciError, Reference,
};
use slopvac_plugins::revoke::{RevocationError, RevocationNotice, Revocations};
use slopvac_plugins::sign::{
    ANNOTATION_ID, ANNOTATION_VERSION, KeyPolicy, MEDIA_MINISIG, MEDIA_STATEMENT, PublicKey,
    SignError, Statement,
};
use slopvac_plugins::sync::{
    ARTIFACT_TYPE_PACK, Change, MEDIA_PACK_LAYER, Network, PackState, Store, SyncError, Syncer,
    available_versions, check_lock, status, update_notices,
};

const NOT_BEFORE: &str = "2026-11-01T00:00:00Z";
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

/// A signed pack artifact, ready to serve.
struct Published {
    manifest: Vec<u8>,
    digest: String,
    blobs: HashMap<String, Vec<u8>>,
    key_id: String,
}

fn publish(key: &Key, namespace: &str, files: &[(&str, &[u8])]) -> Published {
    let layer = targz(files);
    let mut manifest = Manifest {
        schema_version: 2,
        media_type: Some(MEDIA_MANIFEST.into()),
        artifact_type: Some(ARTIFACT_TYPE_PACK.into()),
        config: Descriptor::for_bytes("application/vnd.oci.empty.v1+json", b"{}"),
        layers: vec![Descriptor::for_bytes(MEDIA_PACK_LAYER, &layer)],
        subject: None,
        annotations: BTreeMap::from([
            (ANNOTATION_ID.to_owned(), "style".to_owned()),
            (ANNOTATION_VERSION.to_owned(), "1.2.0".to_owned()),
        ]),
    };
    let key_id = key.public().key_id();
    let statement =
        Statement::for_manifest(namespace, "style", "1.2.0", &key_id, NOT_BEFORE, &manifest)
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
    Published {
        digest: Digest::of(&body).to_string(),
        manifest: body,
        blobs,
        key_id,
    }
}

/// The artifact of [`publish`] with its statement and signature layers removed.
fn publish_without_signature(key: &Key, namespace: &str, files: &[(&str, &[u8])]) -> Published {
    let mut p = publish(key, namespace, files);
    let mut manifest: Manifest = serde_json::from_slice(&p.manifest).unwrap();
    manifest
        .layers
        .retain(|l| l.media_type != MEDIA_STATEMENT && l.media_type != MEDIA_MINISIG);
    p.manifest = serde_json::to_vec(&manifest).unwrap();
    p.digest = Digest::of(&p.manifest).to_string();
    p
}

/// A registry that serves `artifacts` by digest (and any manifest tag as the first one).
fn registry(artifacts: &[&Published]) -> Server {
    let mut manifests: HashMap<String, Vec<u8>> = HashMap::new();
    let mut blobs: HashMap<String, Vec<u8>> = HashMap::new();
    for a in artifacts {
        manifests.insert(a.digest.clone(), a.manifest.clone());
        blobs.extend(a.blobs.clone());
    }
    let first = artifacts.first().map(|a| a.manifest.clone());
    Server::start(move |req| {
        let last = req.path.rsplit('/').next().unwrap_or_default();
        if req.path.contains("/tags/list") {
            return Response::new(200).json(&serde_json::json!({
                "name": "acme/style",
                "tags": ["1.0.0", "latest", "1.2.0", "1.3.0", "2.0.0-rc.1"]
            }));
        }
        if req.path.contains("/manifests/") {
            let body = manifests.get(last).cloned().or_else(|| first.clone());
            return body.map_or_else(
                || Response::new(404),
                |b| {
                    Response::new(200)
                        .header("Content-Type", MEDIA_MANIFEST)
                        .body(b)
                },
            );
        }
        blobs.get(last).map_or_else(
            || Response::new(404),
            |b| Response::new(200).body(b.clone()),
        )
    })
}

fn client() -> Client {
    Client::with_loopback_http_for_tests(Box::new(Anonymous))
}

fn policy(namespace: &str, keys: &[&Key]) -> KeyPolicy {
    KeyPolicy {
        pinned: BTreeMap::from([(
            namespace.to_owned(),
            keys.iter().map(|k| k.public()).collect(),
        )]),
        ..KeyPolicy::default()
    }
}

fn lock_text(entries: &[String]) -> Lockfile {
    let mut text = String::from("schema_version = 3\n");
    for e in entries {
        text.push_str(e);
    }
    Lockfile::parse(&text).unwrap()
}

fn oci_entry(id: &str, registry: &str, digest: &str, key_id: &str) -> String {
    format!(
        "\n[[plugins]]\nid = \"{id}\"\nkind = \"data\"\nversion = \"1.2.0\"\nslopvac_api = 1\n\
         source = \"oci://{registry}/acme/style:1.2.0\"\ndigest = \"{digest}\"\n\n\
         [plugins.signature]\nkey_id = \"{key_id}\"\nnot_before = \"{NOT_BEFORE}\"\n"
    )
}

fn oci_lock(registry: &str, p: &Published) -> Lockfile {
    lock_text(&[oci_entry("style", registry, &p.digest, &p.key_id)])
}

struct Env {
    data: support::Scratch,
    project: support::Scratch,
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
            data: support::scratch(),
            project: support::scratch(),
            root,
            list: ListServer::start(Some(empty)),
        }
    }
    fn revocations(&self, now: &str) -> Revocations {
        Revocations::new(
            self.data.path().join("state"),
            vec![self.root.public()],
            self.list.source(),
            now,
        )
        .unwrap()
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
    fn store(&self) -> Store {
        Store::new(self.data.path().join("slopvac"))
    }
    fn assert_no_trees(&self) {
        let trees = self.trees();
        assert!(trees.is_empty(), "unexpected trees: {trees:?}");
    }
    fn trees(&self) -> Vec<PathBuf> {
        let dir = self.data.path().join("slopvac/trees");
        fs::read_dir(dir)
            .map(|rd| {
                rd.flatten()
                    .map(|e| e.path())
                    .filter(|p| {
                        p.file_name()
                            .is_some_and(|n| n.to_string_lossy().starts_with("tree-"))
                    })
                    .collect()
            })
            .unwrap_or_default()
    }
}

fn run(
    env: &Env,
    network: Network<'_>,
    policy: &KeyPolicy,
    lock: &Lockfile,
) -> Result<slopvac_plugins::sync::SyncReport, SyncError> {
    run_at(env, network, policy, lock, NOW)
}

fn run_at(
    env: &Env,
    network: Network<'_>,
    policy: &KeyPolicy,
    lock: &Lockfile,
    now: &str,
) -> Result<slopvac_plugins::sync::SyncReport, SyncError> {
    let store = env.store();
    let revs = env.revocations(now);
    Syncer::new(&store, network, policy, env.project.path(), &revs).sync(lock)
}

const FILES: &[(&str, &[u8])] = &[
    ("pack.toml", b"id = \"style\"\n"),
    ("rules/a.yml", b"rule: a\n"),
];

#[test]
fn sync_installs_exactly_the_locked_pack() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let report = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &oci_lock(&server.registry(), &p),
    )
    .unwrap();

    assert_eq!(report.packs.len(), 1);
    assert_eq!(report.packs[0].change, Change::Installed);
    let tree = &report.packs[0].tree;
    assert_eq!(fs::read(tree.join("rules/a.yml")).unwrap(), b"rule: a\n");
    assert_eq!(
        fs::read(tree.join("pack.toml")).unwrap(),
        b"id = \"style\"\n"
    );
    assert_eq!(env.trees(), vec![tree.clone()]);
    // The lock names the digest, so the manifest is fetched by digest and never by the tag.
    let by_tag = server.count("/v2/acme/style/manifests/1.2.0");
    assert_eq!(by_tag, 0);
    assert_eq!(
        server.count(&format!("/v2/acme/style/manifests/{}", p.digest)),
        1
    );
}

#[test]
fn a_registry_serving_other_content_for_the_locked_digest_installs_nothing() {
    let key = Key::new();
    let locked_pack = publish(&key, "acme", FILES);
    let forged = publish(&key, "acme", &[("pack.toml", b"evil\n")]);
    let server = registry(&[&forged]);
    let env = Env::new();
    let c = client();
    // The lock pins `locked_pack`, but the registry answers with the forged manifest.
    let lock = oci_lock(&server.registry(), &locked_pack);
    let err = run(&env, Network::Online(&c), &policy("acme", &[&key]), &lock).unwrap_err();
    assert!(
        matches!(
            err,
            SyncError::Fetch {
                source: OciError::DigestMismatch { .. },
                ..
            }
        ),
        "{err:?}"
    );
    assert_eq!(err.exit_code(), 2);
    env.assert_no_trees();
}

#[test]
fn a_fetch_failure_with_no_code_of_its_own_reports_sync_fetch() {
    let key = Key::new();
    let good = publish(&key, "acme", FILES);
    let server = registry(&[&good]);
    let env = Env::new();
    let c = client();
    let missing = format!("sha256:{}", "ab".repeat(32));
    let lock = lock_text(&[oci_entry(
        "style",
        &server.registry(),
        &missing,
        &good.key_id,
    )]);
    let err = run(&env, Network::Online(&c), &policy("acme", &[&key]), &lock).unwrap_err();
    assert!(matches!(err, SyncError::Fetch { .. }), "{err:?}");
    assert_eq!(err.code(), "sync-fetch");
    assert_eq!(err.exit_code(), 2);
}

#[test]
fn a_key_that_is_not_pinned_is_refused_and_nothing_is_extracted() {
    // TM-22: the artifact verifies against a key the user did not pin.
    let signer = Key::new();
    let pinned = Key::new();
    let p = publish(&signer, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&pinned]),
        &oci_lock(&server.registry(), &p),
    )
    .unwrap_err();
    assert!(
        matches!(
            err,
            SyncError::Sign {
                source: SignError::KeyNotPinned { .. },
                ..
            }
        ),
        "{err:?}"
    );
    assert_eq!(err.code(), "signature-invalid");
    env.assert_no_trees();
}

#[test]
fn a_first_party_namespace_fails_closed_without_compiled_keys() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let mut pol = policy("acme", &[&key]);
    pol.first_party_namespaces.push("acme".into());
    let err = run(
        &env,
        Network::Online(&c),
        &pol,
        &oci_lock(&server.registry(), &p),
    )
    .unwrap_err();
    assert!(
        matches!(
            err,
            SyncError::Sign {
                source: SignError::KeyNotPinned { .. },
                ..
            }
        ),
        "{err:?}"
    );
    env.assert_no_trees();
}

#[test]
fn a_lock_entry_without_a_signature_is_refused() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let mut entry = oci_entry("style", &server.registry(), &p.digest, &p.key_id);
    entry.truncate(entry.find("\n[plugins.signature]").unwrap());
    let env = Env::new();
    let c = client();
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &lock_text(&[entry]),
    )
    .unwrap_err();
    assert!(matches!(err, SyncError::Unsigned { .. }), "{err:?}");
    assert_eq!(server.requests().len(), 0, "nothing is fetched first");
}

#[test]
fn a_lock_entry_without_a_signature_reports_sync_unsigned() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let mut entry = oci_entry("style", &server.registry(), &p.digest, &p.key_id);
    entry.truncate(entry.find("\n[plugins.signature]").unwrap());
    let env = Env::new();
    let c = client();
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &lock_text(&[entry]),
    )
    .unwrap_err();
    assert_eq!(err.code(), "sync-unsigned");
    assert_eq!(err.exit_code(), 2);
}

#[test]
fn an_artifact_without_the_signature_its_lock_entry_records_reports_signature_invalid() {
    let key = Key::new();
    let stripped = publish_without_signature(&key, "acme", FILES);
    let server = registry(&[&stripped]);
    let env = Env::new();
    let c = client();
    // The lock entry records a signature; the registry serves the artifact without one.
    let lock = oci_lock(&server.registry(), &stripped);
    let err = run(&env, Network::Online(&c), &policy("acme", &[&key]), &lock).unwrap_err();
    assert!(
        matches!(
            err,
            SyncError::Sign {
                source: SignError::MissingSignature,
                ..
            }
        ),
        "{err:?}"
    );
    assert_eq!(err.code(), "signature-invalid");
    env.assert_no_trees();
}

#[test]
fn a_signature_that_differs_from_the_lock_still_reports_signature_invalid() {
    let locked_key = Key::new();
    let other = Key::new();
    let p = publish(&other, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let lock = lock_text(&[oci_entry(
        "style",
        &server.registry(),
        &p.digest,
        &locked_key.public().key_id(),
    )]);
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&locked_key, &other]),
        &lock,
    )
    .unwrap_err();
    assert!(
        matches!(err, SyncError::SignatureDiffersFromLock { .. }),
        "{err:?}"
    );
    assert_eq!(err.code(), "signature-invalid");
}

#[test]
fn a_signature_by_another_pinned_key_than_the_lock_records_is_refused() {
    let locked_key = Key::new();
    let other = Key::new();
    let p = publish(&other, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let lock = lock_text(&[oci_entry(
        "style",
        &server.registry(),
        &p.digest,
        &locked_key.public().key_id(),
    )]);
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&locked_key, &other]),
        &lock,
    )
    .unwrap_err();
    assert!(
        matches!(err, SyncError::SignatureDiffersFromLock { .. }),
        "{err:?}"
    );
    env.assert_no_trees();
}

#[test]
fn one_bad_pack_leaves_the_store_without_any_tree() {
    let key = Key::new();
    let good = publish(&key, "acme", FILES);
    let server = registry(&[&good]);
    let env = Env::new();
    let c = client();
    let missing = format!("sha256:{}", "ab".repeat(32));
    // `style` sorts first and would install before `z-bad` fails, if sync did not verify all first.
    let lock = lock_text(&[
        oci_entry("style", &server.registry(), &good.digest, &good.key_id),
        oci_entry("z-bad", &server.registry(), &missing, &good.key_id),
    ]);
    let err = run(&env, Network::Online(&c), &policy("acme", &[&key]), &lock).unwrap_err();
    assert!(matches!(err, SyncError::Fetch { .. }), "{err:?}");
    env.assert_no_trees();
}

#[test]
fn a_second_sync_changes_nothing_and_makes_no_request() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let pol = policy("acme", &[&key]);
    let lock = oci_lock(&server.registry(), &p);
    let first = run(&env, Network::Online(&c), &pol, &lock).unwrap();
    let requests = server.requests().len();
    let second = run(&env, Network::Online(&c), &pol, &lock).unwrap();
    assert_eq!(second.packs[0].change, Change::Unchanged);
    assert_eq!(second.packs[0].tree, first.packs[0].tree);
    assert_eq!(server.requests().len(), requests);
}

#[test]
fn offline_sync_from_a_warm_cache_succeeds_without_the_network() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let env = Env::new();
    let pol = policy("acme", &[&key]);
    let (lock, requests) = {
        let server = registry(&[&p]);
        let c = client();
        let lock = oci_lock(&server.registry(), &p);
        run(&env, Network::Online(&c), &pol, &lock).unwrap();
        (lock, server.requests().len())
    };
    assert!(requests > 0);
    // The trees are gone (for example a cleaned data dir), the downloads are not.
    slopvac_plugins::extract::evict(&env.data.path().join("slopvac/trees")).unwrap();
    fs::remove_dir_all(env.data.path().join("slopvac/refs")).unwrap();
    let report = run(&env, Network::Offline, &pol, &lock).unwrap();
    assert_eq!(report.packs[0].change, Change::Installed);
    assert_eq!(
        fs::read(report.packs[0].tree.join("rules/a.yml")).unwrap(),
        b"rule: a\n"
    );
}

#[test]
fn offline_sync_from_a_cold_cache_names_the_missing_pack_and_digest() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let env = Env::new();
    let lock = oci_lock("127.0.0.1:9", &p);
    let err = run(&env, Network::Offline, &policy("acme", &[&key]), &lock).unwrap_err();
    assert_eq!(err.code(), "offline-plugin-missing");
    assert_eq!(err.exit_code(), 2);
    let text = err.to_string();
    assert!(text.contains("style") && text.contains(&p.digest), "{text}");
    env.assert_no_trees();
}

#[test]
fn offline_sync_rechecks_a_cached_blob_and_refuses_a_swapped_one() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let env = Env::new();
    let pol = policy("acme", &[&key]);
    let server = registry(&[&p]);
    let c = client();
    let lock = oci_lock(&server.registry(), &p);
    run(&env, Network::Online(&c), &pol, &lock).unwrap();
    // Replace the downloaded manifest by other bytes under the same name.
    let blob = env
        .data
        .path()
        .join("slopvac/blobs")
        .join(p.digest.trim_start_matches("sha256:"));
    fs::write(&blob, b"{}").unwrap();
    let err = run(&env, Network::Offline, &pol, &lock).unwrap_err();
    assert_eq!(err.code(), "offline-plugin-missing", "{err:?}");
}

fn tamper_edit(tree: &Path) {
    let file = tree.join("rules/a.yml");
    let mut perms = fs::metadata(&file).unwrap().permissions();
    #[allow(clippy::permissions_set_readonly_false)]
    perms.set_readonly(false);
    fs::set_permissions(&file, perms).unwrap();
    fs::write(&file, b"rule: evil\n").unwrap();
}

#[cfg(unix)]
fn tamper_add(tree: &Path) {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(tree, fs::Permissions::from_mode(0o755)).unwrap();
    fs::write(tree.join("extra.yml"), b"x").unwrap();
}

#[cfg(not(unix))]
fn tamper_add(tree: &Path) {
    fs::write(tree.join("extra.yml"), b"x").unwrap();
}

#[test]
fn a_tampered_tree_is_reinstalled_online() {
    // TM-46: edit a file; add a file.
    for tamper in [tamper_edit as fn(&Path), tamper_add] {
        let key = Key::new();
        let p = publish(&key, "acme", FILES);
        let server = registry(&[&p]);
        let env = Env::new();
        let c = client();
        let pol = policy("acme", &[&key]);
        let lock = oci_lock(&server.registry(), &p);
        let first = run(&env, Network::Online(&c), &pol, &lock).unwrap();
        let tree = first.packs[0].tree.clone();
        tamper(&tree);
        let states = status(&env.store(), env.project.path(), &lock).unwrap();
        assert!(
            matches!(states[0].state, PackState::Tampered(_)),
            "{states:?}"
        );

        let again = run(&env, Network::Online(&c), &pol, &lock).unwrap();
        assert_eq!(again.packs[0].change, Change::Reinstalled);
        assert_eq!(fs::read(tree.join("rules/a.yml")).unwrap(), b"rule: a\n");
        assert!(!tree.join("extra.yml").exists());
        let states = status(&env.store(), env.project.path(), &lock).unwrap();
        assert!(states[0].is_recorded(), "{states:?}");
    }
}

#[test]
fn a_tampered_tree_is_refused_offline_and_removed() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let pol = policy("acme", &[&key]);
    let lock = oci_lock(&server.registry(), &p);
    let first = run(&env, Network::Online(&c), &pol, &lock).unwrap();
    tamper_edit(&first.packs[0].tree);
    let err = run(&env, Network::Offline, &pol, &lock).unwrap_err();
    assert!(matches!(err, SyncError::CacheTampered { .. }), "{err:?}");
    assert_eq!(err.exit_code(), 2);
    env.assert_no_trees();
}

#[test]
fn status_reports_missing_then_installed() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let lock = oci_lock(&server.registry(), &p);
    let before = status(&env.store(), env.project.path(), &lock).unwrap();
    assert_eq!(before[0].state, PackState::NotInstalled);
    assert!(!before[0].is_recorded());
    let report = run(&env, Network::Online(&c), &policy("acme", &[&key]), &lock).unwrap();
    let after = status(&env.store(), env.project.path(), &lock).unwrap();
    assert_eq!(
        after[0].state,
        PackState::Recorded(report.packs[0].tree.clone())
    );
}

fn path_archive_entry(digest: &str) -> String {
    format!(
        "\n[[plugins]]\nid = \"style\"\nkind = \"data\"\nversion = \"1.2.0\"\nslopvac_api = 1\n\
         source = \"dist/style.tar.gz\"\ndigest = \"{digest}\"\n"
    )
}

#[test]
fn a_path_archive_is_installed_by_its_digest_and_cached_for_offline_use() {
    let env = Env::new();
    let archive = targz(FILES);
    fs::create_dir_all(env.project.path().join("dist")).unwrap();
    fs::write(env.project.path().join("dist/style.tar.gz"), &archive).unwrap();
    let lock = lock_text(&[path_archive_entry(&Digest::of(&archive).to_string())]);
    let pol = KeyPolicy::default();
    let report = run(&env, Network::Offline, &pol, &lock).unwrap();
    assert_eq!(report.packs[0].change, Change::Installed);
    assert_eq!(
        fs::read(report.packs[0].tree.join("rules/a.yml")).unwrap(),
        b"rule: a\n"
    );
}

#[test]
fn a_path_archive_that_does_not_match_the_lock_digest_installs_nothing() {
    let env = Env::new();
    fs::create_dir_all(env.project.path().join("dist")).unwrap();
    fs::write(env.project.path().join("dist/style.tar.gz"), targz(FILES)).unwrap();
    let lock = lock_text(&[path_archive_entry(&format!("sha256:{}", "00".repeat(32)))]);
    let err = run(&env, Network::Offline, &KeyPolicy::default(), &lock).unwrap_err();
    assert_eq!(err.code(), "digest-mismatch");
    env.assert_no_trees();
}

#[test]
fn download_reads_up_to_the_limit_and_production_clients_refuse_http() {
    let server = Server::start(|_| Response::new(200).body(vec![7u8; 100]));
    let url = format!("http://{}/a.tar.gz", server.registry());
    let mut out = Vec::new();
    client().download(&url, 100, &mut out).unwrap();
    assert_eq!(out.len(), 100);
    let err = client().download(&url, 99, &mut Vec::new()).unwrap_err();
    assert!(
        matches!(err, OciError::TooLarge { limit: 99, .. }),
        "{err:?}"
    );
    let err = Client::new(std::env::temp_dir())
        .download(&url, 100, &mut Vec::new())
        .unwrap_err();
    assert!(matches!(err, OciError::InsecureUrl(_)), "{err:?}");
}

#[test]
fn a_path_source_directory_is_checked_by_tree_hash_and_used_in_place() {
    let env = Env::new();
    let dir = env.project.path().join("packs/local");
    fs::create_dir_all(dir.join("rules")).unwrap();
    fs::write(dir.join("pack.toml"), b"id = \"local\"\n").unwrap();
    fs::write(dir.join("rules/a.yml"), b"rule: a\n").unwrap();
    let hash = slopvac_plugins::extract::tree_hash(&dir).unwrap();
    let entry = |digest: &str| {
        format!(
            "\n[[plugins]]\nid = \"local\"\nkind = \"data\"\nversion = \"0.0.1\"\nslopvac_api = 1\n\
             source = \"packs/local\"\ndigest = \"{digest}\"\n"
        )
    };
    let pol = KeyPolicy::default();
    let lock = lock_text(&[entry(hash.as_str())]);
    let report = run(&env, Network::Offline, &pol, &lock).unwrap();
    assert_eq!(report.packs[0].change, Change::InPlace);
    assert_eq!(report.packs[0].tree, dir);
    let states = status(&env.store(), env.project.path(), &lock).unwrap();
    assert_eq!(states[0].state, PackState::InPlace(dir.clone()));

    fs::write(dir.join("rules/a.yml"), b"rule: changed\n").unwrap();
    let err = run(&env, Network::Offline, &pol, &lock).unwrap_err();
    assert_eq!(err.code(), "digest-mismatch");
    let states = status(&env.store(), env.project.path(), &lock).unwrap();
    assert_eq!(states[0].state, PackState::InPlaceChanged(dir));
}

fn resolved(id: &str, version: &str, digest: &str) -> ResolvedPack {
    ResolvedPack {
        id: id.parse().unwrap(),
        version: version.parse().unwrap(),
        source: "oci://ghcr.io/acme/style:1.2.0".parse::<Source>().unwrap(),
        digest: digest.parse().unwrap(),
    }
}

#[test]
fn ci_check_passes_on_a_match_and_exits_2_on_a_mismatch() {
    let digest = format!("sha256:{}", "ab".repeat(32));
    let lock = lock_text(&[oci_entry("style", "ghcr.io", &digest, "A1B2C3D4E5F60718")]);
    assert!(check_lock(&lock, &[resolved("style", "1.2.0", &digest)]).is_ok());

    let other = format!("sha256:{}", "cd".repeat(32));
    let err = check_lock(&lock, &[resolved("style", "1.2.0", &other)]).unwrap_err();
    assert_eq!(err.exit_code(), 2);
    assert_eq!(err.code(), "lock-mismatch");
    let text = err.to_string();
    assert!(
        text.contains(&format!("digest {digest} -> {other}")),
        "{text}"
    );
}

#[test]
fn update_notices_separate_in_range_updates_from_out_of_range_releases() {
    let digest = format!("sha256:{}", "ab".repeat(32));
    let lock = lock_text(&[oci_entry("style", "ghcr.io", &digest, "A1B2C3D4E5F60718")]);
    let id: PackId = "style".parse().unwrap();
    let ranges = BTreeMap::from([(id.clone(), parse_version_req("^1").unwrap())]);
    let v = |s: &str| s.parse::<Version>().unwrap();
    let available = BTreeMap::from([(id.clone(), vec![v("1.2.0"), v("1.3.0"), v("2.0.0")])]);
    assert_eq!(
        update_notices(&lock, &ranges, &available),
        vec![
            "plugin style: 1.3.0 is available (locked 1.2.0); run `slopvac plugins update`",
            "plugin style: 2.0.0 is available but outside the configured range; change the range to use it",
        ]
    );
    let none: BTreeMap<PackId, VersionReq> = BTreeMap::new();
    assert_eq!(
        update_notices(&lock, &none, &available),
        Vec::<String>::new()
    );
}

#[test]
fn available_versions_lists_semver_tags_in_order() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let c = client();
    let repo = Reference::parse(&format!("{}/acme/style:1.2.0", server.registry())).unwrap();
    let got: Vec<String> = available_versions(&c, &repo)
        .unwrap()
        .iter()
        .map(ToString::to_string)
        .collect();
    assert_eq!(got, ["1.0.0", "1.2.0", "1.3.0", "2.0.0-rc.1"]);
}
// ---- review round 1 ----

fn archive_entry(id: &str, url: &str, digest: &str) -> String {
    format!(
        "\n[[plugins]]\nid = \"{id}\"\nkind = \"data\"\nversion = \"1.2.0\"\nslopvac_api = 1\n\
         source = \"{url}\"\ndigest = \"{digest}\"\n"
    )
}

/// Write `files` as `dist/<name>.tar.gz` in the project and return its lock entry.
fn local_archive(env: &Env, id: &str, files: &[(&str, &[u8])]) -> String {
    let bytes = targz(files);
    fs::create_dir_all(env.project.path().join("dist")).unwrap();
    fs::write(env.project.path().join(format!("dist/{id}.tar.gz")), &bytes).unwrap();
    archive_entry(
        id,
        &format!("dist/{id}.tar.gz"),
        &Digest::of(&bytes).to_string(),
    )
}

/// A lock whose one plugin pack has `source` and a placeholder digest.
fn git_pin_lock(source: &str) -> String {
    format!(
        "schema_version = 3\n\n[[plugins]]\nid = \"tagger\"\nkind = \"code\"\n\
         version = \"0.3.1\"\nslopvac_api = 1\nsource = \"{source}\"\n\
         digest = \"sha256:{}\"\n",
        "00".repeat(32)
    )
}

#[test]
fn tm31_a_full_lowercase_commit_hash_is_accepted_as_a_git_pin() {
    let pinned = "0123456789abcdef0123456789abcdef01234567";
    let lock = git_pin_lock(&format!("git+https://github.com/acme/tagger@{pinned}"));
    assert!(Lockfile::parse(&lock).is_ok(), "the control lock parses");
}

/// Each pin is not a full lowercase 40-digit commit hash.
#[rstest]
#[case::branch("main")]
#[case::tag("v1.2.0")]
#[case::head("HEAD")]
#[case::short_hash("0123456")]
#[case::thirty_nine_digits("0123456789abcdef0123456789abcdef0123456")]
#[case::forty_one_digits("0123456789abcdef0123456789abcdef012345670")]
#[case::uppercase("0123456789ABCDEF0123456789ABCDEF01234567")]
fn tm31_a_branch_or_short_name_is_refused_as_a_git_pin(#[case] pin: &str) {
    let err = Lockfile::parse(&git_pin_lock(&format!(
        "git+https://github.com/acme/tagger@{pin}"
    )))
    .unwrap_err();
    assert_eq!(err.pointer, "/plugins/0/source", "{pin}: {err}");
}

#[cfg(unix)]
#[test]
fn a_planted_trees_link_cannot_redirect_extraction_outside_the_store() {
    // CWE-59: `trees` is a link to a directory the attacker chose.
    let env = Env::new();
    let outside = support::scratch();
    fs::create_dir_all(env.data.path().join("slopvac")).unwrap();
    std::os::unix::fs::symlink(outside.path(), env.data.path().join("slopvac/trees")).unwrap();
    let lock = lock_text(&[local_archive(&env, "style", FILES)]);
    let err = run(&env, Network::Offline, &KeyPolicy::default(), &lock).unwrap_err();
    assert!(matches!(err, SyncError::Store(_)), "{err:?}");
    let entries: Vec<_> = fs::read_dir(outside.path()).unwrap().flatten().collect();
    assert!(entries.is_empty(), "wrote outside the store: {entries:?}");
}

#[cfg(unix)]
#[test]
fn a_path_source_through_a_link_is_refused() {
    let env = Env::new();
    let outside = support::scratch();
    fs::write(outside.path().join("pack.toml"), b"x").unwrap();
    fs::create_dir_all(env.project.path().join("plugins")).unwrap();
    std::os::unix::fs::symlink(outside.path(), env.project.path().join("plugins/link")).unwrap();
    let lock = lock_text(&[format!(
        "\n[[plugins]]\nid = \"local\"\nkind = \"data\"\nversion = \"0.0.1\"\nslopvac_api = 1\n\
         source = \"plugins/link\"\ndigest = \"sha256:{}\"\n",
        "00".repeat(32)
    )]);
    let err = run(&env, Network::Offline, &KeyPolicy::default(), &lock).unwrap_err();
    assert!(matches!(err, SyncError::Source { .. }), "{err:?}");
}

#[test]
fn a_second_sync_waits_for_the_store_lock_and_then_sees_the_first_result() {
    // E9: one process holds the store; another sync must not run in between.
    let env = Env::new();
    let lock = lock_text(&[local_archive(&env, "style", FILES)]);
    let store = env.store();
    let held = store.lock().unwrap();
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::scope(|scope| {
        scope.spawn(|| {
            let pol = KeyPolicy::default();
            let revs = env.revocations(NOW);
            let report = Syncer::new(&store, Network::Offline, &pol, env.project.path(), &revs)
                .sync(&lock)
                .unwrap();
            tx.send(report.packs[0].change.clone()).unwrap();
        });
        assert!(
            rx.recv_timeout(std::time::Duration::from_millis(400))
                .is_err(),
            "sync ran while the store lock was held"
        );
        drop(held);
        let change = rx.recv_timeout(std::time::Duration::from_secs(20)).unwrap();
        assert_eq!(change, Change::Installed);
    });
}

#[test]
fn concurrent_syncs_of_one_store_all_succeed_with_an_intact_tree() {
    let env = Env::new();
    let lock = lock_text(&[local_archive(&env, "style", FILES)]);
    let store = env.store();
    let pol = KeyPolicy::default();
    let revs = env.revocations(NOW);
    let changes: Vec<Change> = std::thread::scope(|scope| {
        let handles: Vec<_> = (0..4)
            .map(|_| {
                scope.spawn(|| {
                    Syncer::new(&store, Network::Offline, &pol, env.project.path(), &revs)
                        .sync(&lock)
                        .unwrap()
                        .packs[0]
                        .change
                        .clone()
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).collect()
    });
    let count = |wanted: Change| changes.iter().filter(|c| **c == wanted).count();
    assert_eq!(count(Change::Installed), 1, "{changes:?}");
    assert_eq!(count(Change::Unchanged), 3, "{changes:?}");
    let states = status(&store, env.project.path(), &lock).unwrap();
    assert!(states[0].is_recorded(), "{states:?}");
}

fn https_archive_lock(server: &Server, digest: &str) -> Lockfile {
    lock_text(&[archive_entry(
        "style",
        &format!("https://{}/p/style-1.2.0.tar.gz", server.registry()),
        digest,
    )])
}

#[test]
fn an_https_archive_is_downloaded_checked_installed_and_replayed_from_cache() {
    let archive = targz(FILES);
    let digest = Digest::of(&archive).to_string();
    let env = Env::new();
    let pol = KeyPolicy::default();
    let (lock, requests) = {
        let body = archive.clone();
        let server = Server::start(move |_| Response::new(200).body(body.clone()));
        let lock = https_archive_lock(&server, &digest);
        let c = client();
        let report = run(&env, Network::Online(&c), &pol, &lock).unwrap();
        assert_eq!(report.packs[0].change, Change::Installed);
        assert_eq!(
            fs::read(report.packs[0].tree.join("rules/a.yml")).unwrap(),
            b"rule: a\n"
        );
        (lock, server.requests().len())
    };
    assert_eq!(requests, 1);
    // The trees are removed and the server is not consulted: the cached download is enough.
    slopvac_plugins::extract::evict(&env.data.path().join("slopvac/trees")).unwrap();
    let again = run(&env, Network::Offline, &pol, &lock).unwrap();
    assert_eq!(again.packs[0].change, Change::Installed);
}

#[test]
fn an_https_archive_with_the_wrong_digest_installs_and_caches_nothing() {
    let archive = targz(FILES);
    let server = Server::start(move |_| Response::new(200).body(archive.clone()));
    let env = Env::new();
    let c = client();
    let pol = KeyPolicy::default();
    let wrong = format!("sha256:{}", "00".repeat(32));
    let lock = https_archive_lock(&server, &wrong);
    let err = run(&env, Network::Online(&c), &pol, &lock).unwrap_err();
    assert_eq!(err.code(), "digest-mismatch", "{err:?}");
    env.assert_no_trees();
    // Nothing was cached either: an offline run finds the pack missing.
    let err = run(&env, Network::Offline, &pol, &lock).unwrap_err();
    assert_eq!(err.code(), "offline-plugin-missing", "{err:?}");
}

#[test]
fn an_edited_record_cannot_make_sync_keep_another_tree() {
    // The record for `a` is rewritten to point at the intact tree of `b`.
    let env = Env::new();
    let lock = lock_text(&[
        local_archive(&env, "a", &[("pack.toml", b"a\n")]),
        local_archive(&env, "b", &[("pack.toml", b"b\n")]),
    ]);
    let pol = KeyPolicy::default();
    let first = run(&env, Network::Offline, &pol, &lock).unwrap();
    let (tree_a, tree_b) = (first.packs[0].tree.clone(), first.packs[1].tree.clone());
    let digest_a = lock.packs()[0].digest.to_string();
    let record = env
        .data
        .path()
        .join("slopvac/refs")
        .join(digest_a.trim_start_matches("sha256:"));
    let name_b = tree_b.file_name().unwrap().to_string_lossy().into_owned();
    fs::write(record, name_b.trim_start_matches("tree-")).unwrap();

    // Status only checks the record, and says so by name.
    let states = status(&env.store(), env.project.path(), &lock).unwrap();
    assert_eq!(states[0].state, PackState::Recorded(tree_b));

    // Sync re-derives the tree from the verified download.
    let again = run(&env, Network::Offline, &pol, &lock).unwrap();
    assert_eq!(again.packs[0].tree, tree_a);
    assert_eq!(again.packs[0].change, Change::Installed);
    let states = status(&env.store(), env.project.path(), &lock).unwrap();
    assert_eq!(states[0].state, PackState::Recorded(tree_a));
}

#[cfg(unix)]
#[test]
fn a_tampered_tree_too_large_to_delete_is_reported_as_quarantined_online() {
    use std::os::unix::fs::PermissionsExt;
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let pol = policy("acme", &[&key]);
    let lock = oci_lock(&server.registry(), &p);
    let first = run(&env, Network::Online(&c), &pol, &lock).unwrap();
    let tree = first.packs[0].tree.clone();
    // More than 20 000 nodes: past the bound the extractor never walks.
    fs::set_permissions(&tree, fs::Permissions::from_mode(0o755)).unwrap();
    let crowd = tree.join("crowd");
    fs::create_dir(&crowd).unwrap();
    for i in 0..20_001 {
        fs::write(crowd.join(format!("f{i}")), b"").unwrap();
    }
    let again = run(&env, Network::Online(&c), &pol, &lock).unwrap();
    assert_eq!(again.packs[0].change, Change::Reinstalled);
    let aside = again.packs[0].quarantined.clone().expect("quarantine path");
    assert!(aside.exists(), "{}", aside.display());
}
#[test]
fn a_signature_newer_than_the_one_the_lock_records_is_refused() {
    // Valid, pinned and newer than the lock's floor, so the verifier accepts it;
    // sync still installs only the signature the lock recorded.
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let entry = oci_entry("style", &server.registry(), &p.digest, &p.key_id)
        .replace(NOT_BEFORE, "2026-10-01T00:00:00Z");
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &lock_text(&[entry]),
    )
    .unwrap_err();
    assert!(
        matches!(err, SyncError::SignatureDiffersFromLock { .. }),
        "{err:?}"
    );
    assert_eq!(err.exit_code(), 2);
    env.assert_no_trees();
}
// ---- Revocation (threat model K5, K6; TM-26, TM-27) ----

#[test]
fn tm26_a_revoked_manifest_digest_fails_sync_before_any_request_for_it() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    env.revoke(&[], &[&p.digest]);
    let c = client();
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &oci_lock(&server.registry(), &p),
    )
    .unwrap_err();
    assert!(matches!(err, SyncError::Revoked { .. }), "{err:?}");
    assert_eq!(err.exit_code(), 2);
    assert_eq!(err.code(), "plugin-revoked");
    assert_eq!(server.requests().len(), 0);
    env.assert_no_trees();
}

#[test]
fn tm26_a_revoked_signing_key_fails_sync_and_extracts_nothing() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    env.revoke(&[&p.key_id], &[]);
    let c = client();
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &oci_lock(&server.registry(), &p),
    )
    .unwrap_err();
    assert!(matches!(err, SyncError::Revoked { .. }), "{err:?}");
    assert_eq!(err.exit_code(), 2);
    env.assert_no_trees();
}

#[test]
fn tm26_a_revocation_published_after_install_fails_the_next_sync() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let pol = policy("acme", &[&key]);
    let lock = oci_lock(&server.registry(), &p);
    run(&env, Network::Online(&c), &pol, &lock).unwrap();
    env.revoke(&[], &[&p.digest]);
    // Offline reads the cache, which still holds the old list (residual risk R3).
    run(&env, Network::Offline, &pol, &lock).unwrap();
    let err = run(&env, Network::Online(&c), &pol, &lock).unwrap_err();
    assert!(matches!(err, SyncError::Revoked { .. }), "{err:?}");
    // The online run cached the new list, so offline now refuses too.
    let err = run(&env, Network::Offline, &pol, &lock).unwrap_err();
    assert!(matches!(err, SyncError::Revoked { .. }), "{err:?}");
}

#[test]
fn a_list_that_names_other_artifacts_installs_normally() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let other = Digest::of(b"other").to_string();
    env.revoke(&["0000000000000000"], &[&other]);
    let c = client();
    let report = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &oci_lock(&server.registry(), &p),
    )
    .unwrap();
    assert_eq!(report.packs[0].change, Change::Installed);
    assert_eq!(report.notices, vec![]);
}

#[test]
fn tm27_a_forged_list_fails_online_sync_with_exit_2() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    env.list.serve(Some(Signed::by(
        &Root::new(),
        list_json("2026-11-10T00:00:00Z", "2026-12-10T00:00:00Z", &[], &[]),
    )));
    let c = client();
    let err = run(
        &env,
        Network::Online(&c),
        &policy("acme", &[&key]),
        &oci_lock(&server.registry(), &p),
    )
    .unwrap_err();
    assert!(
        matches!(err, SyncError::Revocation(RevocationError::BadSignature)),
        "{err:?}"
    );
    assert_eq!(err.exit_code(), 2);
    assert_eq!(err.code(), "revocation-list-invalid");
    env.assert_no_trees();
}

#[test]
fn tm27_a_stale_cache_offline_prints_a_notice_and_the_sync_runs() {
    let key = Key::new();
    let p = publish(&key, "acme", FILES);
    let server = registry(&[&p]);
    let env = Env::new();
    let c = client();
    let pol = policy("acme", &[&key]);
    let lock = oci_lock(&server.registry(), &p);
    run(&env, Network::Online(&c), &pol, &lock).unwrap();
    // NOW plus 31 days.
    let report = run_at(&env, Network::Offline, &pol, &lock, "2026-12-15T00:00:00Z").unwrap();
    assert_eq!(report.packs[0].change, Change::Unchanged);
    let codes: Vec<&str> = report.notices.iter().map(RevocationNotice::code).collect();
    assert_eq!(codes, vec!["revocation-list-stale"]);
}

#[test]
fn an_offline_sync_that_never_fetched_a_list_runs_with_a_notice() {
    let env = Env::new();
    let lock = lock_text(&[local_archive(&env, "style", FILES)]);
    let report = run(&env, Network::Offline, &KeyPolicy::default(), &lock).unwrap();
    let codes: Vec<&str> = report.notices.iter().map(RevocationNotice::code).collect();
    assert_eq!(codes, vec!["revocation-list-missing"]);
}

#[test]
fn k6_an_online_sync_fails_when_the_list_is_withheld() {
    let env = Env::new();
    env.list.serve(None);
    let lock = lock_text(&[local_archive(&env, "style", FILES)]);
    let c = client();
    let err = run(&env, Network::Online(&c), &KeyPolicy::default(), &lock).unwrap_err();
    assert!(
        matches!(err, SyncError::Revocation(RevocationError::Fetch(_))),
        "{err:?}"
    );
    assert_eq!(err.exit_code(), 2);
    env.assert_no_trees();
}

#[test]
fn k6_an_online_sync_fails_when_the_served_list_has_expired() {
    let env = Env::new();
    // The empty list the source serves expires 2026-12-01.
    let lock = lock_text(&[local_archive(&env, "style", FILES)]);
    let c = client();
    let err = run_at(
        &env,
        Network::Online(&c),
        &KeyPolicy::default(),
        &lock,
        "2026-12-01T00:00:01Z",
    )
    .unwrap_err();
    assert!(
        matches!(err, SyncError::Revocation(RevocationError::Expired { .. })),
        "{err:?}"
    );
    assert_eq!(err.exit_code(), 2);
    env.assert_no_trees();
}
/// Failures at the I/O boundary of a store whose path holds a soft hyphen, a
/// literal backslash and a legacy runner command. The message must show each of
/// them escaped once: a second escape would turn `\u{ad}` into `\\u{ad}`.
#[cfg(unix)]
mod io_boundary {
    use std::os::unix::fs::PermissionsExt;

    use super::*;

    /// The store root's last component, and how a message shows it.
    const ROOT_NAME: &str = "s\u{ad}\\n##[e]";
    const ROOT_SHOWN: &str = "s\\u{ad}\\\\n\\u{23}#[e]";

    struct Installed {
        env: Env,
        store: Store,
        lock: Lockfile,
        pol: KeyPolicy,
        tree: PathBuf,
        _server: Server,
    }

    fn installed() -> Installed {
        let key = Key::new();
        let p = publish(&key, "acme", FILES);
        let server = registry(&[&p]);
        let env = Env::new();
        let store = Store::new(env.data.path().join(ROOT_NAME));
        let c = client();
        let pol = policy("acme", &[&key]);
        let lock = oci_lock(&server.registry(), &p);
        let revs = env.revocations(NOW);
        let report = Syncer::new(&store, Network::Online(&c), &pol, env.project.path(), &revs)
            .sync(&lock)
            .unwrap();
        let tree = report.packs[0].tree.clone();
        Installed {
            env,
            store,
            lock,
            pol,
            tree,
            _server: server,
        }
    }

    fn sync_offline(i: &Installed) -> SyncError {
        let revs = i.env.revocations(NOW);
        Syncer::new(
            &i.store,
            Network::Offline,
            &i.pol,
            i.env.project.path(),
            &revs,
        )
        .sync(&i.lock)
        .unwrap_err()
    }

    #[test]
    fn an_unreadable_file_with_a_hostile_name_is_escaped_once_by_inspect_and_sync() {
        let i = installed();
        fs::set_permissions(&i.tree, fs::Permissions::from_mode(0o755)).unwrap();
        // The soft hyphen and `##[` pass the name check; the open fails.
        let planted = i.tree.join("a\u{ad}b##[x]");
        fs::write(&planted, b"x").unwrap();
        fs::set_permissions(&planted, fs::Permissions::from_mode(0o000)).unwrap();
        if fs::File::open(&planted).is_ok() {
            return; // running as root: mode 000 does not stop the read
        }
        let want =
            "data directory: reading `a\\u{ad}b\\u{23}#[x]`: Permission denied (os error 13)";
        let direct = i.store.inspect(&i.lock.packs()[0].digest).unwrap_err();
        assert_eq!(direct.to_string(), want);
        assert_eq!(sync_offline(&i).to_string(), want);
    }

    #[test]
    fn a_tree_that_cannot_be_removed_names_its_hostile_path_escaped_once() {
        let i = installed();
        // A regular file where the tree directory belongs: verification calls it
        // tampered, and removing it as a directory fails with ENOTDIR.
        let trees = i.tree.parent().unwrap().to_owned();
        // The tree is installed sealed (read-only); some systems refuse to move a
        // read-only directory, so unseal it and its parent first.
        for dir in [&i.tree, &trees] {
            fs::set_permissions(dir, fs::Permissions::from_mode(0o700)).unwrap();
        }
        fs::rename(&i.tree, trees.join("moved")).unwrap();
        fs::write(&i.tree, b"x").unwrap();
        let msg = sync_offline(&i).to_string();
        let name = i.tree.file_name().unwrap().to_string_lossy().into_owned();
        let tail = format!("/{ROOT_SHOWN}/trees/{name}: Not a directory (os error 20)");
        assert!(msg.starts_with("data directory: removing "), "{msg}");
        assert!(msg.ends_with(&tail), "{msg}");
    }
}

/// Managed Python environments (bead 8l4.9.34), built with a scripted fake uv.
#[cfg(unix)]
mod python {
    use std::os::unix::fs::PermissionsExt;

    use super::*;
    use crate::common::fake_uv::{Fake, fake_uv};
    use slopvac_plugins::extract::{TreeHash, tree_hash};
    use slopvac_plugins::pyenv::{EnvStore, PyEnvError};
    use slopvac_plugins::sync::{PythonBuild, PythonState, status_with_python};

    const PLUGIN_MANIFEST: &str = "schema_version = 3\nid = \"py\"\nversion = \"1.0.0\"\nslopvac_api = 1\nkind = \"code\"\n\n[plugin]\ncommand = \"plugin.py\"\nruntime = \"python\"\npython = \"3.12\"\nnetwork = false\nhooks = []\nfeatures = { required = [], optional = [] }\n";
    const EMPTY_LOCK: &str = "lock-version = \"1.0\"\ncreated-by = \"test\"\n";

    /// A project with one in-place pack `py`, a fake uv and an environment store.
    struct Setup {
        env: Env,
        hash: TreeHash,
        lock: Lockfile,
        uv: PathBuf,
        envs: EnvStore,
    }

    impl Setup {
        fn new(fake: &Fake<'_>, files: &[(&str, &str)]) -> Self {
            let env = Env::new();
            let dir = env.project.path().join("packs/py");
            fs::create_dir_all(&dir).unwrap();
            for (name, text) in files {
                fs::write(dir.join(name), text).unwrap();
            }
            let hash = tree_hash(&dir).unwrap();
            let lock = lock_text(&[format!(
                "\n[[plugins]]\nid = \"py\"\nkind = \"code\"\nversion = \"1.0.0\"\nslopvac_api = 1\n\
                 source = \"packs/py\"\ndigest = \"{hash}\"\n"
            )]);
            let uv = fake_uv(&env.data.path().join("uv-bin"), fake);
            let envs = EnvStore::open(env.data.path().join("envs"));
            Self {
                env,
                hash,
                lock,
                uv,
                envs,
            }
        }

        fn python(files: &[(&str, &str)]) -> Self {
            Self::new(&Fake::real(), files)
        }

        fn build(&self) -> PythonBuild<'_> {
            PythonBuild {
                envs: &self.envs,
                uv: &self.uv,
                python_install_dir: Path::new("/nonexistent/uv-python"),
            }
        }

        fn sync(
            &self,
            network: Network<'_>,
            with_python: bool,
        ) -> Result<slopvac_plugins::sync::SyncReport, SyncError> {
            let (store, revs) = (self.env.store(), self.env.revocations(NOW));
            let pol = KeyPolicy::default();
            let syncer = Syncer::new(&store, network, &pol, self.env.project.path(), &revs);
            let syncer = if with_python {
                syncer.with_python(self.build())
            } else {
                syncer
            };
            syncer.sync(&self.lock)
        }

        fn uv_log(&self) -> String {
            fs::read_to_string(self.env.data.path().join("uv-bin/uv.log")).unwrap_or_default()
        }
    }

    const PLUGIN_FILES: [(&str, &str); 3] = [
        ("slopvac-plugin.toml", PLUGIN_MANIFEST),
        ("plugin.py", "print('plugin')\n"),
        ("pylock.toml", EMPTY_LOCK),
    ];

    #[test]
    fn sync_and_status_find_a_manifest_under_the_name_the_contract_gives() {
        // The literal file name from docs/contract/plugins.md, not the reader's constant.
        let t = Setup::python(&[
            ("slopvac-plugin.toml", PLUGIN_MANIFEST),
            ("plugin.py", "print('plugin')\n"),
            ("pylock.toml", EMPTY_LOCK),
        ]);
        let report = t.sync(Network::Offline, true).unwrap();
        let key = EnvStore::key(&t.hash, "3.12");
        assert_eq!(report.packs[0].python_env, Some(key.clone()));
        assert_eq!(python_states(&t), [PythonState::Verified(key)]);
    }

    #[test]
    fn sync_builds_the_manifest_selected_environment_without_the_network() {
        // The fake exits 99 on any uv call that could download.
        let t = Setup::new(
            &Fake {
                offline_only: true,
                ..Fake::real()
            },
            &PLUGIN_FILES,
        );
        let report = t.sync(Network::Offline, true).unwrap();
        assert_eq!(
            report.packs[0].python_env,
            Some(EnvStore::key(&t.hash, "3.12"))
        );
        assert!(t.envs.load(&t.hash, "3.12").unwrap().is_some());
        assert!(t.uv_log().contains("ARGS venv"), "uv built the environment");
    }

    #[test]
    fn sync_passes_uv_the_pep_440_form_of_a_semver_requirement() {
        let caret = PLUGIN_MANIFEST.replace("python = \"3.12\"", "python = \"^3.12\"");
        let t = Setup::python(&[
            ("slopvac-plugin.toml", caret.as_str()),
            ("plugin.py", "print('plugin')\n"),
            ("pylock.toml", EMPTY_LOCK),
        ]);
        let report = t.sync(Network::Offline, true).unwrap();
        let log = t.uv_log();
        assert!(
            log.contains("--python >=3.12,<4\n") || log.contains("--python >=3.12,<4 "),
            "{log}"
        );
        assert!(!log.contains("^3.12"), "{log}");
        let key = EnvStore::key(&t.hash, ">=3.12,<4");
        assert_eq!(report.packs[0].python_env, Some(key.clone()));
        // Status finds the same environment, and a second sync reuses it.
        assert_eq!(python_states(&t), [PythonState::Verified(key)]);
        t.sync(Network::Offline, true).unwrap();
        assert_eq!(t.uv_log(), log, "uv ran again");
    }

    #[test]
    fn a_repeated_sync_keeps_a_sound_environment() {
        let t = Setup::python(&PLUGIN_FILES);
        t.sync(Network::Offline, true).unwrap();
        let after_first = t.uv_log();
        assert_ne!(after_first, "");
        t.sync(Network::Offline, true).unwrap();
        assert_eq!(t.uv_log(), after_first, "uv ran again");
    }

    #[test]
    fn sync_builds_no_environment_for_a_pack_that_is_not_a_python_plugin() {
        let data_manifest = "schema_version = 3\nid = \"py\"\nversion = \"1.0.0\"\nslopvac_api = 1\nkind = \"data\"\n";
        let t = Setup::python(&[("slopvac-plugin.toml", data_manifest)]);
        let report = t.sync(Network::Offline, true).unwrap();
        assert_eq!(report.packs[0].python_env, None);
        assert_eq!(t.uv_log(), "");
    }

    #[test]
    fn sync_without_a_python_build_configured_builds_nothing() {
        let t = Setup::python(&PLUGIN_FILES);
        let report = t.sync(Network::Offline, false).unwrap();
        assert_eq!(report.packs[0].python_env, None);
        assert_eq!(t.uv_log(), "");
    }

    #[test]
    fn a_failed_environment_build_fails_the_sync() {
        let sdist = format!(
            "lock-version = \"1.0\"\n\n[[packages]]\nname = \"demo\"\nversion = \"1.0\"\nsdist = {{ path = \"demo-1.0.tar.gz\", hashes = {{ sha256 = \"{}\" }} }}\n",
            "ab".repeat(32)
        );
        let t = Setup::python(&[
            ("slopvac-plugin.toml", PLUGIN_MANIFEST),
            ("plugin.py", "x\n"),
            ("pylock.toml", &sdist),
        ]);
        let err = t.sync(Network::Offline, true).unwrap_err();
        assert!(
            matches!(
                &err,
                SyncError::PythonEnv {
                    source: PyEnvError::SourceOnly { .. },
                    ..
                }
            ),
            "{err:?}"
        );
        assert_eq!(err.exit_code(), 2);
        assert_eq!(t.uv_log(), "", "uv never ran");
    }

    #[test]
    fn offline_sync_without_an_installed_interpreter_fails_instead_of_downloading() {
        let t = Setup::new(
            &Fake {
                find_exit: 1,
                ..Fake::real()
            },
            &PLUGIN_FILES,
        );
        let err = t.sync(Network::Offline, true).unwrap_err();
        assert!(
            matches!(&err, SyncError::PythonEnv { source: PyEnvError::OfflinePythonMissing(r), .. } if r == "3.12"),
            "{err:?}"
        );
    }

    fn python_states(t: &Setup) -> Vec<PythonState> {
        status_with_python(&t.env.store(), &t.envs, t.env.project.path(), &t.lock)
            .unwrap()
            .into_iter()
            .map(|p| p.python)
            .collect()
    }

    #[test]
    fn status_verifies_a_built_environment_with_the_full_check() {
        let t = Setup::python(&PLUGIN_FILES);
        t.sync(Network::Offline, true).unwrap();
        assert_eq!(
            python_states(&t),
            [PythonState::Verified(EnvStore::key(&t.hash, "3.12"))]
        );
        let plain = status(&t.env.store(), t.env.project.path(), &t.lock).unwrap();
        assert_eq!(plain[0].python, PythonState::NotChecked);
    }

    #[test]
    fn status_reports_a_missing_environment() {
        let t = Setup::python(&PLUGIN_FILES);
        t.sync(Network::Offline, false).unwrap();
        assert_eq!(python_states(&t), [PythonState::Missing]);
    }

    #[test]
    fn status_reports_an_edit_that_only_the_full_check_sees() {
        let t = Setup::python(&PLUGIN_FILES);
        t.sync(Network::Offline, true).unwrap();
        let env = t.envs.load(&t.hash, "3.12").unwrap().unwrap();
        let file = env.root().join("pyvenv.cfg");
        let (before, text) = (
            fs::metadata(&file).unwrap(),
            fs::read_to_string(&file).unwrap(),
        );
        // Same size, same modification time: a different first letter.
        let edited = format!("H{}", &text[1..]);
        fs::set_permissions(&file, fs::Permissions::from_mode(0o644)).unwrap();
        fs::write(&file, edited).unwrap();
        let f = fs::File::options().write(true).open(&file).unwrap();
        f.set_modified(before.modified().unwrap()).unwrap();
        drop(f);
        fs::set_permissions(&file, before.permissions()).unwrap();
        assert_eq!(fs::metadata(&file).unwrap().len(), before.len());

        env.check_quick().unwrap();
        let states = python_states(&t);
        assert!(
            matches!(&states[..], [PythonState::Failed(why)] if why.contains("pyvenv.cfg")),
            "{states:?}"
        );
    }

    #[test]
    fn status_does_not_look_for_an_environment_of_a_pack_that_is_not_a_python_plugin() {
        let t = Setup::python(&[(
            "slopvac-plugin.toml",
            PLUGIN_MANIFEST
                .replace("runtime = \"python\"\npython = \"3.12\"\n", "")
                .as_str(),
        )]);
        t.sync(Network::Offline, true).unwrap();
        assert_eq!(python_states(&t), [PythonState::NotChecked]);
    }
}
