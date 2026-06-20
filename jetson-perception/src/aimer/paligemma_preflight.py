"""Preflight checks for the local PaliGemma command parser backend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def run_preflight(model_id: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "model_id": model_id,
        "model_is_local_path": Path(model_id).exists(),
        "checks": {},
    }

    report["checks"]["torch"] = _check_torch()
    report["checks"]["transformers_paligemma"] = _check_transformers()

    if report["model_is_local_path"]:
        report["checks"]["huggingface_model_access"] = {
            "ok": True,
            "skipped": True,
            "reason": "model_id is a local path",
        }
    else:
        report["checks"]["huggingface_model_access"] = _check_huggingface_model(model_id)

    report["ok"] = all(check.get("ok", False) for check in report["checks"].values())
    return report


def _check_torch() -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}

    cuda_available = torch.cuda.is_available()
    result: dict[str, Any] = {
        "ok": True,
        "version": torch.__version__,
        "cuda_available": cuda_available,
        "cuda_version": torch.version.cuda,
        "device_count": torch.cuda.device_count(),
    }
    if cuda_available:
        result["device_name"] = torch.cuda.get_device_name(0)
    return result


def _check_transformers() -> dict[str, Any]:
    try:
        import transformers
        from transformers import AutoProcessor, PaliGemmaForConditionalGeneration
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}

    return {
        "ok": True,
        "version": transformers.__version__,
        "auto_processor": AutoProcessor.__name__,
        "model_class": PaliGemmaForConditionalGeneration.__name__,
    }


def _check_huggingface_model(model_id: str) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}

    try:
        info = HfApi().model_info(model_id)
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}

    gated = info.gated
    access_probe = _probe_hub_file_access(model_id, hf_hub_download)
    return {
        "ok": access_probe["ok"],
        "private": info.private,
        "gated": gated,
        "sha": info.sha,
        "file_count": len(info.siblings),
        "requires_hf_token": gated not in (False, None) or info.private,
        "file_access": access_probe,
    }


def _probe_hub_file_access(model_id: str, hf_hub_download) -> dict[str, Any]:
    try:
        path = hf_hub_download(model_id, "config.json")
    except Exception as exc:
        message = " ".join(str(exc).split())
        if "not in the authorized list" in message:
            reason = "token is valid but the account has not been granted access to this gated model"
        elif "gated repo" in message.lower() or "access to model" in message.lower():
            reason = "model is gated; authenticate with a token after accepting model terms"
        else:
            reason = message[:240]
        return {
            "ok": False,
            "filename": "config.json",
            "reason": reason,
        }

    return {
        "ok": True,
        "filename": "config.json",
        "cached_path": path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local PaliGemma runtime prerequisites")
    parser.add_argument(
        "--model-id",
        default="google/paligemma2-3b-mix-224",
        help="Hugging Face model id or local checkpoint path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    print(json.dumps(run_preflight(args.model_id), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
