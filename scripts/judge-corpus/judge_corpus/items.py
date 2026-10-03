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
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("RAYON_NUM_THREADS", "4")
import yaml
from tokenizers import Tokenizer

from .common import read_jsonl, sha256_text, shingles, write_jsonl

# The slopvac checkout whose lint rules label the corpus. Point
# SLOPVAC_LINT_ROOT at a worktree of the commit the build must reflect.
CANONICAL = Path(
    os.environ.get("SLOPVAC_LINT_ROOT", "/Users/sjors/personal/dev/slopvac")
)
JUDGEMENT_REV = "49a91f2b^"
SPLITS = ("train", "dev", "calibration", "test")
GRANULARITY = (("sentence", 30), ("paragraph", 45), ("document", 25))
# Verified rule example bank (see bank.py); private.
BANK_PATH = Path(".cache/bank/bank.jsonl")
# One plain yes/no question per semantic rule, about the item's highlighted
# region, with a one-line Yes example and No example (semantic_questions.py
# drafts them; checked by hand; committed).
QUESTIONS_PATH = Path(__file__).resolve().parents[1] / "items/semantic-questions.yml"
# Judgement rules whose question needs context an item cannot carry. Their bank
# passages stay (so bank splits and held-out rules do not move), but they get
# no semantic-detection items.
EXCLUDED_JUDGEMENT_RULES = {
    "prose-scope.code-change-prose-scope": "needs the code diff and the user's request",
    "ai-tells-content-shape.vaporware-description": "needs the code at HEAD to check each behaviour claim",
    "ai-tells-content-shape.fabricated-citations-remainder": "needs the cited sources, fetched",
    "ste-words.domain-noun-not-organization-approved": "needs the project glossary, API reference or schema",
    "ste-words.domain-noun-category-membership": "needs the controlled vocabulary and the project's declared domain-noun categories",
    "ste-words.domain-verb-category-membership": "needs the controlled vocabulary and the project's declared domain-verb categories",
    "ste-words.unapproved-word-not-a-domain-noun": "needs the controlled vocabulary to know a word is out of vocabulary",
    "ste-words.word-used-outside-permitted-sense": "needs the meaning the controlled-vocabulary entry records",
    "ste-practices.word-sense-incorrect": "needs the sense the controlled-vocabulary entry records",
    "ste-practices.word-swap-insufficient": "needs the replacement word the vocabulary suggests",
}
# The rule files at JUDGEMENT_REV fold a list of exception codes into the
# question text ("... rewrite it. - quotation - code-span").
_EXCEPTION_CODES = re.compile(r"(?:\s+-\s+[a-z][a-z0-9-]*)+\s*$")
# A semantic item's region must hold this many words of prose. Regions picked
# from host text aim at the length of a bank passage for the rule (this many
# characters when the rule has none); an unseeded span whose region fails is
# resampled from up to REGION_ATTEMPTS anchor paragraphs.
MIN_REGION_WORDS = 6
DEFAULT_REGION_CHARS = 200
REGION_ATTEMPTS = 3


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
                    question = rule.get("judgement_question", "")
                    codes = _EXCEPTION_CODES.search(question)
                    found.append(
                        {
                            **rule,
                            "category": category,
                            "id": f"{category}.{rule['id']}",
                            "judgement_question": question[: codes.start()]
                            if codes
                            else question,
                            "judgement_exceptions": re.findall(
                                r"-\s+([a-z][a-z0-9-]*)", codes.group()
                            )
                            if codes
                            else [],
                        }
                    )
    if len(found) != 65:
        raise ValueError(f"expected 65 judgement rules, found {len(found)}")
    return found


def semantic_rules() -> tuple[list[dict], set[str]]:
    """The judgement rules that get semantic-detection items, and the held-out
    ones among them. Held-out rules are drawn from all judgement rules, so an
    excluded rule never moves another rule in or out of the held-out set."""
    rules = _rules_judgement()
    kept = [r for r in rules if r["id"] not in EXCLUDED_JUDGEMENT_RULES]
    return kept, held_out(rules) - set(EXCLUDED_JUDGEMENT_RULES)


