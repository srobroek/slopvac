"""Python `regex` reference (the shipping 2.x engine) and the differential against Rust outputs."""

import json, sys, time, regex


def spans(patfile, corpusfile, out, timeout=None):
    P = json.load(open(patfile))
    T = json.load(open(corpusfile))["texts"]
    res, errs, per = {}, [], {}
    t0 = time.perf_counter()
    for pi, p in enumerate(P):
        r = regex.compile(p["pattern"], p["flags"])
        tp = time.perf_counter()
        d = {}
        for ti, t in enumerate(T):
            try:
                s = [[m.start(), m.end()] for m in r.finditer(t, timeout=timeout)]
            except TimeoutError:
                errs.append([pi, ti, f"timeout {timeout}s"])
                continue
            if s:
                d[str(ti)] = s
        per[str(pi)] = (time.perf_counter() - tp) * 1e3
        res[str(pi)] = d
    ms = (time.perf_counter() - t0) * 1e3
    print(
        f"python {patfile} {corpusfile}: {ms:.0f}ms, {len(errs)} timeouts",
        file=sys.stderr,
    )
    json.dump(
        dict(
            matches=res,
            errors=errs,
            run_ms=ms,
            per_pattern_ms=per,
            regex=regex.__version__,
        ),
        open(out, "w"),
    )


def classes(caseprobe, out):
    allc = "".join(chr(c) for c in range(0x110000) if not 0xD800 <= c <= 0xDFFF)
    F = regex.V0 | regex.UNICODE
    res = {}
    for cls in [
        r"\w",
        r"\s",
        r"\d",
        r"\b",
        r"[[:alpha:]]",
        r"(?i)[a-z]",
        r"(?m)$",
        r"$",
    ]:
        ms = regex.finditer(cls, allc, F)
        res[cls] = [
            m.start() if ("$" in cls or cls == r"\b") else ord(m.group()) for m in ms
        ]
    probe = json.load(open(caseprobe))
    hay = "".join(chr(c) for c in probe)
    res["caseless"] = {
        str(c): sorted(
            ord(m.group())
            for m in regex.finditer("\\x{%x}" % c, hay, F | regex.IGNORECASE)
        )
        for c in probe
    }
    json.dump(res, open(out, "w"))


def diff(py, rs):
    """Per-pattern comparison; texts where either side errored are excluded and counted."""
    P, R = py["matches"], rs["matches"]
    cerr = {e[0] for e in rs["compile_errors"]}
    rerr, perr = {}, {}
    for pi, ti, _ in rs["runtime_errors"]:
        rerr.setdefault(str(pi), set()).add(str(ti))
    for pi, ti, _ in py.get("errors", []):
        perr.setdefault(str(pi), set()).add(str(ti))
    ident = mism = 0
    bad = {}
    for pi in P:
        if pi not in R:
            continue
        rs_ = {str(ti): sp for ti, sp in R[pi]}
        skip = rerr.get(pi, set()) | perr.get(pi, set())
        b = [
            ti
            for ti in set(rs_) | set(P[pi])
            if ti not in skip and rs_.get(ti) != P[pi].get(ti)
        ]
        if b:
            mism += 1
            ti = min(b, key=int)
            bad[pi] = dict(n=len(b), ti=ti, py=P[pi].get(ti), rs=rs_.get(ti))
        else:
            ident += 1
    return dict(
        identical=ident,
        mismatched=mism,
        compile_failed=len(cerr),
        rs_errors=len(rs["runtime_errors"]),
        py_errors=len(py.get("errors", [])),
        detail=bad,
    )


def classdiff(py, rs):
    out = {}
    for k in py:
        if k == "caseless":
            d = {c: (py[k][c], rs[k].get(c)) for c in py[k] if py[k][c] != rs[k].get(c)}
            out[k] = dict(n_diff=len(d), sample={c: d[c] for c in list(d)[:40]})
        else:
            a, b = set(py[k]), set(rs[k])
            out[k] = dict(
                py=len(a),
                rs=len(b),
                only_py=sorted(a - b)[:60],
                only_rs=sorted(b - a)[:60],
                n_only_py=len(a - b),
                n_only_rs=len(b - a),
            )
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "spans":
        spans(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            float(sys.argv[5]) if len(sys.argv) > 5 else None,
        )
    elif cmd == "classes":
        classes(sys.argv[2], sys.argv[3])
    elif cmd == "diff":
        print(
            json.dumps(
                diff(json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))),
                ensure_ascii=False,
            )
        )
