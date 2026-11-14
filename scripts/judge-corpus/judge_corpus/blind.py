"""Blind evaluation set: human documents the judges never trained on, and LLM
documents generated to match each one on topic, outcome and prose structure.

`admit_sources` samples fresh units from the source families of
sources/human.jsonl: the same pinned git commits, Stack Exchange dump,
Wikipedia and RFC Editor. It takes only files, posts, pages and RFCs that no
corpus source came from, and only text last revised before BLIND_CUTOFF. Every
candidate is compared, by word 5-gram shingles, with every cached corpus
source unit, generated document, bank passage and item text, and with the
blind units already admitted; near-duplicates are rejected.

`run_briefs` and `run_generation` run batch.py on a separate root,
.cache/blind/, so the brief and generation prompts, model bodies, the
vendor/tier rotation and the source leak filter are the corpus ones. Every
call runs on demand (one blind model input is far below the Bedrock batch
minimum of 100 records) and is recorded in the shared cost ledger. A brief
whose generation failed or leaked gets the next model in the rotation, from a
vendor its other document does not have.

`build_items` lints every blind document at SLOPVAC_LINT_ROOT. It writes a
finding-confirmation item for every finding and semantic-detection items over
up to REGIONS prose regions per document, each region asked every kept
judgement rule, in the export format the SageMaker eval container reads
(export.py). The labels are unknown: rows carry the placeholder labels the
container needs to run, and label_origin UNLABELLED, which the container's
metrics never score. blind_report.py reads the eval predictions.

Text stays under .cache/blind/ and s3://<corpus bucket>/blind/. The committed
blind/manifest.json holds pointers, digests and counts only.
"""

from __future__ import annotations

import fnmatch
import functools
import json
import os
import re
import statistics
import subprocess
import time
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from .batch import (
    collect_briefs,
    collect_generated,
    generation_prompt,
    model_body,
    parse_output,
    prepare_briefs,
    prepare_generation,
)
from .bedrock import pricing_for, upload, upload_text
from .common import (
    normalise,
    read_jsonl,
    sha256_text,
    shingles,
    token_estimate,
    write_jsonl,
)
from .export import (
    CHOICE_CRITERIA,
    _choice_instructions,
    _noul_instructions,
    render_state,
)
from .items import (
    BANK_PATH,
    CANONICAL,
    _make_item,
    _offset,
    _lint_text,
    _pick_region,
    _prose_paragraphs,
    _relative_anchor,
    _rules_current,
    _run_lint,
    _set_region,
    digest,
    granularity,
    held_out,
    load_tokenizers,
    prose_words,
    seed,
    semantic_rules,
)
from .ondemand import run_ondemand
from .sources import (
    REPOSITORIES,
    RFC_BASE,
    RFC_INDEX,
    STACKEXCHANGE_SITES,
    WIKI_API,
    _document_chunks,
    _git_snapshot,
    _github_url,
    _request,
    _sections,
    _strip_markup,
    _wiki_plaintext,
    fetch_json,
)

BLIND = Path(".cache/blind")
S3_PREFIX = "blind"
# Committed pointers, digests and counts (no text).
MANIFEST = Path("blind/manifest.json")
# Every admitted human unit was last revised before this instant.
BLIND_CUTOFF = "2022-01-01T00:00:00Z"
WIKI_RVSTART = "2021-12-31T23:59:59Z"
# Documents per genre and family group. "git" is every git family of the genre
# that sources/human.jsonl holds, taken in turn.
GROUP_QUOTAS = {
    "consumer": {"git": 40},
    "internal": {"git": 40},
    "change-comms": {"git": 40},
    "reference": {"git": 20, "rfc-editor": 20},
    "informal": {"stackexchange-archive": 20, "wikipedia": 20},
}
# Candidates drawn per family: this many times its fair share of the group quota.
POOL_FACTOR = 3
# Unit length bounds in words (sources.py takes 300 to 2,500). The corpus took
# every release note of 300 words or more, so change-comms units may be shorter.
MIN_WORDS = {"change-comms": 150}
DEFAULT_MIN_WORDS = 300
GIT_POOL_FLOOR = 30
# Keep one in SE_SAMPLE eligible questions while streaming a site's dump, so a
# site's candidates span its whole history.
SE_SAMPLE = 20
# A candidate is a near-duplicate of an existing text when their shingle
# Jaccard reaches NEAR_JACCARD, when NEAR_CONTAINMENT of the candidate's
# shingles are in that text, or when PASSAGE_CONTAINMENT of the shingles of an
# existing passage of at least PASSAGE_MIN_SHINGLES shingles are in the candidate.
NEAR_JACCARD = 0.5
NEAR_CONTAINMENT = 0.5
PASSAGE_CONTAINMENT = 0.8
PASSAGE_MIN_SHINGLES = 25
NEAR_KINDS = ("source", "generated", "item", "bank")
# Licences that allow private copying and analysis. A GitHub-detected licence
# outside this set rejects the repository's candidates.
OPEN_LICENCES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Python-2.0",
    "PSF-2.0",
    "PostgreSQL",
    "GPL-2.0",
    "GPL-2.0-only",
    "GPL-3.0",
    "GPL-3.0-or-later",
    "LGPL-2.1",
    "MPL-2.0",
    "CC-BY-4.0",
    "CC-BY-SA-3.0",
    "CC-BY-SA-4.0",
    "CC0-1.0",
    "Unlicense",
    "curl",
}
_UNIT_SUFFIXES = {".md", ".rst", ".txt", ".adoc", ".sgml"}
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)
# A brief missing a generated document gets up to this many fallback rounds.
FALLBACK_ROUNDS = 2
GENERATION_OUTPUT_TOKENS = 1200
BRIEF_OUTPUT_TOKENS = 1600
# Semantic regions per document; each region is asked every kept judgement rule.
REGIONS = 3
# label_origin of blind rows. The eval container needs a label to run an item;
# these placeholders are never scored (judge-sagemaker pilot/metrics.py).
UNLABELLED = "blind-unlabelled"
PLACEHOLDER_LABEL = {"choice": "no-defect", "noul": False}
CALIBRATION_BUILD = "corpus-20261003-s17-v5b"
CALIBRATION_VARIANT = "full"
USW2_BUCKET = "slopvac-judge-536697262379-usw2"


def blind_root(root: Path) -> Path:
    return root / BLIND


def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe(value: str) -> str:
    return value.replace("/", "_")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ---------- admission ----------


def _corpus_pointers(root: Path) -> dict:
    """What the corpus already used: git files, RFCs, Stack Exchange posts and
    Wikipedia pages of sources/human.jsonl, and of every unit an earlier build
    cached under .cache/sources/, plus the source text digests."""
    used = {"git": set(), "rfc": set(), "se": set(), "wiki": set()}
    commits: dict[str, str] = {}
    shas: set[str] = set()
    families: Counter = Counter()
    for row in read_jsonl(root / "sources" / "human.jsonl"):
        loc = row["immutable_locator"]
        shas.add(row["sha256"])
        families[row["source_family"]] += 1
        if "repository" in loc:
            used["git"].add((loc["repository"], loc["path"]))
            commits[row["source_family"]] = loc["commit"]
        elif "rfc" in loc:
            used["rfc"].add(int(loc["rfc"]))
        elif "post_id" in loc:
            used["se"].add((loc["site"], int(loc["post_id"])))
        elif "oldid" in loc:
            used["wiki"].add(int(row["id"].split("-")[1]))
    for path in (root / ".cache" / "sources").glob("*.txt"):
        stem = path.stem
        if m := re.fullmatch(r"rfc-(\d+)-[0-9a-f]+", stem):
            used["rfc"].add(int(m.group(1)))
        elif m := re.fullmatch(r"wiki-(\d+)-\d+-[0-9a-f]+", stem):
            used["wiki"].add(int(m.group(1)))
        elif m := re.fullmatch(r"se-(.+)-(\d+)", stem):
            used["se"].add((m.group(1).replace("-", "."), int(m.group(2))))
    return {"used": used, "commits": commits, "sha256": shas, "families": families}


