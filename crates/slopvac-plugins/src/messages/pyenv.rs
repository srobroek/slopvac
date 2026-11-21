//! The messages of managed Python environments and the pack index: sentences with parameters
//! and fixed phrases.
//!
//! [`PyenvText`] holds sentences with named parameters. [`PyenvPhrase`] holds fixed phrases,
//! which callers read as `&'static str` through `as_static`. No published error code lives
//! here: the errors of this area are free-form text. The path helpers at the end build the
//! `what` of an I/O failure.

use std::path::Path;

use slopvac_messages::{Catalog, Entry};

/// Sentences of the Python environment builder, the lock reader, the manifest reader and the
/// pack index.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum PyenvText {
    /// The lock is malformed.
    #[code("plugins-pyenv-lock-refused")]
    #[text("the Python lock is refused: {detail}")]
    LockRefused { detail: String },
    /// A package is not a wheel inside the artifact.
    #[code("plugins-pyenv-source-only")]
    #[text(
        "package `{package}` is not a vendored wheel ({source_kind}); slopvac builds environments from locked wheels only and runs no build backend"
    )]
    SourceOnly {
        package: String,
        source_kind: String,
    },
    /// The `[plugin]` table of the pack manifest cannot select an environment.
    #[code("plugins-pyenv-manifest-unusable")]
    #[text("the manifest {path} cannot select a Python environment: {reason}")]
    ManifestUnusable {
        #[display_path]
        path: String,
        reason: String,
    },
    /// No environment is built for the plugin tree.
    #[code("plugins-pyenv-env-missing")]
    #[text(
        "no Python environment is built for plugin `{plugin}` ({python}); run `slopvac plugins sync`"
    )]
    EnvMissing { plugin: String, python: String },
    /// A locked wheel is missing, misnamed or does not match its hash.
    #[code("plugins-pyenv-wheel-refused")]
    #[text("wheel of `{package}` refused: {why}")]
    WheelRefused { package: String, why: String },
    /// The installer setup is unusable.
    #[code("plugins-pyenv-installer-refused")]
    #[text("the Python installer is refused: {detail}")]
    InstallerRefused { detail: String },
    /// Offline, and no managed interpreter matches the request.
    #[code("plugins-pyenv-offline-python-missing")]
    #[text(
        "offline: no uv-managed Python matches `{request}`; run once online, or install it with `uv python install`"
    )]
    OfflinePythonMissing { request: String },
    /// The head of a failed uv or interpreter run.
    #[code("plugins-pyenv-step-head")]
    #[text("{step} failed ({status}):")]
    StepHead { step: String, status: String },
    /// A failed run: its head, then the end of its error output.
    #[code("plugins-pyenv-step-output")]
    #[text("{head} {output}")]
    StepOutput { head: String, output: String },
    /// The environment changed after its build.
    #[code("plugins-pyenv-env-changed")]
    #[text(
        "the Python environment changed: `{path}` {why}; rebuild it and run `slopvac plugins trust`"
    )]
    EnvChanged {
        #[display_path]
        path: String,
        why: String,
    },
    /// The environment holds something it may not, or passes a bound.
    #[code("plugins-pyenv-env-refused")]
    #[text("the Python environment is refused: {detail}")]
    EnvRefused { detail: String },
    /// The environment record is damaged.
    #[code("plugins-pyenv-record-damaged")]
    #[text("the environment record {path} is damaged: {why}")]
    RecordDamaged {
        #[display_path]
        path: String,
        why: String,
    },
    /// A file system operation failed.
    #[code("plugins-pyenv-io-failed")]
    #[text("{what}: {cause}")]
    IoFailed { what: String, cause: String },
    /// An installer path is not absolute.
    #[code("plugins-pyenv-not-absolute")]
    #[text("`{path}` is not an absolute path")]
    NotAbsolute {
        #[display_path]
        path: String,
    },
    /// The installer interpreter request is not a plain version request.
    #[code("plugins-pyenv-not-a-request")]
    #[text("`{request}` is not a Python version request")]
    NotARequest { request: String },
    /// Something changed while the build ran.
    #[code("plugins-pyenv-during-build")]
    #[text("{why} during the build, before trust")]
    DuringBuild { why: String },
    /// A key to remove is not a store key.
    #[code("plugins-pyenv-not-store-key")]
    #[text("`{key}` is not a store key")]
    NotStoreKey { key: String },
    /// Reading a file or directory.
    #[code("plugins-pyenv-reading")]
    #[text("reading {path}")]
    Reading {
        #[display_path]
        path: String,
    },
    /// Inspecting a path.
    #[code("plugins-pyenv-inspecting")]
    #[text("inspecting {path}")]
    Inspecting {
        #[display_path]
        path: String,
    },
    /// Reading a symbolic link.
    #[code("plugins-pyenv-reading-link")]
    #[text("reading link {path}")]
    ReadingLink {
        #[display_path]
        path: String,
    },
    /// Making a path read-only.
    #[code("plugins-pyenv-protecting")]
    #[text("protecting {path}")]
    Protecting {
        #[display_path]
        path: String,
    },
    /// Removing a file.
    #[code("plugins-pyenv-removing")]
    #[text("removing {path}")]
    Removing {
        #[display_path]
        path: String,
    },
    /// Creating a directory.
    #[code("plugins-pyenv-creating")]
    #[text("creating {path}")]
    Creating {
        #[display_path]
        path: String,
    },
    /// Restricting a directory to its owner.
    #[code("plugins-pyenv-securing")]
    #[text("securing {path}")]
    Securing {
        #[display_path]
        path: String,
    },
    /// The environment root is a link or not a directory.
    #[code("plugins-pyenv-not-directory")]
    #[text("{path} is a link or not a directory")]
    NotDirectory {
        #[display_path]
        path: String,
    },
    /// The environment passes the entry bound.
    #[code("plugins-pyenv-too-many-entries")]
    #[text("the environment has more than {nodes} entries")]
    TooManyEntries {
        #[count]
        nodes: usize,
    },
    /// The environment passes the depth bound.
    #[code("plugins-pyenv-too-deep")]
    #[text("the environment is deeper than {depth} levels")]
    TooDeep {
        #[count]
        depth: usize,
    },
    /// The environment passes the size bound.
    #[code("plugins-pyenv-too-many-bytes")]
    #[text("the environment holds more than {bytes} bytes")]
    TooManyBytes {
        #[count]
        bytes: u64,
    },
    /// The environment holds a special file.
    #[code("plugins-pyenv-special-file")]
    #[text("`{rel}` is a special file")]
    SpecialFile {
        #[display_path]
        rel: String,
    },
    /// A link target is not UTF-8.
    #[code("plugins-pyenv-link-target-not-utf8")]
    #[text("`{rel}` has a link target that is not UTF-8")]
    LinkTargetNotUtf8 {
        #[display_path]
        rel: String,
    },
    /// The lock version is not 1.x.
    #[code("plugins-pyenv-lock-version-unsupported")]
    #[text("lock-version {version} is not supported; 1.x is")]
    LockVersionUnsupported { version: String },
    /// A package name is not a distribution name.
    #[code("plugins-pyenv-bad-package-name")]
    #[text("package name `{name}` is not a distribution name")]
    BadPackageName { name: String },
    /// A package version is not exact.
    #[code("plugins-pyenv-version-not-exact")]
    #[text("version `{version}` is not exact")]
    VersionNotExact { version: String },
    /// An environment marker is refused.
    #[code("plugins-pyenv-marker-refused")]
    #[text("marker `{marker}` is refused: {why}")]
    MarkerRefused { marker: String, why: String },
    /// A wheel path or file has a problem.
    #[code("plugins-pyenv-path-problem")]
    #[text("`{path}`: {reason}")]
    PathProblem {
        #[display_path]
        path: String,
        reason: String,
    },
    /// A locked wheel is not a regular file.
    #[code("plugins-pyenv-wheel-not-regular")]
    #[text("`{path}` is not a regular file")]
    WheelNotRegular {
        #[display_path]
        path: String,
    },
    /// A locked wheel does not match its hash.
    #[code("plugins-pyenv-wheel-hash-mismatch")]
    #[text("`{path}` has sha256 {actual}; the lock pins {pinned}")]
    WheelHashMismatch {
        #[display_path]
        path: String,
        actual: String,
        pinned: String,
    },
    /// A wheel holds an entry that may not be installed.
    #[code("plugins-pyenv-wheel-holds")]
    #[text("`{path}` holds `{name}`, {why}")]
    WheelHolds {
        #[display_path]
        path: String,
        #[display_path]
        name: String,
        why: String,
    },
    /// The wheels would expand past the environment bounds.
    #[code("plugins-pyenv-wheels-too-big")]
    #[text(
        "the wheels declare {entries} entries and {bytes} bytes; an environment holds at most {max_entries} entries and 1 GiB"
    )]
    WheelsTooBig {
        #[count]
        entries: u64,
        #[count]
        bytes: u64,
        #[count]
        max_entries: usize,
    },
    /// A wheel path does not end in `.whl`.
    #[code("plugins-pyenv-not-a-wheel")]
    #[text("`{path}` is not a wheel")]
    NotAWheel {
        #[display_path]
        path: String,
    },
    /// A wheel is not named for its package and version.
    #[code("plugins-pyenv-not-wheel-of-package")]
    #[text("`{path}` is not a wheel of {package} {version}")]
    NotWheelOfPackage {
        #[display_path]
        path: String,
        package: String,
        version: String,
    },
    /// A wheel has no sha256.
    #[code("plugins-pyenv-no-sha256")]
    #[text("`{path}` has no sha256")]
    NoSha256 {
        #[display_path]
        path: String,
    },
    /// A wheel sha256 is malformed.
    #[code("plugins-pyenv-bad-sha256")]
    #[text("`{path}` has a malformed sha256")]
    BadSha256 {
        #[display_path]
        path: String,
    },
    /// `runtime = "python"` without a required field.
    #[code("plugins-pyenv-missing-field")]
    #[text("`runtime = \"python\"` needs `{field}`")]
    MissingField { field: String },
    /// The manifest is not valid TOML.
    #[code("plugins-pyenv-toml-at")]
    #[text("it is not valid TOML (line {line}, column {column})")]
    TomlAt {
        #[count]
        line: usize,
        #[count]
        column: usize,
    },
    /// Where a manifest failed to parse.
    #[code("plugins-pyenv-toml-syntax")]
    #[text("TOML syntax error at line {line}, column {column}")]
    TomlSyntax {
        #[count]
        line: usize,
        #[count]
        column: usize,
    },
    /// The built index would pass the size limit.
    #[code("plugins-index-too-big-to-build")]
    #[text("the index would be {size} bytes; the limit is {limit}")]
    IndexTooBigToBuild {
        #[count]
        size: usize,
        #[count]
        limit: usize,
    },
    /// The index document passes the size limit.
    #[code("plugins-index-too-big")]
    #[text("the index is {size} bytes; the limit is {limit}")]
    IndexTooBig {
        #[count]
        size: usize,
        #[count]
        limit: usize,
    },
    /// The index document is not valid JSON.
    #[code("plugins-index-not-json")]
    #[text("not valid JSON: {reason}")]
    NotJson { reason: String },
    /// A key appears twice.
    #[code("plugins-index-repeated-key")]
    #[text("repeated key `{key}`")]
    RepeatedKey { key: String },
    /// A key is not known.
    #[code("plugins-index-unknown-key")]
    #[text("unknown key `{key}`")]
    UnknownKey { key: String },
    /// A required key is missing.
    #[code("plugins-index-missing-key")]
    #[text("missing key `{key}`")]
    MissingKey { key: String },
    /// A value has the wrong type.
    #[code("plugins-index-key-must-be")]
    #[text("`{key}` must be {what}")]
    KeyMustBe { key: String, what: String },
    /// An entry version does not parse.
    #[code("plugins-index-version-invalid")]
    #[text("`{version}`: {reason}")]
    VersionInvalid { version: String, reason: String },
    /// An entry kind is neither `data` nor `code`.
    #[code("plugins-index-kind-invalid")]
    #[text("`{kind}` is not a plugin kind (`data` or `code`)")]
    KindInvalid { kind: String },
    /// The index lists more entries than the limit.
    #[code("plugins-index-too-many-index-entries")]
    #[text("more than {max} entries")]
    TooManyIndexEntries {
        #[count]
        max: usize,
    },
    /// A value is too short or too long.
    #[code("plugins-index-length-between")]
    #[text("{what} must have {min} to {max} characters, not {n}")]
    LengthBetween {
        what: String,
        #[count]
        min: usize,
        #[count]
        max: usize,
        #[count]
        n: usize,
    },
    /// An id or namespace is not valid.
    #[code("plugins-index-id-invalid")]
    #[text(
        "`{value}` is not a valid {key} (lowercase letters, digits and `-`, starting with a letter)"
    )]
    IdInvalid { value: String, key: String },
    /// An id or namespace is reserved.
    #[code("plugins-index-id-reserved")]
    #[text("`{value}` is reserved for the built-in plugin and is never listed")]
    IdReserved { value: String },
    /// A version number is too large.
    #[code("plugins-index-version-number-too-large")]
    #[text("major, minor and patch must be at most {max}")]
    VersionNumberTooLarge {
        #[count]
        max: u64,
    },
    /// The `slopvac_api` is out of range.
    #[code("plugins-index-api-out-of-range")]
    #[text("slopvac_api must be 1 to {max}")]
    ApiOutOfRange {
        #[count]
        max: u64,
    },
    /// A namespace and id pair appears twice.
    #[code("plugins-index-listed-twice")]
    #[text("plugin `{namespace}/{id}` is listed twice")]
    ListedTwice { namespace: String, id: String },
    /// A rejected index document or entry.
    #[code("plugins-index-error-line")]
    #[text("{pointer}: {message}")]
    IndexErrorLine { pointer: String, message: String },
    /// The first line of a search hit.
    #[code("plugins-index-search-head")]
    #[text("{namespace}/{id} {version} ({kind}, needs slopvac API {api})")]
    SearchHead {
        namespace: String,
        id: String,
        version: String,
        kind: String,
        #[count]
        api: u64,
    },
    /// An indented line of a search hit.
    #[code("plugins-index-search-indented")]
    #[text("{text}")]
    SearchIndented { text: String },
    /// The source line of a search hit.
    #[code("plugins-index-search-source")]
    #[text("source: {origin}")]
    SearchSource { origin: String },
    /// The publisher key line of a search hit.
    #[code("plugins-index-search-key")]
    #[text("publisher key: {key_id} (fingerprint {fingerprint})")]
    SearchKey { key_id: String, fingerprint: String },
    /// The warning for a hit that claims a first-party namespace.
    #[code("plugins-index-search-reserved")]
    #[text("warning: claims first-party namespace `{namespace}`; not verified")]
    SearchReserved { namespace: String },
}

