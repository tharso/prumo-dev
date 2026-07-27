"""MAPA-AUTORAL.md (#241) — o arquivo autoral que soma caminhos ao perímetro.

Contratos testados:
1. paridade: o esqueleto do caminho manual (`file-templates.md`) é IDÊNTICO ao
   do runtime (`render_mapa_autoral_md`) — dois setups, um só esqueleto;
2. o setup cria o esqueleto (categoria authorial);
3. o `repair` preserva conteúdo editado byte a byte (é o critério 2 do épico
   #240: update+repair não desfazem a declaração do usuário);
4. o `repair` REPORTA ausência sem recriar — usuário que deletou o mapa não o
   vê ressuscitar (mesmo tratamento dos irmãos do `Agente/`, exceto PERFIL).
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "runtime"))

from prumo_runtime import templates  # noqa: E402
from prumo_runtime.workspace import (  # noqa: E402
    WorkspaceConfig,
    create_missing_files,
    ensure_directories,
    install_skills,
    repair_workspace,
)

FILE_TEMPLATES = REPO_ROOT / "skills" / "prumo" / "references" / "file-templates.md"


def _make_test_workspace(parent: Path) -> Path:
    workspace = parent / "test-ws"
    config = WorkspaceConfig(
        workspace=workspace,
        user_name="Test User",
        agent_name="Prumo",
        timezone_name="America/Sao_Paulo",
        briefing_time="09:00",
        layout_mode="nested",
        workspace_name="Test Workspace",
    )
    ensure_directories(workspace)
    install_skills(workspace, layout_mode="nested")
    create_missing_files(config)
    return workspace


class MapaAutoralTests(unittest.TestCase):
    def test_esqueleto_manual_identico_ao_renderer(self) -> None:
        text = FILE_TEMPLATES.read_text(encoding="utf-8")
        m = re.search(
            r"## Prumo/Agente/MAPA-AUTORAL\.md.*?--- INÍCIO ---\n(.*?)\n--- FIM ---",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "seção do MAPA-AUTORAL sumiu do file-templates.md")
        manual = m.group(1).strip()
        rendered = templates.render_mapa_autoral_md().strip()
        self.assertEqual(
            manual, rendered,
            "esqueleto do caminho manual divergiu do renderer — dois setups, dois produtos",
        )

    def test_setup_cria_o_esqueleto(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_test_workspace(Path(tmpdir))
            mapa = ws / "Prumo" / "Agente" / "MAPA-AUTORAL.md"
            self.assertTrue(mapa.exists())
            self.assertIn("Mapa autoral", mapa.read_text(encoding="utf-8"))

    def test_repair_preserva_conteudo_editado_byte_a_byte(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_test_workspace(Path(tmpdir))
            mapa = ws / "Prumo" / "Agente" / "MAPA-AUTORAL.md"
            autoral = (
                "# Mapa autoral\n\n- `Escrita/` — trabalho autoral; contrato em Escrita/README.md\n"
                "- `Estudos/` — anotações de curso\n"
            )
            mapa.write_text(autoral, encoding="utf-8")
            repair_workspace(ws)
            self.assertEqual(
                mapa.read_text(encoding="utf-8"), autoral,
                "repair tocou o MAPA-AUTORAL — a declaração do usuário tem de sobreviver",
            )

    def test_primeiro_repair_com_schema_legado_ja_reporta(self) -> None:
        """[P1 da r1 do gate]: workspace vindo de versão sem o mapa (schema
        legado não o lista) tem de REPORTAR a ausência já no PRIMEIRO repair —
        não na segunda rodada, depois de o schema atualizar. E nunca recriar."""
        import json
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_test_workspace(Path(tmpdir))
            rel = "Prumo/Agente/MAPA-AUTORAL.md"
            (ws / rel).unlink()
            schema_path = ws / ".prumo" / "state" / "workspace-schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["files"]["authorial"] = [
                f for f in schema["files"]["authorial"] if f != rel
            ]
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            result = repair_workspace(ws)
            self.assertIn(rel, result["missing_authorial"])
            self.assertFalse((ws / rel).exists(), "repair recriou autoral de schema legado")

    def test_repair_reporta_ausencia_sem_recriar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_test_workspace(Path(tmpdir))
            mapa = ws / "Prumo" / "Agente" / "MAPA-AUTORAL.md"
            mapa.unlink()
            result = repair_workspace(ws)
            self.assertFalse(
                mapa.exists(), "repair recriou o MAPA-AUTORAL deletado pelo usuário"
            )
            self.assertIn("Prumo/Agente/MAPA-AUTORAL.md", result["missing_authorial"])
            self.assertNotIn("Prumo/Agente/MAPA-AUTORAL.md", result["recreated"])


if __name__ == "__main__":
    unittest.main()
