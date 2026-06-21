"""Cadeia de inferência de identidade do workspace (Fase 2 da #97).

`infer_user_name()` resolve o nome do usuário nesta ordem:
  1. schema (`workspace-schema.json` -> `user_name`);
  2. `Prumo/AGENT.md` (`- Nome preferido do usuário:`) — fonte canônica;
  3. `Prumo/Agente/INDEX.md` (`- Nome preferido:`) — só compat legado;
  4. None -> `build_config_from_existing()` levanta WorkspaceError legível.

O fallback pelo INDEX existe apenas para workspaces antigos; o caminho
canônico é o AGENT.md. Ver #97 (aposentadoria do INDEX como mapa).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from prumo_runtime.workspace import (
    WorkspaceConfig,
    WorkspaceError,
    build_config_from_existing,
    create_missing_files,
    ensure_directories,
    infer_user_name,
    install_skills,
)
from prumo_runtime.workspace_paths import workspace_paths


def _make_workspace(parent: Path, user_name: str = "Base User") -> Path:
    workspace = parent / "ws"
    config = WorkspaceConfig(
        workspace=workspace,
        user_name=user_name,
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


def _strip_schema_user_name(workspace: Path) -> None:
    schema_path = workspace_paths(workspace).workspace_schema
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    data.pop("user_name", None)
    schema_path.write_text(json.dumps(data), encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class IdentityInferenceTest(unittest.TestCase):
    def test_schema_user_name_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp), user_name="Schema Name")
            paths = workspace_paths(ws)
            _write(paths.canonical_agent, "# AGENT.md\n- Nome preferido do usuário: Agent Name\n")
            _write(paths.agent_index, "# Índice\n- Nome preferido: Index Name\n")
            self.assertEqual(infer_user_name(ws), "Schema Name")

    def test_agent_md_fallback_when_no_schema_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            _strip_schema_user_name(ws)
            paths = workspace_paths(ws)
            _write(paths.canonical_agent, "# AGENT.md\n- Nome preferido do usuário: Batata\n")
            if paths.agent_index.exists():
                paths.agent_index.unlink()
            self.assertEqual(infer_user_name(ws), "Batata")

    def test_legacy_index_fallback_when_no_agent_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            _strip_schema_user_name(ws)
            paths = workspace_paths(ws)
            _write(paths.canonical_agent, "# AGENT.md\n(sem linha de nome aqui)\n")
            _write(paths.agent_index, "# Índice antigo\n\n## Identidade\n\n- Nome preferido: Legado\n")
            self.assertEqual(infer_user_name(ws), "Legado")

    def test_no_source_returns_none_and_build_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(Path(tmp))
            _strip_schema_user_name(ws)
            paths = workspace_paths(ws)
            _write(paths.canonical_agent, "# AGENT.md\n(sem nome)\n")
            if paths.agent_index.exists():
                paths.agent_index.unlink()
            self.assertIsNone(infer_user_name(ws))
            with self.assertRaises(WorkspaceError):
                build_config_from_existing(ws)


if __name__ == "__main__":
    unittest.main()
