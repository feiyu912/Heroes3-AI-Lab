"""Shared, side-effect-light helpers for schema6 strategic behavior cloning.

This package deliberately does NOT call ``qualification.require_qualification``:
that binding still contains WSL-era absolute paths.  The runtime catalog bytes
are pinned here instead, and every request is still validated by the frozen
schema6 encoder.  Native execution remains a separate, admission-gated step.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
PROJECT = EXPERIMENTS.parent
POLICY = EXPERIMENTS / "strategic-active-opponent-policy-v4"
CATALOG = EXPERIMENTS / "strategic-refill-paired-build-20261026/native-01/candidate-positive/agent/creature-catalog.json"
CATALOG_SHA256 = "031d9200e3efa40e2dd82363547d6f39e8f1381296f000d8b83b158ca663eb1e"
DEFAULT_INITIAL = EXPERIMENTS / "strategic-learned-recruitment-policy-v3/initialization-02/recruitment-initialization.pt"
DEFAULT_INITIAL_SHA256 = "1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1"
DEFAULT_UPDATED = EXPERIMENTS / "takeover-20261023/active-learning-delivery-01/control-update-1.pt"
DEFAULT_UPDATED_SHA256 = "b52ac74ad3b0ba6860e57be0a6b2deed9d8c88f14e140b59bd2c61e8b1f739fc"
BC_FORMAT = "strategic-bc-checkpoint-v1"
SCHEMA = "strategy-candidates-v6"
ARCHITECTURE_VERSION = "schema6-recruit-zero-residual-v2"

# The newest research package carries the actual Ubuntu resource-lock paths.
RESOURCE = Path(
    "/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/"
    "WSL迁出-20261025/files/root/heroes3-ai-lab/evaluations"
)


def sha256(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


encoder = module("_bc_schema6_encoder", POLICY / "encoder.py")
architecture = module("_bc_schema6_architecture", POLICY / "model.py")


def load_catalog(path: Path = CATALOG):
    assert sha256(path) == CATALOG_SHA256, "runtime catalog bytes changed"
    return encoder.load_catalog(path, CATALOG_SHA256)


def configure_catalog(path: Path = CATALOG):
    catalog = load_catalog(path)
    encoder.configure_catalog(catalog)
    return catalog


def tensor_sha(state: dict) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        tensor = value.detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str(tensor.dtype).encode())
        digest.update(str(tuple(tensor.shape)).encode())
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def atomic_torch_save(value, path: Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            torch.save(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        folder = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return sha256(path)


def load_any_checkpoint(path: Path, device: str = "cpu"):
    """Load an initialization, PPO checkpoint, or BC checkpoint without catalog admission.

    The caller must call ``configure_catalog`` first.  Returns ``(model, bundle,
    sha256)``.  Optimizer/RNG state is intentionally not restored here: BC starts a
    new optimizer epoch.
    """
    path = Path(path)
    raw = path.read_bytes()
    bundle = torch.load(__import__("io").BytesIO(raw), map_location="cpu", weights_only=True)
    digest = hashlib.sha256(raw).hexdigest()
    state = bundle.get("state_dict")
    hidden = bundle.get("hidden")
    prior = bundle.get("prior_config")
    if not isinstance(state, dict) or not isinstance(hidden, int) or not isinstance(prior, dict):
        raise ValueError("Checkpoint lacks state_dict/hidden/prior_config")
    if bundle.get("catalog_sha256") != CATALOG_SHA256:
        raise ValueError("Checkpoint catalog differs from pinned runtime catalog")
    if bundle.get("encoder_version") != encoder.ENCODER_VERSION:
        raise ValueError("Checkpoint encoder version differs")
    if bundle.get("architecture_version") != ARCHITECTURE_VERSION:
        raise ValueError("Checkpoint architecture version differs")
    model = architecture.PriorCandidateActorCritic(hidden, **prior)
    model.load_state_dict(state, strict=True)
    if not all(bool(torch.isfinite(value).all()) for value in model.state_dict().values()):
        raise ValueError("Nonfinite checkpoint tensor")
    return model.to(device), bundle, digest


def make_bc_bundle(
    model,
    *,
    base_checkpoint_sha256: str,
    dataset_audit_sha256: str,
    config: dict,
    metrics: dict,
    lineage: dict | None = None,
) -> dict:
    state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
    return dict(
        format=BC_FORMAT,
        schema=SCHEMA,
        encoder_version=encoder.ENCODER_VERSION,
        architecture_version=ARCHITECTURE_VERSION,
        state_dim=encoder.STATE_DIM,
        candidate_dim=model.candidate_dim,
        catalog_sha256=CATALOG_SHA256,
        hidden=model.hidden,
        prior_config=dict(
            prior_scale=float(model.prior_scale.detach().cpu()),
            prior_feature_index=13,
            build_bias=float(model.actor.build_bias.detach().cpu()),
            recruit_bias=float(model.actor.recruit_bias.detach().cpu()),
            catalog_size=model.catalog_size,
        ),
        state_dict=state,
        base_checkpoint_sha256=base_checkpoint_sha256,
        dataset_audit_sha256=dataset_audit_sha256,
        bc_config=config,
        metrics=metrics,
        lineage=lineage or {},
        policy_tensor_sha256=tensor_sha(state),
    )


def validate_bc_bundle(bundle: dict):
    required = {
        "format", "schema", "encoder_version", "architecture_version", "state_dim",
        "candidate_dim", "catalog_sha256", "hidden", "prior_config", "state_dict",
        "base_checkpoint_sha256", "dataset_audit_sha256", "bc_config", "metrics",
        "lineage", "policy_tensor_sha256",
    }
    if not isinstance(bundle, dict) or set(bundle) != required:
        raise ValueError("Exact BC checkpoint keys required")
    if bundle["format"] != BC_FORMAT:
        raise ValueError("Not a BC checkpoint")
    if bundle["catalog_sha256"] != CATALOG_SHA256:
        raise ValueError("BC catalog mismatch")
    if bundle["encoder_version"] != encoder.ENCODER_VERSION:
        raise ValueError("BC encoder mismatch")
    if bundle["architecture_version"] != ARCHITECTURE_VERSION:
        raise ValueError("BC architecture mismatch")
    if bundle["state_dim"] != encoder.STATE_DIM:
        raise ValueError("BC state dimension mismatch")
    if bundle["candidate_dim"] != encoder.CANDIDATE_DIM + len(load_catalog()["ids"]):
        raise ValueError("BC candidate dimension mismatch")
    if tensor_sha(bundle["state_dict"]) != bundle["policy_tensor_sha256"]:
        raise ValueError("BC tensor digest mismatch")
    if not all(bool(torch.isfinite(value).all()) for value in bundle["state_dict"].values()):
        raise ValueError("Nonfinite BC tensor")
    return bundle


def read_jsonl(path: Path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: invalid JSON: {error}") from error
    return rows


def write_json(path: Path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    os.replace(temporary, path)