def _github_token() -> None:
    if os.environ.get("GITHUB_TOKEN"):
        return
    token = subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=False
    ).stdout.strip()
    if token:
        os.environ["GITHUB_TOKEN"] = token


def _owner(repo: str, path: str) -> str | None:
    """The family a git path belongs to: of the repository's entries whose
    patterns match it, the one with the longest matching pattern. A release
    note under the docs tree belongs to the release-notes family."""
    best, length = None, -1
    for entry_repo, _, _, family, patterns, _ in REPOSITORIES:
        if entry_repo != repo:
            continue
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern) and len(pattern) > length:
                best, length = family, len(pattern)
    return best


def _git_pool(root: Path, pointers: dict, retrieved_at: str) -> list[dict]:
    entries = [e for e in REPOSITORIES if e[3] in pointers["commits"]]
    per_genre = Counter(e[2] for e in entries)
    pool = []
    for repo, _ref, genre, family, patterns, licence in entries:
        sha = pointers["commits"][family]
        # A floor, because some families have little unused material left.
        size = max(
            GIT_POOL_FLOOR,
            POOL_FACTOR * -(-GROUP_QUOTAS[genre]["git"] // per_genre[genre]),
        )
        checkout, tree = _git_snapshot(root, repo, sha, patterns)
        paths = sorted(
            (
                p
                for p in (item["path"] for item in tree)
                if Path(p).suffix.lower() in _UNIT_SUFFIXES
                and any(fnmatch.fnmatch(p, pattern) for pattern in patterns)
                and not any(
                    part in p
                    for part in ("node_modules", ".github", "_build", "target")
                )
                and (repo, p) not in pointers["used"]["git"]
                and _owner(repo, p) == family
            ),
            key=lambda p: (seed(f"blind:file:{repo}:{p}"), p),
        )
        taken = 0
        for path in paths:
            try:
                raw = (checkout / path).read_bytes()
            except OSError:
                continue
            text = _strip_markup(raw.decode("utf-8", "replace"), path)
            min_words = MIN_WORDS.get(genre, DEFAULT_MIN_WORDS)
            units = list(_sections(text, min_words=min_words)) or _document_chunks(
                text, min_words=min_words
            )
            if not units:
                continue
            section, body = units[seed(f"blind:unit:{repo}:{path}") % len(units)]
            if sha256_text(body) in pointers["sha256"]:
                continue
            source_id = f"blind-gh-{repo.replace('/', '-')}-{sha[:12]}-{sha256_text(path + section)[:12]}"
            row = {
                "id": source_id,
                "genre": genre,
                "source_family": family,
                "url": f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path, safe='/')}",
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
            }
            pool.append(
                {
                    "row": row,
                    "text": body,
                    "group": "git",
                    "queue": family,
                    "git": (repo, sha, path),
                }
            )
            taken += 1
            if taken >= size:
                break
    return pool


def _rfc_pool(pointers: dict, retrieved_at: str, size: int) -> list[dict]:
    index = _request(RFC_INDEX).decode("utf-8", "replace")
    blocks = re.findall(r"(?ms)^\s*(\d+)\s+(.+?)(?=^\s*\d+\s+|\Z)", index)
    candidates = []
    for number, block in blocks:
        publication = re.search(rf"\b({_MONTHS})\s+(\d{{4}})\.", block)
        if not publication or int(publication.group(2)) >= 2022:
            continue
        if int(number) in pointers["used"]["rfc"]:
            continue
        candidates.append((int(number), publication.group(1), publication.group(2)))
    candidates.sort(key=lambda c: (seed(f"blind:rfc:{c[0]}"), c[0]))
    pool = []
    for number, month, year in candidates:
        url = RFC_BASE.format(number=number)
        try:
            raw = _request(url).decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError):
            continue
        text = normalise(raw)
        units = list(_sections(text)) or _document_chunks(text)
        if not units:
            continue
        section, body = units[seed(f"blind:unit:rfc:{number}") % len(units)]
        if sha256_text(body) in pointers["sha256"]:
            continue
        source_id = f"blind-rfc-{number}-{sha256_text(section)[:10]}"
        revision = datetime.strptime(f"{month} {year}", "%B %Y").strftime("%Y-%m")
        row = {
            "id": source_id,
            "genre": "reference",
            "source_family": "rfc-editor",
            "url": url,
            "immutable_locator": {
                "rfc": number,
                "publication": f"{month} {year}",
                "section": section,
                "bulk_index": RFC_INDEX,
            },
            "licence": "IETF Trust Legal Provisions (RFC Editor)",
            "licence_check": {"method": "publisher terms", "basis": "RFC Editor"},
            "redistribution_consent": "private S3 use under RFC Editor terms",
            "revision_date": revision,
            "retrieved_at": retrieved_at,
            "word_count": len(body.split()),
            "sha256": sha256_text(body),
        }
        pool.append(
            {"row": row, "text": body, "group": "rfc-editor", "queue": "rfc-editor"}
        )
        if len(pool) >= size:
            break
        time.sleep(0.2)
    return pool


def _se_licence(date: str) -> str:
    """Stack Exchange's content licence at the date a post was last edited."""
    if date < "2011-04-08":
        return "CC BY-SA 2.5"
    if date < "2018-05-02":
        return "CC BY-SA 3.0"
    return "CC BY-SA 4.0"


def _se_pool(
    root: Path, pointers: dict, retrieved_at: str, per_site: int
) -> list[dict]:
    pool = []
    for site in STACKEXCHANGE_SITES:
        archive = root / ".cache" / "stackexchange" / f"{site}.7z"
        process = subprocess.Popen(
            ["bsdtar", "-xOf", str(archive), "Posts.xml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        site_rows = []
        try:
            assert process.stdout is not None
            for _, element in ET.iterparse(process.stdout, events=("end",)):
                if element.tag != "row":
                    continue
                attrs = element.attrib
                post_id = attrs.get("Id", "")
                if (
                    attrs.get("PostTypeId") != "1"
                    or (site, int(post_id)) in pointers["used"]["se"]
                    or seed(f"blind:se:{site}:{post_id}") % SE_SAMPLE
                    or attrs.get("CreationDate", "") >= BLIND_CUTOFF
                ):
                    element.clear()
                    continue
                title = unescape(attrs.get("Title", ""))
                body = unescape(attrs.get("Body", ""))
                text = normalise(re.sub(r"<[^>]+>", " ", f"{title}\n{body}"))
                element.clear()
                if len(text.split()) < 100:
                    continue
                created = attrs.get("CreationDate", "")
                edited = attrs.get("LastEditDate") or created
                revision = max(created, edited)
                source_id = f"blind-se-{site.replace('.', '-')}-{post_id}"
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
                        "last_edit_date": edited,
                        "archive_file": f"{site}.7z",
                    },
                    "licence": f"{_se_licence(revision)} (Stack Exchange data dump)",
                    "licence_check": {
                        "method": "Stack Exchange licence by last edit date",
                        "basis": revision,
                    },
                    "redistribution_consent": "private S3 use with attribution and share-alike",
                    "revision_date": revision,
                    "retrieved_at": retrieved_at,
                    "word_count": len(text.split()),
                    "sha256": sha256_text(text),
                }
                if row["sha256"] not in pointers["sha256"]:
                    site_rows.append(
                        {
                            "row": row,
                            "text": text,
                            "group": "stackexchange-archive",
                            "queue": site,
                        }
                    )
        finally:
            if process.stdout:
                process.stdout.close()
            if process.wait() != 0:
                error = (
                    process.stderr.read().decode("utf-8", "replace")
                    if process.stderr
                    else ""
                )
                raise RuntimeError(f"bsdtar failed for {site}: {error.strip()}")
        site_rows.sort(
            key=lambda c: (seed(f"blind:se-order:{c['row']['id']}"), c["row"]["id"])
        )
        pool.extend(site_rows[:per_site])
    return pool


