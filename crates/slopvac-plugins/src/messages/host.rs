//! The messages of the plugin host: its errors, protocol framing, process, launcher, budget,
//! hook result checks and recipe path checks.
//!
//! [`HostMessage`] has one entry per published code of the host. `HostText` holds sentences with
//! parameters and `HostPhrase` holds fixed phrases that callers read as `&'static str`.

use std::io;
use std::time::Duration;

use slopvac_messages::{Catalog, Entry};
use slopvac_sanitize::{line as esc, terminal};

use crate::error::RpcError;

/// The error codes of the plugin host, one per code a [`crate::PluginError`] reports.
///
/// The text of each entry is the sentence the host prints for that failure. The eight codes that
/// a plugin's JSON-RPC error object can map to (`parse-error` and the rest) wrap the whole
/// sentence of the `Rpc` variant as `detail`.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum HostMessage {
    /// The content hash has no recorded trust.
    #[code("plugin-untrusted")]
    #[message("plugin {plugin} is not trusted; run `slopvac plugins trust` for it")]
    PluginUntrusted {
        /// Plugin name, escaped.
        plugin: String,
    },
    /// Trust records exist but the key they were made under is gone.
    #[code("trust-key-missing")]
    #[message(
        "the trust key is missing while trust records exist, so plugin {plugin} cannot be checked; run `slopvac plugins trust` for it to trust it again"
    )]
    TrustKeyMissing {
        /// Plugin name, escaped.
        plugin: String,
    },
    /// The trust records were made under another key than the store's.
    #[code("trust-key-mismatch")]
    #[message(
        "the trust key changed after plugin {plugin} was trusted, so it cannot be checked; run `slopvac plugins trust` for it to trust it again"
    )]
    TrustKeyMismatch {
        /// Plugin name, escaped.
        plugin: String,
    },
    /// The trust key file is not private to the user or does not hold a key.
    #[code("trust-key-unusable")]
    #[message(
        "the trust key cannot be used for plugin {plugin}; fix the file, or delete it and run `slopvac plugins trust` for each plugin"
    )]
    TrustKeyUnusable {
        /// Plugin name, escaped.
        plugin: String,
    },
    /// The installed bytes differ from the hash that trust recorded.
    #[code("plugin-hash-mismatch")]
    #[message(
        "plugin {plugin} changed after it was trusted; run `slopvac plugins sync` to restore the verified files, and `slopvac plugins trust` to approve new content"
    )]
    HashMismatch {
        /// Plugin name, escaped.
        plugin: String,
    },
    /// A timer of the protocol expired.
    #[code("plugin-timeout")]
    #[message("plugin {plugin} timed out: {what}")]
    Timeout {
        /// Plugin name, escaped.
        plugin: String,
        /// Which timer expired, escaped.
        what: String,
    },
    /// The process ended with requests pending.
    #[code("plugin-exited")]
    #[message("plugin {plugin} exited ({status}){stderr}")]
    Exited {
        /// Plugin name, escaped.
        plugin: String,
        /// Exit status description, escaped.
        status: String,
        /// The stderr tail with a leading newline, or empty, escaped.
        stderr: String,
    },
    /// A framing error, a limit breach or a duplicate key.
    #[code("plugin-protocol-violation")]
    #[message("plugin protocol violation: {detail}")]
    ProtocolViolation {
        /// What broke the protocol, escaped.
        detail: String,
    },
    /// A result does not match its schema or breaks a rule such as span bounds.
    #[code("plugin-output-invalid")]
    #[message("plugin output invalid: {detail}")]
    OutputInvalid {
        /// What is invalid, escaped.
        detail: String,
    },
    /// The program did not start.
    #[code("plugin-spawn-failed")]
    #[message("plugin failed to start: {detail}")]
    SpawnFailed {
        /// Why it did not start, escaped.
        detail: String,
    },
    /// The running program never installed the plugin launcher.
    #[code("launcher-not-installed")]
    #[message(
        "the running program did not install the slopvac plugin launcher, so plugins and git plugin sources cannot start"
    )]
    LauncherNotInstalled,
    /// The reply disagrees with the hashed manifest.
    #[code("plugin-declaration-mismatch")]
    #[message("plugin declaration mismatch: {detail}")]
    DeclarationMismatch {
        /// What disagrees, escaped.
        detail: String,
    },
    /// The request counter reached its limit.
    #[code("request-id-exhausted")]
    #[message("request ids exhausted")]
    RequestIdExhausted,
    /// No common protocol version.
    #[code("protocol-version-unsupported")]
    #[message("no common protocol version: host speaks {host}, plugin speaks {plugin}")]
    ProtocolVersionUnsupported {
        /// Host range, escaped.
        host: String,
        /// Plugin range as reported, escaped.
        plugin: String,
    },
    /// The host lacks a feature the plugin requires.
    #[code("required-feature-missing")]
    #[message("plugin requires feature `{feature}`, which the host does not offer")]
    RequiredFeatureMissing {
        /// The feature name, escaped.
        feature: String,
    },
    /// The host cancelled the request and discarded the answer.
    #[code("request-cancelled")]
    #[message("request cancelled")]
    RequestCancelled,
    /// The hook or document does not fit a message and cannot be split.
    #[code("message-too-large")]
    #[message("message too large: {detail}")]
    MessageTooLarge {
        /// What does not fit, escaped.
        detail: String,
    },
    /// The caller used the plugin wrongly, for example an undeclared hook.
    #[code("plugin-usage")]
    #[message("invalid use of plugin: {detail}")]
    PluginUsage {
        /// What is wrong, escaped.
        detail: String,
    },
    /// The plugin answered with the JSON-RPC code for malformed JSON.
    #[code("parse-error")]
    #[message("{detail}")]
    RpcParseError {
        /// The plugin error sentence.
        detail: String,
    },
    /// The plugin answered with the JSON-RPC code for an invalid request.
    #[code("invalid-request")]
    #[message("{detail}")]
    RpcInvalidRequest {
        /// The plugin error sentence.
        detail: String,
    },
    /// The plugin answered with the JSON-RPC code for an unknown method.
    #[code("method-not-found")]
    #[message("{detail}")]
    RpcMethodNotFound {
        /// The plugin error sentence.
        detail: String,
    },
    /// The plugin answered with the JSON-RPC code for invalid parameters.
    #[code("invalid-params")]
    #[message("{detail}")]
    RpcInvalidParams {
        /// The plugin error sentence.
        detail: String,
    },
    /// The plugin answered that it is not initialized.
    #[code("not-initialized")]
    #[message("{detail}")]
    RpcNotInitialized {
        /// The plugin error sentence.
        detail: String,
    },
    /// The plugin answered that the document is invalid.
    #[code("document-invalid")]
    #[message("{detail}")]
    RpcDocumentInvalid {
        /// The plugin error sentence.
        detail: String,
    },
    /// The plugin answered that it needs the network while offline mode is on.
    #[code("offline")]
    #[message("{detail}")]
    RpcOffline {
        /// The plugin error sentence.
        detail: String,
    },
    /// The plugin answered with a code the contract does not define.
    #[code("internal-error")]
    #[message("{detail}")]
    RpcInternalError {
        /// The plugin error sentence.
        detail: String,
    },
}