/// Fixed phrases of the same area. Each reads as a `&'static str`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum PyenvPhrase {
    /// Managed environments are not supported on this platform yet.
    #[code("plugins-pyenv-unsupported-platform")]
    #[text(
        "managed Python environments are not supported on Windows yet; slopvac refuses to build or run them"
    )]
    UnsupportedPlatform,
    /// Resolving the interpreter of an environment.
    #[code("plugins-pyenv-resolving-env-interpreter")]
    #[text("resolving the environment's interpreter")]
    ResolvingEnvInterpreter,
    /// Opening the environment lock file.
    #[code("plugins-pyenv-opening-env-lock")]
    #[text("opening the environment lock")]
    OpeningEnvLock,
    /// Locking the environment.
    #[code("plugins-pyenv-locking-env")]
    #[text("locking the environment")]
    LockingEnv,
    /// Creating a staging directory.
    #[code("plugins-pyenv-creating-staging")]
    #[text("creating a staging directory")]
    CreatingStaging,
    /// Moving the environment into place.
    #[code("plugins-pyenv-moving-env")]
    #[text("moving the environment into place")]
    MovingEnv,
    /// Reading the environment store.
    #[code("plugins-pyenv-reading-store")]
    #[text("reading the environment store")]
    ReadingStore,
    /// The step that looks for a managed interpreter.
    #[code("plugins-pyenv-step-find")]
    #[text("uv python find")]
    StepFind,
    /// The step that creates the environment.
    #[code("plugins-pyenv-step-venv")]
    #[text("uv venv")]
    StepVenv,
    /// Writing the requirements file.
    #[code("plugins-pyenv-writing-requirements")]
    #[text("writing the requirements file")]
    WritingRequirements,
    /// The step that installs the wheels.
    #[code("plugins-pyenv-step-pip-install")]
    #[text("uv pip install")]
    StepPipInstall,
    /// The step that compiles bytecode.
    #[code("plugins-pyenv-step-compile")]
    #[text("bytecode compilation")]
    StepCompile,
    /// Resolving the interpreter of a new environment.
    #[code("plugins-pyenv-resolving-new-interpreter")]
    #[text("resolving the new environment's interpreter")]
    ResolvingNewInterpreter,
    /// Creating an output file for a run.
    #[code("plugins-pyenv-creating-output-file")]
    #[text("creating an output file")]
    CreatingOutputFile,
    /// The step that probes the interpreter.
    #[code("plugins-pyenv-step-probe")]
    #[text("interpreter probe")]
    StepProbe,
    /// Reading the probe output.
    #[code("plugins-pyenv-reading-probe")]
    #[text("reading the interpreter probe")]
    ReadingProbe,
    /// Resolving the interpreter.
    #[code("plugins-pyenv-resolving-interpreter")]
    #[text("resolving the interpreter")]
    ResolvingInterpreter,
    /// Resolving the base interpreter.
    #[code("plugins-pyenv-resolving-base")]
    #[text("resolving the base interpreter")]
    ResolvingBase,
    /// Inspecting the interpreter.
    #[code("plugins-pyenv-inspecting-interpreter")]
    #[text("inspecting the interpreter")]
    InspectingInterpreter,
    /// Creating a record file.
    #[code("plugins-pyenv-creating-record-file")]
    #[text("creating a record file")]
    CreatingRecordFile,
    /// Writing the environment record.
    #[code("plugins-pyenv-writing-record")]
    #[text("writing the environment record")]
    WritingRecord,
    /// Replacing the environment record.
    #[code("plugins-pyenv-replacing-record")]
    #[text("replacing the environment record")]
    ReplacingRecord,
    /// A run did not start.
    #[code("plugins-pyenv-did-not-start")]
    #[text("did not start")]
    DidNotStart,
    /// A run timed out.
    #[code("plugins-pyenv-timed-out")]
    #[text("timed out")]
    TimedOut,
    /// A run printed output that cannot be read.
    #[code("plugins-pyenv-unreadable-output")]
    #[text("unreadable output")]
    UnreadableOutput,
    /// The interpreter path is not UTF-8.
    #[code("plugins-pyenv-interpreter-path-not-utf8")]
    #[text("the interpreter path is not UTF-8")]
    InterpreterPathNotUtf8,
    /// The interpreter is not the recorded one.
    #[code("plugins-pyenv-not-recorded-interpreter")]
    #[text("is not the interpreter the build recorded")]
    NotRecordedInterpreter,
    /// An entry is missing.
    #[code("plugins-pyenv-is-missing")]
    #[text("is missing")]
    IsMissing,
    /// An entry has no modification time.
    #[code("plugins-pyenv-no-modification-time")]
    #[text("has no modification time")]
    NoModificationTime,
    /// An entry changed size or modification time.
    #[code("plugins-pyenv-changed-size-or-time")]
    #[text("changed size or modification time")]
    ChangedSizeOrTime,
    /// An entry changed content.
    #[code("plugins-pyenv-changed-content")]
    #[text("changed content")]
    ChangedContent,
    /// An entry was replaced.
    #[code("plugins-pyenv-was-replaced")]
    #[text("was replaced")]
    WasReplaced,
    /// An entry was rewritten.
    #[code("plugins-pyenv-was-rewritten")]
    #[text("was rewritten")]
    WasRewritten,
    /// The record names another tree or interpreter.
    #[code("plugins-pyenv-names-another-tree")]
    #[text("it names another tree or interpreter")]
    NamesAnotherTree,
    /// The record is too large.
    #[code("plugins-pyenv-record-too-large")]
    #[text("larger than 64 MiB")]
    RecordTooLarge,
    /// The record schema is not supported.
    #[code("plugins-pyenv-record-schema")]
    #[text("unsupported schema_version")]
    RecordSchema,
    /// A file name is not UTF-8.
    #[code("plugins-pyenv-file-name-not-utf8")]
    #[text("a file name is not UTF-8")]
    FileNameNotUtf8,
    /// A file changed while it was read.
    #[code("plugins-pyenv-changed-while-read")]
    #[text("changed while it was read")]
    ChangedWhileRead,
    /// An entry was added after the build.
    #[code("plugins-pyenv-added-after-build")]
    #[text("added after the build")]
    AddedAfterBuild,
    /// An entry changed in type, size, time, mode or target.
    #[code("plugins-pyenv-entry-changed")]
    #[text("its type, size, modification time, mode or target changed")]
    EntryChanged,
    /// The content of an entry changed.
    #[code("plugins-pyenv-content-changed")]
    #[text("its content changed")]
    ContentChanged,
    /// An entry was removed after the build.
    #[code("plugins-pyenv-removed-after-build")]
    #[text("removed after the build")]
    RemovedAfterBuild,
    /// Inspecting an entry.
    #[code("plugins-pyenv-inspecting-entry")]
    #[text("inspecting an entry")]
    InspectingEntry,
    /// The lock is too large.
    #[code("plugins-pyenv-lock-too-large")]
    #[text("larger than 4 MiB")]
    LockTooLarge,
    /// The lock is not UTF-8.
    #[code("plugins-pyenv-lock-not-utf8")]
    #[text("not UTF-8")]
    LockNotUtf8,
    /// The lock has no version.
    #[code("plugins-pyenv-lock-version-missing")]
    #[text("`lock-version` is missing")]
    LockVersionMissing,
    /// `packages` is not an array.
    #[code("plugins-pyenv-packages-not-array")]
    #[text("`packages` is not an array")]
    PackagesNotArray,
    /// The lock lists too many packages.
    #[code("plugins-pyenv-too-many-packages")]
    #[text("more than 2000 packages")]
    TooManyPackages,
    /// A package is not a table.
    #[code("plugins-pyenv-package-not-table")]
    #[text("a package is not a table")]
    PackageNotTable,
    /// A package has no name.
    #[code("plugins-pyenv-package-no-name")]
    #[text("a package has no name")]
    PackageNoName,
    /// A package has no exact version.
    #[code("plugins-pyenv-no-exact-version")]
    #[text("no exact version")]
    NoExactVersion,
    /// A marker is not a string.
    #[code("plugins-pyenv-marker-not-string")]
    #[text("marker is not a string")]
    MarkerNotString,
    /// A package lists no wheels.
    #[code("plugins-pyenv-no-wheels")]
    #[text("no wheels")]
    NoWheels,
    /// A wheel is not a table.
    #[code("plugins-pyenv-wheel-not-table")]
    #[text("a wheel is not a table")]
    WheelNotTable,
    /// A wheel has no path inside the artifact.
    #[code("plugins-pyenv-wheel-no-path")]
    #[text("a wheel has no `path` inside the artifact; a `url` would need a download")]
    WheelNoPath,
    /// A marker is empty or too long.
    #[code("plugins-pyenv-marker-empty-or-long")]
    #[text("empty or longer than 1000 bytes")]
    MarkerEmptyOrLong,
    /// A marker holds a control or non-ASCII character.
    #[code("plugins-pyenv-marker-control")]
    #[text("a control or non-ASCII character")]
    MarkerControl,
    /// A marker holds a comment or escape character.
    #[code("plugins-pyenv-marker-comment")]
    #[text("a comment or escape character")]
    MarkerComment,
    /// A marker holds a word that starts with a dash.
    #[code("plugins-pyenv-marker-option")]
    #[text("a word that starts with `-`")]
    MarkerOption,
    /// A marker holds a character outside the grammar.
    #[code("plugins-pyenv-marker-grammar")]
    #[text("a character outside the marker grammar")]
    MarkerGrammar,
    /// A marker has an unclosed quote.
    #[code("plugins-pyenv-marker-quote")]
    #[text("an unclosed quote")]
    MarkerQuote,
    /// A wheel entry leaves the install scheme.
    #[code("plugins-pyenv-entry-outside-scheme")]
    #[text("a path outside the install scheme")]
    EntryOutsideScheme,
    /// A wheel entry would replace the interpreter.
    #[code("plugins-pyenv-entry-replaces-interpreter")]
    #[text("which would replace the interpreter or its activation")]
    EntryReplacesInterpreter,
    /// A wheel entry would write into the interpreter directories.
    #[code("plugins-pyenv-entry-writes-interpreter-dirs")]
    #[text("which would write into the interpreter's own directories")]
    EntryWritesInterpreterDirs,
    /// A wheel entry is a startup hook.
    #[code("plugins-pyenv-entry-startup-hook")]
    #[text("a startup hook that would run before trust")]
    EntryStartupHook,
    /// A wheel entry uses an unknown install scheme.
    #[code("plugins-pyenv-entry-unknown-scheme")]
    #[text("an unknown install scheme")]
    EntryUnknownScheme,
    /// A wheel is not a ZIP archive.
    #[code("plugins-pyenv-not-zip")]
    #[text("not a ZIP archive")]
    NotZip,
    /// A wheel is a ZIP64 archive.
    #[code("plugins-pyenv-zip64")]
    #[text("a ZIP64 archive")]
    Zip64,
    /// The central directory lies outside the file.
    #[code("plugins-pyenv-zip-directory-outside")]
    #[text("a central directory outside the file")]
    ZipDirectoryOutside,
    /// The central directory is damaged.
    #[code("plugins-pyenv-zip-directory-damaged")]
    #[text("a damaged central directory")]
    ZipDirectoryDamaged,
    /// An archive entry is ZIP64.
    #[code("plugins-pyenv-zip64-entry")]
    #[text("a ZIP64 entry")]
    Zip64Entry,
    /// An archive entry name is not UTF-8.
    #[code("plugins-pyenv-zip-name-not-utf8")]
    #[text("an entry name that is not UTF-8")]
    ZipNameNotUtf8,
    /// The manifest is not a regular file.
    #[code("plugins-pyenv-manifest-not-regular")]
    #[text("it is not a regular file")]
    ManifestNotRegular,
    /// The manifest is larger than 1 MiB.
    #[code("plugins-pyenv-manifest-too-large")]
    #[text("it is larger than 1 MiB")]
    ManifestTooLarge,
    /// `python` is set without `runtime = "python"`.
    #[code("plugins-pyenv-python-without-runtime")]
    #[text("`python` needs `runtime = \"python\"`")]
    PythonWithoutRuntime,
    /// `runtime` is set in a pack that is not a code pack.
    #[code("plugins-pyenv-runtime-needs-code-kind")]
    #[text("`runtime` belongs to a `kind = \"code\"` pack")]
    RuntimeNeedsCodeKind,
    /// `python` is not a version request.
    #[code("plugins-pyenv-python-not-a-request")]
    #[text("`python` is not a Python version request")]
    PythonNotARequest,
    /// `command` is not a relative script path.
    #[code("plugins-pyenv-command-not-a-script")]
    #[text("`command` is not a relative script path inside the pack")]
    CommandNotAScript,
    /// `runtime` is neither `native` nor `python`.
    #[code("plugins-pyenv-unknown-runtime")]
    #[text("`runtime` is not a runtime; use `native` or `python`")]
    UnknownRuntime,
    /// The request has a pre-release suffix.
    #[code("plugins-pyenv-pre-release")]
    #[text(
        "the `python` request has a pre-release suffix, which a Python version request cannot express"
    )]
    PreRelease,
    /// The request has a part that is not a version.
    #[code("plugins-pyenv-bad-version")]
    #[text("the `python` request has a part that is not a version of one to three numbers")]
    BadVersion,
    /// The request has a number that is too large.
    #[code("plugins-pyenv-number-too-large")]
    #[text("the `python` request has a number that is too large")]
    NumberTooLarge,
    /// The translated request is too long.
    #[code("plugins-pyenv-request-too-long")]
    #[text("the `python` request translates to more than 64 bytes")]
    RequestTooLong,
    /// A number is negative.
    #[code("plugins-index-negative-number")]
    #[text("negative number")]
    NegativeNumber,
    /// A number is not whole.
    #[code("plugins-index-not-whole-number")]
    #[text("not a whole number")]
    NotWholeNumber,
    /// What the reader expects: a whole number.
    #[code("plugins-index-expect-whole")]
    #[text("a non-negative whole number")]
    ExpectWhole,
    /// What the reader expects: the index document.
    #[code("plugins-index-expect-index-document")]
    #[text("an index document (a JSON object)")]
    ExpectIndexDocument,
    /// What the reader expects: an array of entries.
    #[code("plugins-index-expect-entries")]
    #[text("an array of entries")]
    ExpectEntries,
    /// What the reader expects: an entry.
    #[code("plugins-index-expect-entry")]
    #[text("an entry (a JSON object)")]
    ExpectEntry,
    /// What the reader expects: a publisher key.
    #[code("plugins-index-expect-publisher-key")]
    #[text("a publisher key (a JSON object)")]
    ExpectPublisherKey,
    /// `schema_version` is not 3.
    #[code("plugins-index-schema-version-must-be-3")]
    #[text("schema_version must be 3")]
    SchemaVersionMustBe3,
    /// `schema_version` is missing.
    #[code("plugins-index-schema-version-required")]
    #[text("schema_version is required")]
    SchemaVersionRequired,
    /// `plugins` is not an array.
    #[code("plugins-index-plugins-must-be-array")]
    #[text("plugins must be an array")]
    PluginsMustBeArray,
    /// `plugins` is missing.
    #[code("plugins-index-plugins-required")]
    #[text("plugins is required")]
    PluginsRequired,
    /// An entry is not an object.
    #[code("plugins-index-entry-must-be-object")]
    #[text("an entry must be an object")]
    EntryMustBeObject,
    /// `publisher_key` is not an object.
    #[code("plugins-index-publisher-key-must-be-object")]
    #[text("publisher_key must be an object")]
    PublisherKeyMustBeObject,
    /// A string.
    #[code("plugins-index-a-string")]
    #[text("a string")]
    AString,
    /// A positive whole number.
    #[code("plugins-index-a-positive-whole")]
    #[text("a positive whole number")]
    APositiveWhole,
    /// A version carries build metadata.
    #[code("plugins-index-build-metadata")]
    #[text("a version must not carry build metadata")]
    BuildMetadata,
    /// A source is not an accepted form.
    #[code("plugins-index-source-invalid")]
    #[text("not an oci://, https:// or pinned git+https:// source without user-info")]
    SourceInvalid,
    /// A key id is malformed.
    #[code("plugins-index-key-id-invalid")]
    #[text("a key id is 16 uppercase hex digits")]
    KeyIdInvalid,
    /// A fingerprint is malformed.
    #[code("plugins-index-fingerprint-invalid")]
    #[text("a fingerprint is 64 lowercase hex digits")]
    FingerprintInvalid,
    /// The note that index claims are unverified.
    #[code("plugins-index-search-unverified")]
    #[text(
        "unverified: the namespace, source and key come from the index; pin a key with `slopvac plugins trust --key <fingerprint>`"
    )]
    SearchUnverified,
}

