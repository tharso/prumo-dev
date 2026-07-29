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
from prumo_runtime.workspace_paths import is_legacy_flat_workspace, is_prumo_workspace

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


class MarcadorDiscriminaTests(unittest.TestCase):
    """Um marcador POR VEZ (Codex, r1).

    A fixture completa de `_flat_workspace` tem `_state`, `_logs`, schema, core,
    AGENT e PAUTA — com ela, uma implementação que olhasse só `_logs/` passaria
    em todos os testes positivos. Aqui cada caso isola exatamente um marcador,
    e os negativos provam o que NÃO pode bastar.
    """

    def test_flat_so_com_schema_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_state").mkdir()
            (root / "_state" / "workspace-schema.json").write_text(_SCHEMA, encoding="utf-8")
            self.assertTrue(is_prumo_workspace(root))

    def test_flat_so_com_core_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "PRUMO-CORE.md").write_text(_CORE, encoding="utf-8")
            self.assertTrue(is_prumo_workspace(root))

    def test_flat_so_com_logs_NAO_e_workspace(self) -> None:
        """O buraco crítico da rodada 1: `_logs/` é nome que qualquer projeto
        tem. Aceitá-lo faria `prumo update` rodar `repair` automático
        (update.py:742) dentro de projeto alheio."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_logs").mkdir()
            self.assertFalse(is_prumo_workspace(root))

    def test_flat_so_com_state_NAO_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_state").mkdir()
            self.assertFalse(is_prumo_workspace(root))

    def test_nested_so_com_prumo_dir_e_workspace(self) -> None:
        """A tolerância a infra parcial sobrevive SÓ no nested, porque
        `.prumo/` é nome exclusivo do Prumo. É comportamento herdado do atalho
        antigo e preservado de propósito."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".prumo").mkdir()
            self.assertTrue(is_prumo_workspace(root))

    def test_marcador_que_e_symlink_nao_vale(self) -> None:
        """Symlink pra fora faria o repair disparado pelo update escrever fora
        do workspace."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as fora:
            alvo = Path(fora) / "schema-de-fora.json"
            alvo.write_text(_SCHEMA, encoding="utf-8")
            root = Path(tmp)
            (root / "_state").mkdir()
            (root / "_state" / "workspace-schema.json").symlink_to(alvo)
            self.assertFalse(is_prumo_workspace(root))

    def test_marcador_que_e_diretorio_nao_vale(self) -> None:
        """`.exists()` é True pra diretório: o critério precisa validar
        artefato, não nome."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "PRUMO-CORE.md").mkdir()
            self.assertFalse(is_prumo_workspace(root))

    def test_core_na_posicao_flat_nao_vale_quando_o_layout_e_nested(self) -> None:
        """Porteiro que aceita e manda pro prédio errado: com uma subpasta
        `Prumo/` incidental o layout detectado é nested, e os consumidores vão
        usar caminhos nested. Aceitar o core na posição flat deixaria entrar um
        workspace que ninguém consegue ler direito."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Prumo").mkdir()
            (root / "PRUMO-CORE.md").write_text(_CORE, encoding="utf-8")
            self.assertFalse(is_prumo_workspace(root))


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


class EscritaNoFlatParaTests(unittest.TestCase):
    """Decisão do dono (29/07, #268): no flat a LEITURA funciona e a ESCRITA
    para, oferecendo `prumo migrate`.

    O motivo é concreto: os destinos de escrita do runtime — archive, backups,
    journal, semente, snapshot dos curados — são `.prumo/` literal. Deixar
    gravar num flat criaria uma árvore `.prumo/` DENTRO dele, misturando os
    dois layouts na mesma pasta. Recusar é melhor que corromper o arranjo.
    """

    def test_dry_run_da_sanitize_funciona_no_flat(self) -> None:
        """A metade read-only continua valendo — é o `produz plano` da issue."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            rc, out = _run(["sanitize", "--workspace", str(ws)])
        self.assertEqual(rc, 0, f"o diagnóstico não deveria exigir migração:\n{out}")
        self.assertNotIn("layout antigo", out)

    def test_apply_da_sanitize_para_no_flat_e_oferece_migrate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            rc, out = _run(["sanitize", "--apply", "--workspace", str(ws)])
        self.assertEqual(rc, 1)
        self.assertIn("layout antigo", out)
        self.assertIn("prumo migrate", out)

    def test_apply_no_flat_nao_cria_arvore_prumo(self) -> None:
        """O observável que importa: a recusa tem que ser ANTES de qualquer
        escrita, senão ela chega tarde."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            _run(["sanitize", "--apply", "--workspace", str(ws)])
            self.assertFalse((ws / ".prumo").exists(), "a recusa deixou nascer um `.prumo/` no flat")

    def test_seed_para_no_flat_e_oferece_migrate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            rc, out = _run(["seed", "--workspace", str(ws)])
            self.assertEqual(rc, 1)
            self.assertIn("layout antigo", out)
            self.assertIn("prumo migrate", out)
            self.assertFalse((ws / ".prumo").exists(), "o seed deixou nascer um `.prumo/` no flat")

    def test_seed_continua_semeando_no_nested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_workspace(Path(tmp))
            rc, out = _run(["seed", "--workspace", str(ws)])
        self.assertEqual(rc, 0, f"regressão no nested:\n{out}")

    def test_seed_recusa_pasta_que_nao_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = _run(["seed", "--workspace", tmp])
        self.assertEqual(rc, 1)
        self.assertIn("nada a semear aqui", out)
        self.assertNotIn("prumo migrate", out, "pasta qualquer não é caso de migração")

    def test_flat_legitimo_e_reconhecido_como_legado(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(is_legacy_flat_workspace(_flat_workspace(Path(tmp))))

    def test_nested_nao_e_legado(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(is_legacy_flat_workspace(_nested_workspace(Path(tmp))))

    def test_pasta_qualquer_nao_e_flat_legado(self) -> None:
        """Sem isto, `is_legacy_flat_workspace` viraria 'não é nested', e
        qualquer pasta do disco receberia o convite pra migrar."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(is_legacy_flat_workspace(Path(tmp)))


class UpdateCoreStatusTests(unittest.TestCase):
    """`workspace_core_status` some no flat: o `--check` escondia workspace
    defasado atrás de runtime em dia, que é exatamente o que ele existe pra
    evitar (#170)."""

    def test_enxerga_core_do_workspace_flat(self) -> None:
        """Afirmar só `is not None` seria prova de atletismo sentado: um
        retorno `{}` fixo passaria (Codex, r1). O teste cobra a versão LIDA do
        core flat e o veredito de defasagem."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _flat_workspace(Path(tmp))
            got = workspace_core_status(ws, "5.99.0")
        self.assertIsNotNone(got)
        self.assertEqual(got["workspace_core_version"], "5.0.0")
        self.assertTrue(got["workspace_core_needs_update"])

    def test_ignora_pasta_que_nao_e_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(workspace_core_status(Path(tmp), "5.99.0"))

    def test_infra_sem_core_nao_vira_core_em_dia(self) -> None:
        """`.prumo/` sem core devolvia dict com versão vazia, e a saída humana
        imprimia `Core do workspace: n/d (em dia)` — ausência virando saúde por
        decreto (Codex, r1)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".prumo").mkdir()
            self.assertIsNone(workspace_core_status(root, "5.99.0"))


if __name__ == "__main__":
    unittest.main()