def _wiki_pool(pointers: dict, retrieved_at: str, size: int) -> list[dict]:
    pool: list[dict] = []
    seen = set(pointers["used"]["wiki"])
    while len(pool) < size:
        params = {
            "action": "query",
            "generator": "random",
            "grnnamespace": "0",
            "grnfilterredir": "nonredirects",
            "grnlimit": "50",
            "prop": "info",
            "format": "json",
            "formatversion": "2",
            "maxlag": "5",
        }
        pages = (
            fetch_json(WIKI_API + "?" + urllib.parse.urlencode(params))
            .get("query", {})
            .get("pages", [])
        )
        for page in pages:
            if len(pool) >= size:
                break
            if page["pageid"] in seen or page.get("length", 0) < 12000:
                continue
            seen.add(page["pageid"])
            query = {
                "action": "query",
                "prop": "revisions",
                "pageids": str(page["pageid"]),
                "rvstart": WIKI_RVSTART,
                "rvdir": "older",
                "rvlimit": "1",
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
                "format": "json",
                "formatversion": "2",
                "maxlag": "5",
            }
            time.sleep(1.0)
            payload = fetch_json(WIKI_API + "?" + urllib.parse.urlencode(query))
            found = (payload.get("query", {}).get("pages") or [{}])[0]
            revs = found.get("revisions", [])
            if not revs:
                continue
            rev = revs[0]
            content = rev.get("slots", {}).get("main", {}).get("content") or ""
            text = _wiki_plaintext(content)
            units = list(
                _sections(text, min_words=300, max_words=2500)
            ) or _document_chunks(text)
            if not units:
                continue
            section, body = units[
                seed(f"blind:unit:wiki:{page['pageid']}") % len(units)
            ]
            source_id = f"blind-wiki-{page['pageid']}-{rev['revid']}-{sha256_text(section)[:10]}"
            row = {
                "id": source_id,
                "genre": "informal",
                "source_family": "wikipedia",
                "url": f"https://en.wikipedia.org/w/index.php?oldid={rev['revid']}",
                "immutable_locator": {
                    "page": found["title"],
                    "pageid": page["pageid"],
                    "oldid": rev["revid"],
                    "section": section,
                },
                "licence": "CC BY-SA 3.0 (Wikipedia text)",
                "licence_check": {
                    "method": "Wikipedia text licence",
                    "basis": rev.get("timestamp"),
                },
                "redistribution_consent": "private S3 use permitted with attribution and share-alike",
                "revision_date": rev.get("timestamp", ""),
                "retrieved_at": retrieved_at,
                "word_count": len(body.split()),
                "sha256": sha256_text(body),
            }
            if row["sha256"] not in pointers["sha256"]:
                pool.append(
                    {
                        "row": row,
                        "text": body,
                        "group": "wikipedia",
                        "queue": "wikipedia",
                    }
                )
        time.sleep(1.0)
    return pool


def _signature(text: str) -> set[int]:
    return {hash(s) for s in shingles(text)}


def _existing_texts(root: Path):
    """(kind, name, text) for every text the judges could have trained on:
    cached corpus source units of every build, generated documents, bank
    passages (current and v3), and item texts of every build."""
    for path in sorted((root / ".cache" / "sources").glob("*.txt")):
        yield "source", path.stem, path.read_text(encoding="utf-8", errors="replace")
    for path in sorted((root / ".cache" / "generated").rglob("*.txt")):
        yield (
            "generated",
            str(path.relative_to(root / ".cache" / "generated")),
            path.read_text(encoding="utf-8", errors="replace"),
        )
    for bank in (root / BANK_PATH, root / ".cache/v3-snapshot/bank/bank.jsonl"):
        for row in read_jsonl(bank):
            yield "bank", row["id"], row.get("text") or ""
    for path in (root / ".cache" / "items").glob("*.txt"):
        yield "item", path.stem, path.read_text(encoding="utf-8", errors="replace")


def near_duplicate_scores(root: Path, texts: list[str]) -> tuple[list[dict], Counter]:
    """For each text, the highest Jaccard, containment and passage scores
    against every existing corpus text, per kind, with the first match that
    crosses a near-duplicate threshold."""
    sigs = [_signature(t) for t in texts]
    index: dict[int, list[int]] = defaultdict(list)
    for i, sig in enumerate(sigs):
        for h in sig:
            index[h].append(i)
    best: list[dict] = [{} for _ in texts]
    scanned: Counter = Counter()
    for kind, name, text in _existing_texts(root):
        scanned[kind] += 1
        sig = _signature(text)
        if not sig:
            continue
        overlap: Counter = Counter()
        for h in sig:
            for i in index.get(h, ()):
                overlap[i] += 1
        for i, o in overlap.items():
            j = o / (len(sigs[i]) + len(sig) - o)
            c = o / len(sigs[i])
            p = o / len(sig) if len(sig) >= PASSAGE_MIN_SHINGLES else 0.0
            s = best[i].setdefault(
                kind,
                {"jaccard": 0.0, "containment": 0.0, "passage": 0.0, "match": None},
            )
            s["jaccard"] = max(s["jaccard"], round(j, 4))
            s["containment"] = max(s["containment"], round(c, 4))
            s["passage"] = max(s["passage"], round(p, 4))
            if s["match"] is None and (
                j >= NEAR_JACCARD or c >= NEAR_CONTAINMENT or p >= PASSAGE_CONTAINMENT
            ):
                s["match"] = name
    return best, scanned


def _near_reason(scores: dict) -> str | None:
    for kind in NEAR_KINDS:
        if (scores.get(kind) or {}).get("match"):
            return f"near-duplicate-{kind}"
    return None


@functools.cache
def _repo_licence(repo: str, sha: str) -> dict:
    try:
        data = fetch_json(_github_url(f"repos/{repo}/license?ref={sha}"))
    except urllib.error.HTTPError as exc:
        return {
            "method": "github-license-api",
            "ref": sha,
            "status": exc.code,
            "spdx": None,
        }
    return {
        "method": "github-license-api",
        "ref": sha,
        "path": data.get("path"),
        "spdx": (data.get("license") or {}).get("spdx_id"),
    }


@functools.cache
def _git_revision(repo: str, sha: str, path: str) -> str:
    """Committer date of the last commit at or before `sha` that touched `path`."""
    query = urllib.parse.urlencode({"sha": sha, "path": path, "per_page": "1"})
    data = json.loads(_request(_github_url(f"repos/{repo}/commits?{query}"), api=True))
    return data[0]["commit"]["committer"]["date"] if data else ""


def _licence_verdict(candidate: dict) -> str | None:
    row = candidate["row"]
    if "git" not in candidate:
        return None
    repo, sha, _ = candidate["git"]
    check = _repo_licence(repo, sha)
    recorded = set(re.split(r"\s+OR\s+|\s+AND\s+", row["licence"]))
    detected = check.get("spdx")
    if detected and detected != "NOASSERTION":
        if detected not in OPEN_LICENCES:
            row["licence_check"] = {**check, "verdict": "not an open licence"}
            return "licence-not-open"
        verdict = (
            "matches recorded" if detected in recorded else "detected licence used"
        )
        if detected not in recorded:
            row["licence"] = detected
    else:
        if not recorded <= OPEN_LICENCES:
            row["licence_check"] = {**check, "verdict": "unverified"}
            return "licence-unverified"
        verdict = "no SPDX detected; recorded table licence used"
    row["licence_check"] = {**check, "recorded": sorted(recorded), "verdict": verdict}
    return None


