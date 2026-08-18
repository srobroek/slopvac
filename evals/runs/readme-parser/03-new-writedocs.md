# xisf-header

`xisf-header` reads the XML header from an XISF astronomical image file and returns it as a typed struct. It does not decode, decompress, or read pixel data.

XISF is the image format of PixInsight. A single `.xisf` file can carry gigabytes of pixel data behind a header of a few kilobytes. `xisf-header` reads the signature, the 4-byte header length, and that many bytes of XML, then stops.

## Install

```toml
[dependencies]
xisf-header = "0.4"
```

## Read a header

```rust
use xisf_header::Header;

fn main() -> Result<(), xisf_header::Error> {
    let header = Header::from_path("m31.xisf")?;

    for image in &header.images {
        println!("{:?} {:?}", image.geometry, image.sample_format);
    }
    Ok(())
}
```

Read from any `Read + Seek` source with `Header::from_reader`:

```rust
use std::io::Cursor;
use xisf_header::Header;

let header = Header::from_reader(Cursor::new(bytes))?;
```

## Types

`Header` holds the parsed document:

```rust
pub struct Header {
    pub version: String,
    pub images: Vec<Image>,
    pub properties: Vec<Property>,
    pub metadata: Vec<Property>,
}
```

`Image` describes one `<Image>` element:

```rust
pub struct Image {
    pub geometry: Geometry,          // width, height, channels
    pub sample_format: SampleFormat, // UInt8 .. Float64, Complex32, Complex64
    pub color_space: ColorSpace,     // Gray, RGB, CIELab
    pub location: Location,          // where the pixel data lives
    pub compression: Option<Compression>,
    pub bounds: Option<(f64, f64)>,
    pub id: Option<String>,
    pub fits_keywords: Vec<FitsKeyword>,
    pub properties: Vec<Property>,
}
```

`Property` carries an XISF property with its declared type:

```rust
pub struct Property {
    pub id: String,
    pub value: PropertyValue, // Int64, Float64, String, TimePoint, Vector, Matrix, ...
}
```

## Monolithic and distributed files

XISF stores pixel data either inside the same file or in a separate file. `Location` names which form the header declares:

```rust
pub enum Location {
    /// Monolithic: pixel data lives in this file.
    Attachment { position: u64, size: u64 },
    /// Distributed: pixel data lives at this path or URL.
    Url { url: String, index: Option<u64> },
    /// Pixel data is inline base64 inside the header.
    Embedded,
}
```

`xisf-header` does not resolve a `Url` and does not read the bytes at an `Attachment`. Both variants give you the offset or target so you can read the data yourself.

A distributed XISF header file uses the `.xisf` extension and carries the same signature as a monolithic file, so one code path reads both.

## Errors

Every parse error names the byte offset in the file where the parser stopped:

```rust
match Header::from_path("truncated.xisf") {
    Err(e) => println!("{e}"),
    Ok(_) => {}
}
// XML is not well-formed at byte 1284: mismatched closing tag
```

```rust
pub enum Error {
    Io(std::io::Error),
    /// The first 8 bytes are not "XISF0100".
    BadSignature { found: [u8; 8] },
    /// The declared header length exceeds the file length.
    HeaderLengthOutOfRange { declared: u32, file_len: u64 },
    Xml { offset: u64, reason: String },
    /// A required attribute or element is absent.
    MissingField { offset: u64, field: &'static str },
    /// An attribute value does not parse as its declared type.
    InvalidValue { offset: u64, field: &'static str, value: String },
}
```

`Error` implements `std::error::Error` and `Display`. Variants that carry an offset expose it through `Error::offset() -> Option<u64>`.

## Limits

- `Header::from_path` rejects a declared header length above 64 MiB with `HeaderLengthOutOfRange`. Change the ceiling with `Header::from_path_with_limit`.
- The crate reads XISF 1.0 files (signature `XISF0100`).
- `no_std` is not supported; the crate uses `std::io`.

## Minimum supported Rust version

1.74.

## License

MPL-2.0
