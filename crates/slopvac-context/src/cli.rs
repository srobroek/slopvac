//! `slopvac genre <file>...`: print the genre of each file with scores and reasons.
//!
//! The CLI epic wires [`command`] and [`run`] into the clap tree.

use std::fmt::Write as _;
use std::path::PathBuf;

use clap::{Arg, ArgAction, ArgMatches, Command};
use slopvac_sanitize::line;

use crate::{
    DeclaredGenre, DocumentView, Error, GenreAssignment, GenreRegistry, GenreResult, GenreSource,
    PlainDocument, ResolveOptions, builtin_genres,
};

/// The `genre` subcommand.
#[must_use]
pub fn command() -> Command {
    Command::new("genre")
        .about("Print the genre of each file, with scores and the reasons for the choice")
        .arg(
            Arg::new("files")
                .num_args(1..)
                .required(true)
                .value_name("FILE"),
        )
        .arg(
            Arg::new("assign")
                .long("assign")
                .value_name("GLOB=GENRE")
                .action(ArgAction::Append)
                .help("Assign a genre to files that match a glob, as a `[[genres]]` block would"),
        )
}

/// Render one result as text. Paths, genre ids and reason details come from the document or
/// the config, so each is escaped for a terminal.
#[must_use]
pub fn render(path: &str, r: &GenreResult) -> String {
    let source = match r.source {
        GenreSource::Explicit => "explicit",
        GenreSource::Detected => "detected",
        GenreSource::Default => "default",
    };
    let mut out = format!("{}: {} ({source})\n", line(path), line(&r.id));
    for reason in &r.reasons {
        let _ = writeln!(out, "  {}: {}", line(&reason.signal), line(&reason.detail));
    }
    let scores: Vec<String> = r
        .scores
        .iter()
        .map(|(id, s)| format!("{} {s}", line(id)))
        .collect();
    let _ = writeln!(out, "  scores: {}", scores.join(", "));
    out
}

/// The genre a document declares for itself, as the host checked it against the project's
/// front matter policy: called with the path as typed and the document text.
pub type DeclaredGenres<'a> = dyn FnMut(&str, &str) -> Option<String> + 'a;

/// Resolve the genre of each file against the built-in genres and print the results.
/// `declared` supplies the genre that a document's front matter sets, after the host has
/// applied the project's policy; the document's own front matter is not consulted.
pub fn run(matches: &ArgMatches, declared: &mut DeclaredGenres<'_>) -> Result<String, Error> {
    let registry = builtin_genres()?;
    let assignments = parse_assignments(matches)?;
    let mut out = String::new();
    for path in matches.get_many::<String>("files").into_iter().flatten() {
        out.push_str(&explain(&registry, path, &assignments, declared)?);
    }
    Ok(out)
}

fn parse_assignments(matches: &ArgMatches) -> Result<Vec<GenreAssignment>, Error> {
    matches
        .get_many::<String>("assign")
        .into_iter()
        .flatten()
        .map(|raw| {
            let (glob, genre) = raw
                .split_once('=')
                .ok_or_else(|| Error::Parse(format!("`--assign {raw}` needs GLOB=GENRE")))?;
            Ok(GenreAssignment {
                files: vec![glob.to_string()],
                genre: genre.to_string(),
            })
        })
        .collect()
}

/// The path relative to the working directory, else the file name. Assignments match
/// relative paths, and a path outside the working directory has no relative form.
fn relative_to_cwd(path: &str) -> String {
    let path = std::path::Path::new(path);
    let relative = std::env::current_dir()
        .ok()
        .and_then(|cwd| {
            path.strip_prefix(cwd)
                .ok()
                .map(std::path::Path::to_path_buf)
        })
        .or_else(|| path.is_relative().then(|| path.to_path_buf()))
        .or_else(|| path.file_name().map(std::path::PathBuf::from))
        .unwrap_or_default();
    relative.to_string_lossy().into_owned()
}

fn explain(
    registry: &GenreRegistry,
    path: &str,
    assignments: &[GenreAssignment],
    declared: &mut DeclaredGenres<'_>,
) -> Result<String, Error> {
    // STUB(slopvac-8l4.5.11): PlainDocument stands in for the real Markdown parser.
    let src = read_document(path)?;
    let doc = PlainDocument::from_markdown(path, &src);
    let declared = declared(path, &src);
    let result = registry.resolve(
        &doc as &dyn DocumentView,
        &ResolveOptions {
            assignments,
            relative_path: Some(&relative_to_cwd(path)),
            declared: DeclaredGenre::Given(declared.as_deref()),
        },
    )?;
    Ok(render(path, &result))
}

/// Read `path` as UTF-8 under the document cap. The read refuses a FIFO, a device or another
/// file that is not regular without blocking on it. A symlink is resolved first, as the lint
/// path does.
fn read_document(path: &str) -> Result<String, Error> {
    let resolved = std::fs::canonicalize(path).unwrap_or_else(|_| PathBuf::from(path));
    let read_failed = |source: std::io::Error| Error::Read {
        path: path.to_string(),
        source,
    };
    slopvac_fs::read_capped_regular_to_string(
        &resolved,
        slopvac_fs::MAX_DOCUMENT_BYTES,
        slopvac_fs::ReadOptions::new(),
    )
    .map_err(|e| match e {
        slopvac_fs::Error::Input {
            kind: slopvac_fs::InputKind::TooLarge,
            ..
        } => Error::TooLarge {
            path: path.to_string(),
            cap: slopvac_fs::MAX_DOCUMENT_BYTES,
        },
        slopvac_fs::Error::Input {
            kind: slopvac_fs::InputKind::NotFound,
            ..
        } => read_failed(std::io::ErrorKind::NotFound.into()),
        slopvac_fs::Error::Input {
            kind: slopvac_fs::InputKind::NotUtf8,
            ..
        } => read_failed(std::io::ErrorKind::InvalidData.into()),
        slopvac_fs::Error::Input {
            source: Some(source),
            ..
        } => read_failed(source),
        _ => Error::Unreadable {
            path: path.to_string(),
        },
    })
}
