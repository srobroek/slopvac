//! Prints the genre of each file given, as `slopvac genre` will.
//!
//! Usage: `cargo run -p slopvac-context --example genre -- <files...>`

fn main() {
    let matches = slopvac_context::command()
        .get_matches_from(std::iter::once("genre".to_string()).chain(std::env::args().skip(1)));
    match slopvac_context::run(&matches, &mut |_, _| None) {
        Ok(text) => print!("{text}"),
        Err(e) => {
            eprintln!("error: {e}");
            std::process::exit(2);
        }
    }
}
