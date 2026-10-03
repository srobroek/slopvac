"""Render complete SageMaker corpus-evaluation arms as a Markdown report.

The generator refuses to publish a partial, mixed-dataset, or untraceable
report. It expects every registered arm's fetched evaluation artifacts. The
report leads with per-role headline scores and the same balanced accuracy
sliced by test label origin, then fine-tune-vs-base deltas, an optional
comparison with a campaign that shares the test export, an optional
label-source ablation that sets several such campaigns side by side, and every
ledger job the campaign submitted, failed and stopped attempts included.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import thresholds

EXPECTED_BUILDER = "corpus-export"
SPLITS = ("calibration", "test")
KINDS = ("noul", "choice")
RAW_KEYS = ("n", "accuracy", "balanced_accuracy", "auroc", "brier", "nll", "ece_15")
CI_KEYS = ("balanced_accuracy", "ece_15")
SEEDS = (17, 18, 19)
# The judging role each metric kind answers.
ROLES = {"choice": "finding-confirmation", "noul": "semantic-detection"}
# metrics.py names per-slice class recalls by class index: good_recall is
# index 0 and bad_recall index 1. Choice index 0 is real-defect and 1 is
# no-defect (CHOICE_ORDER); yes/no index 1 is True.
CLASS_RECALLS = {
    "choice": (
        ("real-defect recall", "good_recall"),
        ("no-defect recall", "bad_recall"),
    ),
    "noul": (("True recall", "bad_recall"), ("False recall", "good_recall")),
}
# Test label origins in the order the per-origin tables list them; any other
# origin a test split holds follows, sorted.
ORIGIN_ORDER = ("human-adjudication", "llm-review-consensus", "construction")
# metrics.py scores no test row of this origin (blind items carry no label).
UNSCORED_ORIGINS = ("blind-unlabelled",)
# metrics.py CHOICE_ORDER: the class index of each choice label.
CHOICE_ORDER = ("real-defect", "no-defect", "insufficient-context")
CLASS_NAMES = {"choice": CHOICE_ORDER, "noul": ("False", "True")}


def arms_registry():
    source = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(source))
    from judge_sagemaker.pilot.arms import ARMS

    return ARMS


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def composition(rows):
    """(label origins, choice label counts, yes/no label counts) of a split."""
    origins = Counter(str(row.get("label_origin")) for row in rows)
    choice = Counter(
        str(row.get("label")) for row in rows if row.get("kind") == "choice"
    )
    noul = Counter(str(row.get("label")) for row in rows if row.get("kind") == "noul")
    return (
        dict(sorted(origins.items())),
        dict(sorted(choice.items())),
        dict(sorted(noul.items())),
    )


def file_sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def predicted_index(prediction):
    """metrics.py's argmax of the served distribution; the first maximum wins."""
    answer = prediction["answer"]
    if prediction["kind"] == "noul":
        p = float(answer["noul"])
        return 1 if p > 1 - p else 0
    probs = [float(answer["probabilities"][label]) for label in CHOICE_ORDER]
    return max(range(len(probs)), key=probs.__getitem__)


def truth_index(kind, label):
    return int(bool(label)) if kind == "noul" else CHOICE_ORDER.index(label)


def slice_score(pairs):
    """n, class counts and balanced accuracy of (predicted, true) index pairs.

    Balanced accuracy is the headline's (metrics.py summarize() test_raw): the
    mean recall of classes 0 and 1 that occur, so a choice item labelled
    insufficient-context counts in n but in no recall."""
    recalls = []
    for c in (0, 1):
        predicted = [p for p, y in pairs if y == c]
        if predicted:
            recalls.append(sum(p == c for p in predicted) / len(predicted))
    return {
        "n": len(pairs),
        "counts": Counter(y for _, y in pairs),
        "balanced_accuracy": statistics.mean(recalls) if recalls else None,
    }