@lru_cache(maxsize=1)
def semantic_questions() -> dict[str, dict[str, str]]:
    if not QUESTIONS_PATH.is_file():
        return {}
    return yaml.safe_load(QUESTIONS_PATH.read_text(encoding="utf-8")) or {}


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
    asked = semantic_questions().get(rule["id"])
    if asked is None:
        if rule["id"] not in EXCLUDED_JUDGEMENT_RULES:
            raise KeyError(f"{QUESTIONS_PATH.name} has no question for {rule['id']}")
        # Excluded rules get no items; bank verify still judges their passages.
        return {
            "type": "noul",
            "rule_id": rule["id"],
            "prompt": rule["judgement_question"],
        }
    return {
        "type": "noul",
        "rule_id": rule["id"],
        "prompt": asked["question"],
        "yes_example": asked["yes_example"],
        "no_example": asked["no_example"],
    }


def mark_span(text: str, start: int, end: int) -> str:
    """`text` with text[start:end] marked [[like this]]."""
    if 0 <= start < end <= len(text):
        return text[:start] + "[[" + text[start:end] + "]]" + text[end:]
    return text


def _fenced_spans(text: str) -> list[tuple[int, int]]:
    """Offsets of fenced code blocks, fences included."""
    spans, start, pos = [], None, 0
    for line in text.splitlines(keepends=True):
        if re.match(r"[ \t]*(```|~~~)", line):
            if start is None:
                start = pos
            else:
                spans.append((start, pos + len(line)))
                start = None
        pos += len(line)
    if start is not None:
        spans.append((start, len(text)))
    return spans


def prose_words(text: str) -> int:
    """Words of prose in `text`. Fenced and indented code, headings, rules,
    table separators, directives, prompts, markdown link-reference
    definitions, lines that are only a URL, inline code, HTML tags, URLs, list
    markers and emphasis marks do not count; table cell text does."""
    lines = text.splitlines()
    kept, fenced = [], False
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r"(```|~~~)", s):
            fenced = not fenced
            continue
        if fenced or not s or re.match(r"( {4}|\t)", line):
            continue
        underline = i + 1 < len(lines) and re.fullmatch(
            r"[=~^`-]{3,}", lines[i + 1].strip()
        )
        if (
            underline
            or re.match(r"#{1,6}(\s|$)", s)
            or re.fullmatch(r"[\s|:=~^`*_+-]+", s)
            or s.startswith(("..", ">>>", "$ "))
            or re.match(r"\[[^\]]+\]:\s", s)
            or re.fullmatch(r"<?(?:[A-Za-z][A-Za-z0-9+.-]*://|www\.)\S+>?", s)
        ):
            continue
        s = re.sub(r"`[^`]*`", " ", s)
        s = re.sub(r"<[^>]*>", " ", s)
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"https?://\S+", " ", s)
        s = re.sub(r"^(?:[-*+>]|\d+[.)])\s+", "", s)
        kept.append(s)
    return len(re.findall(r"[A-Za-z][A-Za-z'\u2019-]*", " ".join(kept)))


def region_ok(text: str) -> bool:
    return prose_words(text) >= MIN_REGION_WORDS


def _prose_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """Paragraphs outside fenced code that hold enough prose for a region."""
    fences = _fenced_spans(text)
    return [
        (a, b, p)
        for a, b, p in paragraphs(text)
        if region_ok(p) and not any(fa < b and a < fb for fa, fb in fences)
    ]


def _pick_region(text: str, anchor: int, target: int) -> tuple[int, int] | None:
    """A deterministic prose region of `text`: the run of whole sentences
    inside one prose paragraph closest to `target` characters long and to
    `anchor`. The paragraph holding `anchor` is tried first, then the others
    by distance."""
    target = max(target, 1)
    candidates = sorted(
        _prose_paragraphs(text),
        key=lambda p: (not p[0] <= anchor <= p[1], abs(p[0] - anchor), p[0]),
    )
    for a, b, value in candidates:
        ss = sentences(text, a, b) or [(a, b, value)]
        runs = [
            (ss[i][0], ss[j][1])
            for i in range(len(ss))
            for j in range(i, len(ss))
            if region_ok(text[ss[i][0] : ss[j][1]])
        ]
        if runs:
            return min(
                runs,
                key=lambda r: (
                    abs(r[1] - r[0] - target) / target
                    + abs(r[0] - anchor) / max(len(text), 1),
                    r[0],
                ),
            )
    return None


