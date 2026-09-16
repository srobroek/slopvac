# VersioningLit (scout, delivered via IRC after write failures)

Report: C12 AMEND; C1 KEEP (metadata amendment).

Evidence URLs:
- lm-eval task versioning https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/new_task_guide.md (explicit task/group version, bump on breaking config)
- HELM reruns require matching run-entry/schema https://crfm-helm.readthedocs.io/en/v0.5.5/reproducing_leaderboards/
- HELM living reproducible benchmark https://crfm.stanford.edu/helm/
- BIG-bench individually maintained task dirs https://github.com/google/BIG-bench/blob/main/bigbench/benchmark_tasks/README.md
- MQM typology vs scoring model https://www.themqm.org/
- WCAG success criteria/conformance levels vs techniques https://www.w3.org/WAI/standards-guidelines/wcag/
- Vale rule vs repo severity overrides https://github.com/elastic/vale-rules
- promptfoo cache/re-run config https://www.promptfoo.dev/docs/configuration/caching/
- Sclar et al. 2023 https://arxiv.org/html/2310.11324v2: equivalent formatting up to 76 accuracy points (LLaMA2-13B), ~10 average across 50+ tasks/models; GPT-3.5 up to 56, median 6.4 across 320 formats/53 tasks
- Mizrahi et al. 2024 https://aclanthology.org/2024.tacl-1.52/: 6.5M instances, 20 LLMs, 39 tasks; paraphrased instructions yield very different absolute/relative performance

Verdict: PATCH-without-invalidation indefensible; wording changes need rebaseline or equivalence test.

Amend C12: PATCH only non-semantic metadata/typos; any token/order/example/anchor/gate/dimension/threshold/weight/pack/schema change creates a new evaluation identity and invalidates cache unless a paired equivalence study passes. Comparability key must include canonical spine+pack hashes (ordered rule IDs, criteria, discriminators, shots, preservation classes, masks, generator/schema), thresholds/weights config hash, unit-selection hash, model/provider settings, and document/dataset revision, not merely semver + pack set + units.

Unsupported: no precedent for safe wording-only cache compatibility or a universal hash recipe.

Open eval: paired old/new prompts on a frozen stratified corpus with repeats; report finding/severity flip rates with CI; test typo/punctuation/paraphrase equivalence; hash normalization tests.
