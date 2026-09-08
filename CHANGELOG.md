# Changelog

## [1.0.2](https://github.com/srobroek/slopvac/compare/v1.0.1...v1.0.2) (2026-09-08)


### Bug Fixes

* load documentation skills through native OMP discovery ([#31](https://github.com/srobroek/slopvac/issues/31)) ([7251091](https://github.com/srobroek/slopvac/commit/7251091112cf6846102fa9ff8adc346f49abebc4))

## [1.0.1](https://github.com/srobroek/slopvac/compare/v0.2.0...v1.0.1) (2026-08-21)


### Bug Fixes

* **apm:** restore the packaged plugin skills ([#29](https://github.com/srobroek/slopvac/issues/29)) ([bec61bb](https://github.com/srobroek/slopvac/commit/bec61bb89a88603363109ee11769c195df837531))

## [0.2.0](https://github.com/srobroek/slopvac/compare/v0.1.0...v0.2.0) (2026-08-20)


### ⚠ BREAKING CHANGES

* package versions restart at 0.1.0; the published slopvac 1.0.0 on PyPI is being yanked in favour of 0.1.0.
* `slopvac-lint` no longer installs or imports. The command is `slopvac`, the module is `slopvac`, and `pip install slopvac-lint` finds nothing.
* **write-docs:** requires the vale binary on PATH (mise use -g vale, or brew install vale). Suppression syntax changes from <!-- write-docs:allow E2 --> to Vale's <!-- vale WriteDocs.SlopLexicon = NO --> off/on pairs, which are block-scoped rather than line-scoped.
* docs-specs.project-docs.context.md is removed; installs relying on markdown-wide doc-style steering must add the write-docs package.

### Features

* add the Epigram rule, sharpen the reviewer, wire release-please ([c4f24a0](https://github.com/srobroek/slopvac/commit/c4f24a01f2eaab19f9c8cd7f0398bf176fd1a1d7))
* add UnrequestedReassurance, restructure docs around the agent flow ([d9b4826](https://github.com/srobroek/slopvac/commit/d9b482628f312b3467df540fe3adc6c7eca0ab42))
* **codex:** add first-class APM parity across packages ([879fa56](https://github.com/srobroek/slopvac/commit/879fa560206e7ad156a7801909726649bd15ab6c))
* extract slopvac from agentic-packages ([4893f53](https://github.com/srobroek/slopvac/commit/4893f5335160397b064baa192ad1c753a14d7095))
* flag unasked-for rationale when reviewing prose ([#6](https://github.com/srobroek/slopvac/issues/6)) ([65a5c1c](https://github.com/srobroek/slopvac/commit/65a5c1ce8b148fe95b3c3f215f76c86a98ebcbcb))
* split the linter into its own package and publish it to PyPI ([#10](https://github.com/srobroek/slopvac/issues/10)) ([29d6a80](https://github.com/srobroek/slopvac/commit/29d6a802562e6454bc2131e8ac7eb24eab72c1bf))
* write-docs skill for slop-free, release-focused documentation ([#522](https://github.com/srobroek/slopvac/issues/522)) ([b516adb](https://github.com/srobroek/slopvac/commit/b516adb5ed8789b2b737c5876f75f2fbc809e755))
* **write-docs:** gate over-writing, split the tells catalogue ([1797522](https://github.com/srobroek/slopvac/commit/1797522b3b38f9e8fcbb3bff9426829831c6ae4c))
* **write-docs:** gate Unicode dashes in code, add the PostToolUse prose gate ([4e27321](https://github.com/srobroek/slopvac/commit/4e27321541f6f6d45397e3491d0326be4ac4b11f))
* **write-docs:** mechanise chat-session leakage as E5; add nine tells ([d69f28e](https://github.com/srobroek/slopvac/commit/d69f28ef344cda6928e56c9e6de6ae787bc69d9a))
* **write-docs:** project-owned Vale config with per-rule overrides ([aed0b98](https://github.com/srobroek/slopvac/commit/aed0b9840be249d99c59ac0d490408f0f351621f))
* **write-docs:** publish the prose rules as granular Vale packages ([58dd09a](https://github.com/srobroek/slopvac/commit/58dd09a43eb8759f2caa081c22abd91ed469a8c4))
* **write-docs:** replace slop-lint.py with a Vale prose gate ([73004af](https://github.com/srobroek/slopvac/commit/73004afce910267c555afce809d0b3ee30ab0af9))
* **write-docs:** split the gate into review-docs, publish styles on release ([e2fd715](https://github.com/srobroek/slopvac/commit/e2fd715b09cb033947ec596e6799aa5fdb249598))
* **write-docs:** trigger on buried doc tasks + SubagentStart discipline hook ([#526](https://github.com/srobroek/slopvac/issues/526)) ([e6eb0c7](https://github.com/srobroek/slopvac/commit/e6eb0c76bf65ae9a28309130abebb227c2f8b594))


### Bug Fixes

* **apm:** declare the marketplace owner, drop the deprecated target ([#27](https://github.com/srobroek/slopvac/issues/27)) ([ec8914c](https://github.com/srobroek/slopvac/commit/ec8914c94d11b45d16061eddc197e13258def9b0))
* **apm:** point tagPattern at the lockstep tag ([#24](https://github.com/srobroek/slopvac/issues/24)) ([525f845](https://github.com/srobroek/slopvac/commit/525f845c195184fd3a1a1b7215d855f6e3141af0))
* **ci:** drop the stale packages glob from yamllint ([d56ff19](https://github.com/srobroek/slopvac/commit/d56ff1998e2010c472bd08bf20fbc2ed3296ed38))
* **ci:** pass the App credential as client-id ([#18](https://github.com/srobroek/slopvac/issues/18)) ([3f97f1a](https://github.com/srobroek/slopvac/commit/3f97f1a02c5a462a1058118466105c8fb0b0a0f6))
* **ci:** require both app credentials before minting a token ([8adb558](https://github.com/srobroek/slopvac/commit/8adb55854e2e120276c0f2d60dfb9c720ab92820))
* **ci:** satisfy yamllint, validate rules by loading them ([67b3a80](https://github.com/srobroek/slopvac/commit/67b3a8037ff8bd8666a7faa3b1a9be94e9b5ed01))
* **config:** gate migration.md and exclusions.md instead of excluding them ([#22](https://github.com/srobroek/slopvac/issues/22)) ([3f2d51b](https://github.com/srobroek/slopvac/commit/3f2d51b6b6e420566ed1fa99c75f3e7049150627))
* cut the CLI output, and fix the Vale gate it exposed ([#21](https://github.com/srobroek/slopvac/issues/21)) ([8e35e77](https://github.com/srobroek/slopvac/commit/8e35e77203f9c218fdace99dfff2c63cdb8c704b))
* keep package artifacts stable after tests ([#629](https://github.com/srobroek/slopvac/issues/629)) ([caf391e](https://github.com/srobroek/slopvac/commit/caf391e8d229ca0c095d516736c5876bdab83923))
* point every URL at slopvac, not agentic-packages ([999d1c3](https://github.com/srobroek/slopvac/commit/999d1c3078a7bd8fbd7d6c52ff67fe26db3dad58))
* **reference:** drop the version from the generated header ([#26](https://github.com/srobroek/slopvac/issues/26)) ([4f24443](https://github.com/srobroek/slopvac/commit/4f24443517fcdf7aa0f46ca6a500bad2b09db083))
* **release:** give the APM package its own release-please component ([#16](https://github.com/srobroek/slopvac/issues/16)) ([7c577b2](https://github.com/srobroek/slopvac/commit/7c577b2eddc22d0d4dbf5d5be155afa2a79ffdc2))
* repair suppression annotations, un-exclude docs/, release in lockstep ([#23](https://github.com/srobroek/slopvac/issues/23)) ([dfe2842](https://github.com/srobroek/slopvac/commit/dfe2842c859cd875fc7b8e3e8b4915f7eab35614))
* **vale:** disable DoubleHyphen, which fires on the house dash ([#17](https://github.com/srobroek/slopvac/issues/17)) ([abe47b6](https://github.com/srobroek/slopvac/commit/abe47b6f2ebc539c007109fd1271d08e46a53880))


### Refactors

* flatten the package to the repo root ([921a218](https://github.com/srobroek/slopvac/commit/921a218010e4ab77f4bc05ee80def1cd27f29539))
* **write-docs:** drop the lexical-era appendix, calibrate over-writing ([48ae5a5](https://github.com/srobroek/slopvac/commit/48ae5a5ee8b764d3a11393f62fe07f80ebd3e003))


### Documentation

* document Kiro installation ([a97776c](https://github.com/srobroek/slopvac/commit/a97776c32256e9f89adf4d59d48e86d99cc70f49))
* rename the heading the gate flagged ([5217a3b](https://github.com/srobroek/slopvac/commit/5217a3b0d9dfba4d75804930be9443f67d44195d))
* state the file-format limits instead of teasing them ([eb6e31a](https://github.com/srobroek/slopvac/commit/eb6e31a589afdfe719c520802996adf2bc1eef8b))
* tighten the intro, document every dependency ([1de012e](https://github.com/srobroek/slopvac/commit/1de012ecb152fad398a88b158c3cb73e55d376ec))
* **write-docs:** add ai-tells reference with progressive-disclosure pointers ([#545](https://github.com/srobroek/slopvac/issues/545)) ([5ac1718](https://github.com/srobroek/slopvac/commit/5ac1718107061b1fcf224da5a30e289f614c69fc))
* **write-docs:** modernize ai-tells for current model generations ([#546](https://github.com/srobroek/slopvac/issues/546)) ([32f67bb](https://github.com/srobroek/slopvac/commit/32f67bb58f5512257137dddd099ca0d02c0bd49e))


### Chores

* reset all packages to 0.1.0 for pre-release ([#20](https://github.com/srobroek/slopvac/issues/20)) ([79cc6d3](https://github.com/srobroek/slopvac/commit/79cc6d3eaefb96ca8290146929d2930fb2a7540b))

## [2.0.1](https://github.com/srobroek/slopvac/compare/slopvac-repo--v2.0.0...slopvac-repo--v2.0.1) (2026-08-18)


### Bug Fixes

* **ci:** require both app credentials before minting a token ([8adb558](https://github.com/srobroek/slopvac/commit/8adb55854e2e120276c0f2d60dfb9c720ab92820))
* **release:** give the APM package its own release-please component ([#16](https://github.com/srobroek/slopvac/issues/16)) ([7c577b2](https://github.com/srobroek/slopvac/commit/7c577b2eddc22d0d4dbf5d5be155afa2a79ffdc2))

## [2.0.0](https://github.com/srobroek/slopvac/compare/slopvac-repo--v1.0.1...slopvac-repo--v2.0.0) (2026-08-18)


### ⚠ BREAKING CHANGES

* `slopvac-lint` no longer installs or imports. The command is `slopvac`, the module is `slopvac`, and `pip install slopvac-lint` finds nothing.
* **write-docs:** requires the vale binary on PATH (mise use -g vale, or brew install vale). Suppression syntax changes from <!-- write-docs:allow E2 --> to Vale's <!-- vale WriteDocs.SlopLexicon = NO --> off/on pairs, which are block-scoped rather than line-scoped.
* docs-specs.project-docs.context.md is removed; installs relying on markdown-wide doc-style steering must add the write-docs package.

### Features

* add the Epigram rule, sharpen the reviewer, wire release-please ([c4f24a0](https://github.com/srobroek/slopvac/commit/c4f24a01f2eaab19f9c8cd7f0398bf176fd1a1d7))
* add UnrequestedReassurance, restructure docs around the agent flow ([d9b4826](https://github.com/srobroek/slopvac/commit/d9b482628f312b3467df540fe3adc6c7eca0ab42))
* **codex:** add first-class APM parity across packages ([879fa56](https://github.com/srobroek/slopvac/commit/879fa560206e7ad156a7801909726649bd15ab6c))
* extract slopvac from agentic-packages ([4893f53](https://github.com/srobroek/slopvac/commit/4893f5335160397b064baa192ad1c753a14d7095))
* flag unasked-for rationale when reviewing prose ([#6](https://github.com/srobroek/slopvac/issues/6)) ([65a5c1c](https://github.com/srobroek/slopvac/commit/65a5c1ce8b148fe95b3c3f215f76c86a98ebcbcb))
* split the linter into its own package and publish it to PyPI ([#10](https://github.com/srobroek/slopvac/issues/10)) ([29d6a80](https://github.com/srobroek/slopvac/commit/29d6a802562e6454bc2131e8ac7eb24eab72c1bf))
* write-docs skill for slop-free, release-focused documentation ([#522](https://github.com/srobroek/slopvac/issues/522)) ([b516adb](https://github.com/srobroek/slopvac/commit/b516adb5ed8789b2b737c5876f75f2fbc809e755))
* **write-docs:** gate over-writing, split the tells catalogue ([1797522](https://github.com/srobroek/slopvac/commit/1797522b3b38f9e8fcbb3bff9426829831c6ae4c))
* **write-docs:** gate Unicode dashes in code, add the PostToolUse prose gate ([4e27321](https://github.com/srobroek/slopvac/commit/4e27321541f6f6d45397e3491d0326be4ac4b11f))
* **write-docs:** mechanise chat-session leakage as E5; add nine tells ([d69f28e](https://github.com/srobroek/slopvac/commit/d69f28ef344cda6928e56c9e6de6ae787bc69d9a))
* **write-docs:** project-owned Vale config with per-rule overrides ([aed0b98](https://github.com/srobroek/slopvac/commit/aed0b9840be249d99c59ac0d490408f0f351621f))
* **write-docs:** publish the prose rules as granular Vale packages ([58dd09a](https://github.com/srobroek/slopvac/commit/58dd09a43eb8759f2caa081c22abd91ed469a8c4))
* **write-docs:** replace slop-lint.py with a Vale prose gate ([73004af](https://github.com/srobroek/slopvac/commit/73004afce910267c555afce809d0b3ee30ab0af9))
* **write-docs:** split the gate into review-docs, publish styles on release ([e2fd715](https://github.com/srobroek/slopvac/commit/e2fd715b09cb033947ec596e6799aa5fdb249598))
* **write-docs:** trigger on buried doc tasks + SubagentStart discipline hook ([#526](https://github.com/srobroek/slopvac/issues/526)) ([e6eb0c7](https://github.com/srobroek/slopvac/commit/e6eb0c76bf65ae9a28309130abebb227c2f8b594))


### Bug Fixes

* **ci:** drop the stale packages glob from yamllint ([d56ff19](https://github.com/srobroek/slopvac/commit/d56ff1998e2010c472bd08bf20fbc2ed3296ed38))
* **ci:** satisfy yamllint, validate rules by loading them ([67b3a80](https://github.com/srobroek/slopvac/commit/67b3a8037ff8bd8666a7faa3b1a9be94e9b5ed01))
* keep package artifacts stable after tests ([#629](https://github.com/srobroek/slopvac/issues/629)) ([caf391e](https://github.com/srobroek/slopvac/commit/caf391e8d229ca0c095d516736c5876bdab83923))
* point every URL at slopvac, not agentic-packages ([999d1c3](https://github.com/srobroek/slopvac/commit/999d1c3078a7bd8fbd7d6c52ff67fe26db3dad58))


### Refactors

* flatten the package to the repo root ([921a218](https://github.com/srobroek/slopvac/commit/921a218010e4ab77f4bc05ee80def1cd27f29539))
* **write-docs:** drop the lexical-era appendix, calibrate over-writing ([48ae5a5](https://github.com/srobroek/slopvac/commit/48ae5a5ee8b764d3a11393f62fe07f80ebd3e003))


### Documentation

* document Kiro installation ([a97776c](https://github.com/srobroek/slopvac/commit/a97776c32256e9f89adf4d59d48e86d99cc70f49))
* rename the heading the gate flagged ([5217a3b](https://github.com/srobroek/slopvac/commit/5217a3b0d9dfba4d75804930be9443f67d44195d))
* state the file-format limits instead of teasing them ([eb6e31a](https://github.com/srobroek/slopvac/commit/eb6e31a589afdfe719c520802996adf2bc1eef8b))
* tighten the intro, document every dependency ([1de012e](https://github.com/srobroek/slopvac/commit/1de012ecb152fad398a88b158c3cb73e55d376ec))
* **write-docs:** add ai-tells reference with progressive-disclosure pointers ([#545](https://github.com/srobroek/slopvac/issues/545)) ([5ac1718](https://github.com/srobroek/slopvac/commit/5ac1718107061b1fcf224da5a30e289f614c69fc))
* **write-docs:** modernize ai-tells for current model generations ([#546](https://github.com/srobroek/slopvac/issues/546)) ([32f67bb](https://github.com/srobroek/slopvac/commit/32f67bb58f5512257137dddd099ca0d02c0bd49e))

## [1.0.1](https://github.com/srobroek/slopvac/compare/slopvac--v1.0.0...slopvac--v1.0.1) (2026-07-27)


### Documentation

* rename the heading the gate flagged ([5217a3b](https://github.com/srobroek/slopvac/commit/5217a3b0d9dfba4d75804930be9443f67d44195d))

## [1.0.0](https://github.com/srobroek/slopvac/compare/slopvac--v0.1.0...slopvac--v1.0.0) (2026-07-27)


### ⚠ BREAKING CHANGES

* **write-docs:** requires the vale binary on PATH (mise use -g vale, or brew install vale). Suppression syntax changes from <!-- write-docs:allow E2 --> to Vale's <!-- vale WriteDocs.SlopLexicon = NO --> off/on pairs, which are block-scoped rather than line-scoped.
* docs-specs.project-docs.context.md is removed; installs relying on markdown-wide doc-style steering must add the write-docs package.

### Features

* add the Epigram rule, sharpen the reviewer, wire release-please ([c4f24a0](https://github.com/srobroek/slopvac/commit/c4f24a01f2eaab19f9c8cd7f0398bf176fd1a1d7))
* add UnrequestedReassurance, restructure docs around the agent flow ([d9b4826](https://github.com/srobroek/slopvac/commit/d9b482628f312b3467df540fe3adc6c7eca0ab42))
* **codex:** add first-class APM parity across packages ([879fa56](https://github.com/srobroek/slopvac/commit/879fa560206e7ad156a7801909726649bd15ab6c))
* extract slopvac from agentic-packages ([4893f53](https://github.com/srobroek/slopvac/commit/4893f5335160397b064baa192ad1c753a14d7095))
* write-docs skill for slop-free, release-focused documentation ([#522](https://github.com/srobroek/slopvac/issues/522)) ([b516adb](https://github.com/srobroek/slopvac/commit/b516adb5ed8789b2b737c5876f75f2fbc809e755))
* **write-docs:** gate over-writing, split the tells catalogue ([1797522](https://github.com/srobroek/slopvac/commit/1797522b3b38f9e8fcbb3bff9426829831c6ae4c))
* **write-docs:** gate Unicode dashes in code, add the PostToolUse prose gate ([4e27321](https://github.com/srobroek/slopvac/commit/4e27321541f6f6d45397e3491d0326be4ac4b11f))
* **write-docs:** mechanise chat-session leakage as E5; add nine tells ([d69f28e](https://github.com/srobroek/slopvac/commit/d69f28ef344cda6928e56c9e6de6ae787bc69d9a))
* **write-docs:** project-owned Vale config with per-rule overrides ([aed0b98](https://github.com/srobroek/slopvac/commit/aed0b9840be249d99c59ac0d490408f0f351621f))
* **write-docs:** publish the prose rules as granular Vale packages ([58dd09a](https://github.com/srobroek/slopvac/commit/58dd09a43eb8759f2caa081c22abd91ed469a8c4))
* **write-docs:** replace slop-lint.py with a Vale prose gate ([73004af](https://github.com/srobroek/slopvac/commit/73004afce910267c555afce809d0b3ee30ab0af9))
* **write-docs:** split the gate into review-docs, publish styles on release ([e2fd715](https://github.com/srobroek/slopvac/commit/e2fd715b09cb033947ec596e6799aa5fdb249598))
* **write-docs:** trigger on buried doc tasks + SubagentStart discipline hook ([#526](https://github.com/srobroek/slopvac/issues/526)) ([e6eb0c7](https://github.com/srobroek/slopvac/commit/e6eb0c76bf65ae9a28309130abebb227c2f8b594))


### Bug Fixes

* **ci:** drop the stale packages glob from yamllint ([d56ff19](https://github.com/srobroek/slopvac/commit/d56ff1998e2010c472bd08bf20fbc2ed3296ed38))
* **ci:** satisfy yamllint, validate rules by loading them ([67b3a80](https://github.com/srobroek/slopvac/commit/67b3a8037ff8bd8666a7faa3b1a9be94e9b5ed01))
* keep package artifacts stable after tests ([#629](https://github.com/srobroek/slopvac/issues/629)) ([caf391e](https://github.com/srobroek/slopvac/commit/caf391e8d229ca0c095d516736c5876bdab83923))
* point every URL at slopvac, not agentic-packages ([999d1c3](https://github.com/srobroek/slopvac/commit/999d1c3078a7bd8fbd7d6c52ff67fe26db3dad58))


### Refactors

* flatten the package to the repo root ([921a218](https://github.com/srobroek/slopvac/commit/921a218010e4ab77f4bc05ee80def1cd27f29539))
* **write-docs:** drop the lexical-era appendix, calibrate over-writing ([48ae5a5](https://github.com/srobroek/slopvac/commit/48ae5a5ee8b764d3a11393f62fe07f80ebd3e003))


### Documentation

* document Kiro installation ([a97776c](https://github.com/srobroek/slopvac/commit/a97776c32256e9f89adf4d59d48e86d99cc70f49))
* state the file-format limits instead of teasing them ([eb6e31a](https://github.com/srobroek/slopvac/commit/eb6e31a589afdfe719c520802996adf2bc1eef8b))
* tighten the intro, document every dependency ([1de012e](https://github.com/srobroek/slopvac/commit/1de012ecb152fad398a88b158c3cb73e55d376ec))
* **write-docs:** add ai-tells reference with progressive-disclosure pointers ([#545](https://github.com/srobroek/slopvac/issues/545)) ([5ac1718](https://github.com/srobroek/slopvac/commit/5ac1718107061b1fcf224da5a30e289f614c69fc))
* **write-docs:** modernize ai-tells for current model generations ([#546](https://github.com/srobroek/slopvac/issues/546)) ([32f67bb](https://github.com/srobroek/slopvac/commit/32f67bb58f5512257137dddd099ca0d02c0bd49e))

## Changelog
