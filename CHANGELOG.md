# Changelog

## [2.8.0](https://github.com/srobroek/slopvac/compare/v2.7.0...v2.8.0) (2026-09-19)


### Features

* **judgement:** add noise-floor instrument ([18c5cd1](https://github.com/srobroek/slopvac/commit/18c5cd1e81981d14589478af9499704413a49956))
* **judgement:** add noise-floor instrument ([fc8398d](https://github.com/srobroek/slopvac/commit/fc8398dd8768de5b04bc016c32c0b8ca5a739ac0))


### Bug Fixes

* **judgement:** validate complete response sets ([323fc04](https://github.com/srobroek/slopvac/commit/323fc0471d399791437ccc8357ff054baaf7221e))


### Documentation

* **judgement:** clarify noise-floor registration ([4f08562](https://github.com/srobroek/slopvac/commit/4f085620f55d4a160138cdf4dc7bd51ffea63399))

## [2.7.0](https://github.com/srobroek/slopvac/compare/v2.6.0...v2.7.0) (2026-09-19)


### Features

* add Bedrock batch judgement runner ([1030c2b](https://github.com/srobroek/slopvac/commit/1030c2ba66f8942f35f53ad7bfa7ca5c05d2eabb))
* document AWS batch setup ([274fa42](https://github.com/srobroek/slopvac/commit/274fa4233c1dd859be513cffd9d159bb2fdfa593))
* document AWS Bedrock batch setup ([d93aeb3](https://github.com/srobroek/slopvac/commit/d93aeb377431c00b700fd5244a7eb13341725a1b))
* **judgement:** gold-set recall, control false confirms, evidence-gate discards, opt-in unique-quote salvage ([a22c05a](https://github.com/srobroek/slopvac/commit/a22c05af112e8938d79ae2f0354c135ae12b21ca))
* **judgement:** gold-set recall, control false confirms, evidence-gate discards, opt-in unique-quote salvage ([187e8d2](https://github.com/srobroek/slopvac/commit/187e8d2b36bf50eec31678b82eb5704764db6dc2))
* **judgement:** normative preset covers plain imperative paragraphs ([26f8e2f](https://github.com/srobroek/slopvac/commit/26f8e2f32f96c3bfd2e5f9c276d1046125682c68))
* **judgement:** normative preset covers plain imperative paragraphs ([bd300db](https://github.com/srobroek/slopvac/commit/bd300db774d3c3814ad9f0f318f8c0a2d31731bc))
* **judgement:** standalone Bedrock batch runner for evaluation calls ([f7078fc](https://github.com/srobroek/slopvac/commit/f7078fca50c994e53bfaff1e518e64e038a0cf0a))
* **lint:** reinstate --mode code-comments on the 2.6.0 comment route ([bd84c00](https://github.com/srobroek/slopvac/commit/bd84c0009f19a365aac3a44f8a00bbd7a8752c14))
* **lint:** reinstate --mode code-comments on the 2.6.0 comment route ([a57c192](https://github.com/srobroek/slopvac/commit/a57c19212e55b5d00d9715f6df5d64e811964ff7))
* **slopvac-lint:** stable span identity on the shipped projection ([25e7a30](https://github.com/srobroek/slopvac/commit/25e7a303dda8a1abd01ab8ebb70d96d71e4a9064))
* **slopvac-lint:** stable span identity on the shipped projection ([81bff74](https://github.com/srobroek/slopvac/commit/81bff7496d81062cb3d6fc2870a8b7b8c0d013fe))
* **slopvac:** make inclusive rules opt-in by profile ([1f2b312](https://github.com/srobroek/slopvac/commit/1f2b312752738e7638318c904e67573d8a76418c))
* **slopvac:** make inclusive rules opt-in by profile ([74040c5](https://github.com/srobroek/slopvac/commit/74040c516baf6c985f1811da6651f4a4ada247f3))
* use 32000 token Bedrock budget ([fba847a](https://github.com/srobroek/slopvac/commit/fba847af4f250b3b09cfb75d94971c3e4acf56e5))


### Bug Fixes

* collect native Anthropic batch output ([6351f25](https://github.com/srobroek/slopvac/commit/6351f2503bab727f70b77802805f404df0464fc5))
* **judgement:** finish --adjudication counts each verdict once with an explicit label map ([a959991](https://github.com/srobroek/slopvac/commit/a959991a8b7e9836ab3b031a04eac94fc2306b66))
* **judgement:** FP-FRAGMENT-UNIT row verdicts count as FP ([3e480aa](https://github.com/srobroek/slopvac/commit/3e480aa8377703fd72a452616297b47f75c0d192))
* **judgement:** gate heading-echo on material redundancy ([f4f7546](https://github.com/srobroek/slopvac/commit/f4f7546c896480001bd0091f3bbc16590096bf2f))
* **judgement:** gate heading-echo on material redundancy ([54799af](https://github.com/srobroek/slopvac/commit/54799af5198c5a86ad2bdbe86399e9ae25e0a7b8))
* **judgement:** gold-set review round - shipped v1 schema, evidence-overlap recall, multi-unit spans, unit-only salvage ([5d01773](https://github.com/srobroek/slopvac/commit/5d017733a245ab5b3812d6e1872b902d20657821))
* **judgement:** heading-echo predicate treats locator boilerplate as non-material and normalises derivational forms ([a6aeeeb](https://github.com/srobroek/slopvac/commit/a6aeeeb8e158d3af1ecb934b1a6d3874cd07b381))
* **judgement:** heading-echo redundancy detects new content words and short restatements ([7e068b4](https://github.com/srobroek/slopvac/commit/7e068b45df478902a2cf421431b44fde5a25135f))
* **judgement:** occurrence ordinal on every judgement unit ([0792132](https://github.com/srobroek/slopvac/commit/0792132f6569ebff52c52b3f765b0be85f4b422a))
* **judgement:** ordinal from per-document construction order ([d9305ac](https://github.com/srobroek/slopvac/commit/d9305ac2681810c0f6df861ab6b5ba3c6839fc07))
* **judgement:** plain-paragraph imperative detection uses the text_type classifier; list path unchanged ([a1de89f](https://github.com/srobroek/slopvac/commit/a1de89fe31ed2defc054aa63e2e35e71f7134168))
* **judgement:** repair driver document and response handling ([7f5824a](https://github.com/srobroek/slopvac/commit/7f5824a82b888ca6b50e86d78a8974e1caef5a01))
* **judgement:** repair driver document and response handling ([be6d764](https://github.com/srobroek/slopvac/commit/be6d764cb312e6d93b2069eda2e57184ad776894))
* **lint:** classifier distinguishes noun-subject homographs and bare imperative Note ([6726932](https://github.com/srobroek/slopvac/commit/6726932b278c19169a1558f2fa75a0ad334079a0))
* **lint:** code-comments review round - config mode precedence, informational skips ([c0f03db](https://github.com/srobroek/slopvac/commit/c0f03db84d4f8c63d84253ead10f6c845f953d4d))
* **lint:** code-comments round 3 - unchecked RST-only targets exit 2, TOML out of prose collection ([cd8ec81](https://github.com/srobroek/slopvac/commit/cd8ec817f41620c5ba54090546aa8909b16504fa))
* **lint:** omit empty notes from the JSON report ([fd62c23](https://github.com/srobroek/slopvac/commit/fd62c23fab3f5648810c9ae5bd351f51e42fc748))
* **lint:** phrasal imperatives after safety markers classify PROCEDURAL ([9e8ae69](https://github.com/srobroek/slopvac/commit/9e8ae6918448e97c490304dac7eb7c256ded077e))
* **lint:** safety-marker imperatives and negative imperatives classify PROCEDURAL ([58b861f](https://github.com/srobroek/slopvac/commit/58b861fa19d647e67ccc4e372be4e8a6efe86f1a))
* **lint:** safety-marker imperatives and negative imperatives classify PROCEDURAL ([6494a54](https://github.com/srobroek/slopvac/commit/6494a5435bc44af5b067b7f6d2c1fac7ed955687))
* make judgement gate reporting-only ([5c52a3f](https://github.com/srobroek/slopvac/commit/5c52a3fca92a35bc82bf2102a364e8544042d686))
* make judgement gate reporting-only ([231b624](https://github.com/srobroek/slopvac/commit/231b624b00a2b92b2883f6750f2d755bd2daa476))
* parallelize invoke calls and collect native output ([87f6760](https://github.com/srobroek/slopvac/commit/87f67605a53ae2c6599909750147f1b609e45a1f))
* preserve Bedrock parse diagnostics ([aa03d0c](https://github.com/srobroek/slopvac/commit/aa03d0c7c22f04808aa93c1de22a7a203b05e441))
* reject truncated Bedrock responses ([78362fa](https://github.com/srobroek/slopvac/commit/78362fad36e6f8764ca109eab5f50ea6872febef))
* **slopvac-lint:** span identity review round - text-based ids, unbordered tables, HTML text nodes ([d3d1025](https://github.com/srobroek/slopvac/commit/d3d1025390d97fc43f0ca6c3ed3dc849d6e57a99))
* **slopvac:** compile profile-default rules ([447ccc4](https://github.com/srobroek/slopvac/commit/447ccc46ba8410f1e19e41760a38ba3f9c9358fb))


### Documentation

* explain judgement driver workflow ([071eaa1](https://github.com/srobroek/slopvac/commit/071eaa15dea9499ce827970ef1e9e2a9e86c612d))
* explain judgement driver workflow ([7bf93d0](https://github.com/srobroek/slopvac/commit/7bf93d0eb5d688154b8233538b75eff9a5a84ada))
* fix AWS runner prose gate ([b64ed97](https://github.com/srobroek/slopvac/commit/b64ed974ce3009796c099551b015bfee6b984e10))
* record deleted AWS bucket accurately ([b1f8d3c](https://github.com/srobroek/slopvac/commit/b1f8d3c77a5b7bc63184a0798b1db486858a3e06))
* **slopvac-lint:** evaluation record schema, normalized records, --adjudication precision ([f82c776](https://github.com/srobroek/slopvac/commit/f82c77692d6ad5b46c483b55352268a8e43f515b))
* **slopvac-lint:** evaluation record schema, normalized records, --adjudication precision ([a11a51e](https://github.com/srobroek/slopvac/commit/a11a51eb037b788f6b4b48403feaa988f0d24963))
* **slopvac-lint:** judgement guide review fixes ([f81f81f](https://github.com/srobroek/slopvac/commit/f81f81f6a79e65f043ba90cacc552c415fe40d55))
* **slopvac-lint:** record normalizer review round - single-count adjudications, explicit labels, pre-gate evidence denominator ([686de4e](https://github.com/srobroek/slopvac/commit/686de4e6aa83c09e8dd207510501ba775c34210f))
* **slopvac:** skills README states 26 categories ([2966e93](https://github.com/srobroek/slopvac/commit/2966e93d91233b81d723e1332b39157c1af7bb59))
* **slopvac:** skills README states 26 categories, matching the 2.6.0 inventory ([0b3ace8](https://github.com/srobroek/slopvac/commit/0b3ace821d0e8b07780e9ef654e23603bd58bd84))

## [2.6.0](https://github.com/srobroek/slopvac/compare/v2.5.0...v2.6.0) (2026-09-17)


### Features

* **judgement:** add contract evaluation runner ([af9ef8e](https://github.com/srobroek/slopvac/commit/af9ef8e6f62db72b79a256543d09b4c9ad702080))
* **judgement:** add fact-preservation rewrite checker ([bba1e19](https://github.com/srobroek/slopvac/commit/bba1e1912d97e47da37a98c03f486fd9d47a2546))
* **judgement:** add the prepare/finish/compare evaluation driver ([6f7021f](https://github.com/srobroek/slopvac/commit/6f7021f48cd1f58d426c4db1312cacb6d75d3db4))
* **judgement:** add the prepare/finish/compare evaluation driver ([d2d47b8](https://github.com/srobroek/slopvac/commit/d2d47b87af0d4e0f7a6e755b7341d5a6524f916e))
* **judgement:** adjudicate model verdicts against the rubric contract ([2df8fdd](https://github.com/srobroek/slopvac/commit/2df8fddbba2bb918de74a1fa217a7c0d78d59596))
* **judgement:** aggregate judgement findings without gating the composite score ([36eb301](https://github.com/srobroek/slopvac/commit/36eb301a452489938f15d51860c47045c56bd37d))
* **judgement:** aggregate judgement findings without gating the composite score ([dbf5682](https://github.com/srobroek/slopvac/commit/dbf56823621f5aba84cd0f715c99cdf79e9d30b2))
* **judgement:** precision interventions for the dominant false-positive families ([01a4a47](https://github.com/srobroek/slopvac/commit/01a4a47d92f1aa1633539b3597c89f9786290161))
* **judgement:** precision interventions for the four dominant false-positive families ([1beaaa6](https://github.com/srobroek/slopvac/commit/1beaaa68e69dcbfe8517d4a965b38ffe12a6c7d6))
* **judgement:** render deterministic judgement packs ([bf518e0](https://github.com/srobroek/slopvac/commit/bf518e02744eea9162f509cfe03769a89e923d6b))
* **lint:** detect formulaic heading patterns ([971c62c](https://github.com/srobroek/slopvac/commit/971c62c607e8156a2e9abc7f7cb3d0341a9a61c2))
* **slopvac-lint:** add typed judgement rule contracts ([55dc78c](https://github.com/srobroek/slopvac/commit/55dc78c2dc69a5b817369f4ffdf2ed863c52f461))
* **slopvac-lint:** map projected prose to raw bytes and classify unit origin ([74495c2](https://github.com/srobroek/slopvac/commit/74495c2f02ec159168e2a8f8a2fc33a6636b39b9))
* **slopvac-lint:** STE sentence segmentation boundaries ([3522ca4](https://github.com/srobroek/slopvac/commit/3522ca4d10d0ef7e0c491560cbdcb02ac7977adf))
* **slopvac-lint:** STE sentence segmentation boundaries ([f1bd0a3](https://github.com/srobroek/slopvac/commit/f1bd0a3dde4087983393785d294317e4b8fac1c2))
* **slopvac-lint:** Unicode-aware STE token boundaries ([e936045](https://github.com/srobroek/slopvac/commit/e936045d6c214e1d2291d87260b7c395ba89e95a))
* **slopvac-lint:** Unicode-aware STE token boundaries ([e6b1431](https://github.com/srobroek/slopvac/commit/e6b1431da4e57d6209ac295e92c833eb77bd1ae9))
* **slopvac:** keep documentation on the current artifact ([9114362](https://github.com/srobroek/slopvac/commit/91143620ff1a344238b01131e28f8fe45cd70287))
* **slopvac:** keep documentation on the current artifact ([86a3d9f](https://github.com/srobroek/slopvac/commit/86a3d9f4d24dcb4e971b06e8c2fc487db104faac))


### Bug Fixes

* anchor pruning beneath repository root ([2f56dc0](https://github.com/srobroek/slopvac/commit/2f56dc076556aef2394552717c7a15f2a5eaf710))
* close retention policy review findings ([75eb882](https://github.com/srobroek/slopvac/commit/75eb882401d1c9dc6eabd15a3fc390f41b3e7dc2))
* **judgement:** adjudicate in the 1.1.2 order, keep contract-shaped pack identities, record veto details ([a631066](https://github.com/srobroek/slopvac/commit/a6310669061fd612e17a0197d52367b48d8824d5))
* **judgement:** aggregate probe occurrence records per unit in coverage ([a2d1172](https://github.com/srobroek/slopvac/commit/a2d1172e074996f37d7030fca0a035fd23f1af0b))
* **judgement:** check probe and span result rows carry the schema's occurrences shape ([e6d1825](https://github.com/srobroek/slopvac/commit/e6d18251ebc2e7dfb4d2383162e5522dd1b707b2))
* **judgement:** count distinct units, carry component ids, mark the dependence table uncalibrated ([42242dd](https://github.com/srobroek/slopvac/commit/42242dd9fe6b2e80adebe39e516e0c99e91659bb))
* **judgement:** expose Coverage.dropped through the mapping accessor ([d53ee16](https://github.com/srobroek/slopvac/commit/d53ee168de880cb13c57f1ff65cc3c8196e70d08))
* **judgement:** keep score_document under the complexity gate and restore the min_score guard ([d77d267](https://github.com/srobroek/slopvac/commit/d77d267ab9dbfb23d918e35b8b87601dee1bf0c2))
* **judgement:** make the rewrite checker contract-complete ([e6085ea](https://github.com/srobroek/slopvac/commit/e6085ea2a107779db4a47bf6be0afb1a555ce348))
* **judgement:** one eval record model over adjudicated findings; count every host outcome ([4ad7af4](https://github.com/srobroek/slopvac/commit/4ad7af4088dec9291c673052d89f69986728e542))
* **judgement:** re-export judgement_cache_key from eval.runner ([7817ca8](https://github.com/srobroek/slopvac/commit/7817ca85a2dee798c60b64e46c8c945387078616))
* **judgement:** skip non-prose cells, map sentence starts through the document projection, count offset mismatches ([46bf519](https://github.com/srobroek/slopvac/commit/46bf5198abf5d87edb681b922ad3fd91d4e8ed0c))
* **judgement:** use a typos-neutral JCS vector and blank-line the spine list ([e42c2f4](https://github.com/srobroek/slopvac/commit/e42c2f4298fdfc10194cf6cf1bea9f106481618a))
* **judgement:** validate probe row shape, flatten run output, decode report rows, one cache key ([b4bb9b0](https://github.com/srobroek/slopvac/commit/b4bb9b00a2793e723584608a739a162c797e3d65))
* **lint:** correct the contrastive-core provenance and sync README counts with the reference ([9b4d0a2](https://github.com/srobroek/slopvac/commit/9b4d0a2ea0a99108406b37f2b68d00cbf648e4e6))
* **lint:** keep the contrastive core at prose scope ([69e770e](https://github.com/srobroek/slopvac/commit/69e770ed6aaf386345faa631ea74c81d05a871ba))
* name a real policy owner and report partial removals ([07f25b1](https://github.com/srobroek/slopvac/commit/07f25b175e65e1453332f9f568107c59b9a8d683))
* report partial artifact removal failures ([3dd78b7](https://github.com/srobroek/slopvac/commit/3dd78b7151ba8916c4a16da394e2fcd5dc4c2cc8))
* **slopvac-lint:** closed-class openers after dotted initialisms, documented in metrics.md ([b3bed5a](https://github.com/srobroek/slopvac/commit/b3bed5ab3c62e34a6c4005c3a51655ae28e1ac44))
* **slopvac-lint:** keep the document ProjectionMap and locate block bases in projected text ([7b18601](https://github.com/srobroek/slopvac/commit/7b18601f8d43008a6fa6e14472a783a2a66e358f))
* **slopvac-lint:** paths leave the sentence period to segmentation ([e99c352](https://github.com/srobroek/slopvac/commit/e99c3521be40a0ce07145935882ddfeaf47addb6))
* **slopvac-lint:** refresh the rule reference and accept research-record spellings ([6e2d2f3](https://github.com/srobroek/slopvac/commit/6e2d2f3e9b2ff40144c79a6d11d6d7501b778f59))
* **slopvac-lint:** regenerate the rule reference at its shipped path ([510062f](https://github.com/srobroek/slopvac/commit/510062f221e2479be46e4c39c01cb0b5c169124e))
* **slopvac-lint:** repair provenance links and doc lint for PR 79 ([42f8e3c](https://github.com/srobroek/slopvac/commit/42f8e3cf217ef6ef242f9d7f50d36bc5c6daba71))
* **slopvac-lint:** resolve the rubric contract from the repository root in tests ([2b95d98](https://github.com/srobroek/slopvac/commit/2b95d985bdade7c37ed132922d73ecd69a62f5ed))
* **slopvac-lint:** segmentation review round - initialisms, offsets, list items ([00e978d](https://github.com/srobroek/slopvac/commit/00e978d045eee3108c1a93a82d797feef1c35e75))
* **slopvac-lint:** ship contract 1.1.2, compare every judgement record field, close the token-class type ([6fb480e](https://github.com/srobroek/slopvac/commit/6fb480e251bd40436ed74a9733f31a218f8617a9))
* **slopvac-lint:** tokenizer review round - identifiers, paths, decimal digits, attached marks ([ad1e4e3](https://github.com/srobroek/slopvac/commit/ad1e4e3bdcd3be04bf500ff9fe6680bc379c87d9))
* **slopvac-lint:** Unicode-aware phase-1 path and identifier classes ([8c4d245](https://github.com/srobroek/slopvac/commit/8c4d24596977339f259846b71f970d63232881a1))
* **slopvac-lint:** vertical-list items keep their physical line after blank lines ([9edf002](https://github.com/srobroek/slopvac/commit/9edf0029c7d3e53919cc24443a690bb7abf016c1))


### Documentation

* define orchestration and Beads artefact retention ([5ac6a0a](https://github.com/srobroek/slopvac/commit/5ac6a0a3fcabfa1360489ac61532f46b3b282b52))
* define orchestration and Beads artefact retention ([f17dc58](https://github.com/srobroek/slopvac/commit/f17dc58b347a8887d767916a93f75c020602d94e))
* document doc-comment linting design ([cd94863](https://github.com/srobroek/slopvac/commit/cd948631d4baa327aa41ea214ec9c1c23dd5d2ae))
* **slopvac-lint:** add distinct-unit reconciliation to the sibling sample record ([9d4ac1e](https://github.com/srobroek/slopvac/commit/9d4ac1eaf24a8535889f1c6151e704222b6f8d3c))
* **slopvac-lint:** blank line before the CLI driver heading (MD022) ([0e931b2](https://github.com/srobroek/slopvac/commit/0e931b2489a9854c60fc8d533c9ae27260ed9e1e))
* **slopvac-lint:** commit the generated 1.1.2 contract and correct the record ([ad66a62](https://github.com/srobroek/slopvac/commit/ad66a6266a8b4e9c36d88d2908465c95e508c3f7))
* **slopvac-lint:** doc-comment design review fixes ([4035341](https://github.com/srobroek/slopvac/commit/40353410f48a86e79f324e2b39392b6172b2cd8b))
* **slopvac-lint:** doc-comment linting design (not implemented) ([72b0aad](https://github.com/srobroek/slopvac/commit/72b0aade96b4543420a2afbbeb9a7bdb7d45e53d))
* **slopvac-lint:** exclude one more bot-blocked citation host from lychee ([9bd8072](https://github.com/srobroek/slopvac/commit/9bd8072661e0cadb5090461ff9a71124e8cb8387))
* **slopvac-lint:** make the research record pass typos and lychee in CI ([bcb9703](https://github.com/srobroek/slopvac/commit/bcb9703edd6ef7a1bb9f332a2feeb7dec3ab3ca5))
* **slopvac-lint:** reconcile local-corpus run counts at distinct-unit granularity ([bd19293](https://github.com/srobroek/slopvac/commit/bd1929317840f2d1885c6f08bc574eb5e8608acc))
* **slopvac-lint:** record the 2026-09-15 judgement rubric review and contract ([d620fe9](https://github.com/srobroek/slopvac/commit/d620fe99f1ca5072cdff7294373429b8959024e0))
* **slopvac-lint:** record the 2026-09-15 judgement rubric review and contract ([8d759c7](https://github.com/srobroek/slopvac/commit/8d759c70bf407c2e97af4891ff6dce1c7a6705b5))
* **slopvac-lint:** record the full sibling-repository judgement run ([fa572d0](https://github.com/srobroek/slopvac/commit/fa572d062cb6505123b43e68187461d7010c8b01))
* **slopvac-lint:** record the held-out paired comparison for the precision instrument ([298abc1](https://github.com/srobroek/slopvac/commit/298abc12ae20623517af6c3e65a613f535cde870))
* **slopvac-lint:** record the held-out third-party baseline run ([170ab43](https://github.com/srobroek/slopvac/commit/170ab437d00a2c2958400ccfeb3940912d8ed825))
* **slopvac-lint:** record the local-corpus judgement run with hand adjudication ([7da8921](https://github.com/srobroek/slopvac/commit/7da8921b60bc6cc214f5cdb161651f3dffd6e084))
* **slopvac-lint:** record the README smoke per-finding diff and artefact identities ([f2e4455](https://github.com/srobroek/slopvac/commit/f2e4455fba10701d0134dae9c35f9551ce20c6d3))
* **slopvac-lint:** record the sibling-repository judgement sample and frozen corpus ([01bc29e](https://github.com/srobroek/slopvac/commit/01bc29e3bc3a6a898bcaaaa183d0ac046b0db012))
* **slopvac-lint:** record the unified diff of rewrites the judgement layer proposed on the local corpus ([a291998](https://github.com/srobroek/slopvac/commit/a291998c2d05ca3647ab4d55501f7e3c7332c8b0))
* **slopvac-lint:** regenerate the rule reference after the judgement question rewrites ([5e158c3](https://github.com/srobroek/slopvac/commit/5e158c3182695bee25f215eb70a244b79d255731))
* **slopvac-lint:** remove a double blank line (MD012) ([c0284fd](https://github.com/srobroek/slopvac/commit/c0284fd346758f4df76822f1f1daf4ab7e315832))
* **slopvac-lint:** revise rubric contract to 1.1.1 for the 66th judgement rule ([3e60c5b](https://github.com/srobroek/slopvac/commit/3e60c5b5bc5427a1cde7702c951de4d23e4bcda7))
* **slopvac-lint:** state measured confirm precision and the reader policy for judgement confirms ([9008662](https://github.com/srobroek/slopvac/commit/9008662f7923b201cd7213a105af5dd880baaf7a))
* **slopvac-lint:** state what the held-out comparison does not measure ([a16cdb1](https://github.com/srobroek/slopvac/commit/a16cdb1c93e8b97b65e5a548cb85373f90f4968a))

## [2.5.0](https://github.com/srobroek/slopvac/compare/v2.4.0...v2.5.0) (2026-09-15)


### Features

* add hunk-scoped lint and safe fixes ([b7ae901](https://github.com/srobroek/slopvac/commit/b7ae901816e832f7ade69acd8ff8cc5750981bb7))

## [2.4.0](https://github.com/srobroek/slopvac/compare/v2.3.2...v2.4.0) (2026-09-15)


### Features

* **lint:** add precise comment analysis pipeline ([23dc16e](https://github.com/srobroek/slopvac/commit/23dc16e998978ba91dc569405e6d3716682eee5f))


### Bug Fixes

* **ci:** satisfy lint gates ([bd3a84c](https://github.com/srobroek/slopvac/commit/bd3a84c3b254de6357e3390491ec69c7ae615be5))
* parse TOML multiline quote runs ([df7ba44](https://github.com/srobroek/slopvac/commit/df7ba4412387c474dc8ef646a8d594dc44c1c7eb))
* **vale:** normalize legacy comment line mappings ([fdfd969](https://github.com/srobroek/slopvac/commit/fdfd96985ede4d77197ac75745709bf15537ab31))

## [2.3.2](https://github.com/srobroek/slopvac/compare/v2.3.1...v2.3.2) (2026-09-14)


### Bug Fixes

* **lint:** keep emoji heading ranges literal ([#72](https://github.com/srobroek/slopvac/issues/72)) ([e37f8f2](https://github.com/srobroek/slopvac/commit/e37f8f2869f25c847420416ce476d2d396cc7a46))


### Documentation

* **audit:** name the four missed tells precisely; scope the pinned claim; annotate the 27 count ([#68](https://github.com/srobroek/slopvac/issues/68)) ([daa61cc](https://github.com/srobroek/slopvac/commit/daa61cceff6a39dc9e96791445103155a812522f))

## [2.3.1](https://github.com/srobroek/slopvac/compare/v2.3.0...v2.3.1) (2026-09-13)


### Bug Fixes

* **action:** move Vale and composite logic to Python ([#64](https://github.com/srobroek/slopvac/issues/64)) ([948329f](https://github.com/srobroek/slopvac/commit/948329f9a475a6a17eb82825fc031a02ef3ff962))


### Refactors

* **agnix:** replace shell checks with Python ([#65](https://github.com/srobroek/slopvac/issues/65)) ([438db46](https://github.com/srobroek/slopvac/commit/438db46f522ac3917625c91ce08798fecf69482e))


### Documentation

* **audit:** correct the judgement exceptions count; pin the narrowed rule's probe matrix ([#66](https://github.com/srobroek/slopvac/issues/66)) ([eac6833](https://github.com/srobroek/slopvac/commit/eac6833259dc27adc2920022bbc387e0f2c096b8))

## [2.3.0](https://github.com/srobroek/slopvac/compare/v2.2.0...v2.3.0) (2026-09-13)


### Features

* audit follow-ups: per-target config, native reach, Vale messages, dash gate ([#58](https://github.com/srobroek/slopvac/issues/58)) ([f847b02](https://github.com/srobroek/slopvac/commit/f847b027c1f5a5d481074990cb49379b3a3a19fb))
* rule, steering and code audit of 2026-09-12 ([#56](https://github.com/srobroek/slopvac/issues/56)) ([f7f2ad8](https://github.com/srobroek/slopvac/commit/f7f2ad84f97df804ed629b4298dd2369f9201c4c))


### Bug Fixes

* audit follow-ups 2: HTML/MDX prose, .rst converter gate, composite-action contract ([#59](https://github.com/srobroek/slopvac/issues/59)) ([9f0c426](https://github.com/srobroek/slopvac/commit/9f0c42634eb5214cf4f795e3927fd2b5e4b1f117))
* audit follow-ups 3: STE tokenizer and segmenter per docs/metrics.md ([#60](https://github.com/srobroek/slopvac/issues/60)) ([b4ea1df](https://github.com/srobroek/slopvac/commit/b4ea1dfac31a6fad7e5dd2a1877ee264d74691d0))
* **cli:** emit the requested report format when every target is excluded ([#61](https://github.com/srobroek/slopvac/issues/61)) ([e6799aa](https://github.com/srobroek/slopvac/commit/e6799aab957ea2d911781383efc2b2c4fd2d92b3))

## [2.2.0](https://github.com/srobroek/slopvac/compare/v2.1.0...v2.2.0) (2026-09-09)


### Features

* complete review hardening ([41921b5](https://github.com/srobroek/slopvac/commit/41921b52f4ce10aa420ce030103c6ddef2289e47))


### Bug Fixes

* **lint:** serialize Vale cache and skip Vale-owned fallback rules ([daf9629](https://github.com/srobroek/slopvac/commit/daf9629b40a9e962fe162848c696d011051266f7))
* **lint:** sort cache imports ([e2eaa7b](https://github.com/srobroek/slopvac/commit/e2eaa7bf832423b3981cc12adfd8bc402dbc1baf))


### Documentation

* split density scoring explanation ([24994c5](https://github.com/srobroek/slopvac/commit/24994c5588758b935d6bcd58c599c694b54e4e72))
* split scoring inputs for clarity ([d635eb9](https://github.com/srobroek/slopvac/commit/d635eb9c878a26ade695080f1318d54b3da67ba9))

## [2.1.0](https://github.com/srobroek/slopvac/compare/v2.0.0...v2.1.0) (2026-09-09)


### Features

* **action:** expose warnings, suggestions, documents and words ([#43](https://github.com/srobroek/slopvac/issues/43)) ([962cb83](https://github.com/srobroek/slopvac/commit/962cb8318e03845c6a1ac18acfbfbef4c03ee7c3))
* **lint:** category severity floor ([#39](https://github.com/srobroek/slopvac/issues/39)) ([f6b44ff](https://github.com/srobroek/slopvac/commit/f6b44ffffea453e75b8bc989258eb5796537157e))


### Bug Fixes

* **lint:** apply the 2026-09-09 review, split the large modules, drop the legacy Vale tree ([#38](https://github.com/srobroek/slopvac/issues/38)) ([18c37dc](https://github.com/srobroek/slopvac/commit/18c37dcaf2d11ef43ab9cf4610cae0664e2644af))
* **release:** stop stamping the OMP marketplace symlink ([#45](https://github.com/srobroek/slopvac/issues/45)) ([0ce2f1c](https://github.com/srobroek/slopvac/commit/0ce2f1c6fabd1c2c8c6ad5b4057cf408c55f0eeb))

## [2.0.0](https://github.com/srobroek/slopvac/compare/v1.0.3...v2.0.0) (2026-09-08)


### ⚠ BREAKING CHANGES

* Remove the APM manifest and compiled instruction adapters.

### Features

* replace APM packaging with native skills ([04b18dd](https://github.com/srobroek/slopvac/commit/04b18dd00e6b6cb5282e1e980d95183e490b88b3))


### Bug Fixes

* **ci:** declare manual publish inputs ([0fd060a](https://github.com/srobroek/slopvac/commit/0fd060abd67811312c2e517b77d34ca21e24a404))
* **ci:** harden staged instruction validation ([0423c89](https://github.com/srobroek/slopvac/commit/0423c89913ce5e69f43fc960d352ee053d067471))
* fail closed when staged diff cannot be read ([c1b2020](https://github.com/srobroek/slopvac/commit/c1b20208174c60be3bb8ab1ea7fa9179e7229d94))
* preserve every existing git hook ([320c7ae](https://github.com/srobroek/slopvac/commit/320c7ae7b13b36208693eee6b939c3f3673e5449))
* reject hook path collisions ([#37](https://github.com/srobroek/slopvac/issues/37)) ([146d4fc](https://github.com/srobroek/slopvac/commit/146d4fc9800897268d1f04599ab022344014fe48))


### Documentation

* resolve current prose findings ([d0fe206](https://github.com/srobroek/slopvac/commit/d0fe20625c7d36a918b3e11374954cfc2ceb1f4f))
* tighten development instructions ([f5ee697](https://github.com/srobroek/slopvac/commit/f5ee69770e3f88b6ca2e2f93f4f7e0d0e2bd482a))

## [1.0.3](https://github.com/srobroek/slopvac/compare/v1.0.2...v1.0.3) (2026-09-08)


### Bug Fixes

* correct Unicode matching and reject incomplete checks ([#33](https://github.com/srobroek/slopvac/issues/33)) ([b183001](https://github.com/srobroek/slopvac/commit/b1830014847fd679c40abc06d65bd18099c2f8d5))

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
