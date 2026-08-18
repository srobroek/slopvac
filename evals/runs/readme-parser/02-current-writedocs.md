# xisf-header

Reads the XML header of an XISF astronomical image file into a typed struct. The image data blocks are not decoded.

XISF is the image format of PixInsight. A file begins with a 16-byte signature, then a UTF-8 XML header describing every image, property, and data block in the file. `xisf-header` reads that header and stops.

## Install

```toml
[dependencies]
xisf-header = "0.4"
```

## Read a header

```rust
use xisf_header::Header;

let header = Header::from_path("m42.xisf")?;

for image in &header.images {
    println!("{:?} {} {:?}", image.geometry, image.sample_format, image.color_space);
}
```

`Header::from_path` opens the file, reads the signature and the declared header length, reads exactly that many bytes, and parses them. A 4 GiB image file costs one read of the header region.

From bytes already in memory:

```rust
use xisf_header::Header;

let bytes = std::fs::read("m42.xisf")?;
let header = Header::from_bytes(&bytes)?;
```

From any reader:

```rust
use std::fs::File;
use xisf_header::Header;

let header = Header::from_reader(File::open("m42.xisf")?)?;
```

`from_reader` requires `Read` only; it does not seek.

## Types

| Type | Contents |
| --- | --- |
| `Header` | `form`, `images`, `properties`, `metadata`, `header_len` |
| `Image` | `geometry`, `sample_format`, `color_space`, `bounds`, `location`, `id`, `properties`, `fits_keywords` |
| `Geometry` | `width`, `height`, `channels` |
| `SampleFormat` | `UInt8`, `UInt16`, `UInt32`, `UInt64`, `Float32`, `Float64`, `Complex32`, `Complex64` |
| `ColorSpace` | `Gray`, `RGB`, `CIELab` |
| `DataLocation` | `Attachment { offset, size }`, `Embedded(Vec<u8>)`, `Url { url, index }`, `Path { path, index }` |
| `Property` | `id`, `value: PropertyValue` |
| `PropertyValue` | Scalar, string, time-point, vector, and matrix variants |
| `Form` | `Monolithic`, `Distributed` |

`Image::location` is the entry point for reading pixels yourself: `Attachment` carries the byte offset and length within the same file.

## Monolithic and distributed files

A monolithic XISF file holds the header and the data blocks in one file. A distributed file holds an `.xisf` header whose data blocks are `Url` or `Path` locations pointing at separate files.

`Header::form` reports which one was read. Both parse through the same call.

```rust
use xisf_header::{DataLocation, Form, Header};

let header = Header::from_path("survey.xisf")?;

if header.form == Form::Distributed {
    for image in &header.images {
        match &image.location {
            DataLocation::Path { path, .. } => println!("block at {}", path.display()),
            DataLocation::Url { url, .. } => println!("block at {url}"),
            _ => {}
        }
    }
}
```

Referenced block files are not opened or validated.

## Errors

Every parse failure returns `Error` and names the byte offset in the file where the failure was detected.

```rust
use xisf_header::{Error, Header};

match Header::from_path("truncated.xisf") {
    Ok(header) => println!("{} images", header.images.len()),
    Err(Error::Truncated { offset, expected }) => {
        eprintln!("file ends at byte {offset}, header declares {expected} bytes");
    }
    Err(err) => eprintln!("{err}"),
}
```

| Variant | Condition |
| --- | --- |
| `BadSignature { offset, found }` | The first 8 bytes are not `XISF0100` |
| `Truncated { offset, expected }` | The file is shorter than the declared header length |
| `Xml { offset, source }` | The header region is not well-formed XML |
| `MissingAttribute { offset, element, attribute }` | A required attribute is absent |
| `UnknownValue { offset, attribute, found }` | An attribute value is outside the XISF 1.0 enumeration |
| `Io(std::io::Error)` | The underlying reader failed |

`Display` on `Error` includes the offset, so `{err}` alone is enough for a log line. Offsets are absolute file positions, not positions within the XML.

## FITS keywords

XISF carries FITS keywords as `<FITSKeyword>` elements. They are parsed into `Image::fits_keywords` as `(name, value, comment)` triples in file order, with duplicates preserved.

```rust
let exposure = header.images[0]
    .fits_keywords
    .iter()
    .find(|kw| kw.name == "EXPTIME")
    .map(|kw| kw.value.as_str());
```

## Feature flags

| Flag | Default | Effect |
| --- | --- | --- |
| `std` | on | Filesystem and reader constructors |
| `serde` | off | `Serialize` and `Deserialize` on every public type |

With `default-features = false` the crate is `no_std` with `alloc`, and `Header::from_bytes` is the only constructor.

## Specification

Implements the header portion of the XISF 1.0 specification. Unknown elements and attributes are retained in `Header::metadata` rather than rejected.

## License

MPL-2.0
