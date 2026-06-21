"""Aposentadoria do `Agente/INDEX.md` no runtime (Fase 2 da #97).

Setup novo não gera mais o INDEX; o schema não o lista como autoral; repair
não o recria; overview não o reporta como ausente. Workspaces com schema
antigo (que ainda listava o INDEX) são normalizados sem falso "missing".
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from prumo_runtime.workspace import (
    WorkspaceConfig,
    create_missing_files,
    ensure_directories,
    install_skills,
    read_schema,
    repair_workspace,
    workspace_overview,
)
from prumo_runtime.workspace_paths import workspace_paths

_INDEX_REL = "Prumo/Agente/INDEX.md"


def _make_workspace(parent: Path) -> Path:
    workspace = parent / "ws"
    config = WorkspaceConfig(
        workspace=workspace,
        user_name="Test User",
        agent_name="Prumo",
        timezone_name="America/Sao_Paulo",
        briefing_time="09:00",
        layout_mode="nested",
        workspace_name="Test",
    )
    ensure_directories(workspace)
    install_skills(workspace, layout_mode="nested")
    create_missing_files(config)
    return workspace


class IndexRetirementTest(unittest.TestCase):
    def test_fresh_setup_does_not_create_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            paths = workspace_paths(ws)
            self.assertFalse(paths.agent_index.exists())
            self.assertTrue(paths.canonical_agent.exists())

    def test_schema_authorial_excludes_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            authorial = read_schema(ws)["files"]["authorial"]
            self.assertNotIn(_INDEX_REL, authorial)

    def test_repair_does_not_recreate_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            paths = workspace_paths(ws)
            result = repair_workspace(ws)
            self.assertFalse(paths.agent_index.exists())
            self.assertNotIn(_INDEX_REL, result["missing_authorial"])

    def test_overview_does_not_flag_index_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            overview = workspace_overview(ws)
            self.assertNotIn(_INDEX_REL, overview["missing"]["authorial"])

    def test_legacy_schema_listing_index_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            paths = workspace_paths(ws)
            # Schema antigo que ainda lista o INDEX como autoral, sem o arquivo no disco.
            schema = read_schema(ws)
            schema["files"]["authorial"] = [_INDEX_REL, *schema["files"]["authorial"]]
            paths.workspace_schema.write_text(json.dumps(schema), encoding="utf-8")
            result = repair_workspace(ws)
            self.assertFalse(paths.agent_index.exists())
            self.assertNotIn(_INDEX_REL, result["missing_authorial"])
            self.assertNotIn(_INDEX_REL, read_schema(ws)["files"]["authorial"])


if __name__ == "__main__":
    unittest.main()