def _relative_anchor(value: str, text: str, anchor: int) -> int:
    """`anchor`, a document offset, as an offset into the item's span `value`."""
    para = next((p for p in paragraphs(text) if p[0] <= anchor <= p[1]), None)
    if para:
        at = value.find(para[2])
        if at >= 0:
            return at + anchor - para[0]
    at = text.find(value)
    return min(max(anchor - at, 0), len(value)) if at >= 0 else 0


def _set_region(item: dict, region: tuple[int, int] | None) -> bool:
    """Mark state.text[start:end] as the item's region; False when there is
    no region or it holds fewer than MIN_REGION_WORDS words of prose."""
    if region is None:
        return False
    text = item["state"]["text"]
    start, end = region
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if not region_ok(text[start:end]):
        return False
    item["question"]["region"] = {"start": start, "end": end}
    return True


def _passage_region(item: dict, passage: str) -> tuple[int, int] | None:
    at = item["state"]["text"].find(passage)
    return (at, at + len(passage)) if at >= 0 else None


def _containing_sentences(text: str, span: str) -> tuple[int, int, str]:
    """The run of whole sentences of `text` that holds `span`, or (0, 0, "")."""
    at = text.find(span) if span else -1
    if at < 0:
        return 0, 0, ""
    stop = at + len(span)
    ss = [s for s in sentences(text, 0, len(text)) if s[0] < stop and at < s[1]]
    start, end = (ss[0][0], ss[-1][1]) if ss else (at, stop)
    return start, end, text[start:end]


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
    files: list[tuple[str, Path]], batch_size: int = 40, workers: int = 1
) -> dict[str, list[dict]]:
    out = defaultdict(list)
    if workers > 1 and len(files) > batch_size:
        chunks = [files[i : i + batch_size] for i in range(0, len(files), batch_size)]
        with ThreadPoolExecutor(workers) as pool:
            for found in pool.map(lambda c: _run_lint(c, batch_size), chunks):
                for name, rows in found.items():
                    out[name].extend(rows)
        return out
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
    g: str | None = None,
) -> dict | None:
    g = g or granularity(
        f"{role}:{source['id']}:{rule['id']}:{anchor}:{construction or ''}"
    )
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
        # Each role gets an equal share of the limit; a shortfall in one role
        # passes to the roles after it. Without the shares, the sorted
        # finding-confirmation strata filled the whole sample.
        roles = sorted({key[0] for key in strata})
        selected = []
        for n, role in enumerate(roles):
            quota = (limit - len(selected)) // (len(roles) - n)
            queues = []
            for key, values in sorted(strata.items()):
                if key[0] != role:
                    continue
                values.sort(
                    key=lambda row: (seed(f"17:{split}:{row['id']}"), row["id"])
                )
                queues.append(values)
            taken = []
            while len(taken) < quota and queues:
                remaining = []
                for values in queues:
                    if len(taken) < quota and values:
                        taken.append(values.pop(0))
                    if values:
                        remaining.append(values)
                queues = remaining
            selected += taken
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


# Bank constructions: verified bank passages (bank.py) injected into human host
# text at sentence, paragraph and document granularity. Finding confirmation
# gets real-defect items from bad passages and false-positive items from tricky
# ones (the rule fires on acceptable prose). Semantic detection gets true items
# from bad passages, and false items from good passages, near-miss hard
# negatives and clean host controls.
BANK_SPLIT_PERCENT = {
    "default": (("train", 55), ("dev", 15), ("calibration", 15), ("test", 15)),
    # Hard negatives are calibration material first.
    ("semantic-detection", "near"): (
        ("train", 35),
        ("dev", 15),
        ("calibration", 35),
        ("test", 15),
    ),
}
BANK_REPEATS = {"train": 5, "dev": 3, "calibration": 4, "test": 3}
BANK_USE = {
    ("finding-confirmation", "bad"): "real-defect",
    ("finding-confirmation", "tricky"): "false-positive",
    ("semantic-detection", "bad"): True,
    ("semantic-detection", "good"): False,
    ("semantic-detection", "near"): False,
}
# Draw weights among negative sources when the false class is trimmed.
FALSE_MIX = {"bank-good": 0.5, "bank-near": 0.3, "bank-control": 0.2}
# On a cross-split near-duplicate, the item in the lower-priority split goes.
SPLIT_PRIORITY = {"test": 3, "calibration": 2, "dev": 1, "train": 0}
NEAR_DUP_JACCARD = 0.5
_BLOCK_START = re.compile(r"^\s*(?:#|\||```|~~~|>|[-*+]\s|\d+[.)]\s|\.\. |<)")


