# slopvac judge corpus builder

This project builds provenance-only human source pointers and matched document generations for slopvac local judging. Source text, briefs, and generated text stay in the private S3 bucket or the gitignored `.cache/` directory.

## Install

```sh
cd scripts/judge-corpus
uv sync --locked
```

Use AWS profile `sjors+ig-genai-Admin` in account `536697262379` and region `us-east-1`. The profile must be allowed to create one tagged private S3 bucket, one Bedrock batch service role, and Bedrock batch jobs.

## Reproduce

Run the smoke corpus with 100 sources so the Bedrock batch minimum is met. The commands create a 100-source manifest, a roster, one Stage 1 batch input, and a Stage 2 batch input.

```sh
cd scripts/judge-corpus
uv run judge-corpus sources --limit 100
uv run judge-corpus roster
uv run judge-corpus provision
uv run judge-corpus prepare-briefs --limit 100 --model amazon.nova-lite-v1:0
uv run judge-corpus submit-briefs --input briefs/input.jsonl --model amazon.nova-lite-v1:0 --stage smoke-briefs
uv run judge-corpus wait --job-arn ARN_FROM_THE_PREVIOUS_COMMAND
uv run judge-corpus collect-briefs --prefix outputs/smoke-briefs/INPUT_STEM --model amazon.nova-lite-v1:0
uv run judge-corpus prepare-generation --limit 100
```

After inspecting the smoke report, rebuild the full manifest and submit each generation input file sequentially. `prepare-generation` assigns every brief to two models with deterministic vendor and tier rotation.

```sh
uv run judge-corpus sources --limit 3000
uv run judge-corpus prepare-briefs --limit 3000 --model amazon.nova-lite-v1:0
uv run judge-corpus submit-briefs --input briefs/input.jsonl --model amazon.nova-lite-v1:0 --stage briefs
uv run judge-corpus wait --job-arn ARN_FROM_THE_PREVIOUS_COMMAND
uv run judge-corpus collect-briefs --prefix outputs/briefs/INPUT_STEM --model amazon.nova-lite-v1:0
uv run judge-corpus prepare-generation --limit 3000
```

For each model entry printed by `prepare-generation`, submit its JSONL input and wait for completion before collecting it:

```sh
uv run judge-corpus submit-generation --input generated/inputs/MODEL.jsonl --model MODEL_ID
uv run judge-corpus wait --job-arn ARN_FROM_THE_PREVIOUS_COMMAND
uv run judge-corpus collect-generation --prefix outputs/generation/MODEL --model MODEL_ID
```

The submit command estimates input and output tokens at the published on-demand price with the documented batch discount. It refuses a job that would take the ledger above the USD 200 cap. It also refuses models without a recorded price.

## Labels: rule example bank, constructions, teacher panel, export

These stages build the labelled judging items. All paid calls run on demand and are recorded in the ledger. `--max-usd` and `--max-spend` refuse a run whose pre-run estimate is above the limit you give.

```sh
uv run --frozen judge-corpus bank generate --max-usd 22
uv run --frozen judge-corpus bank verify --max-usd 25
uv run --frozen judge-corpus items draft-questions --max-usd 5
uv run --frozen judge-corpus items build --include-generated --shard 0/4   # and 1/4, 2/4, 3/4
uv run --frozen judge-corpus items build --merge-shards 4
uv run --frozen judge-corpus panel prepare --max-spend 45
uv run --frozen judge-corpus panel submit --on-demand
uv run --frozen judge-corpus panel collect
uv run --frozen python label_sheets.py --low-confidence 0.9 --prefix PREFIX --prefill items/adjudication/OLD-lint-findings-*.csv
uv run --frozen judge-corpus items import-labels --origin llm-review-consensus CONSENSUS_SHEETS...
uv run --frozen judge-corpus items import-labels SHEETS...
uv run --frozen judge-corpus items export --balance oversample --publish BUILD_ID --sheets PREFIX
uv run --frozen judge-corpus items export --min-confidence 0.9 --balance oversample --publish BUILD_ID --sheets PREFIX
uv run --frozen judge-corpus items export --balance oversample --variant human-only --drop-train-origin llm-review-consensus --publish BUILD_ID --sheets PREFIX
uv run --frozen python -c 'from pathlib import Path; from judge_corpus.llm_review import run_review, write_label_queue; run_review(Path("."), prefix="PREFIX"); write_label_queue(Path("."), prefix="PREFIX")'
```

