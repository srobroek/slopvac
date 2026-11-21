//! Plugin host errors and their stable `slopvac_code` strings.

use thiserror::Error;

use crate::messages::host as messages;
use crate::process::Teardown;

/// A JSON-RPC error object sent by a plugin.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RpcError {
    /// Numeric JSON-RPC code.
    pub code: i64,
    /// Human-readable message. Not an interface.
    pub message: String,
    /// The kebab-case `data.slopvac_code` the plugin sent. Untrusted detail: it
    /// is never the reported code. Use [`RpcError::code_name`].
    pub plugin_code: String,
    /// The `data` object, or null.
    pub data: serde_json::Value,
}

impl RpcError {
    /// The code the host reports, chosen by the numeric code alone
    /// (plugin-protocol.md section 10). The plugin's own `slopvac_code` never
    /// decides it. A code the contract does not define, including the plugin's
    /// own range -32050 to -32099, is `internal-error`.
    #[must_use]
    pub fn code_name(&self) -> &'static str {
        match self.code {
            -32700 => "parse-error",
            -32600 => "invalid-request",
            -32601 => "method-not-found",
            -32602 => "invalid-params",
            -32001 => "protocol-version-unsupported",
            -32002 => "required-feature-missing",
            -32003 => "not-initialized",
            -32004 => "message-too-large",
            -32005 => "request-cancelled",
            -32006 => "document-invalid",
            -32007 => "offline",
            _ => "internal-error",
        }
    }
}

/// Everything that can go wrong when a host talks to a plugin.
///
/// Each variant maps to a `slopvac_code` from plugin-protocol.md section 10.
/// Any plugin failure makes the affected run exit 2.
#[derive(Debug, Clone, Error, PartialEq, Eq)]
pub enum PluginError {
    /// The content hash has no recorded trust.
    #[error("{}", messages::untrusted(.0))]
    Untrusted(String),
    /// Trust records exist but the key they were made under is gone. The run exits 2.
    #[error("{}", messages::trust_key_missing(.0))]
    TrustKeyMissing(String),
    /// The trust records were made under another key than the store's. The run exits 2.
    #[error("{}", messages::trust_key_mismatch(.0))]
    TrustKeyMismatch(String),
    /// The trust key file is not private to the user or does not hold a key. The run exits 2.
    #[error("{}", messages::trust_key_unusable(.0))]
    TrustKeyUnusable(String),
    /// The installed bytes differ from the hash that trust recorded.
    #[error("{}", messages::hash_mismatch(.0))]
    HashMismatch(String),
    /// A timer in section 6.3 expired.
    #[error("{}", messages::timeout(.plugin, .what))]
    Timeout {
        /// Plugin name.
        plugin: String,
        /// Which timer expired.
        what: String,
    },
    /// The process ended with requests pending.
    #[error("{}", messages::exited(.plugin, .status, .stderr))]
    Exited {
        /// Plugin name.
        plugin: String,
        /// Exit status description.
        status: String,
        /// Raw stderr tail, with a leading newline, or empty. `Display` escapes it.
        stderr: String,
    },
    /// A framing error, a limit breach or a duplicate key.
    #[error("{}", messages::protocol_violation(.0))]
    ProtocolViolation(String),
    /// A result does not match its schema or breaks a rule such as span bounds.
    #[error("{}", messages::output_invalid(.0))]
    OutputInvalid(String),
    /// The program did not start.
    #[error("{}", messages::spawn_failed(.0))]
    SpawnFailed(String),
    /// The running program never called
    /// [`launch::intercept`](crate::launch::intercept), so the host cannot
    /// start the launcher. Nothing was spawned.
    #[error("{}", messages::launcher_not_installed())]
    LauncherNotInstalled,
    /// The reply disagrees with the hashed manifest.
    #[error("{}", messages::declaration_mismatch(.0))]
    DeclarationMismatch(String),
    /// The request counter reached 2^53-1.
    #[error("{}", messages::request_id_exhausted())]
    RequestIdExhausted,
    /// No common protocol version.
    #[error("{}", messages::protocol_version_unsupported(.host, .plugin))]
    ProtocolVersionUnsupported {
        /// Host range, for example `1..=1`.
        host: String,
        /// Plugin range as reported, or the picked version.
        plugin: String,
    },
    /// The host lacks a feature the plugin requires.
    #[error("{}", messages::required_feature_missing(.0))]
    RequiredFeatureMissing(String),
    /// The plugin needs the network and offline mode is on.
    #[error("{}", messages::offline(.0))]
    Offline(String),
    /// The plugin answered a request with an error object.
    #[error("{}", messages::rpc(.0))]
    Rpc(RpcError),
    /// The host cancelled the request and discarded the answer.
    #[error("{}", messages::request_cancelled())]
    Cancelled,
    /// The hook or document does not fit a message and cannot be split.
    #[error("{}", messages::message_too_large(.0))]
    MessageTooLarge(String),
    /// The caller used the plugin wrongly, for example an undeclared hook.
    #[error("{}", messages::plugin_usage(.0))]
    Usage(String),
}

impl PluginError {
    /// The stable code for diagnostics and reports.
    #[must_use]
    pub fn slopvac_code(&self) -> &str {
        match self {
            Self::Untrusted(_) => "plugin-untrusted",
            Self::TrustKeyMissing(_) => "trust-key-missing",
            Self::TrustKeyMismatch(_) => "trust-key-mismatch",
            Self::TrustKeyUnusable(_) => "trust-key-unusable",
            Self::HashMismatch(_) => "plugin-hash-mismatch",
            Self::Timeout { .. } => "plugin-timeout",
            Self::Exited { .. } => "plugin-exited",
            Self::ProtocolViolation(_) => "plugin-protocol-violation",
            Self::OutputInvalid(_) => "plugin-output-invalid",
            Self::SpawnFailed(_) => "plugin-spawn-failed",
            Self::LauncherNotInstalled => "launcher-not-installed",
            Self::DeclarationMismatch(_) => "plugin-declaration-mismatch",
            Self::RequestIdExhausted => "request-id-exhausted",
            Self::ProtocolVersionUnsupported { .. } => "protocol-version-unsupported",
            Self::RequiredFeatureMissing(_) => "required-feature-missing",
            Self::Offline(_) => "offline-network-needed",
            Self::Rpc(e) => e.code_name(),
            Self::Cancelled => "request-cancelled",
            Self::MessageTooLarge(_) => "message-too-large",
            Self::Usage(_) => "plugin-usage",
        }
    }
}

/// Why [`Plugin::start`](crate::Plugin::start) failed, and what the teardown
/// of the process it started left undone.
#[derive(Debug, Clone, Error, PartialEq, Eq)]
#[error("{error}")]
pub struct StartError {
    /// What went wrong.
    pub error: PluginError,
    /// What the teardowns left undone. Complete when no process started.
    pub teardown: Teardown,
}
