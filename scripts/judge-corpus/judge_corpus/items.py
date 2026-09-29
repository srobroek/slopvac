"""Build private, bounded items for local judging and reproducible data splits."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("RAYON_NUM_THREADS", "4")
import yaml
from tokenizers import Tokenizer

from .common import read_jsonl, sha256_text, write_jsonl

CANONICAL = Path("/Users/sjors/personal/dev/slopvac")
JUDGEMENT_REV = "49a91f2b^"
SPLITS = ("train", "dev", "calibration", "test")
GRANULARITY = (("sentence", 30), ("paragraph", 45), ("document", 25))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seed(value: str) -> int:
    return int(digest(value.encode())[:16], 16)


def granularity(key: str) -> str:
    n = seed(f"17:granularity:{key}") % 100
    return "sentence" if n < 30 else ("paragraph" if n < 75 else "document")


def load_tokenizers() -> tuple[list[tuple[str, Tokenizer]], dict[str, str]]:
    hub = Path.home() / ".cache/huggingface/hub"
    files = {
        "qwen3.5-4b": hub
        / "models--Qwen--Qwen3.5-4B-Base/snapshots/1001bb4d826a52d1f399e183466143f4da7b741b/tokenizer.json",
        "laya-modernbert-en": hub
        / "models--convaiinnovations--laya/snapshots/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851/tokenizer/tokenizer.json",
        "laya-multilingual": hub
        / "models--convaiinnovations--laya-multilingual/snapshots/e4e9ddf21a7b1903b7acffd8814ad4307bf63a67/tokenizer/tokenizer.json",
    }
    encoders, digests = [], {}
    for name, path in files.items():
        if not path.is_file():
            raise FileNotFoundError(f"required cached tokenizer is missing: {path}")
        encoders.append((name, Tokenizer.from_file(str(path))))
        digests[name] = digest(path.read_bytes())
    return encoders, digests


_TOKEN_CACHE: dict[tuple[str, str], int] = {}


def token_count(text: str, encoders: list[tuple[str, Tokenizer]]) -> int:
    key = digest(text.encode("utf-8"))
    counts = []
    for name, tokenizer in encoders:
        cache_key = (name, key)
        count = _TOKEN_CACHE.get(cache_key)
        if count is None:
            count = len(tokenizer.encode_batch([text], add_special_tokens=False)[0].ids)
            _TOKEN_CACHE[cache_key] = count
        counts.append(count)
    return max(counts)


def _count(state: dict, question: dict, encoders: list[tuple[str, Tokenizer]]) -> int:
    state_text = json.dumps(state, ensure_ascii=False, sort_keys=True)
    question_text = json.dumps(question, ensure_ascii=False, sort_keys=True)
    state_key, question_key = (
        digest(state_text.encode()),
        digest(question_text.encode()),
    )
    totals = []
    for name, tokenizer in encoders:
        missing = [
            (cache_key, text)
            for cache_key, text in (
                (state_key, state_text),
                (question_key, question_text),
            )
            if (name, cache_key) not in _TOKEN_CACHE
        ]
        if missing:
            encodings = tokenizer.encode_batch(
                [text for _, text in missing], add_special_tokens=False
            )
            for (cache_key, _), encoding in zip(missing, encodings):
                _TOKEN_CACHE[(name, cache_key)] = len(encoding.ids)
        totals.append(
            _TOKEN_CACHE[(name, state_key)] + _TOKEN_CACHE[(name, question_key)]
        )
    return max(totals)


def paragraphs(text: str) -> list[tuple[int, int, str]]:
    return [
        (m.start(), m.end(), m.group())
        for m in re.finditer(r"\S(?:.*?\S)?(?=\n[ \t]*\n|\Z)", text, re.S)
    ]


def headings(text: str) -> list[tuple[int, int, str]]:
    lines = text.splitlines(keepends=True)
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line)
    out = []
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r"^#{1,6}\s+\S", s):
            out.append(
                (offsets[i], offsets[i] + len(line), re.sub(r"^#{1,6}\s+", "", s))
            )
        elif (
            i + 1 < len(lines)
            and re.fullmatch(r"[=~^`-]{3,}\s*", lines[i + 1].strip())
            and s
        ):
            out.append((offsets[i], offsets[i] + len(line) + len(lines[i + 1]), s))
    return out


def heading_at(text: str, offset: int) -> str:
    title = ""
    for start, end, name in headings(text):
        if start <= offset < end:
            title = name
        elif end <= offset:
            title = name
        elif start > offset:
            break
    return title


def sentences(text: str, start: int, end: int) -> list[tuple[int, int, str]]:
    part = text[start:end]
    boundary = re.compile(r"(?<=[.!?])['\"”’)]*[ \t]+(?=[A-Z0-9])")
    cuts = [start]
    for m in boundary.finditer(part):
        left = part[: m.start()].rstrip()
        if re.search(
            r"\b(?:[A-Z](?:\.[A-Z]){1,4}|Mr|Mrs|Dr|vs|etc|e\.g|i\.e)\.$", left
        ):
            continue
        cuts.append(start + m.end())
    cuts.append(end)
    result = []
    for a, b in zip(cuts, cuts[1:]):
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if a < b:
            result.append((a, b, text[a:b]))
    return result


def _sections(text: str) -> list[tuple[int, int, str, str]]:
    hs = headings(text)
    if hs:
        return [
            (a, b, name, text[a:b].strip())
            for i, (a, _, name) in enumerate(hs)
            if (b := (hs[i + 1][0] if i + 1 < len(hs) else len(text))) > a
        ]
    ps = paragraphs(text)
    return [(a, b, "", value) for a, b, value in ps]


def span_for(
    text: str,
    kind: str,
    anchor: int,
    question: dict,
    encoders: list[tuple[str, Tokenizer]],
    genre: str,
) -> tuple[str, str, int, int, bool, str]:
    ps = paragraphs(text) or [(0, len(text), text)]
    pi = next((i for i, (a, b, _) in enumerate(ps) if a <= anchor <= b), 0)
    start, end, paragraph = ps[pi]
    title = heading_at(text, start)
    if kind == "sentence":
        ss = sentences(text, start, end) or [(start, end, paragraph)]
        a, b, value = next((s for s in ss if s[0] <= anchor <= s[1]), ss[0])
        context = "\n".join(
            x
            for x in (
                title,
                next((x[2] for x in ss if x[1] <= a), ""),
                next((x[2] for x in ss if x[0] >= b), ""),
            )
            if x
        )
        state = {
            "text": value,
            "context": context,
            "heading": title,
            "genre": genre,
            "granularity": kind,
        }
        while context and _count(state, question, encoders) > 1024:
            context = "\n".join(context.splitlines()[:-1])
            state["context"] = context
        return (
            (value, context, a, b, False, title)
            if _count(state, question, encoders) <= 1024
            else ("", context, a, b, False, title)
        )
    if kind == "paragraph":
        context = [title] if title else []
        if pi:
            context.append(ps[pi - 1][2])
        if pi + 1 < len(ps):
            context.append(ps[pi + 1][2])
        context = [x for x in context if x != paragraph]
        state = {
            "text": paragraph,
            "context": "\n\n".join(context),
            "heading": title,
            "genre": genre,
            "granularity": kind,
        }
        while context and _count(state, question, encoders) > 1024:
            context.pop()
            state["context"] = "\n\n".join(context)
        if _count(state, question, encoders) > 1024:
            return "", state["context"], start, end, False, title
        return paragraph, state["context"], start, end, False, title
    selected, selected_end = [], 0
    truncated = False
    for a, b, name, section in _sections(text):
        candidate = "\n\n".join(selected + [section])
        state = {
            "text": candidate,
            "context": "",
            "heading": title,
            "genre": genre,
            "granularity": kind,
        }
        if _count(state, question, encoders) > 4096:
            truncated = True
            break
        selected.append(section)
        selected_end = b
    if selected_end < len(text):
        truncated = True
    value = "\n\n".join(selected)
    if not value:
        return "", "", 0, 0, True, title
    # Each section boundary is a whole-paragraph/sentence boundary, not a character truncation.
    return value, "", 0, len(value), truncated, title


def _source_group(row: dict) -> str:
    loc = row.get("immutable_locator") or {}
    if "repository" in loc:
        key = ("git", loc.get("repository"), loc.get("commit"), loc.get("path"))
    elif "rfc" in loc:
        key = ("rfc", loc.get("rfc"))
    elif "post_id" in loc:
        key = ("se", loc.get("site"), loc.get("post_id"))
    elif "oldid" in loc:
        key = ("wiki", loc.get("oldid"))
    else:
        key = (row.get("source_family"), row["id"])
    return json.dumps(key, ensure_ascii=False, sort_keys=True)


def assign_splits(
    humans: list[dict], generated: list[dict]
) -> tuple[dict[str, str], dict[str, str]]:
    # Keep every unit of an original source document and its generated descendants together.
    by_genre: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    human_group = {r["id"]: _source_group(r) for r in humans}
    for r in humans:
        by_genre[r.get("genre", "unknown")][human_group[r["id"]]].add(r["id"])
    for r in generated:
        parent = r.get("source_id")
        group = human_group.get(parent, f"generated:{parent or r['id']}")
        genre = next(
            (h.get("genre", "unknown") for h in humans if h["id"] == parent),
            r.get("genre", "unknown"),
        )
        by_genre[genre][group].add(r["id"])
    result = {}
    ratios = (("test", 15), ("calibration", 10), ("dev", 10), ("train", 65))
    for genre, groups in by_genre.items():
        ordered = sorted(groups, key=lambda g: (seed(f"17:{genre}:{g}"), g))
        n = len(ordered)
        counts = {s: int(n * pct / 100) for s, pct in ratios}
        counts["train"] += n - sum(counts.values())
        i = 0
        for split, _ in ratios:
            for group in ordered[i : i + counts[split]]:
                for item_id in groups[group]:
                    result[item_id] = split
            i += counts[split]
    return result, {r["id"]: result[r["id"]] for r in humans}


def _rules_current() -> list[dict]:
    proc = subprocess.run(
        [
            "uvx",
            "--from",
            str(CANONICAL / "packages/slopvac-lint"),
            "slopvac",
            "rules",
            "--format",
            "json",
        ],
        cwd=CANONICAL,
        capture_output=True,
        text=True,
        check=True,
    )
    rules = json.loads(proc.stdout)["rules"]
    return [
        {
            **rule,
            "id": rule["rule_id"],
            "category": rule.get("category", rule["rule_id"].split(".")[0]),
        }
        for rule in rules
    ]


def _rules_judgement() -> list[dict]:
    paths = subprocess.run(
        [
            "git",
            "-C",
            str(CANONICAL),
            "ls-tree",
            "-r",
            "--name-only",
            JUDGEMENT_REV,
            "packages/slopvac-lint/src/slopvac/rules",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    found = []
    for path in paths:
        if not path.endswith((".yml", ".yaml")):
            continue
        raw = subprocess.run(
            ["git", "-C", str(CANONICAL), "show", f"{JUDGEMENT_REV}:{path}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for doc in yaml.safe_load_all(raw):
            if not isinstance(doc, dict):
                continue
            category = doc.get("id", Path(path).stem)
            for rule in doc.get("rules", []):
                if rule.get("kind") == "judgement":
                    found.append(
                        {**rule, "category": category, "id": f"{category}.{rule['id']}"}
                    )
    if len(found) != 65:
        raise ValueError(f"expected 65 judgement rules, found {len(found)}")
    return found


def held_out(rules: list[dict]) -> set[str]:
    cats = defaultdict(list)
    for r in rules:
        cats[r.get("category", r["id"].split(".")[0])].append(r["id"])
    result = set()
    for category, ids in cats.items():
        n = max(1, round(0.2 * len(ids))) if len(ids) >= 3 else 0
        result.update(sorted(ids, key=lambda x: (seed(f"17:{category}:{x}"), x))[:n])
    return result


def question_for(role: str, rule: dict, finding: dict | None = None) -> dict:
    if role == "finding-confirmation":
        assert finding is not None
        return {
            "type": "choice",
            "rule_id": finding["rule_id"],
            "prompt": "Is this lint finding valid? Judge the flagged text in the supplied span and context. Select exactly one option.",
            "rule_name": finding.get("rule_name", finding["rule_id"]),
            "rule_message": finding.get("rule_message", ""),
            "lint_message": finding.get("message", ""),
            "matched_text": finding.get("matched_text", ""),
            "options": {
                "real-defect": "A real prose defect under this lint rule.",
                "false-positive": "The rule fired on acceptable prose.",
                "insufficient-context": "The span and context do not decide the finding.",
            },
        }
    return {
        "type": "noul",
        "rule_id": rule["id"],
        "prompt": rule.get("judgement_question", "Does the span exhibit the defect?"),
        "criteria": [
            {k: e.get(k) for k in ("bad", "good", "note") if e.get(k) is not None}
            for e in rule.get("examples", [])
        ],
    }


def _private_text(root: Path, item_id: str, text: str) -> tuple[str, str]:
    rel = Path(".cache/items") / f"{item_id}.txt"
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(rel), sha256_text(text)


def _lint_text(text: str) -> str:
    """Blank a leading `---` line so Vale does not parse the document as YAML
    front matter. Generated documents sometimes open with a horizontal rule;
    Vale then fails the whole batch with E201. Spaces keep every offset."""
    m = re.match(r"(-{3,})[ \t]*(?=\r?\n)", text)
    return " " * len(m.group(1)) + text[m.end(1) :] if m else text


def _run_lint(
    files: list[tuple[str, Path]], batch_size: int = 40
) -> dict[str, list[dict]]:
    out = defaultdict(list)
    cmd = ["uvx", "--from", str(CANONICAL / "packages/slopvac-lint"), "slopvac", "lint"]
    for i in range(0, len(files), batch_size):
        chunk = files[i : i + batch_size]
        p = subprocess.run(
            cmd
            + [str(path) for _, path in chunk]
            + ["--format", "json", "--locale", "und"],
            cwd=CANONICAL,
            capture_output=True,
            text=True,
            env={**os.environ, "HF_HUB_OFFLINE": "1"},
        )
        # Exit 2: some documents were not fully checked. One bad file can make
        # Vale reject the whole batch, so re-lint the batch one file at a time
        # and fail closed if any document is still unchecked.
        if p.returncode == 2 and len(chunk) > 1:
            for name, found in _run_lint(chunk, batch_size=1).items():
                out[name].extend(found)
            continue
        if p.returncode not in (0, 1):
            raise RuntimeError(
                f"slopvac lint failed {p.returncode} on {[str(x) for _, x in chunk]}: "
                f"{p.stdout[-1000:]}{p.stderr[-500:]}"
            )
        report = json.loads(p.stdout)
        if report.get("schema_version") != 1 or any(
            d.get("unchecked") for d in report.get("documents", [])
        ):
            raise RuntimeError("lint returned incomplete results")
        for doc in report.get("documents", []):
            out[Path(doc["path"]).name].extend(doc.get("findings", []))
    return out


def _offset(text: str, line: int, col: int) -> int:
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    return min(
        len(text), starts[max(0, min(line - 1, len(starts) - 1))] + max(0, col - 1)
    )


def _make_item(
    root: Path,
    *,
    role: str,
    rule: dict,
    source: dict,
    text: str,
    label,
    origin: str | None,
    split: str,
    kind: str,
    anchor: int,
    encoders,
    source_group: str,
    finding: dict | None = None,
    construction: dict | None = None,
) -> dict | None:
    g = granularity(f"{role}:{source['id']}:{rule['id']}:{anchor}:{construction or ''}")
    flagged = (finding or {}).get("matched_text") or ""
    if finding and not flagged:
        containing = next((p for p in paragraphs(text) if p[0] <= anchor <= p[1]), None)
        if containing:
            a0, b0, _ = containing
            sentence = next(
                (s for s in sentences(text, a0, b0) if s[0] <= anchor <= s[1]),
                containing,
            )
            flagged = sentence[2]
    question = question_for(
        role,
        rule,
        {
            **(finding or {}),
            "rule_id": rule["id"],
            "rule_name": rule.get("name", rule["id"]),
            "rule_message": rule.get("message", ""),
            "matched_text": flagged,
            "start": 0,
            "end": 0,
        }
        if finding
        else None,
    )
    value, context, a, b, truncated, title = span_for(
        text, g, anchor, question, encoders, source.get("genre", "unknown")
    )
    if not value:
        return None
    state = {
        "text": value,
        "context": context,
        "heading": title,
        "genre": source.get("genre", "unknown"),
        "granularity": g,
    }
    position = -1
    if finding:
        position = value.find(flagged) if flagged else -1
        if position < 0:
            return None
        question["finding"] = {
            "rule_id": rule["id"],
            "rule_name": rule.get("name", rule["id"]),
            "rule_message": rule.get("message", ""),
            "lint_message": finding.get("message", ""),
            "matched_text": flagged,
            "start": position,
            "end": position + len(flagged),
        }
    count = _count(state, question, encoders)
    if count > (4096 if g == "document" else 1024):
        return None
    item_id = digest(
        f"{role}|{source['id']}|{rule['id']}|{kind}|{g}|{anchor}".encode()
    )[:24]
    path, text_digest = _private_text(root, item_id, value)
    item = {
        "id": item_id,
        "role": role,
        "rule_id": rule["id"],
        "rule_category": rule.get("category", rule["id"].split(".")[0]),
        "split": split,
        "rule_held_out": False,
        "genre": source.get("genre", "unknown"),
        "source_id": source["id"],
        "source_group": source_group,
        "source_family": source.get("source_family"),
        "source_vendor": source.get("vendor"),
        "source_tier": source.get("tier"),
        "granularity": g,
        "truncated": truncated,
        "text_path": path,
        "text_sha256": text_digest,
        "question": question,
        "label": label,
        "label_origin": origin,
        "state_question_tokens": count,
        "state": state,
        "context": context,
    }
    if finding:
        item["finding"] = {
            "rule_id": rule["id"],
            "rule_name": rule.get("name", rule["id"]),
            "rule_message": rule.get("message", ""),
            "fix": rule.get("fix", ""),
            "lint_message": finding.get("message", ""),
            "matched_text": flagged,
            "start": position,
            "end": position + len(flagged),
            "text_path": path,
        }
    if construction:
        item["construction"] = construction
    return item


def _externalize_states(root: Path, items: list[dict]) -> None:
    cache_dir = root / ".cache/items/state"
    cache_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        state = item.pop("state", None)
        item.pop("context", None)
        if state is None:
            continue
        encoded = json.dumps(state, ensure_ascii=False, sort_keys=True) + "\n"
        path = cache_dir / f"{item['id']}.json"
        path.write_text(encoded, encoding="utf-8")
        item["state_path"] = str(path.relative_to(root))
        item["state_sha256"] = digest(encoded.encode("utf-8"))


def _state_of(root: Path, item: dict):
    """An item's state, from the record or from its externalised state file."""
    if "state" in item:
        return item["state"]
    if item.get("state_path"):
        return json.loads((root / item["state_path"]).read_text(encoding="utf-8"))
    return None


