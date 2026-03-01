from pathlib import Path

import pytest

from src.main import (
    get_ops_capabilities,
    get_ops_registry_versions,
    get_ops_registry_workflows,
    get_ops_version_detail,
)
from src.ops_registry import (
    OpsSourceConfig,
    get_version_detail,
    get_versions,
    get_workflows,
)


def _write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_parse_versions_and_workflows(tmp_path: Path):
    version_index = tmp_path / "version_index.md"
    workflow_index = tmp_path / "workflow_index.md"

    _write_file(
        version_index,
        """# Version Index\n\n- updated_at_taipei: 2026-03-01T00:00:00+08:00\n\n| 日期 | 版本 | 名稱 | 意義 | 為何要做 | 版本落地處 | 狀態 | 可用性驗證 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| 2026-03-01 | v1.0.0 | Demo | 目的A | 原因A | ui:demo | PLANNED_STEP2 | run_ref=N/A |\n""",
    )

    _write_file(
        workflow_index,
        """# Workflow Index\n\n- updated_at_taipei: 2026-03-01T00:00:00+08:00\n\n| 日期 | ID | 工作流程 | 目的 | 目標 | 場合 | 觸發時機 | 模式 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| 2026-03-01 | .github/workflows/demo.yml | Demo WF | P | T | S | manual | manual |\n""",
    )

    cfg = OpsSourceConfig(version_index_path=version_index, workflow_index_path=workflow_index)

    versions = get_versions(cfg)
    assert versions["count"] == 1
    assert versions["items"][0]["version"] == "v1.0.0"

    workflows = get_workflows(cfg)
    assert workflows["count"] == 1
    assert workflows["items"][0]["workflow"] == "Demo WF"

    detail = get_version_detail(cfg, "v1.0.0")
    assert detail["item"]["name"] == "Demo"


def test_capability_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AAA_ENABLE_OPERATE_MAINTAIN_WORKFLOW_V2", raising=False)
    caps = get_ops_capabilities()
    assert caps["operate_maintain_workflow_v2"]["enabled"] is False


@pytest.mark.parametrize("enabled_value", ["1", "true", "on", "enabled"])
def test_capability_enabled_blocks_removed(monkeypatch, enabled_value):
    monkeypatch.setenv("AAA_ENABLE_OPERATE_MAINTAIN_WORKFLOW_V2", enabled_value)
    caps = get_ops_capabilities()
    assert caps["operate_maintain_workflow_v2"]["enabled"] is True


def test_registry_apis_require_capability(monkeypatch):
    monkeypatch.delenv("AAA_ENABLE_OPERATE_MAINTAIN_WORKFLOW_V2", raising=False)
    with pytest.raises(PermissionError):
        get_ops_registry_versions()
    with pytest.raises(PermissionError):
        get_ops_registry_workflows()
    with pytest.raises(PermissionError):
        get_ops_version_detail("v1.0.0")
