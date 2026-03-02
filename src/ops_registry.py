from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


VERSION_HEADER_MAP = {
    "日期": "date",
    "版本": "version",
    "名稱": "name",
    "意義": "meaning",
    "為何要做": "why",
    "版本落地處": "landing",
    "狀態": "status",
    "可用性驗證": "availability_verification",
}

WORKFLOW_HEADER_MAP = {
    "日期": "date",
    "ID": "id",
    "工作流程": "workflow",
    "目的": "purpose",
    "目標": "target",
    "場合": "scenario",
    "觸發時機": "trigger",
    "模式": "mode",
}


@dataclass
class OpsSourceConfig:
    version_index_path: Path
    workflow_index_path: Path


@dataclass
class CapabilityState:
    enabled: bool
    reason: str


def _to_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def detect_capability_state() -> CapabilityState:
    enabled = _to_bool(os.getenv("AAA_ENABLE_OPERATE_MAINTAIN_WORKFLOW_V2"))
    if enabled:
        return CapabilityState(enabled=True, reason="env_enabled")
    return CapabilityState(enabled=False, reason="capability_not_enabled")


def build_default_config() -> OpsSourceConfig:
    root = Path(os.getenv("AAA_WORKSPACE", "")).expanduser()
    if root and root.exists():
        base = root
    else:
        base = Path(__file__).resolve().parents[3]
    return OpsSourceConfig(
        version_index_path=base / "aaa-tpl-docs" / "version_index.md",
        workflow_index_path=base / "aaa-tpl-docs" / "workflow_index.md",
    )