/// Sentences with parameters: failure details of the host, framing, the launcher, hook results
/// and recipe paths.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum HostText {
    /// The plugin answered a request with an error object.
    #[code("plugins-host-rpc-error")]
    #[text("plugin error {code}: {message} ({name})")]
    RpcError {
        /// The numeric JSON-RPC code.
        code: String,
        /// The message the plugin sent, escaped.
        message: String,
        /// The code the host reports.
        name: String,
    },
    /// A detail that names the plugin it belongs to.
    #[code("plugins-host-named")]
    #[text("{name}: {detail}")]
    Named {
        /// Plugin name.
        name: String,
        /// The detail.
        detail: String,
    },
    /// The stderr tail of a plugin, after a line break.
    #[code("plugins-host-stderr-tail")]
    #[text("stderr:\n{text}")]
    StderrTail {
        /// The last lines of standard error.
        text: String,
    },
    /// An exit status followed by the resource limit the plugin hit.
    #[code("plugins-host-status-limit")]
    #[text("{status}: {limit}")]
    StatusLimit {
        /// The exit status description.
        status: String,
        /// The limit that was hit.
        limit: String,
    },
    /// A plugin sent more unsolicited messages than allowed.
    #[code("plugins-host-unsolicited-cap")]
    #[text("more than {limit} unsolicited messages")]
    UnsolicitedCap {
        /// The cap.
        #[count]
        limit: u32,
    },
    /// A message could not be encoded.
    #[code("plugins-host-encode-message")]
    #[text("cannot encode message: {error}")]
    EncodeMessage {
        /// The encoder error.
        error: String,
    },
    /// A message is larger than the negotiated limit.
    #[code("plugins-host-bytes-exceed")]
    #[text("{bytes} bytes exceed the limit of {max}")]
    BytesExceed {
        /// Size of the message.
        #[count]
        bytes: usize,
        /// The limit.
        #[count]
        max: usize,
    },
    /// A request got no reply before its deadline.
    #[code("plugins-host-method-no-reply")]
    #[text("`{method}` got no reply")]
    MethodNoReply {
        /// The method name.
        method: String,
    },
    /// A request ignored the cancel.
    #[code("plugins-host-method-ignored-cancel")]
    #[text("`{method}` ignored its cancel")]
    MethodIgnoredCancel {
        /// The method name.
        method: String,
    },
    /// A request passed its deadline.
    #[code("plugins-host-method-passed-deadline")]
    #[text("`{method}` passed its deadline")]
    MethodPassedDeadline {
        /// The method name.
        method: String,
    },
    /// The reply and the manifest disagree on network use.
    #[code("plugins-host-network-differs")]
    #[text("reply says requiresNetwork={reply}, manifest says network={manifest}")]
    NetworkDiffers {
        /// What the reply says.
        reply: String,
        /// What the manifest says.
        manifest: String,
    },
    /// A required feature is not required in the manifest.
    #[code("plugins-host-feature-not-required")]
    #[text("feature `{feature}` is not required in the manifest")]
    FeatureNotRequired {
        /// The feature name.
        feature: String,
    },
    /// An optional feature is not optional in the manifest.
    #[code("plugins-host-feature-not-optional")]
    #[text("feature `{feature}` is not optional in the manifest")]
    FeatureNotOptional {
        /// The feature name.
        feature: String,
    },
    /// A hook of the reply is not in the manifest.
    #[code("plugins-host-hook-not-in-manifest")]
    #[text("hook {kind}/{id} is not in the manifest")]
    HookNotInManifest {
        /// The hook kind.
        kind: String,
        /// The hook id.
        id: String,
    },
    /// A limit of the reply is outside the range the host allows.
    #[code("plugins-host-limit-out-of-range")]
    #[text("{field} {value} is outside the allowed range")]
    LimitOutOfRange {
        /// The limit field.
        field: String,
        /// The value the reply gave.
        #[count]
        value: u64,
    },
    /// The initialize result does not parse.
    #[code("plugins-host-initialize-result")]
    #[text("initialize result: {error}")]
    InitializeResult {
        /// The parse error.
        error: String,
    },
    /// A hook that the plugin did not offer was called.
    #[code("plugins-host-hook-not-offered")]
    #[text("{name}: hook {kind}/{id} was not offered")]
    HookNotOffered {
        /// Plugin name.
        name: String,
        /// The hook kind.
        kind: String,
        /// The hook id.
        id: String,
    },
    /// The wall-clock cap expired.
    #[code("plugins-host-wall-clock-cap")]
    #[text("the wall-clock cap of {cap} expired")]
    WallClockCap {
        /// The cap, as a debug-formatted duration.
        cap: String,
    },
    /// A frame stalled outside any request.
    #[code("plugins-host-frame-stalled")]
    #[text("a frame stalled for {stall} outside any request")]
    FrameStalled {
        /// The stall limit, as a debug-formatted duration.
        stall: String,
    },
    /// The plugin hit the CPU time limit.
    #[code("plugins-host-cpu-limit")]
    #[text("the CPU time limit of {limit} was reached")]
    CpuLimit {
        /// The limit, as a debug-formatted duration.
        limit: String,
    },
    /// The plugin hit the file size limit.
    #[code("plugins-host-file-limit")]
    #[text("the file size limit of {limit} bytes was reached")]
    FileLimit {
        /// The limit in bytes.
        #[count]
        limit: u64,
    },
    /// A header line is too long.
    #[code("plugins-frame-header-too-long")]
    #[text("header line longer than {max} bytes")]
    HeaderTooLong {
        /// The limit.
        #[count]
        max: usize,
    },
    /// A header block has too many lines.
    #[code("plugins-frame-too-many-headers")]
    #[text("more than {max} header lines")]
    TooManyHeaders {
        /// The limit.
        #[count]
        max: usize,
    },
    /// A body is larger than the limit.
    #[code("plugins-frame-body-too-long")]
    #[text("body of {len} bytes exceeds the limit of {max}")]
    BodyTooLong {
        /// Declared size.
        #[count]
        len: usize,
        /// The limit.
        #[count]
        max: usize,
    },
    /// Reading from the plugin failed.
    #[code("plugins-frame-read-failed")]
    #[text("read failed: {error}")]
    ReadFailed {
        /// The I/O error.
        error: String,
    },
    /// Waiting for the leader of the process group failed.
    #[code("plugins-process-wait-failed")]
    #[text("wait failed: {error}")]
    WaitFailed {
        /// The OS error.
        error: String,
    },
    /// The whole-run budget is used up.
    #[code("plugins-budget-exceeded")]
    #[text("whole-run budget of {cap} {what} exceeded")]
    BudgetExceeded {
        /// The cap.
        #[count]
        cap: u64,
        /// What the cap counts.
        what: String,
    },
    /// A document does not fit a message.
    #[code("plugins-api-document-too-large")]
    #[text("document `{id}` exceeds the message limit")]
    DocumentTooLarge {
        /// The document id.
        id: String,
    },
    /// A document could not be encoded.
    #[code("plugins-api-encode-document")]
    #[text("cannot encode a document: {error}")]
    EncodeDocument {
        /// The encoder error.
        error: String,
    },
    /// A result entry misses its key.
    #[code("plugins-hooks-entry-key-missing")]
    #[text("a result entry has no string `{key}`")]
    EntryKeyMissing {
        /// The key.
        key: String,
    },
    /// A result names an item that was not sent.
    #[code("plugins-hooks-result-not-requested")]
    #[text("result for `{id}`, which was not requested")]
    ResultNotRequested {
        /// The id.
        id: String,
    },
    /// A result appears twice.
    #[code("plugins-hooks-result-duplicate")]
    #[text("duplicate result for `{id}`")]
    ResultDuplicate {
        /// The id.
        id: String,
    },
    /// A sent item has no result.
    #[code("plugins-hooks-result-missing")]
    #[text("no result for `{id}`")]
    ResultMissing {
        /// The id.
        id: String,
    },
    /// A field is not an array.
    #[code("plugins-hooks-field-not-array")]
    #[text("`{field}` is not an array")]
    FieldNotArray {
        /// The field name.
        field: String,
    },
    /// A value does not parse.
    #[code("plugins-hooks-parse-failed")]
    #[text("{what}: {error}")]
    ParseFailed {
        /// What was parsed.
        what: String,
        /// The parse error.
        error: String,
    },
    /// A tag kind is not kebab-case.
    #[code("plugins-hooks-tag-kind")]
    #[text("tag kind `{kind}` is not kebab-case")]
    TagKind {
        /// The kind.
        kind: String,
    },
    /// A fixer sent too many edits.
    #[code("plugins-hooks-edits-exceed")]
    #[text("{count} edits exceed the limit of {max}")]
    EditsExceed {
        /// The number of edits.
        #[count]
        count: usize,
        /// The limit.
        #[count]
        max: usize,
    },
    /// An edit names a finding that does not exist.
    #[code("plugins-hooks-edit-missing-finding")]
    #[text("edit names missing finding {finding}")]
    EditMissingFinding {
        /// The finding index.
        #[count]
        finding: u64,
    },
    /// An edit lies outside its finding.
    #[code("plugins-hooks-edit-outside-finding")]
    #[text("edit lies outside finding {index}")]
    EditOutsideFinding {
        /// The finding index.
        #[count]
        index: usize,
    },
    /// The edits insert more bytes than the cap.
    #[code("plugins-hooks-inserted-exceed")]
    #[text("{inserted} inserted bytes exceed the cap of {cap}")]
    InsertedExceed {
        /// The inserted bytes.
        #[count]
        inserted: usize,
        /// The cap.
        #[count]
        cap: usize,
    },
    /// A path character is reserved on Windows.
    #[code("plugins-hooks-path-reserved-char")]
    #[text("character `{character}` is reserved on Windows")]
    PathReservedChar {
        /// The character.
        character: String,
    },
    /// A path segment is not a normal name.
    #[code("plugins-hooks-segment-not-normal")]
    #[text("segment `{segment}` is not a normal name")]
    SegmentNotNormal {
        /// The segment.
        segment: String,
    },
    /// A path segment is a reserved name.
    #[code("plugins-hooks-reserved-name")]
    #[text("reserved name `{segment}`")]
    ReservedName {
        /// The segment.
        segment: String,
    },
    /// A recipe path is refused.
    #[code("plugins-hooks-recipe-path")]
    #[text("recipe path `{path}`: {reason}")]
    RecipePath {
        /// The path.
        #[display_path]
        path: String,
        /// Why it is refused.
        reason: String,
    },
    /// A recipe file has no content.
    #[code("plugins-hooks-recipe-no-content")]
    #[text("recipe file `{path}` has no content")]
    RecipeNoContent {
        /// The path.
        #[display_path]
        path: String,
    },
    /// A recipe path appears twice.
    #[code("plugins-hooks-recipe-path-twice")]
    #[text("recipe path `{path}` appears twice")]
    RecipePathTwice {
        /// The path.
        #[display_path]
        path: String,
    },
    /// The project root cannot be resolved.
    #[code("plugins-hooks-project-root")]
    #[text("project root: {error}")]
    ProjectRoot {
        /// The OS error.
        error: String,
    },
    /// A symlink cannot be resolved.
    #[code("plugins-hooks-symlink")]
    #[text("symlink `{path}`: {error}")]
    Symlink {
        /// The path.
        #[display_path]
        path: String,
        /// The OS error.
        error: String,
    },
    /// A path leaves the project root through a symlink.
    #[code("plugins-hooks-leaves-root")]
    #[text("`{path}` leaves the project root through a symlink")]
    LeavesRoot {
        /// The path.
        #[display_path]
        path: String,
    },
    /// A path component cannot be checked.
    #[code("plugins-hooks-path-error")]
    #[text("`{path}`: {error}")]
    PathError {
        /// The path.
        #[display_path]
        path: String,
        /// The OS error.
        error: String,
    },
    /// What the launcher prints when it fails.
    #[code("plugins-launch-failure")]
    #[text("slopvac plugin launcher: {message}")]
    LaunchFailure {
        /// What failed.
        message: String,
    },
    /// An argument of the launcher is malformed.
    #[code("plugins-launch-malformed-arg")]
    #[text("malformed `{key}` argument")]
    MalformedArg {
        /// The argument key.
        key: String,
    },
    /// A resource limit cannot be set.
    #[code("plugins-launch-set-limit")]
    #[text("cannot set the {name} limit: {error}")]
    SetLimit {
        /// The limit name.
        name: String,
        /// The OS error.
        error: String,
    },
    /// The plugin cannot be run.
    #[code("plugins-launch-run-failed")]
    #[text("cannot run the plugin: {error}")]
    RunFailed {
        /// The OS error.
        error: String,
    },
    /// The launcher cannot become a child subreaper.
    #[code("plugins-launch-subreaper")]
    #[text("cannot become a child subreaper: {error}")]
    #[cfg_attr(
        not(target_os = "linux"),
        allow(dead_code, reason = "only the Linux launcher reports this")
    )]
    Subreaper {
        /// The OS error.
        error: String,
    },
    /// The launcher cannot refuse tracing.
    #[code("plugins-launch-refuse-tracing")]
    #[text("cannot refuse tracing: {error}")]
    #[cfg_attr(
        not(target_os = "linux"),
        allow(dead_code, reason = "only the Linux launcher reports this")
    )]
    RefuseTracing {
        /// The OS error.
        error: String,
    },
    /// The launcher lost track of the plugin.
    #[code("plugins-launch-lost-plugin")]
    #[text("lost the plugin: {error}")]
    #[cfg_attr(
        not(target_os = "linux"),
        allow(dead_code, reason = "only the Linux launcher reports this")
    )]
    LostPlugin {
        /// The OS error.
        error: String,
    },
    /// The OS cannot name the running executable.
    #[code("plugins-launch-current-exe")]
    #[text("cannot find the running executable: {error}")]
    CurrentExe {
        /// The OS error.
        error: String,
    },
    /// The usage line of the launcher program.
    #[code("plugins-launch-usage")]
    #[text("usage: slopvac-plugin-launcher {flag} ... (started by the plugin host only)")]
    LaunchUsage {
        /// The launcher flag.
        flag: String,
    },
}

