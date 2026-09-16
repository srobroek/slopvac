# GatesLit (scout, delivered via IRC after write failures)

C3 AMEND: selective classification makes abstain an explicit reject action (Geifman & El-Yaniv, arXiv:1705.08500); Kadavath et al. arXiv:2207.05221 show larger models calibrated on MC/TF and P(I know), RLHF naively miscalibrated, so confidence can gate only when calibrated, never a dimension.

C4 AMEND: ALCE (https://aclanthology.org/2023.emnlp-main.398) and Bohnet et al. (arXiv:2212.08037) separate attribution from correctness; exact substring is mechanically sound. Stanford coreference lecture (https://web.stanford.edu/class/archive/cs/cs224n/cs224n.1162/handouts/cs224n-lecture11-coreference.pdf) supports an antecedent/anaphor pair for non-local defects; arity must be rule-specific; deterministic rules need not quote.

C8 AMEND: Wen et al. survey (arXiv:2407.18418) taxonomy (query/model/human values) indicates the closed list is incomplete; add safety/policy refusal, unsupported language/input, malformed/invalid unit, distribution shift/unknown domain, missing/insufficient context; keep no_quote, needs_repo_fact, ambiguous_unit, unit_out_of_scope. R-Tuning (arXiv:2311.09677) supports explicit I-don't-know. SelectiveNet (arXiv:1901.09192) risk-coverage supports gating over weighted uncertainty.

Weller et al. EACL 2024 (https://aclanthology.org/2024.eacl-long.140/) supports quote prompting; no universal numeric fabricated-span reduction found. No exact-substring reduction number located: UNSUPPORTED.