def _write_outputs(
    root: Path,
    items: list[dict],
    tokenizer_digests: dict,
    held_lint: set[str],
    held_judgement: set[str],
    counts: dict,
) -> dict:
    held = held_lint | held_judgement
    for x in items:
        if x["split"] != "test" and (x["rule_held_out"] or x["rule_id"] in held):
            raise AssertionError(f"held-out rule leaked: {x['rule_id']}")
    out = root / "items"
    out.mkdir(parents=True, exist_ok=True)
    sizes, digests = {}, {}
    for split in SPLITS:
        path = out / f"{split}.jsonl"
        rows = [x for x in items if x["split"] == split]
        write_jsonl(path, rows)
        sizes[split] = len(rows)
        digests[split] = digest(path.read_bytes())
        path.with_suffix(path.suffix + ".sha256").write_text(
            f"{digests[split]}  {path.name}\n"
        )
    manifest = {
        "schema_version": 1,
        "seed": 17,
        "split_group": "source-document locator family plus generated descendants",
        "split_sizes": sizes,
        "split_digests": digests,
        "granularity_target_percent": dict(GRANULARITY),
        "tokenizers": tokenizer_digests,
        "held_out_lint_rules": sorted(held_lint),
        "held_out_judgement_rules": sorted(held_judgement),
        "counts": counts,
    }
    p = out / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (out / "manifest.sha256").write_text(digest(p.read_bytes()) + "  manifest.json\n")
    test = [
        x
        for x in items
        if x["split"] == "test" and x.get("label_origin") == "human-adjudication"
    ]
    sheet_dir = out / "adjudication"
    sheet_dir.mkdir(exist_ok=True)
    sheet = [
        {
            "item_id": x["id"],
            "role": x["role"],
            "rule_id": x["rule_id"],
            "rule_category": x["rule_category"],
            "granularity": x["granularity"],
            "genre": x["genre"],
            "text_path": x["text_path"],
            "text_sha256": x["text_sha256"],
            "state": _state_of(root, x),
            "context": x.get("context")
            or (_state_of(root, x) or {}).get("context", ""),
            "question": x["question"],
            "finding": x.get("finding"),
            "adjudicator_1": None,
            "adjudicator_2": None,
        }
        for x in test
    ]
    jp = sheet_dir / "test-sheet.jsonl"
    write_jsonl(jp, sheet)
    cp = sheet_dir / "test-sheet.csv"
    cols = [
        "item_id",
        "role",
        "rule_id",
        "granularity",
        "genre",
        "text_path",
        "text_sha256",
        "state",
        "question",
        "finding",
        "adjudicator_1",
        "adjudicator_2",
    ]
    with cp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in sheet:
            w.writerow(
                {
                    k: json.dumps(row[k], ensure_ascii=False)
                    if isinstance(row[k], (dict, list))
                    else row[k]
                    for k in cols
                }
            )
    dimensions = {
        "role_rule_label_origin_genre_granularity": dict(
            Counter(
                "|".join(
                    (
                        x["role"],
                        x["rule_id"],
                        str(x.get("label_origin")),
                        x["genre"],
                        x["granularity"],
                    )
                )
                for x in items
            )
        ),
        "finding_confirmation_labels": dict(
            Counter(
                str(x.get("label"))
                for x in items
                if x["role"] == "finding-confirmation"
            )
        ),
        "test_seen_unseen": dict(
            Counter(
                "unseen" if x["rule_held_out"] else "seen"
                for x in items
                if x["split"] == "test"
            )
        ),
        "split_granularity": {
            split: dict(Counter(x["granularity"] for x in items if x["split"] == split))
            for split in SPLITS
        },
    }
    report = {
        "split_sizes": sizes,
        "split_digests": digests,
        "adjudication_sheet_rows": len(sheet),
        "dimensions": dimensions,
    }
    report_path = root / "items-report.md"
    report_path.write_text(
        "# Local judging item pipeline report\n\n```json\n"
        + json.dumps(report, indent=2, sort_keys=True)
        + "\n```\n",
        encoding="utf-8",
    )
    return report


