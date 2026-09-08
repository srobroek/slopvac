#!/usr/bin/env bash
# Install the repository's staged agnix check for this worktree.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
hook_path="$repo_root/.githooks"

if [[ ! -x "$hook_path/pre-commit" ]]; then
	printf 'expected executable hook is missing: %s\n' "$hook_path/pre-commit" >&2
	exit 1
fi

# Read the effective setting before enabling worktree config. Git's path mode
# expands `~` and relative paths consistently with the value Git will use.
current_hooks="$(git config --path --get core.hooksPath || true)"
git config extensions.worktreeConfig true
installed="$(git config --worktree --get agnix.hooksInstalled || true)"
is_agnix_hooks_path() {
	local candidate="$1"
	[[ -n "$candidate" ]] || return 1
	[[ "$candidate" == "$hook_path" ]] && return 0
	[[ -f "$candidate/pre-commit" && -f "$hook_path/pre-commit" ]] || return 1
	cmp -s -- "$candidate/pre-commit" "$hook_path/pre-commit"
}

# Keep the original chain while this hook is active. If a user changes
# core.hooksPath to another scanner, capture that current scanner on the next
# installation so the new choice remains in the chain.
if [[ "$installed" != "true" ]] || ! is_agnix_hooks_path "$current_hooks"; then
	if ! is_agnix_hooks_path "$current_hooks"; then
		if [[ -n "$current_hooks" ]]; then
			git config --worktree agnix.previousHooksPath "$current_hooks"
		else
			git config --worktree --unset-all agnix.previousHooksPath >/dev/null 2>&1 || true
		fi
	fi
	git config --worktree agnix.hooksInstalled true
fi

git config --worktree core.hooksPath "$hook_path"
printf 'Installed agnix pre-commit hook for this worktree.\n'