/// Names a path in the `what` of an I/O failure, as the platform prints it.
fn shown(path: &Path) -> String {
    path.display().to_string()
}

/// `Reading` for `path`.
pub(crate) fn reading(path: &Path) -> String {
    PyenvText::Reading { path: shown(path) }.to_string()
}

/// `Inspecting` for `path`.
pub(crate) fn inspecting(path: &Path) -> String {
    PyenvText::Inspecting { path: shown(path) }.to_string()
}

/// `ReadingLink` for `path`.
pub(crate) fn reading_link(path: &Path) -> String {
    PyenvText::ReadingLink { path: shown(path) }.to_string()
}

/// `Protecting` for `path`.
pub(crate) fn protecting(path: &Path) -> String {
    PyenvText::Protecting { path: shown(path) }.to_string()
}

/// `Removing` for `path`.
pub(crate) fn removing(path: &Path) -> String {
    PyenvText::Removing { path: shown(path) }.to_string()
}

/// `Creating` for `path`.
pub(crate) fn creating(path: &Path) -> String {
    PyenvText::Creating { path: shown(path) }.to_string()
}

/// `Securing` for `path`.
pub(crate) fn securing(path: &Path) -> String {
    PyenvText::Securing { path: shown(path) }.to_string()
}

/// `TomlSyntax` for a manifest failure at `line` and `column`.
pub(crate) fn toml_syntax(line: usize, column: usize) -> String {
    PyenvText::TomlSyntax { line, column }.to_string()
}

