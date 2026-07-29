"""Guard de layout na porta pública dos comandos (#268).

O atalho `(workspace / ".prumo").is_dir()` — herdado da #179 — pergunta "isto é
um workspace?" olhando um caminho que só existe no layout NESTED. No FLAT a
infra mora em `_state/`/`_logs/` e o core na raiz, então a resposta era sempre
"não" e a CLI recusava workspace legítimo.

A #263 tornou o defeito visível: o `/fim` passou a contar `rascunho_old` nos
dois roots e a recomendar `sanitize`, mas a CLI recusava — o painel
recomendando o que a ferramenta não executa.

A lacuna que deixou isso passar por tanto tempo é de teste, não de código: os
testes de flat chamam `build_plan()` direto e nunca atravessam `run_sanitize`.
Estes testes entram pela PORTA PÚBLICA (`cli.main`), nos dois layouts.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from prumo_runtime.cli import main
from prumo_runtime.commands.update import workspace_core_status
from prumo_runtime.workspace_paths import is_prumo_workspace

_SCHEMA = json.dumps(
    {
        "user_name": "Batata",
        "agent_name": "Prumo",
        "timezone": "America/Sao_Paulo",
        "briefing_time": "09:00",
        "files": {"generated": [], "authorial": [], "derived": []},
    }
)

# Fixture deliberadamente antiga e fixa: estes testes checam se o core é
# ENXERGADO, não qual versão ele declara. Casar com a versão real do repo
# criaria manutenção a cada bump sem cobrir nada a mais.
_CORE = "> **prumo_version: 5.0.0**\n"


def _flat_workspace(root: Path) -> Path:
    """Workspace flat legítimo: infra em `_state/`, core na raiz."""
    (root / "_state").mkdir(parents=True, exist_ok=True)
    (root / "_logs").mkdir(parents=True, exist_ok=True)
    (root / "_state" / "workspace-schema.json").write_text(_SCHEMA, encoding="utf-8")
    (root / "PRUMO-CORE.md").write_text(_CORE, encoding="utf-8")
    (root / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
    (root / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
    return root


def _nested_workspace(root: Path) -> Path:
    """Workspace nested legítimo: infra em `.prumo/`, usuário em `Prumo/`."""
    (root / ".prumo" / "state").mkdir(parents=True, exist_ok=True)
    (root / ".prumo" / "system").mkdir(parents=True, exist_ok=True)
    (root / "Prumo").mkdir(parents=True, exist_ok=True)
    (root / ".prumo" / "state" / "workspace-schema.json").write_text(_SCHEMA, encoding="utf-8")
    (root / ".prumo" / "system" / "PRUMO-CORE.md").write_text(_CORE, encoding="utf-8")
    (root / "Prumo" / "AGENT.md").write_text("# AGENT\n", encoding="utf-8")
    return root


def _run(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        rc = main(argv)
    return rc, buffer.getvalue()


class WorkspaceMarkerTests(unittest.TestCase):
    """O critério de 'isto é um workspace do Prumo' precisa valer nos dois layouts."""

    def test_workspace_nested_e_reconhecido(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(is_prumo_workspace(_nested_workspace(Path(tmp))))

    def test_workspace_flat_e_reconhecido(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(is_prumo_workspace(_flat_workspace(Path(tmp))))

    def test_pasta_qualquer_nao_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text("nada aqui\n", encoding="utf-8")
            self.assertFalse(is_prumo_workspace(Path(tmp)))

    def test_pasta_inexistente_nao_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(is_prumo_workspace(Path(tmp) / "nao-existe"))

    def test_subpasta_Prumo_sem_marcador_nao_basta(self) -> None:
        """A proteção real do guard: repo alheio com uma pasta `Prumo/` dentro
        não vira workspace só por causa do nome (mesma armadilha que o
        `detect_nested_layout` já trata)."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Prumo").mkdir()
            (Path(tmp) / "Prumo" / "README.md").write_text("projeto alheio\n", encoding="utf-8")
            self.assertFalse(is_prumo_workspace(Path(tmp)))


class SanitizeCliDoorTests(unittest.TestCase):
    """Critério 1 e 2 da #268, pela porta pública."""

    def test_sanitize_roda_em_workspace_flat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            rc, out = _run(["sanitize", "--workspace", str(ws)])
        self.assertEqual(rc, 0, f"sanitize recusou workspace flat legítimo:\n{out}")
        self.assertNotIn("nada a sanitizar aqui", out)

    def test_sanitize_roda_em_workspace_nested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_workspace(Path(tmp))
            rc, out = _run(["sanitize", "--workspace", str(ws)])
        self.assertEqual(rc, 0, f"regressão no nested:\n{out}")

    def test_sanitize_recusa_pasta_que_nao_e_workspace(self) -> None:
        """A proteção não pode ser perdida na troca do critério."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text("nada aqui\n", encoding="utf-8")
            rc, out = _run(["sanitize", "--workspace", tmp])
        self.assertEqual(rc, 1)
        self.assertIn("nada a sanitizar aqui", out)

    def test_recusa_nao_fala_de_caminho_que_o_layout_nao_tem(self) -> None:
        """Mensagem que cita `.prumo/` num flat manda o usuário procurar pasta
        que não existe no layout dele."""
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = _run(["sanitize", "--workspace", tmp])
        self.assertEqual(rc, 1)
        self.assertNotIn("`.prumo/`", out)


class SeedCliDoorTests(unittest.TestCase):
    """`prumo seed` carrega o snapshot dos curados (#262) e tinha o MESMO
    atalho: no flat o snapshot simplesmente nunca acontecia."""

    def test_seed_nao_recusa_workspace_flat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            rc, out = _run(["seed", "--workspace", str(ws)])
        self.assertEqual(rc, 0, f"seed recusou workspace flat legítimo:\n{out}")
        self.assertNotIn("nada a semear aqui", out)

    def test_seed_recusa_pasta_que_nao_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = _run(["seed", "--workspace", tmp])
        self.assertEqual(rc, 1)
        self.assertIn("nada a semear aqui", out)


class UpdateCoreStatusTests(unittest.TestCase):
    """`workspace_core_status` some no flat: o `--check` escondia workspace
    defasado atrás de runtime em dia, que é exatamente o que ele existe pra
    evitar (#170)."""

    def test_enxerga_core_do_workspace_flat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            self.assertIsNotNone(workspace_core_status(ws, "5.99.0"))

    def test_ignora_pasta_que_nao_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(workspace_core_status(Path(tmp), "5.99.0"))


if __name__ == "__main__":
    unittest.main()
