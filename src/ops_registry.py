from __future__ import annotations

import os
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
    return {
        "source": data["source"],
        "updated_at_taipei": data["updated_at_taipei"],
        "version": version,
        "item": item,
    }
