# Agent setup

Install the CLI and make `vale --version` succeed. Vale is optional but highly
recommended: it executes most deterministic checks. See the
[installation instructions](../README.md#install) for prerequisites.

Run setup from the project where the agent will work:

```sh
uv tool install slopvac
slopvac init --harness claude
```

Choose the harness that reads this project:

| Harness | Initialization | Project instructions |
| --- | --- | --- |
| Claude Code | `slopvac init --harness claude` | `CLAUDE.md` |
| Codex | `slopvac init --harness codex` | `AGENTS.md`, or an existing nonempty `AGENTS.override.md` |
| Oh My Pi | `slopvac init --harness omp` | `AGENTS.md`, or an existing nonempty `.omp/AGENTS.md` |
| Kiro | `slopvac init --harness kiro` | `.kiro/steering/slopvac.md` |
| Other agents that read `AGENTS.md` | `slopvac init` | `AGENTS.md` |

For several harnesses, repeat `--harness`. Shared destinations receive one
section. Start a new agent session after setup and ask the agent to run
`slopvac prime` to confirm that the CLI is available in its environment.

## Files and existing settings

`init` creates `slopvac.toml` if it is absent and installs a short, marked section
in the selected instruction file. Existing configuration remains unchanged.
`--force` replaces the configuration and preserves unrelated agent instructions.
`--skip-agents` creates configuration without steering.

```sh
slopvac init --dry-run
slopvac init --harness claude --harness codex
slopvac init --skip-agents
```

`--path PATH` selects the configuration file. Its parent directory is the root
for that initialization's steering files. Setup does not install binaries,
provider credentials, hooks, or user-wide settings.

The managed section sits between `<!-- slopvac:begin -->` and
`<!-- slopvac:end -->`. Repeated setup replaces that section and preserves text
outside it. An unchanged section is not rewritten. Setup rejects malformed or
duplicate marker pairs before changing any files.

An internal symlink such as `CLAUDE.md -> AGENTS.md` remains a symlink, and setup
updates its target once. A link outside the selected project is an error.

## Check, refresh, or remove steering

`setup` changes steering without creating or replacing configuration:

```sh
slopvac setup --list
slopvac setup claude --check
slopvac setup claude --dry-run
slopvac setup claude
slopvac setup claude --root ../another-project
slopvac setup claude --remove
```

`--check` returns 0 for a current section and 1 for an absent or outdated one.
Invalid arguments, unsafe paths, and malformed markers return 2. A check does
not launch the harness or prove that its settings load the instruction file.
`--remove` deletes only the managed section and leaves the file in place.

For another harness, `slopvac onboard` prints the section without writing files.
Paste it into the instruction file that harness actually loads.

## Details on demand

The steering points to CLI guidance for both linting and contextual review:

```sh
slopvac prime
slopvac prime lint
slopvac prime judgement
slopvac prime --genre consumer --format json
slopvac rules --judgement --format json
slopvac explain prose-craft.relative-date
```

`prime` prints the workflow without running lint, contacting a provider, or
editing files. `--genre` lists matching `recommended_for` categories from the
packaged catalog; it does not change the lint configuration. The writing rules
and their exceptions remain in the catalog, available through `rules` and
`explain`.

The lint workflow uses Vale and checks incomplete results. The judgement workflow
prepares prompts, delegates model calls to the harness, and validates responses
before aggregation. Model findings remain advisory. Both workflows require a
separate check of factual claims and missing task steps against source evidence.
See [contextual review](../README.md#judgement-layer) for the command contract.

## Harness loading

Codex gives a nonempty `AGENTS.override.md` precedence at the same directory.
Setup therefore uses that file when it exists. OMP setup prefers an existing
native `.omp/AGENTS.md`; otherwise it uses the shared `AGENTS.md` convention.
Other OMP discovery providers can shadow a shared file, and a nearer `.omp`
directory can change which native context loads. Verify the active context in
projects with custom discovery settings.

New Kiro files declare `inclusion: always`. Existing frontmatter is preserved,
so check that an existing file's inclusion setting matches the intended use.
A custom Kiro agent must include steering files in its `resources`; setup does
not modify agent JSON or permissions.

Harness documentation: [Claude Code memory](https://code.claude.com/docs/en/memory),
[Codex instructions](https://developers.openai.com/codex/guides/agents-md/),
[OMP context discovery](https://github.com/can1357/oh-my-pi/blob/main/docs/context-files.md),
and [Kiro steering](https://kiro.dev/docs/steering/).

## Remove an existing skill installation

Uninstall the Slopvac plugin through the harness that installed it, or remove
only the manually copied `write-docs` and `review-docs` directories. Then run
`slopvac init --harness HARNESS` or `slopvac setup HARNESS` for each project.
Setup leaves plugins installed and does not delete user-owned skills. Unrelated plugins
and project instructions should remain in place.