def _signature(text: str, n: int) -> set[int]:
    return {hash(s) for s in shingles(text, n)}


def _near_pairs(
    sigs: dict[str, set[int]],
    threshold: float,
    group: dict[str, str] | None = None,
    max_postings: int = 2000,
):
    """Key pairs whose shingle sets reach the Jaccard threshold, found through
    an inverted index. With `group`, only pairs from different groups; each
    key then reads only the other groups' postings."""
    group = group or {}
    index: dict[tuple, list[str]] = defaultdict(list)
    for key, sig in sigs.items():
        for s in sig:
            index[(group.get(key), s)].append(key)
    groups = sorted({group.get(k) for k in sigs}, key=str)
    for key, sig in sigs.items():
        mine = group.get(key)
        shared: Counter = Counter()
        for g in groups:
            if group and g == mine:
                continue
            for s in sig:
                posting = index.get((g, s))
                if posting and len(posting) <= max_postings:
                    shared.update(posting)
        for other, n in shared.items():
            if other <= key:
                continue
            if n / (len(sig) + len(sigs[other]) - n) >= threshold:
                yield key, other


def bank_split(rows: list[dict], held: set[str]) -> dict[str, str]:
    """Split per near-duplicate cluster of kept bank passages, so no passage
    and none of its near copies reach two splits. Held-out rules go to test."""
    sigs = {r["id"]: _signature(r["text"], 3) for r in rows}
    parent = {k: k for k in sigs}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in _near_pairs(sigs, NEAR_DUP_JACCARD):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    members: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        members[find(r["id"])].append(r)
    out = {}
    for rep, group in members.items():
        first = min(group, key=lambda r: r["id"])
        split = "test"
        if not any(r["rule_id"] in held for r in group):
            ratios = BANK_SPLIT_PERCENT.get(
                (first["role"], first["kind"]), BANK_SPLIT_PERCENT["default"]
            )
            n, acc = seed(f"17:bank-split:{rep}") % 100, 0
            for split, pct in ratios:
                acc += pct
                if n < acc:
                    break
        for r in group:
            out[r["id"]] = split
    return out


def _host_paragraphs(text: str) -> list[int]:
    """Indexes of plain prose paragraphs among a host's first 20."""
    ok = []
    for i, (_, _, p) in enumerate(paragraphs(text)[:20]):
        if not 150 <= len(p) <= 1500 or _BLOCK_START.match(p) or "```" in p:
            continue
        if "\n    " in p or not re.search(r"[.!?][\"')\]]*$", p):
            continue
        if sum(c.isalpha() or c.isspace() for c in p) / len(p) < 0.85:
            continue
        ok.append(i)
    return ok


def _granularities(example: str) -> tuple[str, ...]:
    if "\n" in example:
        return ("paragraph", "document") if "\n\n" not in example else ("document",)
    single = len(sentences(example, 0, len(example))) == 1
    if single and (example[0].isupper() or example[0].isdigit()):
        return ("sentence", "paragraph", "document")
    return ("paragraph", "document")


def _inject(text: str, pi: int, example: str, where: int) -> tuple[str, int, int]:
    """The host prefix through the paragraph after `pi`, with the example
    inline after a sentence of paragraph `pi`, or as its own block after it."""
    ps = paragraphs(text)
    a, b, _ = ps[pi]
    end = ps[min(pi + 1, len(ps) - 1)][1]
    if "\n" in example:
        return text[:b] + "\n\n" + example + text[b:end], b + 2, end
    ss = sentences(text, a, b) or [(a, b, text[a:b])]
    cut = ss[where % len(ss)][1]
    return text[:cut] + " " + example + text[cut:end], cut + 1, end


