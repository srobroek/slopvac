//! The plugin launcher as a program of its own, which this package's tests
//! start plugins through. The `slopvac` binary runs the same code.

fn main() {
    slopvac_plugins::launch::intercept();
    eprintln!("{}", slopvac_plugins::launch::usage());
    std::process::exit(2);
}