/// Fixed phrases of the host, read as `&'static str`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum HostPhrase {
    /// The plugin has shut down.
    #[code("plugins-host-shut-down")]
    #[text("the plugin has shut down")]
    ShutDown,
    /// The exit status is not known.
    #[code("plugins-host-status-unknown")]
    #[text("status unknown")]
    StatusUnknown,
    /// The plugin is closed.
    #[code("plugins-host-closed")]
    #[text("plugin is closed")]
    Closed,
    /// The plugin handle was dropped.
    #[code("plugins-host-dropped")]
    #[text("plugin dropped")]
    Dropped,
    /// A plugin message is not a JSON object.
    #[code("plugins-host-not-object")]
    #[text("message is not a JSON object")]
    NotObject,
    /// A plugin message does not carry the JSON-RPC version.
    #[code("plugins-host-bad-jsonrpc")]
    #[text("`jsonrpc` is not \"2.0\"")]
    BadJsonrpc,
    /// A response id is out of range.
    #[code("plugins-host-bad-id")]
    #[text("response id is not an integer from 1 to 2^53-1")]
    BadId,
    /// A message has neither method nor id.
    #[code("plugins-host-no-method-or-id")]
    #[text("message has neither `method` nor `id`")]
    NoMethodOrId,
    /// A response has both or neither of result and error.
    #[code("plugins-host-result-or-error")]
    #[text("response needs exactly one of `result` and `error`")]
    ResultOrError,
    /// The run budget is exceeded.
    #[code("plugins-host-budget-exceeded")]
    #[text("whole-run budget exceeded")]
    BudgetExceeded,
    /// The standard output volume cap was reached.
    #[code("plugins-host-stdout-cap")]
    #[text("standard output volume cap reached")]
    StdoutCap,
    /// The standard error volume cap was reached.
    #[code("plugins-host-stderr-cap")]
    #[text("standard error volume cap reached")]
    StderrCap,
    /// A write to the plugin blocked.
    #[code("plugins-host-write-blocked")]
    #[text("the write to the plugin blocked")]
    WriteBlocked,
    /// No request slot became free.
    #[code("plugins-host-no-slot")]
    #[text("no request slot became free")]
    NoSlot,
    /// The reply carries no supported version.
    #[code("plugins-host-unknown")]
    #[text("unknown")]
    Unknown,
    /// The process has no pipes.
    #[code("plugins-host-missing-pipes")]
    #[text("missing pipes")]
    MissingPipes,
    /// The stream ended inside a header line.
    #[code("plugins-frame-end-in-header-line")]
    #[text("stream ended inside a header line")]
    EndInHeaderLine,
    /// A header line does not end in CRLF.
    #[code("plugins-frame-no-crlf")]
    #[text("header line does not end in CRLF")]
    NoCrlf,
    /// A header line holds a stray CR or LF.
    #[code("plugins-frame-stray-cr-lf")]
    #[text("stray CR or LF in header line")]
    StrayCrLf,
    /// Content-Length is not a plain decimal number.
    #[code("plugins-frame-length-not-decimal")]
    #[text("Content-Length is not a plain decimal number")]
    LengthNotDecimal,
    /// Content-Length has leading zeros.
    #[code("plugins-frame-length-leading-zeros")]
    #[text("Content-Length has leading zeros")]
    LengthLeadingZeros,
    /// Content-Length does not fit 64 bits.
    #[code("plugins-frame-length-overflow-64")]
    #[text("Content-Length overflows 64 bits")]
    LengthOverflow64,
    /// Content-Length does not fit the platform size.
    #[code("plugins-frame-length-overflow-size")]
    #[text("Content-Length overflows the platform size")]
    LengthOverflowSize,
    /// The stream ended inside a header block.
    #[code("plugins-frame-end-in-header-block")]
    #[text("stream ended inside a header block")]
    EndInHeaderBlock,
    /// A header line has no colon.
    #[code("plugins-frame-no-colon")]
    #[text("header line has no colon")]
    NoColon,
    /// Content-Length appears twice.
    #[code("plugins-frame-duplicate-length")]
    #[text("duplicate Content-Length")]
    DuplicateLength,
    /// Content-Length is missing.
    #[code("plugins-frame-missing-length")]
    #[text("missing Content-Length")]
    MissingLength,
    /// The stream ended inside a body.
    #[code("plugins-frame-end-in-body")]
    #[text("stream ended inside a body")]
    EndInBody,
    /// What the standard output budget counts.
    #[code("plugins-budget-stdout-bytes")]
    #[text("standard output bytes")]
    BudgetStdoutBytes,
    /// What the standard error budget counts.
    #[code("plugins-budget-stderr-bytes")]
    #[text("standard error bytes")]
    BudgetStderrBytes,
    /// What the unsolicited message budget counts.
    #[code("plugins-budget-unsolicited")]
    #[text("unsolicited messages")]
    BudgetUnsolicited,
    /// The error object has no code.
    #[code("plugins-hooks-error-code-missing")]
    #[text("error.code is missing or not an integer")]
    ErrorCodeMissing,
    /// The error object has no message.
    #[code("plugins-hooks-error-message-missing")]
    #[text("error.message is missing")]
    ErrorMessageMissing,
    /// The error object has no kebab-case plugin code.
    #[code("plugins-hooks-error-plugin-code")]
    #[text("error.data.slopvac_code is missing or not kebab-case")]
    ErrorPluginCode,
    /// The results are missing.
    #[code("plugins-hooks-results-missing")]
    #[text("`results` is missing or not an array")]
    ResultsMissing,
    /// A tag span is outside the text.
    #[code("plugins-hooks-tag-span")]
    #[text("tag span is outside the text or inside a character")]
    TagSpan,
    /// A tag confidence is out of range.
    #[code("plugins-hooks-tag-confidence")]
    #[text("tag confidence is outside 0..=1")]
    TagConfidence,
    /// A segment context is not kebab-case.
    #[code("plugins-hooks-segment-context")]
    #[text("segment context is not kebab-case")]
    SegmentContext,
    /// A segment span is outside the text.
    #[code("plugins-hooks-segment-span")]
    #[text("segment span is outside the text or inside a character")]
    SegmentSpan,
    /// A score is not a number.
    #[code("plugins-hooks-score-not-number")]
    #[text("score is not a number")]
    ScoreNotNumber,
    /// A score is negative.
    #[code("plugins-hooks-score-negative")]
    #[text("score is negative")]
    ScoreNegative,
    /// An edit span is outside the text.
    #[code("plugins-hooks-edit-span")]
    #[text("edit span is outside the text or inside a character")]
    EditSpan,
    /// Edits overlap.
    #[code("plugins-hooks-edits-overlap")]
    #[text("edits overlap")]
    EditsOverlap,
    /// A provider entry has neither error nor text and model.
    #[code("plugins-hooks-provider-entry")]
    #[text("a provider entry without `error` needs `text` and `model`")]
    ProviderEntry,
    /// The recipe files are missing.
    #[code("plugins-hooks-files-missing")]
    #[text("`files` is missing or not an array")]
    FilesMissing,
    /// A recipe path is empty.
    #[code("plugins-hooks-path-empty")]
    #[text("empty path")]
    PathEmpty,
    /// A recipe path is too long.
    #[code("plugins-hooks-path-too-long")]
    #[text("path longer than 1024 bytes")]
    PathTooLong,
    /// A recipe path is absolute or has a backslash.
    #[code("plugins-hooks-path-absolute")]
    #[text("absolute path or backslash")]
    PathAbsolute,
    /// A recipe path has a control character.
    #[code("plugins-hooks-path-control")]
    #[text("control character in path")]
    PathControl,
    /// A recipe path starts with a drive letter.
    #[code("plugins-hooks-path-drive")]
    #[text("drive letter")]
    PathDrive,
    /// A recipe path has too many segments.
    #[code("plugins-hooks-path-segments")]
    #[text("more than 32 path segments")]
    PathSegments,
    /// A recipe path segment ends in a dot or space.
    #[code("plugins-hooks-segment-dot-space")]
    #[text("segment ends in a dot or space")]
    SegmentDotSpace,
    /// The launcher arguments are malformed.
    #[code("plugins-launch-malformed-args")]
    #[text("malformed arguments")]
    MalformedArgs,
    /// The plugin program is not an absolute path.
    #[code("plugins-launch-not-absolute")]
    #[text("the plugin program is not an absolute path")]
    ProgramNotAbsolute,
    /// The launcher runs on Unix only.
    #[code("plugins-launch-unix-only")]
    #[text("the launcher runs on Unix only")]
    #[cfg_attr(
        unix,
        allow(dead_code, reason = "only the non-Unix launcher reports this")
    )]
    UnixOnly,
    /// The running program never installed the launcher.
    #[code("plugins-launch-not-installed")]
    #[text("the running program did not install the slopvac plugin launcher")]
    NotInstalled,
    /// The name of the core size limit.
    #[code("plugins-launch-limit-core")]
    #[text("core size")]
    LimitCore,
    /// The name of the CPU time limit.
    #[code("plugins-launch-limit-cpu")]
    #[text("CPU time")]
    LimitCpu,
    /// The name of the open file limit.
    #[code("plugins-launch-limit-open-file")]
    #[text("open file")]
    LimitOpenFile,
    /// The name of the file size limit.
    #[code("plugins-launch-limit-file-size")]
    #[text("file size")]
    LimitFileSize,
    /// The name of the memory limit.
    #[code("plugins-launch-limit-memory")]
    #[text("memory")]
    #[cfg_attr(
        not(target_os = "linux"),
        allow(dead_code, reason = "only the Linux launcher reports this")
    )]
    LimitMemory,
}

