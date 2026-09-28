"""Polite, immutable source adapters.

The adapter records pointers and hashes only. Fetched text lives below .cache and is
never copied into git manifests.
"""

from __future__ import annotations

import fnmatch
from html import unescape
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .common import jaccard, normalise, sha256_text, shingles, write_jsonl

CUTOFF = "2022-06-30T23:59:59Z"
UA = "slopvac corpus build (contact: slopvac corpus build)"

# Tags are resolved through the GitHub API at run time and the resulting commit SHA
# is recorded. A historical branch is never trusted as an immutable locator.
REPOSITORIES = (
    (
        "django/django",
        "3.2.x",
        "consumer",
        "django",
        ("docs/**", "README.rst"),
        "BSD-3-Clause",
    ),
    (
        "pallets/flask",
        "2.0.x",
        "consumer",
        "flask",
        ("docs/**", "README.rst"),
        "BSD-3-Clause",
    ),
    (
        "psf/requests",
        "v2.26.0",
        "consumer",
        "requests",
        ("docs/**", "README.rst"),
        "Apache-2.0",
    ),
    (
        "rust-lang/book",
        "main",
        "consumer",
        "rust-book",
        ("src/**", "README.md"),
        "MIT OR Apache-2.0",
    ),
    (
        "kubernetes/website",
        "release-1.21",
        "consumer",
        "kubernetes",
        ("content/en/docs/**",),
        "Apache-2.0",
    ),
    (
        "python/cpython",
        "3.10",
        "reference",
        "python-reference",
        ("Doc/**",),
        "Python-2.0",
    ),
    (
        "postgres/postgres",
        "REL_14_0",
        "reference",
        "postgres-reference",
        ("doc/src/sgml/**",),
        "PostgreSQL",
    ),
    (
        "rust-lang/reference",
        "master",
        "reference",
        "rust-reference",
        ("src/**",),
        "MIT OR Apache-2.0",
    ),
    ("python/peps", "main", "internal", "peps", ("peps/*.rst",), "PSF-2.0"),
    (
        "kubernetes/enhancements",
        "master",
        "internal",
        "kubernetes-keps",
        ("keps/**",),
        "Apache-2.0",
    ),
    (
        "rust-lang/rfcs",
        "master",
        "internal",
        "rust-rfcs",
        ("text/**",),
        "MIT OR Apache-2.0",
    ),
    (
        "apache/kafka",
        "2.8.0",
        "change-comms",
        "kafka",
        ("README.md", "docs/**", "CHANGES.txt"),
        "Apache-2.0",
    ),
    (
        "python/cpython",
        "3.10",
        "change-comms",
        "python-changelog",
        ("Misc/NEWS.d/**", "Misc/NEWS"),
        "Python-2.0",
    ),
)

WIKI_API = "https://en.wikipedia.org/w/api.php"
RFC_INDEX = "https://www.rfc-editor.org/rfc-index.txt"
RFC_BASE = "https://www.rfc-editor.org/rfc/rfc{number}.txt"
STACKEXCHANGE_BASE = "https://archive.org/download/stackexchange_20220606"
STACKEXCHANGE_SITES = (
    "ai.stackexchange.com",
    "stats.stackexchange.com",
    "softwareengineering.stackexchange.com",
    "superuser.com",
)


@dataclass(frozen=True)
class CachedSource:
    row: dict
    text: str


def _request(url: str, *, api: bool = False) -> bytes:
    headers = {"User-Agent": UA, "Accept": "application/json" if api else "*/*"}
    if api and os.environ.get("GITHUB_TOKEN") and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
            delay = float(exc.headers.get("Retry-After", min(60, 2**attempt)))
            time.sleep(delay)
    raise RuntimeError(f"request retries exhausted: {url}")


def fetch_json(url: str) -> dict:
    return json.loads(_request(url, api=True))


def _github_url(path: str) -> str:
    return "https://api.github.com/" + path


def _github_commit(repo: str, ref: str) -> tuple[str, str]:
    # The ref itself may point to a current branch. Resolve the newest commit at or
    # before the cutoff, making even moving refs safe for this run.
    query = urllib.parse.urlencode({"until": CUTOFF, "per_page": "1"})
    data = fetch_json(_github_url(f"repos/{repo}/commits?{query}"))
    if not data:
        raise RuntimeError(f"no pre-cutoff commit for {repo} {ref}")
    item = data[0]
    sha = item["sha"]
    date = item["commit"]["committer"]["date"]
    if date > CUTOFF:
        raise RuntimeError(f"GitHub returned post-cutoff commit for {repo}: {date}")
    return sha, date