- `bank generate` asks Sonnet 5 for bad, good, tricky, and near-miss passages for every current lint rule and every judgement rule, spread across the five corpus genres.
- `bank verify` keeps a lint-rule passage only when `slopvac lint` behaves as intended and gpt-oss and Sonnet both give the intended verdict. For bad passages, the rule must fire and both judges must call the finding a real defect. For tricky passages, the rule must fire and both must call the finding a false positive. For good and near-miss passages, the rule must not fire and both must judge the text acceptable. A judgement-rule passage is kept when both judges agree with its intended answer. The bank itself is private: it is stored in `.cache/bank/bank.jsonl` and under `s3://…/bank/`. The committed `items/bank-manifest.json` records the rule descriptions and the per-rule counts of kept and rejected passages.
- `items build --merge-shards N` inserts kept bank passages into human host text at sentence, paragraph, and document granularity. Finding confirmation gets real-defect items from bad passages and false-positive items from tricky passages. Semantic detection gets true items from bad passages, and false items from good passages, near-miss passages, and clean host controls. Near-duplicate bank passages share a split. Held-out rules go to test only. The build drops any construction whose host span or inserted passage near-duplicates, by shingle Jaccard ≥ 0.5, a construction in another split. It also trims bank constructions until each split holds about as many items of each class per role.
- `items draft-questions` asks Opus 5.5 to restate every semantic-detection rule as one plain yes/no question about the highlighted text (yes means the defect is there), with a one-line Yes example and No example. The result, `items/semantic-questions.yml`, is committed and was checked by hand against each rule's original question and examples. A re-draft only adds missing rules. The training exports, the panel and the review sheets all ask these questions. The exception codes that the rule files fold into `judgement_question` are stripped when the rules are read. The rules listed in `EXCLUDED_JUDGEMENT_RULES` (`judge_corpus/items.py`) get no semantic items, because their question needs context an item cannot carry, such as a code diff, the user's request, cited sources, or a project glossary or vocabulary. They keep their bank passages, and held-out rules are still drawn from all judgement rules.
- Every semantic item has a region, `question.region`, given as offsets into `state.text`. The panel, the exports and the review sheets mark it [[like this]]. For bank-inserted items (bad, good, near-miss) and for judgement-example positives, the region is the inserted passage. Gold positives get the sentence holding the defect span. Clean controls and unseeded items get a deterministic run of whole sentences in a prose paragraph, about as long as the rule's bank passages. A region needs at least 6 words of prose; headings, fences, markup, list numbering, markdown link-reference definitions (`[label]: url`) and lines that hold only a URL do not count. A failing bank passage or control is dropped. A failing unseeded span is resampled from up to 3 anchor paragraphs. The build reports the drops as `semantic_regions` and `dropped_region_*`.
- `panel prepare` samples train items for the teacher panel and adds `--anchors` train constructions with known labels. The panel prompt gives the rule's description and four to six labelled bank passages, never the item's own passage. `panel collect` aggregates the votes with semi-supervised Dawid-Skene per role, with the anchors fixing each teacher's confusion matrix. It writes `label`, `label_confidence` (the posterior), and `label_origin=teacher-panel`.
- `label_sheets.py` writes `items/adjudication/PREFIX-{lint-findings,semantic}-{test,calibration,disagreement}.csv`, filled through the `answer` and `second_answer` columns. The disagreement sheet holds 300 train items, stratified by rule, where the teachers split or the posterior is below `--low-confidence`. Semantic rows show the question, its Yes and No examples, the highlighted text, and the passage with the region marked. `--prefill` copies answers from earlier lint-findings sheets by item id. Run it before `import-labels`.
- `llm_review.run_review` asks Opus, Sol, DeepSeek and Grok every row of the PREFIX sheets three times and writes `llm-PREFIX-*.csv`. `write_label_queue` writes `label-queue.csv` and `label-queue.html` with the rows a person still has to answer. A row is settled, and left out, when at least 11 of the 12 votes give the same definite answer and no run flagged it ambiguous. Rows a person has already answered are left out too. `apply_label_queue` copies the y/n/u answers back into the PREFIX sheets.
- `items import-labels` merges answered sheet rows into the splits as `label_origin=human-adjudication`. With `--origin llm-review-consensus`, the `answer` column holds the consensus of settled LLM-review rows; those labels replace teacher-panel labels but never a human label, whatever the import order.
- `items export` writes `items/export/<variant>/`. `--min-confidence` drops teacher-panel labels below that posterior. `--drop-train-origin ORIGIN` (repeatable, needs `--variant`) leaves train labels of that `label_origin` out, as if the rows were unlabelled; dev, calibration and test keep them, so a label-source ablation shares the full variant's test and calibration bytes. `--balance oversample` repeats minority-class teacher-panel rows in train, with at most 8 copies of any row. Copies have ids of the form `<id>~<n>`. `export-manifest.json` records the class counts, the sampling weights, the dropped train labels by origin, and per-rule class counts per split. `--publish BUILD_ID` uploads the variant and the sheets and records them in `items/export-index.json`.

## Blind evaluation set

The blind set tests whether lint and the judges separate human from generated text on documents the judges never trained on. `judge_corpus/blind.py` builds it and `judge_corpus/blind_report.py` analyses the eval predictions. Text stays in `.cache/blind/` and under `s3://…/blind/`. The committed `blind/manifest.json` records pointers, digests and counts only.

