"""Run the whole differential on this host and write out/summary.json (+ GitHub step summary)."""

import json, os, subprocess, sys, time
from ref import diff, classdiff

BIN = sys.argv[1]
os.makedirs("out", exist_ok=True)
py = sys.executable


def sh(*a, env=None):
    t = time.perf_counter()
    subprocess.run(list(a), check=True, env={**os.environ, **(env or {})})
    return (time.perf_counter() - t) * 1e3


def load(p):
    return json.load(open(p, encoding="utf-8"))


if not os.path.exists("big.json"):
    sh(py, "prep.py")
info = json.loads(
    subprocess.run([BIN, "info"], check=True, capture_output=True, text=True).stdout
)
S = dict(info=info, regex=None, runs={}, diffs={}, timings={})

corpora = {"corpus": "corpus.json", "probes": "probes.json", "big": "big.json"}
for cname, cf in corpora.items():
    to = ["30"] if cname == "big" else []
    for pset in ("patterns", "patterns_bounded"):
        o = f"out/py_{pset}_{cname}.json"
        sh(py, "ref.py", "spans", f"{pset}.json", cf, o, *to)
    for mode in ("jit", "interp") + (("crate",) if cname == "corpus" else ()):
        sh(BIN, "dump", "patterns_pcre.json", cf, f"out/rs_{mode}_{cname}.json", mode)

P = load("patterns_pcre.json")
fut = str(next(i for i, p in enumerate(P) if "future" in p["rule_id"]))
for cname in corpora:
    pyo, pyp = (
        load(f"out/py_patterns_{cname}.json"),
        load(f"out/py_patterns_pcre_{cname}.json"),
    )
    S["regex"] = pyo["regex"]
    S["timings"][f"python_{cname}_ms"] = round(pyp["run_ms"])
    # bounded future-tense: Python original vs Python bounded (domain change only)
    dom = diff(
        pyo,
        dict(
            matches={
                k: [[int(t), s] for t, s in v.items()]
                for k, v in pyp["matches"].items()
            },
            compile_errors=[],
            runtime_errors=[],
        ),
    )
    S["diffs"][f"bounded_domain_{cname}"] = dict(
        mismatched=dom["mismatched"], detail=dom["detail"]
    )
    for mode in ("jit", "interp", "crate"):
        f = f"out/rs_{mode}_{cname}.json"
        if not os.path.exists(f):
            continue
        rs = load(f)
        S["timings"][f"rust_{mode}_{cname}_ms"] = round(rs["run_ms"])
        S["runs"][f"{mode}_{cname}"] = dict(
            jit_patterns=rs["jit_patterns"],
            compile_errors=rs["compile_errors"],
            runtime_errors=rs["runtime_errors"][:10],
            n_runtime_errors=len(rs["runtime_errors"]),
            n_matches=rs["n_matches"],
            limits=rs["limits"],
        )
        S["diffs"][f"{mode}_vs_py_bounded_{cname}"] = diff(pyp, rs)
        S["diffs"][f"{mode}_vs_py_original_{cname}"] = {
            k: v for k, v in diff(pyo, rs).items() if k != "detail"
        } | {
            "mismatched_patterns": [
                P[int(k)]["rule_id"] for k in diff(pyo, rs)["detail"]
            ]
        }
    a, b = load(f"out/rs_jit_{cname}.json"), load(f"out/rs_interp_{cname}.json")
    S["diffs"][f"jit_vs_interp_{cname}"] = a["matches"] == b["matches"]

sh(py, "ref.py", "classes", "caseprobe.json", "out/py_classes.json")
sh(BIN, "classes", "caseprobe.json", "out/rs_classes.json")
S["classes"] = classdiff(load("out/py_classes.json"), load("out/rs_classes.json"))
sh(BIN, "limits", "out/limits.json")
S["limits"] = load("out/limits.json")["rows"]
json.dump(
    S, open("out/summary.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False
)

# short human summary
d = S["diffs"]
lines = [
    f"### {info['target']} PCRE2 {info['pcre2_version']} (Unicode {info['unicode_version']}), JIT={info['jit_configured']}, regex {S['regex']}",
    "",
]
for cname in corpora:
    for mode in ("jit", "interp", "crate"):
        k = f"{mode}_vs_py_bounded_{cname}"
        if k in d:
            x = d[k]
            lines.append(
                f"- {cname}/{mode}: identical {x['identical']}, mismatched {x['mismatched']}, compile-failed {x['compile_failed']}, "
                f"rust errors {x['rs_errors']}, py timeouts {x['py_errors']}; vs original patterns: "
                f"{d[f'{mode}_vs_py_original_{cname}']['mismatched_patterns']}; time {S['timings'][f'rust_{mode}_{cname}_ms']} ms"
            )
    lines.append(
        f"- {cname}: jit==interp {d[f'jit_vs_interp_{cname}']}; bounded-domain mismatches {d[f'bounded_domain_{cname}']['mismatched']}; python {S['timings'][f'python_{cname}_ms']} ms"
    )
for k, v in S["classes"].items():
    lines.append(
        f"- class {k}: "
        + json.dumps(
            {a: b for a, b in v.items() if a.startswith("n_") or a in ("py", "rs")}
        )
    )
lines.append("")
lines += [
    f"| {r['case']} | {r['engine']} | {r['limits']} | {r['ms']:.1f} ms | {r['outcome']} |"
    for r in S["limits"]
]
md = "\n".join(lines)
print(md)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8").write(md + "\n")
