//! Messages for OCI transport, archive extraction and applying plugin changes.

use slopvac_messages::{Catalog, Entry};
use slopvac_sanitize::line as esc;

/// Published credential-helper failures.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum TransportMessage {
    /// A helper exists only in an untrusted directory.
    #[code("credential-helper-untrusted")]
    #[message(
        "credential helper `{program}` was not found in a trusted directory; it exists only in {dir}. \
         Tighten the permissions of that directory so that only you or root can write it, \
         or sign in with a static `auths` login in the Docker config, with SLOPVAC_OCI_USER \
         and SLOPVAC_OCI_TOKEN, or with GITHUB_TOKEN for ghcr.io"
    )]
    HelperUntrusted {
        program: String,
        #[display_path]
        dir: String,
    },
    /// A helper cannot be checked without the project directory.
    #[code("credential-helper-project-unknown")]
    #[message("credential helper `{program}` was not run: the project directory is unknown")]
    HelperProjectUnknown { program: String },
}

/// Failure sentences and operation descriptions.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum TransportText {
    /// OCI input is invalid.
    #[code("plugins-oci-invalid")]
    #[text("invalid OCI input: {detail}")]
    OciInvalid { detail: String },
    /// The network request failed.
    #[code("plugins-oci-network")]
    #[text("network error for {url}: {detail}")]
    OciNetwork { url: String, detail: String },
    /// A URL is not HTTPS.
    #[code("plugins-oci-insecure-url")]
    #[text("refused URL {url}: HTTPS is required")]
    OciInsecureUrl { url: String },
    /// A redirect was refused.
    #[code("plugins-oci-bad-redirect")]
    #[text("bad redirect from {url}: {reason}")]
    OciBadRedirect { url: String, reason: String },
    /// A token realm is not trusted.
    #[code("plugins-oci-realm-rejected")]
    #[text("token realm {url} is not on the registry origin; credentials were not sent")]
    OciRealmRejected { url: String },
    /// Reading credentials failed.
    #[code("plugins-oci-credential")]
    #[text("credential error: {detail}")]
    OciCredential { detail: String },
    /// Access was denied or the object is absent.
    #[code("plugins-oci-denied")]
    #[text("access denied or not found at {url}")]
    OciDenied { url: String },
    /// An object was not found.
    #[code("plugins-oci-not-found")]
    #[text("not found: {url}")]
    OciNotFound { url: String },
    /// An HTTP status was unexpected.
    #[code("plugins-oci-status")]
    #[text("unexpected status {status} from {url}")]
    OciStatus {
        #[count]
        status: u16,
        url: String,
    },
    /// A response exceeded its size limit.
    #[code("plugins-oci-too-large")]
    #[text("{what} exceeds the limit of {limit} bytes")]
    OciTooLarge {
        what: String,
        #[count]
        limit: u64,
    },
    /// A digest did not match.
    #[code("plugins-oci-digest-mismatch")]
    #[text("digest mismatch: expected {expected}, got {actual}")]
    OciDigestMismatch { expected: String, actual: String },
    /// A descriptor size did not match.
    #[code("plugins-oci-size-mismatch")]
    #[text("size mismatch: descriptor says {expected} bytes, received {actual}")]
    OciSizeMismatch {
        #[count]
        expected: u64,
        #[count]
        actual: u64,
    },
    /// A media type is unsupported.
    #[code("plugins-oci-media-type")]
    #[text("unsupported media type `{media_type}`")]
    OciMediaType { media_type: String },
    /// A reference is malformed.
    #[code("plugins-oci-reference")]
    #[text("reference `{reference}`: {reason}")]
    OciReference { reference: String, reason: String },
    /// A digest uses another algorithm.
    #[code("plugins-oci-digest-algorithm")]
    #[text("digest `{digest}` is not sha256")]
    OciDigestAlgorithm { digest: String },
    /// A digest has invalid hex digits.
    #[code("plugins-oci-digest-hex")]
    #[text("digest `{digest}` is not 64 lowercase hex digits")]
    OciDigestHex { digest: String },
    /// A wire response exceeded its limit.
    #[code("plugins-oci-wire-limit")]
    #[text("response exceeds {limit} bytes on the wire")]
    OciWireLimit {
        #[count]
        limit: u64,
    },
    /// Building a request failed.
    #[code("plugins-oci-request")]
    #[text("request for {url}: {detail}")]
    OciRequest { url: String, detail: String },
    /// Reading a manifest failed.
    #[code("plugins-oci-manifest")]
    #[text("manifest: {detail}")]
    OciManifest { detail: String },
    /// Reading an index failed.
    #[code("plugins-oci-index")]
    #[text("index: {detail}")]
    OciIndex { detail: String },
    /// Writing a downloaded blob failed.
    #[code("plugins-oci-write")]
    #[text("write: {detail}")]
    OciWrite { detail: String },
    /// Reading a tag list failed.
    #[code("plugins-oci-tag-list")]
    #[text("tag list: {detail}")]
    OciTagList { detail: String },
    /// Docker config entries conflict.
    #[code("plugins-oci-config-conflict")]
    #[text("the Docker config has conflicting `{section}` entries for `{registry}`")]
    OciConfigConflict { section: String, registry: String },
    /// A credential helper is missing.
    #[code("plugins-oci-helper-missing")]
    #[text("credential helper `{program}` was not found")]
    OciHelperMissing { program: String },
    /// A credential helper name is unsafe.
    #[code("plugins-oci-helper-name")]
    #[text("credential helper name `{name}` is not allowed")]
    OciHelperName { name: String },
    /// Starting a credential helper failed.
    #[code("plugins-oci-helper-start")]
    #[text("cannot start `{program}`: {detail}")]
    OciHelperStart { program: String, detail: String },
    /// Waiting for a helper failed.
    #[code("plugins-oci-helper-wait")]
    #[text("waiting for `{program}`: {detail}")]
    OciHelperWait { program: String, detail: String },
    /// Helper output exceeded the cap.
    #[code("plugins-oci-helper-output")]
    #[text("`{program}` printed more than {limit} bytes")]
    OciHelperOutput {
        program: String,
        #[count]
        limit: usize,
    },
    /// A helper timed out.
    #[code("plugins-oci-helper-timeout")]
    #[text("`{program}` timed out")]
    OciHelperTimeout { program: String },
    /// A helper printed invalid JSON.
    #[code("plugins-oci-helper-json")]
    #[text("`{program}` printed invalid JSON")]
    OciHelperJson { program: String },
    /// Reading a credential config failed.
    #[code("plugins-oci-config-read")]
    #[text("reading the {what}: {detail}")]
    OciConfigRead { what: String, detail: String },
    /// A credential config is too large.
    #[code("plugins-oci-config-size")]
    #[text("the {what} is larger than 1 MiB")]
    OciConfigSize { what: String },
    /// A credential config is invalid JSON.
    #[code("plugins-oci-config-json")]
    #[text("the {what} is not valid JSON")]
    OciConfigJson { what: String },
    /// An archive was refused.
    #[code("plugins-extract-refused")]
    #[text("archive refused: {detail}")]
    ExtractRefused { detail: String },
    /// An archive is malformed.
    #[code("plugins-extract-malformed")]
    #[text("archive is malformed: {detail}")]
    ExtractMalformed { detail: String },
    /// A cached tree does not match its hash.
    #[code("plugins-extract-tampered")]
    #[text("cached tree {path} does not match its hash")]
    ExtractTampered {
        #[display_path]
        path: String,
    },
    /// An extraction operation failed.
    #[code("plugins-extract-io")]
    #[text("{what}: {detail}")]
    ExtractIo { what: String, detail: String },
    /// A tree has too many nodes.
    #[code("plugins-extract-nodes")]
    #[text("tree has more than {limit} files and directories")]
    ExtractNodes {
        #[count]
        limit: usize,
    },
    /// A tree hash is malformed.
    #[code("plugins-extract-tree-hash")]
    #[text("`{hash}` is not a sha256 tree hash")]
    ExtractTreeHash { hash: String },
    /// Compressed bytes exceeded the cap.
    #[code("plugins-extract-compressed-size")]
    #[text("compressed size exceeds {limit} bytes")]
    ExtractCompressedSize {
        #[count]
        limit: u64,
    },
    /// Expanded bytes exceeded the cap.
    #[code("plugins-extract-expanded-size")]
    #[text("expanded size exceeds {limit} bytes")]
    ExtractExpandedSize {
        #[count]
        limit: u64,
    },
    /// Compression ratio exceeded the cap.
    #[code("plugins-extract-ratio")]
    #[text("compression ratio exceeds {limit} to 1")]
    ExtractRatio {
        #[count]
        limit: u64,
    },
    /// An entry path is invalid.
    #[code("plugins-extract-entry-path")]
    #[text("entry path `{path}`: {detail}")]
    ExtractEntryPath {
        #[display_path]
        path: String,
        detail: String,
    },
    /// Two archive names collide.
    #[code("plugins-extract-collision")]
    #[text("`{path}` collides with `{existing}`")]
    ExtractCollision {
        #[display_path]
        path: String,
        #[display_path]
        existing: String,
    },
    /// Creating a directory failed.
    #[code("plugins-extract-creating")]
    #[text("creating {path}")]
    ExtractCreating {
        #[display_path]
        path: String,
    },
    /// Securing a directory failed.
    #[code("plugins-extract-securing")]
    #[text("securing {path}")]
    ExtractSecuring {
        #[display_path]
        path: String,
    },
    /// Inspecting a path failed.
    #[code("plugins-extract-inspecting")]
    #[text("inspecting {path}")]
    ExtractInspecting {
        #[display_path]
        path: String,
    },
    /// Opening a path failed.
    #[code("plugins-extract-opening")]
    #[text("opening {path}")]
    ExtractOpening {
        #[display_path]
        path: String,
    },
    /// A directory vanished before securing it.
    #[code("plugins-extract-vanished")]
    #[text("{path} vanished while securing it")]
    ExtractVanished {
        #[display_path]
        path: String,
    },
    /// A directory has another owner.
    #[code("plugins-extract-owner")]
    #[text("{path} is owned by another user")]
    ExtractOwner {
        #[display_path]
        path: String,
    },
    /// A path is a link or not a directory.
    #[code("plugins-extract-directory")]
    #[text("{path} is a link or not a directory")]
    ExtractDirectory {
        #[display_path]
        path: String,
    },
    /// A directory changed before opening it.
    #[code("plugins-extract-changed")]
    #[text("{path} changed while opening")]
    ExtractChanged {
        #[display_path]
        path: String,
    },
    /// Creating an archive file failed.
    #[code("plugins-extract-creating-file")]
    #[text("creating `{path}`")]
    ExtractCreatingFile {
        #[display_path]
        path: String,
    },
    /// There are too many archive entries.
    #[code("plugins-extract-entries")]
    #[text("more than {limit} entries")]
    ExtractEntries {
        #[count]
        limit: usize,
    },
    /// An archive entry type is unsupported.
    #[code("plugins-extract-entry-type")]
    #[text("entry type {kind} is not a regular file or directory")]
    ExtractEntryType { kind: String },
    /// A PAX record is unsupported.
    #[code("plugins-extract-pax-record")]
    #[text("PAX record `{key}` is not accepted")]
    ExtractPaxRecord { key: String },
    /// An entry is shorter than its header.
    #[code("plugins-extract-short-entry")]
    #[text("`{path}` is shorter than its header says")]
    ExtractShortEntry {
        #[display_path]
        path: String,
    },
    /// An extension header is too large.
    #[code("plugins-extract-extension-size")]
    #[text("extension header larger than {limit} bytes")]
    ExtractExtensionSize {
        #[count]
        limit: u64,
    },
    /// Reading an archive entry failed.
    #[code("plugins-extract-entry-read")]
    #[text("`{what}`: {detail}")]
    ExtractEntryRead {
        #[display_path]
        what: String,
        detail: String,
    },
    /// Writing an archive entry failed.
    #[code("plugins-extract-entry-write")]
    #[text("writing `{what}`")]
    ExtractEntryWrite {
        #[display_path]
        what: String,
    },
    /// An archive entry is too large.
    #[code("plugins-extract-entry-size")]
    #[text("`{what}` is larger than allowed")]
    ExtractEntrySize {
        #[display_path]
        what: String,
    },
    /// An observed tree path is invalid.
    #[code("plugins-extract-path")]
    #[text("`{path}`: {detail}")]
    ExtractPath {
        #[display_path]
        path: String,
        detail: String,
    },
    /// A file exceeds the tree byte bound.
    #[code("plugins-extract-tree-size")]
    #[text("`{path}` exceeds the tree size bound")]
    ExtractTreeSize {
        #[display_path]
        path: String,
    },
    /// A tree file is not regular.
    #[code("plugins-extract-file-type")]
    #[text("`{path}` is not a regular file")]
    ExtractFileType {
        #[display_path]
        path: String,
    },
    /// Reading a tree file failed.
    #[code("plugins-extract-reading-file")]
    #[text("reading `{path}`")]
    ExtractReadingFile {
        #[display_path]
        path: String,
    },
    /// A tree path is a link or special file.
    #[code("plugins-extract-special-file")]
    #[text("`{path}` is a link or special file")]
    ExtractSpecialFile {
        #[display_path]
        path: String,
    },
    /// Removing a stale tree failed.
    #[code("plugins-extract-removing")]
    #[text("removing {path}")]
    ExtractRemoving {
        #[display_path]
        path: String,
    },
    /// An oversized stale tree was quarantined.
    #[code("plugins-extract-quarantining")]
    #[text("quarantining {path} (too many entries to remove)")]
    ExtractQuarantining {
        #[display_path]
        path: String,
    },
    /// An edit set was refused.
    #[code("plugins-apply-invalid-edits")]
    #[text("edits refused: {detail}")]
    ApplyInvalidEdits { detail: String },
    /// A plan was refused.
    #[code("plugins-apply-invalid-plan")]
    #[text("plan refused: {detail}")]
    ApplyInvalidPlan { detail: String },
    /// An application path was refused.
    #[code("plugins-apply-path-refused")]
    #[text("path refused: {detail}")]
    ApplyPathRefused { detail: String },
    /// A target is a symbolic link.
    #[code("plugins-apply-symlink")]
    #[text("`{path}` is a symbolic link")]
    ApplySymlink {
        #[display_path]
        path: String,
    },
    /// A target is not a regular file.
    #[code("plugins-apply-not-regular")]
    #[text("`{path}` is not a regular file")]
    ApplyNotRegular {
        #[display_path]
        path: String,
    },
    /// A target has multiple hard links.
    #[code("plugins-apply-hardlinked")]
    #[text("`{path}` has more than one hard link")]
    ApplyHardlinked {
        #[display_path]
        path: String,
    },
    /// A source changed after reading.
    #[code("plugins-apply-source-changed")]
    #[text("`{path}` changed since it was read")]
    ApplySourceChanged {
        #[display_path]
        path: String,
    },
    /// A source exceeds its size limit.
    #[code("plugins-apply-too-large")]
    #[text("`{path}` is larger than the size limit")]
    ApplyTooLarge {
        #[display_path]
        path: String,
    },
    /// A sensitive target needs approval.
    #[code("plugins-apply-sensitive")]
    #[text("`{path}` is a sensitive path; approve {needs} to write it")]
    ApplySensitive {
        #[display_path]
        path: String,
        needs: String,
    },
    /// A target collides when case is ignored.
    #[code("plugins-apply-case-collision")]
    #[text("`{path}` collides with existing `{existing}` when case is ignored")]
    ApplyCaseCollision {
        #[display_path]
        path: String,
        #[display_path]
        existing: String,
    },
    /// A target appears twice in a plan.
    #[code("plugins-apply-duplicate")]
    #[text("`{path}` appears twice in the plan")]
    ApplyDuplicate {
        #[display_path]
        path: String,
    },
    /// Merging into an existing target is unsupported.
    #[code("plugins-apply-merge")]
    #[text("merge into existing `{path}` is not supported yet")]
    ApplyMerge {
        #[display_path]
        path: String,
    },
    /// Writes on Windows are unsupported.
    #[code("plugins-apply-windows")]
    #[text(
        "`{path}`: writes are not supported on Windows yet; the file-system layer \
         resolves rename, delete and create-directory through absolute paths that a \
         junction swap can redirect"
    )]
    ApplyWindows {
        #[display_path]
        path: String,
    },
    /// An application operation failed.
    #[code("plugins-apply-io")]
    #[text("{detail}")]
    ApplyIo { detail: String },
    /// A path is quoted for an approval list.
    #[code("plugins-apply-quoted-path")]
    #[text("`{path}`")]
    ApplyQuotedPath {
        #[display_path]
        path: String,
    },
    /// An operating-system operation failed at a path.
    #[code("plugins-apply-path-io")]
    #[text("{path}: {detail}")]
    ApplyPathIo {
        #[display_path]
        path: String,
        detail: String,
    },
    /// An edit set exceeds its count cap.
    #[code("plugins-apply-edit-count")]
    #[text("{count} edits exceed the limit of {limit}")]
    ApplyEditCount {
        #[count]
        count: usize,
        #[count]
        limit: usize,
    },
    /// Inserted bytes exceed the cap.
    #[code("plugins-apply-inserted-size")]
    #[text("{count} inserted bytes exceed the cap of {limit}")]
    ApplyInsertedSize {
        #[count]
        count: usize,
        #[count]
        limit: usize,
    },
    /// A plan entry has no content.
    #[code("plugins-apply-content-missing")]
    #[text("`{path}` has no content")]
    ApplyContentMissing {
        #[display_path]
        path: String,
    },
    /// A parent directory is absent.
    #[code("plugins-apply-no-directory")]
    #[text("{path}: no directory")]
    ApplyNoDirectory {
        #[display_path]
        path: String,
    },
    /// A path has stream or reserved characters.
    #[code("plugins-apply-reserved-character")]
    #[text("`{path}`: stream or reserved character")]
    ApplyReservedCharacter {
        #[display_path]
        path: String,
    },
    /// A path looks like a Windows short name.
    #[code("plugins-apply-short-name")]
    #[text("`{path}`: looks like a Windows 8.3 short name")]
    ApplyShortName {
        #[display_path]
        path: String,
    },
    /// A path leaves the project root.
    #[code("plugins-apply-outside-root")]
    #[text("`{path}` leaves the project root")]
    ApplyOutsideRoot {
        #[display_path]
        path: String,
    },
    /// A path component is not a plain directory.
    #[code("plugins-apply-parent-type")]
    #[text("`{path}`: `{component}` is not a plain directory ({detail})")]
    ApplyParentType {
        #[display_path]
        path: String,
        component: String,
        detail: String,
    },
    /// A directory is missing.
    #[code("plugins-apply-directory-missing")]
    #[text("{path}: directory is missing")]
    ApplyDirectoryMissing {
        #[display_path]
        path: String,
    },
    /// No temporary name was available.
    #[code("plugins-apply-temporary-name")]
    #[text("{path}: no free temporary name")]
    ApplyTemporaryName {
        #[display_path]
        path: String,
    },
}