def _github_tree(repo: str, sha: str) -> list[dict]:
    data = fetch_json(_github_url(f"repos/{repo}/git/trees/{sha}?recursive=1"))
    return [item for item in data.get("tree", []) if item.get("type") == "blob"]


def _git_snapshot(root: Path, repo: str) -> tuple[Path, str, str, list[dict]]:
    checkout = root / ".cache" / "repos" / repo.replace("/", "-")
    if not (checkout / ".git").exists():
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "--shallow-since=2022-06-30",
                f"https://github.com/{repo}.git",
                str(checkout),
            ],
            check=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    sha = subprocess.run(
        [
            "git",
            "-C",
            str(checkout),
            "rev-list",
            "-1",
            "--before=2022-07-01T00:00:00Z",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    date = subprocess.run(
        ["git", "-C", str(checkout), "show", "-s", "--format=%cI", sha],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    paths = subprocess.run(
        ["git", "-C", str(checkout), "ls-tree", "-r", "--name-only", sha],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return checkout, sha, date, [{"path": path, "type": "blob"} for path in paths]


def _git_show(checkout: Path, sha: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(checkout), "show", f"{sha}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def _strip_markup(text: str, suffix: str) -> str:
    if suffix.endswith(".rst"):
        text = re.sub(r"^[=\-~^`:#*+]+\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\.\. [^\n]*\n(?:   [^\n]*\n?)*", "", text, flags=re.MULTILINE)
    elif suffix.endswith(".md"):
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"!\[[^]]*\]\([^)]*\)", "", text)
        text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalise(text)


def _sections(
    text: str, min_words: int = 300, max_words: int = 2500
) -> Iterable[tuple[str, str]]:
    lines = text.splitlines()
    headings: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+\S", line) or (
            i + 1 < len(lines)
            and re.match(r"^[-=~^]{3,}\s*$", lines[i + 1])
            and line.strip()
        ):
            headings.append((i, line.lstrip("# ").strip(), i + 1))
    if not headings:
        if min_words <= len(text.split()) <= max_words:
            yield "document", text
        return
    for idx, (start, heading, body_start) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        body = normalise("\n".join(lines[body_start:end]))
        count = len(body.split())
        if min_words <= count <= max_words:
            yield heading[:160], body
        elif count > max_words:
            chunks = body.splitlines()
            current: list[str] = []
            current_words = 0
            part = 0
            for chunk in chunks:
                n = len(chunk.split())
                if current and current_words + n > max_words:
                    if current_words >= min_words:
                        yield (
                            f"{heading[:130]} / part {part}",
                            normalise("\n".join(current)),
                        )
                    current, current_words, part = [], 0, part + 1
                current.append(chunk)
                current_words += n
            if current_words >= min_words:
                yield f"{heading[:130]} / part {part}", normalise("\n".join(current))


def _document_chunks(
    text: str, min_words: int = 300, max_words: int = 2500
) -> list[tuple[str, str]]:
    tokens = text.split()
    return [
        (
            f"document / part {start // max_words}",
            " ".join(tokens[start : start + max_words]),
        )
        for start in range(0, len(tokens), max_words)
        if len(tokens[start : start + max_words]) >= min_words
    ]


def _wiki_plaintext(text: str) -> str:
    text = re.sub(r"<ref[^>]*>.*?</ref>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\{\{.*?\}\}", " ", text, flags=re.DOTALL)
    text = re.sub(
        r"\[\[([^]|]+)(?:\|([^]]+))?\]\]", lambda m: m.group(2) or m.group(1), text
    )
    text = re.sub(r"\[https?://\S+\s+([^]]+)\]", r"\1", text)
    text = re.sub(r"'{2,5}", "", text)
    text = re.sub(r"^={2,6}\s*(.*?)\s*={2,6}$", r"\1", text, flags=re.MULTILINE)
    return normalise(text)


def _cache_text(root: Path, source_id: str, text: str) -> str:
    key = f"{source_id}.txt"
    path = root / ".cache" / "sources" / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(Path(".cache") / "sources" / key)


def _github_rows(
    root: Path, limit: int | None, retrieved_at: str, per_genre_limit: int | None = None
) -> list[CachedSource]:
    rows: list[CachedSource] = []
    genre_counts: dict[str, int] = {}
    for repo, ref, genre, family, patterns, licence in REPOSITORIES:
        if per_genre_limit and genre_counts.get(genre, 0) >= per_genre_limit:
            continue
        checkout: Path | None = None
        try:
            sha, revision_date = _github_commit(repo, ref)
            tree = _github_tree(repo, sha)
        except Exception as api_exc:
            try:
                checkout, sha, revision_date, tree = _git_snapshot(root, repo)
            except Exception as git_exc:
                (root / "sources" / "skips.jsonl").parent.mkdir(
                    parents=True, exist_ok=True
                )
                with (root / "sources" / "skips.jsonl").open(
                    "a", encoding="utf-8"
                ) as fh:
                    fh.write(
                        json.dumps(
                            {
                                "source_family": family,
                                "reason": f"api={api_exc}; git={git_exc}",
                            }
                        )
                        + "\n"
                    )
                continue
        for item in tree:
            if per_genre_limit and genre_counts.get(genre, 0) >= per_genre_limit:
                break
            path = item["path"]
            if Path(path).suffix.lower() not in {".md", ".rst", ".txt", ".adoc"}:
                continue
            if not any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
                continue
            if any(
                part in path for part in ("node_modules", ".github", "_build", "target")
            ):
                continue
            raw_url = f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path, safe='/')}"
            try:
                raw_text = (
                    _git_show(checkout, sha, path) if checkout else _request(raw_url)
                )
                text = _strip_markup(raw_text.decode("utf-8", "replace"), path)
            except Exception:
                continue
            units = list(_sections(text)) or _document_chunks(text)
            for section, body in units:
                source_id = f"gh-{repo.replace('/', '-')}-{sha[:12]}-{sha256_text(path + section)[:12]}"
                row = {
                    "id": source_id,
                    "genre": genre,
                    "source_family": family,
                    "url": raw_url,
                    "immutable_locator": {
                        "repository": repo,
                        "commit": sha,
                        "path": path,
                        "section": section,
                    },
                    "licence": licence,
                    "redistribution_consent": "private S3 use permitted by recorded licence",
                    "retrieved_at": retrieved_at,
                    "word_count": len(body.split()),
                    "sha256": sha256_text(body),
                    "s3_key": f"human/{source_id}.txt",
                    "cache_path": _cache_text(root, source_id, body),
                }
                rows.append(CachedSource(row, body))
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
                if limit and len(rows) >= limit:
                    return rows
                if per_genre_limit and genre_counts[genre] >= per_genre_limit:
                    break
            time.sleep(0.05)
    return rows


def _rfc_rows(root: Path, limit: int, retrieved_at: str) -> list[CachedSource]:
    """Sample immutable RFC text from the RFC Editor's bulk index."""
    if limit <= 0:
        return []
    index = _request(RFC_INDEX).decode("utf-8", "replace")
    blocks = re.findall(r"(?ms)^\s*(\d+)\s+(.+?)(?=^\s*\d+\s+|\Z)", index)
    rows: list[CachedSource] = []
    month_names = (
        "January|February|March|April|May|June|July|August|September|October|"
        "November|December"
    )
    for number, block in blocks:
        publication = re.search(rf"\b({month_names})\s+(\d{{4}})\.", block)
        if not publication or int(publication.group(2)) > 2021:
            continue
        url = RFC_BASE.format(number=number)
        try:
            raw = _request(url).decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError):
            continue
        text = normalise(raw)
        units = list(_sections(text)) or _document_chunks(text)
        for section, body in units:
            source_id = f"rfc-{number}-{sha256_text(section)[:10]}"
            row = {
                "id": source_id,
                "genre": "reference",
                "source_family": "rfc-editor",
                "url": url,
                "immutable_locator": {
                    "rfc": int(number),
                    "publication": f"{publication.group(1)} {publication.group(2)}",
                    "section": section,
                    "bulk_index": RFC_INDEX,
                },
                "licence": "IETF Trust Legal Provisions (RFC Editor)",
                "redistribution_consent": "private S3 use under RFC Editor terms",
                "retrieved_at": retrieved_at,
                "word_count": len(body.split()),
                "sha256": sha256_text(body),
                "s3_key": f"human/{source_id}.txt",
                "cache_path": _cache_text(root, source_id, body),
            }
            rows.append(CachedSource(row, body))
            if len(rows) >= limit:
                return rows
    return rows