def _read_texts(root: Path, rows: list[dict]) -> dict[str, str]:
    texts = {}
    for row in rows:
        paths = [
            row.get("cache_path"),
            row.get("text_path"),
            f".cache/generated/{row['id']}.txt",
            f".cache/{row.get('s3_key', '')}" if row.get("s3_key") else None,
        ]
        path = next(
            (root / value for value in paths if value and (root / value).is_file()),
            None,
        )
        if path:
            texts[row["id"]] = path.read_text(encoding="utf-8")
    return texts


def _sample_adjudication(
    items: list[dict], limits: dict[str, int]
) -> tuple[list[dict], dict[str, int]]:
    selected_by_split = {}
    selected_items = [
        row
        for row in items
        if row["split"] not in limits or row.get("label_origin") == "construction"
    ]
    dropped = {}
    for split, limit in limits.items():
        candidates = [
            row
            for row in items
            if row["split"] == split and row.get("label_origin") != "construction"
        ]
        strata: dict[tuple, list[dict]] = defaultdict(list)
        for row in candidates:
            strata[
                (
                    row["role"],
                    row["rule_category"],
                    row["genre"],
                    row["granularity"],
                    json.dumps(row.get("provenance", {}), sort_keys=True),
                )
            ].append(row)
        queues = []
        for key, values in sorted(strata.items()):
            values.sort(key=lambda row: (seed(f"17:{split}:{row['id']}"), row["id"]))
            queues.append(values)
        selected = []
        while len(selected) < limit and queues:
            remaining = []
            for values in queues:
                if len(selected) < limit and values:
                    selected.append(values.pop(0))
                if values:
                    remaining.append(values)
            queues = remaining
        selected_by_split[split] = {row["id"] for row in selected}
        selected_items.extend(selected)
        dropped[split] = len(candidates) - len(selected)
    retained = [
        row
        for row in selected_items
        if row["split"] not in limits
        or row.get("label_origin") == "construction"
        or row["id"] in selected_by_split[row["split"]]
    ]
    return retained, dropped