/// `IndexErrorLine` for a JSON Pointer and an already escaped message. An empty pointer is the
/// whole document and prints as `/`.
pub(crate) fn index_error(pointer: &str, message: &str) -> String {
    PyenvText::IndexErrorLine {
        pointer: if pointer.is_empty() { "/" } else { pointer }.to_owned(),
        message: message.to_owned(),
    }
    .to_string()
}

/// The catalogs of this area, concatenated.
pub(super) fn entries() -> Vec<Entry> {
    [PyenvText::entries(), PyenvPhrase::entries()].concat()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(text: &str) -> String {
        text.to_owned()
    }

    /// Every sentence with sample parameters, beside the text the code printed before the registry.
    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn every_text_keeps_its_published_wording_and_is_registered() {
        let texts: Vec<(PyenvText, &str)> = vec![
            (
                PyenvText::LockRefused {
                    detail: s("detail-0"),
                },
                "the Python lock is refused: detail-0",
            ),
            (
                PyenvText::SourceOnly {
                    package: s("package-1"),
                    source_kind: s("source_kind-1"),
                },
                "package `package-1` is not a vendored wheel (source_kind-1); slopvac builds environments from locked wheels only and runs no build backend",
            ),
            (
                PyenvText::ManifestUnusable {
                    path: s("path-2"),
                    reason: s("reason-2"),
                },
                "the manifest path-2 cannot select a Python environment: reason-2",
            ),
            (
                PyenvText::EnvMissing {
                    plugin: s("plugin-3"),
                    python: s("python-3"),
                },
                "no Python environment is built for plugin `plugin-3` (python-3); run `slopvac plugins sync`",
            ),
            (
                PyenvText::WheelRefused {
                    package: s("package-4"),
                    why: s("why-4"),
                },
                "wheel of `package-4` refused: why-4",
            ),
            (
                PyenvText::InstallerRefused {
                    detail: s("detail-5"),
                },
                "the Python installer is refused: detail-5",
            ),
            (
                PyenvText::OfflinePythonMissing {
                    request: s("request-6"),
                },
                "offline: no uv-managed Python matches `request-6`; run once online, or install it with `uv python install`",
            ),
            (
                PyenvText::StepHead {
                    step: s("step-7"),
                    status: s("status-7"),
                },
                "step-7 failed (status-7):",
            ),
            (
                PyenvText::StepOutput {
                    head: s("head-8"),
                    output: s("output-8"),
                },
                "head-8 output-8",
            ),
            (
                PyenvText::EnvChanged {
                    path: s("path-9"),
                    why: s("why-9"),
                },
                "the Python environment changed: `path-9` why-9; rebuild it and run `slopvac plugins trust`",
            ),
            (
                PyenvText::EnvRefused {
                    detail: s("detail-10"),
                },
                "the Python environment is refused: detail-10",
            ),
            (
                PyenvText::RecordDamaged {
                    path: s("path-11"),
                    why: s("why-11"),
                },
                "the environment record path-11 is damaged: why-11",
            ),
            (
                PyenvText::IoFailed {
                    what: s("what-12"),
                    cause: s("cause-12"),
                },
                "what-12: cause-12",
            ),
            (
                PyenvText::NotAbsolute { path: s("path-13") },
                "`path-13` is not an absolute path",
            ),
            (
                PyenvText::NotARequest {
                    request: s("request-14"),
                },
                "`request-14` is not a Python version request",
            ),
            (
                PyenvText::DuringBuild { why: s("why-15") },
                "why-15 during the build, before trust",
            ),
            (
                PyenvText::NotStoreKey { key: s("key-16") },
                "`key-16` is not a store key",
            ),
            (PyenvText::Reading { path: s("path-17") }, "reading path-17"),
            (
                PyenvText::Inspecting { path: s("path-18") },
                "inspecting path-18",
            ),
            (
                PyenvText::ReadingLink { path: s("path-19") },
                "reading link path-19",
            ),
            (
                PyenvText::Protecting { path: s("path-20") },
                "protecting path-20",
            ),
            (
                PyenvText::Removing { path: s("path-21") },
                "removing path-21",
            ),
            (
                PyenvText::Creating { path: s("path-22") },
                "creating path-22",
            ),
            (
                PyenvText::Securing { path: s("path-23") },
                "securing path-23",
            ),
            (
                PyenvText::NotDirectory { path: s("path-24") },
                "path-24 is a link or not a directory",
            ),
            (
                PyenvText::TooManyEntries { nodes: 32 },
                "the environment has more than 32 entries",
            ),
            (
                PyenvText::TooDeep { depth: 33 },
                "the environment is deeper than 33 levels",
            ),
            (
                PyenvText::TooManyBytes { bytes: 34 },
                "the environment holds more than 34 bytes",
            ),
            (
                PyenvText::SpecialFile { rel: s("rel-28") },
                "`rel-28` is a special file",
            ),
            (
                PyenvText::LinkTargetNotUtf8 { rel: s("rel-29") },
                "`rel-29` has a link target that is not UTF-8",
            ),
            (
                PyenvText::LockVersionUnsupported {
                    version: s("version-30"),
                },
                "lock-version version-30 is not supported; 1.x is",
            ),
            (
                PyenvText::BadPackageName { name: s("name-31") },
                "package name `name-31` is not a distribution name",
            ),
            (
                PyenvText::VersionNotExact {
                    version: s("version-32"),
                },
                "version `version-32` is not exact",
            ),
            (
                PyenvText::MarkerRefused {
                    marker: s("marker-33"),
                    why: s("why-33"),
                },
                "marker `marker-33` is refused: why-33",
            ),
            (
                PyenvText::PathProblem {
                    path: s("path-34"),
                    reason: s("reason-34"),
                },
                "`path-34`: reason-34",
            ),
            (
                PyenvText::WheelNotRegular { path: s("path-35") },
                "`path-35` is not a regular file",
            ),
            (
                PyenvText::WheelHashMismatch {
                    path: s("path-36"),
                    actual: s("actual-36"),
                    pinned: s("pinned-36"),
                },
                "`path-36` has sha256 actual-36; the lock pins pinned-36",
            ),
            (
                PyenvText::WheelHolds {
                    path: s("path-37"),
                    name: s("name-37"),
                    why: s("why-37"),
                },
                "`path-37` holds `name-37`, why-37",
            ),
            (
                PyenvText::WheelsTooBig {
                    entries: 45,
                    bytes: 45,
                    max_entries: 45,
                },
                "the wheels declare 45 entries and 45 bytes; an environment holds at most 45 entries and 1 GiB",
            ),
            (
                PyenvText::NotAWheel { path: s("path-39") },
                "`path-39` is not a wheel",
            ),
            (
                PyenvText::NotWheelOfPackage {
                    path: s("path-40"),
                    package: s("package-40"),
                    version: s("version-40"),
                },
                "`path-40` is not a wheel of package-40 version-40",
            ),
            (
                PyenvText::NoSha256 { path: s("path-41") },
                "`path-41` has no sha256",
            ),
            (
                PyenvText::BadSha256 { path: s("path-42") },
                "`path-42` has a malformed sha256",
            ),
            (
                PyenvText::MissingField {
                    field: s("field-43"),
                },
                "`runtime = \"python\"` needs `field-43`",
            ),
            (
                PyenvText::TomlAt {
                    line: 51,
                    column: 51,
                },
                "it is not valid TOML (line 51, column 51)",
            ),
            (
                PyenvText::TomlSyntax {
                    line: 52,
                    column: 52,
                },
                "TOML syntax error at line 52, column 52",
            ),
            (
                PyenvText::IndexTooBigToBuild {
                    size: 53,
                    limit: 53,
                },
                "the index would be 53 bytes; the limit is 53",
            ),
            (
                PyenvText::IndexTooBig {
                    size: 54,
                    limit: 54,
                },
                "the index is 54 bytes; the limit is 54",
            ),
            (
                PyenvText::NotJson {
                    reason: s("reason-48"),
                },
                "not valid JSON: reason-48",
            ),
            (
                PyenvText::RepeatedKey { key: s("key-49") },
                "repeated key `key-49`",
            ),
            (
                PyenvText::UnknownKey { key: s("key-50") },
                "unknown key `key-50`",
            ),
            (
                PyenvText::MissingKey { key: s("key-51") },
                "missing key `key-51`",
            ),
            (
                PyenvText::KeyMustBe {
                    key: s("key-52"),
                    what: s("what-52"),
                },
                "`key-52` must be what-52",
            ),
            (
                PyenvText::VersionInvalid {
                    version: s("version-53"),
                    reason: s("reason-53"),
                },
                "`version-53`: reason-53",
            ),
            (
                PyenvText::KindInvalid { kind: s("kind-54") },
                "`kind-54` is not a plugin kind (`data` or `code`)",
            ),
            (
                PyenvText::TooManyIndexEntries { max: 62 },
                "more than 62 entries",
            ),
            (
                PyenvText::LengthBetween {
                    what: s("what-56"),
                    min: 63,
                    max: 63,
                    n: 63,
                },
                "what-56 must have 63 to 63 characters, not 63",
            ),
            (
                PyenvText::IdInvalid {
                    value: s("value-57"),
                    key: s("key-57"),
                },
                "`value-57` is not a valid key-57 (lowercase letters, digits and `-`, starting with a letter)",
            ),
            (
                PyenvText::IdReserved {
                    value: s("value-58"),
                },
                "`value-58` is reserved for the built-in plugin and is never listed",
            ),
            (
                PyenvText::VersionNumberTooLarge { max: 66 },
                "major, minor and patch must be at most 66",
            ),
            (
                PyenvText::ApiOutOfRange { max: 67 },
                "slopvac_api must be 1 to 67",
            ),
            (
                PyenvText::ListedTwice {
                    namespace: s("namespace-61"),
                    id: s("id-61"),
                },
                "plugin `namespace-61/id-61` is listed twice",
            ),
            (
                PyenvText::IndexErrorLine {
                    pointer: s("pointer-62"),
                    message: s("message-62"),
                },
                "pointer-62: message-62",
            ),
            (
                PyenvText::SearchHead {
                    namespace: s("namespace-63"),
                    id: s("id-63"),
                    version: s("version-63"),
                    kind: s("kind-63"),
                    api: 70,
                },
                "namespace-63/id-63 version-63 (kind-63, needs slopvac API 70)",
            ),
            (PyenvText::SearchIndented { text: s("text-64") }, "text-64"),
            (
                PyenvText::SearchSource {
                    origin: s("source-65"),
                },
                "source: source-65",
            ),
            (
                PyenvText::SearchKey {
                    key_id: s("key_id-66"),
                    fingerprint: s("fingerprint-66"),
                },
                "publisher key: key_id-66 (fingerprint fingerprint-66)",
            ),
            (
                PyenvText::SearchReserved {
                    namespace: s("namespace-67"),
                },
                "warning: claims first-party namespace `namespace-67`; not verified",
            ),
        ];
        let registered = PyenvText::entries();
        for (message, text) in &texts {
            assert_eq!(message.to_string(), *text);
            assert!(registered.iter().any(|e| e.code == message.code()));
        }
        assert_eq!(registered.len(), texts.len());
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn every_phrase_keeps_its_published_wording_and_is_registered() {
        let phrases: [(PyenvPhrase, &str); 103] = [
            (
                PyenvPhrase::UnsupportedPlatform,
                "managed Python environments are not supported on Windows yet; slopvac refuses to build or run them",
            ),
            (
                PyenvPhrase::ResolvingEnvInterpreter,
                "resolving the environment's interpreter",
            ),
            (PyenvPhrase::OpeningEnvLock, "opening the environment lock"),
            (PyenvPhrase::LockingEnv, "locking the environment"),
            (PyenvPhrase::CreatingStaging, "creating a staging directory"),
            (PyenvPhrase::MovingEnv, "moving the environment into place"),
            (PyenvPhrase::ReadingStore, "reading the environment store"),
            (PyenvPhrase::StepFind, "uv python find"),
            (PyenvPhrase::StepVenv, "uv venv"),
            (
                PyenvPhrase::WritingRequirements,
                "writing the requirements file",
            ),
            (PyenvPhrase::StepPipInstall, "uv pip install"),
            (PyenvPhrase::StepCompile, "bytecode compilation"),
            (
                PyenvPhrase::ResolvingNewInterpreter,
                "resolving the new environment's interpreter",
            ),
            (PyenvPhrase::CreatingOutputFile, "creating an output file"),
            (PyenvPhrase::StepProbe, "interpreter probe"),
            (PyenvPhrase::ReadingProbe, "reading the interpreter probe"),
            (
                PyenvPhrase::ResolvingInterpreter,
                "resolving the interpreter",
            ),
            (PyenvPhrase::ResolvingBase, "resolving the base interpreter"),
            (
                PyenvPhrase::InspectingInterpreter,
                "inspecting the interpreter",
            ),
            (PyenvPhrase::CreatingRecordFile, "creating a record file"),
            (PyenvPhrase::WritingRecord, "writing the environment record"),
            (
                PyenvPhrase::ReplacingRecord,
                "replacing the environment record",
            ),
            (PyenvPhrase::DidNotStart, "did not start"),
            (PyenvPhrase::TimedOut, "timed out"),
            (PyenvPhrase::UnreadableOutput, "unreadable output"),
            (
                PyenvPhrase::InterpreterPathNotUtf8,
                "the interpreter path is not UTF-8",
            ),
            (
                PyenvPhrase::NotRecordedInterpreter,
                "is not the interpreter the build recorded",
            ),
            (PyenvPhrase::IsMissing, "is missing"),
            (PyenvPhrase::NoModificationTime, "has no modification time"),
            (
                PyenvPhrase::ChangedSizeOrTime,
                "changed size or modification time",
            ),
            (PyenvPhrase::ChangedContent, "changed content"),
            (PyenvPhrase::WasReplaced, "was replaced"),
            (PyenvPhrase::WasRewritten, "was rewritten"),
            (
                PyenvPhrase::NamesAnotherTree,
                "it names another tree or interpreter",
            ),
            (PyenvPhrase::RecordTooLarge, "larger than 64 MiB"),
            (PyenvPhrase::RecordSchema, "unsupported schema_version"),
            (PyenvPhrase::FileNameNotUtf8, "a file name is not UTF-8"),
            (PyenvPhrase::ChangedWhileRead, "changed while it was read"),
            (PyenvPhrase::AddedAfterBuild, "added after the build"),
            (
                PyenvPhrase::EntryChanged,
                "its type, size, modification time, mode or target changed",
            ),
            (PyenvPhrase::ContentChanged, "its content changed"),
            (PyenvPhrase::RemovedAfterBuild, "removed after the build"),
            (PyenvPhrase::InspectingEntry, "inspecting an entry"),
            (PyenvPhrase::LockTooLarge, "larger than 4 MiB"),
            (PyenvPhrase::LockNotUtf8, "not UTF-8"),
            (PyenvPhrase::LockVersionMissing, "`lock-version` is missing"),
            (PyenvPhrase::PackagesNotArray, "`packages` is not an array"),
            (PyenvPhrase::TooManyPackages, "more than 2000 packages"),
            (PyenvPhrase::PackageNotTable, "a package is not a table"),
            (PyenvPhrase::PackageNoName, "a package has no name"),
            (PyenvPhrase::NoExactVersion, "no exact version"),
            (PyenvPhrase::MarkerNotString, "marker is not a string"),
            (PyenvPhrase::NoWheels, "no wheels"),
            (PyenvPhrase::WheelNotTable, "a wheel is not a table"),
            (
                PyenvPhrase::WheelNoPath,
                "a wheel has no `path` inside the artifact; a `url` would need a download",
            ),
            (
                PyenvPhrase::MarkerEmptyOrLong,
                "empty or longer than 1000 bytes",
            ),
            (
                PyenvPhrase::MarkerControl,
                "a control or non-ASCII character",
            ),
            (PyenvPhrase::MarkerComment, "a comment or escape character"),
            (PyenvPhrase::MarkerOption, "a word that starts with `-`"),
            (
                PyenvPhrase::MarkerGrammar,
                "a character outside the marker grammar",
            ),
            (PyenvPhrase::MarkerQuote, "an unclosed quote"),
            (
                PyenvPhrase::EntryOutsideScheme,
                "a path outside the install scheme",
            ),
            (
                PyenvPhrase::EntryReplacesInterpreter,
                "which would replace the interpreter or its activation",
            ),
            (
                PyenvPhrase::EntryWritesInterpreterDirs,
                "which would write into the interpreter's own directories",
            ),
            (
                PyenvPhrase::EntryStartupHook,
                "a startup hook that would run before trust",
            ),
            (PyenvPhrase::EntryUnknownScheme, "an unknown install scheme"),
            (PyenvPhrase::NotZip, "not a ZIP archive"),
            (PyenvPhrase::Zip64, "a ZIP64 archive"),
            (
                PyenvPhrase::ZipDirectoryOutside,
                "a central directory outside the file",
            ),
            (
                PyenvPhrase::ZipDirectoryDamaged,
                "a damaged central directory",
            ),
            (PyenvPhrase::Zip64Entry, "a ZIP64 entry"),
            (
                PyenvPhrase::ZipNameNotUtf8,
                "an entry name that is not UTF-8",
            ),
            (PyenvPhrase::ManifestNotRegular, "it is not a regular file"),
            (PyenvPhrase::ManifestTooLarge, "it is larger than 1 MiB"),
            (
                PyenvPhrase::PythonWithoutRuntime,
                "`python` needs `runtime = \"python\"`",
            ),
            (
                PyenvPhrase::RuntimeNeedsCodeKind,
                "`runtime` belongs to a `kind = \"code\"` pack",
            ),
            (
                PyenvPhrase::PythonNotARequest,
                "`python` is not a Python version request",
            ),
            (
                PyenvPhrase::CommandNotAScript,
                "`command` is not a relative script path inside the pack",
            ),
            (
                PyenvPhrase::UnknownRuntime,
                "`runtime` is not a runtime; use `native` or `python`",
            ),
            (
                PyenvPhrase::PreRelease,
                "the `python` request has a pre-release suffix, which a Python version request cannot express",
            ),
            (
                PyenvPhrase::BadVersion,
                "the `python` request has a part that is not a version of one to three numbers",
            ),
            (
                PyenvPhrase::NumberTooLarge,
                "the `python` request has a number that is too large",
            ),
            (
                PyenvPhrase::RequestTooLong,
                "the `python` request translates to more than 64 bytes",
            ),
            (PyenvPhrase::NegativeNumber, "negative number"),
            (PyenvPhrase::NotWholeNumber, "not a whole number"),
            (PyenvPhrase::ExpectWhole, "a non-negative whole number"),
            (
                PyenvPhrase::ExpectIndexDocument,
                "an index document (a JSON object)",
            ),
            (PyenvPhrase::ExpectEntries, "an array of entries"),
            (PyenvPhrase::ExpectEntry, "an entry (a JSON object)"),
            (
                PyenvPhrase::ExpectPublisherKey,
                "a publisher key (a JSON object)",
            ),
            (
                PyenvPhrase::SchemaVersionMustBe3,
                "schema_version must be 3",
            ),
            (
                PyenvPhrase::SchemaVersionRequired,
                "schema_version is required",
            ),
            (PyenvPhrase::PluginsMustBeArray, "plugins must be an array"),
            (PyenvPhrase::PluginsRequired, "plugins is required"),
            (PyenvPhrase::EntryMustBeObject, "an entry must be an object"),
            (
                PyenvPhrase::PublisherKeyMustBeObject,
                "publisher_key must be an object",
            ),
            (PyenvPhrase::AString, "a string"),
            (PyenvPhrase::APositiveWhole, "a positive whole number"),
            (
                PyenvPhrase::BuildMetadata,
                "a version must not carry build metadata",
            ),
            (
                PyenvPhrase::SourceInvalid,
                "not an oci://, https:// or pinned git+https:// source without user-info",
            ),
            (
                PyenvPhrase::KeyIdInvalid,
                "a key id is 16 uppercase hex digits",
            ),
            (
                PyenvPhrase::FingerprintInvalid,
                "a fingerprint is 64 lowercase hex digits",
            ),
            (
                PyenvPhrase::SearchUnverified,
                "unverified: the namespace, source and key come from the index; pin a key with `slopvac plugins trust --key <fingerprint>`",
            ),
        ];
        let registered = PyenvPhrase::entries();
        for (phrase, expected) in phrases {
            assert_eq!(phrase.as_static(), expected);
            assert!(registered.iter().any(|e| e.code == phrase.code()));
        }
        assert_eq!(registered.len(), phrases.len());
    }

    #[test]
    fn entries_hold_both_catalogs() {
        assert_eq!(
            entries().len(),
            PyenvText::entries().len() + PyenvPhrase::entries().len()
        );
    }

    #[test]
    fn helpers_print_the_wording_of_the_errors_they_replace() {
        assert_eq!(toml_syntax(3, 9), "TOML syntax error at line 3, column 9");
        assert_eq!(index_error("", "boom"), "/: boom");
        assert_eq!(index_error("/plugins/0", "boom"), "/plugins/0: boom");
    }

    #[test]
    fn path_helpers_print_the_path_after_the_verb() {
        let p = Path::new("/a/b");
        assert_eq!(reading(p), "reading /a/b");
        assert_eq!(inspecting(p), "inspecting /a/b");
        assert_eq!(reading_link(p), "reading link /a/b");
        assert_eq!(protecting(p), "protecting /a/b");
        assert_eq!(removing(p), "removing /a/b");
        assert_eq!(creating(p), "creating /a/b");
        assert_eq!(securing(p), "securing /a/b");
    }
}
