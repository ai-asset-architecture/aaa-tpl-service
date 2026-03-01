from __future__ import annotations

from typing import Dict

from src.ops_registry import (
    build_default_config,
    detect_capability_state,
    get_version_detail,
    get_versions,
    get_workflows,
)


def health() -> dict:
    return {"status": "ok"}


def get_ops_capabilities() -> Dict[str, object]:
    state = detect_capability_state()
    return {
        "operate_maintain_workflow_v2": {
            "enabled": state.enabled,
            "reason": state.reason,
        }
    }


def _ensure_enabled() -> None:
    state = detect_capability_state()
    if not state.enabled:
        raise PermissionError("operate_maintain_workflow_v2 capability is disabled")


def get_ops_registry_versions() -> Dict[str, object]:
    _ensure_enabled()
    cfg = build_default_config()
    return get_versions(cfg)


def get_ops_registry_workflows() -> Dict[str, object]:
    _ensure_enabled()
    cfg = build_default_config()
    return get_workflows(cfg)


def get_ops_version_detail(version: str) -> Dict[str, object]:
    _ensure_enabled()
    cfg = build_default_config()
    return get_version_detail(cfg, version)


try:
    from fastapi import FastAPI, HTTPException

    app = FastAPI(title="AAA Ops Capability Service", version="0.1.0")

    @app.get("/health")
    def api_health() -> Dict[str, str]:
        return health()

    @app.get("/api/ops/capabilities")
    def api_capabilities() -> Dict[str, object]:
        return get_ops_capabilities()

    @app.get("/api/ops/registry/versions")
    def api_versions() -> Dict[str, object]:
        try:
            return get_ops_registry_versions()
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/ops/registry/workflows")
    def api_workflows() -> Dict[str, object]:
        try:
            return get_ops_registry_workflows()
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/ops/version/{version}")
    def api_version_detail(version: str) -> Dict[str, object]:
        try:
            return get_ops_version_detail(version)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

except Exception:
    app = None
