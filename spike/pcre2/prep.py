"""Generate PCRE2-ready patterns, Unicode edge probes, oversized inputs and the case probe."""

import json, re as stdre, sys, unicodedata

P = json.load(open("patterns.json"))
C = json.load(open("corpus.json"))
EX = [t for t in C["texts"][: C["n_examples"]] if t]

# 1. \uXXXX / \UXXXXXXXX -> \x{..}; bounded future-tense lookbehinds.
ESC = stdre.compile(r"(?<!\\)((?:\\\\)*)\\(u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8}))")
FUT_OLD = r"(?:\s+[\w-]+){0,2}\s+)"
FUT_NEW = r"(?:\s{1,3}[\w-]{1,40}){0,2}\s{1,3})"
THAT_OLD = r"(?<=\bthat\s+)"
THAT_NEW = r"(?<=\bthat\s{1,3})"
# Python `regex` has no \x{..} and PCRE2 has no \u/\U, so the Rust loader must translate.
out, bounded, changed = [], [], []
for p in P:
    b = p["pattern"]
    if "future" in p["rule_id"]:
        assert FUT_OLD in b and THAT_OLD in b, p["rule_id"]
        b = b.replace(FUT_OLD, FUT_NEW).replace(THAT_OLD, THAT_NEW)
    s = ESC.sub(
        lambda m: (
            m.group(1) + "\\x{" + (m.group(3) or m.group(4)).lstrip("0").lower() + "}"
        ),
        b,
    )
    if s != p["pattern"]:
        changed.append(p["rule_id"])
    bounded.append(dict(p, pattern=b))
    out.append(dict(p, pattern=s))
json.dump(out, open("patterns_pcre.json", "w"), ensure_ascii=False, indent=0)
json.dump(bounded, open("patterns_bounded.json", "w"), ensure_ascii=False, indent=0)
print("rewritten:", changed)


# 2. Unicode edge probes over the rule examples.
def comb_after_words(t):
    return stdre.sub(r"(\w)\b", "\\1\u0301", t)


def fullwidth(t):
    return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in t)


V = {
    "nbsp": lambda t: t.replace(" ", "\u00a0"),
    "narrow-nbsp": lambda t: t.replace(" ", "\u202f"),
    "thin-space": lambda t: t.replace(" ", "\u2009"),
    "ideographic-space": lambda t: t.replace(" ", "\u3000"),
    "zwsp": lambda t: t.replace(" ", "\u200b"),
    "nel": lambda t: t.replace(" ", "\u0085"),
    "tab-newline": lambda t: t.replace(" ", "\t", 1).replace(" ", "\n", 1),
    "crlf": lambda t: t.replace(". ", ".\r\n") + "\r\n",
    "trailing-newline": lambda t: t + "\n",
    "combining-after-words": comb_after_words,
    "combining-on-e": lambda t: t.replace("e", "e\u0301"),
    "nfd-accented": lambda t: unicodedata.normalize("NFD", t.replace("e", "\u00e9")),
    "precomposed-accented": lambda t: t.replace("e", "\u00e9"),
    "upper": str.upper,
    "title": str.title,
    "swapcase": str.swapcase,
    "long-s": lambda t: t.replace("s", "\u017f"),
    "kelvin": lambda t: t.replace("k", "\u212a"),
    "dotted-I": lambda t: t.replace("I", "\u0130").replace("i", "\u0131"),
    "sharp-s": lambda t: t.replace("ss", "\u00df"),
    "cjk-around": lambda t: (
        "\u4e2d\u6587\uff1a" + t + "\u3002\u65e5\u672c\u8a9e\u306e\u6587\u7ae0"
    ),
    "cjk-glued": lambda t: t.replace(" ", " \u6f22\u5b57"),
    "emoji-around": lambda t: (
        "\U0001f680 "
        + t
        + " \U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466"
    ),
    "emoji-between": lambda t: t.replace(" ", " \U0001f44d\U0001f3fd ", 3),
    "emoji-glued": lambda t: t.replace(" ", "\U0001f525", 2),
    "zwj-glued": lambda t: t.replace(" ", "\u200d", 2),
    "variation-selector": lambda t: t.replace("a", "a\ufe0f"),
    "flag": lambda t: "\U0001f1f3\U0001f1f1 " + t,
    "rtl-marks": lambda t: "\u200f" + t.replace(" ", " \u200e"),
    "fullwidth": fullwidth,
    "greek-sigma": lambda t: (
        t + " \u039f\u0394\u039f\u03a3 \u03bf\u03b4\u03bf\u03c2 \u03c3\u03c2\u03a3"
    ),
    "smart-quotes-dashes": lambda t: (
        t.replace("'", "\u2019").replace('"', "\u201c").replace(" - ", " \u2014 ")
    ),
}
probes, labels = [], []
for name, f in V.items():
    for t in EX:
        v = f(t)
        if v != t:
            probes.append(v)
            labels.append(name)
json.dump(
    dict(texts=probes, labels=labels), open("probes.json", "w"), ensure_ascii=False
)
print("probes:", len(probes))

# 3. Oversized inputs: one ~9 MB document, plus pathological 1 MB runs.
doc = "\n\n".join(C["texts"])
big = [
    (doc + "\n\n") * 5,
    "a" * 1_000_000,
    " " * 1_000_000,
    "word " * 200_000,
    "which " * 170_000 + "will be",
    "that " * 200_000 + "will be",
    "\u00df\U0001f44d\u0301 " * 150_000,
    "x-" * 500_000,
    "very " * 200_000,
]
json.dump(dict(texts=big), open("big.json", "w"), ensure_ascii=False)
print("big:", [len(b) for b in big])

# 4. Case probe: every scalar with a case mapping, and its simple mappings.
cps = set()
for c in range(0x110000):
    if 0xD800 <= c <= 0xDFFF:
        continue
    ch = chr(c)
    for m in (ch.lower(), ch.upper(), ch.casefold(), ch.title()):
        if m != ch:
            cps.add(c)
            if len(m) == 1:
                cps.add(ord(m))
json.dump(sorted(cps), open("caseprobe.json", "w"))
print("caseprobe:", len(cps))
