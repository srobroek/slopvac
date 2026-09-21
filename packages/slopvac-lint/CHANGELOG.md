# Changelog

## Unreleased
- Record the 2026-09-22 human-ext adjudication arm: 49 confirms, majority TP 38 / FP 10 / borderline 1, with per-genre false-positive incidence and whitelist assessment.
- Tolerate benign judgement model annotation fields host-side and report annotation-stripped calls.

* Clarify that judgement outcomes are reporting-only and never affect deterministic gates or counts.
* `judgement finish` now defaults to Q02 `unique-quote` offset salvage; pass `--offset-salvage none` for raw-offset behavior, and reports record the selected mode.

* Guard noise-floor `majority-of-3` decisions with 30 complete units, record decision basis and repeat fingerprints, and align malformed-repeat documentation with incomplete-unit handling.

* Improve `ai-tells-structure.absolute-assertion-remainder` guidance to preserve quoted, attributed, historical, and explicitly bounded claims while retaining unsupported-universal detection.
* Fix judgement prompts so rule questions and exemplars are included in model-visible criteria; instrument ids and pack hashes now change when those fields change.

* Refine absolute-assertion judgement guidance to preserve attributed and bounded factual claims while flagging unsupported authorial guarantees and sweeping absolutes; add regression fixtures for three adjudicated true positives.
* Refine `ai-tells-content-shape.one-point-dilution` judgement guidance to preserve bounded recommendations and conditions; add adjudication regression fixtures for the shipped recall-guard case.
* `slopvac judgement prepare` no longer rescans the document projection per unit: per-document projection, neighbour-context and range indexes plus per-pack id caching cut a 10,000-word document from 792 s to 61 s wall (240 s to 18 s CPU) with byte-identical prompts, units and manifest (slopvac-cz0.38).

## [1.0.0](https://github.com/srobroek/slopvac/compare/slopvac--v0.1.0...slopvac--v1.0.0) (2026-08-18)


### ⚠ BREAKING CHANGES

* `slopvac-lint` no longer installs or imports. The command is `slopvac`, the module is `slopvac`, and `pip install slopvac-lint` finds nothing.

### Features

* split the linter into its own package and publish it to PyPI ([#10](https://github.com/srobroek/slopvac/issues/10)) ([29d6a80](https://github.com/srobroek/slopvac/commit/29d6a802562e6454bc2131e8ac7eb24eab72c1bf))