/// Every host catalog, concatenated.
pub(super) fn entries() -> Vec<Entry> {
    [
        HostMessage::entries(),
        HostText::entries(),
        HostPhrase::entries(),
    ]
    .concat()
}

pub(crate) fn untrusted(plugin: &str) -> String {
    HostMessage::PluginUntrusted {
        plugin: esc(plugin),
    }
    .to_string()
}

pub(crate) fn trust_key_missing(plugin: &str) -> String {
    HostMessage::TrustKeyMissing {
        plugin: esc(plugin),
    }
    .to_string()
}

pub(crate) fn trust_key_mismatch(plugin: &str) -> String {
    HostMessage::TrustKeyMismatch {
        plugin: esc(plugin),
    }
    .to_string()
}

pub(crate) fn trust_key_unusable(plugin: &str) -> String {
    HostMessage::TrustKeyUnusable {
        plugin: esc(plugin),
    }
    .to_string()
}

pub(crate) fn hash_mismatch(plugin: &str) -> String {
    HostMessage::HashMismatch {
        plugin: esc(plugin),
    }
    .to_string()
}

pub(crate) fn timeout(plugin: &str, what: &str) -> String {
    HostMessage::Timeout {
        plugin: esc(plugin),
        what: esc(what),
    }
    .to_string()
}

