//! Content-Length framing (plugin-protocol.md section 2.1).

use std::io::{self, BufRead, Read, Write};

use slopvac_sanitize::line as esc;
use thiserror::Error;

use crate::messages::host::{self as messages, HostPhrase, HostText};

/// Longest header line, without its line ending.
pub const MAX_HEADER_LINE: usize = 1024;
/// Most header lines in one block.
pub const MAX_HEADER_LINES: usize = 8;

/// Why a frame could not be read.
#[derive(Debug, Error)]
pub enum FrameError {
    /// The bytes break the framing rules. Fatal for the connection.
    #[error("{}", esc(.0))]
    Framing(String),
    /// The stream failed.
    #[error("{}", messages::frame_read_failed(.0))]
    Io(#[from] io::Error),
}

fn framing(msg: impl Into<String>) -> FrameError {
    FrameError::Framing(msg.into())
}

/// Read one header line. `Ok(None)` is end of stream before any byte.
fn read_line<R: BufRead>(r: &mut R) -> Result<Option<Vec<u8>>, FrameError> {
    let mut line: Vec<u8> = Vec::new();
    loop {
        let buf = r.fill_buf()?;
        if buf.is_empty() {
            if line.is_empty() {
                return Ok(None);
            }
            return Err(framing(HostPhrase::EndInHeaderLine.as_static()));
        }
        let (take, found) = match buf.iter().position(|&b| b == b'\n') {
            Some(i) => (i + 1, true),
            None => (buf.len(), false),
        };
        // The line ending adds two bytes beyond the content limit.
        if line.len() + take > MAX_HEADER_LINE + 2 {
            return Err(framing(
                HostText::HeaderTooLong {
                    max: MAX_HEADER_LINE,
                }
                .to_string(),
            ));
        }
        line.extend_from_slice(&buf[..take]);
        r.consume(take);
        if found {
            break;
        }
    }
    if !line.ends_with(b"\r\n") {
        return Err(framing(HostPhrase::NoCrlf.as_static()));
    }
    line.truncate(line.len() - 2);
    if line.contains(&b'\r') || line.contains(&b'\n') {
        return Err(framing(HostPhrase::StrayCrLf.as_static()));
    }
    Ok(Some(line))
}

/// Parse a `Content-Length` value with checked arithmetic.
fn parse_length(value: &[u8]) -> Result<usize, FrameError> {
    if value.is_empty() || !value.iter().all(u8::is_ascii_digit) {
        return Err(framing(HostPhrase::LengthNotDecimal.as_static()));
    }
    if value.len() > 1 && value[0] == b'0' {
        return Err(framing(HostPhrase::LengthLeadingZeros.as_static()));
    }
    let mut n: u64 = 0;
    for &d in value {
        n = n
            .checked_mul(10)
            .and_then(|n| n.checked_add(u64::from(d - b'0')))
            .ok_or_else(|| framing(HostPhrase::LengthOverflow64.as_static()))?;
    }
    usize::try_from(n).map_err(|_| framing(HostPhrase::LengthOverflowSize.as_static()))
}

/// Read one frame body, or `None` at a clean end of stream.
///
/// `max_body` is checked before any body byte is read or buffer allocated.
///
/// # Errors
/// [`FrameError::Framing`] for any rule violation, [`FrameError::Io`] for a stream failure.
pub fn read_frame<R: BufRead>(r: &mut R, max_body: usize) -> Result<Option<Vec<u8>>, FrameError> {
    read_frame_with(r, &|| max_body)
}

/// Like [`read_frame`], but asks for the limit once the header block is in.
///
/// A limit that changes while the reader waits for the next frame (the
/// `initialize` negotiation) applies to the frame that arrives afterwards.
///
/// # Errors
/// As [`read_frame`].
pub fn read_frame_with<R: BufRead>(
    r: &mut R,
    max_body: &dyn Fn() -> usize,
) -> Result<Option<Vec<u8>>, FrameError> {
    let mut length: Option<usize> = None;
    let mut lines = 0;
    let mut first = true;
    loop {
        let Some(line) = read_line(r)? else {
            return if first {
                Ok(None)
            } else {
                Err(framing(HostPhrase::EndInHeaderBlock.as_static()))
            };
        };
        first = false;
        if line.is_empty() {
            break;
        }
        lines += 1;
        if lines > MAX_HEADER_LINES {
            return Err(framing(
                HostText::TooManyHeaders {
                    max: MAX_HEADER_LINES,
                }
                .to_string(),
            ));
        }
        let Some(colon) = line.iter().position(|&b| b == b':') else {
            return Err(framing(HostPhrase::NoColon.as_static()));
        };
        let (name, value) = (&line[..colon], &line[colon + 1..]);
        if name.eq_ignore_ascii_case(b"content-length") {
            if length.is_some() {
                return Err(framing(HostPhrase::DuplicateLength.as_static()));
            }
            length = Some(parse_length(value.trim_ascii())?);
        }
    }
    let len = length.ok_or_else(|| framing(HostPhrase::MissingLength.as_static()))?;
    let max_body = max_body();
    if len > max_body {
        return Err(framing(
            HostText::BodyTooLong { len, max: max_body }.to_string(),
        ));
    }
    let mut body = Vec::new();
    let got = r.take(len as u64).read_to_end(&mut body)?;
    if got < len {
        return Err(framing(HostPhrase::EndInBody.as_static()));
    }
    Ok(Some(body))
}

/// Encode one frame.
#[must_use]
pub fn encode_frame(body: &[u8]) -> Vec<u8> {
    // ast-grep-ignore: user-text-literal
    let mut out = format!("Content-Length: {}\r\n\r\n", body.len()).into_bytes();
    out.extend_from_slice(body);
    out
}

/// Write one frame and flush.
///
/// # Errors
/// Any write error.
pub fn write_frame<W: Write>(w: &mut W, body: &[u8]) -> io::Result<()> {
    w.write_all(&encode_frame(body))?;
    w.flush()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn read(bytes: &[u8], max: usize) -> Result<Option<Vec<u8>>, FrameError> {
        read_frame(&mut io::BufReader::new(bytes), max)
    }

    fn is_framing(r: &Result<Option<Vec<u8>>, FrameError>) -> bool {
        matches!(r, Err(FrameError::Framing(_)))
    }

    #[test]
    fn round_trips_a_body() {
        let framed = encode_frame(b"{\"a\":1}");
        assert_eq!(read(&framed, 100).unwrap().unwrap(), b"{\"a\":1}");
    }

    #[test]
    fn clean_end_of_stream_is_none() {
        assert!(read(b"", 10).unwrap().is_none());
    }

    #[test]
    fn extra_headers_and_case_are_accepted() {
        let r = read(b"content-length:  2\r\nContent-Type: x\r\n\r\n{}", 10).unwrap();
        assert_eq!(r.unwrap(), b"{}");
    }

    #[test]
    fn body_at_limit_passes_and_one_more_fails_before_reading() {
        assert!(read(b"Content-Length: 4\r\n\r\nabcd", 4).is_ok());
        // The body is absent: the error must come from the length check alone.
        let r = read(b"Content-Length: 5\r\n\r\n", 4);
        match r {
            Err(FrameError::Framing(m)) => assert!(m.contains("exceeds the limit"), "{m}"),
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn bad_content_length_values() {
        let cases: &[&[u8]] = &[
            b"Content-Length: -1\r\n\r\n",
            b"Content-Length: +1\r\n\r\n",
            b"Content-Length: 0x10\r\n\r\n",
            b"Content-Length: 01\r\n\r\n",
            b"Content-Length: \r\n\r\n",
            b"Content-Length: 18446744073709551616\r\n\r\n",
            b"Content-Length: 99999999999999999999999\r\n\r\n",
            b"Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}",
            b"Content-Length: 2\r\nContent-Length: 3\r\n\r\n{}",
            b"Content-Type: x\r\n\r\n{}",
        ];
        for case in cases {
            assert!(
                is_framing(&read(case, 1 << 20)),
                "{}",
                String::from_utf8_lossy(case)
            );
        }
    }

    #[test]
    fn length_over_u32_with_small_limit_is_refused_before_allocating() {
        // 4294967296 fits in usize on 64-bit hosts and must still hit the limit.
        assert!(is_framing(&read(
            b"Content-Length: 4294967296\r\n\r\n",
            16 * 1024 * 1024
        )));
    }

    #[test]
    fn length_zero_is_valid() {
        assert_eq!(
            read(b"Content-Length: 0\r\n\r\n", 10).unwrap().unwrap(),
            b""
        );
    }

    #[test]
    fn a_header_line_without_a_colon_is_a_framing_error() {
        assert!(is_framing(&read(
            b"Content-Length: 2\r\nContent-Type\r\n\r\n{}",
            10
        )));
    }

    #[test]
    fn bare_newline_is_a_framing_error() {
        assert!(is_framing(&read(b"Content-Length: 2\n\n{}", 10)));
    }

    #[test]
    fn long_header_line_is_a_framing_error() {
        let mut v = b"X: ".to_vec();
        v.extend(std::iter::repeat_n(b'a', 2000));
        v.extend_from_slice(b"\r\nContent-Length: 0\r\n\r\n");
        assert!(is_framing(&read(&v, 10)));
    }

    #[test]
    fn nine_header_lines_fail_and_eight_pass() {
        let mut ok = "X: a\r\n".repeat(7);
        ok.push_str("Content-Length: 0\r\n\r\n");
        assert!(read(ok.as_bytes(), 10).is_ok());
        let bad = format!("X7: a\r\n{ok}");
        assert!(is_framing(&read(bad.as_bytes(), 10)));
    }

    #[test]
    fn stray_text_before_a_frame_is_a_framing_error() {
        assert!(is_framing(&read(
            b"hello world\r\nContent-Length: 0\r\n\r\n",
            10
        )));
    }

    #[test]
    fn truncated_body_is_a_framing_error() {
        assert!(is_framing(&read(b"Content-Length: 10\r\n\r\nabc", 100)));
    }
}