/// Fixed failure reasons and operation labels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum TransportPhrase {
    /// A reference has no repository.
    #[code("plugins-oci-no-repository")]
    #[text("no repository")]
    OciNoRepository,
    /// A registry host is invalid.
    #[code("plugins-oci-bad-host")]
    #[text("bad registry host")]
    OciBadHost,
    /// A repository name is invalid.
    #[code("plugins-oci-bad-repository")]
    #[text("bad repository name")]
    OciBadRepository,
    /// A tag is invalid.
    #[code("plugins-oci-bad-tag")]
    #[text("bad tag")]
    OciBadTag,
    /// A reference needs a target.
    #[code("plugins-oci-target-required")]
    #[text("needs a tag or a digest")]
    OciTargetRequired,
    /// A redirect location is unusable.
    #[code("plugins-oci-location-unusable")]
    #[text("unusable Location")]
    OciLocationUnusable,
    /// A redirect target is not HTTPS.
    #[code("plugins-oci-target-insecure")]
    #[text("target is not HTTPS")]
    OciTargetInsecure,
    /// A redirect used an unsupported request method.
    #[code("plugins-oci-redirect-method")]
    #[text("redirect on a request that is not GET or HEAD")]
    OciRedirectMethod,
    /// A request followed too many redirects.
    #[code("plugins-oci-redirect-count")]
    #[text("more than 5 redirects")]
    OciRedirectCount,
    /// A redirect has no location.
    #[code("plugins-oci-location-missing")]
    #[text("no Location header")]
    OciLocationMissing,
    /// A bearer challenge has no realm.
    #[code("plugins-oci-realm-missing")]
    #[text("bearer challenge without realm")]
    OciRealmMissing,
    /// A token response is invalid JSON.
    #[code("plugins-oci-token-json")]
    #[text("token response is not JSON")]
    OciTokenJson,
    /// An upload response has no location.
    #[code("plugins-oci-upload-location")]
    #[text("upload response without Location")]
    OciUploadLocation,
    /// An upload target is on another host.
    #[code("plugins-oci-upload-host")]
    #[text("upload target is on another host")]
    OciUploadHost,
    /// A registry name is unsafe for a helper.
    #[code("plugins-oci-registry-unsafe")]
    #[text("registry name is not safe to pass to a credential helper")]
    OciRegistryUnsafe,
    /// A helper has no stdout.
    #[code("plugins-oci-helper-stdout")]
    #[text("no helper stdout")]
    OciHelperStdout,
    /// A helper reader failed.
    #[code("plugins-oci-helper-reader")]
    #[text("helper reader failed")]
    OciHelperReader,
    /// A helper did not finish.
    #[code("plugins-oci-helper-unfinished")]
    #[text("helper did not finish")]
    OciHelperUnfinished,
    /// Identity tokens are unsupported.
    #[code("plugins-oci-helper-identity-token")]
    #[text("identity tokens from credential helpers are not supported")]
    OciHelperIdentityToken,
    /// An auth entry is not base64.
    #[code("plugins-oci-auth-base64")]
    #[text("an `auth` entry is not base64 text")]
    OciAuthBase64,
    /// An auth entry has no colon.
    #[code("plugins-oci-auth-colon")]
    #[text("an `auth` entry has no colon")]
    OciAuthColon,
    /// The Docker configuration label.
    #[code("plugins-oci-docker-config")]
    #[text("Docker config")]
    OciDockerConfig,
    /// The registry auth file label.
    #[code("plugins-oci-registry-auth-file")]
    #[text("registry auth file")]
    OciRegistryAuthFile,
    /// The response size label.
    #[code("plugins-oci-response")]
    #[text("response")]
    OciResponse,
    /// The archive size label.
    #[code("plugins-oci-archive")]
    #[text("archive")]
    OciArchive,
    /// The blob size label.
    #[code("plugins-oci-blob")]
    #[text("blob")]
    OciBlob,
    /// The manifest size label.
    #[code("plugins-oci-manifest-label")]
    #[text("manifest")]
    OciManifest,
    /// The referrers list size label.
    #[code("plugins-oci-referrers-list")]
    #[text("referrers list")]
    OciReferrersList,
    /// The referrers index size label.
    #[code("plugins-oci-referrers-index")]
    #[text("referrers index")]
    OciReferrersIndex,
    /// The tag list size label.
    #[code("plugins-oci-tag-list-label")]
    #[text("tag list")]
    OciTagList,
    /// The token response size label.
    #[code("plugins-oci-token-response")]
    #[text("token response")]
    OciTokenResponse,
    /// The absent media type label.
    #[code("plugins-oci-media-none")]
    #[text("none")]
    OciMediaNone,
    /// An entry path is not UTF-8.
    #[code("plugins-extract-path-utf8")]
    #[text("entry path is not UTF-8")]
    ExtractPathUtf8,
    /// A path contains a colon.
    #[code("plugins-extract-path-colon")]
    #[text("colon in path")]
    ExtractPathColon,
    /// A staging directory is being created.
    #[code("plugins-extract-create-staging")]
    #[text("creating the staging directory")]
    ExtractCreateStaging,
    /// A tree directory is being created.
    #[code("plugins-extract-create-tree")]
    #[text("creating the tree directory")]
    ExtractCreateTree,
    /// A staging directory is being removed.
    #[code("plugins-extract-remove-staging")]
    #[text("removing the staging directory")]
    ExtractRemoveStaging,
    /// A directory is being created.
    #[code("plugins-extract-create-directory")]
    #[text("creating a directory")]
    ExtractCreateDirectory,
    /// Sparse entries are unsupported.
    #[code("plugins-extract-sparse")]
    #[text("sparse entries are not accepted")]
    ExtractSparse,
    /// A long name lacks an entry.
    #[code("plugins-extract-long-name")]
    #[text("a long name describes no entry")]
    ExtractLongName,
    /// The executable list is being created.
    #[code("plugins-extract-create-executable-list")]
    #[text("creating the executable list")]
    ExtractCreateExecutableList,
    /// The executable list is being written.
    #[code("plugins-extract-write-executable-list")]
    #[text("writing the executable list")]
    ExtractWriteExecutableList,
    /// A PAX key is not UTF-8.
    #[code("plugins-extract-pax-utf8")]
    #[text("PAX key is not UTF-8")]
    ExtractPaxUtf8,
    /// Two names describe one entry.
    #[code("plugins-extract-two-names")]
    #[text("two names describe the same entry")]
    ExtractTwoNames,
    /// A tree is being stored.
    #[code("plugins-extract-store-tree")]
    #[text("storing the tree")]
    ExtractStoreTree,
    /// A tree is being sealed.
    #[code("plugins-extract-seal-tree")]
    #[text("sealing the tree")]
    ExtractSealTree,
    /// A directory is being read.
    #[code("plugins-extract-read-directory")]
    #[text("reading a directory")]
    ExtractReadDirectory,
    /// An entry is being inspected.
    #[code("plugins-extract-inspect-entry")]
    #[text("inspecting an entry")]
    ExtractInspectEntry,
    /// A directory is being sealed.
    #[code("plugins-extract-seal-directory")]
    #[text("sealing a directory")]
    ExtractSealDirectory,
    /// A file is being sealed.
    #[code("plugins-extract-seal-file")]
    #[text("sealing a file")]
    ExtractSealFile,
    /// An opened handle is not regular.
    #[code("plugins-extract-not-regular")]
    #[text("not a regular file")]
    ExtractNotRegular,
    /// A tree root is being inspected.
    #[code("plugins-extract-inspect-root")]
    #[text("inspecting the tree root")]
    ExtractInspectRoot,
    /// A tree root is not a directory.
    #[code("plugins-extract-root-type")]
    #[text("the tree root is a link or not a directory")]
    ExtractRootType,
    /// A file name is not UTF-8.
    #[code("plugins-extract-name-utf8")]
    #[text("a file name is not UTF-8")]
    ExtractNameUtf8,
    /// An executable file is unlisted.
    #[code("plugins-extract-executable-unlisted")]
    #[text("a file has the executable bit but is not listed")]
    ExtractExecutableUnlisted,
    /// A listed file lost its executable bit.
    #[code("plugins-extract-executable-bit")]
    #[text("a listed file lost its executable bit")]
    ExtractExecutableBit,
    /// The executable list is being read.
    #[code("plugins-extract-read-executable-list")]
    #[text("reading the executable list")]
    ExtractReadExecutableList,
    /// The executable list has an invalid line.
    #[code("plugins-extract-executable-line")]
    #[text("the executable list has a bad line")]
    ExtractExecutableLine,
    /// The executable list is not sorted and unique.
    #[code("plugins-extract-executable-order")]
    #[text("the executable list is not sorted and unique")]
    ExtractExecutableOrder,
    /// The executable list names a missing file.
    #[code("plugins-extract-executable-missing")]
    #[text("the executable list names a missing file")]
    ExtractExecutableMissing,
    /// The executable list names itself.
    #[code("plugins-extract-executable-self")]
    #[text("the executable list names itself")]
    ExtractExecutableSelf,
    /// Edit source bytes are not UTF-8.
    #[code("plugins-apply-source-utf8")]
    #[text("source is not UTF-8")]
    ApplySourceUtf8,
    /// An edit span is outside the text or splits a character.
    #[code("plugins-apply-span-character")]
    #[text("a span is outside the text or inside a character")]
    ApplySpanCharacter,
    /// An edit span splits a CRLF pair.
    #[code("plugins-apply-span-crlf")]
    #[text("a span splits a CRLF pair")]
    ApplySpanCrlf,
    /// Edits overlap.
    #[code("plugins-apply-overlap")]
    #[text("edits overlap")]
    ApplyOverlap,
    /// An edit span is outside the text.
    #[code("plugins-apply-span-range")]
    #[text("a span is outside the text")]
    ApplySpanRange,
    /// The nonblocking flag cannot be represented.
    #[code("plugins-apply-nonblock")]
    #[text("O_NONBLOCK does not fit")]
    ApplyNonblock,
    /// A path is a git directory.
    #[code("plugins-apply-git-directory")]
    #[text("git directory")]
    ApplyGitDirectory,
    /// A path holds slopvac state.
    #[code("plugins-apply-state")]
    #[text("slopvac state")]
    ApplyState,
    /// A path is a CI workflow.
    #[code("plugins-apply-ci-workflow")]
    #[text("CI workflow")]
    ApplyCiWorkflow,
    /// A path is an environment file.
    #[code("plugins-apply-environment")]
    #[text("environment file")]
    ApplyEnvironment,
    /// A path is git configuration.
    #[code("plugins-apply-git-config")]
    #[text("git configuration")]
    ApplyGitConfig,
    /// A path is tool configuration.
    #[code("plugins-apply-tool-config")]
    #[text("tool configuration")]
    ApplyToolConfig,
    /// A path is an editor task file.
    #[code("plugins-apply-editor-task")]
    #[text("editor task file")]
    ApplyEditorTask,
}

