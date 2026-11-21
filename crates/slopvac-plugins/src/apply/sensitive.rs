//! The sensitive-path deny list (O7) and agent-harness marks (O8).
//!
//! Matching is case-insensitive on every platform, so the list fails closed on
//! case-insensitive file systems. Paths are root-relative with `/` separators.

use unicode_normalization::UnicodeNormalization;

use crate::messages::transport::TransportPhrase;

/// The path components under the canonical caseless match of Unicode 3.13
/// (D145), `NFD(toCasefold(NFD(x)))`, the same fold `extract.rs` uses for
/// collisions. It maps `ſ` (U+017F) to `s`, which `str::to_lowercase` does not.
fn canonical_parts(path: &str) -> Vec<String> {
    path.split('/').map(fold_name).collect()
}

/// One name under the canonical caseless match.
fn fold_name(name: &str) -> String {
    let decomposed: String = name.nfd().collect();
    caseless::default_case_fold_str(&decomposed).nfd().collect()
}

/// The path components under the NTFS name comparison, which uppercases per
/// character and so merges `i` with the dotless `ı` (U+0131), where the
/// canonical fold keeps them apart. The result is ASCII-lowercased to meet the
/// deny list constants.
fn ntfs_parts(path: &str) -> Vec<String> {
    path.split('/')
        .map(|c| {
            c.nfc()
                .map(|ch| {
                    let mut up = ch.to_uppercase();
                    match (up.next(), up.next()) {
                        (Some(u), None) => u.to_ascii_lowercase(),
                        _ => ch,
                    }
                })
                .collect()
        })
        .collect()
}

/// Why `path` is on the deny list, or `None`.
///
/// The list is the one in threat O7: `.git/` and `.slopvac/` at any depth
/// (hooks included), `.github/workflows/` at the root only, anything named
/// `.env*`, `.gitmodules`, `.gitattributes`, `slopvac.toml` and `.slopvac.toml`
/// at any depth, `.mise.toml`, `.envrc` and `.vscode/tasks.json`. `mise.toml` is
/// also listed, because mise reads it like `.mise.toml`.
///
/// Names match by case-fold equivalence, so `.ſlopvac` and `.SlopVac` are
/// `.slopvac`. A name is denied when either the canonical fold or the NTFS
/// comparison puts it on the list. The match is the same on every platform, so
/// the list fails closed on case-insensitive file systems.
#[must_use]
pub fn deny_reason(path: &str) -> Option<&'static str> {
    classify(&canonical_parts(path)).or_else(|| classify(&ntfs_parts(path)))
}

/// The deny list over components already folded to lowercase.
fn classify(p: &[String]) -> Option<&'static str> {
    let name = p.last().map_or("", String::as_str);
    if p.iter().any(|c| c == ".git") {
        Some(TransportPhrase::ApplyGitDirectory.as_static())
    } else if p.iter().any(|c| c == ".slopvac") {
        Some(TransportPhrase::ApplyState.as_static())
    } else if p.len() > 2 && p[0] == ".github" && p[1] == "workflows" {
        Some(TransportPhrase::ApplyCiWorkflow.as_static())
    } else if p.iter().any(|c| c.starts_with(".env")) {
        Some(TransportPhrase::ApplyEnvironment.as_static())
    } else if matches!(name, ".gitmodules" | ".gitattributes") {
        Some(TransportPhrase::ApplyGitConfig.as_static())
    } else if matches!(
        name,
        "slopvac.toml" | ".slopvac.toml" | ".mise.toml" | "mise.toml"
    ) {
        Some(TransportPhrase::ApplyToolConfig.as_static())
    } else if p.len() >= 2 && p[p.len() - 2] == ".vscode" && name == "tasks.json" {
        Some(TransportPhrase::ApplyEditorTask.as_static())
    } else {
        None
    }
}

/// A mark on a plan entry that writes something an agent harness will read.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HarnessWarning {
    /// An instruction file such as `AGENTS.md` or `CLAUDE.md`.
    InstructionFile,
    /// A file under an agent directory such as `.claude/` or `.opencode/`.
    AgentDirectory,
    /// The content declares a hook.
    Hook,
    /// The content declares an MCP server entry.
    McpServer,
}

const INSTRUCTION_FILES: [&str; 5] = [
    "agents.md",
    "claude.md",
    "gemini.md",
    ".cursorrules",
    ".github/copilot-instructions.md",
];

const AGENT_DIRS: [&str; 6] = [
    ".claude/",
    ".opencode/",
    ".cursor/",
    ".codex/",
    ".gemini/",
    ".windsurf/",
];

/// Marks for writing `content` to `path`.
///
/// The path decides whether the file is a harness file. Only then does the
/// content get scanned for hook and MCP entries. The scan is a text match on
/// the usual key names. It is a warning for a person to read and not a boundary.
#[must_use]
pub fn harness_warnings(path: &str, content: Option<&str>) -> Vec<HarnessWarning> {
    let lower = path.to_lowercase();
    let file = lower.rsplit('/').next().unwrap_or("");
    let mut out = Vec::new();
    let instruction = INSTRUCTION_FILES
        .iter()
        .any(|f| lower == *f || (!f.contains('/') && file == *f));
    let in_dir = AGENT_DIRS.iter().any(|d| lower.starts_with(d));
    let mcp_file = file == ".mcp.json" || (in_dir && file.starts_with("mcp"));
    if instruction {
        out.push(HarnessWarning::InstructionFile);
    }
    if in_dir || mcp_file {
        out.push(HarnessWarning::AgentDirectory);
    }
    if !(instruction || in_dir || mcp_file) {
        return out;
    }
    let body = content.unwrap_or("").to_lowercase();
    let hook_path = lower.contains("/hooks/") || lower.contains("/plugin");
    if hook_path || body.contains("\"hooks\"") || body.contains("[hooks") || body.contains("hooks:")
    {
        out.push(HarnessWarning::Hook);
    }
    if mcp_file
        || body.contains("mcpservers")
        || body.contains("mcp_servers")
        || body.contains("\"mcp\"")
        || body.contains("[mcp")
    {
        out.push(HarnessWarning::McpServer);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn deny_list_matches_each_threat_o7_entry_in_any_case() {
        for p in [
            ".git/config",
            ".GIT/hooks/pre-commit",
            "sub/.git/HEAD",
            ".slopvac/plugins.lock",
            "a/.\u{17f}lopvac/x",
            ".g\u{131}t/config",
            ".slopvac.toml",
            "a/.SLOPVAC.TOML",
            ".github/workflows/ci.yml",
            ".GitHub/Workflows/ci.yml",
            ".env",
            ".env.local",
            "app/.envrc",
            ".gitmodules",
            "x/.gitattributes",
            "slopvac.toml",
            "pkg/Slopvac.toml",
            ".mise.toml",
            "mise.toml",
            ".vscode/tasks.json",
        ] {
            assert!(deny_reason(p).is_some(), "{p} should be denied");
        }
    }

    #[test]
    fn deny_list_leaves_ordinary_files_alone() {
        for p in [
            "README.md",
            "docs/git.md",
            ".github/CODEOWNERS",
            ".github/workflows",
            ".vscode/settings.json",
            "src/environment.rs",
            "my.git/x",
        ] {
            assert_eq!(deny_reason(p), None, "{p} should be allowed");
        }
    }
}