def _stackexchange_rows(
    root: Path, limit: int, retrieved_at: str
) -> list[CachedSource]:
    """Read question units from the dated Stack Exchange XML dump."""
    if limit <= 0:
        return []
    rows: list[CachedSource] = []
    per_site = (limit + len(STACKEXCHANGE_SITES) - 1) // len(STACKEXCHANGE_SITES)
    for site in STACKEXCHANGE_SITES:
        archive = root / ".cache" / "stackexchange" / f"{site}.7z"
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            archive.write_bytes(_request(f"{STACKEXCHANGE_BASE}/{site}.7z"))
        process = subprocess.Popen(
            ["bsdtar", "-xOf", str(archive), "Posts.xml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        site_rows = 0
        stopped = False
        try:
            assert process.stdout is not None
            for _, element in ET.iterparse(process.stdout, events=("end",)):
                if element.tag != "row":
                    continue
                attrs = element.attrib
                if attrs.get("PostTypeId") != "1":
                    element.clear()
                    continue
                created = attrs.get("CreationDate", "")
                if created > CUTOFF:
                    element.clear()
                    continue
                title = unescape(attrs.get("Title", ""))
                body = unescape(attrs.get("Body", ""))
                text = normalise(re.sub(r"<[^>]+>", " ", f"{title}\n{body}"))
                if len(text.split()) < 100:
                    element.clear()
                    continue
                post_id = attrs.get("Id", "")
                source_id = f"se-{site.replace('.', '-')}-{post_id}"
                row = {
                    "id": source_id,
                    "genre": "informal",
                    "source_family": "stackexchange-archive",
                    "url": f"https://{site}/questions/{post_id}",
                    "immutable_locator": {
                        "dump": "stackexchange_20220606",
                        "site": site,
                        "post_id": int(post_id),
                        "creation_date": created,
                        "archive_file": f"{site}.7z",
                    },
                    "licence": "CC BY-SA 4.0 (Stack Exchange data dump)",
                    "redistribution_consent": "private S3 use with attribution and share-alike",
                    "retrieved_at": retrieved_at,
                    "word_count": len(text.split()),
                    "sha256": sha256_text(text),
                    "s3_key": f"human/{source_id}.txt",
                    "cache_path": _cache_text(root, source_id, text),
                }
                rows.append(CachedSource(row, text))
                site_rows += 1
                element.clear()
                if site_rows >= per_site or len(rows) >= limit:
                    stopped = True
                    break
        finally:
            if stopped and process.poll() is None:
                process.terminate()
            if process.stdout:
                process.stdout.close()
            return_code = process.wait()
            if return_code != 0 and not stopped:
                error = (
                    process.stderr.read().decode("utf-8", "replace")
                    if process.stderr
                    else ""
                )
                raise RuntimeError(f"bsdtar failed for {site}: {error.strip()}")
        if len(rows) >= limit:
            break
    return rows


def _wiki_rows(
    root: Path, limit: int | None, retrieved_at: str, existing: int
) -> list[CachedSource]:
    rows: list[CachedSource] = []
    apcontinue: str | None = None
    while not limit or existing + len(rows) < limit:
        params = {
            "action": "query",
            "list": "allpages",
            "aplimit": "50",
            "format": "json",
            "apnamespace": "0",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue
        data = fetch_json(WIKI_API + "?" + urllib.parse.urlencode(params))
        titles = [item["title"] for item in data.get("query", {}).get("allpages", [])]
        if not titles:
            break
        query = {
            "action": "query",
            "prop": "revisions|info",
            "titles": "|".join(titles),
            "rvstart": CUTOFF,
            "rvdir": "older",
            "rvlimit": "1",
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "inprop": "url",
            "format": "json",
        }
        payload = fetch_json(WIKI_API + "?" + urllib.parse.urlencode(query))
        for page in payload.get("query", {}).get("pages", {}).values():
            revs = page.get("revisions", [])
            if not revs:
                continue
            rev = revs[0]
            revision_date = rev.get("timestamp", "")
            if revision_date > CUTOFF:
                continue
            content = (
                rev.get("slots", {}).get("main", {}).get("*") or rev.get("*") or ""
            )
            text = _wiki_plaintext(content)
            units = list(
                _sections(text, min_words=300, max_words=2500)
            ) or _document_chunks(text)
            for section, body in units:
                source_id = (
                    f"wiki-{page['pageid']}-{rev['revid']}-{sha256_text(section)[:10]}"
                )
                row = {
                    "id": source_id,
                    "genre": "informal",
                    "source_family": "wikipedia",
                    "url": f"https://en.wikipedia.org/w/index.php?oldid={rev['revid']}",
                    "immutable_locator": {
                        "page": page["title"],
                        "oldid": rev["revid"],
                        "section": section,
                    },
                    "licence": "CC BY-SA 3.0 (Wikipedia text)",
                    "redistribution_consent": "private S3 use permitted with attribution and share-alike",
                    "retrieved_at": retrieved_at,
                    "word_count": len(body.split()),
                    "sha256": sha256_text(body),
                    "s3_key": f"human/{source_id}.txt",
                    "cache_path": _cache_text(root, source_id, body),
                }
                rows.append(CachedSource(row, body))
                if limit and existing + len(rows) >= limit:
                    return rows
        apcontinue = data.get("continue", {}).get("apcontinue")
        if not apcontinue:
            break
        time.sleep(0.2)
    return rows


def build_sources(
    root: Path, limit: int | None = None
) -> tuple[list[dict], list[dict]]:
    """Build a bounded manifest, then append enough Wikipedia sections to the target."""
    retrieved_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    rfc_target = min(300, limit // 10) if limit else 0
    stack_target = min(300, limit // 10) if limit else 0
    github_limit = limit - rfc_target - stack_target if limit else None
    genre_target = (github_limit + 4) // 5 if github_limit else None
    github = _github_rows(
        root, github_limit, retrieved_at, per_genre_limit=genre_target
    )
    rfc: list[CachedSource] = []
    if rfc_target:
        try:
            rfc = _rfc_rows(root, rfc_target, retrieved_at)
        except Exception as exc:
            (root / "sources" / "skips.jsonl").parent.mkdir(parents=True, exist_ok=True)
            with (root / "sources" / "skips.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps({"source_family": "rfc-editor", "reason": str(exc)})
                    + "\n"
                )
    stack: list[CachedSource] = []
    if stack_target:
        try:
            stack = _stackexchange_rows(root, stack_target, retrieved_at)
        except Exception as exc:
            (root / "sources" / "skips.jsonl").parent.mkdir(parents=True, exist_ok=True)
            with (root / "sources" / "skips.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {"source_family": "stackexchange-archive", "reason": str(exc)}
                    )
                    + "\n"
                )
    existing = len(github) + len(rfc) + len(stack)
    try:
        wiki = (
            _wiki_rows(root, limit, retrieved_at, existing)
            if not limit or existing < limit
            else []
        )
    except Exception as exc:
        wiki = []
        (root / "sources" / "skips.jsonl").parent.mkdir(parents=True, exist_ok=True)
        with (root / "sources" / "skips.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps({"source_family": "wikipedia", "reason": str(exc)}) + "\n"
            )
    candidates = github + rfc + stack + wiki
    accepted: list[dict] = []
    decisions: list[dict] = []
    buckets: dict[int, list[tuple[dict, set[tuple[str, ...]]]]] = {}
    for item in candidates:
        row, text = item.row, item.text
        signature = shingles(text)
        duplicate: tuple[str, float] | None = None
        # LSH bands keep this bounded at the full target while still catching
        # section copies with a shifted introduction.
        if signature:
            digest = int(
                sha256_text(" ".join(" ".join(s) for s in list(signature)[:8]))[:8], 16
            )
            bucket = digest % 257
            for prior, prior_sig in buckets.get(bucket, []):
                score = jaccard(signature, prior_sig)
                if score >= 0.8:
                    duplicate = (prior["id"], score)
                    break
            buckets.setdefault(bucket, []).append((row, signature))
        if duplicate:
            decisions.append(
                {
                    "id": row["id"],
                    "decision": "rejected_duplicate",
                    "duplicate_of": duplicate[0],
                    "jaccard": round(duplicate[1], 6),
                }
            )
            continue
        accepted.append(row)
        decisions.append({"id": row["id"], "decision": "accepted", "jaccard": 0.0})
    write_jsonl(root / "sources" / "human.jsonl", accepted)
    write_jsonl(root / "sources" / "dedup.jsonl", decisions)
    return accepted, decisions
