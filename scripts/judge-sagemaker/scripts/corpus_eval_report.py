"""Render complete SageMaker corpus-evaluation arms as a Markdown report.

The generator refuses to publish a partial, mixed-dataset, or untraceable
report. It expects every registered arm's fetched evaluation artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

import thresholds

EXPECTED_BUILDER = "corpus-export"
SPLITS = ("calibration", "test")
KINDS = ("noul", "choice")
RAW_KEYS = ("n", "accuracy", "balanced_accuracy", "auroc", "brier", "nll", "ece_15")
CI_KEYS = ("balanced_accuracy", "ece_15")


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
        result["_report"] = {
            "job_name": job_name,
            "region": region or "—",
            "instance_type": instance or "—",
            "cost_usd": ledger_job.get("cost_usd"),
            "billable_seconds": ledger_job.get("billable_seconds"),
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


def render(results, signature, panel_values, ledger, panel_path, registry):
    builder, splits = signature
    lines = [
        "# Corpus evaluation report",
        "",
        "## Dataset and coverage",
        "",
        f"- Dataset builder: `{builder}`; same calibration/test hashes are verified for all arms.",
        f"- Evaluated arms: {len(results)} of {len(results)} required.",
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
    lines += [
        "",
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
    for base, info in registry.items():
        if info.get("ft_seed"):
            continue
        ft_names = sorted(
            (
                name
                for name, arm_info in registry.items()
                if arm_info.get("ft_base") == base
            ),
            key=lambda name: registry[name]["ft_seed"],
        )
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
        "- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate.",
        "- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.",
        "",
    ]
    return "\n".join(lines)


def campaign_arms(campaign, registry):
    seeds = (17, 18, 19)
    names = list(campaign["base_arms"]) + [
        f"{model}-ft-s{seed}" for model in campaign["train_models"] for seed in seeds
    ]
    missing = [n for n in names if n not in registry]
    if missing:
        raise ValueError(f"campaign arms not in arms.py: {missing}")
    return {n: registry[n] for n in names}


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
}


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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        campaign = load_json(args.campaign) if args.campaign else ROUND1
        registry = campaign_arms(campaign, arms_registry())
        results_root = (
            args.results_root or script.parents[1] / "results" / campaign["results"]
        )
        panel_path = args.panel_agreement or corpus / campaign["panel_agreement"]
        output = args.output or results_root / "corpus-eval-report.md"
        results, signature, panel_values, ledger = collect(
            results_root, registry, args.ledger, panel_path
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report = render(results, signature, panel_values, ledger, panel_path, registry)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output} ({len(results)} arms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