def _revision_verdict(candidate: dict) -> str | None:
    row = candidate["row"]
    if "git" in candidate:
        repo, sha, path = candidate["git"]
        row["revision_date"] = _git_revision(repo, sha, path)
        row["immutable_locator"]["file_last_commit_date"] = row["revision_date"]
        if not row["revision_date"]:
            return "revision-unknown"
    return "revised-after-cutoff" if row["revision_date"] >= BLIND_CUTOFF else None


def _select(pool: list[dict]) -> tuple[list[dict], list[dict], Counter]:
    queues: dict[tuple[str, str], dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for c in pool:
        queues[(c["row"]["genre"], c["group"])][c["queue"]].append(c)
    accepted: list[dict] = []
    decisions: list[dict] = []
    unused: Counter = Counter()
    for genre, groups in GROUP_QUOTAS.items():
        for group, quota in groups.items():
            qs = queues.get((genre, group), {})
            names = sorted(qs)
            taken = 0
            while taken < quota and any(qs[n] for n in names):
                for name in names:
                    if taken >= quota:
                        break
                    q = qs[name]
                    while q:
                        c = q.pop(0)
                        reason = _near_reason(c["scores"])
                        if reason is None:
                            for prior in accepted:
                                o = len(c["sig"] & prior["sig"])
                                if (
                                    o / max(1, len(c["sig"] | prior["sig"]))
                                    >= NEAR_JACCARD
                                    or o / max(1, len(c["sig"])) >= NEAR_CONTAINMENT
                                    or o / max(1, len(prior["sig"])) >= NEAR_CONTAINMENT
                                ):
                                    reason = "near-duplicate-blind"
                                    c["scores"]["blind"] = {"match": prior["row"]["id"]}
                                    break
                        if reason is None:
                            reason = _revision_verdict(c)
                        if reason is None:
                            reason = _licence_verdict(c)
                        decisions.append(
                            {
                                "id": c["row"]["id"],
                                "genre": genre,
                                "source_family": c["row"]["source_family"],
                                "queue": name,
                                "decision": "accepted"
                                if reason is None
                                else "rejected",
                                "reason": reason,
                                "revision_date": c["row"].get("revision_date"),
                                "scores": c["scores"],
                            }
                        )
                        if reason is None:
                            accepted.append(c)
                            taken += 1
                            break
            for name in names:
                unused[f"{genre}/{name}"] += len(qs[name])
    return accepted, decisions, unused


def admit_sources(root: Path) -> dict:
    """Admit the blind human set; write .cache/blind/sources/ and upload text."""
    _github_token()
    blind = blind_root(root)
    retrieved_at = _now()
    pointers = _corpus_pointers(root)
    pool = _git_pool(root, pointers, retrieved_at)
    pool += _rfc_pool(
        pointers, retrieved_at, POOL_FACTOR * GROUP_QUOTAS["reference"]["rfc-editor"]
    )
    per_site = POOL_FACTOR * -(
        -GROUP_QUOTAS["informal"]["stackexchange-archive"] // len(STACKEXCHANGE_SITES)
    )
    pool += _se_pool(root, pointers, retrieved_at, per_site)
    pool += _wiki_pool(
        pointers, retrieved_at, POOL_FACTOR * GROUP_QUOTAS["informal"]["wikipedia"]
    )
    scores, scanned = near_duplicate_scores(root, [c["text"] for c in pool])
    for c, s in zip(pool, scores):
        c["scores"], c["sig"] = s, _signature(c["text"])
    accepted, decisions, unused = _select(pool)
    rows = []
    for c in accepted:
        row = c["row"]
        rel = Path("text/human") / f"{row['id']}.txt"
        (blind / rel).parent.mkdir(parents=True, exist_ok=True)
        (blind / rel).write_text(c["text"], encoding="utf-8")
        row["cache_path"] = str(rel)
        row["s3_key"] = f"{S3_PREFIX}/human/{row['id']}.txt"
        upload_text(root, c["text"], row["s3_key"])
        rows.append(row)
    write_jsonl(blind / "sources" / "human.jsonl", rows)
    write_jsonl(blind / "sources" / "decisions.jsonl", decisions)
    summary = {
        "built_at": retrieved_at,
        "cutoff": BLIND_CUTOFF,
        "pool": len(pool),
        "pool_by_family": dict(Counter(c["row"]["source_family"] for c in pool)),
        "min_words": {g: MIN_WORDS.get(g, DEFAULT_MIN_WORDS) for g in GROUP_QUOTAS},
        "accepted": len(rows),
        "accepted_by_genre": dict(Counter(r["genre"] for r in rows)),
        "accepted_by_family": dict(Counter(r["source_family"] for r in rows)),
        "rejected": sum(d["decision"] == "rejected" for d in decisions),
        "rejected_by_reason": dict(
            Counter(d["reason"] for d in decisions if d["reason"])
        ),
        "rejected_by_family_reason": dict(
            Counter(
                f"{d['source_family']}: {d['reason']}" for d in decisions if d["reason"]
            )
        ),
        "pool_not_needed": dict(unused),
        "excluded_corpus_locators": {k: len(v) for k, v in pointers["used"].items()},
        "near_duplicate_scan": dict(scanned),
        "thresholds": {
            "jaccard": NEAR_JACCARD,
            "containment": NEAR_CONTAINMENT,
            "passage_containment": PASSAGE_CONTAINMENT,
            "passage_min_shingles": PASSAGE_MIN_SHINGLES,
            "shingle_words": 5,
        },
    }
    _write_json(blind / "sources" / "admission.json", summary)
    return summary


# ---------- briefs and generation ----------


def _corpus_brief_model(root: Path) -> str:
    models = Counter(
        row["model"] for row in read_jsonl(root / "briefs" / "manifest.jsonl")
    )
    return models.most_common(1)[0][0]


def _latest(lines) -> dict[str, dict]:
    """One output line per record id; a successful line wins over an error."""
    out: dict[str, dict] = {}
    for line in lines:
        rid = line.get("recordId")
        if rid not in out or "modelOutput" in line:
            out[rid] = line
    return out


def run_briefs(root: Path, *, max_usd: float) -> dict:
    blind = blind_root(root)
    model = _corpus_brief_model(root)
    input_path, _, _ = prepare_briefs(blind, limit=None, model_id=model)
    raw = blind / "briefs" / "raw-output.jsonl"
    jobs = [
        run_ondemand(
            root,
            input_path,
            model,
            raw,
            stage="blind-briefs",
            expected_output_tokens=BRIEF_OUTPUT_TOKENS,
            max_usd=max_usd,
        )
    ]
    lines = _latest(read_jsonl(raw))
    accepted, rejected = collect_briefs(blind, lines.values(), model_id=model)
    if rejected:
        # One retry for invalid or leaking briefs, as the corpus build does.
        retry_ids = {r["source_id"] for r in rejected}
        retry_input = blind / "briefs" / "retry-input.jsonl"
        write_jsonl(
            retry_input,
            [r for r in read_jsonl(input_path) if r["recordId"] in retry_ids],
        )
        retry_raw = blind / "briefs" / "retry-output.jsonl"
        jobs.append(
            run_ondemand(
                root,
                retry_input,
                model,
                retry_raw,
                stage="blind-briefs-retry",
                expected_output_tokens=BRIEF_OUTPUT_TOKENS,
                max_usd=max_usd,
            )
        )
        for rid, line in _latest(read_jsonl(retry_raw)).items():
            if "modelOutput" in line:
                lines[rid] = line
        accepted, rejected = collect_briefs(blind, lines.values(), model_id=model)
    for brief in accepted:
        upload_text(
            root,
            json.dumps(brief["brief"], ensure_ascii=False, sort_keys=True),
            f"{S3_PREFIX}/briefs/{brief['id']}.json",
        )
    summary = {
        "model": model,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "rejected_by_reason": dict(Counter(r["reason"] for r in rejected)),
        "jobs": jobs,
    }
    _write_json(blind / "briefs" / "summary.json", summary)
    return summary


def _rotation(root: Path) -> list[dict]:
    """The corpus generation rotation (models/roster.json order, priced and
    batch-verified) without the models generated/routes.json marks skipped."""
    roster = json.loads((root / "models" / "roster.json").read_text())
    routes = json.loads((root / "generated" / "routes.json").read_text())
    return [
        m
        for m in roster["models"]
        if m.get("batch_supported")
        and m.get("pricing_usd_per_million_on_demand")
        and (routes.get(m["model_id"]) or {}).get("state") != "skipped"
    ]


def _max_tokens(brief: dict) -> int:
    try:
        target_words = int(brief.get("target_length_words") or 800)
    except (TypeError, ValueError):
        target_words = 800
    return min(4000, max(600, int(target_words * 1.6)))


def _run_models(root: Path, inputs: dict[str, Path], stage: str, parallel: int) -> dict:
    blind = blind_root(root)

    def one(model: str) -> dict:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
        out = blind / "generated" / "raw" / f"{safe}.jsonl"
        for attempt in range(3):
            try:
                return run_ondemand(
                    root,
                    inputs[model],
                    model,
                    out,
                    stage=f"{stage}-{model.rsplit('/', 1)[-1]}",
                    concurrency=8,
                    expected_output_tokens=GENERATION_OUTPUT_TOKENS,
                )
            except json.JSONDecodeError:
                # The shared ledger was being rewritten by a sibling run.
                time.sleep(2 + attempt)
        raise RuntimeError(f"{model}: ledger unreadable")

    with ThreadPoolExecutor(parallel) as pool:
        return dict(zip(inputs, pool.map(one, inputs)))


def _estimate(inputs: dict[str, Path]) -> float:
    total = 0.0
    for model, path in inputs.items():
        records = list(read_jsonl(path))
        price_in, price_out = pricing_for(model) or (0.0, 0.0)
        tokens = sum(token_estimate(json.dumps(r["modelInput"])) for r in records)
        total += (
            tokens * price_in + len(records) * GENERATION_OUTPUT_TOKENS * price_out
        ) / 1e6
    return total


def run_generation(root: Path, *, max_usd: float, parallel: int = 6) -> dict:
    blind = blind_root(root)
    models = _rotation(root)
    _write_json(
        blind / "models" / "roster.json",
        {
            "source": "models/roster.json without the models generated/routes.json marks skipped",
            "models": models,
        },
    )
    prepared = prepare_generation(blind, limit=None)
    inputs = {
        m: p for m, (p, _, _) in prepared.items() if any(True for _ in read_jsonl(p))
    }
    estimate = _estimate(inputs)
    if estimate > max_usd:
        raise RuntimeError(
            f"generation estimate ${estimate:.2f} exceeds ${max_usd:.2f}"
        )
    briefs = list(read_jsonl(blind / "briefs" / "manifest.jsonl"))
    payloads = {
        b["id"]: json.loads((blind / b["brief_cache_path"]).read_text(encoding="utf-8"))
        for b in briefs
    }
    order = [m["model_id"] for m in models]
    by_id = {m["model_id"]: m for m in models}
    tried: dict[str, list[str]] = defaultdict(list)
    for a in read_jsonl(blind / "generated" / "assignments.jsonl"):
        tried[a["brief_id"]].append(a["model"])
    jobs: list[dict] = []
    accepted_all: list[dict] = []
    rejected_all: list[dict] = []
    texts: dict[str, str] = {}
    dead: set[str] = set()
    for round_no in range(FALLBACK_ROUNDS + 1):
        ran = _run_models(root, inputs, f"blind-generation-r{round_no}", parallel)
        jobs.extend({**job, "round": round_no} for job in ran.values())
        for model, path in inputs.items():
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
            wanted = {r["recordId"] for r in read_jsonl(path)}
            lines = [
                line
                for rid, line in _latest(
                    read_jsonl(blind / "generated" / "raw" / f"{safe}.jsonl")
                ).items()
                if rid in wanted
            ]
            accepted, rejected = collect_generated(blind, lines, model_id=model)
            for line in lines:
                if line["recordId"] in {a["id"] for a in accepted}:
                    texts[line["recordId"]] = parse_output(line)
            accepted_all.extend(
                {**a, "model": model, "round": round_no} for a in accepted
            )
            rejected_all.extend({**r, "round": round_no} for r in rejected)
            if (
                not accepted
                and rejected
                and all(r["reason"] == "empty_or_failed_output" for r in rejected)
            ):
                dead.add(model)
        have: dict[str, list[str]] = defaultdict(list)
        for a in accepted_all:
            have[a["brief_id"]].append(a["model"])
        missing = [b for b in briefs if len(have[b["id"]]) < 2]
        if not missing or round_no == FALLBACK_ROUNDS:
            break
        fallback: dict[str, list[dict]] = defaultdict(list)
        assignments = list(read_jsonl(blind / "generated" / "assignments.jsonl"))
        for brief in missing:
            vendors = {by_id[m]["vendor"] for m in have[brief["id"]]}
            start = order.index(tried[brief["id"]][-1])
            for step in range(1, len(order)):
                model = order[(start + step) % len(order)]
                if (
                    model in tried[brief["id"]]
                    or model in dead
                    or by_id[model]["vendor"] in vendors
                ):
                    continue
                break
            else:
                continue
            tried[brief["id"]].append(model)
            record_id = f"gen-{brief['source_id']}-{model.replace(':', '_')}"
            payload = payloads[brief["id"]]
            fallback[model].append(
                {
                    "recordId": record_id,
                    "modelInput": model_body(
                        model,
                        generation_prompt(payload),
                        max_tokens=_max_tokens(payload),
                    ),
                }
            )
            assignments.append(
                {
                    "recordId": record_id,
                    "brief_id": brief["id"],
                    "source_id": brief["source_id"],
                    "model": model,
                    "vendor": by_id[model]["vendor"],
                    "tier": by_id[model]["tier"],
                    "fallback_round": round_no + 1,
                }
            )
        if not fallback:
            break
        write_jsonl(blind / "generated" / "assignments.jsonl", assignments)
        inputs = {}
        for model, records in fallback.items():
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
            path = (
                blind / "generated" / "inputs" / f"fallback-{round_no + 1}-{safe}.jsonl"
            )
            write_jsonl(path, records)
            inputs[model] = path
    # The corpus leak filter compares a document with its own source only. A
    # blind document must also not near-duplicate anything the judges saw.
    ids = sorted(texts)
    scores, _ = near_duplicate_scores(root, [texts[i] for i in ids])
    near = {i: (s, _near_reason(s)) for i, s in zip(ids, scores)}
    manifest = []
    for row in accepted_all:
        s, reason = near[row["id"]]
        if reason:
            rejected_all.append(
                {
                    "record_id": row["id"],
                    "source_id": row["source_id"],
                    "model": row["model"],
                    "reason": reason,
                    "scores": s,
                    "round": row["round"],
                }
            )
            continue
        rel = Path("text/generated") / f"{_safe(row['id'])}.txt"
        (blind / rel).parent.mkdir(parents=True, exist_ok=True)
        (blind / rel).write_text(texts[row["id"]], encoding="utf-8")
        row = {
            **row,
            "text_path": str(rel),
            "s3_key": f"{S3_PREFIX}/generated/{_safe(row['id'])}.txt",
            "word_count": len(texts[row["id"]].split()),
            "near_duplicate_scores": s,
        }
        upload_text(root, texts[row["id"]], row["s3_key"])
        manifest.append(row)
    write_jsonl(blind / "generated" / "blind-manifest.jsonl", manifest)
    write_jsonl(blind / "generated" / "blind-rejections.jsonl", rejected_all)
    per_brief = Counter(Counter(r["brief_id"] for r in manifest).values())
    spend = round(sum(float(j.get("estimate_usd", 0.0)) for j in jobs), 4)
    summary = {
        "pre_run_estimate_usd": round(estimate, 4),
        "spend_usd": spend,
        "models": sorted({r["model"] for r in manifest}),
        "accepted": len(manifest),
        "accepted_by_vendor_tier": dict(
            Counter(f"{r['vendor']}/{r['tier']}" for r in manifest)
        ),
        "rejected_by_reason": dict(Counter(r["reason"] for r in rejected_all)),
        "dead_models": sorted(dead),
        "briefs_by_documents": {str(k): v for k, v in sorted(per_brief.items())},
        "briefs_without_documents": sum(
            1 for b in briefs if b["id"] not in {r["brief_id"] for r in manifest}
        ),
        "jobs": jobs,
    }
    _write_json(blind / "generated" / "summary.json", summary)
    write_docs(root)
    return summary


def write_docs(root: Path) -> list[dict]:
    """.cache/blind/docs.jsonl: one row per blind document, human and generated."""
    blind = blind_root(root)
    humans = list(read_jsonl(blind / "sources" / "human.jsonl"))
    briefs = {
        b["source_id"]: b["id"] for b in read_jsonl(blind / "briefs" / "manifest.jsonl")
    }
    by_source = {h["id"]: h for h in humans}
    docs = [
        {
            "doc_id": h["id"],
            "provenance": "human",
            "genre": h["genre"],
            "source_family": h["source_family"],
            "source_id": h["id"],
            "brief_id": briefs.get(h["id"]),
            "model": None,
            "vendor": None,
            "tier": None,
            "text_path": h["cache_path"],
            "sha256": h["sha256"],
            "word_count": h["word_count"],
        }
        for h in humans
    ]
    for g in read_jsonl(blind / "generated" / "blind-manifest.jsonl"):
        docs.append(
            {
                "doc_id": g["id"],
                "provenance": "generated",
                "genre": g["genre"],
                "source_family": by_source[g["source_id"]]["source_family"],
                "source_id": g["source_id"],
                "brief_id": g["brief_id"],
                "model": g["model"],
                "vendor": g["vendor"],
                "tier": g["tier"],
                "text_path": g["text_path"],
                "sha256": g["sha256"],
                "word_count": g["word_count"],
            }
        )
    write_jsonl(blind / "docs.jsonl", docs)
    return docs


# ---------- items ----------


def _smoke_docs(docs: list[dict], humans: int, generated: int) -> list[dict]:
    """`humans` human documents with two generated matches each (seeded order),
    and those matches, up to `generated`."""
    gen_by_source: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        if d["provenance"] == "generated":
            gen_by_source[d["source_id"]].append(d)
    complete = sorted(
        (
            d
            for d in docs
            if d["provenance"] == "human" and len(gen_by_source[d["doc_id"]]) >= 2
        ),
        key=lambda d: (seed(f"blind:smoke:{d['doc_id']}"), d["doc_id"]),
    )
    chosen: list[dict] = []
    by_genre: dict[str, list[dict]] = defaultdict(list)
    for d in complete:
        by_genre[d["genre"]].append(d)
    while len(chosen) < humans and any(by_genre.values()):
        for genre in sorted(by_genre):
            if by_genre[genre] and len(chosen) < humans:
                chosen.append(by_genre[genre].pop(0))
    gens = [
        g
        for h in chosen
        for g in sorted(gen_by_source[h["doc_id"]], key=lambda g: g["doc_id"])
    ]
    return chosen + gens[:generated]


def _region_target(root: Path, rule_ids: set[str]) -> int:
    lengths = [
        len(r["text"])
        for r in read_jsonl(root / BANK_PATH)
        if r.get("kept")
        and r["role"] == "semantic-detection"
        and r["rule_id"] in rule_ids
    ]
    return int(statistics.median(lengths)) if lengths else 200


def _export_row(item: dict, doc: dict, held: bool) -> dict:
    question = item["question"]
    if question["type"] == "choice":
        kind = "choice"
        out_question = {
            "type": "choice",
            "instructions": _choice_instructions(question),
            "criteria": dict(CHOICE_CRITERIA),
        }
    else:
        kind = "noul"
        out_question = {"type": "noul", "instructions": _noul_instructions(question)}
    return {
        "id": item["id"],
        "kind": kind,
        "state": render_state(item["state"], question.get("region")),
        "label": PLACEHOLDER_LABEL[kind],
        "question": out_question,
        "split": "test",
        "role": item["role"],
        "rule_id": item["rule_id"],
        "rule_held_out": held,
        "granularity": item.get("granularity"),
        "genre": item.get("genre"),
        "label_origin": UNLABELLED,
        "label_confidence": None,
        "provenance": doc["provenance"],
        "doc_id": doc["doc_id"],
    }


GRANULARITIES = ("sentence", "paragraph", "document")


def _first_item(make, first: str, counts: Counter, role: str) -> dict | None:
    """The item at granularity `first`, else at the next granularity that
    fits. A long human paragraph often exceeds the 1,024-token span budget;
    without the fallback its findings would go unjudged, and only on the human
    side."""
    for g in (first, *(x for x in GRANULARITIES if x != first)):
        item = make(g)
        if item is not None:
            if g != first:
                counts[f"{role}_granularity_fallback"] += 1
            return item
    return None


def build_items(
    root: Path,
    *,
    build_id: str,
    smoke: tuple[int, int] | None = None,
    regions: int = REGIONS,
    workers: int = 4,
) -> dict:
    """Lint the blind documents and write .cache/blind/builds/<build_id>/."""
    blind = blind_root(root)
    out = blind / "builds" / build_id
    docs = list(read_jsonl(blind / "docs.jsonl"))
    if smoke:
        docs = _smoke_docs(docs, *smoke)
    texts = {
        d["doc_id"]: (blind / d["text_path"]).read_text(encoding="utf-8") for d in docs
    }
    lint_dir = out / "lint-input"
    lint_dir.mkdir(parents=True, exist_ok=True)
    files = []
    name_of = {}
    for d in docs:
        name = f"{digest(d['doc_id'].encode())[:24]}.md"
        (lint_dir / name).write_text(_lint_text(texts[d["doc_id"]]), encoding="utf-8")
        files.append((d["doc_id"], lint_dir / name))
        name_of[d["doc_id"]] = name
    found = _run_lint(files, workers=workers)
    lint_rules = _rules_current()
    by_lint = {r["id"]: r for r in lint_rules}
    held_lint = held_out(lint_rules)
    judge_rules, held_judge = semantic_rules()
    target = _region_target(root, {r["id"] for r in judge_rules})
    encoders, tokenizer_digests = load_tokenizers()
    items: list[dict] = []
    findings_out: list[dict] = []
    counts: Counter = Counter()
    for d in docs:
        doc_id, text = d["doc_id"], texts[d["doc_id"]]
        source = {
            "id": doc_id,
            "genre": d["genre"],
            "source_family": d["source_family"],
            "vendor": d["vendor"],
            "tier": d["tier"],
        }
        seen_ids: set[str] = set()
        for finding in found.get(name_of[doc_id], []):
            rule = by_lint.get(finding["rule_id"])
            record = {
                "doc_id": doc_id,
                "rule_id": finding["rule_id"],
                "line": finding.get("line"),
                "column": finding.get("column"),
                "item_id": None,
                "rule_held_out": finding["rule_id"] in held_lint,
            }
            if rule is None:
                counts["finding_rule_not_in_rules"] += 1
                findings_out.append({**record, "dropped": "rule-not-in-rules"})
                continue
            anchor = _offset(text, finding.get("line", 1), finding.get("column", 1))
            item = _first_item(
                lambda g: _make_item(
                    blind,
                    role="finding-confirmation",
                    rule=rule,
                    source=source,
                    text=text,
                    label=None,
                    origin=None,
                    split="test",
                    kind="finding",
                    anchor=anchor,
                    encoders=encoders,
                    source_group=doc_id,
                    finding=finding,
                    g=g,
                ),
                granularity(f"finding-confirmation:{doc_id}:{rule['id']}:{anchor}:"),
                counts,
                "finding",
            )
            if item is None:
                counts["finding_item_dropped"] += 1
                findings_out.append({**record, "dropped": "item-not-buildable"})
                continue
            findings_out.append({**record, "item_id": item["id"]})
            if item["id"] in seen_ids:
                counts["finding_item_duplicate"] += 1
                continue
            seen_ids.add(item["id"])
            item["rule_held_out"] = rule["id"] in held_lint
            items.append({**item, "doc_id": doc_id})
        prose = sorted(
            _prose_paragraphs(text),
            key=lambda p: (seed(f"blind:region:{doc_id}:{p[0]}"), p[0]),
        )
        made = 0
        for a, _, _ in prose:
            if made >= regions:
                break
            g = granularity(f"blind:{doc_id}:{made}")
            region_items = []
            region_of: dict[str, tuple[int, int] | None] = {}
            for rule in judge_rules:
                item = _first_item(
                    lambda gg: _make_item(
                        blind,
                        role="semantic-detection",
                        rule=rule,
                        source=source,
                        text=text,
                        label=None,
                        origin=None,
                        split="test",
                        kind=f"blind-region-{made}",
                        anchor=a,
                        encoders=encoders,
                        source_group=doc_id,
                        g=gg,
                    ),
                    g,
                    counts,
                    "semantic",
                )
                if item is None:
                    counts["semantic_item_dropped"] += 1
                    continue
                value = item["state"]["text"]
                if value not in region_of:
                    region_of[value] = _pick_region(
                        value, _relative_anchor(value, text, a), target
                    )
                if not _set_region(item, region_of[value]):
                    counts["semantic_region_failed"] += 1
                    continue
                item["rule_held_out"] = rule["id"] in held_judge
                region_items.append({**item, "doc_id": doc_id, "region_index": made})
            if region_items:
                items.extend(region_items)
                made += 1
            else:
                counts["region_skipped"] += 1
        counts["documents_with_regions"] += made > 0
        counts["regions"] += made
    doc_by_id = {d["doc_id"]: d for d in docs}
    rows = [
        _export_row(item, doc_by_id[item["doc_id"]], item["rule_held_out"])
        for item in items
    ]
    for d in docs:
        d["prose_words"] = prose_words(texts[d["doc_id"]])
        d["findings"] = len(found.get(name_of[d["doc_id"]], []))
    write_jsonl(out / "docs.jsonl", docs)
    write_jsonl(out / "findings.jsonl", findings_out)
    write_jsonl(out / "items.jsonl", items)
    write_jsonl(out / "test.jsonl", rows)
    test_bytes = (out / "test.jsonl").read_bytes()
    lint_commit = subprocess.run(
        ["git", "-C", str(CANONICAL), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    report = {
        "build_id": build_id,
        "built_at": _now(),
        "smoke": list(smoke) if smoke else None,
        "lint_root": str(CANONICAL),
        "lint_commit": lint_commit,
        "documents": dict(Counter(d["provenance"] for d in docs)),
        "findings": len(findings_out),
        "items": len(rows),
        "items_by_role": dict(Counter(r["role"] for r in rows)),
        "items_by_role_provenance": dict(
            Counter(f"{r['role']}/{r['provenance']}" for r in rows)
        ),
        "requests_per_arm": sum(2 if r["kind"] == "choice" else 1 for r in rows),
        "semantic_rules": len(judge_rules),
        "regions_per_document": regions,
        "region_target_chars": target,
        "counts": dict(counts),
        "tokenizers": tokenizer_digests,
        "test_sha256": digest(test_bytes),
        "test_records": len(rows),
        "placeholder_labels": PLACEHOLDER_LABEL,
        "label_origin": UNLABELLED,
    }
    _write_json(out / "build-manifest.json", report)
    return report


def publish_items(root: Path, build_id: str) -> dict:
    """Upload a build's test.jsonl and a container export manifest to
    s3://<corpus bucket>/blind/<build_id>/ and the us-west-2 bucket. The
    manifest is the calibration build's, with files.test pointing at the blind
    test file, so the container checks the blind digest and keeps the labelled
    calibration split for its temperature fit."""
    import boto3

    from .bedrock import PROFILE, clients

    blind = blind_root(root)
    out = blind / "builds" / build_id
    report = json.loads((out / "build-manifest.json").read_text())
    if report.get("smoke"):
        raise RuntimeError(
            f"{build_id} is a smoke build; build the full set to publish"
        )
    index = json.loads((root / "items" / "export-index.json").read_text())
    variant = index["builds"][CALIBRATION_BUILD]["variants"][CALIBRATION_VARIANT]
    manifest_uri = next(
        o["uri"]
        for o in variant["objects"]
        if o["path"].endswith("export-manifest.json")
    )
    bucket, key = manifest_uri.removeprefix("s3://").split("/", 1)
    s3, _, _ = clients()
    calibration_manifest = json.loads(
        s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    )
    manifest = {
        **{k: v for k, v in calibration_manifest.items() if k != "per_rule"},
        "variant": f"blind/{build_id}",
        "files": {
            **calibration_manifest["files"],
            "test": {
                "path": f"{S3_PREFIX}/{build_id}/test.jsonl",
                "records": report["test_records"],
                "sha256": report["test_sha256"],
            },
        },
        "blind": {
            "build_id": build_id,
            "label_origin": UNLABELLED,
            "calibration_from": f"{CALIBRATION_BUILD}/{CALIBRATION_VARIANT}",
            "items_by_role": report["items_by_role"],
        },
    }
    _write_json(out / "export-manifest.json", manifest)
    uris = {}
    usw2 = boto3.Session(profile_name=PROFILE, region_name="us-west-2").client("s3")
    for name in ("test.jsonl", "export-manifest.json"):
        key = f"{S3_PREFIX}/{build_id}/{name}"
        uris[f"us-east-1:{name}"] = upload(root, out / name, key)
        usw2.upload_file(
            str(out / name),
            USW2_BUCKET,
            key,
            ExtraArgs={"ServerSideEncryption": "AES256"},
        )
        uris[f"us-west-2:{name}"] = f"s3://{USW2_BUCKET}/{key}"
    for name in ("docs.jsonl", "findings.jsonl", "build-manifest.json"):
        uris[f"us-east-1:{name}"] = upload(
            root, out / name, f"{S3_PREFIX}/{build_id}/{name}"
        )
    report["published"] = uris
    report["export_manifest_sha256"] = digest(
        (out / "export-manifest.json").read_bytes()
    )
    _write_json(out / "build-manifest.json", report)
    _write_json(
        root / "blind" / f"campaign-{build_id}.json", _campaign(variant, report, uris)
    )
    return report


def _campaign(variant: dict, report: dict, uris: dict) -> dict:
    """An eval-only judge-sagemaker campaign: the v5b-full checkpoints and base
    arms on the blind test file, with the v5b calibration split."""
    east = {o["path"].rsplit("/", 1)[-1]: o["uri"] for o in variant["objects"]}
    east_bucket = east["train.jsonl"].removeprefix("s3://").split("/", 1)[0]

    def west(uri: str) -> str:
        return uri.replace(f"s3://{east_bucket}/", f"s3://{USW2_BUCKET}/")

    calibration_sha = next(
        o["sha256"]
        for o in variant["objects"]
        if o["path"].endswith("/calibration.jsonl")
    )
    # The slowest arm (kev-4b fine-tunes) answers about 11 requests/s; the
    # calibration split adds about 3,400 requests. The eval cap is 21,600 s.
    seconds = (report["requests_per_arm"] + 3400) / 10 + 900
    runtime = min(21600, 1800 * -(-int(seconds) // 1800))
    return {
        "id": f"{CALIBRATION_BUILD}/blind-{report['build_id']}",
        "results": f"corpus-blind-{report['build_id']}",
        "checkpoints_from": f"{CALIBRATION_BUILD}/{CALIBRATION_VARIANT}",
        "train_models": ["kev-0.8b", "kev-4b", "kev-9b"],
        "base_arms": [
            "kev-0.8b",
            "kev-4b",
            "kev-9b",
            "laya-english",
            "laya-multilingual",
            "laya-typed-decisions",
        ],
        "eval_runtime": runtime,
        "data": {
            "us-east-1": {
                "train": east["train.jsonl"],
                "calibration": east["calibration.jsonl"],
                "test": uris["us-east-1:test.jsonl"],
                "manifest": uris["us-east-1:export-manifest.json"],
            },
            "us-west-2": {
                "train": west(east["train.jsonl"]),
                "calibration": west(east["calibration.jsonl"]),
                "test": uris["us-west-2:test.jsonl"],
                "manifest": uris["us-west-2:export-manifest.json"],
            },
        },
        "expected": {"test": report["test_sha256"], "calibration": calibration_sha},
        "notes": (
            f"Blind set {report['build_id']} (judge_corpus/blind.py): human documents the judges "
            "never trained on and LLM documents generated from their briefs. Test rows are "
            "unlabelled (label_origin blind-unlabelled, placeholder labels) and never scored; "
            "the v5b calibration split fits the temperature. Analyse the predictions with "
            "`judge-corpus blind report`."
        ),
    }


def write_manifest(root: Path, build_id: str | None = None) -> dict:
    """blind/manifest.json: pointers, digests and counts; never text."""
    blind = blind_root(root)
    humans = list(read_jsonl(blind / "sources" / "human.jsonl"))
    generated = list(read_jsonl(blind / "generated" / "blind-manifest.jsonl"))
    briefs = list(read_jsonl(blind / "briefs" / "manifest.jsonl"))
    admission = json.loads((blind / "sources" / "admission.json").read_text())
    brief_summary = json.loads((blind / "briefs" / "summary.json").read_text())
    gen_summary = json.loads((blind / "generated" / "summary.json").read_text())
    data = {
        "schema_version": 1,
        "description": "Blind human-versus-generated evaluation set (judge_corpus/blind.py). Pointers, digests and counts only; text is in .cache/blind/ and s3://<corpus bucket>/blind/.",
        "cutoff": BLIND_CUTOFF,
        "admission": {k: v for k, v in admission.items() if k != "built_at"},
        "briefs": {
            "model": brief_summary["model"],
            "accepted": brief_summary["accepted"],
            "rejected_by_reason": brief_summary["rejected_by_reason"],
            "digests": {b["source_id"]: b["digest"] for b in briefs},
        },
        "generation": {k: v for k, v in gen_summary.items() if k not in {"jobs"}},
        "human": [
            {
                "id": h["id"],
                "genre": h["genre"],
                "source_family": h["source_family"],
                "url": h["url"],
                "immutable_locator": h["immutable_locator"],
                "licence": h["licence"],
                "licence_check": h.get("licence_check"),
                "revision_date": h["revision_date"],
                "word_count": h["word_count"],
                "sha256": h["sha256"],
                "s3_key": h["s3_key"],
            }
            for h in humans
        ],
        "generated": [
            {
                "id": g["id"],
                "brief_id": g["brief_id"],
                "source_id": g["source_id"],
                "model": g["model"],
                "vendor": g["vendor"],
                "tier": g["tier"],
                "round": g["round"],
                "word_count": g["word_count"],
                "sha256": g["sha256"],
                "leak_score": g["leak_score"],
                "s3_key": g["s3_key"],
            }
            for g in generated
        ],
    }
    if build_id:
        build = json.loads(
            (blind / "builds" / build_id / "build-manifest.json").read_text()
        )
        data["items"] = {k: v for k, v in build.items() if k != "tokenizers"}
    path = root / MANIFEST
    _write_json(path, data)
    return {"path": str(path), "human": len(humans), "generated": len(generated)}


# ---------- CLI ----------


def _cmd(args) -> None:
    root = Path(args.root or Path(__file__).resolve().parents[1]).resolve()
    action = args.blind_action
    if action == "sources":
        result = admit_sources(root)
    elif action == "briefs":
        result = run_briefs(root, max_usd=args.max_usd)
    elif action == "generate":
        result = run_generation(root, max_usd=args.max_usd, parallel=args.parallel)
    elif action == "items":
        smoke = tuple(int(x) for x in args.smoke.split(":")) if args.smoke else None
        result = build_items(
            root,
            build_id=args.build_id,
            smoke=smoke,
            regions=args.regions,
            workers=args.workers,
        )
        if args.publish:
            result = publish_items(root, args.build_id)
    elif action == "manifest":
        result = write_manifest(root, args.build_id)
    else:
        from .blind_report import report

        result = report(
            root,
            build_id=args.build_id,
            predictions=args.predictions,
            out=Path(args.out) if args.out else None,
            lint_only=args.lint_only,
        )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


def add_blind_parser(sub) -> None:
    p = sub.add_parser("blind", help="blind human-versus-generated evaluation set")
    actions = p.add_subparsers(dest="blind_action", required=True)
    actions.add_parser("sources", help="admit the blind human documents")
    for name in ("briefs", "generate"):
        s = actions.add_parser(name)
        s.add_argument(
            "--max-usd",
            type=float,
            required=True,
            help="refuse a run whose pre-run estimate exceeds this",
        )
        if name == "generate":
            s.add_argument("--parallel", type=int, default=6, help="models run at once")
    s = actions.add_parser(
        "items", help="lint the blind documents and write eval items"
    )
    s.add_argument("--build-id", required=True)
    s.add_argument(
        "--smoke", metavar="HUMANS:GENERATED", help="only this many matched documents"
    )
    s.add_argument("--regions", type=int, default=REGIONS)
    s.add_argument("--workers", type=int, default=4)
    s.add_argument(
        "--publish", action="store_true", help="upload test.jsonl and the eval manifest"
    )
    s = actions.add_parser("manifest", help="write the committed blind/manifest.json")
    s.add_argument("--build-id")
    s = actions.add_parser("report", help="write REPORT-blind.md from eval predictions")
    s.add_argument("--build-id", required=True)
    s.add_argument(
        "--predictions",
        nargs="*",
        default=[],
        metavar="[ARM=]PATH",
        help="results/<campaign>/<arm>/results/predictions/<arm>.jsonl files",
    )
    s.add_argument("--lint-only", action="store_true")
    s.add_argument("--out")
    for s in (p, *actions.choices.values()):
        s.set_defaults(func=_cmd)