def _extract_updated_at(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- updated_at_taipei:"):
            return stripped.split(":", 1)[1].strip()
    return "unknown"


def _split_table_row(line: str) -> List[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    parts = [p.strip() for p in stripped.strip("|").split("|")]
    return parts


def _parse_markdown_table(content: str, required_headers: Dict[str, str]) -> List[Dict[str, str]]:
    lines = content.splitlines()
    header_idx = None
    headers: List[str] = []

    for i, line in enumerate(lines):
        row = _split_table_row(line)
        if not row:
            continue
        row_set = set(row)
        if set(required_headers.keys()).issubset(row_set):
            header_idx = i
            headers = row
            break

    if header_idx is None or header_idx + 2 >= len(lines):
        return []

    mapped_headers = [required_headers.get(h, h) for h in headers]
    data_rows: List[Dict[str, str]] = []

    for line in lines[header_idx + 2 :]:
        row = _split_table_row(line)
        if not row:
            break
        if len(row) < len(mapped_headers):
            row += [""] * (len(mapped_headers) - len(row))
        if len(row) > len(mapped_headers):
            row = row[: len(mapped_headers)]
        item = {mapped_headers[idx]: row[idx] for idx in range(len(mapped_headers))}
        data_rows.append(item)

    return data_rows


def _load_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


_RUN_REF_RE = re.compile(r"^gh-actions:([^@]+)@([^#]+)#([0-9]+)")


def _parse_availability_verification(raw: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    if not raw:
        return parsed
    for segment in raw.split(";"):
        part = segment.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _split_csv_paths(raw: str) -> List[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _classify_step(path: str) -> str:
    normalized = path.strip()
    if not normalized:
        return "unknown"
    if (
        "/completion-reports/" in normalized
        or "step4-" in normalized
        or normalized.endswith("-step4-exit-checklist.md")
    ):
        return "step4"
    if "/milestones/" in normalized or normalized.endswith("-step3-exit-checklist.md"):
        return "step3"
    if (
        "/evidence/" in normalized
        or "run-evidence" in normalized
        or "version-dashboard/" in normalized
        or "ops_version_list.v0.1.json" in normalized
        or normalized.endswith("-step2-exit-checklist.md")
    ):
        return "step2"
    if (
        normalized.startswith("docs/plans/")
        or normalized.startswith("docs/audits/")
        or normalized.startswith("docs/reviews/")
        or normalized.startswith("docs/contracts/")
        or normalized.startswith("scripts/gates/")
        or normalized.startswith(".github/workflows/")
        or normalized.endswith("-step1-exit-checklist.md")
    ):
        return "step1"
    return "unknown"


def _run_ref_to_url(run_ref: str) -> Optional[str]:
    match = _RUN_REF_RE.match(run_ref)
    if not match:
        return None
    repo = match.group(1)
    run_id = match.group(3)
    return f"https://github.com/{repo}/actions/runs/{run_id}"


def _step_status(step: str, artifacts: List[str], run_ref: str, top_status: str) -> str:
    if step == "step1":
        return "COMPLETED" if artifacts else "UNVERIFIED"
    if step == "step2":
        if run_ref and run_ref != "N/A (step2-pending)":
            return "COMPLETED"
        if top_status in {"COMPLETED", "BRIDGE_ONLY"} and artifacts:
            return "COMPLETED"
        return "UNVERIFIED"
    if step == "step3":
        return "COMPLETED" if artifacts else "N/A"
    if step == "step4":
        return "COMPLETED" if artifacts else "N/A"
    return "UNVERIFIED"


def _build_step_view(item: Optional[Dict[str, str]]) -> Dict[str, object]:
    labels = {
        "step1": "Step1 契約基線",
        "step2": "Step2 實作與執行",
        "step3": "Step3 資產保存",
        "step4": "Step4 結案交付",
    }
    steps: Dict[str, Dict[str, object]] = {
        key: {"title": labels[key], "status": "UNVERIFIED", "artifacts": []}
        for key in ["step1", "step2", "step3", "step4"]
    }
    if not item:
        return steps

    parsed = _parse_availability_verification(item.get("availability_verification", ""))
    paths = _split_csv_paths(parsed.get("evidence", ""))
    run_ref = parsed.get("run_ref", "")
    top_status = item.get("status", "")

    for path in paths:
        bucket = _classify_step(path)
        if bucket in steps:
            steps[bucket]["artifacts"].append(path)

    if run_ref:
        steps["step2"]["run_ref"] = run_ref
        run_url = _run_ref_to_url(run_ref)
        if run_url:
            steps["step2"]["run_url"] = run_url

    for step_name, view in steps.items():
        artifacts = view.get("artifacts", [])
        view["artifact_count"] = len(artifacts)
        view["status"] = _step_status(step_name, artifacts, run_ref, top_status)

    criteria_ref = parsed.get("criteria")
    note = parsed.get("note")
    if criteria_ref:
        steps["step1"]["criteria_ref"] = criteria_ref
    if note:
        steps["step1"]["note"] = note

    return steps


def get_versions(config: OpsSourceConfig) -> Dict[str, object]:
    content = _load_file(config.version_index_path)
    items = _parse_markdown_table(content, VERSION_HEADER_MAP)
    return {
        "source": str(config.version_index_path),
        "updated_at_taipei": _extract_updated_at(content),
        "count": len(items),
        "items": items,
    }


def get_workflows(config: OpsSourceConfig) -> Dict[str, object]:
    content = _load_file(config.workflow_index_path)
    items = _parse_markdown_table(content, WORKFLOW_HEADER_MAP)
    return {
        "source": str(config.workflow_index_path),
        "updated_at_taipei": _extract_updated_at(content),
        "count": len(items),
        "items": items,
    }


def get_version_detail(config: OpsSourceConfig, version: str) -> Dict[str, object]:
    data = get_versions(config)
    item = next((row for row in data["items"] if row.get("version") == version), None)
    availability = _parse_availability_verification(
        item.get("availability_verification", "") if item else ""
    )
    return {
        "source": data["source"],
        "updated_at_taipei": data["updated_at_taipei"],
        "version": version,
        "item": item,
        "availability": availability,
        "steps": _build_step_view(item),
    }
