"""Corpus co-occurrence measurement for claim C6 (cluster gate keyed on categories).

Read-only against the checkout. Writes only under the work dir.
Corpus B (model-authored session prose) is local to the machine that ran the study and is not
in the repository; the numbers it produced are recorded in cooccurrence.json.
Environment: SLOPVAC_CHECKOUT (repo root), SLOPVAC_RESEARCH_WORK (scratch), SLOPVAC_SESSION_CORPUS.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import pathlib
import shutil
import statistics
import subprocess
import sys
from collections import Counter, defaultdict

CHECKOUT = pathlib.Path(os.environ.get("SLOPVAC_CHECKOUT", pathlib.Path(__file__).resolve().parents[6]))
WORK = pathlib.Path(os.environ.get("SLOPVAC_RESEARCH_WORK", pathlib.Path.home() / "tmp/slopvac-rubric-research/work/corpus"))
CONFIG = CHECKOUT / "slopvac.toml"
SESSIONS = pathlib.Path(os.environ.get("SLOPVAC_SESSION_CORPUS", pathlib.Path.home() / ".omp/agent/sessions"))


def lint(targets: list[str], cwd: pathlib.Path, extra: list[str] = ()) -> dict:
    cmd = [
        "uv", "run", "--project", str(CHECKOUT / "packages/slopvac-lint"), "slopvac", "lint",
        "--profile", "strict", "--format", "json", "--config", str(CONFIG), *extra, *targets,
    ]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = proc.stdout
    if not out.strip():
        sys.stderr.write(proc.stderr[-2000:])
        raise SystemExit("no json")
    return json.loads(out)


def paragraphs(text: str) -> list[tuple[int, int]]:
    """(start_line, end_line) inclusive, 1-indexed, blank-line delimited."""
    spans, start = [], None
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        if line.strip():
            if start is None:
                start = i
        elif start is not None:
            spans.append((start, i - 1))
            start = None
    if start is not None:
        spans.append((start, len(lines)))
    return spans


def bucket(findings: list[dict], spans: list[tuple[int, int]], window: int | None):
    """Map each finding to a paragraph index (or fixed line window)."""
    buckets: dict[int, list[dict]] = defaultdict(list)
    for f in findings:
        line = f["line"]
        if window:
            key = (line - 1) // window
        else:
            key = next((i for i, (a, b) in enumerate(spans) if a <= line <= b), -1)
        buckets[key].append(f)
    return buckets


def analyse(doc_results: list[tuple[pathlib.Path, dict]], window: int | None):
    total_units = 0
    rule_presence: dict[str, set] = defaultdict(set)   # rule -> set(unit ids)
    unit_rules: dict[tuple, set] = {}
    old_gate = new_gate = same_cat3 = 0
    cluster_cats = Counter()
    doc_scope_dropped = 0
    for path, doc in doc_results:
        text = path.read_text(encoding="utf-8", errors="replace")
        spans = paragraphs(text)
        n_units = len(spans) if not window else math.ceil(text.count("\n") / window) + 1
        total_units += n_units
        # document-scope findings are reported at line 1 with no matched text; drop them.
        span_findings = [f for f in doc["findings"] if not (f["line"] == 1 and not f["matched_text"])]
        doc_scope_dropped += len(doc["findings"]) - len(span_findings)
        for key, fs in bucket(span_findings, spans, window).items():
            uid = (str(path), key)
            rules = {f["rule_id"] for f in fs}
            cats = {f["category"] for f in fs}
            unit_rules[uid] = rules
            for r in rules:
                rule_presence[r].add(uid)
            if len(fs) >= 3:
                old_gate += 1
                if len(cats) >= 2:
                    new_gate += 1
                    for c in cats:
                        cluster_cats[c] += 1
                if any(sum(f["category"] == c for f in fs) >= 3 for c in cats):
                    same_cat3 += 1
    # pairwise Jaccard and phi over rules with >= 3 unit hits
    rules = sorted(r for r, u in rule_presence.items() if len(u) >= 3)
    within, across = [], []
    within_phi, across_phi = [], []
    N = total_units
    for a, b in itertools.combinations(rules, 2):
        ua, ub = rule_presence[a], rule_presence[b]
        inter = len(ua & ub)
        union = len(ua | ub)
        jac = inter / union if union else 0.0
        n11 = inter
        n10 = len(ua) - inter
        n01 = len(ub) - inter
        n00 = N - union
        den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
        phi = ((n11 * n00) - (n10 * n01)) / den if den else 0.0
        same = a.split(".")[0] == b.split(".")[0]
        (within if same else across).append(jac)
        (within_phi if same else across_phi).append(phi)

    def q(xs):
        if not xs:
            return "n/a"
        xs = sorted(xs)

        def p(k):
            return xs[min(len(xs) - 1, int(k * (len(xs) - 1)))]

        return f"n={len(xs)} mean={statistics.mean(xs):.4f} median={p(0.5):.4f} p90={p(0.9):.4f} max={xs[-1]:.4f} share>0={sum(x>0 for x in xs)/len(xs):.3f}"

    return {
        "units": N,
        "units_with_findings": len(unit_rules),
        "span_findings": sum(len(v) for v in rule_presence.values()),
        "doc_scope_findings_dropped": doc_scope_dropped,
        "rules_with_ge3_units": len(rules),
        "pairs_within": len(within), "pairs_across": len(across),
        "jaccard_within": q(within), "jaccard_across": q(across),
        "phi_within": q(within_phi), "phi_across": q(across_phi),
        "old_gate_units(>=3 findings)": old_gate,
        "new_gate_units(>=3 findings, >=2 categories)": new_gate,
        "units_with>=3_same_category": same_cat3,
        "cluster_categories": cluster_cats.most_common(8),
    }


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    # Corpus A: repository markdown (config exclusions apply).
    repo_md = sorted(p for p in CHECKOUT.rglob("*.md") if ".venv" not in p.parts and ".git" not in p.parts)
    res_a = lint([str(p.relative_to(CHECKOUT)) for p in repo_md], CHECKOUT)
    docs_a = [(CHECKOUT / d["path"], d) for d in res_a["documents"]]
    # Corpus B: model-authored session prose (>2KB), copied to the work dir.
    dst = WORK / "sessions"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir()
    picked = []
    for p in SESSIONS.glob("*/*/local/**/*.md"):
        if p.stat().st_size > 2000:
            name = f"{p.parts[6][:24]}__{p.stem}.md"
            target = dst / name
            if target.exists():
                name = f"{p.parts[6][:24]}__{p.parts[7][:20]}__{p.stem}.md"
                target = dst / name
            shutil.copy(p, target)
            picked.append(target)
    res_b = lint([str(p) for p in picked], WORK)
    docs_b = [(pathlib.Path(d["path"]) if pathlib.Path(d["path"]).is_absolute() else WORK / d["path"], d) for d in res_b["documents"]]

    report = {}
    for name, docs, res in (("repo_markdown", docs_a, res_a), ("session_model_prose", docs_b, res_b)):
        s = res["summary"]
        report[name] = {
            "documents": s["documents"], "words": s["words"], "findings": s["findings"],
            "errors": s["errors"], "warnings": s["warnings"], "suggestions": s["suggestions"],
            "per_100_words": s["per_100_words"],
            "paragraph": analyse(docs, None),
            "window10": analyse(docs, 10),
        }
    (WORK / "cooccurrence.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
