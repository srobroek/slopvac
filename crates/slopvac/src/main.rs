//! The `slopvac` command-line interface.

use clap::Parser;

/// Lint prose for AI-generated text patterns.
#[derive(Debug, Parser)]
#[command(version, about)]
struct Cli {}

fn main() {
    Cli::parse();
}
