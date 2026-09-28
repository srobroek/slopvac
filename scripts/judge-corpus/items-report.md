# Local judging corpus items — human-only build

Build `human-20260928-s17-v1`; generated manifest was absent when this build ran. Rerun `judge-corpus items build --include-generated` and then upload a new immutable build once generated documents and caches land.

## Build summary

- Human source units: 2,971; generated source units: 0.
- Items retained: 87,384.
- Split sizes: train 73,829; dev 12,121; calibration 350; test 1,084 (test contains 600 model-derived adjudication items plus 484 construction items).
- Test split model-derived items dropped above the adjudication cap: 18,494; calibration model-derived items dropped: 11,212.
- Finding-confirmation outcomes by label: `None=81128, real-defect=134`. Constructed lint-example positives: 134 real-defect items.
- Role totals: `finding-confirmation=81262, semantic-detection=6122`.
- Granularity by role: `finding-confirmation/document=23054, finding-confirmation/paragraph=26276, finding-confirmation/sentence=31932, semantic-detection/document=1678, semantic-detection/paragraph=2371, semantic-detection/sentence=2073`.
- Rule holdouts: 33 lint rules and 12 judgement rules; test seen/unseen counts are in `items/manifest.json`. Source document families do not cross splits.
- Test-sheet rows: 600, exported to JSONL and CSV.
- Tokenizer SHA-256 digests (Qwen3.5-4B, Laya ModernBERT English, Laya multilingual) and frozen split SHA-256 digests: `items/manifest.json`.
- Teacher-panel spend and agreement: not run yet. Planned human-only three-vendor sample estimates $54.86 against the $60 cap using `pricing_for`; hold submission until generated documents arrive so one panel includes both provenances.

## Item counts by role, rule, label origin, genre and granularity

`items/manifest.json` contains the full Cartesian count table under `dimensions.role_rule_label_origin_genre_granularity` and split × granularity totals.