def _draw(rows: list[dict], n: int) -> set[str]:
    """`n` rows by weighted round-robin over construction kinds, and within a
    kind round-robin over rules, in seeded order."""
    queues = {}
    by_kind: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for x in rows:
        by_kind[x["construction"]["kind"]][x["rule_id"]].append(x)
    for kind, rules in by_kind.items():
        pools = [
            sorted(rules[r], key=lambda x: seed(f"17:balance:{x['id']}"))
            for r in sorted(rules)
        ]
        order = []
        while any(pools):
            for pool in pools:
                if pool:
                    order.append(pool.pop(0))
        queues[kind] = order
    taken: Counter = Counter()
    chosen: set[str] = set()
    while len(chosen) < n and any(queues.values()):
        kind = min(
            (k for k in queues if queues[k]),
            key=lambda k: (taken[k] / FALSE_MIX.get(k, 1.0), k),
        )
        chosen.add(queues[kind].pop(0)["id"])
        taken[kind] += 1
    return chosen


def _bank_items(
    root: Path,
    humans: list[dict],
    human_splits: dict[str, str],
    texts: dict[str, str],
    rules: dict[str, dict],
    held: set[str],
    encoders,
) -> tuple[list[dict], dict]:
    bank = [r for r in read_jsonl(root / BANK_PATH) if r.get("kept")]
    report: Counter = Counter()
    pools: dict[tuple[str, str | None], list[dict]] = defaultdict(list)
    eligible = {}
    for h in sorted(humans, key=lambda h: h["id"]):
        if h["id"] in texts and (ps := _host_paragraphs(texts[h["id"]])):
            eligible[h["id"]] = ps
            pools[(human_splits[h["id"]], h.get("genre"))].append(h)
            pools[(human_splits[h["id"]], None)].append(h)
    plans = []
    for row in sorted(bank, key=lambda r: r["id"]):
        label = BANK_USE.get((row["role"], row["kind"]))
        if label is None or row["rule_id"] not in rules or not row.get("split"):
            continue
        split, example = row["split"], row["text"]
        pool = pools.get((split, row["genre"])) or pools.get((split, None)) or []
        allowed = _granularities(example)
        # A sentence-granularity item is the passage alone, so a passage is
        # used at sentence granularity at most once; later repeats cycle
        # through the wider granularities.
        wider = [g for g in allowed if g != "sentence"]
        base = seed(f"17:bank-host:{row['id']}")
        for r in range(min(BANK_REPEATS[split], len(pool))):
            host = pool[(base + r) % len(pool)]
            ps = eligible[host["id"]]
            pi = ps[seed(f"17:bank-p:{row['id']}:{r}") % len(ps)]
            if r < len(allowed):
                g = allowed[(base + r) % len(allowed)]
            else:
                g = wider[(base + r) % len(wider)]
            where = seed(f"17:bank-s:{row['id']}:{r}")
            new, start, end = _inject(texts[host["id"]], pi, example, where)
            plans.append(
                (row, r, host, g, new, start, start + len(example), end, label)
            )
            if row["role"] == "semantic-detection" and label is True:
                # A clean control: the same rule on an untouched host paragraph.
                chost = pool[(base + r + len(pool) // 2) % len(pool)]
                cps = eligible[chost["id"]]
                cpi = cps[seed(f"17:bank-cp:{row['id']}:{r}") % len(cps)]
                ctext = texts[chost["id"]]
                a, b, _ = paragraphs(ctext)[cpi]
                ss = sentences(ctext, a, b) or [(a, b, "")]
                anchor = ss[where % len(ss)][0]
                cend = paragraphs(ctext)[min(cpi + 1, len(paragraphs(ctext)) - 1)][1]
                plans.append(
                    (row, r, chost, g, ctext[:cend], anchor, anchor, cend, False)
                )
    report["planned"] = len(plans)
    # Finding confirmation needs the rule to fire inside the injected passage.
    work = root / ".cache/items/bank-input"
    work.mkdir(parents=True, exist_ok=True)
    files, names = [], {}
    for plan in plans:
        row, r, host, *_ = plan
        if row["role"] == "finding-confirmation":
            name = digest(f"{row['id']}:{r}:{host['id']}".encode())[:24]
            path = work / f"{name}.md"
            path.write_text(_lint_text(plan[4]), encoding="utf-8")
            files.append((name, path))
            names[(row["id"], r)] = f"{name}.md"
    found = _run_lint(files, workers=6)
    items = []
    for row, r, host, g, new, start, stop, end, label in plans:
        rule = rules[row["rule_id"]]
        control = start == stop
        kind = "bank-control" if control else f"bank-{row['kind']}"
        finding, anchor = None, start
        if row["role"] == "finding-confirmation":
            finding = next(
                (
                    f
                    for f in found.get(names[(row["id"], r)], [])
                    if f["rule_id"] == rule["id"]
                    and start
                    <= _offset(new, f.get("line", 1), f.get("column", 1))
                    < stop
                ),
                None,
            )
            if finding is None:
                report["dropped_rule_silent_in_context"] += 1
                continue
            anchor = _offset(new, finding.get("line", 1), finding.get("column", 1))
        construction = {
            "kind": kind,
            "bank_id": None if control else row["id"],
            "paired_bank_id": row["id"] if control else None,
            "bank_split": row["split"],
            "host_id": host["id"],
            "injected_start": None if control else start,
            "injected_end": None if control else stop,
            "repeat": r,
            "provenance": row["provenance"],
        }
        item = _make_item(
            root,
            role=row["role"],
            rule=rule,
            source=host,
            text=new,
            label=label,
            origin="construction",
            split=row["split"],
            kind=f"{kind}:{row['id']}:{r}",
            anchor=anchor,
            encoders=encoders,
            source_group=_source_group(host),
            finding=finding,
            construction=construction,
            g=g,
        )
        if item is None:
            report["dropped_span_budget"] += 1
            continue
        value = item["state"]["text"]
        if not control:
            at = value.find(row["text"])
            if at < 0:
                report["dropped_span_excludes_passage"] += 1
                continue
            if finding:
                # The flagged text must be the occurrence inside the passage.
                flagged = item["finding"]["matched_text"]
                pos = value.find(flagged, at)
                if pos < 0 or pos + len(flagged) > at + len(row["text"]):
                    report["dropped_flag_outside_passage"] += 1
                    continue
                for f in (item["finding"], item["question"]["finding"]):
                    f["start"], f["end"] = pos, pos + len(flagged)
        if row["role"] == "semantic-detection":
            # The region is the inserted passage; a clean control gets a host
            # region of about the paired passage's length.
            region = (
                _pick_region(
                    value, _relative_anchor(value, new, start), len(row["text"])
                )
                if control
                else _passage_region(item, row["text"])
            )
            if not _set_region(item, region):
                report[f"dropped_region_{kind}"] += 1
                continue
        if g == "document" and end < len(texts[host["id"]]):
            item["truncated"] = True
        item["rule_held_out"] = rule["id"] in held
        items.append(item)
    report["built"] = len(items)
    return items, dict(report)


def _dedup_constructions(
    items: list[dict], passages: dict[str, str]
) -> tuple[list[dict], dict]:
    """Drop constructions whose host span or injected passage near-duplicates
    (shingle Jaccard >= NEAR_DUP_JACCARD) a construction in another split."""
    cons = [x for x in items if x.get("label_origin") == "construction"]
    group = {x["id"]: x["split"] for x in cons}
    host_sigs, passage_sigs = {}, {}
    for x in cons:
        text = (x.get("state") or {}).get("text", "")
        passage = passages.get((x.get("construction") or {}).get("bank_id") or "")
        if passage:
            passage_sigs[x["id"]] = _signature(passage, 3)
            text = text.replace(passage, " ")
        if sig := _signature(text, 5):
            host_sigs[x["id"]] = sig
    drop: dict[str, str] = {}
    for sigs, reason in ((passage_sigs, "injected-passage"), (host_sigs, "host-span")):
        for a, b in _near_pairs(sigs, NEAR_DUP_JACCARD, group):
            loser = a if SPLIT_PRIORITY[group[a]] < SPLIT_PRIORITY[group[b]] else b
            drop.setdefault(loser, reason)
    by_id = {x["id"]: x for x in cons}
    report = dict(
        Counter(
            f"{by_id[i]['split']}|{by_id[i]['role']}|{reason}"
            for i, reason in drop.items()
        )
    )
    return [x for x in items if x["id"] not in drop], report


def _balance_constructions(items: list[dict]) -> tuple[list[dict], dict]:
    """Trim bank constructions of the majority class so every split holds
    about as many true as false (finding confirmation: real-defect as
    false-positive) constructions per role. Other constructions stay."""
    classes: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for x in items:
        if x.get("label_origin") == "construction":
            classes[(x["split"], x["role"])][json.dumps(x["label"])].append(x)
    drop: set[str] = set()
    for by_label in classes.values():
        if len(by_label) < 2:
            continue
        target = min(len(v) for v in by_label.values())
        for rows in by_label.values():
            bank = [
                x
                for x in rows
                if (x.get("construction") or {}).get("kind", "").startswith("bank-")
            ]
            keep = _draw(bank, max(0, target - (len(rows) - len(bank))))
            drop |= {x["id"] for x in bank if x["id"] not in keep}
    kept = [x for x in items if x["id"] not in drop]
    report = {
        split: {
            role: {
                str(json.loads(label)): len(rows) - sum(x["id"] in drop for x in rows)
                for label, rows in sorted(classes[(split, role)].items())
            }
            for role in ("finding-confirmation", "semantic-detection")
            if (split, role) in classes
        }
        for split in SPLITS
    }
    return kept, report


def _add_bank_constructions(
    root: Path,
    items: list[dict],
    humans: list[dict],
    generated: list[dict],
    texts: dict[str, str],
    lint_rules: list[dict],
    judge_rules: list[dict],
    held: set[str],
    encoders,
) -> tuple[list[dict], dict]:
    _, human_splits = assign_splits(humans, generated)
    rules = {r["id"]: r for r in lint_rules + judge_rules}
    bank_items, report = _bank_items(
        root, humans, human_splits, texts, rules, held, encoders
    )
    ids = {x["id"] for x in items}
    items = items + [x for x in bank_items if x["id"] not in ids]
    passages = {r["id"]: r["text"] for r in read_jsonl(root / BANK_PATH)}
    items, report["near_duplicate_drops"] = _dedup_constructions(items, passages)
    items, report["construction_classes"] = _balance_constructions(items)
    report["bank_constructions"] = dict(
        Counter(
            f"{x['split']}|{x['role']}|{x['construction']['kind']}"
            for x in items
            if (x.get("construction") or {}).get("kind", "").startswith("bank-")
        )
    )
    return items, report


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
    root_rows = list(read_jsonl(root / "sources/human.jsonl"))
    generated = list(read_jsonl(root / "generated/manifest.jsonl"))
    encoders, tokenizer_digests = load_tokenizers()
    lint_rules, (judge_rules, held_judge) = _rules_current(), semantic_rules()
    held_lint = held_out(lint_rules)
    merged, bank_report = _add_bank_constructions(
        root,
        merged,
        root_rows,
        generated,
        _read_texts(root, root_rows),
        lint_rules,
        judge_rules,
        held_lint | held_judge,
        encoders,
    )
    merged.sort(
        key=lambda row: (
            row["split"],
            row["role"],
            row["rule_id"],
            row["source_id"],
            row["id"],
        )
    )
    merged, dropped = _sample_adjudication(merged, {"test": 600, "calibration": 300})
    _externalize_states(root, merged)
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
        "constructions": bank_report,
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
    judgement_rules, held_judge = semantic_rules()
    by_lint = {r["id"]: r for r in lint_rules}
    by_judge = {r["id"]: r for r in judgement_rules}
    held_lint = held_out(lint_rules)
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
    region_report: Counter = Counter()
    region_lengths: dict[str, list[int]] = defaultdict(list)
    for r in read_jsonl(root / BANK_PATH):
        if r.get("kept") and r["role"] == "semantic-detection":
            region_lengths[r["rule_id"]].append(len(r["text"]))
    for lengths in region_lengths.values():
        lengths.sort()
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
        prose = _prose_paragraphs(text)
        for rule in selected_rules:
            if not prose:
                region_report["unseeded|no-prose-paragraph"] += 1
                continue
            # The anchor paragraph is a seeded draw among prose paragraphs; a
            # span whose region holds too little prose is resampled from the
            # next one.
            order = sorted(
                prose,
                key=lambda p: (
                    seed(f"17:anchor:{source_id}:{rule['id']}:{p[0]}"),
                    p[0],
                ),
            )
            lengths = region_lengths.get(rule["id"]) or [DEFAULT_REGION_CHARS]
            target = lengths[seed(f"17:region:{source_id}:{rule['id']}") % len(lengths)]
            for attempt, (anchor, _, _) in enumerate(order[:REGION_ATTEMPTS]):
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
                if item and _set_region(
                    item,
                    _pick_region(
                        item["state"]["text"],
                        _relative_anchor(item["state"]["text"], text, anchor),
                        target,
                    ),
                ):
                    item["rule_held_out"] = rule["id"] in held_judge
                    items.append(item)
                    if attempt:
                        region_report["unseeded|resampled"] += 1
                    break
            else:
                region_report["unseeded|dropped"] += 1
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
        ps = _prose_paragraphs(base)
        if not ps:
            continue
        a, b, para = ps[seed(f"17:judgespan:{rule['id']}") % len(ps)]
        ex = exs[0]
        bad = (ex.get("bad") or "").strip()
        if not bad:
            continue
        g = granularity(f"judgeseed:{rule['id']}:{host['id']}")
        seeded = base[:b].rstrip() + " " + bad + base[b:]
        # The positive's anchor is the inserted example itself, so a sentence
        # span is the example and not the host sentence before it.
        anchor = len(base[:b].rstrip()) + 1
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
            if not item:
                continue
            # The positive's region is the example; the control's is host
            # text of about its length at the same place, the paragraph end.
            value = item["state"]["text"]
            region = (
                _passage_region(item, bad)
                if label
                else _pick_region(value, _relative_anchor(value, base, b), len(bad))
            )
            if not _set_region(item, region):
                region_report[f"judgement-example:{int(label)}|dropped"] += 1
                continue
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
    records = [json.loads(line) for line in gold[1:]]
    # A gold positive's region is the sentence holding its defect span; the
    # region of a control row is a seeded sentence run of the median length.
    defect_sentences = sorted(
        len(_containing_sentences(r["text"], r["defect_span"])[2])
        for r in records
        if r.get("defect_span") and r["defect_span"] in r["text"]
    )
    gold_target = (
        defect_sentences[len(defect_sentences) // 2]
        if defect_sentences
        else DEFAULT_REGION_CHARS
    )
    control_index = 0
    for n, record in enumerate(records):
        if shard and n % shard_count != shard_index:
            continue
        content = record["text"]
        if record.get("rule_id"):
            if record["rule_id"] not in by_judge:
                continue
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
            ss = sentences(content, 0, len(content)) or [(0, len(content), content)]
            anchor = (
                pos
                if pos >= 0
                else ss[seed(f"17:gold-anchor:{fake['id']}") % len(ss)][0]
            )
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
                anchor=anchor,
                encoders=encoders,
                source_group=f"gold-v1:{rule['id']}",
                construction={
                    "kind": "gold-v1",
                    "control": not bool(record.get("rule_id")),
                    "defect_start": pos if pos >= 0 else None,
                    "defect_end": pos + len(defect) if pos >= 0 else None,
                },
            )
            if not item:
                continue
            value = item["state"]["text"]
            if pos >= 0:
                start, end, _ = _containing_sentences(value, defect)
                region = (start, end) if end > start else None
            else:
                region = _pick_region(
                    value, _relative_anchor(value, content, anchor), gold_target
                )
            if not _set_region(item, region):
                region_report[f"gold-v1:{int(label)}|dropped"] += 1
                continue
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
            "semantic_regions": dict(region_report),
        }
    items, bank_report = _add_bank_constructions(
        root,
        items,
        humans,
        generated,
        texts,
        lint_rules,
        judgement_rules,
        held_lint | held_judge,
        encoders,
    )
    items.sort(key=lambda x: (x["split"], x["role"], x["rule_id"], x["id"]))
    counts = {
        "human_documents": len(humans),
        "generated_documents": len(generated),
        "lint_findings": sum(len(x) for x in findings.values()),
        "gold_v1_rows": len(gold) - 1,
        "built_items": len(items),
        "semantic_regions": dict(region_report),
        "constructions": bank_report,
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
