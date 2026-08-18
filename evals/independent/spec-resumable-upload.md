# Resumable Chunked Upload Protocol (RCUP), Version 1

## Status of This Document

This document specifies an application-layer protocol for the resumable
transfer of octet streams over HTTP/1.1 and HTTP/2. Distribution of this
document is unlimited.

## 1. Introduction

Large file transfers over unreliable networks frequently terminate before
completion. When a transfer terminates, a client that lacks a means of
determining how much of the representation the server has durably stored
must retransmit the entire representation. This document defines a protocol
by which a client and a server negotiate a byte offset, transmit the
remainder of a representation in one or more chunks, and verify the
integrity of the assembled result.

### 1.1 Terminology

The key words MUST, MUST NOT, REQUIRED, SHALL, SHOULD, SHOULD NOT, MAY, and
OPTIONAL in this document are to be interpreted as described in BCP 14.

Upload resource
: A server-side resource, identified by a URI, that accumulates the octets
  of a single representation across one or more requests.

Committed offset
: The number of contiguous octets, counted from the beginning of the
  representation, that the server has durably stored for a given upload
  resource.

Chunk
: The payload body of a single request that appends octets to an upload
  resource.

## 2. Protocol Overview

The protocol comprises four operations: creation of an upload resource
(Section 3), offset negotiation (Section 4), chunk transmission
(Section 5), and integrity verification (Section 6). An upload resource is
subject to expiry (Section 7).

## 3. Creation of an Upload Resource

A client initiates an upload by issuing a POST request to a
server-designated collection URI. The client MUST include the
`Upload-Length` header field, whose value is the total size in octets of
the complete representation, expressed as a non-negative decimal integer.

The client MAY include the `Upload-Digest` header field, carrying the
expected digest of the complete representation as defined in Section 6.

A server that accepts the request MUST respond with status code `201
Created`, a `Location` header field bearing the absolute URI of the upload
resource, and an `Upload-Offset` header field whose value is `0`.

A server that declines the request because `Upload-Length` exceeds a
configured maximum MUST respond with status code `413 Content Too Large`
and SHOULD include the `Upload-Max-Length` header field stating that
maximum.

## 4. Offset Negotiation

Before transmitting or retransmitting a chunk, a client whose knowledge of
the committed offset is uncertain MUST issue a HEAD request to the upload
resource URI.

A server responding to such a request MUST include:

1. an `Upload-Offset` header field whose value is the committed offset;
2. an `Upload-Length` header field whose value is the total size declared
   at creation;
3. a `Cache-Control` header field with the `no-store` directive.

The response MUST NOT include a payload body.

A client MUST treat the value of `Upload-Offset` as authoritative and MUST
resume transmission at that offset. A client MUST NOT assume that the
committed offset equals the sum of octets it has previously transmitted; a
server MAY have discarded octets that were not durably stored.

## 5. Chunk Transmission

A client appends octets by issuing a PATCH request to the upload resource
URI. The request MUST satisfy all of the following:

- The `Content-Type` header field MUST be
  `application/partial-upload`.
- The `Upload-Offset` header field MUST be present and MUST state the
  offset at which the chunk begins.
- The `Content-Length` header field MUST be present and MUST state the
  length of the chunk in octets.

If the value of `Upload-Offset` does not equal the server's committed
offset, the server MUST reject the request with status code `409 Conflict`
and MUST include its own `Upload-Offset` in the response. The server MUST
NOT store any part of the rejected chunk.

If the chunk is accepted and the upload remains incomplete, the server MUST
respond with status code `204 No Content` and an `Upload-Offset` header
field stating the new committed offset. The server MUST NOT acknowledge
octets that are not durably stored.

If the new committed offset equals the declared `Upload-Length`, the server
MUST perform verification as specified in Section 6 before responding.

A client MAY select any chunk size. A server MAY reject a chunk that
exceeds a configured maximum with status code `413 Content Too Large` and
SHOULD advertise that maximum in the `Upload-Chunk-Max-Size` header field
of every HEAD response.

## 6. Integrity Verification

Digests are expressed as a token naming a hash algorithm, followed by
U+003A COLON, followed by the base64 encoding of the hash output. Servers
MUST support `sha-256` and MAY support additional algorithms.

A client MAY include `Upload-Chunk-Digest` on a PATCH request, covering
only the octets of that chunk. A server that receives this field MUST
compute the digest of the received chunk and, on mismatch, MUST discard the
chunk and respond with status code `422 Unprocessable Content`. The
committed offset MUST remain unchanged.

Upon receipt of the final chunk, a server holding an `Upload-Digest` value
MUST compute the digest of the assembled representation. On mismatch, the
server MUST delete the upload resource and respond with status code `422
Unprocessable Content`. On match, the server MUST respond with status code
`201 Created` and a `Location` header field identifying the completed
resource.

## 7. Expiry of Partial Uploads

A server MUST assign an expiry instant to each upload resource and MUST
communicate it in the `Upload-Expires` header field of every `201` and
`204` response and of every HEAD response. The value is an HTTP-date.

A server MUST reset the expiry instant upon each accepted PATCH request. A
server MAY reclaim the storage of an upload resource whose expiry instant
has passed. A request addressed to a reclaimed upload resource MUST receive
status code `404 Not Found`, and the client MUST restart the upload as
specified in Section 3.

## 8. Security Considerations

An upload resource URI functions as a bearer capability. Servers MUST
generate upload resource identifiers with at least 128 bits of entropy
drawn from a cryptographically secure source, and MUST require the
transport to be TLS. Digest verification detects corruption; it does not
authenticate the sender. Servers MUST enforce per-principal quotas on the
aggregate size of unexpired upload resources.