def _merge_shards(root: Path, shard_count: int) -> dict:
    rows = []
    for index in range(shard_count):
        path = root / ".cache/items/shards" / f"{index:02d}-of-{shard_count:02d}.jsonl"
        rows.extend(read_jsonl(path))
    unique = {row["id"]: row for row in rows}
    merged = sorted(
        unique.values(),
        key=lambda row: (
            row["split"],
            row["role"],
            row["rule_id"],
            row["source_id"],
            row["id"],
        ),
    )
    if not merged:
        raise ValueError("shard manifests are empty")
    merged, dropped = _sample_adjudication(merged, {"test": 600, "calibration": 300})
    _externalize_states(root, merged)
    root_rows = list(read_jsonl(root / "sources/human.jsonl"))
    generated = list(read_jsonl(root / "generated/manifest.jsonl"))
    _, tokenizer_digests = load_tokenizers()
    lint_rules, judge_rules = _rules_current(), _rules_judgement()
    held_lint, held_judge = held_out(lint_rules), held_out(judge_rules)
    counts = {
        "human_documents": len(root_rows),
        "generated_documents": len(generated),
        "lint_findings": sum(
            r["role"] == "finding-confirmation"
            and r.get("label_origin") != "construction"
            for r in merged
        ),
        "gold_v1_items": sum(r.get("source_family") == "gold-v1" for r in merged),
        "built_items": len(merged),
        "dropped_model_derived_for_adjudication": dropped,
    }
    report = _write_outputs(
        root, merged, tokenizer_digests, held_lint, held_judge, counts
    )
    report.update(counts)
    return report


