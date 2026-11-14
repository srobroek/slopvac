import json, glob, regex as re
from slopvac.rules import load_ruleset
from slopvac.engine import rule_pattern
from slopvac.model import RuleKind

rs = load_ruleset()
rules = rs.rules if hasattr(rs, "rules") else list(rs)
out = []
ex = []
for r in rules:
    if r.kind in (RuleKind.TOKENS, RuleKind.PATTERN, RuleKind.SUBSTITUTION):
        p = rule_pattern(r)
        if p is None:
            continue
        out.append(
            dict(
                rule_id=r.qualified_id,
                source_kind=getattr(r.kind, "value", str(r.kind)),
                pattern=p.pattern,
                flags=int(p.flags),
                ignore_case=bool(r.ignore_case),
            )
        )
        for e in r.examples:
            ex += [e.bad, e.good]
json.dump(out, open("patterns.json", "w"), ensure_ascii=False, indent=0)
T = "/private/var/folders/8d/02tkxcq55qzfyj7_z_ktft1r0000gq/T/opencode/"
docs = []
files = glob.glob(T + "detector-proto/**/*.md", recursive=True) + [
    T + "synxis/before.md",
    T + "synxis/after.md",
]
for f in files:
    t = open(f, encoding="utf-8", errors="replace").read()
    docs += [p for p in re.split(r"\n\s*\n", t) if p.strip()]
texts = [x for x in ex if x] + docs
json.dump(
    dict(n_examples=len(ex), texts=texts), open("corpus.json", "w"), ensure_ascii=False
)
print(len(out), len(texts), len(files), sorted({o["flags"] for o in out}))
