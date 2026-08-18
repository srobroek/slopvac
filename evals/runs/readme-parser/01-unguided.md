# xisf-header

A blazingly fast Rust crate for parsing XISF headers.

## Overview

XISF (Extensible Image Serialization Format) is a modern, powerful image format used extensively in the astrophotography community. While there are several crates that handle XISF files, `xisf-header` takes a fundamentally different approach: it reads *only* the XML header, without ever touching the image data.

Why does this matter? Because in many workflows you don't actually need the pixels. You need the metadata — exposure time, filter, temperature, coordinates. Traditional parsers force you to decode megabytes of image data just to answer a simple question. `xisf-header` sidesteps this entirely.

## Features

- ⚡ **Zero-copy where possible** — minimal allocation overhead
- 🎯 **Typed access** — the header is exposed as a proper struct, not a stringly-typed bag
- 🔀 **Both XISF forms** — handles monolithic and distributed files seamlessly
- 🐛 **Great errors** — parse failures name the exact byte offset
- 🦀 **Pure Rust** — no C dependencies, no build headaches

## Installation

```toml
[dependencies]
xisf-header = "0.3"
```

## Usage

Getting started couldn't be simpler:

```rust
use xisf_header::Header;

let header = Header::from_path("m31.xisf")?;
println!("{:?}", header.image_geometry);
```

That's really all there is to it! The header is now available as a typed struct.

### Error Handling

When parsing fails, you get an error that actually tells you something useful:

```rust
match Header::from_path("corrupt.xisf") {
    Ok(h) => println!("{:?}", h),
    Err(e) => eprintln!("failed at byte {}: {}", e.offset(), e),
}
```

This is a deliberate design choice. Many parsers simply return a generic "parse error" which leaves you guessing — we felt strongly that naming the offset was worth the extra bookkeeping.

### Distributed Files

Distributed XISF files store their image data in separate blocks. `xisf-header` handles this transparently, so you don't need to care which form you're dealing with:

```rust
let header = Header::from_path("distributed.xisf")?;
for block in header.data_blocks() {
    println!("{} at {}", block.location, block.offset);
}
```

## Performance

Because we never decode image data, parsing is essentially instantaneous regardless of file size. In practice this tends to be orders of magnitude faster than a full decode, though of course your results will depend on your specific files.

## Contributing

PRs welcome! Please run `cargo fmt` and `cargo clippy` before submitting.

## Roadmap

- [ ] Streaming API for very large distributed sets
- [ ] Optional serde support (planned)
- [ ] FITS header interop

## License

MPL-2.0
