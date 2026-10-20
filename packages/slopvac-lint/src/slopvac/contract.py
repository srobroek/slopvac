"""What `slopvac lint` promises its callers: the exit codes, and the files a
directory target expands to.

The `cli` docstring explains the exit codes. They and the target globs live
apart from `pipeline` so that every command can exit with them, and `slopvac
prime` can document them, without loading the lint machinery.
"""

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

LINTABLE = ("*.md", "*.mdx", "*.markdown", "*.txt", "*.rst", "*.html")

SKIP_SOURCE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "vendor",
        "build",
        "dist",
        "target",
        "__pycache__",
    }
)
