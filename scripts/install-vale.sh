#!/usr/bin/env bash
# Install one Vale release on a Linux runner, verified against the checksum file
# the same release publishes. Every workflow and the composite action call this
# instead of carrying their own curl/tar/install recipe.
#
# Usage: install-vale.sh <version>   (e.g. 3.15.2)
set -euo pipefail

version="${1:?usage: install-vale.sh <version>}"
base="https://github.com/errata-ai/vale/releases/download/v${version}"
archive="vale_${version}_Linux_64-bit.tar.gz"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

curl -sSfL -o "$work/$archive" "$base/$archive"
curl -sSfL -o "$work/checksums.txt" "$base/vale_${version}_checksums.txt"
(cd "$work" && grep " ${archive}\$" checksums.txt | sha256sum -c -)
tar -xzf "$work/$archive" -C "$work" vale
sudo install -m 0755 "$work/vale" /usr/local/bin/vale
vale --version