def origin_scores(arm, predictions_path, test_rows, metrics, errors):
    """Per kind, the all-origin score and one score per test label_origin.

    Forward-order test predictions are joined by id to the arm's test split,
    whose label and label_origin are authoritative. The all-origin balanced
    accuracy must reproduce metrics.<kind>.test_raw, which ties the slices to
    the container's scoring."""
    by_id = {row["id"]: row for row in test_rows}
    pairs = {kind: defaultdict(list) for kind in KINDS}
    seen = set()
    try:
        predictions = load_jsonl(predictions_path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{arm}: invalid predictions {predictions_path} ({exc})")
        return None
    for prediction in predictions:
        if prediction.get("split") != "test" or prediction.get("order") != "forward":
            continue
        row = by_id.get(prediction.get("id"))
        if row is None or row.get("kind") != prediction.get("kind"):
            errors.append(
                f"{arm}: prediction {prediction.get('id')!r} is not a {prediction.get('kind')} item of the test split"
            )
            continue
        if row["id"] in seen or prediction.get("label") != row.get("label"):
            errors.append(
                f"{arm}: prediction {row['id']} is repeated or disagrees with the test label"
            )
            continue
        seen.add(row["id"])
        origin = str(row.get("label_origin"))
        if (
            origin in UNSCORED_ORIGINS
            or prediction.get("status") != 200
            or not prediction.get("answer")
        ):
            continue
        pairs[row["kind"]][origin].append(
            (predicted_index(prediction), truth_index(row["kind"], row["label"]))
        )
    if by_id.keys() - seen:
        errors.append(
            f"{arm}: {len(by_id.keys() - seen)} test items have no forward-order prediction"
        )
    out = {}
    for kind in KINDS:
        overall = slice_score(
            [pair for group in pairs[kind].values() for pair in group]
        )
        expected = metrics.get(kind, {}).get("test_raw", {}).get("balanced_accuracy")
        if (
            overall["balanced_accuracy"] is None
            or not isinstance(expected, (int, float))
            or abs(overall["balanced_accuracy"] - expected) > 1e-9
        ):
            errors.append(
                f"{arm}/{kind}: balanced accuracy from predictions ({overall['balanced_accuracy']}) does not reproduce metrics test_raw ({expected})"
            )
        out[kind] = {
            "all": overall,
            "origins": {
                origin: slice_score(group) for origin, group in pairs[kind].items()
            },
        }
    return out


def validate_metric(metric, label, expected_cal_n, expected_test_n, errors):
    expected_counts = {
        "calibration_raw": expected_cal_n,
        "test_raw": expected_test_n,
        "test_cal": expected_test_n,
    }
    for section, expected_n in expected_counts.items():
        values = metric.get(section)
        if not isinstance(values, dict):
            errors.append(f"{label}: missing metrics.{section}")
            continue
        for field in RAW_KEYS:
            value = values.get(field)
            if (
                field not in values
                or (value is None and field != "auroc")
                or (value is not None and not isinstance(value, (int, float)))
            ):
                errors.append(f"{label}: missing/non-numeric metrics.{section}.{field}")
            elif field == "n" and value != expected_n:
                errors.append(
                    f"{label}: metrics.{section}.n={value}; expected {expected_n}"
                )
            elif (
                value is not None
                and isinstance(value, float)
                and not math.isfinite(value)
            ):
                errors.append(f"{label}: non-finite metrics.{section}.{field}")
    for section, fields in (("test_raw_ci95", CI_KEYS), ("test_cal_ci95", ("ece_15",))):
        values = metric.get(section)
        if not isinstance(values, dict):
            errors.append(f"{label}: missing metrics.{section}")
            continue
        for field in fields:
            ci = values.get(field)
            if (
                not isinstance(ci, list)
                or len(ci) != 2
                or any(
                    not isinstance(x, (int, float)) or not math.isfinite(x) for x in ci
                )
                or ci[0] > ci[1]
            ):
                errors.append(f"{label}: missing/invalid metrics.{section}.{field}")
    if not isinstance(metric.get("errors"), dict) or metric.get("errors"):
        errors.append(f"{label}: prediction errors are missing or non-empty")
    if not isinstance(metric.get("test_slices"), dict):
        errors.append(f"{label}: missing metrics.test_slices")
    if not isinstance(metric.get("test_accuracy_by_source"), dict):
        errors.append(f"{label}: missing metrics.test_accuracy_by_source")


def collect(results_root: Path, registry, ledger_path: Path, panel_path: Path):
    errors = []
    results = {}
    signatures = {}
    ledger = load_json(ledger_path)
    ledger_jobs = {job.get("job_name"): job for job in ledger.get("jobs", [])}
    expected_arms = set(registry)
    for arm in sorted(expected_arms):
        arm_dir = results_root / arm
        result_path = arm_dir / "results" / f"{arm}.json"
        dataset_path = arm_dir / "results" / "dataset-manifest.json"
        manifest_path = arm_dir / "manifest.json"
        for path in (result_path, dataset_path, manifest_path):
            if not path.is_file():
                errors.append(f"{arm}: missing {path}")
        if (
            not result_path.is_file()
            or not dataset_path.is_file()
            or not manifest_path.is_file()
        ):
            continue
        try:
            result = load_json(result_path)
            dataset_manifest = load_json(dataset_path)
            run_manifest = load_json(manifest_path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{arm}: invalid result or manifest ({exc})")
            continue
        if result.get("arm") != arm or run_manifest.get("arm") != arm:
            errors.append(f"{arm}: result/manifest identity does not match directory")
        if dataset_manifest.get("builder") != EXPECTED_BUILDER:
            errors.append(
                f"{arm}: dataset builder is {dataset_manifest.get('builder')!r}; expected {EXPECTED_BUILDER!r}"
            )
        files = dataset_manifest.get("files")
        if not isinstance(files, dict):
            errors.append(f"{arm}: dataset manifest has no files map")
            continue

        split_data = {}
        for split in SPLITS:
            entry = files.get(split)
            if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
                errors.append(f"{arm}: missing dataset manifest entry for {split}")
                continue
            data_path = arm_dir / "data" / f"{split}.jsonl"
            if not data_path.is_file():
                errors.append(f"{arm}: missing {split} split file {data_path}")
                continue
            try:
                rows = load_jsonl(data_path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{arm}: invalid {split} JSONL ({exc})")
                continue
            if file_sha256(data_path) != entry.get("sha256"):
                errors.append(
                    f"{arm}: {split} data SHA-256 does not match its manifest"
                )
            if len(rows) != entry.get("items"):
                errors.append(
                    f"{arm}: {split} has {len(rows)} rows; manifest says {entry.get('items')!r}"
                )
            split_data[split] = {
                "rows": rows,
                "entry": entry,
                "counts": {
                    kind: sum(row.get("kind") == kind for row in rows) for kind in KINDS
                },
            }

        signature = tuple(
            (
                split,
                files.get(split, {}).get("sha256"),
                files.get(split, {}).get("items"),
            )
            for split in SPLITS
        )
        signatures.setdefault((dataset_manifest.get("builder"), signature), []).append(
            arm
        )
        recorded_dataset = result.get("dataset")
        if not isinstance(recorded_dataset, dict):
            errors.append(f"{arm}: result is missing dataset metadata")
        else:
            for split in SPLITS:
                expected = files.get(split, {})
                actual = recorded_dataset.get(split, {})
                if actual.get("sha256") != expected.get("sha256") or actual.get(
                    "items"
                ) != expected.get("items"):
                    errors.append(
                        f"{arm}: result dataset metadata disagrees with {split} manifest"
                    )
        if "test" not in split_data:
            errors.append(f"{arm}: test split could not be loaded")
        else:
            # Composition (label origins, class counts) is reported, not
            # asserted: it changes between exports and once human labels land.
            result["_test_rows"] = split_data["test"]["rows"]
        predictions = arm_dir / "results" / "predictions" / f"{arm}.jsonl"
        result["_thresholds"] = (
            thresholds.analyse(predictions) if predictions.is_file() else None
        )

        metrics = result.get("metrics")
        if not isinstance(metrics, dict):
            errors.append(f"{arm}: missing metrics")
            continue
        for kind in KINDS:
            metric = metrics.get(kind)
            if not isinstance(metric, dict):
                errors.append(f"{arm}: missing metrics for {kind}")
                continue
            cal_n = split_data.get("calibration", {}).get("counts", {}).get(kind)
            test_n = split_data.get("test", {}).get("counts", {}).get(kind)
            if cal_n is not None and test_n is not None:
                validate_metric(metric, f"{arm}/{kind}", cal_n, test_n, errors)
            if (
                kind == "choice"
                and test_n is not None
                and metric.get("test_order_swap_n") != test_n
            ):
                errors.append(
                    f"{arm}/choice: order-swap n={metric.get('test_order_swap_n')!r}; expected {test_n}"
                )
            slices = metric.get("test_slices")
            roles = slices.get("role") if isinstance(slices, dict) else None
            if (
                not isinstance(roles, dict)
                or set(roles) != {ROLES[kind]}
                or roles[ROLES[kind]].get("n") != test_n
            ):
                errors.append(
                    f"{arm}/{kind}: test_slices.role must hold only {ROLES[kind]} with n={test_n}"
                )
        if not predictions.is_file():
            errors.append(f"{arm}: missing {predictions}")
        elif "test" in split_data:
            result["_origins"] = origin_scores(
                arm, predictions, split_data["test"]["rows"], metrics, errors
            )

        job_name = run_manifest.get("job_name")
        ledger_job = ledger_jobs.get(job_name)
        if not job_name or not isinstance(ledger_job, dict):
            errors.append(
                f"{arm}: no cost-ledger job matches manifest job {job_name!r}"
            )
            continue
        arn = run_manifest.get("training_job_arn")
        region = (
            arn.split(":")[3]
            if isinstance(arn, str) and len(arn.split(":")) > 4
            else None
        )
        if ledger_job.get("status") != "Completed" or ledger_job.get("arm") != arm:
            errors.append(
                f"{arm}: ledger entry {job_name} is not a completed evaluation for this arm"
            )
        if ledger_job.get("arn") and arn != ledger_job["arn"]:
            errors.append(
                f"{arm}: SageMaker ARN differs between manifest and cost ledger"
            )
        if not isinstance(
            ledger_job.get("billable_seconds"), (int, float)
        ) or not isinstance(ledger_job.get("cost_usd"), (int, float)):
            errors.append(f"{arm}: completed ledger job lacks billed seconds or cost")
        hardware = result.get("hardware", {})
        instance = hardware.get("instance_type")
        if not instance or instance != ledger_job.get("instance_type"):
            errors.append(
                f"{arm}: result hardware instance type disagrees with cost ledger"
            )
        checkpoint_ref = run_manifest.get("checkpoint_ref") or ""
        result["_report"] = {
            "job_name": job_name,
            "region": region or "—",
            "instance_type": instance or "—",
            "cost_usd": ledger_job.get("cost_usd"),
            "billable_seconds": ledger_job.get("billable_seconds"),
            # s3://<bucket>/training/<training job>/output/... for fine-tunes.
            "training_job": (
                checkpoint_ref.split("/training/", 1)[1].split("/", 1)[0]
                if "/training/" in checkpoint_ref
                else None
            ),
        }
        results[arm] = result

    if len(signatures) != 1:
        groups = [", ".join(arms) for arms in signatures.values()]
        errors.append(
            "arms do not share one identical dataset manifest: " + " | ".join(groups)
        )
    if expected_arms - results.keys():
        errors.append(
            "incomplete arm results: "
            + ", ".join(sorted(expected_arms - results.keys()))
        )

    try:
        panel = load_json(panel_path)
        per_role = panel["per_role"]
        panel_values = {
            role: {
                "fleiss_kappa": float(per_role[role]["fleiss_kappa"]),
                "items": int(per_role[role]["items"]),
            }
            for role in ("finding-confirmation", "semantic-detection")
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"missing/invalid panel-agreement data {panel_path}: {exc}")
        panel_values = {}
    if errors:
        raise ValueError(
            "Corpus report not generated; required results are incomplete or incompatible:\n- "
            + "\n- ".join(errors)
        )
    return results, next(iter(signatures)), panel_values, ledger


def fmt(value):
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def ci_text(metric, key):
    return "–".join(fmt(x) for x in metric[key[0]][key[1]])


def metric_row(name, result, metric):
    raw, cal = metric["test_raw"], metric["test_cal"]
    latency = result.get("latency", {}).get("single_request_all_test_ms", {})
    return [
        name,
        fmt(raw["n"]),
        fmt(raw["accuracy"]),
        fmt(raw["balanced_accuracy"]),
        fmt(raw["auroc"]),
        fmt(raw["brier"]),
        fmt(raw["nll"]),
        fmt(raw["ece_15"]),
        fmt(cal["brier"]),
        fmt(cal["nll"]),
        fmt(cal["ece_15"]),
        ci_text(metric, ("test_raw_ci95", "balanced_accuracy")),
        ci_text(metric, ("test_raw_ci95", "ece_15")),
        ci_text(metric, ("test_cal_ci95", "ece_15")),
        fmt(metric.get("test_bad_recall")),
        fmt(metric.get("test_good_recall")),
        fmt(raw.get("abstain_rate")),
        fmt(metric.get("test_order_swap_agreement")),
        fmt(metric.get("test_order_swap_mean_abs_shift_real_defect")),
        fmt(latency.get("p50")),
        fmt(latency.get("p95")),
    ]


def seed_summaries(names, results, kind):
    fields = (
        ("accuracy", "test_raw"),
        ("balanced_accuracy", "test_raw"),
        ("auroc", "test_raw"),
        ("brier", "test_raw"),
        ("nll", "test_raw"),
        ("ece_15", "test_raw"),
        ("brier", "test_cal"),
        ("nll", "test_cal"),
        ("ece_15", "test_cal"),
        ("abstain_rate", "test_raw"),
        ("test_order_swap_agreement", "metric"),
        ("test_order_swap_mean_abs_shift_real_defect", "metric"),
    )
    rendered = []
    for field, section in fields:
        numbers = []
        for arm in names:
            metric = results[arm]["metrics"][kind]
            value = (metric if section == "metric" else metric[section]).get(field)
            if value is None:
                break
            numbers.append(value)
        if len(numbers) != len(names):
            rendered.append("—")
        else:
            mean = statistics.mean(numbers)
            spread = statistics.stdev(numbers) if len(numbers) > 1 else 0.0
            rendered.append(
                f"{mean:.3f} ± {spread:.3f} [{min(numbers):.3f}–{max(numbers):.3f}]"
            )
    return rendered


def table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def families(registry):
    """Base arm -> its fine-tuned arms in seed order, in registry order.

    A campaign that trains without evaluating the base still yields the base
    key, so fine-tunes group under their base either way."""
    grouped = {}
    for name, info in registry.items():
        base = info["ft_base"] if info.get("ft_seed") else name
        grouped.setdefault(base, [])
        if info.get("ft_seed"):
            grouped[base].append(name)
    for names in grouped.values():
        names.sort(key=lambda name: registry[name]["ft_seed"])
    return grouped


def role_score(result, kind):
    """Headline test scores for the role a metric kind answers."""
    metric = result["metrics"][kind]
    sliced = metric["test_slices"]["role"][ROLES[kind]]
    score = {
        "balanced_accuracy": metric["test_raw"]["balanced_accuracy"],
        "ece_raw": metric["test_raw"]["ece_15"],
        "ece_cal": metric["test_cal"]["ece_15"],
    }
    for label, key in CLASS_RECALLS[kind]:
        score[label] = sliced[key]
    return score


def delta_keys(kind):
    return (
        "balanced_accuracy",
        *(label for label, _ in CLASS_RECALLS[kind]),
        "ece_raw",
        "ece_cal",
    )


def mean_of(scores, key):
    values = [score[key] for score in scores]
    return None if any(v is None for v in values) else statistics.mean(values)


def spread_text(scores, key):
    """Seed mean ± sample SD [min–max] of one score."""
    values = [score[key] for score in scores]
    if not values or any(v is None for v in values):
        return "—"
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{statistics.mean(values):.3f} ± {sd:.3f} [{min(values):.3f}–{max(values):.3f}]"


def delta_text(value, reference):
    return "—" if value is None or reference is None else f"{value - reference:+.3f}"


def complete_family(names, results):
    return len(names) == len(SEEDS) and all(name in results for name in names)


def class_counts_text(kind, choice_counts, noul_counts):
    counts = choice_counts if kind == "choice" else noul_counts
    labels = [label.removesuffix(" recall") for label, _ in CLASS_RECALLS[kind]]
    return ", ".join(f"{label}={counts.get(label, 0)}" for label in labels)


def headline_lines(results, registry, test_rows, results_dir):
    _, choice_counts, noul_counts = composition(test_rows or [])
    lines = [
        "## Headline by role",
        "",
        f"Each arm's numbers come from `results/{results_dir}/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds {', '.join(map(str, SEEDS))}.",
        "",
    ]
    grouped = families(registry)
    for kind in ("choice", "noul"):
        role = ROLES[kind]
        recall_labels = [label for label, _ in CLASS_RECALLS[kind]]
        n = next(iter(results.values()))["metrics"][kind]["test_raw"]["n"]
        lines += [
            f"### {role} (`{kind}`)",
            "",
            f"Test items: {n} ({class_counts_text(kind, choice_counts, noul_counts)}).",
            "",
        ]
        absent = [
            label
            for label in recall_labels
            if all(role_score(r, kind)[label] is None for r in results.values())
        ]
        if absent:
            lines += [
                f"No test item has the class behind {', '.join(absent)}, so that recall is undefined and balanced accuracy reduces to the recall of the class present.",
                "",
            ]
        headers = [
            "Arm",
            "Bal. acc.",
            "Bal. acc. 95% CI",
            *recall_labels,
            "ECE raw",
            "ECE cal.",
            "GPU",
            "p50 ms",
            "Eval USD",
        ]
        rows = []
        family_means = []
        for base, fine_tunes in grouped.items():
            for name in (base, *fine_tunes):
                if name not in results:
                    continue
                result = results[name]
                score = role_score(result, kind)
                latency = result.get("latency", {}).get(
                    "single_request_all_test_ms", {}
                )
                rows.append(
                    [
                        name,
                        fmt(score["balanced_accuracy"]),
                        ci_text(
                            result["metrics"][kind],
                            ("test_raw_ci95", "balanced_accuracy"),
                        ),
                        *(fmt(score[label]) for label in recall_labels),
                        fmt(score["ece_raw"]),
                        fmt(score["ece_cal"]),
                        result.get("hardware", {}).get("gpu", "—"),
                        fmt(latency.get("p50")),
                        f"${result['_report']['cost_usd']:.4f}",
                    ]
                )
            if fine_tunes and complete_family(fine_tunes, results):
                scores = [role_score(results[name], kind) for name in fine_tunes]
                family_means.append(
                    (mean_of(scores, "balanced_accuracy"), base, scores)
                )
                rows.append(
                    [
                        f"{base} FT mean ± SD [range]",
                        spread_text(scores, "balanced_accuracy"),
                        "—",
                        *(spread_text(scores, label) for label in recall_labels),
                        spread_text(scores, "ece_raw"),
                        spread_text(scores, "ece_cal"),
                        "—",
                        "—",
                        "—",
                    ]
                )
        best_arm = max(
            results,
            key=lambda name: role_score(results[name], kind)["balanced_accuracy"],
        )
        lines += [
            table(headers, rows),
            "",
            f"- Best single arm: `{best_arm}` (balanced accuracy {role_score(results[best_arm], kind)['balanced_accuracy']:.3f}).",
        ]
        if family_means:
            _, base, scores = max(family_means, key=lambda entry: entry[0])
            lines.append(
                f"- Best fine-tuned family by seed mean: `{base}` ({spread_text(scores, 'balanced_accuracy')})."
            )
        lines.append("")
    return lines


def ft_vs_base_lines(results, registry, compare):
    """Seed-mean fine-tune minus base, per role. A campaign that does not
    evaluate the base borrows it from the comparison campaign, whose test
    and calibration hashes collect() has already matched."""
    pool = {}
    if compare is not None:
        pool.update({name: (compare[0], r) for name, r in compare[1].items()})
    pool.update({name: ("this campaign", r) for name, r in results.items()})
    trained = {base: names for base, names in families(registry).items() if names}
    if not trained:
        return []
    lines = [
        "## Fine-tune vs base",
        "",
        'Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.',
        "",
    ]
    for kind in ("choice", "noul"):
        recall_labels = [label for label, _ in CLASS_RECALLS[kind]]
        headers = [
            "Family",
            "Base from",
            "Base bal. acc.",
            "FT mean bal. acc.",
            "Δ bal. acc.",
            "Seeds > base",
            *(f"Δ {label}" for label in recall_labels),
            "Δ ECE raw",
            "Δ ECE cal.",
        ]
        rows = []
        for base, fine_tunes in trained.items():
            if not complete_family(fine_tunes, results):
                continue
            scores = [role_score(results[name], kind) for name in fine_tunes]
            if base not in pool:
                rows.append(
                    [
                        base,
                        "not evaluated",
                        "—",
                        fmt(mean_of(scores, "balanced_accuracy")),
                    ]
                    + ["—"] * (len(headers) - 4)
                )
                continue
            source, base_result = pool[base]
            reference = role_score(base_result, kind)
            means = {key: mean_of(scores, key) for key in delta_keys(kind)}
            wins = sum(
                score["balanced_accuracy"] > reference["balanced_accuracy"]
                for score in scores
            )
            rows.append(
                [
                    base,
                    source,
                    fmt(reference["balanced_accuracy"]),
                    fmt(means["balanced_accuracy"]),
                    delta_text(
                        means["balanced_accuracy"], reference["balanced_accuracy"]
                    ),
                    f"{wins}/{len(scores)}",
                    *(
                        delta_text(means[label], reference[label])
                        for label in recall_labels
                    ),
                    delta_text(means["ece_raw"], reference["ece_raw"]),
                    delta_text(means["ece_cal"], reference["ece_cal"]),
                ]
            )
        lines += [f"### {ROLES[kind]} (`{kind}`)", "", table(headers, rows), ""]
    return lines


def comparison_lines(results, registry, compare, results_dir):
    """Seed means of the fine-tunes both campaigns trained, this minus other."""
    other_dir, other = compare
    shared = {
        base: names
        for base, names in families(registry).items()
        if names and complete_family(names, results) and complete_family(names, other)
    }
    lines = [
        f"## Comparison with `{other_dir}`",
        "",
        f'Both campaigns score the same test and calibration export (hashes verified). Δ is `{results_dir}` minus `{other_dir}` seed means for the same family and seeds; "Seeds better" counts seeds whose balanced accuracy is higher here than the same seed there.',
        "",
    ]
    if not shared:
        return lines + ["No fine-tuned family is complete in both campaigns.", ""]
    for kind in ("choice", "noul"):
        recall_labels = [label for label, _ in CLASS_RECALLS[kind]]
        headers = [
            "Family",
            f"{results_dir} bal. acc.",
            f"{other_dir} bal. acc.",
            "Δ bal. acc.",
            "Seeds better",
            *(f"Δ {label}" for label in recall_labels),
            "Δ ECE raw",
            "Δ ECE cal.",
        ]
        rows = []
        for base, names in shared.items():
            mine = [role_score(results[name], kind) for name in names]
            theirs = [role_score(other[name], kind) for name in names]
            better = sum(
                a["balanced_accuracy"] > b["balanced_accuracy"]
                for a, b in zip(mine, theirs)
            )
            rows.append(
                [
                    base,
                    spread_text(mine, "balanced_accuracy"),
                    spread_text(theirs, "balanced_accuracy"),
                    delta_text(
                        mean_of(mine, "balanced_accuracy"),
                        mean_of(theirs, "balanced_accuracy"),
                    ),
                    f"{better}/{len(names)}",
                    *(
                        delta_text(mean_of(mine, key), mean_of(theirs, key))
                        for key in (*recall_labels, "ece_raw", "ece_cal")
                    ),
                ]
            )
        lines += [f"### {ROLES[kind]} (`{kind}`)", "", table(headers, rows), ""]
    return lines


def mean_sd_text(values):
    """Seed mean ± sample SD."""
    if not values or any(v is None for v in values):
        return "—"
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{statistics.mean(values):.3f} ± {sd:.3f}"


def origin_ba(result, kind, origin=None):
    """Balanced accuracy over all test items of a kind, or one label origin's."""
    scores = result["_origins"][kind]
    score = scores["all"] if origin is None else scores["origins"].get(origin)
    return None if score is None else score["balanced_accuracy"]


def origin_columns(result_sets, kind):
    """The test label origins of a kind: ORIGIN_ORDER first, then any other."""
    present = {
        origin
        for results in result_sets
        for result in results.values()
        for origin in result["_origins"][kind]["origins"]
    }
    return [o for o in ORIGIN_ORDER if o in present] + sorted(
        present - set(ORIGIN_ORDER)
    )


def origin_cells(names, results, kind, origins):
    """All-test and per-origin balanced accuracy: one arm's values, or the seed
    mean ± SD of a fine-tune family."""
    columns = (None, *origins)
    if len(names) == 1:
        return [fmt(origin_ba(results[names[0]], kind, o)) for o in columns]
    return [
        mean_sd_text([origin_ba(results[name], kind, o) for name in names])
        for o in columns
    ]


def origin_counts_text(result, kind, origins):
    classes = CLASS_NAMES[kind]
    parts = []
    for origin in origins:
        score = result["_origins"][kind]["origins"][origin]
        counts = ", ".join(
            f"{classes[c]}={score['counts'][c]}" for c in sorted(score["counts"])
        )
        parts.append(f"`{origin}` {score['n']} ({counts})")
    return "; ".join(parts)


def origin_lines(results, registry, results_dir):
    lines = [
        "## Balanced accuracy by test label origin",
        "",
        f"Computed by this generator from each arm's forward-order test predictions (`results/{results_dir}/<arm>/results/predictions/<arm>.jsonl`) joined by item id to the arm's hash-checked test split (`<arm>/data/test.jsonl`), which supplies `label` and `label_origin`. Balanced accuracy is the headline's (`test_raw`): the mean recall of real-defect and no-defect for finding confirmation, where insufficient-context items count in n only, and of True and False for semantic detection. The *All* column reproduces each arm's headline; the generator refuses to render when it does not. A slice that holds one class reduces to that class's recall, and small slices are noisy. Fine-tune family rows give the seed mean ± sample SD over seeds {', '.join(map(str, SEEDS))}.",
        "",
    ]
    grouped = families(registry)
    first = next(iter(results.values()))
    for kind in ("choice", "noul"):
        origins = origin_columns([results], kind)
        absent = [o for o in ORIGIN_ORDER if o not in origins]
        lines += [
            f"### {ROLES[kind]} (`{kind}`)",
            "",
            f"Test items by origin: {origin_counts_text(first, kind, origins)}."
            + (
                f" No test item has origin {', '.join(f'`{o}`' for o in absent)}."
                if absent
                else ""
            ),
            "",
        ]
        rows = []
        for base, fine_tunes in grouped.items():
            for name in (base, *fine_tunes):
                if name in results:
                    rows.append([name, *origin_cells([name], results, kind, origins)])
            if fine_tunes and complete_family(fine_tunes, results):
                rows.append(
                    [
                        f"{base} FT mean ± SD",
                        *origin_cells(fine_tunes, results, kind, origins),
                    ]
                )
        lines += [table(["Arm", "All", *origins], rows), ""]
    return lines


def ablation_lines(results, registry, campaign, peers):
    """This campaign and each --ablation campaign side by side: per role and
    test label origin, the seed mean ± SD of every complete fine-tune family,
    and each base arm from the first campaign that evaluates it."""
    campaigns = [(campaign, results, registry), *peers]
    order = []
    for _, _, other_registry in campaigns:
        order += [base for base in families(other_registry) if base not in order]
    described = "; ".join(
        f"`{other['results']}` (`{other['id']}`"
        + (
            f", checkpoints from `{other['checkpoints_from']}`"
            if other.get("checkpoints_from")
            else ""
        )
        + ")"
        for other, _, _ in campaigns
    )
    lines = [
        "## Label-source ablation",
        "",
        f"Campaigns on this campaign's test and calibration export (hashes verified): {described}. Each campaign's notes say what its fine-tunes trained on.",
        "",
        "Cells are balanced accuracy as defined under *Balanced accuracy by test label origin*: the seed mean ± sample SD of a complete fine-tune family, or a single base-arm run taken from the first listed campaign that evaluates it. A gap between two families reflects more than training-seed variation only when it is well beyond both SDs.",
        "",
    ]
    for kind in ("choice", "noul"):
        origins = origin_columns([r for _, r, _ in campaigns], kind)
        rows = []
        for base in order:
            source = next((c for c in campaigns if base in c[1]), None)
            if source is not None:
                rows.append(
                    [
                        base,
                        f"base, `{source[0]['results']}`",
                        "1",
                        *origin_cells([base], source[1], kind, origins),
                    ]
                )
            for other, other_results, other_registry in campaigns:
                fine_tunes = families(other_registry).get(base, [])
                if fine_tunes and complete_family(fine_tunes, other_results):
                    rows.append(
                        [
                            f"{base} FT",
                            f"`{other['results']}`",
                            str(len(fine_tunes)),
                            *origin_cells(fine_tunes, other_results, kind, origins),
                        ]
                    )
        lines += [
            f"### {ROLES[kind]} (`{kind}`)",
            "",
            table(["Family", "Arms from", "Seeds", "All", *origins], rows),
            "",
        ]
    return lines


def campaign_jobs(ledger, campaign, registry, unmarked_by_time):
    """Ledger jobs this campaign submitted, as the scheduler attributes them:
    training jobs whose train data is the campaign export, evaluation jobs
    marked with its run id. With `unmarked_by_time` (round 1), unmarked
    evaluations submitted after its first training job count too."""
    source = f"/exports/{campaign['id']}/train.jsonl"
    models = set(campaign["train_models"])
    training = [
        job
        for job in ledger["jobs"]
        if job.get("model") in models
        and source in job.get("data", {}).get("train", {}).get("source", "")
    ]
    started = min(
        (job["submitted_at"] for job in training if job.get("submitted_at")),
        default=None,
    )
    run_id = f"corpus-{campaign['id']}"
    evaluation = []
    for job in ledger["jobs"]:
        if job.get("kind") != "evaluation" or job.get("arm") not in registry:
            continue
        marked = job.get("scheduler", {}).get("campaign")
        if marked == run_id or (
            unmarked_by_time
            and marked is None
            and started
            and job.get("submitted_at", "") >= started
        ):
            evaluation.append(job)
    unsettled = [
        job["job_name"]
        for job in training + evaluation
        if job.get("status") not in {"Completed", "Failed", "Stopped"}
    ]
    if unsettled:
        raise ValueError(f"campaign has unsettled ledger jobs: {', '.join(unsettled)}")
    return training, evaluation


def job_target(job):
    if job.get("kind") == "evaluation":
        return job["arm"]
    seed = job.get("hyperparameters", {}).get("seed")
    return f"{job['model']}-ft-s{seed if seed is not None else '? (no seed)'}"


def job_reason(job):
    """One line saying why a job did not complete, from what the ledger kept."""
    scheduler = job.get("scheduler", {})
    marker = scheduler.get("implementation_defect") or scheduler.get(
        "retry_implementation_defect"
    )
    reason = (job.get("failure_reason") or "").strip()
    if reason:
        reason = reason.splitlines()[0]
    elif marker:
        reason = f"scheduler marker `{marker}`"
    elif scheduler.get("submission_errors"):
        error = str(scheduler["submission_errors"][-1].get("error", "")).strip()
        last = error.splitlines()[-1] if error else "?"
        # botocore.errorfactory.X: An error occurred (X) when calling the Y operation: msg
        last = re.sub(
            r"^botocore\.errorfactory\.(\w+): An error occurred \(\w+\) when calling the \w+ operation: ",
            r"\1: ",
            last,
        )
        reason = "submission rejected: " + last
    elif job.get("note") or scheduler.get("attempt_budget_exempt_reason"):
        reason = job.get("note") or scheduler["attempt_budget_exempt_reason"]
    elif job.get("secondary_status"):
        reason = f"no failure reason; secondary status {job['secondary_status']}"
    else:
        reason = "no reason recorded"
    return reason if len(reason) <= 120 else reason[:119] + "…"


def status_counts(jobs):
    counts = Counter(job["status"] for job in jobs)
    return " / ".join(
        f"{counts.get(status, 0)}" for status in ("Completed", "Failed", "Stopped")
    )


def cost(jobs):
    return sum(float(job.get("cost_usd") or 0.0) for job in jobs)


def jobs_lines(results, registry, training, evaluation):
    by_target = defaultdict(lambda: {"training": [], "evaluation": []})
    for job in training:
        by_target[job_target(job)]["training"].append(job)
    for job in evaluation:
        by_target[job["arm"]]["evaluation"].append(job)
    ledger_names = {job["job_name"]: job for job in training}
    headers = [
        "Arm",
        "Training jobs C / F / S",
        "Training USD (all)",
        "Accepted training job",
        "Accepted training USD",
        "Eval jobs C / F / S",
        "Eval USD (all)",
        "Arm USD",
    ]
    rows = []
    for name in registry:
        jobs = by_target[name]
        accepted = results[name]["_report"]["training_job"] if name in results else None
        accepted_job = ledger_names.get(accepted) if accepted else None
        rows.append(
            [
                name,
                status_counts(jobs["training"])
                if registry[name].get("ft_seed")
                else "—",
                f"${cost(jobs['training']):.2f}"
                if registry[name].get("ft_seed")
                else "—",
                accepted or "—",
                f"${float(accepted_job.get('cost_usd') or 0.0):.2f}"
                if accepted_job
                else ("not in ledger" if accepted else "—"),
                status_counts(jobs["evaluation"]),
                f"${cost(jobs['evaluation']):.2f}",
                f"${cost(jobs['training']) + cost(jobs['evaluation']):.2f}",
            ]
        )
    stray = sorted(set(by_target) - set(registry))
    groups = defaultdict(list)
    accepted_jobs = {r["_report"]["training_job"] for r in results.values()}
    for job in training + evaluation:
        if job["status"] != "Completed":
            task = "evaluation" if job.get("kind") == "evaluation" else "training"
            reason = job_reason(job)
            if job["job_name"] in accepted_jobs:
                reason = "ACCEPTED (checkpoint saved before the failure): " + reason
            groups[(job_target(job), task, job["status"], reason)].append(job)
    failure_rows = [
        [target, task, status, len(jobs), f"${cost(jobs):.2f}", reason]
        for (target, task, status, reason), jobs in sorted(groups.items())
    ]
    total = cost(training) + cost(evaluation)
    lines = [
        "## Campaign jobs, failures, and cost",
        "",
        "Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.",
        "",
        table(headers, rows),
        "",
        f"Campaign total: **${total:.2f} USD** (training ${cost(training):.2f}, evaluation ${cost(evaluation):.2f}) over {len(training)} training and {len(evaluation)} evaluation jobs.",
        "",
    ]
    if stray:
        lines += [
            f"Ledger jobs for targets outside this campaign's arms: {', '.join(stray)}.",
            "",
        ]
    lines += ["### Failed and stopped attempts", ""]
    if failure_rows:
        lines += [
            table(["Target", "Task", "Status", "Jobs", "USD", "Reason"], failure_rows),
            "",
        ]
    else:
        lines += ["None.", ""]
    return lines


def render(
    results,
    signature,
    panel_values,
    ledger,
    panel_path,
    registry,
    *,
    campaign,
    results_dir,
    jobs,
    compare=None,
    ablation=(),
    notes=(),
):
    builder, splits = signature
    training, evaluation = jobs
    unfinished = [job for job in training + evaluation if job["status"] != "Completed"]
    lines = [f"# Corpus evaluation report: `{results_dir}`", ""]
    if notes:
        lines += ["## Status", "", *(f"- {note}" for note in notes), ""]
    lines += [
        "## Dataset and coverage",
        "",
        f"- Campaign: `{campaign['id']}`."
        + (f" {campaign['notes']}" if campaign.get("notes") else ""),
        f"- Dataset builder: `{builder}`; same calibration/test hashes are verified for all arms.",
        f"- Evaluated arms: {len(results)} of {len(registry)} required ({', '.join(f'`{name}`' for name in registry)}). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.",
        f"- Failed or stopped SageMaker attempts: {len(unfinished)} of {len(training) + len(evaluation)} campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.",
    ]
    for split, digest, count in splits:
        lines.append(f"- {split.title()}: {count} examples; SHA-256 `{digest}`.")
    test_rows = next(iter(results.values())).get("_test_rows")
    if test_rows is not None:
        origins, choice_counts, noul_counts = composition(test_rows)
        lines.append(
            "- Test composition: label origins "
            + ", ".join(f"`{o}`={n}" for o, n in origins.items())
            + "; choice labels "
            + (", ".join(f"{k}={v}" for k, v in choice_counts.items()) or "none")
            + "; yes/no labels "
            + (", ".join(f"{k}={v}" for k, v in noul_counts.items()) or "none")
            + "."
        )
    lines += [""]
    lines += headline_lines(results, registry, test_rows, results_dir)
    lines += origin_lines(results, registry, results_dir)
    lines += ft_vs_base_lines(results, registry, compare)
    if compare is not None:
        lines += comparison_lines(results, registry, compare, results_dir)
    if ablation:
        lines += ablation_lines(results, registry, campaign, ablation)
    lines += jobs_lines(results, registry, training, evaluation)
    lines += [
        "## Panel agreement caveat",
        "",
        f"Independent corpus panel agreement (source: `{panel_path}`):",
    ]
    for role in ("finding-confirmation", "semantic-detection"):
        value = panel_values[role]
        lines.append(
            f"- {role}: Fleiss κ={value['fleiss_kappa']:.2f} ({value['items']} three-vote items)."
        )
    lines += [
        "- Scores on panel-labelled rows measure agreement with the panel. Only constructions and human-adjudicated rows have independent ground truth.",
        "",
        "## Per-arm training recipes",
        "",
        table(
            [
                "Family / arm",
                "Seeds",
                "Epochs",
                "Batch × accumulation",
                "LR",
                "Max state / max length",
                "Dtype / weights",
            ],
            [
                [
                    "Kev-0.8B",
                    "17, 18, 19",
                    "2",
                    "4 × 2",
                    "2e-5",
                    "4096 / 4096",
                    "bf16 autocast / fp32 weights",
                ],
                [
                    "Kev-4B",
                    "17, 18, 19",
                    "2",
                    "2 × 4",
                    "2e-5",
                    "4096 / 4096",
                    "bf16 autocast / fp32 weights",
                ],
                [
                    "Kev-9B",
                    "17, 18, 19",
                    "2",
                    "1 × 8",
                    "2e-5",
                    "4096 / 4096",
                    "bf16 autocast / fp32 weights; LoRA/head fp32",
                ],
                [
                    "Laya typed decisions",
                    "17, 18, 19",
                    "4",
                    "micro-batch 8 × grad accum 8",
                    "2.5e-5 encoder / 1e-4 head",
                    "4096 / head 1024",
                    "fp32 training; fp16 saved",
                ],
            ],
        ),
        "",
        "Kev uses CUDA bf16 autocast, fp32 frozen backbone weights and gradient checkpointing; 9B uses micro-batch 1 × accumulation 8 to preserve effective batch 8. Laya uses its 4-epoch pilot recipe; its encoder sequence max_len is raised to 4096 for this corpus.",
        "",
    ]
    lines += [
        "## Per-arm evaluation tables",
        "",
        "Model results include checkpoints from failed fine-tuning jobs only when calibration failed after training and the archived adapter/head were validated; their evaluation job—not the training job—fits calibration to the test/calibration export.",
        "",
    ]
    headers = [
        "Arm / seed summary",
        "N",
        "Accuracy",
        "Balanced acc.",
        "AUROC",
        "Brier raw",
        "NLL raw",
        "ECE raw",
        "Brier cal.",
        "NLL cal.",
        "ECE cal.",
        "Bal. acc. 95% CI",
        "ECE raw 95% CI",
        "ECE cal. 95% CI",
        "Bad recall",
        "Good recall",
        "Abstain",
        "Order-swap agree",
        "Order-swap prob. shift",
        "Latency p50 ms",
        "Latency p95 ms",
    ]
    for base, ft_names in families(registry).items():
        members = [name for name in (base, *ft_names) if name in results]
        lines += [f"### {base}", ""]
        for kind in KINDS:
            rows = [
                metric_row(name, results[name], results[name]["metrics"][kind])
                for name in members
            ]
            if len(ft_names) == 3 and all(name in results for name in ft_names):
                summary = seed_summaries(ft_names, results, kind)
                # Score means are aligned with raw/calibrated score columns; diagnostics align with choice columns.
                rows.append(
                    [
                        "FT mean ± SD [range]",
                        "—",
                        *summary[:9],
                        *("—",) * 5,
                        *summary[9:12],
                        *("—",) * 2,
                    ]
                )
            lines += [f"#### {kind}", "", table(headers, rows), ""]

    resource_headers = [
        "Arm",
        "GPU class",
        "Instance type",
        "Region",
        "p50 ms",
        "p95 ms",
        "Billable seconds",
        "Billed USD",
        "Job",
    ]
    resource_rows = []
    total_cost = 0.0
    for arm in sorted(results):
        result = results[arm]
        report_meta = result["_report"]
        latency = result.get("latency", {}).get("single_request_all_test_ms", {})
        gpu = result.get("hardware", {}).get("gpu", "—")
        total_cost += report_meta["cost_usd"]
        resource_rows.append(
            [
                arm,
                gpu,
                report_meta["instance_type"],
                report_meta["region"],
                fmt(latency.get("p50")),
                fmt(latency.get("p95")),
                fmt(report_meta["billable_seconds"]),
                f"${report_meta['cost_usd']:.4f}",
                report_meta["job_name"],
            ]
        )
    lines += [
        "## Latency by GPU class and billed evaluation cost",
        "",
        table(resource_headers, resource_rows),
        "",
        f"Total billed evaluation cost for the reported arms: **${total_cost:.4f} USD** (completed SageMaker jobs matched by job name and ARN in `{ledger.get('currency', 'USD')}` ledger).",
        "",
    ]

    lines += [
        "## Per-arm slice and source details",
        "",
        "All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.",
        "",
    ]
    slice_headers = [
        "Arm",
        "Metric kind",
        "Breakdown",
        "Value",
        "N",
        "Accuracy",
        "Balanced accuracy",
        "ECE-15",
        "Bad recall",
        "Good recall",
    ]
    slice_rows = []
    for arm in sorted(results):
        for kind in KINDS:
            metric = results[arm]["metrics"][kind]
            for field, groups in sorted(metric["test_slices"].items()):
                for value, score in sorted(groups.items()):
                    slice_rows.append(
                        [
                            arm,
                            kind,
                            field,
                            value,
                            fmt(score.get("n")),
                            fmt(score.get("accuracy")),
                            fmt(score.get("balanced_accuracy")),
                            fmt(score.get("ece_15")),
                            fmt(score.get("bad_recall")),
                            fmt(score.get("good_recall")),
                        ]
                    )
            for source, score in sorted(metric["test_accuracy_by_source"].items()):
                slice_rows.append(
                    [
                        arm,
                        kind,
                        "source accuracy",
                        source,
                        fmt(score.get("n")),
                        fmt(score.get("accuracy")),
                        "—",
                        "—",
                        "—",
                        "—",
                    ]
                )
    lines += [
        table(slice_headers, slice_rows),
        "",
        "## Decision thresholds (yes/no questions)",
        "",
        f"Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least {thresholds.MIN_PER_CLASS} calibration items (other rules fall back to the global one). Test balanced accuracy at each:",
        "",
    ]
    threshold_rows = []
    for arm in sorted(results):
        t = results[arm].get("_thresholds")
        if t is None:
            threshold_rows.append([arm, "—", "—", "—", "—", "—", "—"])
            continue
        b = t["test_balanced_accuracy"]
        threshold_rows.append(
            [
                arm,
                fmt(t["calibration_n"]),
                fmt(t["global_threshold"]),
                fmt(t["rules_with_own_threshold"]),
                fmt(b["at_0.5"]),
                fmt(b["at_global"]),
                fmt(b["at_per_rule"]),
            ]
        )
    lines += [
        table(
            [
                "arm",
                "calibration n",
                "global threshold",
                "rules with own threshold",
                "test bal. acc @0.5",
                "@global",
                "@per-rule",
            ],
            threshold_rows,
        ),
        "",
    ]
    origins, choice_counts, noul_counts = composition(test_rows or [])
    kappas = ", ".join(
        f"κ={panel_values[role]['fleiss_kappa']:.2f} {role}"
        for role in ("finding-confirmation", "semantic-detection")
    )
    lines += [
        "## Interpretation and caveats",
        "",
        f"- Test label origins: {', '.join(f'{o} ({n})' for o, n in origins.items())}. Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.",
        f"- Test class counts: choice {', '.join(f'{k}={v}' for k, v in choice_counts.items()) or 'none'}; yes/no {', '.join(f'{k}={v}' for k, v in noul_counts.items()) or 'none'}. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.",
        f"- Training labels come from a teacher panel with {kappas}. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.",
        "- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.",
        "- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.",
        "- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.",
        "- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.",
        "- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.",
        "",
    ]
    return "\n".join(lines)


def campaign_arms(campaign, registry):
    names = list(campaign["base_arms"]) + [
        f"{model}-ft-s{seed}" for model in campaign["train_models"] for seed in SEEDS
    ]
    missing = [n for n in names if n not in registry]
    if missing:
        raise ValueError(f"campaign arms not in arms.py: {missing}")
    return {n: registry[n] for n in names}


# The default campaign; its id is the corpus export named in resources.json.
ROUND1 = {
    "results": "corpus",
    "panel_agreement": ".cache/items-v2/panel-agreement.json",
    "base_arms": [
        "kev-0.8b",
        "kev-4b",
        "kev-9b",
        "laya-english",
        "laya-multilingual",
        "laya-typed-decisions",
    ],
    "train_models": ["kev-0.8b", "kev-4b", "kev-9b", "laya-typed-decisions"],
    "notes": "Round 1 (default campaign) on the export named in resources.json: six base arms plus three-seed fine-tunes of Kev 0.8B, 4B, 9B and Laya typed-decisions.",
}


def load_campaign(path, script):
    """A campaign JSON, or round 1 when path is None."""
    if path is not None:
        return load_json(path), False
    resources = load_json(script.parents[1] / "resources.json")
    return {**ROUND1, "id": resources["corpus_export"]["build_id"]}, True


def main():
    script = Path(__file__).resolve()
    corpus = script.parents[4] / "exp-judge-corpus" / "scripts" / "judge-corpus"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign",
        type=Path,
        help="campaign JSON under campaigns/; default: round 1 (results/corpus)",
    )
    parser.add_argument("--results-root", type=Path)
    parser.add_argument(
        "--ledger", type=Path, default=script.parents[1] / "cost-ledger.json"
    )
    parser.add_argument("--panel-agreement", type=Path)
    parser.add_argument(
        "--compare",
        type=Path,
        help="campaign JSON sharing this campaign's test/calibration export: adds a "
        "fine-tune comparison and supplies base arms this campaign does not evaluate",
    )
    parser.add_argument(
        "--ablation",
        type=Path,
        action="append",
        default=[],
        help="campaign JSON sharing this campaign's test/calibration export, set side "
        "by side with it in a label-source ablation section (repeatable)",
    )
    parser.add_argument(
        "--note",
        action="append",
        default=[],
        help="status line printed at the top of the report (repeatable)",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        campaign, is_round1 = load_campaign(args.campaign, script)
        registry = campaign_arms(campaign, arms_registry())
        results_root = (
            args.results_root or script.parents[1] / "results" / campaign["results"]
        )
        panel_path = args.panel_agreement or corpus / campaign["panel_agreement"]
        output = args.output or results_root / "REPORT.md"
        results, signature, panel_values, ledger = collect(
            results_root, registry, args.ledger, panel_path
        )
        jobs = campaign_jobs(ledger, campaign, registry, unmarked_by_time=is_round1)

        def load_other(path, flag):
            """A complete campaign on this campaign's test/calibration export."""
            other, _ = load_campaign(path, script)
            other_registry = campaign_arms(other, arms_registry())
            other_results, other_signature, _, _ = collect(
                script.parents[1] / "results" / other["results"],
                other_registry,
                args.ledger,
                corpus / other["panel_agreement"],
            )
            if other_signature != signature:
                raise ValueError(
                    f"{flag} {path}: test/calibration export differs from this campaign's"
                )
            return other, other_results, other_registry

        compare = None
        if args.compare is not None:
            other, other_results, _ = load_other(args.compare, "--compare")
            compare = (other["results"], other_results)
        ablation = [load_other(path, "--ablation") for path in args.ablation]
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report = render(
        results,
        signature,
        panel_values,
        ledger,
        panel_path,
        registry,
        campaign=campaign,
        results_dir=campaign["results"],
        jobs=jobs,
        compare=compare,
        ablation=ablation,
        notes=args.note,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output} ({len(results)} arms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
