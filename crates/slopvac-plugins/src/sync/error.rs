use std::path::PathBuf;

use thiserror::Error;

use crate::error::PluginError;
use crate::extract::ExtractError;
use crate::lock::{LockDiff, PackId};
use crate::messages::sync as messages;
use crate::oci::OciError;
use crate::pyenv::PyEnvError;
use crate::revoke::RevocationError;
use crate::sign::SignError;

/// Why a sync, status or check failed. Every variant makes the command exit 2
/// (policies.md, section 3.5): the run could not establish that the installed
/// packs are the locked packs.
#[derive(Debug, Error)]
pub enum SyncError {
    /// Offline mode and the cache lacks content the lock needs.
    #[error("{}", messages::offline_missing(id, digest, what))]
    OfflinePackMissing {
        /// Pack id.
        id: PackId,
        /// The digest the lock pins.
        digest: String,
        /// What is missing.
        what: String,
    },
    /// The lock entry cannot be resolved as written.
    #[error("{}", messages::source_failed(id, why))]
    Source {
        /// Pack id.
        id: PackId,
        /// What is wrong.
        why: String,
    },
    /// Fetching or exporting a pinned git commit failed, or the commit holds
    /// something a pack may not (a link or a submodule).
    #[error("{}", messages::git_source(id, why))]
    Git {
        /// Pack id.
        id: PackId,
        /// What went wrong.
        why: String,
    },
    /// A git source needs the plugin launcher and the running program did not
    /// install it ([`PluginError::LauncherNotInstalled`], code
    /// `launcher-not-installed`). No git process ran and nothing was installed.
    #[error("{}", messages::plugin_cause(id, source))]
    Launcher {
        /// Pack id.
        id: PackId,
        /// The cause.
        #[source]
        source: PluginError,
    },
    /// A git source passed a limit: the download size, the number of files or
    /// the expanded size.
    #[error("{}", messages::git_source_limit(id, why))]
    GitLimit {
        /// Pack id.
        id: PackId,
        /// Which limit.
        why: String,
    },
    /// The registry or the network failed.
    #[error("{}", messages::fetch_cause(id, source))]
    Fetch {
        /// Pack id.
        id: PackId,
        /// The cause.
        #[source]
        source: OciError,
    },
    /// The signature gate refused the artifact.
    #[error("{}", messages::sign_failed(id, source))]
    Sign {
        /// Pack id.
        id: PackId,
        /// The cause.
        #[source]
        source: SignError,
    },
    /// An OCI entry has no `[plugins.signature]` table. Data packs must be signed.
    #[error("{}", messages::unsigned(id))]
    Unsigned {
        /// Pack id.
        id: PackId,
    },
    /// The signed statement is valid but is not the one the lock records.
    #[error("{}", messages::sign_differs(id, why))]
    SignatureDiffersFromLock {
        /// Pack id.
        id: PackId,
        /// What differs.
        why: String,
    },
    /// Fetched or read content does not hash to the locked digest.
    #[error("{}", messages::digest_mismatch(id, expected, actual))]
    DigestMismatch {
        /// Pack id.
        id: PackId,
        /// Locked digest.
        expected: String,
        /// Computed digest.
        actual: String,
    },
    /// The manifest does not have the shape of a pack artifact.
    #[error("{}", messages::layout(id, why))]
    Layout {
        /// Pack id.
        id: PackId,
        /// What is wrong.
        why: String,
    },
    /// An installed tree changed and sync is offline, so it cannot be fetched
    /// again. The tree was removed.
    #[error("{}", messages::cache_tampered(id, path))]
    CacheTampered {
        /// Pack id.
        id: PackId,
        /// The tree.
        path: PathBuf,
    },
    /// Safe extraction refused the archive, or a file operation failed.
    #[error("{}", messages::plugin_cause(id, source))]
    Extract {
        /// Pack id.
        id: PackId,
        /// The cause.
        #[source]
        source: ExtractError,
    },
    /// The managed Python environment of a plugin pack could not be built.
    #[error("{}", messages::pack_env(id, source))]
    PythonEnv {
        /// Pack id.
        id: PackId,
        /// The cause.
        #[source]
        source: PyEnvError,
    },
    /// The data directory could not be prepared or written.
    #[error("{}", messages::data_dir(.0))]
    Store(String),
    /// The revocation list names the pack's artifact or its signing key
    /// (threat model K5).
    #[error("{}", messages::revoked(id, what))]
    Revoked {
        /// Pack id.
        id: PackId,
        /// What is revoked.
        what: String,
    },
    /// The revocation list could not be fetched, verified or read from the cache.
    #[error(transparent)]
    Revocation(#[from] RevocationError),
    /// The resolved packs differ from the lock.
    #[error("{}", messages::lock_mismatch(.0))]
    LockMismatch(LockDiff),
}

impl SyncError {
    /// The exit code. Slopvac uses no other failing code for an incomplete run.
    #[must_use]
    pub fn exit_code(&self) -> u8 {
        2
    }

    /// The stable error code of the contract (policies.md, section 1.3), where
    /// one exists.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::OfflinePackMissing { .. } => "offline-plugin-missing",
            Self::LockMismatch(_) => "lock-mismatch",
            Self::CacheTampered { .. } => "cache-tampered",
            Self::DigestMismatch { .. } => "digest-mismatch",
            // A credential helper refused while fetching a signature blob is a
            // login problem, not a bad signature.
            Self::Sign {
                source: SignError::Fetch(e),
                ..
            } if e.code().is_some() => e.code().unwrap_or("signature-invalid"),
            Self::Unsigned { .. } => "sync-unsigned",
            Self::Sign { .. } | Self::SignatureDiffersFromLock { .. } => "signature-invalid",
            Self::Revoked { .. } => "plugin-revoked",
            Self::Revocation(e) => e.code(),
            Self::Fetch { source, .. } => source.code().unwrap_or("sync-fetch"),
            Self::Launcher { .. } => "launcher-not-installed",
            _ => "sync-failed",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn refusal() -> OciError {
        OciError::HelperUntrusted {
            program: "docker-credential-x".into(),
            dir: "tools".into(),
        }
    }

    fn sign_fetch(e: OciError) -> SyncError {
        SyncError::Sign {
            id: "demo".parse().unwrap(),
            source: SignError::Fetch(e),
        }
    }

    #[test]
    fn a_helper_refusal_while_fetching_a_signature_keeps_its_code() {
        assert_eq!(sign_fetch(refusal()).code(), "credential-helper-untrusted");
    }

    #[test]
    fn another_failure_while_fetching_a_signature_is_still_a_signature_failure() {
        let err = sign_fetch(OciError::NotFound("sig".into()));
        assert_eq!(err.code(), "signature-invalid");
    }

    #[test]
    fn a_helper_refusal_while_fetching_a_pack_keeps_its_code() {
        let err = SyncError::Fetch {
            id: "demo".parse().unwrap(),
            source: refusal(),
        };
        assert_eq!(err.code(), "credential-helper-untrusted");
    }
}
