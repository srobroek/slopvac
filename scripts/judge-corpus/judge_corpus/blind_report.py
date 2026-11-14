"""REPORT-blind.md: does lint, and do the judges, separate human from generated
blind documents?

Per document (blind.py build directory, docs.jsonl and findings.jsonl):

- lint rate: lint findings per 100 words (whitespace-separated; items.prose_words
  drops indented lines, which leaves RFC text with almost no words);
- confirmed rate: findings whose finding-confirmation item the judge calls a
  real defect with p >= THRESHOLD, per 100 words (p is the mean of the
  forward and reversed criteria orders; a finding without an item is not
  confirmed);
- semantic yes rate: the share of the document's semantic-detection items
  with p(yes) >= THRESHOLD, and the mean p(yes).

Probabilities are the raw served distributions from the eval predictions
(results/<campaign>/<arm>/results/predictions/<arm>.jsonl). Separation is the
AUC of a score for generated (positive) against human documents, with ties at
one half, and a 95% percentile interval from a cluster bootstrap that
resamples human sources together with their generated matches. Per genre
compares the genre's documents; per vendor and tier compares the vendor's or
tier's generated documents with the human documents they were matched to.
The paired win rate is the share of generated documents scoring above their
own human source (ties count one half).
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from .blind import UNLABELLED, blind_root
from .common import read_jsonl

THRESHOLD = 0.5
REPS = 2000
RULE_REPS = 1000
SEED = 17


def auc(scores: list[float], positive: list[bool]) -> float | None:
    """Mann-Whitney AUC with average ranks for ties."""
    pairs = sorted(zip(scores, positive))
    n_pos = sum(positive)
    n_neg = len(pairs) - n_pos
    if not n_pos or not n_neg:
        return None
    rank_sum, i = 0.0, 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        average = (i + j) / 2 + 1
        rank_sum += average * sum(1 for k in range(i, j + 1) if pairs[k][1])
        i = j + 1
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def cluster_ci(
    scores: list[float], positive: list[bool], clusters: list[str], reps: int
) -> tuple[float | None, float | None]:
    groups: dict[str, list[int]] = defaultdict(list)
    for i, c in enumerate(clusters):
        groups[c].append(i)
    keys = sorted(groups)
    rng = random.Random(SEED)
    values = []
    for _ in range(reps):
        idx = [i for k in rng.choices(keys, k=len(keys)) for i in groups[k]]
        value = auc([scores[i] for i in idx], [positive[i] for i in idx])
        if value is not None:
            values.append(value)
    if not values:
        return None, None
    values.sort()
    return values[int(0.025 * len(values))], values[
        min(len(values) - 1, int(0.975 * len(values)))
    ]


def paired_win_rate(docs: list[dict], score: dict[str, float]) -> float | None:
    human = {
        d["doc_id"]: score[d["doc_id"]] for d in docs if d["provenance"] == "human"
    }
    wins = [
        1.0
        if score[d["doc_id"]] > human[d["source_id"]]
        else 0.5
        if score[d["doc_id"]] == human[d["source_id"]]
        else 0.0
        for d in docs
        if d["provenance"] == "generated" and d["source_id"] in human
    ]
    return sum(wins) / len(wins) if wins else None


def _load_predictions(
    path: Path, item_ids: set[str]
) -> tuple[dict[str, float], Counter]:
    """item id -> p(real-defect) (mean over criteria orders) or p(yes)."""
    sums: dict[str, list[float]] = defaultdict(list)
    counts: Counter = Counter()
    for rec in read_jsonl(path):
        if rec["id"] not in item_ids:
            counts["not_blind"] += 1
            continue
        if rec.get("label_origin") not in (None, UNLABELLED):
            counts["unexpected_label_origin"] += 1
        answer = rec.get("answer")
        if rec.get("status") != 200 or not answer:
            counts["errors"] += 1
            continue
        if rec["kind"] == "noul":
            sums[rec["id"]].append(float(answer["noul"]))
        else:
            sums[rec["id"]].append(float(answer["probabilities"]["real-defect"]))
    counts["items_predicted"] = len(sums)
    return {k: sum(v) / len(v) for k, v in sums.items()}, counts


def _doc_scores(
    docs: list[dict],
    findings: list[dict],
    items: list[dict],
    p: dict[str, float] | None,
) -> dict[str, dict[str, float]]:
    """score name -> doc id -> value."""
    words = {d["doc_id"]: max(1, d["word_count"]) for d in docs}
    lint = Counter(f["doc_id"] for f in findings)
    out: dict[str, dict[str, float]] = {
        "lint rate": {d: 100 * lint[d] / w for d, w in words.items()}
    }
    if p is None:
        return out
    confirmed = Counter(
        f["doc_id"]
        for f in findings
        if f.get("item_id") and p.get(f["item_id"], 0.0) >= THRESHOLD
    )
    out["confirmed rate"] = {d: 100 * confirmed[d] / w for d, w in words.items()}
    sem: dict[str, list[float]] = defaultdict(list)
    for item in items:
        if item["role"] == "semantic-detection" and item["id"] in p:
            sem[item["doc_id"]].append(p[item["id"]])
    out["semantic yes rate"] = {
        d: (sum(x >= THRESHOLD for x in sem[d]) / len(sem[d])) if sem[d] else 0.0
        for d in words
    }
    out["semantic mean p"] = {
        d: (sum(sem[d]) / len(sem[d])) if sem[d] else 0.0 for d in words
    }
    return out


def _fmt(value: float | None, digits: int = 3) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def _sep(docs: list[dict], score: dict[str, float], reps: int = REPS) -> dict:
    s = [score[d["doc_id"]] for d in docs]
    y = [d["provenance"] == "generated" for d in docs]
    clusters = [d["source_id"] for d in docs]
    value = auc(s, y)
    lo, hi = cluster_ci(s, y, clusters, reps) if value is not None else (None, None)
    human = [v for v, g in zip(s, y) if not g]
    gen = [v for v, g in zip(s, y) if g]
    return {
        "n_human": len(human),
        "n_generated": len(gen),
        "human_mean": sum(human) / len(human) if human else None,
        "generated_mean": sum(gen) / len(gen) if gen else None,
        "auc": value,
        "ci": (lo, hi),
        "paired_win_rate": paired_win_rate(docs, score),
    }


def _row(label: str, sep: dict) -> str:
    lo, hi = sep["ci"]
    return (
        f"| {label} | {sep['n_human']} | {sep['n_generated']} | {_fmt(sep['human_mean'])} | "
        f"{_fmt(sep['generated_mean'])} | {_fmt(sep['auc'])} | [{_fmt(lo)}, {_fmt(hi)}] | "
        f"{_fmt(sep['paired_win_rate'])} |"
    )


HEADER = (
    "| {first} | human docs | generated docs | human mean | generated mean | AUC | 95% CI | paired win rate |\n"
    "|---|---|---|---|---|---|---|---|"
)


def _matched(docs: list[dict], keep) -> list[dict]:
    """Generated documents passing `keep` and the human documents they match."""
    gens = [d for d in docs if d["provenance"] == "generated" and keep(d)]
    sources = {d["source_id"] for d in gens}
    return [
        d for d in docs if d["provenance"] == "human" and d["doc_id"] in sources
    ] + gens


def report(
    root: Path,
    *,
    build_id: str,
    predictions: list[str],
    out: Path | None = None,
    lint_only: bool = False,
) -> dict:
    build = blind_root(root) / "builds" / build_id
    manifest = json.loads((build / "build-manifest.json").read_text())
    docs = list(read_jsonl(build / "docs.jsonl"))
    findings = [f for f in read_jsonl(build / "findings.jsonl")]
    items = list(read_jsonl(build / "items.jsonl"))
    item_ids = {i["id"] for i in items}
    arms: dict[str, dict[str, dict[str, float]]] = {}
    item_p: dict[str, dict[str, float]] = {}
    coverage: dict[str, dict] = {}
    if not lint_only:
        for spec in predictions:
            name, _, path = spec.rpartition("=")
            path_obj = Path(path)
            name = name or path_obj.stem
            p, counts = _load_predictions(path_obj, item_ids)
            counts["items_without_prediction"] = len(item_ids - set(p))
            coverage[name] = dict(counts)
            arms[name] = _doc_scores(docs, findings, items, p)
            item_p[name] = p
    lint_scores = _doc_scores(docs, findings, items, None)["lint rate"]
    tiny = len(docs) < 60
    lines = [
        f"# Blind human-versus-generated report: {build_id}",
        "",
        f"Documents: {manifest['documents']}. Findings: {manifest['findings']}. Items: {manifest['items_by_role']}. "
        f"Lint: {manifest['lint_root']} at {manifest['lint_commit'][:10]}.",
        "",
    ]
    if tiny:
        lines += [
            f"**Tiny set ({len(docs)} documents): a smoke check of the pipeline, not a measurement. The intervals are wide.**",
            "",
        ]
    lines += [
        "AUC is P(generated scores above human), ties counted one half; 0.5 is no separation. "
        "The 95% CI is a cluster bootstrap over human sources with their generated matches "
        f"({REPS} resamples, seed {SEED}). The paired win rate compares each generated document "
        f"with its own human source. Judged scores use raw served probabilities with threshold {THRESHOLD}. "
        "Rates are per 100 words.",
        "",
        "## Separation",
        "",
        HEADER.format(first="score"),
        _row("lint rate (lint only)", _sep(docs, lint_scores)),
    ]
    for name, scores in arms.items():
        for score_name in ("confirmed rate", "semantic yes rate", "semantic mean p"):
            lines.append(_row(f"{score_name}, {name}", _sep(docs, scores[score_name])))
    if coverage:
        lines += [
            "",
            "Prediction coverage per arm: " + json.dumps(coverage, sort_keys=True),
        ]
    for title, field in (
        ("genre", "genre"),
        ("generator vendor", "vendor"),
        ("generator tier", "tier"),
    ):
        lines += ["", f"## By {title}", ""]
        lines.append(HEADER.format(first=f"{title} / score"))
        values = sorted({d[field] for d in docs if d.get(field)})
        for value in values:
            if field == "genre":
                subset = [d for d in docs if d["genre"] == value]
            else:
                subset = _matched(docs, lambda d, v=value, f=field: d[f] == v)
            lines.append(_row(f"{value}: lint rate", _sep(subset, lint_scores)))
            for name, scores in arms.items():
                lines.append(
                    _row(
                        f"{value}: confirmed rate, {name}",
                        _sep(subset, scores["confirmed rate"]),
                    )
                )
                lines.append(
                    _row(
                        f"{value}: semantic mean p, {name}",
                        _sep(subset, scores["semantic mean p"]),
                    )
                )
    words = {d["doc_id"]: max(1, d["word_count"]) for d in docs}
    lines += [
        "",
        "## Per lint rule",
        "",
        "Score: the rule's findings per 100 words. Rules that fired on at least one document.",
        "",
        "| rule | held out | human docs firing | generated docs firing | AUC | 95% CI |"
        + "".join(f" confirmed AUC, {name} |" for name in arms),
        "|---|---|---|---|---|---|" + "---|" * len(arms),
    ]
    by_rule: dict[str, Counter] = defaultdict(Counter)
    held = {}
    for f in findings:
        by_rule[f["rule_id"]][f["doc_id"]] += 1
        held[f["rule_id"]] = f.get("rule_held_out")
    provenance = {d["doc_id"]: d["provenance"] for d in docs}
    rule_rows = []
    for rule, per_doc in by_rule.items():
        score = {d: 100 * per_doc[d] / w for d, w in words.items()}
        sep = _sep(docs, score, RULE_REPS)
        firing = Counter(provenance[d] for d in per_doc)
        cells = []
        for name in arms:
            p = item_p[name]
            confirmed = Counter(
                f["doc_id"]
                for f in findings
                if f["rule_id"] == rule
                and f.get("item_id")
                and p.get(f["item_id"], 0.0) >= THRESHOLD
            )
            cells.append(
                _fmt(
                    auc(
                        [
                            100 * confirmed[d["doc_id"]] / words[d["doc_id"]]
                            for d in docs
                        ],
                        [d["provenance"] == "generated" for d in docs],
                    )
                )
            )
        rule_rows.append(
            (
                -(abs((sep["auc"] or 0.5) - 0.5)),
                rule,
                f"| {rule} | {'yes' if held.get(rule) else 'no'} | {firing['human']} | {firing['generated']} | "
                f"{_fmt(sep['auc'])} | [{_fmt(sep['ci'][0])}, {_fmt(sep['ci'][1])}] |"
                + "".join(f" {c} |" for c in cells),
            )
        )
    lines += [r for _, _, r in sorted(rule_rows)]
    for name in arms:
        lines += [
            "",
            f"## Per semantic rule, {name}",
            "",
            "Score: the document's mean p(yes) for the rule over its regions.",
            "",
            "| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |",
            "|---|---|---|---|---|---|",
        ]
        per_rule: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        rule_held = {}
        p = item_p[name]
        for item in items:
            if item["role"] == "semantic-detection" and item["id"] in p:
                per_rule[item["rule_id"]][item["doc_id"]].append(p[item["id"]])
                rule_held[item["rule_id"]] = item.get("rule_held_out")
        sem_rows = []
        for rule, per_doc in per_rule.items():
            covered = [d for d in docs if per_doc.get(d["doc_id"])]
            score = {
                d["doc_id"]: sum(per_doc[d["doc_id"]]) / len(per_doc[d["doc_id"]])
                for d in covered
            }
            sep = _sep(covered, score, RULE_REPS)
            yes = {
                prov: [
                    x >= THRESHOLD
                    for d in covered
                    if d["provenance"] == prov
                    for x in per_doc[d["doc_id"]]
                ]
                for prov in ("human", "generated")
            }
            rate = {k: (sum(v) / len(v) if v else None) for k, v in yes.items()}
            sem_rows.append(
                (
                    -(abs((sep["auc"] or 0.5) - 0.5)),
                    rule,
                    f"| {rule} | {'yes' if rule_held.get(rule) else 'no'} | {_fmt(rate['human'])} | "
                    f"{_fmt(rate['generated'])} | {_fmt(sep['auc'])} | [{_fmt(sep['ci'][0])}, {_fmt(sep['ci'][1])}] |",
                )
            )
        lines += [r for _, _, r in sorted(sem_rows)]
    path = out or build / "REPORT-blind.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    headline = _sep(docs, lint_scores)
    return {
        "report": str(path),
        "documents": dict(Counter(d["provenance"] for d in docs)),
        "tiny": tiny,
        "lint_rate_auc": headline["auc"],
        "lint_rate_ci95": headline["ci"],
        "lint_rate_means": {
            "human": headline["human_mean"],
            "generated": headline["generated_mean"],
        },
        "lint_rate_paired_win_rate": headline["paired_win_rate"],
        "arms": coverage,
    }
