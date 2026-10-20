"""Test-wide isolation.

THE SUITE MUST NOT WRITE TO THE USER'S CACHE. Several tests call
`compile_ruleset` without an `outdir`, which is the real code path and worth
exercising, and that path writes to `cache_root()`. Most of those calls also pass
`validate=False`, because they assert something about the fingerprint rather than
about Vale, and an unvalidated compile writes every rule INCLUDING the ones Vale
refuses to load.

The result was a poisoned cache entry in the developer's own `~/.cache/slopvac`:
a real `slopvac` run whose config happened to fingerprint the same way found a
manifest, trusted it, and handed Vale a style tree containing an emoji rule Go's
regex engine rejects. Vale answers E201 and then lints NOTHING while exiting 0,
so the file reads clean and the score silently drops to the native rules alone.

Redirecting the cache per test session fixes it at the source. The compiler also
now refuses to publish an unvalidated tree to the shared cache, so this fixture
is the belt to that suspenders -- either alone would have prevented it.

`load_ruleset` writes to the same root, and module-scoped fixtures call it before
any function-scoped fixture runs, so the session gets its own root as well.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolated_session_cache(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(
            "SLOPVAC_CACHE_DIR", str(tmp_path_factory.mktemp("slopvac-session-cache"))
        )
        yield


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path_factory, monkeypatch):
    monkeypatch.setenv(
        "SLOPVAC_CACHE_DIR", str(tmp_path_factory.mktemp("slopvac-cache"))
    )
