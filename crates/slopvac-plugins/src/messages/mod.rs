//! The messages `slopvac-plugins` reports: error codes and the text of every failure, notice and
//! summary line.
//!
//! The catalogs sit in five files by area: [`host`] (the plugin host, its protocol and its
//! process), [`trust`] (trust store, signatures, revocation and strict mode), [`transport`]
//! (the OCI client, safe extraction and applying fixes), [`sync`] (sync, the lock and update)
//! and [`pyenv`] (the pack index and managed Python environments). Each file derives `Catalog`
//! for three kinds of entry: one per published error code, sentences with parameters, and fixed phrases
//! that callers read as `&'static str`. The binary registers all of them through
//! [`message_entries`].
//!
//! A published code that several failures share has one entry whose template is the wrapped
//! text, so the entry keeps the code and each failure keeps its own sentence.

use std::sync::OnceLock;

use slopvac_messages::Entry;
use slopvac_update::messages::UpdateMessage;

pub(crate) mod host;
pub(crate) mod pyenv;
pub(crate) mod sync;
pub(crate) mod transport;
pub(crate) mod trust;

/// `offline-network-needed`, as `slopvac-update` defines it, for the command that needs the
/// network. The code has one home, in the catalog of `slopvac-update`.
pub(crate) fn offline_network_needed(command: &str) -> String {
    UpdateMessage::OfflineNetworkNeeded {
        command: command.to_owned(),
    }
    .to_string()
}

/// The entries of every plugins catalog, for the one registration of `slopvac-plugins`: the
/// host, trust, transport, pyenv and sync catalogs in that order.
#[must_use]
pub fn message_entries() -> &'static [Entry] {
    static ALL: OnceLock<Vec<Entry>> = OnceLock::new();
    ALL.get_or_init(|| {
        [
            host::entries(),
            trust::entries(),
            transport::entries(),
            pyenv::entries(),
            sync::entries(),
        ]
        .concat()
    })
}
