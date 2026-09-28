"""Build the pilot validation set from slopvac rule examples. Labels come only from construction.

Each rule example pair {bad, good} yields:
  * two `noul` items: bad -> true, good -> false;
  * two `choice` items (real-defect / no-defect / insufficient-context): bad -> real-defect, good -> no-defect;
and each `bad` example also yields one cross-rule hard negative: the same sentence asked about an
unrelated rule Y (a different category, same split, and Y's own regex does not match the sentence)
-> false. That gives noul positives:negatives = 1:2.

Splits are grouped by rule id (category.rule), shuffled with seed 17: 60% train / 15% calibration /
25% test of the rules that have examples. Output: data/<split>.jsonl plus
results/dataset-manifest.json with SHA-256 digests and the portable-profile check.

    uv run --no-project --with-requirements requirements-harness.txt python build_dataset.py
"""

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import regex
import yaml

PILOT = Path(__file__).resolve().parent
REPO = PILOT.parents[1]
RULES_DIR = REPO / "packages" / "slopvac-lint" / "src" / "slopvac" / "rules"
DATA = PILOT / "data"
RESULTS = PILOT / "results"
SEED = 17
SPLITS = (("train", 0.60), ("calibration", 0.15), ("test", 0.25))
PROFILE_MAX_TOKENS = 1024
PROFILE_MAX_OPTIONS = 8

CHOICE_CRITERIA = {
    "real-defect": "The text exhibits this defect.",
    "no-defect": "The text does not exhibit this defect.",
    "insufficient-context": "The text is too short or ambiguous to decide.",
}
# Tokenizers used for the 1,024-token profile check: Laya's ModernBERT and Kev's Qwen3.5 vocabulary.
PROFILE_TOKENIZERS = (
    (
        "convaiinnovations/laya-typed-decisions",
        "1a793eb568e6718f15941d08f85432581df534e3",
        "tokenizer/tokenizer.json",
    ),
    (
        "jaredpalmer/kev-0.8b",
        "9a45d25eb2ab761841196625383fa1dff0e56c1e",
        "tokenizer.json",
    ),
)

_QUOTED_PLACEHOLDER = regex.compile(r"""["'“‘]\s*\{[a-z_]+\}\s*["'”’]""")
_PLACEHOLDER = regex.compile(r"\{[a-z_]+\}")
_LABEL = regex.compile(r"^([^:{}.]{3,60}):\s")
_EMPTY_PARENS = regex.compile(r"\(\s*(?:and|or|,|\s)*\)")
_DANGLING = regex.compile(
    r"(?:\b(?:and|or|as|of|than|use|instead of|by|to)|:)\s*(?:[.;]|$)|\bas but not as\b|\buse as an?\b",
    regex.IGNORECASE,
)


def _clean(text, numeric=False):
    text = _QUOTED_PLACEHOLDER.sub("", text)
    text = text.replace("{value}", "N")
    text = _PLACEHOLDER.sub("N" if numeric else "", text)
    text = _EMPTY_PARENS.sub("", text)
    text = regex.sub(r"\s{2,}", " ", text)
    return regex.sub(r"\s+([.,;:])", r"\1", text).strip(" -:")


def defect_description(rule):
    """Short defect description from the rule's message, falling back to its fix; no placeholders.

    "label: {match} -- advice" messages give the label; sentence messages lose their placeholders
    and keep at most two sentences; a message whose subject was the placeholder is read as
    "text that ..."; a message that the removal leaves ungrammatical falls back to the rule's fix.
    """
    message = (rule.get("message") or "").strip()
    label = _LABEL.match(message)
    if label and "{" not in label.group(1) and len(label.group(1).split()) <= 6:
        return label.group(1).strip()
    text = _clean(message.split(" -- ")[0], numeric=rule.get("kind") == "metric")
    if text[:1].islower():
        text = "text that " + text
    if len(regex.findall(r"\p{L}+", text)) < 4 or _DANGLING.search(text):
        return "fixed by: " + _clean(rule.get("fix") or "").rstrip(".")
    return (
        ". ".join(s.strip() for s in regex.split(r"(?<=\.)\s+", text)[:2])
        .replace("..", ".")
        .rstrip(".")
    )


def noul_question(rule_name, description):
    return f"Does the text contain this defect: {rule_name} — {description}?"


def choice_question(rule_name, description):
    return f"Is this defect present in the text: {rule_name} — {description}?"


def load_rules():
    rules = []
    for path in sorted(RULES_DIR.glob("*.yml")):
        for doc in yaml.safe_load_all(path.read_text()):
            if not doc:
                continue
            for rule in doc.get("rules", []):
                pairs = [(e["bad"], e["good"]) for e in rule.get("examples") or []]
                rules.append(
                    {
                        "rule_id": f"{doc['id']}.{rule['id']}",
                        "category": doc["id"],
                        "name": rule["name"],
                        "description": defect_description(rule),
                        "pattern": rule.get("pattern"),
                        "ignore_case": bool(rule.get("ignore_case")),
                        "pairs": pairs,
                        "source_file": path.name,
                    }
                )
    return rules


def pattern_matches(rule, text):
    if not rule["pattern"]:
        return False
    flags = regex.IGNORECASE if rule["ignore_case"] else 0
    try:
        return regex.search(rule["pattern"], text, flags) is not None
    except regex.error:
        return True  # an unparseable pattern cannot certify the negative; skip that pairing


