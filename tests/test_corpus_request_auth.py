"""Authorization stays on the exact HTTPS GitHub API origin."""
import io
import sys
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/judge-corpus"))
from judge_corpus import sources


@pytest.mark.parametrize("url", [
    "https://api.github.com/repos/owner/repo",
    "https://API.GITHUB.COM:443/repos/owner/repo",
])
def test_github_api_receives_token(monkeypatch, url):
    seen = []
    def open_request(request, timeout):
        seen.append(request)
        assert timeout == 45
        return io.BytesIO(b"{}")
    monkeypatch.setenv("GITHUB_TOKEN", "test-credential")
    monkeypatch.setattr(urllib.request, "build_opener", lambda handler: SimpleNamespace(open=open_request))
    assert sources.fetch_json(url) == {}
    assert seen[0].get_header("Authorization") == "Bearer test-credential"
    assert "Authorization" not in seen[0].headers


@pytest.mark.parametrize("url", [
    "https://api.github.com.evil.example/path",
    "https://evil.example/api.github.com",
    "https://evil.example/?host=api.github.com",
    "https://api.github.com@evil.example/path",
    "https://user@api.github.com/path",
    "https://api.github.com:8443/path",
    "http://api.github.com/path",
    "https://en.wikipedia.org/w/api.php",
])
def test_other_sources_remain_unauthenticated(monkeypatch, url):
    monkeypatch.setenv("GITHUB_TOKEN", "test-credential")
    def open_request(request, timeout):
        assert request.get_header("Authorization") is None
        return io.BytesIO(b"{}")
    monkeypatch.setattr(urllib.request, "urlopen", open_request)
    assert sources.fetch_json(url) == {}


@pytest.mark.parametrize("url", ["https://api.github.com:bad/", " https://api.github.com/", "https://api.github.com/\tpath"])
def test_ambiguous_origins_are_not_authorized(url):
    assert not sources._github_api_origin(url)


@pytest.mark.parametrize("destination,authorized", [
    ("https://api.github.com/repos/new/repo", True),
    ("https://api.github.com:443/repos/new/repo", True),
    ("https://other.example/", False),
    ("https://api.github.com.evil.example/", False),
    ("http://api.github.com/", False),
])
def test_redirects_preserve_only_trusted_authorization(destination, authorized):
    request = urllib.request.Request("https://api.github.com/repos/old/repo")
    request.add_unredirected_header("Authorization", "Bearer test-credential")
    redirected = sources._GitHubRedirectHandler("test-credential").redirect_request(
        request, None, 302, "Found", {}, destination
    )
    assert redirected.get_header("Authorization") == ("Bearer test-credential" if authorized else None)
    assert "Authorization" not in redirected.headers


def test_transient_failures_retry_without_changing_authorization(monkeypatch):
    attempts = []
    monkeypatch.setenv("GITHUB_TOKEN", "test-credential")
    monkeypatch.setattr(sources.time, "sleep", lambda delay: None)
    def open_request(request, timeout):
        attempts.append(request.get_header("Authorization"))
        if len(attempts) == 1:
            raise sources.urllib.error.URLError("temporary")
        return io.BytesIO(b"{}")
    monkeypatch.setattr(urllib.request, "build_opener", lambda handler: SimpleNamespace(open=open_request))
    assert sources.fetch_json("https://api.github.com/repos/owner/repo") == {}
    assert attempts == ["Bearer test-credential", "Bearer test-credential"]
