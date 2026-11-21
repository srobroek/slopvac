# Changelog

## [3.0.0](https://github.com/slopvac/slopvac/compare/v2.18.1...v3.0.0) (2026-11-21)


### ⚠ BREAKING CHANGES

* **migrate:** write backups to .slopvac/migrate-backup/<UTC timestamp>
* **release:** publish 3.x wheels from publish-pypi.yml ([#559](https://github.com/slopvac/slopvac/issues/559))
* **contract:** one slopvac plugins group, data and code kinds, reserved core and two compiled keys ([#615](https://github.com/slopvac/slopvac/issues/615))
* **engine:** Removed rules: vertical-list-lead-in-missing-colon, vertical-list-item-punctuation, safety-block-missing-consequence, inconsistent-term-for-same-thing, inconsistent-wording-for-same-step. `slopvac migrate` drops references to them.
* **engine:** make Input non_exhaustive with constructors ([#499](https://github.com/slopvac/slopvac/issues/499))

### Features

* **action:** add the slopvac 3.0 composite action with reviewdog, SARIF and Code Climate reports ([da33afa](https://github.com/slopvac/slopvac/commit/da33afab17159012b7e5e49706166c34a702e597))
* **agents:** add claims, changed-claim candidates with lexical alignment ([f1da5ff](https://github.com/slopvac/slopvac/commit/f1da5ff14c9b4cf583fa03323f897610f136a009))
* **agents:** add diagrams prime topic ([eb31257](https://github.com/slopvac/slopvac/commit/eb31257f49ff64bb02ef67053409350e4276d299))
* **agents:** add review types, scope budget and reviewer model rule ([c6e8922](https://github.com/slopvac/slopvac/commit/c6e89227bca254bff1477545162f1519f06258ac))
* **agents:** add setup for all harnesses including OpenCode ([4e57384](https://github.com/slopvac/slopvac/commit/4e57384f9d1fbb80c23eb93b0906bd100ea3a1eb))
* **agents:** append labelled PRIME.md notes after built-in prime text ([#693](https://github.com/slopvac/slopvac/issues/693)) ([93fc26d](https://github.com/slopvac/slopvac/commit/93fc26de571973910dc6214fbfa19551974f7d58))
* **agents:** generate reviewer model recommendations from eval results ([a47d12d](https://github.com/slopvac/slopvac/commit/a47d12dca1b100451ce9238ff4da85213b4aba84))
* **agents:** move slopvac-agents text onto the message registry ([#675](https://github.com/slopvac/slopvac/issues/675)) ([4fa063f](https://github.com/slopvac/slopvac/commit/4fa063fb9623623f6f5b4425ee6c3bc79e4ddfd6))
* **agents:** publish no reviewer ranking until the results are rescored ([#539](https://github.com/slopvac/slopvac/issues/539)) ([0312302](https://github.com/slopvac/slopvac/commit/0312302b848f2f747da1c72d64ee4693a9011d68))
* **agents:** read [guidance] from slopvac-config in prime and setup ([bb7d564](https://github.com/slopvac/slopvac/commit/bb7d564423bf5a49493d4fa36d6602d788387e9f))
* **agents:** render prime topics from Markdown with levels and overrides ([368ff1e](https://github.com/slopvac/slopvac/commit/368ff1e1082cd9f22dba22f4f8c58b15cdb717ba))
* **agents:** serve prime migrate from the shared migration guide ([3a4c8f9](https://github.com/slopvac/slopvac/commit/3a4c8f9a576a67b94ab264953699261a6672b3c8))
* **agents:** warn on an unset reviewer model, add --author-model and a model guide ([#563](https://github.com/slopvac/slopvac/issues/563)) ([10a7258](https://github.com/slopvac/slopvac/commit/10a7258b5eeb9b9efd2273f9edb337a9782d014d))
* **ci:** accept the 3.0 fork-review artifact in the privileged consumer ([3951b67](https://github.com/slopvac/slopvac/commit/3951b67561c21a614728cea39c40b55a33768296))
* **ci:** add MegaLinter and Trunk descriptors for slopvac ([#468](https://github.com/slopvac/slopvac/issues/468)) ([e8d62e6](https://github.com/slopvac/slopvac/commit/e8d62e69f7eed0031430c55595b5b249cbb4627c))
* **cli:** add the clap command tree and global settings ([8445dc0](https://github.com/slopvac/slopvac/commit/8445dc01212fc61c361383cf7f2f0edb69affcbc))
* **cli:** assign genres from [[genres]] blocks and share one files matcher ([#606](https://github.com/slopvac/slopvac/issues/606)) ([2598b05](https://github.com/slopvac/slopvac/commit/2598b05103f8ca607761b975badcce98f026d9a0))
* **cli:** lint with the real engine ([#474](https://github.com/slopvac/slopvac/issues/474)) ([c28feea](https://github.com/slopvac/slopvac/commit/c28feea6735d5cae73bb517fd788c16948ed2c31))
* **cli:** list and explain rules with slopvac rules and slopvac explain ([779129e](https://github.com/slopvac/slopvac/commit/779129e6ba2eda2ddbc2a5e0b8463be7c6e2bde2))
* **cli:** open the --out report with the platform opener under lint --open ([#501](https://github.com/slopvac/slopvac/issues/501)) ([ac9e812](https://github.com/slopvac/slopvac/commit/ac9e812856ff7cad4a912ef730f88bba91bac4eb))
* **cli:** port slopvac init with a schema-generated commented config ([53009f1](https://github.com/slopvac/slopvac/commit/53009f1cd7920e2c55f2224060ca9bfcf7bc4c3b))
* **cli:** render lint reports in every format and write them with --out ([403ba1b](https://github.com/slopvac/slopvac/commit/403ba1b91cc050595f13c3651a9c4f225cbdf9e5))
* **cli:** report doctor's install method and update state from slopvac-update ([#515](https://github.com/slopvac/slopvac/issues/515)) ([af9f4e9](https://github.com/slopvac/slopvac/commit/af9f4e94894a4b5b514f7b533ed703ef338eb193))
* **cli:** resolve rule severity through config and styles in rules and explain ([#462](https://github.com/slopvac/slopvac/issues/462)) ([9bc6391](https://github.com/slopvac/slopvac/commit/9bc639180b5846045db426c2cf6e74dbdfb3b349))
* **cli:** stdin linting contract for lint --stdin and --language ([34fe02a](https://github.com/slopvac/slopvac/commit/34fe02a02f6702c6302b7924d0ce29a5744a5e89))
* **cli:** wire lint --explain-config ([#683](https://github.com/slopvac/slopvac/issues/683)) ([e5895fe](https://github.com/slopvac/slopvac/commit/e5895fe0680cc46354f77651f7e484e7d75e3453))
* **cli:** wire slopvac claims ([#653](https://github.com/slopvac/slopvac/issues/653)) ([a516007](https://github.com/slopvac/slopvac/commit/a516007848ccdc11c158e6694e51b31f20f4e2a9))
* **cli:** wire slopvac migrate into the binary ([aadaa13](https://github.com/slopvac/slopvac/commit/aadaa13d9165ae83f093901c6972fbb59995f3fa))
* **cli:** wire slopvac review through the owner crate ([#616](https://github.com/slopvac/slopvac/issues/616)) ([a953a08](https://github.com/slopvac/slopvac/commit/a953a089533ce2e3929b0d0a1678dc5f607ab93d))
* **cli:** wire terms files, blocklists and the casing rule into lint and lsp ([#520](https://github.com/slopvac/slopvac/issues/520)) ([d00153c](https://github.com/slopvac/slopvac/commit/d00153c14c1649159d5f6ad41e5ef0c88757963c))
* **cli:** wire terms, genre, validate, setup and prime from their owner crates ([#491](https://github.com/slopvac/slopvac/issues/491)) ([0a77065](https://github.com/slopvac/slopvac/commit/0a770656bc56bfb1dd096195a9593934e8fc77ff))
* **comments:** extract code comments with tree-sitter ([#371](https://github.com/slopvac/slopvac/issues/371)) ([c452710](https://github.com/slopvac/slopvac/commit/c45271050f1171e51cea46a923245b9ee335821e))
* **comments:** extract Python docstrings in comment mode ([#648](https://github.com/slopvac/slopvac/issues/648)) ([fbb8d7a](https://github.com/slopvac/slopvac/commit/fbb8d7ac0111e4fabd3f3811c522b37d7ef848d9))
* **config:** add the validate command ([0dcf51f](https://github.com/slopvac/slopvac/commit/0dcf51f910f47faf5a5855fce72f93cf1fdf08cd))
* **config:** read front matter under the project's allow policy ([86fa85d](https://github.com/slopvac/slopvac/commit/86fa85d6e3e99ab332cc93209adfca60af9ff5e0))
* **config:** read inline directives for formats without front matter ([9ad7ab9](https://github.com/slopvac/slopvac/commit/9ad7ab93def3bd37e6a5e8c94a022dfda6ee390e))
* **config:** resolve layered settings with per-value provenance ([acf73d5](https://github.com/slopvac/slopvac/commit/acf73d5c119f283b4148816b127d28b68bf57918))
* **config:** validate config and front matter with coded diagnostics ([caefcf0](https://github.com/slopvac/slopvac/commit/caefcf06afed874c1f563a39da7e36c08ef15c1c))
* **config:** warn on unknown rule ids with config-unknown-rule ([#685](https://github.com/slopvac/slopvac/issues/685)) ([0a34b81](https://github.com/slopvac/slopvac/commit/0a34b81e52f4bdc635844348ac0fbb35fb631dc7))
* **context:** add the change-note, requirement, invariant and structural taggers ([f83b368](https://github.com/slopvac/slopvac/commit/f83b3681162ad2a901414c08a94d9bcd85c27510))
* **context:** add the genre registry with detection and the genre command ([e79489a](https://github.com/slopvac/slopvac/commit/e79489a0b92f6954a5da701ecc1d7857daf8d1bd))
* **context:** add the mixed content-type judgement item ([07b140e](https://github.com/slopvac/slopvac/commit/07b140e6993669f6a7fc28021f988fc5a1d74d9d))
* **context:** add the tagger interface, registry and declarative taggers ([cab7ea5](https://github.com/slopvac/slopvac/commit/cab7ea527fe46479b1321c452aeb90db595023d8))
* **context:** add ui-copy, agent-instructions and Diataxis content types ([f6967eb](https://github.com/slopvac/slopvac/commit/f6967eb8387eb088580d5216706ab782793a0b7c))
* **context:** align genre and tagger structs with the v3 pack schemas ([c0c58b8](https://github.com/slopvac/slopvac/commit/c0c58b8b22e0b89841e35f7d54c47ba29ad23704))
* **context:** carry history-internal-reference tolerances per genre ([#451](https://github.com/slopvac/slopvac/issues/451)) ([1124146](https://github.com/slopvac/slopvac/commit/11241462df9a0863ac8ac6a1351a67f77b102499))
* **context:** declare security context from a genre and add the enforcement hint ([766148a](https://github.com/slopvac/slopvac/commit/766148a248cd6971260117bc752a1832276bdd5c))
* **context:** filter review checklists by context ([e62e504](https://github.com/slopvac/slopvac/commit/e62e504726469938a575fda32a01cab94f74c564))
* **contract:** accept none to clear a category budget in config ([1163ad6](https://github.com/slopvac/slopvac/commit/1163ad65d571f4b9020b56f32a12d7c5a6138244))
* **contract:** add binary-extractor/extract hook kind (slopvac-8l4.2.27) ([#514](https://github.com/slopvac/slopvac/issues/514)) ([008275a](https://github.com/slopvac/slopvac/commit/008275a4a7d48a0e97d82f5a2689fe1a7c49f60f))
* **contract:** add optional Finding.origin (slopvac-8l4.2.29) ([#517](https://github.com/slopvac/slopvac/issues/517)) ([628effc](https://github.com/slopvac/slopvac/commit/628effceb31e44c2425443cae231d4ebd8efc069))
* **contract:** add the additive-only schema check and schema-source policy ([#524](https://github.com/slopvac/slopvac/issues/524)) ([5d4ff12](https://github.com/slopvac/slopvac/commit/5d4ff1200b896784f478f14ec8bd09f2ec566472))
* **contract:** add the removed-rules list and fix the legacy style gaps ([#567](https://github.com/slopvac/slopvac/issues/567)) ([a9f233d](https://github.com/slopvac/slopvac/commit/a9f233d1f4c611cc4347172106f8e45fe8b42c0b))
* **contract:** define pack manifest, style, genre, tagger, terms and lockfile schemas ([d460f72](https://github.com/slopvac/slopvac/commit/d460f72f5f4d26ade1130cc720c61081f150914e))
* **contract:** define the v3 config and front-matter schemas ([1b7ec28](https://github.com/slopvac/slopvac/commit/1b7ec287b79c6a0610a8939e968b6921f9669023))
* **contract:** define the v3 lint report schema ([575a0f7](https://github.com/slopvac/slopvac/commit/575a0f7eb93e224d78cf5b388695b70834d51591))
* **contract:** define the v3 rule and category schemas ([433d288](https://github.com/slopvac/slopvac/commit/433d288ed52e7b326b1e0152994d5b1f663bafd4))
* **contract:** map 2.x profiles and tiers onto 3.0 styles ([134fada](https://github.com/slopvac/slopvac/commit/134fada8ec1ce42ec82994a1d40088654297c4c4))
* **contract:** one slopvac plugins group, data and code kinds, reserved core and two compiled keys ([#615](https://github.com/slopvac/slopvac/issues/615)) ([d6d9a29](https://github.com/slopvac/slopvac/commit/d6d9a2985d36539be02605abfbbd87acb14b2c7b))
* **contract:** specify the plugin index model ([#684](https://github.com/slopvac/slopvac/issues/684)) ([d82d114](https://github.com/slopvac/slopvac/commit/d82d114b91be5b4920d518874e57eea3e4d8cce7))
* **diagrams:** add the deterministic diagram label and prose signals ([f0cf258](https://github.com/slopvac/slopvac/commit/f0cf258492754a85c40d1d159eea169b4729129e))
* **diagrams:** add the slopvac-diagrams crate with a Mermaid extractor ([c7b10ca](https://github.com/slopvac/slopvac/commit/c7b10ca1932fb15d9244b755ca78db85b2482102))
* **diagrams:** dispatch diagram signals from a rule pack through the engine ([45fd757](https://github.com/slopvac/slopvac/commit/45fd757901b68df5606d9a6769dd52d7274938ec))
* **diagrams:** extract draw.io labels ([52d081a](https://github.com/slopvac/slopvac/commit/52d081a392fd04421b21dadbeadb16bdcad57935))
* **diagrams:** extract PlantUML and Excalidraw labels ([4b7017e](https://github.com/slopvac/slopvac/commit/4b7017eb512bd9230a3f4c446624cbf5c829e671))
* **diagrams:** find diagram fences with slopvac-parse code blocks ([16780d6](https://github.com/slopvac/slopvac/commit/16780d6497846fb25da02e9f58b523a35feac48b))
* **docs:** generate style and built-in terms reference pages ([f5355dd](https://github.com/slopvac/slopvac/commit/f5355dd131b2cd0bc6c83e8ed25f99a94c9bba78))
* **docs:** generate the reference docs site source ([0a8c42c](https://github.com/slopvac/slopvac/commit/0a8c42ca93c30b928cf676291cc254bfddc5bd6d))
* **docs:** scaffold the Starlight site over the generated pages ([3928d35](https://github.com/slopvac/slopvac/commit/3928d3524206eaf7b5fa1a4dbfd0d71b6dfcffc1))
* **doctor:** report version, update state, config, packs, trust and directories ([#435](https://github.com/slopvac/slopvac/issues/435)) ([80e2272](https://github.com/slopvac/slopvac/commit/80e227260c3a999cf3785cd7034c361267708374))
* **engine:** add the capitalization rule kind ([#394](https://github.com/slopvac/slopvac/issues/394)) ([03893c9](https://github.com/slopvac/slopvac/commit/03893c989eb65bd2232a4b7e09f8ae395056160d))
* **engine:** add the locale rule ([#408](https://github.com/slopvac/slopvac/issues/408)) ([de4a20e](https://github.com/slopvac/slopvac/commit/de4a20ea496d124f02a1f93824d4c089d83681f8))
* **engine:** add the negated-antecedent detector and the LLM firing rate ([#470](https://github.com/slopvac/slopvac/issues/470)) ([97913e6](https://github.com/slopvac/slopvac/commit/97913e684e96f412adfbc45536b5e53f5b16d4ea))
* **engine:** apply safe substitution fixes ([#395](https://github.com/slopvac/slopvac/issues/395)) ([c7b41dd](https://github.com/slopvac/slopvac/commit/c7b41dd153299110b1ece79dc444f031ee0d470c))
* **engine:** compute changed-line scope from git ([#396](https://github.com/slopvac/slopvac/issues/396)) ([01d593c](https://github.com/slopvac/slopvac/commit/01d593cbb9df9f5619ccf5379909356a58f05767))
* **engine:** discover files with ignore and globset ([#361](https://github.com/slopvac/slopvac/issues/361)) ([54c3500](https://github.com/slopvac/slopvac/commit/54c35001c5cf97b920414c93b859813bc8b3aa50))
* **engine:** fix RST files outside protected spans ([#412](https://github.com/slopvac/slopvac/issues/412)) ([09581d5](https://github.com/slopvac/slopvac/commit/09581d5fb733f33561588317ec57c7e086c815d3))
* **engine:** lint documents with matching, exceptions, directives and scoring ([#388](https://github.com/slopvac/slopvac/issues/388)) ([ee3132d](https://github.com/slopvac/slopvac/commit/ee3132d4249eb725d3b8da70a20dcb20188596f3))
* **engine:** lint raw HTML block prose with every rule ([#421](https://github.com/slopvac/slopvac/issues/421)) ([acdbecf](https://github.com/slopvac/slopvac/commit/acdbecfc167b547be336c076a858e4b548ad6d65))
* **engine:** lint RST through a bundled docutils adapter ([#393](https://github.com/slopvac/slopvac/issues/393)) ([3fa5c3b](https://github.com/slopvac/slopvac/commit/3fa5c3bdc704ca91d5745295657c45e51f9972e5))
* **engine:** lint the comments of source files ([0b0acec](https://github.com/slopvac/slopvac/commit/0b0acecd164d57759196625b19ba7f4e0d1e7790))
* **engine:** port the metric rules ([#390](https://github.com/slopvac/slopvac/issues/390)) ([ddaccde](https://github.com/slopvac/slopvac/commit/ddaccde7c31d80e0ffcb09d86f8989ccbaf53560))
* **engine:** resolve the genre of each document and apply its levels ([#538](https://github.com/slopvac/slopvac/issues/538)) ([00404f1](https://github.com/slopvac/slopvac/commit/00404f1c977cc375d22faf81be0c54043e4eb44d))
* **engine:** run comment-mode rules on extracted comments ([#617](https://github.com/slopvac/slopvac/issues/617)) ([0b0acec](https://github.com/slopvac/slopvac/commit/0b0acecd164d57759196625b19ba7f4e0d1e7790))
* **engine:** run heading-hierarchy and remove five unimplemented structure rules ([#502](https://github.com/slopvac/slopvac/issues/502)) ([fb5c997](https://github.com/slopvac/slopvac/commit/fb5c9974660f826090eedd72f45a1dfb72ada340))
* **engine:** run vocabulary rules on the Rust POS tagger ([#392](https://github.com/slopvac/slopvac/issues/392)) ([e3c5e28](https://github.com/slopvac/slopvac/commit/e3c5e28e5b205bf716b3fca275c8ad4e76d593f5))
* **evals:** add GPT-6 Luna to model evals with 2026-11-17 results ([#549](https://github.com/slopvac/slopvac/issues/549)) ([eb25259](https://github.com/slopvac/slopvac/commit/eb25259de07ad98b2ba2f41d44bfb7f095d9b807))
* **evals:** add model evals per review type with 2026-11-14 results ([#404](https://github.com/slopvac/slopvac/issues/404)) ([359a644](https://github.com/slopvac/slopvac/commit/359a644cf3850a1d235c1e0bcd96477ffe5f4ded))
* **evals:** add the eval corpus manifest and fetch tooling ([6e43579](https://github.com/slopvac/slopvac/commit/6e4357906fc6e37f00308adbdb6cdfcfe767ea95))
* **evals:** add the eval runner, scorecard and paired A/B ([9037bcb](https://github.com/slopvac/slopvac/commit/9037bcb8280c37a38f770ecd87346639f3a5db5c))
* **evals:** add the labelling workflow with two-family judges and adjudication ([eb8cc6a](https://github.com/slopvac/slopvac/commit/eb8cc6a72218311abe1dd4986e1e73ecf0ffc151))
* **evals:** add the precision ratchet with a committed baseline ([b348562](https://github.com/slopvac/slopvac/commit/b348562fcfa7f42d9e984b12f18e28808a96dec8))
* **evals:** cap label judge invocations and add the review worksheet ([#631](https://github.com/slopvac/slopvac/issues/631)) ([d12f45c](https://github.com/slopvac/slopvac/commit/d12f45c9db8ca948310402df42dbc5f1949e2596))
* **evals:** LLM-written diagram set with per-rule recall and precision ([#479](https://github.com/slopvac/slopvac/issues/479)) ([f2e806c](https://github.com/slopvac/slopvac/commit/f2e806c7c20bb6a8201276e5eb0b85c21646c444))
* **evals:** planted-damage reviewer tasks for mechanical and update ([#633](https://github.com/slopvac/slopvac/issues/633)) ([2065ce6](https://github.com/slopvac/slopvac/commit/2065ce6842ba7747d37e480a7b5d20b55fb8e076))
* **evals:** record token usage and model per invocation and add models cost ([#505](https://github.com/slopvac/slopvac/issues/505)) ([5152b14](https://github.com/slopvac/slopvac/commit/5152b146269d7d0c34b7b5c03805142b80eea2e6))
* **frontmatter-spans:** generic front-matter crate with value spans ([#351](https://github.com/slopvac/slopvac/issues/351)) ([338424b](https://github.com/slopvac/slopvac/commit/338424b405a40af5862b03295af6a02641793c8f))
* **fs:** add slopvac-fs crate ([#510](https://github.com/slopvac/slopvac/issues/510)) ([ffa40df](https://github.com/slopvac/slopvac/commit/ffa40df6504be1c769505362eaa5f5f6c87d189a))
* **fs:** harden errors, add confined regular-file reads ([#545](https://github.com/slopvac/slopvac/issues/545)) ([4c948d2](https://github.com/slopvac/slopvac/commit/4c948d2853cffff91e68be42fa422d09371aa2de))
* **hooks:** ship binary-based pre-commit hooks and document prek, lefthook and hk ([047257d](https://github.com/slopvac/slopvac/commit/047257d568f06ac75893f51917da0515ab650036))
* **lsp:** add slopvac lsp on lsp-server ([57aa04c](https://github.com/slopvac/slopvac/commit/57aa04cd3546c73f47d038a5e3b8dd38398af619))
* **lsp:** move language server messages onto the message registry ([#618](https://github.com/slopvac/slopvac/issues/618)) ([c4d82f1](https://github.com/slopvac/slopvac/commit/c4d82f175b8724b69380aaaa56ab0cc4f5b69594))
* **lsp:** one incomplete diagnostic for binary container documents (slopvac-8l4.20.14) ([#541](https://github.com/slopvac/slopvac/issues/541)) ([e6e6408](https://github.com/slopvac/slopvac/commit/e6e6408a10949180b401ebf6fb7f7362eddf6599))
* **lsp:** register the front-matter validation check ([#699](https://github.com/slopvac/slopvac/issues/699)) ([66e7943](https://github.com/slopvac/slopvac/commit/66e7943a4f94643499517d75a6a145b79ccd66da))
* **lsp:** show extract-unsupported notices as information diagnostics ([#674](https://github.com/slopvac/slopvac/issues/674)) ([8e35269](https://github.com/slopvac/slopvac/commit/8e352692fa231b080e7688135e2774c47e964dc7))
* **messages:** add the message catalog crates and registry checks ([#526](https://github.com/slopvac/slopvac/issues/526)) ([de6b848](https://github.com/slopvac/slopvac/commit/de6b848386a99cdec53ddb047a553c9857d5f2ff))
* **messages:** move text, pos, parse and terms onto the message registry ([#677](https://github.com/slopvac/slopvac/issues/677)) ([f634507](https://github.com/slopvac/slopvac/commit/f634507f9f5b2dddb5fd9825333e50a65341ad43))
* **migrate:** add the slopvac-migrate crate for 2.x to 3.0 rewrites ([be392f8](https://github.com/slopvac/slopvac/commit/be392f83c31d8b0ef1d693a0eb4942245a40e1a3))
* **migrate:** detect 2.x configs with the config version gate and lint both sides with the engine ([#495](https://github.com/slopvac/slopvac/issues/495)) ([b1f069d](https://github.com/slopvac/slopvac/commit/b1f069ded38cfddb06a5063da2cf71e648438345))
* **migrate:** drop the five removed 2.x structure rules ([#512](https://github.com/slopvac/slopvac/issues/512)) ([ea7765a](https://github.com/slopvac/slopvac/commit/ea7765ac1bc433895bd3a075c030e4ba19857fb3))
* **migrate:** expand --preserve-behavior into the 2.x profile gates ([48e58b6](https://github.com/slopvac/slopvac/commit/48e58b66b326b5e9d3b24c4e1b0c92330f9de686))
* **migrate:** generate the rename table and legacy data from the landed contract ([a4a8ba8](https://github.com/slopvac/slopvac/commit/a4a8ba8d46e9b7aed8b8b9519608c742af3f440e))
* **migrate:** prime migrate renders only the decision sections ([#613](https://github.com/slopvac/slopvac/issues/613)) ([2ca414d](https://github.com/slopvac/slopvac/commit/2ca414d4d9286321bd699c402224d5a4f1ef8c34))
* **migrate:** report removed rules and categories with migrate-rule-removed ([#654](https://github.com/slopvac/slopvac/issues/654)) ([de68ca2](https://github.com/slopvac/slopvac/commit/de68ca27c035d0d465245bd0fa0db694408042ed))
* **migrate:** rewrite 2.x steering blocks to the block setup writes ([d9b27de](https://github.com/slopvac/slopvac/commit/d9b27de4fb729b494633fb9ff4e553ebbc8a6d03))
* **migrate:** write backups to .slopvac/migrate-backup/&lt;UTC time&gt; ([#673](https://github.com/slopvac/slopvac/issues/673)) ([de0cb6b](https://github.com/slopvac/slopvac/commit/de0cb6b19caf793080a5dd5bf92ed67bd1e86bf8))
* **migrate:** write backups to .slopvac/migrate-backup/&lt;UTC timestamp&gt; ([de0cb6b](https://github.com/slopvac/slopvac/commit/de0cb6b19caf793080a5dd5bf92ed67bd1e86bf8))
* **model:** add core types, position index and edit application ([14db3d2](https://github.com/slopvac/slopvac/commit/14db3d2c5e4e671fb675096e17db58633a0df941))
* **model:** add optional structured data to lint-report Notice ([#571](https://github.com/slopvac/slopvac/issues/571)) ([cc662f7](https://github.com/slopvac/slopvac/commit/cc662f7cd8310c14cf821d6deac2cdb29cfded51))
* **packs:** embedded core pack with directory and embedded sources ([#647](https://github.com/slopvac/slopvac/issues/647)) ([b63911f](https://github.com/slopvac/slopvac/commit/b63911f180327a83e9c6de72ea6eab0b99d9256a))
* **packs:** pack manifest parser and namespaced registry (slopvac-8l4.9.1 step 1) ([#570](https://github.com/slopvac/slopvac/issues/570)) ([c02ee03](https://github.com/slopvac/slopvac/commit/c02ee0355275d9d2f0e5b8359801ea482be5e83f))
* **parse:** carry list and quote ancestry on HTML blocks ([#397](https://github.com/slopvac/slopvac/issues/397)) ([6314bac](https://github.com/slopvac/slopvac/commit/6314baca50969c7566a730672b4826c8a3e582df))
* **parse:** extract HTML text with positions ([#367](https://github.com/slopvac/slopvac/issues/367)) ([e1f02fa](https://github.com/slopvac/slopvac/commit/e1f02fae272bfd3d7839a6753a44097c41bd8496))
* **parse:** parse Markdown and MDX into blocks with exact positions ([#358](https://github.com/slopvac/slopvac/issues/358)) ([51c181f](https://github.com/slopvac/slopvac/commit/51c181fd98445a64b83d3b6e634345123dd15331))
* **plugins:** add key rotation and the signed revocation list ([38f1ed0](https://github.com/slopvac/slopvac/commit/38f1ed00e36fae9604e45547e9dddc5808151014))
* **plugins:** add pack index schema, builder and search ([36b89ed](https://github.com/slopvac/slopvac/commit/36b89edce796824d8014a84496ef4f8b9605126f))
* **plugins:** add plugin resource limits, a Linux subreaper and the stalled-frame rule ([#389](https://github.com/slopvac/slopvac/issues/389)) ([1804271](https://github.com/slopvac/slopvac/commit/18042716a3e7322d0d85481ab95bda7930b60ef2))
* **plugins:** add safe archive extraction ([985e46d](https://github.com/slopvac/slopvac/commit/985e46dca7a6bd0c7dc7d616dcd2f416d6c1ae2f))
* **plugins:** add the JSON-RPC plugin host ([9a56ed3](https://github.com/slopvac/slopvac/commit/9a56ed377c7f984d87f7470abd68326ee44b6b48))
* **plugins:** add the OCI client on ureq ([d828c68](https://github.com/slopvac/slopvac/commit/d828c681a92dc507782cba599cef23d87355dc9d))
* **plugins:** add the packs.lock model and lock diff ([1a067b6](https://github.com/slopvac/slopvac/commit/1a067b68399907018fd4414441f8084a4b2629be))
* **plugins:** add the Python plugin SDK and conformance suite ([bda85fb](https://github.com/slopvac/slopvac/commit/bda85fb174dd9d06ca5a6642286b8022ab79fd7d))
* **plugins:** add the trust store and the spawn gate ([9c64dbd](https://github.com/slopvac/slopvac/commit/9c64dbd86b2bc7f77e1aafa8984f967c922c3f36))
* **plugins:** apply fixer edits and recipe plans safely ([3b8e5ac](https://github.com/slopvac/slopvac/commit/3b8e5ac0224f61dc60c4ea4211021b3830b90825))
* **plugins:** compile the plugins key beside the release key ([#641](https://github.com/slopvac/slopvac/issues/641)) ([c05d7c1](https://github.com/slopvac/slopvac/commit/c05d7c1e5a277e743cffa6717c1113ce784a275a))
* **plugins:** embed the first-party release key as the signing and revocation root ([a92c46c](https://github.com/slopvac/slopvac/commit/a92c46c97f795c625e7317b2b1294cc1b84d67f8))
* **plugins:** fetch git pack sources at their pinned commit ([#464](https://github.com/slopvac/slopvac/issues/464)) ([b40da4d](https://github.com/slopvac/slopvac/commit/b40da4d96057e08e3e978c7988f561ad926e0a13))
* **plugins:** key the trust hash's commitment to environment values ([#629](https://github.com/slopvac/slopvac/issues/629)) ([b461290](https://github.com/slopvac/slopvac/commit/b46129001104618f93bd99a8d360cb19c98ed79f))
* **plugins:** managed Python environments for plugins (threat model Y1 to Y7) ([#428](https://github.com/slopvac/slopvac/issues/428)) ([961a857](https://github.com/slopvac/slopvac/commit/961a8577489920cdd0ccd5dba2747200fafb4dca))
* **plugins:** one shared sanitizer for plugin-origin text ([21cb2ed](https://github.com/slopvac/slopvac/commit/21cb2ed096ffdacc45f61affa6b1614f47eccf5a))
* **plugins:** sync the lock into the data dir, with status and CI check ([d44e193](https://github.com/slopvac/slopvac/commit/d44e19385b6dbc578978489b77a0fb8758d037ec))
* **plugins:** update the lock within config ranges ([#456](https://github.com/slopvac/slopvac/issues/456)) ([971c0e1](https://github.com/slopvac/slopvac/commit/971c0e1cf0159097cef06ff33153747ae1e35d70))
* **plugins:** verify minisign signatures over a canonical statement ([0bad537](https://github.com/slopvac/slopvac/commit/0bad5376c6211ea25385f81a0b424d231dc35aac))
* **plugins:** whole-run output budget across plugins (threat model P3) ([#459](https://github.com/slopvac/slopvac/issues/459)) ([5b2926e](https://github.com/slopvac/slopvac/commit/5b2926ed2b7303bd7cab8d02337a46c740d40de4))
* **plugins:** wire managed Python environments into sync, status and the spawn gate ([#481](https://github.com/slopvac/slopvac/issues/481)) ([91cc180](https://github.com/slopvac/slopvac/commit/91cc1804255f60231ba7ef3696b1994bec7c3282))
* **pos:** port the prose v3.3.1 averaged-perceptron tagger ([#355](https://github.com/slopvac/slopvac/issues/355)) ([92e5d8e](https://github.com/slopvac/slopvac/commit/92e5d8e12091ad7eb273515362b3231a00a527f2))
* **release:** add the 3.0.0 release-readiness gate script and checklist ([00169e4](https://github.com/slopvac/slopvac/commit/00169e432a02360b9b48748030e92a305048fe98))
* **release:** add the release candidate workflow and stable provenance gate ([b95d44c](https://github.com/slopvac/slopvac/commit/b95d44c93f29f67fff66e76793515a3e5b3e982e))
* **release:** minisign signing and App-minted Homebrew tap token ([61f55f7](https://github.com/slopvac/slopvac/commit/61f55f738ab349f4731ee01499db01a3cd59f45f))
* **report:** move report errors and labels onto the message registry ([#621](https://github.com/slopvac/slopvac/issues/621)) ([c0786e6](https://github.com/slopvac/slopvac/commit/c0786e6465c7b246a648b8ae4d29512e65a4cde4))
* **report:** preview and submit issue reports and generate the issue forms ([#475](https://github.com/slopvac/slopvac/issues/475)) ([cd0873f](https://github.com/slopvac/slopvac/commit/cd0873f6997887d35b7dd7e353d3de4edf6e5405))
* **report:** render the lint report in every output format ([c23774f](https://github.com/slopvac/slopvac/commit/c23774f691caca71d9acfd327679e1ea23fc3360))
* **rules:** add history-internal-reference ([#405](https://github.com/slopvac/slopvac/issues/405)) ([4a8a7a5](https://github.com/slopvac/slopvac/commit/4a8a7a589cfdff8301b5ec0d9390673ada6e8f31))
* **rules:** add the mixed content types judgment rule ([#550](https://github.com/slopvac/slopvac/issues/550)) ([dddd4ab](https://github.com/slopvac/slopvac/commit/dddd4abae6fba60cab476a40c4fc70a7e155dd6c))
* **rules:** context gates in the Python model, converter and golden deltas ([#504](https://github.com/slopvac/slopvac/issues/504)) ([a8f0d3c](https://github.com/slopvac/slopvac/commit/a8f0d3ce473afbdc584bacdc07a96c23a35460c5))
* **rules:** load v3 rules and compile them with PCRE2 ([#381](https://github.com/slopvac/slopvac/issues/381)) ([7fcd5c8](https://github.com/slopvac/slopvac/commit/7fcd5c80997d0f0df4b2f14eb135c9f6ad9468b7))
* **rules:** run rule test cases ([#419](https://github.com/slopvac/slopvac/issues/419)) ([35a3f5a](https://github.com/slopvac/slopvac/commit/35a3f5a58fbf0d5ca8a88a412336baa36ae61f8e))
* **rules:** skip change-note context in history-narration ([#578](https://github.com/slopvac/slopvac/issues/578)) ([2d4ca96](https://github.com/slopvac/slopvac/commit/2d4ca9604c532594a3a3716f5f807944a955a623))
* **schemas:** add genre contexts and structural tagger conditions ([#455](https://github.com/slopvac/slopvac/issues/455)) ([f02ef60](https://github.com/slopvac/slopvac/commit/f02ef60fd95a50489cea8017be1ec66e40ba4d8b))
* **schemas:** generate common, lint-report, rule and category from the Rust types ([#588](https://github.com/slopvac/slopvac/issues/588)) ([bdbccb6](https://github.com/slopvac/slopvac/commit/bdbccb6eed17127c6baeec010b843937a9fdffed))
* stable codes for the update policy cap, style detection cap and fix refusals ([#610](https://github.com/slopvac/slopvac/issues/610)) ([cf6b3cd](https://github.com/slopvac/slopvac/commit/cf6b3cdc8ac863fcafe54b5f689eb36a69ab171b))
* **styles:** add minimum_severity and a clearing max_per_100_words ([d79873a](https://github.com/slopvac/slopvac/commit/d79873ad8d9548cdca5b7a45e4b82f11f8d4d524))
* **styles:** add the Google developer style preset ([ef8a40b](https://github.com/slopvac/slopvac/commit/ef8a40bd2046942ce83b7b72e793ce278313903f))
* **styles:** bundle the STE preset ([8a45c06](https://github.com/slopvac/slopvac/commit/8a45c06e53e1e57f90cc4290607e5c68a5927622))
* **styles:** detect house styles in init and add prime configure guidance ([#461](https://github.com/slopvac/slopvac/issues/461)) ([f680c71](https://github.com/slopvac/slopvac/commit/f680c715ef30adc59a20d0541a3ccdc0e60601aa))
* **styles:** generate reference pages for the bundled presets ([6791f60](https://github.com/slopvac/slopvac/commit/6791f60f9fc401927c5d2732acc4c00e7d11df75))
* **styles:** load presets through the style schema and the config layer stack ([#453](https://github.com/slopvac/slopvac/issues/453)) ([9fb6a02](https://github.com/slopvac/slopvac/commit/9fb6a02fbc2816d0097c502818a505d933029d2a))
* **styles:** report a style detection file over the size cap as an info notice ([#625](https://github.com/slopvac/slopvac/issues/625)) ([76ed3f5](https://github.com/slopvac/slopvac/commit/76ed3f5cecb91e17a531dd804a53dac9dc087cb7))
* **styles:** resolve ordered style presets with conflict reporting ([22b757e](https://github.com/slopvac/slopvac/commit/22b757e492a1550e6fae5834d49f0acb0612d440))
* **terms:** add term files, blocklists and the casing matcher ([e91dd90](https://github.com/slopvac/slopvac/commit/e91dd90ee50375848cd1419faada810e723f8e7e))
* **terms:** add terms suggest with evidence counts ([dcdf647](https://github.com/slopvac/slopvac/commit/dcdf647f8b8ab9ae5d92bef6221cbdc713316d36))
* **terms:** add the terms command ([a38dc77](https://github.com/slopvac/slopvac/commit/a38dc7726480443c8327ceae4dd1a23f87f764b1))
* **terms:** bundle the built-in terms list ([b28c382](https://github.com/slopvac/slopvac/commit/b28c382f51e2b0e9d77dce07211f766418593245))
* **terms:** doc- and repo-level proper-noun inference (H4) ([#483](https://github.com/slopvac/slopvac/issues/483)) ([6fcdd80](https://github.com/slopvac/slopvac/commit/6fcdd80934160ab4bd32e3fe828670e4ee4c9941))
* **terms:** follow the terms schema and load YAML blocklists ([#448](https://github.com/slopvac/slopvac/issues/448)) ([4de8e16](https://github.com/slopvac/slopvac/commit/4de8e16cfb96462ea8419ee7fcf56af0565ff3f4))
* **terms:** generate the built-in terms reference page ([83de5b1](https://github.com/slopvac/slopvac/commit/83de5b1aa65c58446e6cbb8c4924a98403b95e87))
* **terms:** register the term casing check as an engine rule ([#454](https://github.com/slopvac/slopvac/issues/454)) ([c841b0e](https://github.com/slopvac/slopvac/commit/c841b0e3ec5cd16af1d8adb1ba0e7cc8c22370f3))
* **terms:** require schema_version in blocklists and wire the conformance corpus ([#496](https://github.com/slopvac/slopvac/issues/496)) ([89f9b5c](https://github.com/slopvac/slopvac/commit/89f9b5c4f0d229a667b55c93f63bed7fd90dd5a7))
* **text:** port word counting, sentence splitting and text-type classifier ([74e83a2](https://github.com/slopvac/slopvac/commit/74e83a2ba86aef3157741d0e69cffa1a8419662a))
* **text:** wrap PCRE2 with the limits policy ([#434](https://github.com/slopvac/slopvac/issues/434)) ([841555c](https://github.com/slopvac/slopvac/commit/841555c7990cc63dde16d981352d08dc271e8b8c))
* **update:** add update notices and slopvac self update ([624b6ad](https://github.com/slopvac/slopvac/commit/624b6ad642abd55cd9c41e020f7d83d751b9601f))
* **update:** lock self update and trust a list of release keys ([#548](https://github.com/slopvac/slopvac/issues/548)) ([967ecd7](https://github.com/slopvac/slopvac/commit/967ecd710b1a7b775db720b3886a1122e5a88e8b))
* **update:** verify self update archives with the embedded release key ([#490](https://github.com/slopvac/slopvac/issues/490)) ([d0147cc](https://github.com/slopvac/slopvac/commit/d0147cc65b1a3776d536cceecb84c50b75ae7b30))


### Bug Fixes

* **action:** escape binary stderr before it reaches the job log ([#636](https://github.com/slopvac/slopvac/issues/636)) ([1d8410c](https://github.com/slopvac/slopvac/commit/1d8410ce7e79e2d12803e3d07565d0fb94dff23d))
* **action:** escape untrusted filenames in Action log output ([b0ba57a](https://github.com/slopvac/slopvac/commit/b0ba57a9bb76d8a465b3512132993f5c1644a1ef))
* **agents:** apply every [guidance] control in prime and setup ([#658](https://github.com/slopvac/slopvac/issues/658)) ([a3ac1a2](https://github.com/slopvac/slopvac/commit/a3ac1a26f88c8c5fb6774a027e51dd1af4e0435d))
* **agents:** check the target again right before the rename or delete ([#687](https://github.com/slopvac/slopvac/issues/687)) ([43eff99](https://github.com/slopvac/slopvac/commit/43eff995ae9afb3d3b34ff0617ed981a0d52ce52))
* **agents:** golden-path vetting fixes (config redaction, error sources, reviewer permissions, setup atomicity) ([#558](https://github.com/slopvac/slopvac/issues/558)) ([e5d13c0](https://github.com/slopvac/slopvac/commit/e5d13c0389188219c147f5721f4ffba7f7f26a8e))
* cap input size at every non-CLI entry point ([#533](https://github.com/slopvac/slopvac/issues/533)) ([9f8f4cf](https://github.com/slopvac/slopvac/commit/9f8f4cf00c61ece8e391bf3f92e8607a2f216a9f))
* **ci:** allow the AKS product name and two regex stems in typos ([ff1b883](https://github.com/slopvac/slopvac/commit/ff1b883b1c45a74a1e42d9783102aa6987cdbc70))
* **cli:** cap stdin and file lint reads at the document limit ([#568](https://github.com/slopvac/slopvac/issues/568)) ([f73282e](https://github.com/slopvac/slopvac/commit/f73282eb1a5b61859bfd727f24604bac7816b758))
* **cli:** carry budget data into lint JSON notices ([#664](https://github.com/slopvac/slopvac/issues/664)) ([8cc0c91](https://github.com/slopvac/slopvac/commit/8cc0c915f2d3284dbeea6bda4829cb8753372fa3))
* **cli:** match the placeholder array length to its entries ([b5d9c7a](https://github.com/slopvac/slopvac/commit/b5d9c7a01884214eb312092feccd04ae8b509c5a))
* **cli:** never ignore lint --fix, --diff-base or --explain-config ([#659](https://github.com/slopvac/slopvac/issues/659)) ([6924078](https://github.com/slopvac/slopvac/commit/692407826757e218e23c00bdb40914d901fbd96d))
* **cli:** normalize paths before redaction ([#623](https://github.com/slopvac/slopvac/issues/623)) ([397e154](https://github.com/slopvac/slopvac/commit/397e1541431ea914c53d99f8dcb3a8935aa38ba5))
* **config,rules:** bound aggregate extends and pack work ([#585](https://github.com/slopvac/slopvac/issues/585)) ([1c8e2da](https://github.com/slopvac/slopvac/commit/1c8e2da7c22376e01d530fc25f18798abb900615))
* **config:** match exclude and block patterns only under the project root ([#646](https://github.com/slopvac/slopvac/issues/646)) ([7bef808](https://github.com/slopvac/slopvac/commit/7bef808dc2e92567b4ba0c095f54ac43ce406768))
* **config:** show provenance outside the root as &lt;external&gt;/&lt;file name&gt; ([1702618](https://github.com/slopvac/slopvac/commit/1702618789c432d35c71b9c8e74a79792a48f2c0))
* **context:** cap genre file reads at the document size limit ([#686](https://github.com/slopvac/slopvac/issues/686)) ([a827c6c](https://github.com/slopvac/slopvac/commit/a827c6c283d3dc72e7384502de53573972da4824))
* **context:** index tag lookups so each takes logarithmic time ([#604](https://github.com/slopvac/slopvac/issues/604)) ([b2bead5](https://github.com/slopvac/slopvac/commit/b2bead5d6f86b9ef5aaea2d9343ca28d0d5b870d))
* **context:** scan negation tokens in linear time ([#678](https://github.com/slopvac/slopvac/issues/678)) ([1d6918d](https://github.com/slopvac/slopvac/commit/1d6918dec4a4f2b0f52b1cfe2eac302267336e9b))
* **context:** split blocks into sentences for sentence-scoped structural taggers ([34009ea](https://github.com/slopvac/slopvac/commit/34009ead15c8f447d3f230bef7898bdc07c669b5))
* **context:** tag sections and clean sentences in linear time ([#560](https://github.com/slopvac/slopvac/issues/560)) ([a8f61e6](https://github.com/slopvac/slopvac/commit/a8f61e6071ee757d93d441d371a319d83370e8b5))
* **context:** tag sentences, not whole blocks, for sentence-scoped taggers ([#688](https://github.com/slopvac/slopvac/issues/688)) ([34009ea](https://github.com/slopvac/slopvac/commit/34009ead15c8f447d3f230bef7898bdc07c669b5))
* **context:** tie-break, pattern cap, number checks, sanitized output, error sources ([#543](https://github.com/slopvac/slopvac/issues/543)) ([21071fa](https://github.com/slopvac/slopvac/commit/21071fad986675d89f69481a5329a276c1b06917))
* **contract:** anchor tagger id pattern at true end of string ([#530](https://github.com/slopvac/slopvac/issues/530)) ([1c6934d](https://github.com/slopvac/slopvac/commit/1c6934d12d6cbc5519e6c6fb0871924f55d95c31))
* **contract:** drop removed rules from the shipped legacy presets ([#679](https://github.com/slopvac/slopvac/issues/679)) ([9d74d70](https://github.com/slopvac/slopvac/commit/9d74d706041111b39129bff8579d1c880fe50682))
* **contract:** keep allow entries passing once their change lands ([#620](https://github.com/slopvac/slopvac/issues/620)) ([e247ef9](https://github.com/slopvac/slopvac/commit/e247ef9d12e6841cb5f8d2caa5a7cf333d636bb0))
* **contract:** match blocklist pos set between schema and loader ([#607](https://github.com/slopvac/slopvac/issues/607)) ([315ad5d](https://github.com/slopvac/slopvac/commit/315ad5d3d54d89d9008b753d64d043089ab8c203))
* **contract:** unique schema def names and document the code-comment tag ([#537](https://github.com/slopvac/slopvac/issues/537)) ([a72f3c3](https://github.com/slopvac/slopvac/commit/a72f3c3fda8b6a8fdf4602b4a3ad4e0e1a77d242))
* **contract:** use the portable end anchor in every schema pattern ([#652](https://github.com/slopvac/slopvac/issues/652)) ([d7c8767](https://github.com/slopvac/slopvac/commit/d7c87674a5195a062cf6a5be6832cb93c7f8e983))
* **diagrams:** analyse a shared paragraph once and report it once ([#660](https://github.com/slopvac/slopvac/issues/660)) ([77682ee](https://github.com/slopvac/slopvac/commit/77682ee9c22b6da07787e9692b18b6b4d63cb498))
* **diagrams:** count every &lt;br&gt; form and PlantUML \n as a line break ([#489](https://github.com/slopvac/slopvac/issues/489)) ([5e11e04](https://github.com/slopvac/slopvac/commit/5e11e0466b699dfc4bc092ef8d81479d477223cd))
* **diagrams:** decode draw.io matched text and tighten gloss rule ([96ff6b2](https://github.com/slopvac/slopvac/commit/96ff6b2ede574e7b53c6b537477fe4da2189922e))
* **diagrams:** report extraction failures and bound extraction memory ([#553](https://github.com/slopvac/slopvac/issues/553)) ([8544dc7](https://github.com/slopvac/slopvac/commit/8544dc7ea692f64521f0c6dfabb6ac6768dd2ac5))
* **diagrams:** strip container prefixes from fenced diagram bodies ([#446](https://github.com/slopvac/slopvac/issues/446)) ([9bcb457](https://github.com/slopvac/slopvac/commit/9bcb457cd3d1a63b4ebf236f3980411da6b7c94e))
* **doctor:** report the per-user directories plugins actually use ([#662](https://github.com/slopvac/slopvac/issues/662)) ([eba23ef](https://github.com/slopvac/slopvac/commit/eba23efee615efa3bcc5062a77e20880b4b819fe))
* **engine:** define incomplete runs; rules not run stay info ([#667](https://github.com/slopvac/slopvac/issues/667)) ([04786b2](https://github.com/slopvac/slopvac/commit/04786b2ee74076b0c174951e6feb794addf51d24))
* **engine:** list the diagram context in contexts_seen ([#689](https://github.com/slopvac/slopvac/issues/689)) ([a74301a](https://github.com/slopvac/slopvac/commit/a74301a489fc862ee01bf0c4de08191e39362a24))
* **engine:** make nearby diagram prose lookup linear ([#573](https://github.com/slopvac/slopvac/issues/573)) ([fe560ca](https://github.com/slopvac/slopvac/commit/fe560cab43c9355473bbff1ff47a69a1186bb5a4))
* **engine:** match 2.x sentence and paragraph counting ([#511](https://github.com/slopvac/slopvac/issues/511)) ([9d86b57](https://github.com/slopvac/slopvac/commit/9d86b57ed9f595dbbcbd4227cc6387eedcd327d7))
* **engine:** render non-string front matter scalars for taggers ([#619](https://github.com/slopvac/slopvac/issues/619)) ([4eefa63](https://github.com/slopvac/slopvac/commit/4eefa63ad8f4f3201f9c1e3a3c5ca87b6ea93954))
* **evals:** address golden-path vetting findings ([#564](https://github.com/slopvac/slopvac/issues/564)) ([37c9fe4](https://github.com/slopvac/slopvac/commit/37c9fe43f05e1b6137b81959d28ba5f97f8e8d7a))
* **evals:** explain missing labels only for precision failures ([#596](https://github.com/slopvac/slopvac/issues/596)) ([7159605](https://github.com/slopvac/slopvac/commit/7159605a1cc617e29f0ea5b5995fe431b890ea5f))
* **evals:** record corpus licence and dates at the content revision ([#562](https://github.com/slopvac/slopvac/issues/562)) ([43b4e50](https://github.com/slopvac/slopvac/commit/43b4e50f69869c651bbb4693327e0a6626033042))
* **evals:** score reviewer diagnosis, relabel lexical retention, redact provider stderr ([#542](https://github.com/slopvac/slopvac/issues/542)) ([40e1782](https://github.com/slopvac/slopvac/commit/40e17826cbe4232c9f5b8ad73cd8ab31f7617da0))
* **evals:** verify judge provenance and require the spot-check before export ([#586](https://github.com/slopvac/slopvac/issues/586)) ([1350916](https://github.com/slopvac/slopvac/commit/13509167e1b46da977877f313314c017c1129adb))
* **fs:** read capped inputs as regular files so a FIFO cannot hang a run ([#605](https://github.com/slopvac/slopvac/issues/605)) ([1c3e2e4](https://github.com/slopvac/slopvac/commit/1c3e2e43424d66ccd8035e9827aed7dbbf9dcc1e))
* **lint:** escape file names in read refusal messages ([#690](https://github.com/slopvac/slopvac/issues/690)) ([501b719](https://github.com/slopvac/slopvac/commit/501b719aec8b6c1dafc2772b874809cbfa85d1e0))
* **lsp:** keep parser text out of invalid-params and io errors ([#671](https://github.com/slopvac/slopvac/issues/671)) ([32c5d9f](https://github.com/slopvac/slopvac/commit/32c5d9f5c9848d27a0e8afc4f95e9dfda54e059e))
* **messages:** leave text ids off the error-code reference page ([#661](https://github.com/slopvac/slopvac/issues/661)) ([f6e06fe](https://github.com/slopvac/slopvac/commit/f6e06fe8b70d27cb497bebbaf80309a183cebbc7))
* **migrate:** keep comments on table collapse and cover inline overrides and the repo config ([d63b12e](https://github.com/slopvac/slopvac/commit/d63b12e86f10eeb8b2ac96fd68edcd15628ef819))
* **migrate:** rewrite vocabulary.path blocklists to the 3.0 format ([#634](https://github.com/slopvac/slopvac/issues/634)) ([c782eeb](https://github.com/slopvac/slopvac/commit/c782eeb3ee49db84626a7e584eee5cf74c03891a))
* **migrate:** sanitize output, cap reads, fail on bad input, use engine file kinds ([#547](https://github.com/slopvac/slopvac/issues/547)) ([9784eba](https://github.com/slopvac/slopvac/commit/9784ebaa1e7fcccb565fec6e4252a7f3f522a94b))
* **migrate:** store each key path piece once in the config provenance map ([#665](https://github.com/slopvac/slopvac/issues/665)) ([8e3b552](https://github.com/slopvac/slopvac/commit/8e3b5522309987f1b8fc23ad159d6e2fb82410ef))
* **migrate:** write through write_atomic and restore only what the migration wrote ([#566](https://github.com/slopvac/slopvac/issues/566)) ([0c441ce](https://github.com/slopvac/slopvac/commit/0c441ced31653051e23adbe6b0c6e028f35aab46))
* **plugins:** bind a stopped stray's children from the same table read ([#651](https://github.com/slopvac/slopvac/issues/651)) ([16c5b7a](https://github.com/slopvac/slopvac/commit/16c5b7a003f9d1bc883bc773b4ed627f082d97a7))
* **plugins:** bound raw bytes and trailers in the OCI transport ([#518](https://github.com/slopvac/slopvac/issues/518)) ([82aba3c](https://github.com/slopvac/slopvac/commit/82aba3c05f0da84f5f0c2f333d5d210f01cacd44))
* **plugins:** credential lookup follow-ups from [#572](https://github.com/slopvac/slopvac/issues/572) ([#630](https://github.com/slopvac/slopvac/issues/630)) ([ba46b74](https://github.com/slopvac/slopvac/commit/ba46b74d3391bfb5ef8f22a15e971ab7959cc93a))
* **plugins:** deflake host teardown and late-charge drain tests ([#591](https://github.com/slopvac/slopvac/issues/591)) ([b345411](https://github.com/slopvac/slopvac/commit/b3454117b3c1527687ba0542994fe3e768243577))
* **plugins:** fail closed when the launcher entry point is not installed ([#555](https://github.com/slopvac/slopvac/issues/555)) ([f268afe](https://github.com/slopvac/slopvac/commit/f268afe60a63147f6924069916be4cfec8fccac8))
* **plugins:** find OCI credential helpers only in trusted PATH directories ([#572](https://github.com/slopvac/slopvac/issues/572)) ([c709368](https://github.com/slopvac/slopvac/commit/c709368b76f8fe08c17438d18408308c7ad2c4b5))
* **plugins:** match OCI credentials case-insensitively on the registry host ([#487](https://github.com/slopvac/slopvac/issues/487)) ([7411222](https://github.com/slopvac/slopvac/commit/741122234de3c43482501e62d99df40b58ace910))
* **plugins:** refuse .slopvac/ and slopvac config files at any depth in apply plans ([#704](https://github.com/slopvac/slopvac/issues/704)) ([029ce53](https://github.com/slopvac/slopvac/commit/029ce53ee66f809db91b2d3157ea8207f59ba600))
* **plugins:** reserve core, map plugin error codes by number, name the offline refusal ([#628](https://github.com/slopvac/slopvac/issues/628)) ([3f76a77](https://github.com/slopvac/slopvac/commit/3f76a7761504e9ac3187e5c79dbe0d90c9214282))
* **plugins:** validate fixer edits and recipe paths as positions.md says ([795befa](https://github.com/slopvac/slopvac/commit/795befa082623e951671ef23b3e845a55a77d1e8))
* reject a trailing newline in Python copies of schema patterns ([#702](https://github.com/slopvac/slopvac/issues/702)) ([c042f8a](https://github.com/slopvac/slopvac/commit/c042f8a600741e137402e265b4a4cc99a746f21a))
* **release:** bump every workspace crate in Cargo.lock ([7958838](https://github.com/slopvac/slopvac/commit/7958838d9a1f738cee84f0d7ad2d6a7ee470de9e))
* **release:** bump slopvac-agents in Cargo.lock ([2d7d464](https://github.com/slopvac/slopvac/commit/2d7d464d58d6c822606e1430983d541ae0122a26))
* **release:** bump slopvac-context in Cargo.lock ([fd016f7](https://github.com/slopvac/slopvac/commit/fd016f701cb8c4db7576bd64785e310a1190ccc4))
* **release:** bump slopvac-terms in Cargo.lock ([6dd5290](https://github.com/slopvac/slopvac/commit/6dd52909bafddbdb3c1422a258dafa4517cb7b94))
* **release:** publish GitHub releases from a job that runs no build output ([#705](https://github.com/slopvac/slopvac/issues/705)) ([45d6d6e](https://github.com/slopvac/slopvac/commit/45d6d6efc336b5a9b5321c65c14465b53e17058e))
* **release:** re-pin the release tag ruleset after adding plugin-* tags ([#639](https://github.com/slopvac/slopvac/issues/639)) ([cca0839](https://github.com/slopvac/slopvac/commit/cca0839f4e999f1f0da5ffaf2a44eea1391b1fb4))
* **release:** recognise the real oras not-found as an absent revocation manifest ([#611](https://github.com/slopvac/slopvac/issues/611)) ([bf538e4](https://github.com/slopvac/slopvac/commit/bf538e43b2e8475f9afa8bdcc314842d30a93b81))
* **release:** reject leading zeros in version tags and pin the candidate ancestry branch ([615bf90](https://github.com/slopvac/slopvac/commit/615bf907fb3988e0e158423485854abc17a4d674))
* **release:** report a missing cargo-nextest as an incomplete gate ([4374c4f](https://github.com/slopvac/slopvac/commit/4374c4f633fbd3e6487bc149910a0b9945b5e98d))
* **report:** escape GitHub annotation output through slopvac-sanitize ([#657](https://github.com/slopvac/slopvac/issues/657)) ([990dcd9](https://github.com/slopvac/slopvac/commit/990dcd9d8402277c462d8ee0c3b8e55164540243))
* **report:** refuse --body-file - and show the form labels ([#531](https://github.com/slopvac/slopvac/issues/531)) ([377093c](https://github.com/slopvac/slopvac/commit/377093c3efbf7e7289fb8d9c1c908ac753a27e20))
* **report:** sanitize terminal controls in text output ([#622](https://github.com/slopvac/slopvac/issues/622)) ([e891f4a](https://github.com/slopvac/slopvac/commit/e891f4a3ee329d4bcc58b09f1d24d90de67f8677))
* **rules,config:** linear duplicate checks and per-list entry limits ([#642](https://github.com/slopvac/slopvac/issues/642)) ([cb9c68b](https://github.com/slopvac/slopvac/commit/cb9c68b23970442da3df4ddbbb062b29f1165d4d))
* **rules:** cap authored patterns at 8,192 bytes ([#669](https://github.com/slopvac/slopvac/issues/669)) ([001cce8](https://github.com/slopvac/slopvac/commit/001cce85ba002d6cb8fc2e6c6dd9dcf4d5517941))
* **rules:** limit 'no longer' to change verbs and add a versioned-change-note exception ([aaa63ef](https://github.com/slopvac/slopvac/commit/aaa63ef0357cca0cc5be2ba4283904bf842df9dd))
* **rules:** limit negative-inventory-core to inventory form ([81849b3](https://github.com/slopvac/slopvac/commit/81849b3d070a109fa75bb5ede20c3dc3f05045ce))
* **rules:** make rule patterns PCRE2-compatible ([a4a3518](https://github.com/slopvac/slopvac/commit/a4a3518bf14f3397113012dce4db7e586c36deb5))
* **rules:** skip acronyms, CamelCase and allowed terms in title-case-heading ([d705dcb](https://github.com/slopvac/slopvac/commit/d705dcb87fb839843537d8010a260e6d35094363))
* **rules:** split the appositive contrastive form out of contrastive-inversion-frames ([c025f3a](https://github.com/slopvac/slopvac/commit/c025f3a18354c2b4bd8fd4cba35a5f46ea338295))
* **rules:** stop condition-after-command firing on headings, cells and descriptions ([6b9b02d](https://github.com/slopvac/slopvac/commit/6b9b02d1a1aa0ee2c04946575fb5a26972d8cbc1)), closes [#254](https://github.com/slopvac/slopvac/issues/254)
* **schemas:** drop stale blocklist pos allow entries ([#614](https://github.com/slopvac/slopvac/issues/614)) ([cae366a](https://github.com/slopvac/slopvac/commit/cae366addb7c1b476092c6a48c4ee6c7aa5c5aba))
* **sdk:** reject a trailing newline in schema-copied patterns ([c042f8a](https://github.com/slopvac/slopvac/commit/c042f8a600741e137402e265b4a4cc99a746f21a))
* **text:** linear sentence splitting on repetitive input ([#467](https://github.com/slopvac/slopvac/issues/467)) ([f66cb60](https://github.com/slopvac/slopvac/commit/f66cb60100186e75063ac3581317d6034547a31f))
* **update:** bounded regular-file reads and durable atomic writes ([#706](https://github.com/slopvac/slopvac/issues/706)) ([14f99f7](https://github.com/slopvac/slopvac/commit/14f99f79a8c35ff4eacf1b3f50457e328031d345))
* **update:** list supported schema and extension-API versions in --version --json ([#645](https://github.com/slopvac/slopvac/issues/645)) ([9ffb872](https://github.com/slopvac/slopvac/commit/9ffb87259da73d473b8535e5d57e0f79e6d4aed6))
* **update:** stop naming the unpublished slopvac crate in the cargo upgrade hint ([#635](https://github.com/slopvac/slopvac/issues/635)) ([3a33743](https://github.com/slopvac/slopvac/commit/3a337431a4b5bf63fb46a017b95c74949b2f2d7c))


### Performance

* **engine:** tag documents in linear time ([#601](https://github.com/slopvac/slopvac/issues/601)) ([97b7d28](https://github.com/slopvac/slopvac/commit/97b7d28670f067aa5da5b059eeb6b7c5b69c3d4c))
* wire real CLI scenarios and record binary budgets ([88fb973](https://github.com/slopvac/slopvac/commit/88fb973740c3f37b8429d41ad06a00ccc66fdb21))


### Refactors

* **agents:** use slopvac-text for claims sentences and tokens ([988e3d4](https://github.com/slopvac/slopvac/commit/988e3d45b275d3f05fef58c992c08644ecd5b7d0))
* **config:** move codes and diagnostic text onto the message registry ([#626](https://github.com/slopvac/slopvac/issues/626)) ([1d4f39b](https://github.com/slopvac/slopvac/commit/1d4f39bb08ef48e58d4f79c20f9f6beed1da0251))
* **config:** read front matter with frontmatter-spans ([#443](https://github.com/slopvac/slopvac/issues/443)) ([f413b23](https://github.com/slopvac/slopvac/commit/f413b23080025359d4c11e920ee164d59833c7c5))
* **config:** read presets from the core pack ([#694](https://github.com/slopvac/slopvac/issues/694)) ([6ad4358](https://github.com/slopvac/slopvac/commit/6ad43582bbcfd47f23e1a7d4976a663b79262bda))
* **config:** use slopvac-model ConfigSource and ConfigLayer ([#682](https://github.com/slopvac/slopvac/issues/682)) ([640bace](https://github.com/slopvac/slopvac/commit/640bacea126e20cfa14b0e7c039b1b208383eb8e))
* **engine:** make Input non_exhaustive with constructors ([#499](https://github.com/slopvac/slopvac/issues/499)) ([f92d5b1](https://github.com/slopvac/slopvac/commit/f92d5b1d07abc4a05120521a9c8f2819cf02754b))
* **engine:** register engine and model messages ([#695](https://github.com/slopvac/slopvac/issues/695)) ([6cc86c2](https://github.com/slopvac/slopvac/commit/6cc86c2cd1fced85231dbb0390fbaf13a0ac65b1))
* **migrate:** move codes and text onto the message registry ([#681](https://github.com/slopvac/slopvac/issues/681)) ([a10afa9](https://github.com/slopvac/slopvac/commit/a10afa9ae9e43dea2aac6bc3959578e2d79fabbe))
* **model:** origin error non_exhaustive, Result alias, rstest limits (slopvac-8l4.20.16) ([#554](https://github.com/slopvac/slopvac/issues/554)) ([8d9226f](https://github.com/slopvac/slopvac/commit/8d9226f5d80e21c665e033bfd9c1e1ef8faa4a31))
* **rules:** read the v3 rule schema from schemas/v3 ([#403](https://github.com/slopvac/slopvac/issues/403)) ([57b44dc](https://github.com/slopvac/slopvac/commit/57b44dc86e379c8b69a2623ef6b7cab7c6887c00))
* **update:** build the release download hint from RELEASES_URL ([#644](https://github.com/slopvac/slopvac/issues/644)) ([e251ca3](https://github.com/slopvac/slopvac/commit/e251ca30618e3f37ec19c08f2775e5e61f929428))
* **update:** move codes and update text onto the message registry ([#637](https://github.com/slopvac/slopvac/issues/637)) ([4d40f33](https://github.com/slopvac/slopvac/commit/4d40f33b2c4e1c848c3c3f5d64287524f24880ed))


### Documentation

* **action:** pin the Action to a commit SHA instead of a floating v3 tag ([#668](https://github.com/slopvac/slopvac/issues/668)) ([bc4d77a](https://github.com/slopvac/slopvac/commit/bc4d77a52eec42c804dd5a27ad101ef5ab64992e))
* add engineering standards ([#507](https://github.com/slopvac/slopvac/issues/507)) ([dfea7e7](https://github.com/slopvac/slopvac/commit/dfea7e7b75cb4b12f67b3bea5af35ba112bc4b0d))
* add the CLA and sign it through CLA Assistant ([#484](https://github.com/slopvac/slopvac/issues/484)) ([2c2bc4f](https://github.com/slopvac/slopvac/commit/2c2bc4f115e7df5759d88770209390d863812149))
* **adr:** record the slopvac 3.0 architecture ([4a47880](https://github.com/slopvac/slopvac/commit/4a47880b53b48010b6008e70967bf81537d4616a))
* **contract:** add binary hosts section to positions contract (slopvac-8l4.2.28) ([#509](https://github.com/slopvac/slopvac/issues/509)) ([6062e07](https://github.com/slopvac/slopvac/commit/6062e07b45f5b65f749427326085fe3ae7ff6d59))
* **contract:** add network, accessibility and API lifecycle policies ([e402ca8](https://github.com/slopvac/slopvac/commit/e402ca8a0c155c5529413e12b0acc0c91ce0d449))
* **contract:** add the 2.x compatibility matrix ([efec42c](https://github.com/slopvac/slopvac/commit/efec42c21a3738beadb04bc502b7b82843a4f3a9))
* **contract:** add the plugin, trust and OCI threat model ([54504db](https://github.com/slopvac/slopvac/commit/54504db193c213e8ee5dfce0fe943e159bf69930))
* **contract:** audit, engine and migration rulings ([#698](https://github.com/slopvac/slopvac/issues/698)) ([1717b45](https://github.com/slopvac/slopvac/commit/1717b4560710dc8b902ff0c3bdf5e9aead5a2123))
* **contract:** define the position contract and test vectors ([46dff06](https://github.com/slopvac/slopvac/commit/46dff0680eeb62a381cc7a9d0e064a2d9be54af9))
* **contract:** document the plugin audit choices ([#700](https://github.com/slopvac/slopvac/issues/700)) ([e572b60](https://github.com/slopvac/slopvac/commit/e572b60d855c2dc908c1d31e613f42f173f6c32a))
* **contract:** list YAML blocklists in packs and the blocklist schema ([7f2ce11](https://github.com/slopvac/slopvac/commit/7f2ce11268b815f01bb305286f2d3687957394c8))
* **contract:** mark native Windows out of scope for 3.0 in the threat model ([#447](https://github.com/slopvac/slopvac/issues/447)) ([da56438](https://github.com/slopvac/slopvac/commit/da56438bf683a4be55435bdafdcfbccd938ab83d))
* **contract:** specify plugin protocol v1 ([f292c6f](https://github.com/slopvac/slopvac/commit/f292c6f9976b873275184a67d9188cbe5f3980a0))
* **contract:** state only the Unix process-group kill for plugins ([#544](https://github.com/slopvac/slopvac/issues/544)) ([596abf1](https://github.com/slopvac/slopvac/commit/596abf1d6eb88c11beded1b076700e3090e50fef))
* **contract:** threat-model rows and limits for binary containers (slopvac-8l4.2.30) ([#535](https://github.com/slopvac/slopvac/issues/535)) ([eda2d15](https://github.com/slopvac/slopvac/commit/eda2d15721fa7161e6fe44b702f044cbfe7c67c7))
* **design:** add the slopvac 3.0 plan ([#261](https://github.com/slopvac/slopvac/issues/261)) ([e112ccc](https://github.com/slopvac/slopvac/commit/e112ccc01047e87b8028e15dbecd28b3c6c7f4d3))
* **design:** binary container inputs design and ADR decision 27 (slopvac-8l4.2.31) ([#508](https://github.com/slopvac/slopvac/issues/508)) ([88d35c5](https://github.com/slopvac/slopvac/commit/88d35c558aaf6f78b6c02a9acc9a4b04a9ea8456))
* draft the 3.0 README ([4b36f9a](https://github.com/slopvac/slopvac/commit/4b36f9a8875fee30bedc9536f3a98b76a964f839))
* **engineering:** record the single-maintainer plugins-signing departure ([#640](https://github.com/slopvac/slopvac/issues/640)) ([5870ebb](https://github.com/slopvac/slopvac/commit/5870ebbf1d652c98b098d74f4bfc1fe9bb73a850))
* generate CLI and config reference pages ([#488](https://github.com/slopvac/slopvac/issues/488)) ([1baf59c](https://github.com/slopvac/slopvac/commit/1baf59cccb4e4b441be1e82c67ece4180484efb2))
* generate genre reference pages from the registry ([ec96e81](https://github.com/slopvac/slopvac/commit/ec96e817a24c4ef4664499cd4ad7c122b795b8b5))
* **migrate:** render the migration guide and prime migrate from one source ([06a6f7b](https://github.com/slopvac/slopvac/commit/06a6f7b4d4a7fd37211276f8b659082d6e26acb9))
* point links at the slopvac org ([#482](https://github.com/slopvac/slopvac/issues/482)) ([9e2dfe3](https://github.com/slopvac/slopvac/commit/9e2dfe3594a2abe63d32a4afc546036b4a0b0487))
* record approved departures in engineering standards ([#527](https://github.com/slopvac/slopvac/issues/527)) ([515d3d7](https://github.com/slopvac/slopvac/commit/515d3d7e392b66d12f0536e42a7c70bb6d9e6d2e))
* record release freshness and descriptor-test limits ([#536](https://github.com/slopvac/slopvac/issues/536)) ([92ca365](https://github.com/slopvac/slopvac/commit/92ca365f774d954cc567d74802c7daa0235d8101))
* **site:** generate plugin protocol, pack manifest and pack pages ([#466](https://github.com/slopvac/slopvac/issues/466)) ([b970782](https://github.com/slopvac/slopvac/commit/b970782f2056d4f1d96d66d7a5655f987e2b96a5))


### CI/CD

* **release:** publish 3.x wheels from publish-pypi.yml ([#559](https://github.com/slopvac/slopvac/issues/559)) ([3239608](https://github.com/slopvac/slopvac/commit/323960811ee937ad1110c987dd68011d6f2d7316))

## [2.18.1](https://github.com/srobroek/slopvac/compare/v2.18.0...v2.18.1) (2026-10-23)


### Bug Fixes

* **release:** start stable publishing by hand for approval ([#242](https://github.com/srobroek/slopvac/issues/242)) ([0910e91](https://github.com/srobroek/slopvac/commit/0910e9106b867df943ee5894e4d47d8c65b1b924))
* **reporter:** close report workflow gaps ([#248](https://github.com/srobroek/slopvac/issues/248)) ([bb1fa48](https://github.com/srobroek/slopvac/commit/bb1fa48d0f33b5de47b89e76f053c62fec4e932a))
* **rules:** read a plural object before a preposition as an object ([#249](https://github.com/srobroek/slopvac/issues/249)) ([0fdc5a6](https://github.com/srobroek/slopvac/commit/0fdc5a6da02fe3b4704117afcd7089caea1c5375))


### Documentation

* **rules:** state how the omitted-that verb list was labelled ([#250](https://github.com/srobroek/slopvac/issues/250)) ([ed374ed](https://github.com/srobroek/slopvac/commit/ed374edd051f3795bcda014c74c60000279a2768))

## [2.18.0](https://github.com/srobroek/slopvac/compare/v2.16.2...v2.18.0) (2026-10-22)


### Features

* **lint:** read a document from stdin with --stdin and --language ([7767aa9](https://github.com/srobroek/slopvac/commit/7767aa93ab1de3f1d95a001fe279d03b30737519))
* **release:** build release candidates from the release PR ([7c2a06e](https://github.com/srobroek/slopvac/commit/7c2a06e10ed17bc7a40c1e1efdbae70426923f29))
* structured problem reporting with issue forms, prime report, and doctor JSON ([97da777](https://github.com/srobroek/slopvac/commit/97da7777cf0316f8efdc77947bbba6fb81889534))


### Bug Fixes

* **reporting:** keep paths and private data out of reports and require agent disclosure ([2f8d28e](https://github.com/srobroek/slopvac/commit/2f8d28e0dd6bb86f023cf1be8c040f85ce3a8471))
* **rules:** keep HTML comments out of em-dash density ([#240](https://github.com/srobroek/slopvac/issues/240)) ([231f5de](https://github.com/srobroek/slopvac/commit/231f5de578ab839cf9a3e45bed88ce2f45725d81))
* **rules:** only flag an omitted "that" when a clause follows ([#241](https://github.com/srobroek/slopvac/issues/241)) ([8f80d97](https://github.com/srobroek/slopvac/commit/8f80d97468edb4bd5b36c3b7530d3bd822f047ef))
* **rules:** stop status-language flagging the imperative verb draft ([#239](https://github.com/srobroek/slopvac/issues/239)) ([ddf3ba2](https://github.com/srobroek/slopvac/commit/ddf3ba2b2207aef073102b8ee326d7c5de1a1236))


### Chores

* release 2.18.0 ([bd665c5](https://github.com/srobroek/slopvac/commit/bd665c5d27fce87babbad580f2300e6a3da58270))

## [2.16.2](https://github.com/srobroek/slopvac/compare/v2.16.1...v2.16.2) (2026-10-21)


### Bug Fixes

* **rules:** leave modal and passive guarantees to contextual review ([ea5e690](https://github.com/srobroek/slopvac/commit/ea5e690697f370f5a26e18d716b63145a7768e03))

## [2.16.1](https://github.com/srobroek/slopvac/compare/v2.17.0...v2.16.1) (2026-10-20)

### Version selection and installation

This release intentionally uses 2.16.1 and includes all changes documented in 2.17.0, plus the fixes and dependency updates below. Existing 2.17.0 tags and artifacts are preserved and are not yanked.

Because 2.16.1 sorts below 2.17.0, an ordinary upgrade does not downgrade an installed 2.17.0. Install explicitly with `python -m pip install --upgrade "slopvac==2.16.1"` or `uv tool install --force slopvac==2.16.1`. Update project pins and lockfiles as needed. For one-off runs use `uvx --from slopvac==2.16.1 slopvac --version`.

Unpinned package resolution and Slopvac's update notifier can still select or advertise the unyanked 2.17.0. Keep the explicit 2.16.1 pin to use these corrections. This release does not change version ordering or promise automatic downgrades.

### Dependency updates

Includes typos 1.51.1, cargo-binstall 1.26.0, Trivy 0.76.0, TruffleHog 3.99.3, download-artifact 8.0.2, upload-artifact 7.0.2, CodeQL 4.39.0, setup-uv 10.3.0, OSV scanner 2.7.0, uv 0.13.4 ([#225](https://github.com/srobroek/slopvac/pull/225)), and the PyPI publishing action 1.14.3 ([#226](https://github.com/srobroek/slopvac/pull/226)). The publishing action update includes an upstream security fix. Python 3.15 remains a separate compatibility change; the tested Python 3.11–3.14 support remains unchanged.

### Bug Fixes

* require supported Vale for complete linting ([#217](https://github.com/srobroek/slopvac/issues/217)) ([591c1e0](https://github.com/srobroek/slopvac/commit/591c1e07a95eeb5c24095623d809582a40881ca3))
* secure ruleset cache and address outstanding reviews ([#218](https://github.com/srobroek/slopvac/issues/218)) ([fb1cfd8](https://github.com/srobroek/slopvac/commit/fb1cfd82b11d2734037e8be110560ebbcd4e0e86))
* stabilize cache identities and profiler warmup ([#222](https://github.com/srobroek/slopvac/issues/222)) ([9c9e7a2](https://github.com/srobroek/slopvac/commit/9c9e7a2f2fe10c2762e1acc0dcf2f955e6448df5))


### Documentation

* clean up reviewed guidance and finding dispositions ([#223](https://github.com/srobroek/slopvac/issues/223)) ([8f26ccb](https://github.com/srobroek/slopvac/commit/8f26ccb57d1642fd9bf0b09a1253d0640f5fc98d))


### Chores

* **deps:** roll up compatible Renovate updates ([#224](https://github.com/srobroek/slopvac/issues/224)) ([c930676](https://github.com/srobroek/slopvac/commit/c9306760ca0aa85ae66b0558fd064669b6aefad0))

### Changes included from 2.17.0

#### Features

* **rules:** `ai-tells-structure.negative-guarantee-core` accepts subjects of up to seven words. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** `ai-tells-structure.negative-guarantee-core` flags "X will never " and "X can never "; "must/should/shall never" stay exempt. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** `ai-tells-structure.negative-guarantee-core` flags the passive "X is/are never " and "X will/can never be ". ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend ai-tells-structure, ai-tells-register, ai-tells-formatting and ai-tells-content-shape for `reference`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend orwell for `reference` and `change-comms`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend prose-discipline for `change-comms`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend prose-scope for `reference` and `internal`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend the STE categories (descriptive, nouns, practices, punctuation, safety, sentences, verbs, words) for `consumer`, `internal` and `change-comms`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))


#### Bug Fixes

* **engine:** report a match inside a table cell at that cell's line, not the table's first row. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **rules:** `ai-tells-structure.negative-guarantee-core` treats "go" as a state verb, so "can never go below zero" stays clean. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))


#### Performance

* **analyze:** tokenize each sentence once for its word count and text type. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **engine:** compile each rule pattern once per process and share it across files and engines. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **projection:** bisect the segment index in submap and in the block start lookup. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **rules:** reuse the proved locale spelling rule across runs. ([a824f07](https://github.com/srobroek/slopvac/commit/a824f07906c94c5856b510d8312731bc5f6d583c))
* **vale:** validate compiled rules in one Vale run instead of one run per rule; a cold README lint with Vale drops from 3.0 s to 0.9 s of CPU. ([a824f07](https://github.com/srobroek/slopvac/commit/a824f07906c94c5856b510d8312731bc5f6d583c))


#### Documentation

* state what `slopvac setup` and the prime topics do, not what they never do. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))


## [2.17.0](https://github.com/srobroek/slopvac/compare/v2.16.0...v2.17.0) (2026-10-20)


### Features

* **rules:** `ai-tells-structure.negative-guarantee-core` accepts subjects of up to seven words. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** `ai-tells-structure.negative-guarantee-core` flags "X will never &lt;verb&gt;" and "X can never &lt;verb&gt;"; "must/should/shall never" stay exempt. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** `ai-tells-structure.negative-guarantee-core` flags the passive "X is/are never &lt;participle&gt;" and "X will/can never be &lt;participle&gt;". ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend ai-tells-structure, ai-tells-register, ai-tells-formatting and ai-tells-content-shape for `reference`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend orwell for `reference` and `change-comms`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend prose-discipline for `change-comms`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend prose-scope for `reference` and `internal`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))
* **rules:** recommend the STE categories (descriptive, nouns, practices, punctuation, safety, sentences, verbs, words) for `consumer`, `internal` and `change-comms`. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))


### Bug Fixes

* **engine:** report a match inside a table cell at that cell's line, not the table's first row. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **rules:** `ai-tells-structure.negative-guarantee-core` treats "go" as a state verb, so "can never go below zero" stays clean. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))


### Performance

* **analyze:** tokenize each sentence once for its word count and text type. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **engine:** compile each rule pattern once per process and share it across files and engines. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **projection:** bisect the segment index in submap and in the block start lookup. ([2b0970e](https://github.com/srobroek/slopvac/commit/2b0970e8dfb69fb364388d326751af4f19d77338))
* **rules:** reuse the proved locale spelling rule across runs. ([a824f07](https://github.com/srobroek/slopvac/commit/a824f07906c94c5856b510d8312731bc5f6d583c))
* **vale:** validate compiled rules in one Vale run instead of one run per rule; a cold README lint with Vale drops from 3.0 s to 0.9 s of CPU. ([a824f07](https://github.com/srobroek/slopvac/commit/a824f07906c94c5856b510d8312731bc5f6d583c))


### Documentation

* state what `slopvac setup` and the prime topics do, not what they never do. ([37b8203](https://github.com/srobroek/slopvac/commit/37b82033ba9bf9da765ef63a200439c9342c1fab))

## [2.16.0](https://github.com/srobroek/slopvac/compare/v2.15.0...v2.16.0) (2026-10-20)


### Features

* **rules:** `negative-guarantee-core` skips instructions ("Never edit …"), MUST NOT/NEVER, "must/will never" and past tense, and accepts the exceptions `quotation`, `normative-keyword` and `enforced-invariant`. ([f6ac399](https://github.com/srobroek/slopvac/commit/f6ac399ff9eaf7b3e1785594197097bb70d814d8))
* **rules:** add the judgement rule `prose-discipline.negative-guarantee-remainder` (enforced at strict, advisory at normal; recommended for consumer, reference and internal), which asks whether a "never" guarantee names what stops the action, is stacked, or lists side effects that do not happen. ([f6ac399](https://github.com/srobroek/slopvac/commit/f6ac399ff9eaf7b3e1785594197097bb70d814d8))
* **rules:** add the pattern rule `ai-tells-structure.negative-guarantee-core` (warning, on at strict and normal) for components described by what they never do ("X never Y", "X itself never Y", "X runs no Z"). ([f6ac399](https://github.com/srobroek/slopvac/commit/f6ac399ff9eaf7b3e1785594197097bb70d814d8))


### Bug Fixes

* **dev:** run py-spy from the profile group, not the scratch venv ([#205](https://github.com/srobroek/slopvac/issues/205)) ([beaf593](https://github.com/srobroek/slopvac/commit/beaf5932e54fd6801f70d5100640a8721b4294a7))
* **rules:** narrow `ai-tells-structure.absolute-assertion-remainder` so a component's behavioural "never" guarantee goes to `negative-guarantee-remainder` instead of being preserved. ([f6ac399](https://github.com/srobroek/slopvac/commit/f6ac399ff9eaf7b3e1785594197097bb70d814d8))


### Performance

* **analyze:** build the offset and line-start tables once per document instead of once per block; linting the 17,844-word generated rules reference drops from 89 s to 4.5 s and its peak memory from 513 to 145 MiB. ([f928a46](https://github.com/srobroek/slopvac/commit/f928a460223446a6e8221c3a389ead1b4908f5b3))
* **analyze:** build the offset tables once for HTML blocks and lines too. ([f928a46](https://github.com/srobroek/slopvac/commit/f928a460223446a6e8221c3a389ead1b4908f5b3))
* **analyze:** compile the text-classifier regexes on first use. ([f928a46](https://github.com/srobroek/slopvac/commit/f928a460223446a6e8221c3a389ead1b4908f5b3))
* **cli:** load only the modules each command needs, so `slopvac --version` takes 78 ms instead of 429 ms. ([d5b1d52](https://github.com/srobroek/slopvac/commit/d5b1d52b3d07c2b98a4fe6563f22e2e918ff70ac))
* **cli:** read the PyPI update notice from cache only and refresh a stale cache in a detached process, so no command waits on the network. ([d5b1d52](https://github.com/srobroek/slopvac/commit/d5b1d52b3d07c2b98a4fe6563f22e2e918ff70ac))
* **rules:** cache the verified ruleset load under the cache root, keyed by package version, loader source and every rule file's text; a lint of a small file drops from 1458 ms to 575 ms and `rules`/`explain` from about 1.3 s to about 0.4 s. ([7e19bc3](https://github.com/srobroek/slopvac/commit/7e19bc31821eb7cc8306df3dce547f8b932d5f71))
* **rules:** parse rule YAML and write Vale rule YAML with PyYAML's bundled libyaml binding, re-parsing with the pure-Python loader on error so messages are unchanged. ([7e19bc3](https://github.com/srobroek/slopvac/commit/7e19bc31821eb7cc8306df3dce547f8b932d5f71))
* **rules:** prove shipped rule examples in tests and user rules once per cache build instead of on every run. ([7e19bc3](https://github.com/srobroek/slopvac/commit/7e19bc31821eb7cc8306df3dce547f8b932d5f71))
* **vale:** ask `vale --version` once per binary per process. ([7e19bc3](https://github.com/srobroek/slopvac/commit/7e19bc31821eb7cc8306df3dce547f8b932d5f71))


### Refactors

* move the plain enums to `slopvac.enums`, and the exit codes, `LINTABLE` and `SKIP_SOURCE_DIRS` to `slopvac.contract`; the old import paths still work. ([d5b1d52](https://github.com/srobroek/slopvac/commit/d5b1d52b3d07c2b98a4fe6563f22e2e918ff70ac))


### Documentation

* **changelog:** list every change and rule in 2.12.0 and 2.15.0 ([#208](https://github.com/srobroek/slopvac/issues/208)) ([eec974f](https://github.com/srobroek/slopvac/commit/eec974f7ae45a8125ab4fabcf8322126a4bf39b8))

## [2.15.0](https://github.com/srobroek/slopvac/compare/v2.14.0...v2.15.0) (2026-10-20)


### Features

* **rules:** `slopvac rules` gains `--genre <genre>` and `--format md` ([#202](https://github.com/srobroek/slopvac/issues/202)). `--include-excluded` keeps excluded rules in the output. Each Markdown block gives:
  - the category, scope, and kind
  - the severity and tier at the profile, and all tiers
  - the question or message, and the fix when defined
  - every bad and good example with its note
  - the exceptions and the provenance
* **explain:** `slopvac explain` renders through the same code and gains `--profile` and `--format md`. Its JSON gains `tier` and `effective_severity`.
* **prime:** `prime write` and `prime review` no longer embed rule lists. They point to `slopvac rules --kind judgement --genre <genre> --profile <profile> --format md` and say how to use each field. The review verdict gains `Checked:` and `Suppressions:` lines. A missing rules command or an unjustified suppression makes the verdict REVISE.
* **prime:** the generated command reference shows the positional arguments `TARGETS…`, `RULE_ID`, `[TOPIC]` and `[HARNESS]`, with their choices and whether each is required.
* **docs:** `docs/suppressions.md` is the full suppression reference. `docs/rules-output.md` documents both `--format json` and `--format md`.
* No rules were added or removed in 2.15.0; the ruleset matches 2.12.0 (231 rules: 165 checked, 66 judgement).


### Bug Fixes

* **suppressions:** five defects fixed, covered by tests that run through the CLI ([#202](https://github.com/srobroek/slopvac/issues/202)):
  1. A bad or missing reason on a rule that Vale runs is reported once, whichever engine runs the rule.
  2. Comment mode applies directives with and without Vale. A directive inside a source comment covers the next comment block.
  3. Diff mode keeps `meta.invalid-suppression` when the directive is on an added line.
  4. Vale's own comments (`<!-- vale off -->`, `<!-- vale X = NO -->`, `.. vale off`) no longer hide findings.
  5. Non-raw Vale findings in front matter and HTML comments are dropped, matching the native engine.
* **vale:** the minimum Vale version is 3.18.0, up from 3.15. Earlier releases need the external `mdx2vast` to read MDX. Vale 3.15 also reported lines one late after an empty comment line in comment mode, so a finding could land inside a suppression. An older Vale gets the "upgrade Vale" incomplete note.
* **ci:** CI and the GitHub Action install Vale 3.24.0. The pin lives in `scripts/install_vale.py`, where Renovate updates it. The Action's `vale-version` input defaults to that pin.

## [2.14.0](https://github.com/srobroek/slopvac/compare/v2.13.1...v2.14.0) (2026-10-20)


### Features

* **prime:** full CLI reference in prime; correct cross-referenced docs ([#200](https://github.com/srobroek/slopvac/issues/200)) ([2331f6a](https://github.com/srobroek/slopvac/commit/2331f6a2ea126e1ac2d26c09c26a9723f1de076e))

## [2.13.1](https://github.com/srobroek/slopvac/compare/v2.13.0...v2.13.1) (2026-10-19)


### Bug Fixes

* **guidance:** keep facts, default to one subagent review pass ([#198](https://github.com/srobroek/slopvac/issues/198)) ([99e54d2](https://github.com/srobroek/slopvac/commit/99e54d2aaea89fa50b85344d9b8a7dce3bda9542))

## [2.13.0](https://github.com/srobroek/slopvac/compare/v2.12.0...v2.13.0) (2026-10-19)


### Features

* **cli:** add a PyPI update notice ([#197](https://github.com/srobroek/slopvac/issues/197)) ([1ed19ec](https://github.com/srobroek/slopvac/commit/1ed19ec873429487e0669bdbd1d64e620c69924b))


### Bug Fixes

* **ci:** give the publish smoke probe a stable native finding ([#195](https://github.com/srobroek/slopvac/issues/195)) ([206d4f2](https://github.com/srobroek/slopvac/commit/206d4f2e48ac0d3d7f4124e17c356be1af998ddf))

## [2.12.0](https://github.com/srobroek/slopvac/compare/v2.11.0...v2.12.0) (2026-10-19)


### Features

* **rules:** re-release the judgement rules removed in 2.11.0 ([26beea3](https://github.com/srobroek/slopvac/commit/26beea3feba9daaa4c0c7e752116ae2034876af0)). The ruleset grows from 166 to 231 rules: 165 checked rules and 66 judgement rules. Judgement rules are questions for a reviewer, so lint does not run them. They reach the reviewer through `slopvac prime review`, `slopvac rules --kind judgement`, and the Judgement rules section of the rules reference. They stay out of compiled Vale styles and SARIF output.
  - 65 of them return from before 2.11.0. The question for `ai-tells-content-shape.one-point-dilution` now includes a shorter test and an explicit keep condition. `ai-tells-register.disclaimed-claim-remainder` is new (see below).
  - The 66 judgement rules, by category:
    - `ai-tells-content-shape` (9): `elegant-variation`, `epigram-closer-remainder`, `fabricated-citations-remainder`, `one-point-dilution`, `over-writing-remainder`, `padded-symmetry`, `textbook-connector-runs`, `unasked-for-rationale`, `vaporware-description`
    - `ai-tells-formatting` (1): `table-wrapping-one-sentence`
    - `ai-tells-register` (10): `anthropomorphised-justification-remainder`, `disclaimed-claim-remainder`, `false-agency-remainder`, `faux-candor-remainder`, `figurative-verb-verdict-remainder`, `hedged-symmetry`, `intensifier-tics-remainder`, `organic-consequence-remainder`, `over-formatting-reflex`, `urgency-inflation-remainder`
    - `ai-tells-structure` (19): `absolute-assertion-remainder`, `analogy-stack-authority`, `anaphora-abuse`, `audience-straddle-remainder`, `cataphoric-lead-in-remainder`, `contrastive-inversion-remainder`, `false-range`, `false-suspense-remainder`, `heading-echo`, `hollow-acknowledgment`, `invented-concept-label`, `listicle-in-a-trench-coat`, `meta-narration-remainder`, `negative-inventory-remainder`, `staccato-negative-parallel-remainder`, `summary-closer-remainder`, `think-of-it-as-remainder`, `tricolon-abuse-remainder`, `vague-attribution-remainder`
    - `orwell` (1): `concrete-floor`
    - `prose-discipline` (5): `bare-quantifier-with-figure-available`, `competing-actor-terms`, `hedged-into-uselessness`, `marketing-register`, `overloaded-sentence`
    - `prose-scope` (1): `code-change-prose-scope`
    - `ste-descriptive` (4): `information-not-gradual`, `missing-key-word-structure`, `paragraph-has-multiple-topics`, `paragraph-without-related-information`
    - `ste-nouns` (1): `long-domain-term-without-short-form`
    - `ste-practices` (3): `ambiguous-preposition-with`, `word-sense-incorrect`, `word-swap-insufficient`
    - `ste-punctuation` (1): `parentheses-misuse`
    - `ste-safety` (1): `risk-level-word-missing-or-wrong`
    - `ste-sentences` (2): `missing-connector-between-related-sentences`, `sentence-not-short-or-clear`
    - `ste-verbs` (2): `gerund-outside-noun-use`, `past-participle-not-adjectival`
    - `ste-words` (6): `domain-noun-category-membership`, `domain-noun-not-organization-approved`, `domain-noun-too-long-or-unclear`, `domain-verb-category-membership`, `unapproved-word-not-a-domain-noun`, `word-used-outside-permitted-sense`
  - `one-point-dilution` asks one decidable question with a keep condition.
* **rules:** new pattern rule `ai-tells-register.disclaimed-claim-core` (warning, on at `normal`), with the judgement rule `ai-tells-register.disclaimed-claim-remainder`. Both flag an artifact that disclaims a claim instead of naming the check that was run, such as "This change makes no claim about endpoint health".
* **guidance:** `slopvac prime write` prints a writing guide. `slopvac prime review` prints a review workflow with a checklist generated from the judgement rules. It asks a remainder question even when its pattern partner already fired. A `[guidance]` config table accepts `auto` or `off` for `write`, and `auto`, `ask`, or `off` for `review`. Reworded claims must stay as strong as their source.
* **setup:** `slopvac init --harness` and `slopvac setup` install a thin `slopvac-prose` skill for harnesses that load project skills, and `slopvac init --no-skills` skips it during initialization. Setup treats a `SKILL.md` as slopvac-managed only when its exact marker line is present. It refuses to overwrite or remove a hand-written one.


### Bug Fixes

* **rules:** retire two rules and rename one after human labelling judged their findings false positives ([#181](https://github.com/srobroek/slopvac/issues/181), [#183](https://github.com/srobroek/slopvac/issues/183)):
  - removed `ai-tells-formatting.curly-quotes` (every curly-apostrophe finding was a false positive)
  - removed `ai-tells-register.uniform-paragraph-mass` (no actionable true positive)
  - `ste-sentences.omitted-word-or-contraction` is now `ste-sentences.omitted-subject`. It checks only the subject-elided conditional opener ("If, When, or Once" with no subject) and no longer flags contractions.
* **rules:** narrow false-positive hotspots found by human labelling of 199 disputed findings. Rule ids are unchanged ([#183](https://github.com/srobroek/slopvac/issues/183)). Affected: `prose-agency.false-agency`, `prose-agency.unattributed-recommendation`, `prose-agency.agentless-passive`, `ai-tells-structure.tricolon-abuse-core` (evaluative triads only), `ai-tells-content-shape.durable-vocabulary-habits`, `prose-promotion.promotional-puffery`, `prose-discipline.frozen-verb`, `prose-craft.articles`, `prose-craft.future-tense`, `ste-nouns.multiword-noun-too-long`, `ste-procedural.condition-after-command`, and `prose-format.prose-block` (a series-based `enumerating_paragraph_words` check above 100 words, replacing `paragraph_words` above 80).
* **rules:** `ste-practices.latin-abbreviation` and all of `prose-craft.latinisms` are off by default. A `[rules."<id>"]` entry with a severity turns either one on when its category is enabled. At `relaxed`, enable the category too. Enabling `prose-craft.latinisms` enables its substitutions for `e.g.`, `i.e.`, `etc.`, `viz.`, `vs.`, `cf.` and `N.B.` ([#184](https://github.com/srobroek/slopvac/issues/184), [#185](https://github.com/srobroek/slopvac/issues/185)).

## [2.11.0](https://github.com/srobroek/slopvac/compare/v2.10.0...v2.11.0) (2026-09-25)


### Features

* replace agent skills with CLI-managed steering ([49a91f2](https://github.com/srobroek/slopvac/commit/49a91f2bb96d90dad6b7f9c4c289fd328acae2f7))


### Documentation

* add Codex Security threat model ([#171](https://github.com/srobroek/slopvac/issues/171)) ([95b386c](https://github.com/srobroek/slopvac/commit/95b386c7daa76e1fad43900fdbf9336111add91e))
* fix README markdown spacing ([9baed52](https://github.com/srobroek/slopvac/commit/9baed52e4ae95d1d52863ed05a065623e56f9d0d))
* fix Roadmap heading level ([c6f77f9](https://github.com/srobroek/slopvac/commit/c6f77f9ada9c89ddac0847a2efafbf12220340a6))
* fix threat model lint errors ([d186e51](https://github.com/srobroek/slopvac/commit/d186e5169f989dc6d08a9d87a7fef471d1a80d41))
* point status badges at main ([867adf8](https://github.com/srobroek/slopvac/commit/867adf872aab0d04cc8951ccda04024f71d3b9df))
* polish linter and roadmap description ([e7d3104](https://github.com/srobroek/slopvac/commit/e7d3104779404697f01e85d8a643b415084735f4))
* refresh Slopvac linter documentation and assets ([9e72c0a](https://github.com/srobroek/slopvac/commit/9e72c0a0eedaa5d8dfaff83a27aee34c9288fa19))
* show live Tests gate state ([f35c63c](https://github.com/srobroek/slopvac/commit/f35c63c10ff38ec2a4706da371c8ec46d5946e86))
* use consistent workflow status badges ([09f29ae](https://github.com/srobroek/slopvac/commit/09f29ae041dd9c56280e4d987d04e51a847db923))
* use live workflow status for tests badge ([3b4ee70](https://github.com/srobroek/slopvac/commit/3b4ee70213b43395303a380ae635681afb8baade))
* use native GitHub CI badge ([#170](https://github.com/srobroek/slopvac/issues/170)) ([38ab682](https://github.com/srobroek/slopvac/commit/38ab682ef1c72c1e151e6838a8fa7a766c5fbd53))
* use native workflow status badges ([313fc5a](https://github.com/srobroek/slopvac/commit/313fc5a802ff3502a6f616d9070cf66dc4f09e27))

## [2.10.0](https://github.com/srobroek/slopvac/compare/v2.9.1...v2.10.0) (2026-09-22)


### Features

* **judgement:** add validate and brief subcommands ([#156](https://github.com/srobroek/slopvac/issues/156)) ([f79dad3](https://github.com/srobroek/slopvac/commit/f79dad3571f32cab9578737a72965a9638dbc0a7))
* **report:** add ai_signal axis with prose and AI-register roll-ups ([#154](https://github.com/srobroek/slopvac/issues/154)) ([03f5738](https://github.com/srobroek/slopvac/commit/03f5738444485f859a3502799be27f513cb6c000))
* **review-docs:** add opt-in judgement workflow ([#155](https://github.com/srobroek/slopvac/issues/155)) ([a0b8c90](https://github.com/srobroek/slopvac/commit/a0b8c908a51aac5a305b9378d09661cd5b5b1131))


### Bug Fixes

* **lint:** preserve match case and skip multi-alternative replacements in --fix ([#153](https://github.com/srobroek/slopvac/issues/153)) ([3a2cba2](https://github.com/srobroek/slopvac/commit/3a2cba2b53cf57283796c086fa8f7fbfd23f4e9d))
* **rules:** retire corporate-analytic-filler-remainder ([#151](https://github.com/srobroek/slopvac/issues/151)) ([60f9381](https://github.com/srobroek/slopvac/commit/60f9381ba3a84e25487797caf4025990f77e4ca3))


### Documentation

* **readme:** describe the two layers up front and write up the judgement layer ([#157](https://github.com/srobroek/slopvac/issues/157)) ([3c11f49](https://github.com/srobroek/slopvac/commit/3c11f49d1240ba8609e0f125448c7193647699df))
* **readme:** restructure into how it works, usage, methodology, and the science ([#159](https://github.com/srobroek/slopvac/issues/159)) ([9f81aea](https://github.com/srobroek/slopvac/commit/9f81aea07e2f685cfe8a041f5ddc5500302ae51a))
* **readme:** separate ai_signal strength from ai_signal_source; describe agnix precisely ([#160](https://github.com/srobroek/slopvac/issues/160)) ([343c6ae](https://github.com/srobroek/slopvac/commit/343c6ae30870522bbb73c2ab7db2c7fdf3f07ae1))

## [2.9.1](https://github.com/srobroek/slopvac/compare/v2.9.0...v2.9.1) (2026-09-22)


### Bug Fixes

* **judgement:** report noise-floor failure denominators and fingerprint the full instrument ([#148](https://github.com/srobroek/slopvac/issues/148)) ([a9b60a8](https://github.com/srobroek/slopvac/commit/a9b60a8992c4e9f4cff6b53a92b1b5e55d625311))
* **lint:** apply the text_type gate to document-scope lexical matches ([#149](https://github.com/srobroek/slopvac/issues/149)) ([7b2b448](https://github.com/srobroek/slopvac/commit/7b2b448d0aa68dd18449696eac82ff39aa18c31d))
* **lint:** pin text_type classifier Unicode and locale determinism ([#147](https://github.com/srobroek/slopvac/issues/147)) ([05f5a0b](https://github.com/srobroek/slopvac/commit/05f5a0bf3ddda14a94f13b84ad8f6911ef8927eb))

## [2.9.0](https://github.com/srobroek/slopvac/compare/v2.8.0...v2.9.0) (2026-09-21)


### Features

* **judgement:** add repeated Sol adjudication CLI ([d3977d7](https://github.com/srobroek/slopvac/commit/d3977d7dc101da5d9cb66ac35469cf04fba53c61))
* **judgement:** add standing Sol adjudication ([efab5ee](https://github.com/srobroek/slopvac/commit/efab5ee7379dff2df954425f6ba844dca9f238ff))


### Bug Fixes

* **judgement:** satisfy typo and markdown lint ([4630b87](https://github.com/srobroek/slopvac/commit/4630b8750441832bb3b07150c1e3eaeca95da174))
* **judgement:** sort exported symbols ([61fa100](https://github.com/srobroek/slopvac/commit/61fa100107383da6907282ee399c037d3e2e7d5b))
* **judgement:** tolerate benign model annotations ([38ab199](https://github.com/srobroek/slopvac/commit/38ab199d91e72a3121236d91515ceca883e178c1))
* **judgement:** tolerate model annotations ([de1d1a4](https://github.com/srobroek/slopvac/commit/de1d1a4ac2e6f104321b155e96bcf99826d21993))


### Performance

* cache judgement prepare projections ([ed6ca3f](https://github.com/srobroek/slopvac/commit/ed6ca3f151eebe8c2ea5e0524318ab014f68e926))
* index document projection ranges ([54acfc9](https://github.com/srobroek/slopvac/commit/54acfc93375062034f2d02210be4359ca8bc7e1d))
* **judgement:** changelog and import order for prepare caching ([c708945](https://github.com/srobroek/slopvac/commit/c7089451149e0a7b466be0b0ffe012c8ce4dc96b))
* **judgement:** make prepare linear in document size ([ecc4e31](https://github.com/srobroek/slopvac/commit/ecc4e31fa58ed7ac64d21fedc875783e8eea0543))


### Documentation

* finish v2 judgement evaluation ([4cd6977](https://github.com/srobroek/slopvac/commit/4cd6977fb62e5acee26ee47bdbfd941d218e517b))
* fix metrics list indentation ([a3b23bc](https://github.com/srobroek/slopvac/commit/a3b23bc863dcdda69a11c5314765ea86feeae3c0))
* **judgement:** fix prose lint wording ([eda4d25](https://github.com/srobroek/slopvac/commit/eda4d259123e75696bf7416f3516b78353254e5e))
* record corporate analytic filler adjudication ([243bfae](https://github.com/srobroek/slopvac/commit/243bfae776e60af3d277f68c9daba43324479301))
* record human-ext arm ([117f9c9](https://github.com/srobroek/slopvac/commit/117f9c95460357bb10588fcf1693315368915a22))
* record human-ext judgement arm ([e2a9536](https://github.com/srobroek/slopvac/commit/e2a9536a912301d952d31441c8167aaf76ceea99))
* spell out corporate analytic filler evidence ([8f920f4](https://github.com/srobroek/slopvac/commit/8f920f497e3f4f6f87e5241b08d4e343e52da43d))

## [2.8.0](https://github.com/srobroek/slopvac/compare/v2.7.0...v2.8.0) (2026-09-20)


### Features

* **judgement:** add noise-floor instrument ([18c5cd1](https://github.com/srobroek/slopvac/commit/18c5cd1e81981d14589478af9499704413a49956))
* **judgement:** default to unique quote salvage ([cdeff1f](https://github.com/srobroek/slopvac/commit/cdeff1fa1b7ad91a1f0762bed34b12354dd362f3))
* **judgement:** guard noise-floor decisions ([6e5a926](https://github.com/srobroek/slopvac/commit/6e5a92686ae59d2e1c3864cb709c7d952f6010e2))


### Bug Fixes

* gate lexical rules by text type ([0cd4f29](https://github.com/srobroek/slopvac/commit/0cd4f295c139b812b09d2fdaa4d67b006f272d47))
* improve absolute assertion precision ([9e2ddbb](https://github.com/srobroek/slopvac/commit/9e2ddbb5891bafb92672de515248f87890a4a99a))
* **judgement:** render rule questions and examples in judgement prompts ([0493862](https://github.com/srobroek/slopvac/commit/049386264442984bdb27ac88e404b5b5fe6bfa34))
* **judgement:** split noise-floor measurement and policy ([01cb1b1](https://github.com/srobroek/slopvac/commit/01cb1b193bc0befe6ea72568e856586fbde6c4cb))
* **judgement:** validate complete response sets ([323fc04](https://github.com/srobroek/slopvac/commit/323fc0471d399791437ccc8357ff054baaf7221e))
* keep non-imperative rule untyped ([ac5f267](https://github.com/srobroek/slopvac/commit/ac5f26733e862f0854aef46dd2566fe27d4ea2a3))
* refine absolute assertion judgement ([b5c7fac](https://github.com/srobroek/slopvac/commit/b5c7fac80b8e4b9ac52f6d10a7333cf73ec22644))
* refine absolute assertion judgement guidance ([e3a7372](https://github.com/srobroek/slopvac/commit/e3a73723e971a039679de82c9ee4d63f5f7ff425))


### Documentation

* fix evaluation record markdown ([c8b023e](https://github.com/srobroek/slopvac/commit/c8b023ea050f2f8411097bca53d19d7e7875158e))
* **judgement:** clarify noise-floor registration ([4f08562](https://github.com/srobroek/slopvac/commit/4f085620f55d4a160138cdf4dc7bd51ffea63399))
* record 2026-09-19 wider judgement evaluation ([d4858b9](https://github.com/srobroek/slopvac/commit/d4858b96d52332ba2274c9201b17ca4253de8819))
* record wider judgement evaluation ([1a50c91](https://github.com/srobroek/slopvac/commit/1a50c919e351d40183e6c99bf8af315b36267c57))
* refine evaluation record prose ([92afdeb](https://github.com/srobroek/slopvac/commit/92afdebdc14f46fdc92ce7a7b0a92790fe4c20b4))
* update evaluation record after human retry ([a74f5c2](https://github.com/srobroek/slopvac/commit/a74f5c29ddb12ac58e319d0cea9b6dce75a3ed1c))

## [2.7.0](https://github.com/srobroek/slopvac/compare/v2.6.0...v2.7.0) (2026-09-19)


### Features

* add Bedrock batch judgement runner ([1030c2b](https://github.com/srobroek/slopvac/commit/1030c2ba66f8942f35f53ad7bfa7ca5c05d2eabb))
* document AWS batch setup ([274fa42](https://github.com/srobroek/slopvac/commit/274fa4233c1dd859be513cffd9d159bb2fdfa593))
* document AWS Bedrock batch setup ([d93aeb3](https://github.com/srobroek/slopvac/commit/d93aeb377431c00b700fd5244a7eb13341725a1b))
* **judgement:** gold-set recall, control false confirms, evidence-gate discards, opt-in unique-quote salvage ([a22c05a](https://github.com/srobroek/slopvac/commit/a22c05af112e8938d79ae2f0354c135ae12b21ca))
* **judgement:** normative preset covers plain imperative paragraphs ([26f8e2f](https://github.com/srobroek/slopvac/commit/26f8e2f32f96c3bfd2e5f9c276d1046125682c68))
* **judgement:** standalone Bedrock batch runner for evaluation calls ([f7078fc](https://github.com/srobroek/slopvac/commit/f7078fca50c994e53bfaff1e518e64e038a0cf0a))
* **lint:** reinstate --mode code-comments on the 2.6.0 comment route ([bd84c00](https://github.com/srobroek/slopvac/commit/bd84c0009f19a365aac3a44f8a00bbd7a8752c14))
* **slopvac-lint:** stable span identity on the shipped projection ([25e7a30](https://github.com/srobroek/slopvac/commit/25e7a303dda8a1abd01ab8ebb70d96d71e4a9064))
* **slopvac:** make inclusive rules opt-in by profile ([1f2b312](https://github.com/srobroek/slopvac/commit/1f2b312752738e7638318c904e67573d8a76418c))
* use 32000 token Bedrock budget ([fba847a](https://github.com/srobroek/slopvac/commit/fba847af4f250b3b09cfb75d94971c3e4acf56e5))


### Bug Fixes

* collect native Anthropic batch output ([6351f25](https://github.com/srobroek/slopvac/commit/6351f2503bab727f70b77802805f404df0464fc5))
* **judgement:** finish --adjudication counts each verdict once with an explicit label map ([a959991](https://github.com/srobroek/slopvac/commit/a959991a8b7e9836ab3b031a04eac94fc2306b66))
* **judgement:** FP-FRAGMENT-UNIT row verdicts count as FP ([3e480aa](https://github.com/srobroek/slopvac/commit/3e480aa8377703fd72a452616297b47f75c0d192))
* **judgement:** gate heading-echo on material redundancy ([f4f7546](https://github.com/srobroek/slopvac/commit/f4f7546c896480001bd0091f3bbc16590096bf2f))
* **judgement:** gold-set review round - shipped v1 schema, evidence-overlap recall, multi-unit spans, unit-only salvage ([5d01773](https://github.com/srobroek/slopvac/commit/5d017733a245ab5b3812d6e1872b902d20657821))
* **judgement:** heading-echo predicate treats locator boilerplate as non-material and normalises derivational forms ([a6aeeeb](https://github.com/srobroek/slopvac/commit/a6aeeeb8e158d3af1ecb934b1a6d3874cd07b381))
* **judgement:** heading-echo redundancy detects new content words and short restatements ([7e068b4](https://github.com/srobroek/slopvac/commit/7e068b45df478902a2cf421431b44fde5a25135f))
* **judgement:** occurrence ordinal on every judgement unit ([0792132](https://github.com/srobroek/slopvac/commit/0792132f6569ebff52c52b3f765b0be85f4b422a))
* **judgement:** ordinal from per-document construction order ([d9305ac](https://github.com/srobroek/slopvac/commit/d9305ac2681810c0f6df861ab6b5ba3c6839fc07))
* **judgement:** plain-paragraph imperative detection uses the text_type classifier; list path unchanged ([a1de89f](https://github.com/srobroek/slopvac/commit/a1de89fe31ed2defc054aa63e2e35e71f7134168))
* **judgement:** repair driver document and response handling ([7f5824a](https://github.com/srobroek/slopvac/commit/7f5824a82b888ca6b50e86d78a8974e1caef5a01))
* **lint:** classifier distinguishes noun-subject homographs and bare imperative Note ([6726932](https://github.com/srobroek/slopvac/commit/6726932b278c19169a1558f2fa75a0ad334079a0))
* **lint:** code-comments review round - config mode precedence, informational skips ([c0f03db](https://github.com/srobroek/slopvac/commit/c0f03db84d4f8c63d84253ead10f6c845f953d4d))
* **lint:** code-comments round 3 - unchecked RST-only targets exit 2, TOML out of prose collection ([cd8ec81](https://github.com/srobroek/slopvac/commit/cd8ec817f41620c5ba54090546aa8909b16504fa))
* **lint:** omit empty notes from the JSON report ([fd62c23](https://github.com/srobroek/slopvac/commit/fd62c23fab3f5648810c9ae5bd351f51e42fc748))
* **lint:** phrasal imperatives after safety markers classify PROCEDURAL ([9e8ae69](https://github.com/srobroek/slopvac/commit/9e8ae6918448e97c490304dac7eb7c256ded077e))
* **lint:** safety-marker imperatives and negative imperatives classify PROCEDURAL ([58b861f](https://github.com/srobroek/slopvac/commit/58b861fa19d647e67ccc4e372be4e8a6efe86f1a))
* make judgement gate reporting-only ([5c52a3f](https://github.com/srobroek/slopvac/commit/5c52a3fca92a35bc82bf2102a364e8544042d686))
* parallelize invoke calls and collect native output ([87f6760](https://github.com/srobroek/slopvac/commit/87f67605a53ae2c6599909750147f1b609e45a1f))
* preserve Bedrock parse diagnostics ([aa03d0c](https://github.com/srobroek/slopvac/commit/aa03d0c7c22f04808aa93c1de22a7a203b05e441))
* reject truncated Bedrock responses ([78362fa](https://github.com/srobroek/slopvac/commit/78362fad36e6f8764ca109eab5f50ea6872febef))
* **slopvac-lint:** span identity review round - text-based ids, unbordered tables, HTML text nodes ([d3d1025](https://github.com/srobroek/slopvac/commit/d3d1025390d97fc43f0ca6c3ed3dc849d6e57a99))
* **slopvac:** compile profile-default rules ([447ccc4](https://github.com/srobroek/slopvac/commit/447ccc46ba8410f1e19e41760a38ba3f9c9358fb))


### Documentation

* explain judgement driver workflow ([071eaa1](https://github.com/srobroek/slopvac/commit/071eaa15dea9499ce827970ef1e9e2a9e86c612d))
* fix AWS runner prose gate ([b64ed97](https://github.com/srobroek/slopvac/commit/b64ed974ce3009796c099551b015bfee6b984e10))
* record deleted AWS bucket accurately ([b1f8d3c](https://github.com/srobroek/slopvac/commit/b1f8d3c77a5b7bc63184a0798b1db486858a3e06))
* **slopvac-lint:** evaluation record schema, normalized records, --adjudication precision ([f82c776](https://github.com/srobroek/slopvac/commit/f82c77692d6ad5b46c483b55352268a8e43f515b))
* **slopvac-lint:** judgement guide review fixes ([f81f81f](https://github.com/srobroek/slopvac/commit/f81f81f6a79e65f043ba90cacc552c415fe40d55))
* **slopvac-lint:** record normalizer review round - single-count adjudications, explicit labels, pre-gate evidence denominator ([686de4e](https://github.com/srobroek/slopvac/commit/686de4e6aa83c09e8dd207510501ba775c34210f))
* **slopvac:** skills README states 26 categories ([2966e93](https://github.com/srobroek/slopvac/commit/2966e93d91233b81d723e1332b39157c1af7bb59))
* **slopvac:** skills README states 26 categories, matching the 2.6.0 inventory ([0b3ace8](https://github.com/srobroek/slopvac/commit/0b3ace821d0e8b07780e9ef654e23603bd58bd84))

## [2.6.0](https://github.com/srobroek/slopvac/compare/v2.5.0...v2.6.0) (2026-09-17)


### Features

* **judgement:** add contract evaluation runner ([af9ef8e](https://github.com/srobroek/slopvac/commit/af9ef8e6f62db72b79a256543d09b4c9ad702080))
* **judgement:** add fact-preservation rewrite checker ([bba1e19](https://github.com/srobroek/slopvac/commit/bba1e1912d97e47da37a98c03f486fd9d47a2546))
* **judgement:** add the prepare/finish/compare evaluation driver ([6f7021f](https://github.com/srobroek/slopvac/commit/6f7021f48cd1f58d426c4db1312cacb6d75d3db4))
* **judgement:** adjudicate model verdicts against the rubric contract ([2df8fdd](https://github.com/srobroek/slopvac/commit/2df8fddbba2bb918de74a1fa217a7c0d78d59596))
* **judgement:** aggregate judgement findings without gating the composite score ([36eb301](https://github.com/srobroek/slopvac/commit/36eb301a452489938f15d51860c47045c56bd37d))
* **judgement:** precision interventions for the dominant false-positive families ([01a4a47](https://github.com/srobroek/slopvac/commit/01a4a47d92f1aa1633539b3597c89f9786290161))
* **judgement:** precision interventions for the four dominant false-positive families ([1beaaa6](https://github.com/srobroek/slopvac/commit/1beaaa68e69dcbfe8517d4a965b38ffe12a6c7d6))
* **judgement:** render deterministic judgement packs ([bf518e0](https://github.com/srobroek/slopvac/commit/bf518e02744eea9162f509cfe03769a89e923d6b))
* **lint:** detect formulaic heading patterns ([971c62c](https://github.com/srobroek/slopvac/commit/971c62c607e8156a2e9abc7f7cb3d0341a9a61c2))
* **slopvac-lint:** add typed judgement rule contracts ([55dc78c](https://github.com/srobroek/slopvac/commit/55dc78c2dc69a5b817369f4ffdf2ed863c52f461))
* **slopvac-lint:** map projected prose to raw bytes and classify unit origin ([74495c2](https://github.com/srobroek/slopvac/commit/74495c2f02ec159168e2a8f8a2fc33a6636b39b9))
* **slopvac-lint:** STE sentence segmentation boundaries ([3522ca4](https://github.com/srobroek/slopvac/commit/3522ca4d10d0ef7e0c491560cbdcb02ac7977adf))
* **slopvac-lint:** Unicode-aware STE token boundaries ([e936045](https://github.com/srobroek/slopvac/commit/e936045d6c214e1d2291d87260b7c395ba89e95a))
* **slopvac:** keep documentation on the current artifact ([9114362](https://github.com/srobroek/slopvac/commit/91143620ff1a344238b01131e28f8fe45cd70287))


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

* fix judgement coverage and enforce complete evaluation-record measurements (slopvac-cz0.23)

## Changelog

* gate lexical rules on the repaired sentence `text_type` classifier

* keep `instruction-not-imperative` untyped because its bad examples are deliberately descriptive violations

* document the official v2 judgement evaluation, tolerant finish, shared-population comparison, and adjudicated precision metrics (slopvac-cz0.36)
