#!/usr/bin/env bash
# Install the repository's staged agnix check for this worktree.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
tracked_hooks="$repo_root/.githooks"
tracked_pre_commit="$tracked_hooks/pre-commit"

if [[ ! -x "$tracked_pre_commit" ]]; then
	printf 'expected executable hook is missing: %s\n' "$tracked_pre_commit" >&2
	exit 1
fi

# Read the effective setting before enabling worktree config. Git's path mode
# expands `~` and relative paths consistently with the value Git will use.
configured_hooks="$(git config --path --get core.hooksPath || true)"
git config extensions.worktreeConfig true

git_dir="$(git rev-parse --git-dir)"
case "$git_dir" in
/*) ;;
*) git_dir="$repo_root/$git_dir" ;;
esac
agnix_hooks="$git_dir/agnix-hooks"
common_hooks="$(git rev-parse --git-common-dir)/hooks"
case "$common_hooks" in
/*) ;;
*) common_hooks="$repo_root/$common_hooks" ;;
esac

absolute_path() {
	local candidate="$1"
	case "$candidate" in
	/*) printf '%s\n' "$candidate" ;;
	*) printf '%s\n' "$repo_root/$candidate" ;;
	esac
}

if [[ -n "$configured_hooks" ]]; then
	# `--git-path` resolves relative core.hooksPath values the same way Git
	# resolves them when it runs a hook.
	current_hooks="$(git rev-parse --git-path hooks)"
else
	current_hooks="$common_hooks"
fi
current_hooks="$(absolute_path "$current_hooks")"

recorded_hooks="$(git config --worktree --get agnix.hooksPath || true)"
if [[ -n "$recorded_hooks" ]]; then
	recorded_hooks="$(absolute_path "$recorded_hooks")"
fi
previous_hooks="$(git config --worktree --get agnix.previousHooksPath || true)"
if [[ -n "$previous_hooks" ]]; then
	previous_hooks="$(absolute_path "$previous_hooks")"
fi

is_managed_hooks_path() {
	local candidate="$1"
	[[ "$candidate" == "$agnix_hooks" ]] && return 0
	# Versions of this installer before the all-hook fix used the tracked
	# directory itself. Treat it as managed so its recorded scanner survives
	# migration to the per-worktree directory.
	[[ "$candidate" == "$tracked_hooks" ]] && return 0
	[[ -n "$recorded_hooks" && "$candidate" == "$recorded_hooks" ]] && return 0
	return 1
}
if is_managed_hooks_path "$current_hooks"; then
	# Reinstalling while agnix is active must not replace the original scanner.
	# A legacy install may not have recorded one, so fall back to common hooks.
	if [[ -z "$previous_hooks" || "$previous_hooks" == "$agnix_hooks" || "$previous_hooks" == "$tracked_hooks" ]]; then
		source_hooks="$common_hooks"
		git config --worktree agnix.previousHooksPath "$source_hooks"
	else
		source_hooks="$previous_hooks"
	fi
else
	# A different scanner was selected. Capture it before replacing the active
	# hook directory so the new wrappers chain to the newly selected scanner.
	source_hooks="$current_hooks"
	git config --worktree agnix.previousHooksPath "$source_hooks"
fi

git config --worktree agnix.hooksInstalled true
git config --worktree agnix.hooksPath "$agnix_hooks"
mkdir -p "$agnix_hooks"

# The directory is private to this worktree. Remove only symlinks so an
# operator's regular files there are not destroyed, then rebuild links from
# the currently selected scanner.
find "$agnix_hooks" -mindepth 1 -maxdepth 1 -type l -delete
if [[ -d "$source_hooks" && "$source_hooks" != "$agnix_hooks" ]]; then
	while IFS= read -r -d '' candidate; do
		[[ -f "$candidate" && -x "$candidate" ]] || continue
		name="${candidate##*/}"
		[[ "$name" == "pre-commit" ]] && continue
		ln -sfn -- "$candidate" "$agnix_hooks/$name"
	done < <(find "$source_hooks" -mindepth 1 -maxdepth 1 \( -type f -o -type l \) -print0)
fi

# Keep the repository hook as the one tracked entry point. It invokes the
# selected scanner's pre-commit hook before running agnix.
ln -sfn -- "$tracked_pre_commit" "$agnix_hooks/pre-commit"
git config --worktree core.hooksPath "$agnix_hooks"
printf 'Installed agnix hooks for this worktree; existing hooks remain chained.\n'
