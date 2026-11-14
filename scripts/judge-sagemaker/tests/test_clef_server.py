"""Exercise the HTTP boundary without loading model or GPU dependencies."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def server(monkeypatch):
    for name, attributes in {
        "torch": {"bfloat16": "bfloat16"},
        "uvicorn": {},
        "huggingface_hub": {"snapshot_download": None},
        "arms": {"ARMS": {}, "RUNS": Path("unused")},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    path = Path(__file__).resolve().parents[1] / "src/judge_sagemaker/pilot/clef_server.py"
    spec = importlib.util.spec_from_file_location("clef_server_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def client(server, callback):
    arm = {"placement": "single", "model": "test", "repo": "test/model", "revision": "pinned"}
    app = server.create_app(arm, SimpleNamespace(systemone=callback), object(), object(), {"dtype": "bf16"})
    return TestClient(app)


@pytest.mark.parametrize("error_type", [ValueError, KeyError, TypeError])
def test_invalid_requests_hide_exception_details(server, error_type, caplog):
    secret = "synthetic-sensitive-model-path"
    def fail(*args):
        raise error_type(secret)
    response = client(server, fail).post("/v1/systemone", json={"state": "test"})
    assert response.status_code == 422
    assert response.json() == {"error": {"type": "invalid_request", "message": "The request could not be processed."}}
    assert secret not in response.text
    assert secret in caplog.text


def test_success_and_health_contract_remain(server):
    http = client(server, lambda model, processor, body: {"answer": body["state"]})
    response = http.post("/v1/systemone", json={"state": "accepted"})
    assert response.status_code == 200
    assert response.json()["answer"] == "accepted"
    assert response.json()["latency_ms"] >= 0
    assert response.headers["x-typesafe-request-id"]
    assert http.get("/v1/models").json()["data"][0]["id"] == "test"
