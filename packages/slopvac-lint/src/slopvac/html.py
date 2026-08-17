"""The `--format html` report.

WHY A REPORT AND NOT A PRETTIER TERMINAL. The text output answers "did this pass",
and a reader who wants to ACT on a failing run needs three things it cannot give
them at once: which documents are worst, which rules account for the findings, and
what did not run. In a terminal those compete for the same screen, so the useful
one scrolls away. Here they sit side by side and the reader picks.

WHAT DID NOT RUN LEADS. `unchecked` is rendered first, in the loudest style on the
page, and a run that has any is banner-flagged whatever it scored. A high score
from an engine that silently failed to start is the one output this project exists
to prevent, and burying that in a footnote reproduces the failure in a new medium.

One self-contained file, no assets and no network. It is written to a path the
caller names, mailed, attached to a CI artifact, and opened from a file:// URL, all
of which break the moment it fetches a stylesheet. That rules out a CSS framework
and a charting library, so the bars are divs and the styling is one embedded sheet.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from .model import DocumentScore, Severity
from .report import RunSummary

# Score bands, and the words attached to them. The boundaries match the profile
# thresholds (`min_score`: strict 85, normal 70) so a badge never reads "good" on a
# document the gate rejected.
_BANDS = ((85.0, "strong", "good"), (70.0, "fair", "warn"), (0.0, "weak", "bad"))

_SEVERITY_ORDER = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.SUGGESTION: 2}

_STYLE = """
:root {
  --bg: #fbfbfa; --panel: #fff; --ink: #1a1a1a; --muted: #6b6b6b;
  --line: #e4e4e1; --bad: #b4232a; --warn: #9a6700; --good: #1a7f37;
  --accent: #24445c;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181a; --panel: #1e2124; --ink: #e8e8e6; --muted: #9a9a97;
    --line: #33373b; --bad: #f0666d; --warn: #d4a017; --good: #4ac26b;
    --accent: #7fb3d5;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem 1.5rem; background: var(--bg); color: var(--ink);
  font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 68rem; margin: 0 auto; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; }
h2 { font-size: 1.05rem; margin: 2rem 0 .75rem; }
.sub { color: var(--muted); margin: 0 0 1.5rem; font-size: .875rem; }
.panel {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  padding: 1rem 1.25rem; margin-bottom: 1rem;
}
.verdict { display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
.verdict .badge {
  font-size: 1.75rem; font-weight: 700; letter-spacing: .02em;
}
.verdict .score { font-size: 1.75rem; font-weight: 700; }
.good { color: var(--good); } .warn { color: var(--warn); } .bad { color: var(--bad); }
.stats { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: .5rem;
  color: var(--muted); font-size: .875rem; }
.stats b { color: var(--ink); font-variant-numeric: tabular-nums; }
.unchecked { border-left: 4px solid var(--bad); }
.unchecked h2 { margin-top: 0; color: var(--bad); }
.unchecked li { margin-bottom: .4rem; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 52rem) { .cols { grid-template-columns: 1fr; } }
table { width: 100%; border-collapse: collapse; font-size: .875rem; }
th, td { text-align: left; padding: .35rem .5rem; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 600; font-size: .8125rem; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--accent); }
code, .loc { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: .8125rem; }
details { border-bottom: 1px solid var(--line); }
details:last-child { border-bottom: 0; }
summary { cursor: pointer; padding: .5rem 0; display: flex; gap: .75rem;
  align-items: baseline; }
summary::-webkit-details-marker { display: none; }
summary::before { content: "\\25B8"; color: var(--muted); }
details[open] > summary::before { content: "\\25BE"; }
summary .path { font-weight: 600; }
summary .meta { color: var(--muted); font-size: .8125rem; margin-left: auto; }
.sev { font-size: .75rem; font-weight: 700; text-transform: uppercase; }
.msg { display: block; color: var(--muted); }
.reasons { color: var(--bad); font-size: .8125rem; margin: .25rem 0 .5rem; }
.clean { color: var(--muted); font-style: italic; }
footer { color: var(--muted); font-size: .8125rem; margin-top: 2rem;
  border-top: 1px solid var(--line); padding-top: .75rem; }