pub(crate) fn exited(plugin: &str, status: &str, stderr: &str) -> String {
    HostMessage::Exited {
        plugin: esc(plugin),
        status: esc(status),
        stderr: terminal(stderr),
    }
    .to_string()
}

pub(crate) fn protocol_violation(detail: &str) -> String {
    HostMessage::ProtocolViolation {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn output_invalid(detail: &str) -> String {
    HostMessage::OutputInvalid {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn spawn_failed(detail: &str) -> String {
    HostMessage::SpawnFailed {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn launcher_not_installed() -> String {
    HostMessage::LauncherNotInstalled.to_string()
}

pub(crate) fn declaration_mismatch(detail: &str) -> String {
    HostMessage::DeclarationMismatch {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn request_id_exhausted() -> String {
    HostMessage::RequestIdExhausted.to_string()
}

pub(crate) fn protocol_version_unsupported(host: &str, plugin: &str) -> String {
    HostMessage::ProtocolVersionUnsupported {
        host: esc(host),
        plugin: esc(plugin),
    }
    .to_string()
}

pub(crate) fn required_feature_missing(feature: &str) -> String {
    HostMessage::RequiredFeatureMissing {
        feature: esc(feature),
    }
    .to_string()
}

pub(crate) fn request_cancelled() -> String {
    HostMessage::RequestCancelled.to_string()
}

pub(crate) fn message_too_large(detail: &str) -> String {
    HostMessage::MessageTooLarge {
        detail: esc(detail),
    }
    .to_string()
}

pub(crate) fn plugin_usage(detail: &str) -> String {
    HostMessage::PluginUsage {
        detail: esc(detail),
    }
    .to_string()
}

/// The text of a plugin's error object: its own sentence, under the code the host reports.
pub(crate) fn rpc(error: &RpcError) -> String {
    let detail = HostText::RpcError {
        code: error.code.to_string(),
        message: esc(&error.message),
        name: error.code_name().to_owned(),
    }
    .to_string();
    match error.code_name() {
        "parse-error" => HostMessage::RpcParseError { detail }.to_string(),
        "invalid-request" => HostMessage::RpcInvalidRequest { detail }.to_string(),
        "method-not-found" => HostMessage::RpcMethodNotFound { detail }.to_string(),
        "invalid-params" => HostMessage::RpcInvalidParams { detail }.to_string(),
        "not-initialized" => HostMessage::RpcNotInitialized { detail }.to_string(),
        "document-invalid" => HostMessage::RpcDocumentInvalid { detail }.to_string(),
        "offline" => HostMessage::RpcOffline { detail }.to_string(),
        "internal-error" => HostMessage::RpcInternalError { detail }.to_string(),
        _ => detail,
    }
}

/// `{name}: {detail}`, for a detail that belongs to one plugin.
pub(crate) fn named(name: &str, detail: &str) -> String {
    HostText::Named {
        name: name.to_owned(),
        detail: detail.to_owned(),
    }
    .to_string()
}

pub(crate) fn offline(command: &str) -> String {
    super::offline_network_needed(&esc(command))
}

pub(crate) fn frame_read_failed(error: &io::Error) -> String {
    HostText::ReadFailed {
        error: error.to_string(),
    }
    .to_string()
}

pub(crate) fn current_exe_failed(error: &io::Error) -> String {
    HostText::CurrentExe {
        error: error.to_string(),
    }
    .to_string()
}

/// The stderr tail after the line break that separates it from the status.
pub(crate) fn stderr_tail(text: &str) -> String {
    let tail = HostText::StderrTail {
        text: text.to_owned(),
    };
    format!("\n{tail}")
}

pub(crate) fn status_with_limit(status: &str, limit: &str) -> String {
    HostText::StatusLimit {
        status: status.to_owned(),
        limit: limit.to_owned(),
    }
    .to_string()
}

pub(crate) fn wall_clock_cap(cap: Duration) -> String {
    HostText::WallClockCap {
        cap: format!("{cap:?}"),
    }
    .to_string()
}

pub(crate) fn frame_stalled(stall: Duration) -> String {
    HostText::FrameStalled {
        stall: format!("{stall:?}"),
    }
    .to_string()
}

pub(crate) fn cpu_limit(limit: Duration) -> String {
    HostText::CpuLimit {
        limit: format!("{limit:?}"),
    }
    .to_string()
}

pub(crate) fn file_limit(limit: u64) -> String {
    HostText::FileLimit { limit }.to_string()
}

pub(crate) fn budget_exceeded(cap: u64, what: &str) -> String {
    HostText::BudgetExceeded {
        cap,
        what: what.to_owned(),
    }
    .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(text: &str) -> String {
        text.to_owned()
    }

    /// Every published code, rendered with sample parameters, beside the text the host printed
    /// before the registry existed.
    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn every_published_code_keeps_its_text_and_is_registered() {
        let table: Vec<(HostMessage, &str, &str)> = vec![
            (
                HostMessage::PluginUntrusted { plugin: s("p") },
                "plugin-untrusted",
                "plugin p is not trusted; run `slopvac plugins trust` for it",
            ),
            (
                HostMessage::TrustKeyMissing { plugin: s("p") },
                "trust-key-missing",
                "the trust key is missing while trust records exist, so plugin p cannot be checked; run `slopvac plugins trust` for it to trust it again",
            ),
            (
                HostMessage::TrustKeyMismatch { plugin: s("p") },
                "trust-key-mismatch",
                "the trust key changed after plugin p was trusted, so it cannot be checked; run `slopvac plugins trust` for it to trust it again",
            ),
            (
                HostMessage::TrustKeyUnusable { plugin: s("p") },
                "trust-key-unusable",
                "the trust key cannot be used for plugin p; fix the file, or delete it and run `slopvac plugins trust` for each plugin",
            ),
            (
                HostMessage::HashMismatch { plugin: s("p") },
                "plugin-hash-mismatch",
                "plugin p changed after it was trusted; run `slopvac plugins sync` to restore the verified files, and `slopvac plugins trust` to approve new content",
            ),
            (
                HostMessage::Timeout {
                    plugin: s("p"),
                    what: s("`tag` got no reply"),
                },
                "plugin-timeout",
                "plugin p timed out: `tag` got no reply",
            ),
            (
                HostMessage::Exited {
                    plugin: s("p"),
                    status: s("exit status: 3"),
                    stderr: s("\nstderr:\nboom"),
                },
                "plugin-exited",
                "plugin p exited (exit status: 3)\nstderr:\nboom",
            ),
            (
                HostMessage::ProtocolViolation { detail: s("p: x") },
                "plugin-protocol-violation",
                "plugin protocol violation: p: x",
            ),
            (
                HostMessage::OutputInvalid { detail: s("x") },
                "plugin-output-invalid",
                "plugin output invalid: x",
            ),
            (
                HostMessage::SpawnFailed { detail: s("x") },
                "plugin-spawn-failed",
                "plugin failed to start: x",
            ),
            (
                HostMessage::LauncherNotInstalled,
                "launcher-not-installed",
                "the running program did not install the slopvac plugin launcher, so plugins and git plugin sources cannot start",
            ),
            (
                HostMessage::DeclarationMismatch { detail: s("x") },
                "plugin-declaration-mismatch",
                "plugin declaration mismatch: x",
            ),
            (
                HostMessage::RequestIdExhausted,
                "request-id-exhausted",
                "request ids exhausted",
            ),
            (
                HostMessage::ProtocolVersionUnsupported {
                    host: s("1..=1"),
                    plugin: s("2"),
                },
                "protocol-version-unsupported",
                "no common protocol version: host speaks 1..=1, plugin speaks 2",
            ),
            (
                HostMessage::RequiredFeatureMissing { feature: s("f") },
                "required-feature-missing",
                "plugin requires feature `f`, which the host does not offer",
            ),
            (
                HostMessage::RequestCancelled,
                "request-cancelled",
                "request cancelled",
            ),
            (
                HostMessage::MessageTooLarge { detail: s("x") },
                "message-too-large",
                "message too large: x",
            ),
            (
                HostMessage::PluginUsage { detail: s("x") },
                "plugin-usage",
                "invalid use of plugin: x",
            ),
            (
                HostMessage::RpcParseError { detail: s("d") },
                "parse-error",
                "d",
            ),
            (
                HostMessage::RpcInvalidRequest { detail: s("d") },
                "invalid-request",
                "d",
            ),
            (
                HostMessage::RpcMethodNotFound { detail: s("d") },
                "method-not-found",
                "d",
            ),
            (
                HostMessage::RpcInvalidParams { detail: s("d") },
                "invalid-params",
                "d",
            ),
            (
                HostMessage::RpcNotInitialized { detail: s("d") },
                "not-initialized",
                "d",
            ),
            (
                HostMessage::RpcDocumentInvalid { detail: s("d") },
                "document-invalid",
                "d",
            ),
            (HostMessage::RpcOffline { detail: s("d") }, "offline", "d"),
            (
                HostMessage::RpcInternalError { detail: s("d") },
                "internal-error",
                "d",
            ),
        ];
        let registered = HostMessage::entries();
        assert_eq!(registered.len(), table.len());
        for (value, code, text) in table {
            assert_eq!(value.code(), code);
            assert_eq!(value.to_string(), text);
            assert!(registered.iter().any(|e| e.code == code), "{code}");
        }
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn every_sentence_keeps_its_text_and_is_registered() {
        let table: Vec<(HostText, &str)> = vec![
            (
                HostText::RpcError {
                    code: s("-32602"),
                    message: s("bad"),
                    name: s("invalid-params"),
                },
                "plugin error -32602: bad (invalid-params)",
            ),
            (
                HostText::Named {
                    name: s("p"),
                    detail: s("d"),
                },
                "p: d",
            ),
            (HostText::StderrTail { text: s("boom") }, "stderr:\nboom"),
            (
                HostText::StatusLimit {
                    status: s("signal: 24"),
                    limit: s("the file size limit of 5 bytes was reached"),
                },
                "signal: 24: the file size limit of 5 bytes was reached",
            ),
            (
                HostText::UnsolicitedCap { limit: 8 },
                "more than 8 unsolicited messages",
            ),
            (
                HostText::EncodeMessage { error: s("e") },
                "cannot encode message: e",
            ),
            (
                HostText::BytesExceed { bytes: 9, max: 8 },
                "9 bytes exceed the limit of 8",
            ),
            (
                HostText::MethodNoReply { method: s("m") },
                "`m` got no reply",
            ),
            (
                HostText::MethodIgnoredCancel { method: s("m") },
                "`m` ignored its cancel",
            ),
            (
                HostText::MethodPassedDeadline { method: s("m") },
                "`m` passed its deadline",
            ),
            (
                HostText::NetworkDiffers {
                    reply: s("true"),
                    manifest: s("false"),
                },
                "reply says requiresNetwork=true, manifest says network=false",
            ),
            (
                HostText::FeatureNotRequired { feature: s("f") },
                "feature `f` is not required in the manifest",
            ),
            (
                HostText::FeatureNotOptional { feature: s("f") },
                "feature `f` is not optional in the manifest",
            ),
            (
                HostText::HookNotInManifest {
                    kind: s("tagger"),
                    id: s("h"),
                },
                "hook tagger/h is not in the manifest",
            ),
            (
                HostText::LimitOutOfRange {
                    field: s("maxInFlight"),
                    value: 0,
                },
                "maxInFlight 0 is outside the allowed range",
            ),
            (
                HostText::InitializeResult { error: s("e") },
                "initialize result: e",
            ),
            (
                HostText::HookNotOffered {
                    name: s("p"),
                    kind: s("tagger"),
                    id: s("h"),
                },
                "p: hook tagger/h was not offered",
            ),
            (
                HostText::WallClockCap { cap: s("1s") },
                "the wall-clock cap of 1s expired",
            ),
            (
                HostText::FrameStalled { stall: s("2s") },
                "a frame stalled for 2s outside any request",
            ),
            (
                HostText::CpuLimit { limit: s("3s") },
                "the CPU time limit of 3s was reached",
            ),
            (
                HostText::FileLimit { limit: 4 },
                "the file size limit of 4 bytes was reached",
            ),
            (
                HostText::HeaderTooLong { max: 1024 },
                "header line longer than 1024 bytes",
            ),
            (
                HostText::TooManyHeaders { max: 8 },
                "more than 8 header lines",
            ),
            (
                HostText::BodyTooLong { len: 9, max: 8 },
                "body of 9 bytes exceeds the limit of 8",
            ),
            (HostText::ReadFailed { error: s("e") }, "read failed: e"),
            (HostText::WaitFailed { error: s("e") }, "wait failed: e"),
            (
                HostText::BudgetExceeded {
                    cap: 5,
                    what: s("standard output bytes"),
                },
                "whole-run budget of 5 standard output bytes exceeded",
            ),
            (
                HostText::DocumentTooLarge { id: s("d") },
                "document `d` exceeds the message limit",
            ),
            (
                HostText::EncodeDocument { error: s("e") },
                "cannot encode a document: e",
            ),
            (
                HostText::EntryKeyMissing { key: s("id") },
                "a result entry has no string `id`",
            ),
            (
                HostText::ResultNotRequested { id: s("d") },
                "result for `d`, which was not requested",
            ),
            (
                HostText::ResultDuplicate { id: s("d") },
                "duplicate result for `d`",
            ),
            (HostText::ResultMissing { id: s("d") }, "no result for `d`"),
            (
                HostText::FieldNotArray { field: s("tags") },
                "`tags` is not an array",
            ),
            (
                HostText::ParseFailed {
                    what: s("tag"),
                    error: s("e"),
                },
                "tag: e",
            ),
            (
                HostText::TagKind { kind: s("Bad") },
                "tag kind `Bad` is not kebab-case",
            ),
            (
                HostText::EditsExceed { count: 9, max: 8 },
                "9 edits exceed the limit of 8",
            ),
            (
                HostText::EditMissingFinding { finding: 3 },
                "edit names missing finding 3",
            ),
            (
                HostText::EditOutsideFinding { index: 1 },
                "edit lies outside finding 1",
            ),
            (
                HostText::InsertedExceed {
                    inserted: 9,
                    cap: 8,
                },
                "9 inserted bytes exceed the cap of 8",
            ),
            (
                HostText::PathReservedChar { character: s(":") },
                "character `:` is reserved on Windows",
            ),
            (
                HostText::SegmentNotNormal { segment: s("..") },
                "segment `..` is not a normal name",
            ),
            (
                HostText::ReservedName { segment: s("con") },
                "reserved name `con`",
            ),
            (
                HostText::RecipePath {
                    path: s("a"),
                    reason: s("empty path"),
                },
                "recipe path `a`: empty path",
            ),
            (
                HostText::RecipeNoContent { path: s("a") },
                "recipe file `a` has no content",
            ),
            (
                HostText::RecipePathTwice { path: s("a") },
                "recipe path `a` appears twice",
            ),
            (HostText::ProjectRoot { error: s("e") }, "project root: e"),
            (
                HostText::Symlink {
                    path: s("a"),
                    error: s("e"),
                },
                "symlink `a`: e",
            ),
            (
                HostText::LeavesRoot { path: s("a") },
                "`a` leaves the project root through a symlink",
            ),
            (
                HostText::PathError {
                    path: s("a"),
                    error: s("e"),
                },
                "`a`: e",
            ),
            (
                HostText::LaunchFailure { message: s("m") },
                "slopvac plugin launcher: m",
            ),
            (
                HostText::MalformedArg { key: s("cpu") },
                "malformed `cpu` argument",
            ),
            (
                HostText::SetLimit {
                    name: s("CPU time"),
                    error: s("e"),
                },
                "cannot set the CPU time limit: e",
            ),
            (
                HostText::RunFailed { error: s("e") },
                "cannot run the plugin: e",
            ),
            (
                HostText::Subreaper { error: s("e") },
                "cannot become a child subreaper: e",
            ),
            (
                HostText::RefuseTracing { error: s("e") },
                "cannot refuse tracing: e",
            ),
            (HostText::LostPlugin { error: s("e") }, "lost the plugin: e"),
            (
                HostText::CurrentExe { error: s("e") },
                "cannot find the running executable: e",
            ),
            (
                HostText::LaunchUsage {
                    flag: s("--slopvac-plugin-launcher"),
                },
                "usage: slopvac-plugin-launcher --slopvac-plugin-launcher ... (started by the plugin host only)",
            ),
        ];
        let registered = HostText::entries();
        assert_eq!(registered.len(), table.len());
        for (value, text) in table {
            assert_eq!(value.to_string(), text);
            assert!(
                registered.iter().any(|e| e.code == value.code()),
                "{}",
                value.code()
            );
        }
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn every_phrase_keeps_its_text_and_is_registered() {
        let table: Vec<(HostPhrase, &str)> = vec![
            (HostPhrase::ShutDown, "the plugin has shut down"),
            (HostPhrase::StatusUnknown, "status unknown"),
            (HostPhrase::Closed, "plugin is closed"),
            (HostPhrase::Dropped, "plugin dropped"),
            (HostPhrase::NotObject, "message is not a JSON object"),
            (HostPhrase::BadJsonrpc, "`jsonrpc` is not \"2.0\""),
            (
                HostPhrase::BadId,
                "response id is not an integer from 1 to 2^53-1",
            ),
            (
                HostPhrase::NoMethodOrId,
                "message has neither `method` nor `id`",
            ),
            (
                HostPhrase::ResultOrError,
                "response needs exactly one of `result` and `error`",
            ),
            (HostPhrase::BudgetExceeded, "whole-run budget exceeded"),
            (HostPhrase::StdoutCap, "standard output volume cap reached"),
            (HostPhrase::StderrCap, "standard error volume cap reached"),
            (HostPhrase::WriteBlocked, "the write to the plugin blocked"),
            (HostPhrase::NoSlot, "no request slot became free"),
            (HostPhrase::Unknown, "unknown"),
            (HostPhrase::MissingPipes, "missing pipes"),
            (
                HostPhrase::EndInHeaderLine,
                "stream ended inside a header line",
            ),
            (HostPhrase::NoCrlf, "header line does not end in CRLF"),
            (HostPhrase::StrayCrLf, "stray CR or LF in header line"),
            (
                HostPhrase::LengthNotDecimal,
                "Content-Length is not a plain decimal number",
            ),
            (
                HostPhrase::LengthLeadingZeros,
                "Content-Length has leading zeros",
            ),
            (
                HostPhrase::LengthOverflow64,
                "Content-Length overflows 64 bits",
            ),
            (
                HostPhrase::LengthOverflowSize,
                "Content-Length overflows the platform size",
            ),
            (
                HostPhrase::EndInHeaderBlock,
                "stream ended inside a header block",
            ),
            (HostPhrase::NoColon, "header line has no colon"),
            (HostPhrase::DuplicateLength, "duplicate Content-Length"),
            (HostPhrase::MissingLength, "missing Content-Length"),
            (HostPhrase::EndInBody, "stream ended inside a body"),
            (HostPhrase::BudgetStdoutBytes, "standard output bytes"),
            (HostPhrase::BudgetStderrBytes, "standard error bytes"),
            (HostPhrase::BudgetUnsolicited, "unsolicited messages"),
            (
                HostPhrase::ErrorCodeMissing,
                "error.code is missing or not an integer",
            ),
            (HostPhrase::ErrorMessageMissing, "error.message is missing"),
            (
                HostPhrase::ErrorPluginCode,
                "error.data.slopvac_code is missing or not kebab-case",
            ),
            (
                HostPhrase::ResultsMissing,
                "`results` is missing or not an array",
            ),
            (
                HostPhrase::TagSpan,
                "tag span is outside the text or inside a character",
            ),
            (HostPhrase::TagConfidence, "tag confidence is outside 0..=1"),
            (
                HostPhrase::SegmentContext,
                "segment context is not kebab-case",
            ),
            (
                HostPhrase::SegmentSpan,
                "segment span is outside the text or inside a character",
            ),
            (HostPhrase::ScoreNotNumber, "score is not a number"),
            (HostPhrase::ScoreNegative, "score is negative"),
            (
                HostPhrase::EditSpan,
                "edit span is outside the text or inside a character",
            ),
            (HostPhrase::EditsOverlap, "edits overlap"),
            (
                HostPhrase::ProviderEntry,
                "a provider entry without `error` needs `text` and `model`",
            ),
            (
                HostPhrase::FilesMissing,
                "`files` is missing or not an array",
            ),
            (HostPhrase::PathEmpty, "empty path"),
            (HostPhrase::PathTooLong, "path longer than 1024 bytes"),
            (HostPhrase::PathAbsolute, "absolute path or backslash"),
            (HostPhrase::PathControl, "control character in path"),
            (HostPhrase::PathDrive, "drive letter"),
            (HostPhrase::PathSegments, "more than 32 path segments"),
            (
                HostPhrase::SegmentDotSpace,
                "segment ends in a dot or space",
            ),
            (HostPhrase::MalformedArgs, "malformed arguments"),
            (
                HostPhrase::ProgramNotAbsolute,
                "the plugin program is not an absolute path",
            ),
            (HostPhrase::UnixOnly, "the launcher runs on Unix only"),
            (
                HostPhrase::NotInstalled,
                "the running program did not install the slopvac plugin launcher",
            ),
            (HostPhrase::LimitCore, "core size"),
            (HostPhrase::LimitCpu, "CPU time"),
            (HostPhrase::LimitOpenFile, "open file"),
            (HostPhrase::LimitFileSize, "file size"),
            (HostPhrase::LimitMemory, "memory"),
        ];
        let registered = HostPhrase::entries();
        assert_eq!(registered.len(), table.len());
        for (value, text) in table {
            assert_eq!(value.as_static(), text);
            assert_eq!(value.to_string(), text);
            assert!(
                registered.iter().any(|e| e.code == value.code()),
                "{}",
                value.code()
            );
        }
    }

    #[test]
    fn a_control_character_in_a_plugin_name_is_escaped() {
        // `slopvac_sanitize::line` writes ESC (U+001B) as the visible `\u{1b}`.
        assert_eq!(
            untrusted("a\u{1b}b"),
            "plugin a\\u{1b}b is not trusted; run `slopvac plugins trust` for it"
        );
    }

    #[test]
    fn an_rpc_error_keeps_the_sentence_under_the_reported_code() {
        let error = RpcError {
            code: -32602,
            message: s("bad"),
            plugin_code: s("x-y"),
            data: serde_json::Value::Null,
        };
        assert_eq!(rpc(&error), "plugin error -32602: bad (invalid-params)");
    }
}