def build_items(
    root: Path,
    include_generated: bool = False,
    shard: tuple[int, int] | None = None,
    merge_shards: int | None = None,
) -> dict:
    if merge_shards:
        return _merge_shards(root, merge_shards)
    humans = list(read_jsonl(root / "sources/human.jsonl"))
    if not humans:
        raise ValueError("sources/human.jsonl is empty")
    generated = (
        list(read_jsonl(root / "generated/manifest.jsonl")) if include_generated else []
    )
    encoders, tokenizer_digests = load_tokenizers()
    lint_rules = _rules_current()
    judgement_rules = _rules_judgement()
    by_lint = {r["id"]: r for r in lint_rules}
    by_judge = {r["id"]: r for r in judgement_rules}
    held_lint, held_judge = held_out(lint_rules), held_out(judgement_rules)
    splits, human_splits = assign_splits(humans, generated)
    rows = humans + generated
    if shard:
        shard_index, shard_count = shard
        if shard_count < 1 or shard_index < 0 or shard_index >= shard_count:
            raise ValueError("shard must be index/count with 0 <= index < count")
        rows = [row for row in rows if seed(row["id"]) % shard_count == shard_index]
    texts = _read_texts(root, rows)
    rows = [row for row in rows if row["id"] in texts]
    work = root / ".cache/items/lint-input"
    work.mkdir(parents=True, exist_ok=True)
    lint_files = []
    for row in rows:
        path = work / f"{row['id']}.md"
        path.write_text(_lint_text(texts[row["id"]]), encoding="utf-8")
        lint_files.append((row["id"], path))
    findings = _run_lint(lint_files)
    items = []
    shard_index, shard_count = shard or (0, 1)
    for row in rows:
        source_id, text, split = row["id"], texts[row["id"]], splits[row["id"]]
        srcgroup = _source_group(row)
        genre = row.get("genre", "unknown")
        for finding in findings.get(f"{source_id}.md", []):
            rule = by_lint.get(finding["rule_id"])
            if not rule:
                continue
            anchor = _offset(text, finding.get("line", 1), finding.get("column", 1))
            item = _make_item(
                root,
                role="finding-confirmation",
                rule=rule,
                source=row,
                text=text,
                label=None,
                origin="human-adjudication"
                if split == "test"
                else ("teacher-panel" if split == "train" else None),
                split=split,
                kind="finding",
                anchor=anchor,
                encoders=encoders,
                source_group=srcgroup,
                finding=finding,
            )
            if item:
                item["rule_held_out"] = rule["id"] in held_lint
                items.append(item)
        # At most three rule questions per unit. Deterministic random rotation balances rules over units.
        candidates = [
            r for r in judgement_rules if r["id"] not in held_judge or split == "test"
        ]
        candidates.sort(
            key=lambda r: (seed(f"17:rule-choice:{source_id}:{r['id']}"), r["id"])
        )
        selected_rules = candidates[:3]
        for rule in selected_rules:
            ps = paragraphs(text)
            if not ps:
                continue
            anchor = ps[seed(f"17:anchor:{source_id}:{rule['id']}") % len(ps)][0]
            item = _make_item(
                root,
                role="semantic-detection",
                rule=rule,
                source=row,
                text=text,
                label=None,
                origin="human-adjudication"
                if split == "test"
                else ("teacher-panel" if split == "train" else None),
                split=split,
                kind="unseeded",
                anchor=anchor,
                encoders=encoders,
                source_group=srcgroup,
            )
            if item:
                item["rule_held_out"] = rule["id"] in held_judge
                items.append(item)
    # Construction positives from lint-rule bad examples, re-linted at sentence/paragraph/document scope.
    seed_work = root / ".cache/items/seed-input"
    seed_work.mkdir(parents=True, exist_ok=True)
    seed_meta, seed_files = {}, []
    genres = defaultdict(list)
    for r in humans:
        genres[r.get("genre", "unknown")].append(r)
    for rule in lint_rules:
        for ex_i, example in enumerate(rule.get("examples") or []):
            bad = (example.get("bad") or "").strip()
            if not bad:
                continue
            host = min(
                humans,
                key=lambda r: (
                    seed(f"17:lintseed:{rule['id']}:{ex_i}:{r['id']}"),
                    r["id"],
                ),
            )
            if shard and seed(host["id"]) % shard_count != shard_index:
                continue
            base = texts[host["id"]]
            ps = paragraphs(base)
            if not ps:
                continue
            a, b, paragraph = ps[seed(f"17:lintpara:{rule['id']}:{ex_i}") % len(ps)]
            # Locate a sentence if possible; insert at the selected granularity using a boundary-preserving append.
            g = granularity(f"lintseed:{rule['id']}:{ex_i}")
            if g == "sentence":
                ss = sentences(base, a, b)
                a, b, paragraph = (
                    next((s for s in ss if s[0] <= (a + b) // 2 <= s[1]), ss[0])
                    if ss
                    else (a, b, paragraph)
                )
            elif g == "document":
                a, b, paragraph = 0, len(base), base
            seeded = base[:b].rstrip() + " " + bad + base[b:]
            injected = b - len(base[:b]) + len(base[:b].rstrip()) + 1
            seed_name = f"{rule['id']}:{ex_i}:{host['id']}"
            path = seed_work / f"{digest(seed_name.encode())[:24]}.md"
            path.write_text(_lint_text(seeded), encoding="utf-8")
            seed_files.append((path.stem, path))
            seed_meta[path.name] = (rule, host, seeded, injected, len(bad), ex_i)
    seed_findings = _run_lint(seed_files)
    for filename, (rule, host, seeded, injected, bad_length, ex_i) in seed_meta.items():
        exact = [
            f
            for f in seed_findings.get(filename, [])
            if f["rule_id"] == rule["id"]
            and injected
            <= _offset(seeded, f.get("line", 1), f.get("column", 1))
            <= injected + bad_length
        ]
        if not exact:
            continue
        f = exact[0]
        anchor = _offset(seeded, f.get("line", 1), f.get("column", 1))
        split = human_splits[host["id"]]
        item = _make_item(
            root,
            role="finding-confirmation",
            rule=rule,
            source=host,
            text=seeded,
            label="real-defect",
            origin="construction",
            split=split,
            kind=f"lint-example:{ex_i}",
            anchor=anchor,
            encoders=encoders,
            source_group=_source_group(host),
            finding=f,
            construction={
                "kind": "lint-example",
                "example_index": ex_i,
                "seed_start": injected,
                "seed_end": injected + bad_length,
            },
        )
        if item:
            item["rule_held_out"] = rule["id"] in held_lint
            items.append(item)
    # Judgement-rule seed/control pairs for each pinned exemplar, sampled across source units.
    for rule in judgement_rules:
        exs = rule.get("examples", [])
        if not exs:
            continue
        eligible_hosts = [
            r
            for r in humans
            if shard is None or seed(r["id"]) % shard_count == shard_index
        ]
        if not eligible_hosts:
            continue
        host = min(
            eligible_hosts,
            key=lambda r: (seed(f"17:judgeseed:{rule['id']}:{r['id']}"), r["id"]),
        )
        if shard and seed(host["id"]) % shard_count != shard_index:
            continue
        base = texts[host["id"]]
        ps = paragraphs(base)
        if not ps:
            continue
        a, b, para = ps[seed(f"17:judgespan:{rule['id']}") % len(ps)]
        ex = exs[0]
        bad = (ex.get("bad") or "").strip()
        if not bad:
            continue
        g = granularity(f"judgeseed:{rule['id']}:{host['id']}")
        seeded = base[:b].rstrip() + " " + bad + base[b:]
        anchor = b
        split = human_splits[host["id"]]
        for label, content, content_anchor in (
            (False, base, a),
            (True, seeded, anchor),
        ):
            item = _make_item(
                root,
                role="semantic-detection",
                rule=rule,
                source=host,
                text=content,
                label=label,
                origin="construction",
                split=split,
                kind=f"judgement-example:{int(label)}",
                anchor=content_anchor,
                encoders=encoders,
                source_group=_source_group(host),
                construction={
                    "kind": "judgement-example",
                    "example_index": 0,
                    "positive": label,
                },
            )
            if item:
                item["rule_held_out"] = rule["id"] in held_judge
                item["granularity"] = g
                items.append(item)
    gold = subprocess.run(
        [
            "git",
            "-C",
            str(CANONICAL),
            "show",
            f"{JUDGEMENT_REV}:packages/slopvac-lint/tests/fixtures/judgement/gold/gold-v1.jsonl",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    if json.loads(gold[0]).get("version") != 1:
        raise ValueError("unknown gold fixture version")
    judgement_order = sorted(judgement_rules, key=lambda rule: rule["id"])
    control_index = 0
    for n, line in enumerate(gold[1:]):
        if shard and n % shard_count != shard_index:
            continue
        record = json.loads(line)
        content = record["text"]
        if record.get("rule_id"):
            rule = by_judge[record["rule_id"]]
            assignments = [(rule, bool(record.get("defect_span")))]
            defect = record.get("defect_span", "")
            pos = content.find(defect) if defect else -1
        else:
            assignments = [
                (
                    judgement_order[
                        (control_index * 3 + offset) % len(judgement_order)
                    ],
                    False,
                )
                for offset in range(3)
            ]
            defect, pos = "", -1
            control_index += 1
        for rule, label in assignments:
            fake = {
                "id": f"gold-v1-{n}-{rule['id']}",
                "genre": "unknown",
                "source_family": "gold-v1",
            }
            item = _make_item(
                root,
                role="semantic-detection",
                rule=rule,
                source=fake,
                text=content,
                label=label,
                origin="construction",
                split="test",
                kind=f"gold-v1:{n}:{rule['id']}",
                anchor=max(0, pos),
                encoders=encoders,
                source_group=f"gold-v1:{rule['id']}",
                construction={
                    "kind": "gold-v1",
                    "control": not bool(record.get("rule_id")),
                    "defect_start": pos if pos >= 0 else None,
                    "defect_end": pos + len(defect) if pos >= 0 else None,
                },
            )
            if item:
                item["rule_held_out"] = rule["id"] in held_judge
                items.append(item)
    # Avoid duplicate item IDs. A held-out rule is unseen: none of its items,
    # constructions included, may reach train, dev, or calibration.
    unique = {
        x["id"]: x for x in items if not (x["rule_held_out"] and x["split"] != "test")
    }
    items = sorted(
        unique.values(), key=lambda x: (x["split"], x["role"], x["rule_id"], x["id"])
    )
    if shard:
        shard_path = (
            root / ".cache/items/shards" / f"{shard[0]:02d}-of-{shard[1]:02d}.jsonl"
        )
        write_jsonl(shard_path, items)
        return {
            "shard": list(shard),
            "items": len(items),
            "manifest": str(shard_path.relative_to(root)),
        }
    counts = {
        "human_documents": len(humans),
        "generated_documents": len(generated),
        "lint_findings": sum(len(x) for x in findings.values()),
        "gold_v1_rows": len(gold) - 1,
        "built_items": len(items),
    }
    report = _write_outputs(
        root, items, tokenizer_digests, held_lint, held_judge, counts
    )
    report.update(counts)
    return report


def split_items(root: Path) -> dict:
    items = [
        x for split in SPLITS for x in read_jsonl(root / "items" / f"{split}.jsonl")
    ]
    if not items:
        raise ValueError("no items; run items build first")
    _, tokenizers = load_tokenizers()
    manifest = json.loads((root / "items/manifest.json").read_text(encoding="utf-8"))
    return _write_outputs(
        root,
        items,
        tokenizers,
        set(manifest["held_out_lint_rules"]),
        set(manifest["held_out_judgement_rules"]),
        {**manifest.get("counts", {}), "built_items": len(items)},
    )