```sh
export SLOPVAC_LINT_ROOT=/path/to/slopvac-at-the-lint-commit
uv run --frozen judge-corpus blind sources
uv run --frozen judge-corpus blind briefs --max-usd 5
uv run --frozen judge-corpus blind generate --max-usd 40
uv run --frozen judge-corpus blind items --build-id BLIND_ID --smoke 5:10
uv run --frozen judge-corpus blind report --build-id BLIND_ID --lint-only
uv run --frozen judge-corpus blind items --build-id BLIND_ID --publish
uv run --frozen judge-corpus blind manifest --build-id BLIND_ID
uv run --frozen judge-corpus blind report --build-id BLIND_ID --predictions ARM=results/CAMPAIGN/ARM/results/predictions/ARM.jsonl ... --out blind/REPORT-blind.md
```

- `blind sources` samples about 40 units per genre. The units come from the source families of `sources/human.jsonl`, at the same pinned commits and the same Stack Exchange dump, plus RFCs and Wikipedia revisions. It skips every file, RFC, post and page that a corpus source of any build came from. A unit must have been last revised before 2022-01-01. For git files that date is the last commit touching the file, from the GitHub API. The repository licence is checked through the GitHub licence API at the pinned commit. Stack Exchange posts take the licence that applied on their last-edit date. A unit is rejected when its word 5-gram shingles near-duplicate any cached corpus source unit, generated document, bank passage, item text or admitted blind unit. Near-duplicate means a Jaccard of at least 0.5, at least half of the unit found in one text, or at least 80% of an existing passage of 25 or more shingles found in the unit. Change-comms units may be as short as 150 words, because the corpus already used every release note of 300 words or more. `.cache/blind/sources/admission.json` counts the admitted units, and the rejected ones by reason.
- `blind briefs` and `blind generate` run the corpus brief and generation stages (`batch.py`) on the root `.cache/blind/`. They use the same brief model, the vendor and tier rotation (without the models `generated/routes.json` marks skipped) and the source leak filter. Every call runs on demand and is recorded in `ledgers/cost-ledger.json`. When a brief's generation fails or leaks, the next model in the rotation takes its place, from a vendor the brief's other document does not already have; this runs for up to two rounds. Generated documents that near-duplicate corpus text are dropped as well.
- `blind items` runs `slopvac lint` at `SLOPVAC_LINT_ROOT` on every blind document. It writes a finding-confirmation item for every finding. It adds semantic-detection items for up to `--regions` (default 3) seeded prose regions per document, and asks every kept judgement rule about each region. The items use the export format and go to `.cache/blind/builds/BLIND_ID/test.jsonl`. Their labels are unknown, so each row carries a placeholder label (choice `no-defect`, yes/no `false`) and `label_origin=blind-unlabelled`; the eval's `pilot/metrics.py` never scores such rows. `--smoke H:G` builds only H human documents and G of their generated matches. `--publish` uploads the test file to both regional buckets. It also uploads an export manifest that pairs the blind test file with the v5b calibration split and writes `blind/campaign-BLIND_ID.json`. Copy that eval-only campaign, which reuses the v5b-full checkpoints, into `scripts/judge-sagemaker/campaigns/` to run the judges.
- `blind report` computes per-document scores: the lint rate (findings per 100 words), the confirmed rate (findings the judge calls a real defect at p ≥ 0.5, per 100 words) and the semantic yes rate. For each score it reports the AUC of generated against human documents, with a cluster-bootstrap 95% interval over human sources and their matches. It breaks the AUC down by genre, by generator vendor and tier (against the matched human documents) and per rule.

## Outputs

- `sources/human.jsonl` records one immutable source pointer, revision date, licence, normalized-text digest, and S3 key per admitted document or section.
- `sources/dedup.jsonl` records every accepted or near-duplicate decision.
- `briefs/manifest.jsonl` records the abstract brief digest and source-overlap score. `briefs/rejections.jsonl` records invalid or leaking outputs; rejected briefs are written to `briefs/retry-input.jsonl` for a new batch.
- `models/roster.json` records live Bedrock text models, inference profiles, tier, vendor, and batch verification state.
- `generated/manifest.jsonl` records model, vendor, tier, inference parameters, token count, digest, and leak score. Leaking outputs are absent from this manifest and recorded in `generated/rejections.jsonl`.
- `ledgers/cost-ledger.json` records every submitted job and its pre-submit estimate.
- `ledgers/resources.json` records the bucket, role, and job ARNs.
- `corpus-build-report.md` summarizes counts by genre, source family, vendor, and tier.

Never commit `.cache/` or model output text. The root `.gitignore` excludes this cache path.

## Licence

Check each source licence and consent field before redistributing the corpus.