def split_rules(rules):
    ids = sorted(r["rule_id"] for r in rules if r["pairs"])
    random.Random(SEED).shuffle(ids)
    n = len(ids)
    n_train = round(n * SPLITS[0][1])
    n_cal = round(n * SPLITS[1][1])
    return {
        "train": set(ids[:n_train]),
        "calibration": set(ids[n_train : n_train + n_cal]),
        "test": set(ids[n_train + n_cal :]),
    }


def build_items(rules, split_ids, split):
    rng = random.Random(f"{SEED}:{split}")
    members = [r for r in rules if r["rule_id"] in split_ids]
    items = []

    def add(kind, rule, state, label, source, pair_index, asked):
        q = (
            noul_question(asked["name"], asked["description"])
            if kind == "noul"
            else choice_question(asked["name"], asked["description"])
        )
        item = {
            "id": f"{split}:{kind}:{source}:{rule['rule_id']}:{pair_index}"
            + (f":as:{asked['rule_id']}" if asked is not rule else ""),
            "split": split,
            "kind": kind,
            "source": source,
            "state_rule": rule["rule_id"],
            "asked_rule": asked["rule_id"],
            "state": state,
            "question": {"type": kind, "instructions": q},
            "label": label,
        }
        if kind == "choice":
            item["question"]["criteria"] = dict(CHOICE_CRITERIA)
        items.append(item)

    for rule in members:
        for i, (bad, good) in enumerate(rule["pairs"]):
            add("noul", rule, bad, True, "bad", i, rule)
            add("noul", rule, good, False, "good", i, rule)
            add("choice", rule, bad, "real-defect", "bad", i, rule)
            add("choice", rule, good, "no-defect", "good", i, rule)
    # Cross-rule hard negatives: one per bad example, capped at the positive count (1:2 overall).
    for rule in members:
        for i, (bad, _good) in enumerate(rule["pairs"]):
            candidates = [
                y
                for y in members
                if y["category"] != rule["category"] and not pattern_matches(y, bad)
            ]
            if not candidates:
                continue
            add("noul", rule, bad, False, "cross", i, rng.choice(candidates))
    return items


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def profile_check(items):
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    report = {}
    for repo, rev, filename in PROFILE_TOKENIZERS:
        tok = Tokenizer.from_file(hf_hub_download(repo, filename, revision=rev))
        worst = 0
        for it in items:
            q = it["question"]
            text = (
                it["state"]
                + "\n"
                + q["instructions"]
                + "".join(f"\n{k}: {v}" for k, v in q.get("criteria", {}).items())
            )
            worst = max(worst, len(tok.encode(text).ids))
        report[f"{repo}@{rev}"] = {
            "max_state_plus_question_tokens": worst,
            "within_1024": worst <= PROFILE_MAX_TOKENS,
        }
    max_options = max(len(it["question"].get("criteria", {})) for it in items)
    report["max_options"] = max_options
    report["within_8_options"] = max_options <= PROFILE_MAX_OPTIONS
    return report


def main():
    rules = load_rules()
    splits = split_rules(rules)
    DATA.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    all_items, files = [], {}
    for split, _ in SPLITS:
        items = build_items(rules, splits[split], split)
        body = "".join(canonical(it) + "\n" for it in items)
        path = DATA / f"{split}.jsonl"
        path.write_text(body)
        counts = Counter((it["kind"], str(it["label"])) for it in items)
        files[split] = {
            "path": f"data/{split}.jsonl",
            "sha256": hashlib.sha256(body.encode()).hexdigest(),
            "items": len(items),
            "rules": len(splits[split]),
            "rule_ids_sha256": hashlib.sha256(
                "\n".join(sorted(splits[split])).encode()
            ).hexdigest(),
            "counts": {f"{k}={v}": n for (k, v), n in sorted(counts.items())},
        }
        all_items += items
    for a, b in (("train", "calibration"), ("train", "test"), ("calibration", "test")):
        assert not splits[a] & splits[b], (a, b)
    rules_digest = hashlib.sha256(
        b"".join(p.read_bytes() for p in sorted(RULES_DIR.glob("*.yml")))
    ).hexdigest()
    manifest = {
        "builder": "scripts/judge-pilot/build_dataset.py",
        "seed": SEED,
        "splits": dict(SPLITS),
        "rules_source": "packages/slopvac-lint/src/slopvac/rules/*.yml",
        "rules_source_sha256": rules_digest,
        "rules_total": len(rules),
        "rules_with_examples": sum(1 for r in rules if r["pairs"]),
        "example_pairs": sum(len(r["pairs"]) for r in rules),
        "choice_criteria": CHOICE_CRITERIA,
        "files": files,
        "portable_profile": profile_check(all_items),
        "descriptions": {r["rule_id"]: r["description"] for r in rules if r["pairs"]},
    }
    (RESULTS / "dataset-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        json.dumps(
            {
                k: {kk: vv for kk, vv in v.items() if kk != "path"}
                for k, v in files.items()
            },
            indent=1,
        )
    )
    print(json.dumps(manifest["portable_profile"], indent=1))


if __name__ == "__main__":
    main()
