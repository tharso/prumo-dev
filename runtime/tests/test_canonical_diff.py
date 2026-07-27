"""Aviso de perda no mapa do canonical (#247).

"Backup que ninguém lê é lixo com data": o repair regenera o `AGENT.md` e o
que o usuário tinha adicionado ao mapa some em silêncio. Estes testes travam a
identidade por PATH (release que só muda descrição não dispara), o aviso neutro
(o runtime não atribui autoria que não conhece) e o fail-safe.
"""

from __future__ import annotations

import io
import re
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "runtime"))

from prumo_runtime import canonical_diff  # noqa: E402
from prumo_runtime.commands.repair import run_repair  # noqa: E402
from prumo_runtime.workspace import (  # noqa: E402
    WorkspaceConfig,
    create_missing_files,
    ensure_directories,
    install_skills,
    repair_workspace,
)

_MAP = """# AGENT

## Mapa do workspace

- `Agente/`: contexto modular
- `PAUTA.md`: estado vivo
- `Escrita/`: meu trabalho autoral

## Outra seção

- `Ignorado.md`: fora do mapa
"""


def _make_ws(parent: Path) -> Path:
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


def _force_core_version(workspace: Path, version: str) -> None:
    core = workspace / ".prumo" / "system" / "PRUMO-CORE.md"
    text = core.read_text(encoding="utf-8")
    core.write_text(
        re.sub(r"prumo_version:\s*[0-9.]+", f"prumo_version: {version}", text, count=1),
        encoding="utf-8",
    )


class MapExtractionTest(unittest.TestCase):
    def test_paths_do_mapa_param_no_proximo_heading(self) -> None:
        paths = canonical_diff.map_paths(_MAP)
        self.assertEqual(paths, ["Agente/", "PAUTA.md", "Escrita/"])

    def test_descricao_alterada_nao_e_perda(self) -> None:
        """[P7-1]: identidade é o PATH — release que muda a prosa não alarma."""
        novo = _MAP.replace("`PAUTA.md`: estado vivo", "`PAUTA.md`: pendências e estado")
        self.assertEqual(canonical_diff.dropped_paths(_MAP, novo), [])

    def test_path_removido_aparece(self) -> None:
        novo = _MAP.replace("- `Escrita/`: meu trabalho autoral\n", "")
        self.assertEqual(canonical_diff.dropped_paths(_MAP, novo), ["Escrita/"])

    def test_sem_secao_no_antigo_nao_inventa_alarme(self) -> None:
        self.assertEqual(canonical_diff.dropped_paths("# AGENT\n\nsem mapa\n", _MAP), [])

    def test_heading_duplicado_e_fail_safe(self) -> None:
        duplicado = _MAP + "\n## Mapa do workspace\n\n- `Outro.md`: duplicado\n"
        self.assertEqual(canonical_diff.map_paths(duplicado), ["Agente/", "PAUTA.md", "Escrita/"])


class RepairAvisoTest(unittest.TestCase):
    def _repair_com_drift(self, extra_bullet: str | None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_ws(Path(tmp))
            canonical = ws / "Prumo" / "AGENT.md"
            if extra_bullet:
                text = canonical.read_text(encoding="utf-8")
                canonical.write_text(
                    text.replace(
                        "- `Agente/`:", f"{extra_bullet}\n- `Agente/`:", 1
                    ),
                    encoding="utf-8",
                )
            _force_core_version(ws, "1.0.0")
            return repair_workspace(ws)

    def test_caminho_autoral_no_mapa_vira_aviso(self) -> None:
        result = self._repair_com_drift("- `Escrita/`: meu trabalho autoral")
        self.assertIn("Escrita/", result.get("canonical_map_dropped", []))

    def test_mapa_de_template_puro_nao_avisa(self) -> None:
        result = self._repair_com_drift(None)
        self.assertEqual(result.get("canonical_map_dropped"), [])

    def test_repair_sem_drift_nao_traz_o_campo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_ws(Path(tmp))
            result = repair_workspace(ws)
        self.assertNotIn("canonical_map_dropped", result)

    def test_saida_humana_traz_o_aviso_e_o_destino_certo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_ws(Path(tmp))
            canonical = ws / "Prumo" / "AGENT.md"
            canonical.write_text(
                canonical.read_text(encoding="utf-8").replace(
                    "- `Agente/`:", "- `Escrita/`: autoral\n- `Agente/`:", 1
                ),
                encoding="utf-8",
            )
            _force_core_version(ws, "1.0.0")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_repair(Namespace(workspace=str(ws), format="text"))
            out = buffer.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("não aparecem no mapa regenerado", out)
        self.assertIn("- Escrita/", out)
        self.assertIn("MAPA-AUTORAL.md", out)


if __name__ == "__main__":
    unittest.main()
