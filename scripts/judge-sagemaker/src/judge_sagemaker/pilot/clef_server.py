"""Serve one Clef release through a Jev-compatible HTTP API with the release's own code.

    $CLEF_PY clef_server.py <arm> <port>

Resolves the arm's pinned Hub revision (HF_HUB_OFFLINE=1 after download_models.py), imports the
joint_schema_model.py that ships in it, and answers POST /v1/systemone with the release's
`systemone`: encode_record -> collate_records -> one bf16 forward -> a softmax per question. A
run_arm.py request is one System One record: the item's state, plus its question's type,
instructions and (for choice) criteria. GET /v1/models is the health route.

Placement (arms.py `placement`):
  single   load_release_model(path, device="cuda:0"), as the model card shows.
  sharded  load_release_model pins device_map={"": device}, so a backbone larger than one GPU is
           loaded the same way (bf16, use_cache off) with device_map="auto" over every visible
           GPU. The joint head goes on the GPU that holds the backbone's final norm, where the
           last hidden state lands, with a copy there of the output-embedding matrix it reads;
           ShardedClef.forward is ClefModel.forward plus those device moves.
Writes runs/<arm>/placement.json: the placement, devices and per-GPU memory after load.
"""

import json
import sys
import threading
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Annotated

import torch
import uvicorn
from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from huggingface_hub import snapshot_download

from arms import ARMS, RUNS

DTYPE = torch.bfloat16


def release_module(path):
    sys.path.insert(0, str(path))
    import joint_schema_model

    return joint_schema_model


def load_sharded(jsm, path, device_map="auto", dtype=DTYPE):
    """load_release_model with the backbone spread over several devices."""
    from safetensors.torch import load_file
    from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

    class ShardedClef(jsm.ClefModel):
        def __init__(self, language_model, head, head_device):
            super().__init__(language_model, head)
            self.head_device = head_device
            weight = language_model.get_output_embeddings().weight.detach()
            self.output_weight = weight.to(head_device)

        def forward(self, batch):
            if batch.get("media"):
                raise ValueError("the sharded placement serves text-only records")
            text_model = self.language_model.model.language_model
            outputs = text_model(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                use_cache=False,
                return_dict=True,
            )
            device = self.head_device
            return self.head(
                outputs.last_hidden_state.to(device),
                batch["input_ids"].to(device),
                batch["attention_mask"].to(device),
                batch["records"],
                self.output_weight,
            )

    backbone = Qwen3_5ForConditionalGeneration.from_pretrained(
        path, dtype=dtype, device_map=device_map
    )
    backbone.config.use_cache = False
    head_device = backbone.model.language_model.norm.weight.device
    head = jsm.JointSchemaHead(
        **json.loads((path / "joint_head_config.json").read_text())
    )
    head.load_state_dict(load_file(path / "joint_head.safetensors"), strict=True)
    head = head.to(device=head_device, dtype=dtype)
    model = ShardedClef(backbone, head, head_device).eval()
    return model, AutoProcessor.from_pretrained(path)


def load(arm):
    path = Path(snapshot_download(arm["repo"], revision=arm["revision"]))
    jsm = release_module(path)
    if arm["placement"] == "single":
        model, processor = jsm.load_release_model(path, device="cuda:0", dtype=DTYPE)
    else:
        model, processor = load_sharded(jsm, path)
    device_map = getattr(model.language_model, "hf_device_map", None) or {}
    devices = Counter(str(d) for d in device_map.values())
    head_device = str(next(model.head.parameters()).device)
    placement = {
        "placement": arm["placement"],
        "dtype": str(DTYPE).removeprefix("torch."),
        "release_dir": str(path),
        "backbone_modules_per_device": dict(devices),
        "head_device": head_device,
        "gpus": [
            {
                "index": i,
                "name": torch.cuda.get_device_name(i),
                "total_bytes": torch.cuda.get_device_properties(i).total_memory,
                "allocated_bytes_after_load": torch.cuda.memory_allocated(i),
            }
            for i in range(torch.cuda.device_count())
        ],
    }
    return jsm, model, processor, placement


def create_app(arm, jsm, model, processor, placement):
    app = FastAPI()
    lock = threading.Lock()
    device = (
        "cuda:0"
        if arm["placement"] == "single"
        else "cuda:" + ",".join(str(g["index"]) for g in placement["gpus"])
    )
    card = {
        "id": arm["model"],
        "object": "model",
        "run": f"{arm['repo']}@{arm['revision']}",
        "device": device,
        "backend": "transformers",
        "dtype": placement["dtype"],
        "placement": arm["placement"],
    }

    @app.get("/v1/models")
    def models():
        return {"object": "list", "data": [card], "models": [card]}

    @app.post("/v1/systemone")
    def systemone(body: Annotated[dict, Body()]):
        t0 = time.perf_counter()
        try:
            with lock:
                response = jsm.systemone(model, processor, body)
        except (ValueError, KeyError, TypeError) as error:
            return JSONResponse(
                status_code=422,
                content={"error": {"type": "invalid_request", "message": str(error)}},
            )
        response["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return JSONResponse(
            response, headers={"x-typesafe-request-id": uuid.uuid4().hex}
        )

    return app


def main():
    name, port = sys.argv[1], int(sys.argv[2])
    arm = ARMS[name]
    t0 = time.time()
    jsm, model, processor, placement = load(arm)
    placement["load_s"] = round(time.time() - t0, 1)
    out = RUNS / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "placement.json").write_text(json.dumps(placement, indent=2) + "\n")
    print(f"clef_server: {name} loaded {json.dumps(placement)}", flush=True)
    uvicorn.run(
        create_app(arm, jsm, model, processor, placement),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