"""


def _band(score: float) -> tuple[str, str]:
    for floor, word, css in _BANDS:
        if score >= floor:
            return word, css
    return "weak", "bad"


def _e(value: object) -> str:
    """Escape for HTML text.

    EVERY interpolation goes through this. A finding carries the matched source
    text, so a document containing `<script>` would otherwise inject it into the
    report -- and the documents this tool reads are exactly the ones that discuss
    markup.
    """
    return html.escape(str(value), quote=True)


def _bar(value: float, ceiling: float) -> str:
    width = 0.0 if ceiling <= 0 else min(100.0, value / ceiling * 100)
    return f'<div class="bar"><span style="width:{width:.1f}%"></span></div>'


def render_html(
    summary: RunSummary,
    documents: list[DocumentScore],
    version: str,
    *,
    generated: datetime | None = None,
) -> str:
    """One self-contained HTML page for a whole run.

    `generated` is injectable so a test can assert a byte-for-byte page. Defaults to
    now, in UTC, because a report read on another machine in another timezone is the
    normal case.
    """
    stamp = (generated or datetime.now(UTC)).strftime("%Y-%m-%d %H:%M UTC")
    unchecked = [(doc.path, note) for doc in documents for note in doc.unchecked]
    band, css = _band(summary.score)
    verdict = "PASS" if summary.passed else "FAIL"
    verdict_css = "good" if summary.passed else "bad"

    out: list[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>slopvac report</title>",
        f"<style>{_STYLE}</style>",
        "</head><body><main>",
        "<h1>slopvac report</h1>",
        f'<p class="sub">{summary.documents} document(s), '
        f"{summary.words:,} words &middot; generated {_e(stamp)} "
        f"&middot; slopvac {_e(version)}</p>",
    ]

    # --- what did not run, first and loudest -------------------------------
    if unchecked:
        out.append('<section class="panel unchecked">')
        out.append(
            f"<h2>{len(unchecked)} check(s) did not run</h2>"
            "<p>A rule that did not run is indistinguishable from prose that "
            "complies, so the score below is an upper bound and nothing more.</p><ul>"
        )
        for path, note in unchecked:
            out.append(f"<li><code>{_e(path)}</code> &mdash; {_e(note)}</li>")
        out.append("</ul></section>")

    # --- verdict ------------------------------------------------------------
    out.append('<section class="panel"><div class="verdict">')
    out.append(f'<span class="badge {verdict_css}">{verdict}</span>')
    out.append(f'<span class="score {css}">{summary.score:.1f}</span>')
    out.append(f'<span class="sub" style="margin:0">/100 &middot; {band}</span>')
    out.append("</div><div class=stats>")
    for label, value in (
        ("findings", f"{summary.findings}"),
        ("errors", f"{summary.errors}"),
        ("warnings", f"{summary.warnings}"),
        ("suggestions", f"{summary.suggestions}"),
        ("per 100 words", f"{summary.per_100_words:.2f}"),
    ):
        out.append(f"<span>{label} <b>{value}</b></span>")
    out.append("</div></section>")

    # --- documents and categories, side by side ----------------------------
    out.append('<div class="cols">')

    out.append('<section class="panel"><h2>Documents</h2><table>')
    out.append(
        '<tr><th>path</th><th class=num>score</th><th class=num>findings</th>'
        "<th class=num>/100w</th></tr>"
    )
    # Worst first: a reader fixing a repository starts at the bottom of the score.
    for doc in sorted(documents, key=lambda d: (d.score, -d.total_findings)):
        _, doc_css = _band(doc.score)
        flag = " &#9888;" if doc.unchecked else ""
        out.append(
            f"<tr><td><code>{_e(doc.path)}</code>{flag}</td>"
            f'<td class="num {doc_css}">{doc.score:.1f}</td>'
            f"<td class=num>{doc.total_findings}</td>"
            f"<td class=num>{doc.per_100_words:.2f}</td></tr>"
        )
    out.append("</table></section>")

    out.append('<section class="panel"><h2>Categories</h2>')
    # Only the categories that fired. The summary carries all 23 including the
    # zeroes, and listing them buries the twelve that matter under eleven rows of
    # `0` -- the terminal report keeps them behind --verbose for the same reason.
    scored = [c for c in summary.categories if c.findings]
    if scored:
        worst = max(c.findings for c in scored) or 1
        out.append("<table><tr><th>category</th><th class=num>findings</th><th></th></tr>")
        for cat in sorted(scored, key=lambda c: -c.findings):
            out.append(
                f"<tr><td><code>{_e(cat.category)}</code></td>"
                f"<td class=num>{cat.findings}</td>"
                f"<td style='width:40%'>{_bar(cat.findings, worst)}</td></tr>"
            )
        out.append("</table>")
    else:
        out.append('<p class="clean">No category produced a finding.</p>')
    out.append("</section></div>")

    # --- the findings themselves -------------------------------------------
    out.append('<section class="panel"><h2>Findings</h2>')
    if not any(doc.findings for doc in documents):
        out.append('<p class="clean">No findings.</p>')
    for doc in sorted(documents, key=lambda d: (d.score, -d.total_findings)):
        if not doc.findings and not doc.failure_reasons:
            continue
        _, doc_css = _band(doc.score)
        # Open a failing document, and open a passing one when it is the only
        # document: a single-file report that renders as one collapsed line hides
        # the entire reason it was generated.
        state = " open" if not doc.passed or len(documents) == 1 else ""
        out.append(
            f"<details{state}><summary><span class=path>{_e(doc.path)}</span>"
            f'<span class="{doc_css}">{doc.score:.1f}</span>'
            f"<span class=meta>{doc.total_findings} finding(s), "
            f"{doc.words:,} words</span></summary>"
        )
        for reason in doc.failure_reasons:
            out.append(f'<p class="reasons">{_e(reason)}</p>')
        out.append("<table>")
        ordered = sorted(
            doc.findings,
            key=lambda f: (_SEVERITY_ORDER.get(f.severity, 9), f.line, f.rule_id),
        )
        for finding in ordered:
            sev = finding.severity.value
            sev_css = {"error": "bad", "warning": "warn"}.get(sev, "")
            fix = (
                f' &rarr; <code>{_e(finding.replacement)}</code>'
                if finding.replacement
                else ""
            )
            out.append(
                f'<tr><td class="loc">{finding.line}:{finding.column}</td>'
                f'<td><span class="sev {sev_css}">{_e(sev)}</span></td>'
                f"<td><code>{_e(finding.rule_id)}</code>"
                f'<span class="msg">{_e(finding.message)}{fix}</span></td></tr>'
            )
        out.append("</table></details>")
    out.append("</section>")

    out.append(
        "<footer>Scores are per profile: a document that passes at "
        "<code>relaxed</code> may fail at <code>strict</code>. "
        "Rule ids resolve through <code>slopvac explain &lt;rule-id&gt;</code>."
        "</footer>"
    )
    out.append("</main></body></html>")
    return "\n".join(out) + "\n"
