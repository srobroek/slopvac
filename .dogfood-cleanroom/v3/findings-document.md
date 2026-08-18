# Document-scope findings: subject.md

Reviewed against the 17 `scope: document` rules in `rules-document.json`.

## tricolon-abuse-remainder
severity: suggestion
scope: document
where: 487-493
quote: "- Bad config.\n- An unknown category name.\n- An unknown rule name.\n- An unloadable ruleset.\n- A broken blocklist."
why: No. Seven identical-shape fragments where the first item subsumes at least three of the others: an unknown category name, an unknown rule name, and a blocklist path that does not load are all "bad config" by the document's own account (lines 210-211 say the config layer rejects unknown category and rule names). The items do not each state a fact the others do not.
fix: Drop the generic "Bad config." bullet and keep only the causes that name a distinct failure, or fold the whole list into one sentence: exit 2 covers a config error, an unknown category or rule name, an unloadable ruleset, a missing target, a broken blocklist, and a stale `reference --check` diff.

## tricolon-abuse-remainder
severity: suggestion
scope: document
where: 289-295
quote: "That choice has two costs, and slopvac pays both in the open:"
why: No. The two parallel bullets are not two instances of the same thing: the first is a real cost (duplicate scopes become a validation error), the second is a mitigation (`--explain-config` names the block that won). The symmetry of the pair is asserted by the lead-in and not carried by the items.
fix: State the one cost as prose and move the `--explain-config` sentence out of the pair, since it is the remedy rather than a second cost.

## listicle-in-a-trench-coat
severity: suggestion
scope: document
where: 27-34
quote: "First, nothing passes in silence. ... Second, a misconfiguration is an error rather than a no-op."
why: Yes. Two consecutive paragraphs enumerate positions in a sequence ("First, ... Second, ...") and neither depends on the other; the second paragraph would read identically if the first were deleted. The prose form is carrying list content.
fix: Convert to a two-item list under the "Two design commitments" lead-in, or drop the ordinal markers and let each commitment be its own short paragraph.

## over-formatting-reflex
severity: suggestion
scope: document
where: 358-364, 474-493 (also 8-12, 335-343, 466-472)
quote: "- Code fences.\n- Inline code.\n- URLs.\n- Front matter."
why: No. Several lists hold no columns and no independent parallel items, only a noun phrase per line where a single sentence says the same thing: the four excluded spans (358-364), the five possible failures (466-472), the seven causes of exit 2 (487-493), and the three ruleset sources (8-12). "Would two sentences of prose say the same thing?" answers yes for each. The four real tables are fine.
fix: Unwrap the single-noun-phrase lists into sentences, e.g. "The `prose` scope leaves out code fences, inline code, URLs, and front matter." Keep bullets only where an item runs to a clause with its own detail, as in the output-format list at 139-150.

## vaporware-description
severity: suggestion
scope: document
where: 354 vs 77
quote: "| `metric` | A counted measurement against a threshold: sentence words, clause boundaries, passive ratio, syllables per word. |"
why: Not for every behaviour. The rule-kind table presents `metric` in the present tense as a working checker, while the sample run at line 77 discloses that five metric rules "have no implementation in either engine, so they did NOT run". That is the mixture the rule targets: the body prose reads as shipped and the unshipped part is admitted in a transcript. I could not verify the remaining present-tense claims against HEAD, since I am read-only on the document.
fix: State the coverage where the kind is described: say in the `metric` row (or a status column) how many metric rules have a checker and how many do not, rather than leaving the gap to a sample transcript.

## elegant-variation
severity: suggestion
scope: document
where: 406-417 and 122/171/311-319
quote: "No wordlist ships with slopvac ... A packaged dictionary enforced as an *allowlist* ... Point `[vocabulary] path` at a file ... slopvac loads the blocklist"
why: Yes, twice. One file is called a wordlist, a dictionary, a blocklist, and `[vocabulary] path` inside eight lines, with no sentence saying they are the same file. Separately, "tier" and "profile" rotate for one referent: `--profile` "Override the configured tier" (122), "`--profile` seeds the tier" (171), "The three shipped profiles" and "The tiers do not form a strict ordering" (311-318).
fix: Pick one name for the file (the config key `vocabulary`, or `blocklist` if that is the shipped word) and use it every time; likewise choose either "profile" or "tier" and state the relationship once if both must exist.

## one-point-dilution
severity: suggestion
scope: document
where: 32-34, 125, 166, 210-211, 415-417, 483, 487-497
quote: "Second, a misconfiguration is an error rather than a no-op."
why: Yes. The "a misconfiguration exits 2 rather than passing silently" argument is made at least six times in fresh clothing: as a design commitment (32-34), as flag notes ("An unknown name exits 2", "An unknown rule id exits 2"), as "slopvac rejects unknown keys" (210), as "a config error rather than a gate that checks nothing in silence" (417), as the exit-code table row (483), and again as the "Causes of exit 2" list plus its closing paragraph (487-497). The later passages add no fact the earlier ones lack.
fix: State the rule once where exit codes are defined, and delete the restatements at 32-34 and 415-417, leaving only the specifics that are new (which layer validates what).