pub(crate) fn oci_invalid(detail: &str) -> String {
    TransportText::OciInvalid {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn oci_network(url: &str, detail: &str) -> String {
    TransportText::OciNetwork {
        url: esc(url),
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn oci_insecure_url(url: &str) -> String {
    TransportText::OciInsecureUrl { url: esc(url) }.to_string()
}

pub(crate) fn oci_bad_redirect(url: &str, reason: &str) -> String {
    TransportText::OciBadRedirect {
        url: esc(url),
        reason: esc(reason),
    }
    .to_string()
}

pub(crate) fn oci_realm_rejected(url: &str) -> String {
    TransportText::OciRealmRejected { url: esc(url) }.to_string()
}

pub(crate) fn oci_credential(detail: &str) -> String {
    TransportText::OciCredential {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn helper_untrusted(program: &str, dir: &str) -> String {
    TransportMessage::HelperUntrusted {
        program: esc(program),
        dir: esc(dir),
    }
    .to_string()
}

pub(crate) fn helper_project_unknown(program: &str) -> String {
    TransportMessage::HelperProjectUnknown {
        program: esc(program),
    }
    .to_string()
}

pub(crate) fn oci_denied(url: &str) -> String {
    TransportText::OciDenied { url: esc(url) }.to_string()
}

pub(crate) fn oci_not_found(url: &str) -> String {
    TransportText::OciNotFound { url: esc(url) }.to_string()
}

pub(crate) fn oci_status(status: u16, url: &str) -> String {
    TransportText::OciStatus {
        status,
        url: esc(url),
    }
    .to_string()
}

pub(crate) fn oci_too_large(what: &str, limit: u64) -> String {
    TransportText::OciTooLarge {
        what: esc(what),
        limit,
    }
    .to_string()
}

pub(crate) fn oci_digest_mismatch(expected: &str, actual: &str) -> String {
    TransportText::OciDigestMismatch {
        expected: esc(expected),
        actual: esc(actual),
    }
    .to_string()
}

pub(crate) fn oci_size_mismatch(expected: u64, actual: u64) -> String {
    TransportText::OciSizeMismatch { expected, actual }.to_string()
}

pub(crate) fn oci_media_type(media_type: &str) -> String {
    TransportText::OciMediaType {
        media_type: esc(media_type),
    }
    .to_string()
}

pub(crate) fn apply_invalid_edits(detail: &str) -> String {
    TransportText::ApplyInvalidEdits {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn apply_invalid_plan(detail: &str) -> String {
    TransportText::ApplyInvalidPlan {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn apply_path_refused(detail: &str) -> String {
    TransportText::ApplyPathRefused {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn apply_symlink(path: &str) -> String {
    TransportText::ApplySymlink { path: esc(path) }.to_string()
}

pub(crate) fn apply_not_regular(path: &str) -> String {
    TransportText::ApplyNotRegular { path: esc(path) }.to_string()
}

pub(crate) fn apply_hardlinked(path: &str) -> String {
    TransportText::ApplyHardlinked { path: esc(path) }.to_string()
}

pub(crate) fn apply_source_changed(path: &str) -> String {
    TransportText::ApplySourceChanged { path: esc(path) }.to_string()
}

pub(crate) fn apply_too_large(path: &str) -> String {
    TransportText::ApplyTooLarge { path: esc(path) }.to_string()
}

pub(crate) fn apply_sensitive(path: &str, needs: &[String]) -> String {
    let needs: Vec<String> = needs
        .iter()
        .map(|path| TransportText::ApplyQuotedPath { path: esc(path) }.to_string())
        .collect();
    TransportText::ApplySensitive {
        path: esc(path),
        needs: needs.join(", "),
    }
    .to_string()
}

pub(crate) fn apply_case_collision(path: &str, existing: &str) -> String {
    TransportText::ApplyCaseCollision {
        path: esc(path),
        existing: esc(existing),
    }
    .to_string()
}

pub(crate) fn apply_duplicate(path: &str) -> String {
    TransportText::ApplyDuplicate { path: esc(path) }.to_string()
}

pub(crate) fn apply_merge(path: &str) -> String {
    TransportText::ApplyMerge { path: esc(path) }.to_string()
}

pub(crate) fn apply_windows(path: &str) -> String {
    TransportText::ApplyWindows { path: esc(path) }.to_string()
}

pub(crate) fn apply_io(detail: &str) -> String {
    TransportText::ApplyIo {
        detail: esc(detail),
    }
    .to_string()
}

pub(super) fn entries() -> Vec<Entry> {
    [
        TransportMessage::entries(),
        TransportText::entries(),
        TransportPhrase::entries(),
    ]
    .concat()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(value: &str) -> String {
        value.to_owned()
    }

    #[test]
    fn published_messages_keep_their_wording_and_are_registered() {
        let table = [
            (
                TransportMessage::HelperUntrusted {
                    program: s("docker-credential-test"),
                    dir: s("<external>/bin"),
                },
                "credential helper `docker-credential-test` was not found in a trusted directory; it exists only in <external>/bin. Tighten the permissions of that directory so that only you or root can write it, or sign in with a static `auths` login in the Docker config, with SLOPVAC_OCI_USER and SLOPVAC_OCI_TOKEN, or with GITHUB_TOKEN for ghcr.io",
            ),
            (
                TransportMessage::HelperProjectUnknown {
                    program: s("docker-credential-test"),
                },
                "credential helper `docker-credential-test` was not run: the project directory is unknown",
            ),
        ];
        let registered = entries();
        assert_eq!(TransportMessage::entries().len(), table.len());
        for (value, expected) in table {
            assert_eq!(value.to_string(), expected);
            assert!(registered.iter().any(|entry| entry.code == value.code()));
        }
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn text_keeps_its_wording_and_is_registered() {
        use TransportText as T;

        let table = [
            (T::OciInvalid { detail: s("x") }, "invalid OCI input: x"),
            (
                T::OciNetwork {
                    url: s("https://example.test/a"),
                    detail: s("x"),
                },
                "network error for https://example.test/a: x",
            ),
            (
                T::OciInsecureUrl {
                    url: s("http://example.test/a"),
                },
                "refused URL http://example.test/a: HTTPS is required",
            ),
            (
                T::OciBadRedirect {
                    url: s("https://example.test/a"),
                    reason: s("x"),
                },
                "bad redirect from https://example.test/a: x",
            ),
            (
                T::OciRealmRejected {
                    url: s("https://example.test/a"),
                },
                "token realm https://example.test/a is not on the registry origin; credentials were not sent",
            ),
            (T::OciCredential { detail: s("x") }, "credential error: x"),
            (
                T::OciDenied {
                    url: s("https://example.test/a"),
                },
                "access denied or not found at https://example.test/a",
            ),
            (
                T::OciNotFound {
                    url: s("https://example.test/a"),
                },
                "not found: https://example.test/a",
            ),
            (
                T::OciStatus {
                    status: 503,
                    url: s("https://example.test/a"),
                },
                "unexpected status 503 from https://example.test/a",
            ),
            (
                T::OciTooLarge {
                    what: s("blob"),
                    limit: 7,
                },
                "blob exceeds the limit of 7 bytes",
            ),
            (
                T::OciDigestMismatch {
                    expected: s("x"),
                    actual: s("y"),
                },
                "digest mismatch: expected x, got y",
            ),
            (
                T::OciSizeMismatch {
                    expected: 7,
                    actual: 9,
                },
                "size mismatch: descriptor says 7 bytes, received 9",
            ),
            (
                T::OciMediaType { media_type: s("x") },
                "unsupported media type `x`",
            ),
            (
                T::OciReference {
                    reference: s("x"),
                    reason: s("y"),
                },
                "reference `x`: y",
            ),
            (
                T::OciDigestAlgorithm { digest: s("x") },
                "digest `x` is not sha256",
            ),
            (
                T::OciDigestHex { digest: s("x") },
                "digest `x` is not 64 lowercase hex digits",
            ),
            (
                T::OciWireLimit { limit: 7 },
                "response exceeds 7 bytes on the wire",
            ),
            (
                T::OciRequest {
                    url: s("https://example.test/a"),
                    detail: s("x"),
                },
                "request for https://example.test/a: x",
            ),
            (T::OciManifest { detail: s("x") }, "manifest: x"),
            (T::OciIndex { detail: s("x") }, "index: x"),
            (T::OciWrite { detail: s("x") }, "write: x"),
            (T::OciTagList { detail: s("x") }, "tag list: x"),
            (
                T::OciConfigConflict {
                    section: s("auths"),
                    registry: s("example.test"),
                },
                "the Docker config has conflicting `auths` entries for `example.test`",
            ),
            (
                T::OciHelperMissing { program: s("x") },
                "credential helper `x` was not found",
            ),
            (
                T::OciHelperName { name: s("x") },
                "credential helper name `x` is not allowed",
            ),
            (
                T::OciHelperStart {
                    program: s("x"),
                    detail: s("y"),
                },
                "cannot start `x`: y",
            ),
            (
                T::OciHelperWait {
                    program: s("x"),
                    detail: s("y"),
                },
                "waiting for `x`: y",
            ),
            (
                T::OciHelperOutput {
                    program: s("x"),
                    limit: 7,
                },
                "`x` printed more than 7 bytes",
            ),
            (T::OciHelperTimeout { program: s("x") }, "`x` timed out"),
            (
                T::OciHelperJson { program: s("x") },
                "`x` printed invalid JSON",
            ),
            (
                T::OciConfigRead {
                    what: s("Docker config"),
                    detail: s("x"),
                },
                "reading the Docker config: x",
            ),
            (
                T::OciConfigSize {
                    what: s("Docker config"),
                },
                "the Docker config is larger than 1 MiB",
            ),
            (
                T::OciConfigJson {
                    what: s("Docker config"),
                },
                "the Docker config is not valid JSON",
            ),
            (T::ExtractRefused { detail: s("x") }, "archive refused: x"),
            (
                T::ExtractMalformed { detail: s("x") },
                "archive is malformed: x",
            ),
            (
                T::ExtractTampered {
                    path: s("store/tree-x"),
                },
                "cached tree store/tree-x does not match its hash",
            ),
            (
                T::ExtractIo {
                    what: s("x"),
                    detail: s("y"),
                },
                "x: y",
            ),
            (
                T::ExtractNodes { limit: 7 },
                "tree has more than 7 files and directories",
            ),
            (
                T::ExtractTreeHash { hash: s("x") },
                "`x` is not a sha256 tree hash",
            ),
            (
                T::ExtractCompressedSize { limit: 7 },
                "compressed size exceeds 7 bytes",
            ),
            (
                T::ExtractExpandedSize { limit: 7 },
                "expanded size exceeds 7 bytes",
            ),
            (
                T::ExtractRatio { limit: 7 },
                "compression ratio exceeds 7 to 1",
            ),
            (
                T::ExtractEntryPath {
                    path: s("x"),
                    detail: s("y"),
                },
                "entry path `x`: y",
            ),
            (
                T::ExtractCollision {
                    path: s("x"),
                    existing: s("y"),
                },
                "`x` collides with `y`",
            ),
            (T::ExtractCreating { path: s("x") }, "creating x"),
            (T::ExtractSecuring { path: s("x") }, "securing x"),
            (T::ExtractInspecting { path: s("x") }, "inspecting x"),
            (T::ExtractOpening { path: s("x") }, "opening x"),
            (
                T::ExtractVanished { path: s("x") },
                "x vanished while securing it",
            ),
            (
                T::ExtractOwner { path: s("x") },
                "x is owned by another user",
            ),
            (
                T::ExtractDirectory { path: s("x") },
                "x is a link or not a directory",
            ),
            (
                T::ExtractChanged { path: s("x") },
                "x changed while opening",
            ),
            (T::ExtractCreatingFile { path: s("x") }, "creating `x`"),
            (T::ExtractEntries { limit: 7 }, "more than 7 entries"),
            (
                T::ExtractEntryType { kind: s("Symlink") },
                "entry type Symlink is not a regular file or directory",
            ),
            (
                T::ExtractPaxRecord { key: s("size") },
                "PAX record `size` is not accepted",
            ),
            (
                T::ExtractShortEntry { path: s("x") },
                "`x` is shorter than its header says",
            ),
            (
                T::ExtractExtensionSize { limit: 7 },
                "extension header larger than 7 bytes",
            ),
            (
                T::ExtractEntryRead {
                    what: s("x"),
                    detail: s("y"),
                },
                "`x`: y",
            ),
            (T::ExtractEntryWrite { what: s("x") }, "writing `x`"),
            (
                T::ExtractEntrySize { what: s("x") },
                "`x` is larger than allowed",
            ),
            (
                T::ExtractPath {
                    path: s("x"),
                    detail: s("y"),
                },
                "`x`: y",
            ),
            (
                T::ExtractTreeSize { path: s("x") },
                "`x` exceeds the tree size bound",
            ),
            (
                T::ExtractFileType { path: s("x") },
                "`x` is not a regular file",
            ),
            (T::ExtractReadingFile { path: s("x") }, "reading `x`"),
            (
                T::ExtractSpecialFile { path: s("x") },
                "`x` is a link or special file",
            ),
            (T::ExtractRemoving { path: s("x") }, "removing x"),
            (
                T::ExtractQuarantining { path: s("x") },
                "quarantining x (too many entries to remove)",
            ),
            (T::ApplyInvalidEdits { detail: s("x") }, "edits refused: x"),
            (T::ApplyInvalidPlan { detail: s("x") }, "plan refused: x"),
            (T::ApplyPathRefused { detail: s("x") }, "path refused: x"),
            (T::ApplySymlink { path: s("x") }, "`x` is a symbolic link"),
            (
                T::ApplyNotRegular { path: s("x") },
                "`x` is not a regular file",
            ),
            (
                T::ApplyHardlinked { path: s("x") },
                "`x` has more than one hard link",
            ),
            (
                T::ApplySourceChanged { path: s("x") },
                "`x` changed since it was read",
            ),
            (
                T::ApplyTooLarge { path: s("x") },
                "`x` is larger than the size limit",
            ),
            (
                T::ApplySensitive {
                    path: s("x"),
                    needs: s("`y`, `z`"),
                },
                "`x` is a sensitive path; approve `y`, `z` to write it",
            ),
            (
                T::ApplyCaseCollision {
                    path: s("x"),
                    existing: s("X"),
                },
                "`x` collides with existing `X` when case is ignored",
            ),
            (
                T::ApplyDuplicate { path: s("x") },
                "`x` appears twice in the plan",
            ),
            (
                T::ApplyMerge { path: s("x") },
                "merge into existing `x` is not supported yet",
            ),
            (
                T::ApplyWindows { path: s("x") },
                "`x`: writes are not supported on Windows yet; the file-system layer resolves rename, delete and create-directory through absolute paths that a junction swap can redirect",
            ),
            (T::ApplyIo { detail: s("x") }, "x"),
            (T::ApplyQuotedPath { path: s("x") }, "`x`"),
            (
                T::ApplyPathIo {
                    path: s("x"),
                    detail: s("y"),
                },
                "x: y",
            ),
            (
                T::ApplyEditCount { count: 9, limit: 7 },
                "9 edits exceed the limit of 7",
            ),
            (
                T::ApplyInsertedSize { count: 9, limit: 7 },
                "9 inserted bytes exceed the cap of 7",
            ),
            (
                T::ApplyContentMissing { path: s("x") },
                "`x` has no content",
            ),
            (T::ApplyNoDirectory { path: s("x") }, "x: no directory"),
            (
                T::ApplyReservedCharacter { path: s("x") },
                "`x`: stream or reserved character",
            ),
            (
                T::ApplyShortName { path: s("x") },
                "`x`: looks like a Windows 8.3 short name",
            ),
            (
                T::ApplyOutsideRoot { path: s("x") },
                "`x` leaves the project root",
            ),
            (
                T::ApplyParentType {
                    path: s("x"),
                    component: s("y"),
                    detail: s("z"),
                },
                "`x`: `y` is not a plain directory (z)",
            ),
            (
                T::ApplyDirectoryMissing { path: s("x") },
                "x: directory is missing",
            ),
            (
                T::ApplyTemporaryName { path: s("x") },
                "x: no free temporary name",
            ),
        ];
        let registered = entries();
        assert_eq!(T::entries().len(), table.len());
        for (value, expected) in table {
            assert_eq!(value.to_string(), expected);
            assert!(registered.iter().any(|entry| entry.code == value.code()));
        }
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn phrases_keep_their_wording_and_are_registered() {
        use TransportPhrase as P;

        let table = [
            (P::OciNoRepository, "no repository"),
            (P::OciBadHost, "bad registry host"),
            (P::OciBadRepository, "bad repository name"),
            (P::OciBadTag, "bad tag"),
            (P::OciTargetRequired, "needs a tag or a digest"),
            (P::OciLocationUnusable, "unusable Location"),
            (P::OciTargetInsecure, "target is not HTTPS"),
            (
                P::OciRedirectMethod,
                "redirect on a request that is not GET or HEAD",
            ),
            (P::OciRedirectCount, "more than 5 redirects"),
            (P::OciLocationMissing, "no Location header"),
            (P::OciRealmMissing, "bearer challenge without realm"),
            (P::OciTokenJson, "token response is not JSON"),
            (P::OciUploadLocation, "upload response without Location"),
            (P::OciUploadHost, "upload target is on another host"),
            (
                P::OciRegistryUnsafe,
                "registry name is not safe to pass to a credential helper",
            ),
            (P::OciHelperStdout, "no helper stdout"),
            (P::OciHelperReader, "helper reader failed"),
            (P::OciHelperUnfinished, "helper did not finish"),
            (
                P::OciHelperIdentityToken,
                "identity tokens from credential helpers are not supported",
            ),
            (P::OciAuthBase64, "an `auth` entry is not base64 text"),
            (P::OciAuthColon, "an `auth` entry has no colon"),
            (P::OciDockerConfig, "Docker config"),
            (P::OciRegistryAuthFile, "registry auth file"),
            (P::OciResponse, "response"),
            (P::OciArchive, "archive"),
            (P::OciBlob, "blob"),
            (P::OciManifest, "manifest"),
            (P::OciReferrersList, "referrers list"),
            (P::OciReferrersIndex, "referrers index"),
            (P::OciTagList, "tag list"),
            (P::OciTokenResponse, "token response"),
            (P::OciMediaNone, "none"),
            (P::ExtractPathUtf8, "entry path is not UTF-8"),
            (P::ExtractPathColon, "colon in path"),
            (P::ExtractCreateStaging, "creating the staging directory"),
            (P::ExtractCreateTree, "creating the tree directory"),
            (P::ExtractRemoveStaging, "removing the staging directory"),
            (P::ExtractCreateDirectory, "creating a directory"),
            (P::ExtractSparse, "sparse entries are not accepted"),
            (P::ExtractLongName, "a long name describes no entry"),
            (
                P::ExtractCreateExecutableList,
                "creating the executable list",
            ),
            (P::ExtractWriteExecutableList, "writing the executable list"),
            (P::ExtractPaxUtf8, "PAX key is not UTF-8"),
            (P::ExtractTwoNames, "two names describe the same entry"),
            (P::ExtractStoreTree, "storing the tree"),
            (P::ExtractSealTree, "sealing the tree"),
            (P::ExtractReadDirectory, "reading a directory"),
            (P::ExtractInspectEntry, "inspecting an entry"),
            (P::ExtractSealDirectory, "sealing a directory"),
            (P::ExtractSealFile, "sealing a file"),
            (P::ExtractNotRegular, "not a regular file"),
            (P::ExtractInspectRoot, "inspecting the tree root"),
            (
                P::ExtractRootType,
                "the tree root is a link or not a directory",
            ),
            (P::ExtractNameUtf8, "a file name is not UTF-8"),
            (
                P::ExtractExecutableUnlisted,
                "a file has the executable bit but is not listed",
            ),
            (
                P::ExtractExecutableBit,
                "a listed file lost its executable bit",
            ),
            (P::ExtractReadExecutableList, "reading the executable list"),
            (
                P::ExtractExecutableLine,
                "the executable list has a bad line",
            ),
            (
                P::ExtractExecutableOrder,
                "the executable list is not sorted and unique",
            ),
            (
                P::ExtractExecutableMissing,
                "the executable list names a missing file",
            ),
            (P::ExtractExecutableSelf, "the executable list names itself"),
            (P::ApplySourceUtf8, "source is not UTF-8"),
            (
                P::ApplySpanCharacter,
                "a span is outside the text or inside a character",
            ),
            (P::ApplySpanCrlf, "a span splits a CRLF pair"),
            (P::ApplyOverlap, "edits overlap"),
            (P::ApplySpanRange, "a span is outside the text"),
            (P::ApplyNonblock, "O_NONBLOCK does not fit"),
            (P::ApplyGitDirectory, "git directory"),
            (P::ApplyState, "slopvac state"),
            (P::ApplyCiWorkflow, "CI workflow"),
            (P::ApplyEnvironment, "environment file"),
            (P::ApplyGitConfig, "git configuration"),
            (P::ApplyToolConfig, "tool configuration"),
            (P::ApplyEditorTask, "editor task file"),
        ];
        let registered = entries();
        assert_eq!(P::entries().len(), table.len());
        for (value, expected) in table {
            assert_eq!(value.to_string(), expected);
            assert_eq!(value.as_static(), expected);
            assert!(registered.iter().any(|entry| entry.code == value.code()));
        }
    }

    #[test]
    fn credential_helper_name_still_escapes_terminal_controls() {
        assert_eq!(
            helper_project_unknown("docker-credential-\u{1b}[31mtest"),
            "credential helper `docker-credential-\\u{1b}[31mtest` was not run: the project directory is unknown",
        );
    }
}
