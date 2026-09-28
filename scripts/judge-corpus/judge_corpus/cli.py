"""Command-line orchestration for source, brief, and generation stages."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .batch import (
    collect_briefs,
    collect_generated,
    parse_output,
    prepare_briefs,
    prepare_generation,
)
from .bedrock import download_outputs, provision, submit, upload, upload_text, wait
from .common import read_jsonl, token_estimate, write_jsonl
from .roster import build_roster
from .sources import build_sources


def root_from_args(value: str | None) -> Path:
    return Path(value or Path(__file__).resolve().parents[1]).resolve()


def cmd_sources(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    accepted, decisions = build_sources(root, args.limit)
    print(
        json.dumps(
            {
                "accepted": len(accepted),
                "dedup_decisions": len(decisions),
                "duplicates": sum(d["decision"] != "accepted" for d in decisions),
            }
        )
    )


def cmd_roster(args: argparse.Namespace) -> None:
    data = build_roster(root_from_args(args.root))
    print(
        json.dumps(
            {
                "models": len(data["models"]),
                "candidates": sum(
                    m.get("batch_supported") is True for m in data["models"]
                ),
            }
        )
    )


def cmd_provision(args: argparse.Namespace) -> None:
    resources = provision(root_from_args(args.root))
    print(
        json.dumps(
            {"bucket_arn": resources["bucket_arn"], "role_arn": resources["role_arn"]}
        )
    )


def cmd_prepare_briefs(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    local, input_tokens, output_tokens = prepare_briefs(
        root, limit=args.limit, model_id=args.model
    )
    for source in read_jsonl(root / "sources" / "human.jsonl"):
        from .batch import _source_text

        upload_text(root, _source_text(root, source), source["s3_key"])
    uri = upload(
        root, local, f"inputs/briefs/{local.stem}-{args.limit or 'full'}.jsonl"
    )
    print(
        json.dumps(
            {
                "input": str(local),
                "s3_uri": uri,
                "records": sum(1 for _ in read_jsonl(local)),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )
    )


def cmd_submit_briefs(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"input does not exist: {input_path}")
    input_tokens = sum(
        token_estimate(json.dumps(row["modelInput"])) for row in read_jsonl(input_path)
    )
    records = sum(1 for _ in read_jsonl(input_path))
    resources = json.loads((root / "ledgers" / "resources.json").read_text())
    uri = args.s3_uri or upload(
        root, input_path, f"inputs/{args.stage}/{input_path.name}"
    )
    job = submit(
        root,
        stage=args.stage,
        model_id=args.model,
        input_s3_uri=uri,
        input_tokens=input_tokens,
        output_tokens=records * 800,
        output_key=f"outputs/{args.stage}/{input_path.stem}/",
    )
    print(json.dumps(job))


def cmd_collect_briefs(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    raw = root / "briefs" / "raw-output.jsonl"
    lines = download_outputs(root, args.prefix, raw)
    accepted, rejected = collect_briefs(root, lines, model_id=args.model)
    print(
        json.dumps(
            {
                "accepted": len(accepted),
                "rejected": len(rejected),
                "raw": str(raw),
                "retry_input": str(root / "briefs" / "retry-input.jsonl"),
            }
        )
    )
    if rejected:
        source_map = {
            row["id"]: row for row in read_jsonl(root / "sources" / "human.jsonl")
        }
        retry = []
        for row in rejected:
            source = source_map.get(row.get("source_id"))
            if source:
                from .batch import brief_prompt, model_body, _source_text

                retry.append(
                    {
                        "recordId": source["id"],
                        "modelInput": model_body(
                            args.model,
                            brief_prompt(source, _source_text(root, source)),
                            max_tokens=800,
                        ),
                    }
                )
        write_jsonl(root / "briefs" / "retry-input.jsonl", retry)
    for brief in accepted:
        upload_text(
            root,
            json.dumps(brief["brief"], ensure_ascii=False),
            f"briefs/{brief['id']}.json",
        )


def cmd_prepare_generation(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    prepared = prepare_generation(root, limit=args.limit)
    result = {}
    for model, (path, input_tokens, output_tokens) in prepared.items():
        if not any(True for _ in read_jsonl(path)):
            continue
        uri = upload(root, path, f"inputs/generation/{path.name}")
        result[model] = {
            "input": str(path),
            "s3_uri": uri,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    print(json.dumps(result))


def cmd_submit_generation(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    input_path = Path(args.input).resolve()
    uri = args.s3_uri or upload(
        root, input_path, f"inputs/generation/{input_path.name}"
    )
    records = sum(1 for _ in read_jsonl(input_path))
    input_tokens = sum(
        token_estimate(json.dumps(row["modelInput"])) for row in read_jsonl(input_path)
    )
    job = submit(
        root,
        stage=f"generation-{args.model.rsplit('/', 1)[-1]}",
        model_id=args.model,
        input_s3_uri=uri,
        input_tokens=input_tokens,
        output_tokens=records * 1200,
        output_key=f"outputs/generation/{input_path.stem}/",
    )
    print(json.dumps(job))


def cmd_collect_generation(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    raw = (
        root
        / "generated"
        / "raw"
        / f"{args.model.rsplit('/', 1)[-1].replace(':', '_')}.jsonl"
    )
    lines = download_outputs(root, args.prefix, raw)
    accepted, rejected = collect_generated(root, lines, model_id=args.model)
    print(
        json.dumps(
            {
                "model": args.model,
                "accepted": len(accepted),
                "rejected": len(rejected),
                "raw": str(raw),
            }
        )
    )
    accepted_ids = {row["id"]: row for row in accepted}
    for line in lines:
        row = accepted_ids.get(line.get("recordId"))
        if row:
            upload_text(root, parse_output(line), row["s3_key"])


def cmd_wait(args: argparse.Namespace) -> None:
    detail = wait(root_from_args(args.root), args.job_arn, poll_seconds=args.poll)
    print(
        json.dumps(
            {
                "job_arn": args.job_arn,
                "status": detail.get("status"),
                "failure_message": detail.get("failureMessage"),
            }
        )
    )


def cmd_report(args: argparse.Namespace) -> None:
    root = root_from_args(args.root)
    human = list(read_jsonl(root / "sources" / "human.jsonl"))
    generated = list(read_jsonl(root / "generated" / "manifest.jsonl"))
    dedup = list(read_jsonl(root / "sources" / "dedup.jsonl"))
    rejected_briefs = list(read_jsonl(root / "briefs" / "rejections.jsonl"))
    rejected_generated = list(read_jsonl(root / "generated" / "rejections.jsonl"))
    lines = [
        "# Slopvac corpus build report",
        "",
        "This report is generated from the committed manifests.",
        "",
        "## Counts",
        "",
        f"- Human accepted: **{len(human)}**",
        f"- Generated accepted: **{len(generated)}**",
        f"- Dedup rejected: **{sum(row.get('decision') == 'rejected_duplicate' for row in dedup)}**",
        f"- Brief leak/parse rejections: **{len(rejected_briefs)}**",
        f"- Generated leak/empty rejections: **{len(rejected_generated)}**",
        "",
        "### Human by genre and source family",
        "",
        "| Genre | Source family | Count |",
        "|---|---|---:|",
    ]
    for (genre, family), count in sorted(
        Counter((row["genre"], row["source_family"]) for row in human).items()
    ):
        lines.append(f"| {genre} | {family} | {count} |")
    lines += [
        "",
        "### Generated by genre, vendor, and tier",
        "",
        "| Genre | Vendor | Tier | Count |",
        "|---|---|---|---:|",
    ]
    brief_map = {
        row["id"]: row for row in read_jsonl(root / "briefs" / "manifest.jsonl")
    }
    for (genre, vendor, tier), count in sorted(
        Counter(
            (
                brief_map.get(row["brief_id"], {})
                .get("brief", {})
                .get("genre", "unknown"),
                row["vendor"],
                row["tier"],
            )
            for row in generated
        ).items()
    ):
        lines.append(f"| {genre} | {vendor} | {tier} | {count} |")
    lines += ["", "## Licences", "", "| Licence | Count |", "|---|---:|"]
    for licence, count in sorted(Counter(row["licence"] for row in human).items()):
        lines.append(f"| {licence} | {count} |")
    ledger = root / "ledgers" / "cost-ledger.json"
    total = (
        json.loads(ledger.read_text()).get("total_estimate_usd", 0.0)
        if ledger.exists()
        else 0.0
    )
    lines += [
        "",
        f"## Bedrock cost",
        "",
        f"Estimated batch cost: **${total:.4f} / $200.00 cap**.",
        "",
        "## AWS resources",
        "",
    ]
    resources = root / "ledgers" / "resources.json"
    if resources.exists():
        data = json.loads(resources.read_text())
        lines.extend(
            [
                f"- Bucket: `{data.get('bucket_arn')}`",
                f"- Role: `{data.get('role_arn')}`",
                f"- Jobs: {len(data.get('jobs', []))}",
            ]
        )
    else:
        lines.append("- No AWS resources recorded.")
    (root / "corpus-build-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(str(root / "corpus-build-report.md"))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="judge-corpus")
    p.add_argument("--root", help="scripts/judge-corpus directory")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sources")
    s.add_argument("--limit", type=int)
    s.set_defaults(func=cmd_sources)
    s = sub.add_parser("roster")
    s.set_defaults(func=cmd_roster)
    s = sub.add_parser("provision")
    s.set_defaults(func=cmd_provision)
    s = sub.add_parser("prepare-briefs")
    s.add_argument("--limit", type=int)
    s.add_argument("--model", default="amazon.nova-lite-v1:0")
    s.set_defaults(func=cmd_prepare_briefs)
    s = sub.add_parser("submit-briefs")
    s.add_argument("--input", required=True)
    s.add_argument("--model", default="amazon.nova-lite-v1:0")
    s.add_argument("--stage", default="briefs")
    s.add_argument("--s3-uri")
    s.set_defaults(func=cmd_submit_briefs)
    s = sub.add_parser("collect-briefs")
    s.add_argument("--prefix", required=True)
    s.add_argument("--model", default="amazon.nova-lite-v1:0")
    s.set_defaults(func=cmd_collect_briefs)
    s = sub.add_parser("prepare-generation")
    s.add_argument("--limit", type=int)
    s.set_defaults(func=cmd_prepare_generation)
    s = sub.add_parser("submit-generation")
    s.add_argument("--input", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--s3-uri")
    s.set_defaults(func=cmd_submit_generation)
    s = sub.add_parser("collect-generation")
    s.add_argument("--prefix", required=True)
    s.add_argument("--model", required=True)
    s.set_defaults(func=cmd_collect_generation)
    s = sub.add_parser("wait")
    s.add_argument("--job-arn", required=True)
    s.add_argument("--poll", type=float, default=30)
    s.set_defaults(func=cmd_wait)
    s = sub.add_parser("report")
    s.set_defaults(func=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:
        print(f"judge-corpus: {exc}", file=sys.stderr)
        return 1
    return 0