## competing-actor-terms
severity: suggestion
scope: document
where: 19-25, 155-159, 356, 410, 495
quote: "An agentic reviewer that needs a machine-readable source of truth" / "the decidable question a reviewer must answer" / "a human or an agentic reviewer reads one source of truth"
why: Rotation, and the distinction is never drawn. "reviewer", "agentic reviewer", and "human" act on the same output, and line 159's bare "reviewer" cannot be resolved to either. A second rotation covers the audience: "teams" (19), "you"/"your project" (185, 188, 411), "the project" (410, 495), and "anyone" (260) all name whoever configures slopvac.
fix: Use "reviewer" for the role and say once at first use whether it may be a person or an agent; pick one of "you" or "the project" for the configuring actor and replace the rest.

## bare-quantifier-with-figure-available
severity: suggestion
scope: document
where: 46, 457
quote: "hands most mechanical rules to Vale" / "twenty-odd such scores drown out the categories"
why: Yes for both. The document has the numbers: it states 216 packaged rules in 23 categories (333-334) and says `slopvac compile` reports exactly how many rules Vale took (177-183), so "most mechanical rules" withholds a count the tool prints. "twenty-odd" rounds off the 23 categories the same document names. Neither set is unbounded or unmeasured, so no exception applies.
fix: Give the routing count in the Install section ("hands N of the 216 rules to Vale"), and replace "twenty-odd" with 23.

## domain-noun-not-organization-approved
severity: suggestion
scope: document
where: 122, 131, 171, 311-318, 406-417
quote: "`--profile strict\|normal\|relaxed` | Override the configured tier for this run." / "Skip the Vale sub-gate."
why: No. The config schema in this same document is the glossary, and it names the setting `profile` and the section `[vocabulary]`; the prose calls them "tier" and "wordlist"/"blocklist". "Vale sub-gate" (131) appears once and matches nothing in the schema, where the switch is `[vale] enabled`.
fix: Use the schema's own names in prose: `profile` for the setting, `vocabulary` (or a single declared synonym) for the word file, and "Vale" or "the Vale step" instead of "sub-gate".

# Rules that did not fire

- **summary-closer-remainder** — the last section is `## License / Apache-2.0.`, a fact, not a re-list. No closing recap section exists.
- **invented-concept-label** — no title-cased or quoted coinage. "gating density" is bolded but defined in place (426-428); "strictest-wins" and "specificity ranking" are named and then explained (280-287).
- **audience-straddle-remainder** — no term is both glossed and later assumed. ASD-STE100 is expanded once (11) and never re-assumed; the unglossed items (SARIF, `pathspec`, RFC 2119, Pydantic) are consistently unglossed, which is one audience.
- **table-wrapping-one-sentence** — all four tables (120-134, 348-356, 312-316, 479-483) have two or more rows whose cells vary in the same dimension.
- **fabricated-citations-remainder** — the only references are https://vale.sh, ASD-STE100, Orwell's 1946 rules, SARIF 2.1.0, and RFC 2119. All are real, all are cited as facts rather than as support for a number, and none carries a DOI, ISBN, or author-year cite. No claim in the document rests on a source I would have had to fetch to check.
- **padded-symmetry** — no FAQ, Tips, or Troubleshooting section, and section lengths are genuinely uneven (License is one line). The five `slopvac <command>` subsections share an opening formula ("This command ...") and a similar mass, but each carries its own facts, so nothing exists purely to match a sibling.
- **hedged-into-uselessness** — the document asserts throughout. Load-bearing claims (precedence is file order, exit 2 means no trust, the score floor) are stated flat, with no double hedge and no hedged hedge.
- **long-domain-term-without-short-form** — no project-owned term runs past three words outside code spans; the long identifiers (`max_total_per_100_words`, `partialFingerprints`) fall under the code-span exception.

# Summary
- rules evaluated: 17
- rules that fired: 9 (11 findings, tricolon-abuse-remainder twice)
- rules that did not apply: 8

| category | fired rule ids |
| --- | --- |
| ai-tells-structure | tricolon-abuse-remainder (x2), listicle-in-a-trench-coat |
| ai-tells-register | over-formatting-reflex |
| ai-tells-content-shape | vaporware-description, elegant-variation, one-point-dilution |
| prose-discipline | competing-actor-terms, bare-quantifier-with-figure-available |
| ste-words | domain-noun-not-organization-approved |
