"""Jev wire-compatibility probe, run against every arm's live server.

Checks the portable Jev subset the slopvac spec requires (docs/design/local-judging.md, "Wire
protocol" and "Conformance suite"): one noul + one choice + one score per request, question ids
returned as sent, distribution coverage and sums, score legend keys, model/usage fields, 422 on a
malformed request, 422 (not truncation) on an oversized state, versioned `model` ids, determinism
over five identical requests, and response headers. Auth (401) is not probed: servers run open.
"""

STATE = {
    "span": "As of my last update, the loader retried twice.",
    "context": "Release notes, v2.3.",
}
MIXED = {
    "defect": {
        "type": "noul",
        "instructions": "Does the text contain chat-session leakage?",
    },
    "verdict": {
        "type": "choice",
        "instructions": "Is chat-session leakage present in the text?",
        "criteria": {
            "real-defect": "The text exhibits this defect.",
            "no-defect": "The text does not exhibit this defect.",
            "insufficient-context": "The text is too short or ambiguous to decide.",
        },
    },
    "severity": {
        "type": "score",
        "instructions": "How severe is the defect?",
        "criteria": ["No defect.", "Minor defect.", "Major defect."],
    },
}


def _dist_ok(ans, keys):
    probs = ans.get("probabilities") or {}
    return set(probs) == set(keys) and abs(sum(probs.values()) - 1.0) <= 0.01


def _dist(ans):
    if ans.get("type") == "noul":
        return {"true": ans.get("noul")}
    return ans.get("probabilities") or {}


def probe(client, arm):
    out = {}
    body = {"state": STATE, "model": arm["model"], "questions": MIXED}
    status, payload, headers, _ = client.request("POST", "/v1/systemone", body)
    answers = (payload or {}).get("answers", {}) if status == 200 else {}
    noul = answers.get("defect", {})
    choice = answers.get("verdict", {})
    score = answers.get("severity", {})
    lower = {k.lower() for k in headers}
    out["mixed_request"] = {
        "status": status,
        "ids_returned_exactly": set(answers) == set(MIXED),
        "noul_scalar_in_unit_interval": isinstance(noul.get("noul"), (int, float))
        and 0 <= noul["noul"] <= 1,
        "noul_has_probabilities_map": "probabilities" in noul,
        "choice_distribution_ok": _dist_ok(choice, MIXED["verdict"]["criteria"]),
        "choice_selected": choice.get("choice"),
        "score_distribution_ok": _dist_ok(score, [str(i) for i in range(3)]),
        "score_legend_ok": set((score.get("legend") or {})) == {"0", "1", "2"},
        "model_field": (payload or {}).get("model"),
        "usage_present": isinstance((payload or {}).get("usage"), dict),
        "answer_type_fields": sorted({a.get("type") for a in answers.values()}),
        "x_typesafe_request_id": "x-typesafe-request-id" in lower,
        "x_slopvac_model_revision": "x-slopvac-model-revision" in lower,
        "raw": payload,
    }
    for model_id in ("jev-1.13.0", "slopvac-judge-pilot-v1"):
        s, p, _, _ = client.request(
            "POST", "/v1/systemone", {**body, "model": model_id}
        )
        out[f"model_id:{model_id}"] = {
            "status": s,
            "response_model": (p or {}).get("model") if s == 200 else None,
            "routing": (p or {}).get("routing") if s == 200 else None,
            "error": None if s == 200 else p,
        }
    s, p, _, _ = client.request(
        "POST",
        "/v1/systemone",
        {
            "state": "x",
            "model": arm["model"],
            "questions": {"q": {"instructions": "no type"}},
        },
    )
    out["malformed_missing_type"] = {"status": s, "error": p if s != 200 else None}
    s, p, _, _ = client.request(
        "POST",
        "/v1/systemone",
        {
            "state": "x",
            "model": arm["model"],
            "questions": {"q": {"type": "choice", "instructions": "?", "criteria": {}}},
        },
    )
    out["malformed_empty_criteria"] = {"status": s, "error": p if s != 200 else None}
    s, p, _, _ = client.request("POST", "/v1/systemone", b"{not json")
    out["malformed_json"] = {"status": s}
    big = (
        "The loader retries twice. " * 12000
    )  # ~300k characters, far past a 1,024-token profile
    s, p, _, _ = client.request(
        "POST",
        "/v1/systemone",
        {"state": big, "model": arm["model"], "questions": {"defect": MIXED["defect"]}},
    )
    out["oversized_state_300k_chars"] = {
        "status": s,
        "truncated_and_answered": s == 200,
        "error": p if s != 200 else None,
    }
    dists = []
    for _ in range(5):
        s, p, _, _ = client.request("POST", "/v1/systemone", body)
        if s == 200:
            dists.append({q: _dist(a) for q, a in p["answers"].items()})
    diff = 0.0
    for d in dists[1:]:
        for q, dist in d.items():
            for k, v in dist.items():
                diff = max(diff, abs((v or 0) - (dists[0][q].get(k) or 0)))
    out["determinism_5x"] = {
        "ok_responses": len(dists),
        "max_abs_diff": diff,
        "within_1e-4": diff <= 1e-4,
    }
    s, p, _, _ = client.request("GET", "/v1/models")
    out["get_v1_models"] = {"status": s, "payload": p}
    return out
