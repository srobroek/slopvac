# Changelog

## [2.0.0](https://github.com/srobroek/slopvac/compare/slopvac--v1.0.1...slopvac--v2.0.0) (2026-08-18)


### ⚠ BREAKING CHANGES

* `slopvac-lint` no longer installs or imports. The command is `slopvac`, the module is `slopvac`, and `pip install slopvac-lint` finds nothing.

### Features

* add the Epigram rule, sharpen the reviewer, wire release-please ([c4f24a0](https://github.com/srobroek/slopvac/commit/c4f24a01f2eaab19f9c8cd7f0398bf176fd1a1d7))
* add UnrequestedReassurance, restructure docs around the agent flow ([d9b4826](https://github.com/srobroek/slopvac/commit/d9b482628f312b3467df540fe3adc6c7eca0ab42))
* extract slopvac from agentic-packages ([4893f53](https://github.com/srobroek/slopvac/commit/4893f5335160397b064baa192ad1c753a14d7095))
* split the linter into its own package and publish it to PyPI ([#10](https://github.com/srobroek/slopvac/issues/10)) ([29d6a80](https://github.com/srobroek/slopvac/commit/29d6a802562e6454bc2131e8ac7eb24eab72c1bf))


### Bug Fixes

* point every URL at slopvac, not agentic-packages ([999d1c3](https://github.com/srobroek/slopvac/commit/999d1c3078a7bd8fbd7d6c52ff67fe26db3dad58))


### Refactors

* flatten the package to the repo root ([921a218](https://github.com/srobroek/slopvac/commit/921a218010e4ab77f4bc05ee80def1cd27f29539))
