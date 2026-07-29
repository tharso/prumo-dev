"""Snapshot de arquivo curado (#262, P8+P9 do relatório de incidente de 29/07).

Em 27/07 uma sessão reescreveu `Prumo/Referencias/INDICE.md` com escrita
integral querendo acrescentar 4 linhas: 48 entradas viraram 5. O dano ficou
invisível por dois dias e nenhum backup do produto cobria o caminho de edição
comum — todos os scopes existentes são disparados por comando do runtime.

Cada teste aqui cobre uma obrigação do contrato; os negativos existem porque
guard que não reprova o que proíbe é decoração (série #241/#248/#258).
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from prumo_runtime import curated
from prumo_runtime.projetos import PULSO_BEGIN, PULSO_END
from prumo_runtime.workspace_paths import workspace_paths


def _workspace(root: Path) -> Path:
    """Workspace nested mínimo, com os curados que os testes tocam."""
    (root / "Prumo" / "Agente").mkdir(parents=True)
    (root / "Prumo" / "Referencias").mkdir(parents=True)
    (root / ".prumo" / "state").mkdir(parents=True)
    for name in ("PAUTA.md", "INBOX.md", "REGISTRO.md", "IDEIAS.md"):
        (root / "Prumo" / name).write_text(f"# {name}\n", encoding="utf-8")
    for name in (
        "PERFIL.md", "MAPA-AUTORAL.md", "PESSOAS.md", "SAUDE.md",
        "ROTINA.md", "INFRA.md", "PROJETOS.md", "RELACOES.md",
    ):
        (root / "Prumo" / "Agente" / name).write_text(f"# {name}\n", encoding="utf-8")
    for name in ("INDICE.md", "WORKFLOWS.md", "EMAIL-CURADORIA.md"):
        (root / "Prumo" / "Referencias" / name).write_text(f"# {name}\n", encoding="utf-8")
    return root


class BaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = _workspace(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)

    def indice(self) -> Path:
        return self.ws / "Prumo" / "Referencias" / "INDICE.md"

    def snapshot(self, stamp: str) -> dict:
        return curated.snapshot_curated(self.ws, stamp=stamp)

    def scope_root(self) -> Path:
        return self.ws / ".prumo" / "backups" / "curated"

    def _seed_falso(self) -> Path:
        """Semente mínima. Path RESOLVIDO: os comandos resolvem o workspace e
        fazem `relative_to` contra ele."""
        alvo = self.ws.resolve() / ".prumo" / "state" / "seed.json"
        alvo.write_text(
            json.dumps(
                {"local_panorama": {"pauta": {"sections": [], "outras_secoes": []},
                                    "generated_for": "2026-07-29"},
                 "generated_at": "2026-07-29T08:00:00"}
            ),
            encoding="utf-8",
        )
        return alvo


class ClasseCuradaTest(BaseTest):
    def test_curada_cobre_todo_autoral(self) -> None:
        """Cobertura, não contagem: afirmar os PATHS. Contar deixaria a lista
        trocar de conteúdo mantendo o tamanho (armadilha da série #258)."""
        paths = workspace_paths(self.ws)
        curados = set(paths.curated_relative_paths())
        faltando = set(paths.authorial_relative_paths()) - curados
        self.assertEqual(faltando, set(), "curado perdeu arquivo autoral")

    def test_email_curadoria_entra_mesmo_ausente_do_disco(self) -> None:
        """O `append` explícito só compra algo quando o arquivo NÃO existe —
        com ele em disco o glob de fichas o pegaria de qualquer jeito, e o
        teste não distinguiria as duas implementações (achado da bateria de
        mutação). A classe curada responde "este path é curado?" para arquivo
        que ainda vai nascer, que é o que a #261 vai consultar antes de deixar
        escrever."""
        (self.ws / "Prumo" / "Referencias" / "EMAIL-CURADORIA.md").unlink()
        curados = workspace_paths(self.ws).curated_relative_paths()
        self.assertIn("Prumo/Referencias/EMAIL-CURADORIA.md", curados)

    def test_ficha_nova_entra_sem_editar_lista(self) -> None:
        """Fichas são enumeradas por regra. Lista manual apodrece: a ficha de
        amanhã não estaria nela, e é exatamente o arquivo insubstituível."""
        ficha = self.ws / "Prumo" / "Referencias" / "atomic-habits.md"
        ficha.write_text("# Atomic Habits\n", encoding="utf-8")
        curados = workspace_paths(self.ws).curated_relative_paths()
        self.assertIn("Prumo/Referencias/atomic-habits.md", curados)

    def test_curada_nao_repete_path(self) -> None:
        paths = workspace_paths(self.ws).curated_relative_paths()
        self.assertEqual(len(paths), len(set(paths)), "path duplicado na classe curada")

    def test_operacional_oculto_fica_fora(self) -> None:
        (self.ws / "Prumo" / "Referencias" / "_rascunho.md").write_text("x", encoding="utf-8")
        curados = workspace_paths(self.ws).curated_relative_paths()
        self.assertNotIn("Prumo/Referencias/_rascunho.md", curados)

    def test_classificacao_de_vigilancia(self) -> None:
        paths = workspace_paths(self.ws)
        flow, hybrid = paths.curated_flow_paths(), paths.curated_hybrid_paths()
        self.assertEqual(curated.watch_class("Prumo/REGISTRO.md", flow, hybrid), curated.FLOW)
        self.assertEqual(
            curated.watch_class("Prumo/Agente/PROJETOS.md", flow, hybrid), curated.HYBRID
        )
        self.assertEqual(
            curated.watch_class("Prumo/Referencias/INDICE.md", flow, hybrid),
            curated.ACCUMULATIVE,
        )

    def test_ficha_homonima_nao_herda_classe_do_canonico(self) -> None:
        """Uma ficha chamada `Referencias/PAUTA.md` é catálogo do usuário. Com
        classificação por basename ela cairia em `fluxo` e sumiria sem alarme
        (Codex, 262F-5)."""
        paths = workspace_paths(self.ws)
        flow, hybrid = paths.curated_flow_paths(), paths.curated_hybrid_paths()
        for homonimo in ("Prumo/Referencias/PAUTA.md", "Prumo/Referencias/PROJETOS.md"):
            self.assertEqual(
                curated.watch_class(homonimo, flow, hybrid), curated.ACCUMULATIVE, homonimo
            )


class SnapshotTest(BaseTest):
    def test_copia_conteudo_integro(self) -> None:
        """Existência não prova nada — comparar o CONTEÚDO."""
        self.indice().write_text("# Índice\n| 1 | a |\n| 2 | b |\n", encoding="utf-8")
        report = self.snapshot("2026-07-27T08-00-00")

        copia = self.scope_root() / "2026-07-27T08-00-00" / "Prumo__Referencias__INDICE.md"
        self.assertEqual(copia.read_text(encoding="utf-8"), self.indice().read_text(encoding="utf-8"))
        self.assertIn("Prumo/Referencias/INDICE.md", report["copied"])

    def test_pula_quando_nada_mudou(self) -> None:
        self.snapshot("2026-07-27T08-00-00")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertEqual(report["skipped"], "sem-mudanca")
        self.assertFalse((self.scope_root() / "2026-07-27T20-00-00").exists())

    def test_novo_carimbo_quando_algo_mudou(self) -> None:
        self.snapshot("2026-07-27T08-00-00")
        self.indice().write_text("# Índice\nmudou\n", encoding="utf-8")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertIsNone(report["skipped"])
        self.assertTrue((self.scope_root() / "2026-07-27T20-00-00").exists())

    def test_binario_nao_entra(self) -> None:
        (self.ws / "Prumo" / "Referencias" / "artigo.pdf").write_bytes(b"%PDF-1.4 fake")
        report = self.snapshot("2026-07-27T08-00-00")
        self.assertNotIn(
            "Prumo/Referencias/artigo.pdf", report["copied"],
            "PDF é a estante do usuário, não o fichário — o Prumo não é dono dela",
        )

    def test_arquivo_grande_e_reportado_nunca_copiado_em_silencio(self) -> None:
        gorda = self.ws / "Prumo" / "Referencias" / "gorda.md"
        gorda.write_text("x" * (curated.MAX_FILE_BYTES + 1), encoding="utf-8")
        report = self.snapshot("2026-07-27T08-00-00")

        self.assertNotIn("Prumo/Referencias/gorda.md", report["copied"])
        self.assertIn("Prumo/Referencias/gorda.md", report["oversized"])

    def test_falha_de_io_nao_derruba(self) -> None:
        """Backup que derruba a rota é pior que o problema que resolve."""
        alvo = self.ws / ".prumo" / "backups"
        alvo.write_text("sou um arquivo, não uma pasta", encoding="utf-8")

        report = curated.snapshot_curated(self.ws, stamp="2026-07-27T08-00-00")
        self.assertTrue(report["errors"], "falha de I/O tem de ser reportada")
        self.assertEqual(report["copied"], [])

    def test_snapshot_nao_contem_backup(self) -> None:
        """Regra de ouro da #178 com o scope novo."""
        self.snapshot("2026-07-27T08-00-00")
        self.indice().write_text("mudou\n", encoding="utf-8")
        self.snapshot("2026-07-27T20-00-00")

        aninhado = list((self.scope_root() / "2026-07-27T20-00-00").rglob("backups"))
        self.assertEqual(aninhado, [], "backup dentro de backup")


class AlertaDeEncolhimentoTest(BaseTest):
    def _alerta_de(self, report: dict, rel: str) -> dict | None:
        return next((a for a in report["alerts"] if a["path"] == rel), None)

    def test_o_caso_real_dispara(self) -> None:
        """48 entradas viram 4: o incidente de 27/07."""
        linhas = "".join(f"| {n} | ficha {n} | descrição autoral |\n" for n in range(1, 49))
        self.indice().write_text("# Índice\n" + linhas, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")

        self.indice().write_text(
            "".join(f"| {n} | ficha {n} | nova |\n" for n in range(45, 49)), encoding="utf-8"
        )
        report = self.snapshot("2026-07-27T20-00-00")

        alerta = self._alerta_de(report, "Prumo/Referencias/INDICE.md")
        self.assertIsNotNone(alerta, "encolhimento de 92% no índice não alarmou")
        self.assertGreater(alerta["before_bytes"], alerta["after_bytes"])
        self.assertIn("2026-07-27T08-00-00", alerta["previous_copy"])

    def test_arquivo_de_fluxo_nao_alarma(self) -> None:
        """Negativa: REGISTRO existe pra ser drenado. Rotação da faxina
        encolhe por contrato — alarmar aqui seria ruído que treina a ignorar."""
        registro = self.ws / "Prumo" / "REGISTRO.md"
        registro.write_text("# Registro\n" + "| linha |\n" * 200, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")

        registro.write_text("# Registro\n| linha |\n", encoding="utf-8")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertIsNone(self._alerta_de(report, "Prumo/REGISTRO.md"))

    def test_arquivo_novo_nunca_alarma(self) -> None:
        """Negativa: sem cópia anterior não há delta — só ausência de história."""
        self.snapshot("2026-07-27T08-00-00")
        nova = self.ws / "Prumo" / "Referencias" / "nova.md"
        nova.write_text("# Nova\n", encoding="utf-8")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertIsNone(self._alerta_de(report, "Prumo/Referencias/nova.md"))

    def test_encolhimento_pequeno_nao_alarma(self) -> None:
        """Negativa: acumulativo também é legitimamente condensado (Codex, r1
        — PERFIL enxugado na higiene). O limiar tem de ser relevante."""
        perfil = self.ws / "Prumo" / "Agente" / "PERFIL.md"
        perfil.write_text("x" * 1000, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")

        perfil.write_text("x" * 900, encoding="utf-8")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertIsNone(self._alerta_de(report, "Prumo/Agente/PERFIL.md"))


class HibridoTest(BaseTest):
    """`PROJETOS.md` é híbrido (#201): só o miolo dos blocos de pulso é
    reescrito pelo `projetos --sync`; todo byte fora deles é autoral."""

    def projetos(self) -> Path:
        return self.ws / "Prumo" / "Agente" / "PROJETOS.md"

    def _alerta(self, report: dict) -> dict | None:
        return next(
            (a for a in report["alerts"] if a["path"] == "Prumo/Agente/PROJETOS.md"), None
        )

    def test_sync_do_pulso_nao_alarma(self) -> None:
        """Negativa central do híbrido: o bloco encolhe muito, o autoral não."""
        autoral = "# Projetos\n\n## Startup X\n- Caminho: /x\n" + "contexto autoral\n" * 50
        self.projetos().write_text(
            autoral + PULSO_BEGIN + "\n" + "pulso velho\n" * 200 + PULSO_END + "\n",
            encoding="utf-8",
        )
        self.snapshot("2026-07-27T08-00-00")

        self.projetos().write_text(
            autoral + PULSO_BEGIN + "\n" + "pulso novo\n" + PULSO_END + "\n",
            encoding="utf-8",
        )
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertIsNone(self._alerta(report), "`projetos --sync` disparou falso alarme")

    def test_perda_fora_do_pulso_alarma(self) -> None:
        """Positiva: o conteúdo autoral sumiu, o bloco de pulso ficou igual."""
        pulso = PULSO_BEGIN + "\n" + "pulso\n" * 10 + PULSO_END + "\n"
        self.projetos().write_text(
            "# Projetos\n" + "contexto autoral\n" * 200 + pulso, encoding="utf-8"
        )
        self.snapshot("2026-07-27T08-00-00")

        self.projetos().write_text("# Projetos\n" + pulso, encoding="utf-8")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertIsNotNone(self._alerta(report), "perda de autoral no híbrido passou calada")


class GanchoTest(BaseTest):
    """O incidente aconteceu no Cowork, onde a rota é `prumo seed` (#216) e
    NÃO `prumo briefing`. Pendurar só no briefing deixaria o host do incidente
    descoberto — o achado que reabriu o desenho na revisão.

    Comportamental, não bytecode: procurar o nome em `co_names` passaria com a
    chamada dentro de um `if False` ou depois da escrita (Codex, 262D-8).
    """

    def _args(self, **extra):
        return SimpleNamespace(workspace=str(self.ws), format="json", **extra)

    def test_seed_dispara_o_snapshot_antes_de_escrever(self) -> None:
        from prumo_runtime.commands import seed as seed_cmd

        ordem: list[str] = []
        with patch.object(
            seed_cmd, "snapshot_curated", side_effect=lambda *a, **k: ordem.append("snapshot") or {}
        ) as spy, patch.object(
            seed_cmd, "write_seed", side_effect=lambda *a, **k: ordem.append("escrita") or self._seed_falso()
        ):
            seed_cmd.run_seed(self._args())

        self.assertEqual(spy.call_count, 1, "a rota do Cowork não dispara o snapshot")
        self.assertEqual(ordem, ["snapshot", "escrita"], "snapshot depois da escrita não protege")

    def test_briefing_dispara_o_snapshot_antes_de_montar(self) -> None:
        from prumo_runtime.commands import briefing as briefing_cmd

        ordem: list[str] = []
        with patch.object(
            briefing_cmd, "snapshot_curated",
            side_effect=lambda *a, **k: ordem.append("snapshot") or {},
        ) as spy, patch.object(
            briefing_cmd, "build_briefing_payload",
            side_effect=lambda *a, **k: ordem.append("payload") or {"message": "ok"},
        ):
            briefing_cmd.run_briefing(self._args())

        self.assertEqual(spy.call_count, 1, "`prumo briefing` não dispara o snapshot")
        self.assertEqual(ordem, ["snapshot", "payload"])

    def test_mark_done_nao_dispara(self) -> None:
        """`--mark-done` só carimba o dia; não é ritual de leitura."""
        from prumo_runtime.commands import briefing as briefing_cmd

        with patch.object(briefing_cmd, "snapshot_curated") as spy, patch.object(
            briefing_cmd, "build_config_from_existing"
        ), patch.object(briefing_cmd, "update_last_briefing"):
            briefing_cmd.run_briefing(self._args(mark_done=True))
        spy.assert_not_called()

    def test_dispara_no_modo_texto_tambem(self) -> None:
        """Os dois testes de ordem usavam só JSON: um mutante que chamasse o
        snapshot apenas quando `format == "json"` passaria (Codex, 262E-7)."""
        from prumo_runtime.commands import briefing as briefing_cmd
        from prumo_runtime.commands import seed as seed_cmd

        with patch.object(briefing_cmd, "snapshot_curated", return_value={}) as spy, patch.object(
            briefing_cmd, "build_briefing_payload", return_value={"message": "ok"}
        ):
            with redirect_stdout(io.StringIO()):
                briefing_cmd.run_briefing(SimpleNamespace(workspace=str(self.ws), format="text"))
        spy.assert_called_once_with(self.ws.resolve())

        with patch.object(seed_cmd, "snapshot_curated", return_value={}) as spy, patch.object(
            seed_cmd, "write_seed", side_effect=lambda *a, **k: self._seed_falso()
        ):
            with redirect_stdout(io.StringIO()):
                seed_cmd.run_seed(SimpleNamespace(workspace=str(self.ws), format="text"))
        spy.assert_called_once_with(self.ws.resolve())

    def test_relatorio_de_texto_chega_ao_stdout(self) -> None:
        """Integração: `render_report` ligado na rota de texto, não só testado
        como unidade (Codex, 262E-7)."""
        from prumo_runtime.commands import briefing as briefing_cmd

        buf = io.StringIO()
        with patch.object(
            briefing_cmd, "snapshot_curated",
            return_value={"alerts": [], "oversized": ["Prumo/Referencias/gorda.md"], "errors": []},
        ), patch.object(briefing_cmd, "build_briefing_payload", return_value={"message": "painel"}):
            with redirect_stdout(buf):
                briefing_cmd.run_briefing(SimpleNamespace(workspace=str(self.ws), format="text"))

        saida = buf.getvalue()
        self.assertIn("gorda.md", saida)
        self.assertIn("painel", saida)

    def test_construtores_de_payload_nao_escrevem(self) -> None:
        """Codex, design r1: 'consulta com efeito colateral é casca de banana
        arquitetural'. O snapshot é chamada explícita do comando."""
        from prumo_runtime.commands import briefing as briefing_cmd
        from prumo_runtime.commands import seed as seed_cmd

        for fn in (briefing_cmd.build_briefing_payload, seed_cmd.build_seed_payload):
            self.assertNotIn(
                "snapshot_curated", fn.__code__.co_names,
                f"{fn.__name__} ganhou escrita surpresa",
            )


class SaidaJsonTest(BaseTest):
    """Quando o alerta finalmente dispara, ele não pode quebrar quem consome a
    saída — seria o alerta bloqueando o ritual pela porta dos fundos."""

    def _com_alerta(self) -> None:
        linhas = "".join(f"| {n} | ficha {n} | descrição |\n" for n in range(1, 49))
        self.indice().write_text("# Índice\n" + linhas, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")
        self.indice().write_text("| 45 | x | y |\n", encoding="utf-8")

    def test_seed_json_continua_parseavel_com_alerta(self) -> None:
        from prumo_runtime.commands import seed as seed_cmd

        self._com_alerta()
        buf = io.StringIO()
        with patch.object(seed_cmd, "write_seed", side_effect=lambda *a, **k: self._seed_falso()):
            with redirect_stdout(buf):
                seed_cmd.run_seed(SimpleNamespace(workspace=str(self.ws), format="json"))

        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["curated_snapshot"]["alerts"], "alerta sumiu do payload")

    def test_briefing_json_continua_parseavel_com_alerta(self) -> None:
        from prumo_runtime.commands import briefing as briefing_cmd

        self._com_alerta()
        buf = io.StringIO()
        with patch.object(
            briefing_cmd, "build_briefing_payload", return_value={"message": "ok"}
        ):
            with redirect_stdout(buf):
                briefing_cmd.run_briefing(SimpleNamespace(workspace=str(self.ws), format="json"))

        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["curated_snapshot"]["alerts"])


class ColetaIncompletaTest(BaseTest):
    """O dedupe lia do snapshot anterior só os paths que ainda existiam: o
    arquivo apagado sumia dos dois lados e o resultado era 'sem-mudanca' —
    silêncio no caso mais grave de todos (Codex, 262D-1)."""

    def test_arquivo_apagado_alarma_e_nao_pula(self) -> None:
        linhas = "".join(f"| {n} | ficha {n} | descrição |\n" for n in range(1, 49))
        self.indice().write_text("# Índice\n" + linhas, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")

        self.indice().unlink()
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertIsNone(report["skipped"], "arquivo apagado virou 'sem-mudanca'")
        alerta = next(
            (a for a in report["alerts"] if a["path"] == "Prumo/Referencias/INDICE.md"), None
        )
        self.assertIsNotNone(alerta, "sumiço completo passou calado")
        self.assertEqual(alerta["state"], curated.GONE)
        self.assertEqual(alerta["shrink_pct"], 100)

    def _manifesto(self, stamp: str) -> dict:
        return json.loads(
            (self.scope_root() / stamp / curated.MANIFEST_NAME).read_text(encoding="utf-8")
        )

    def test_falha_de_leitura_nao_vira_baseline(self) -> None:
        """Buraco no inventário: retrato furado não pode virar régua."""
        self.indice().write_text("x" * 500, encoding="utf-8")
        with patch.object(
            curated.Path, "read_bytes", side_effect=OSError("disco pifou")
        ):
            self.snapshot("2026-07-27T08-00-00")
        self.assertFalse(
            self._manifesto("2026-07-27T08-00-00")["complete"],
            "retrato furado se declarou completo",
        )

    def test_baseline_pula_o_incompleto_e_usa_o_completo(self) -> None:
        """O cenário exato do Codex (262E-1): completo → incompleto sem o
        índice → índice mutilado. A régua tem de ser o COMPLETO, senão o
        arquivo que faltou no meio nunca tem contra o que alarmar."""
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")  # completo, com o índice

        manifesto = self._manifesto("t1")
        (self.scope_root() / "t2").mkdir()
        (self.scope_root() / "t2" / curated.MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "schema": curated.MANIFEST_SCHEMA,
                    "captured_at_utc": manifesto["captured_at_utc"][:-1] + "9",
                    "complete": False,       # incompleto e MAIS NOVO
                    "files": {},             # sem o índice no inventário
                    "oversized": [],
                }
            ),
            encoding="utf-8",
        )

        self.indice().write_text("a" * 50, encoding="utf-8")
        report = self.snapshot("t3")

        alerta = next(
            (a for a in report["alerts"] if a["path"] == "Prumo/Referencias/INDICE.md"), None
        )
        self.assertIsNotNone(alerta, "comparou contra o snapshot incompleto e ficou cego")

    def test_oversized_estavel_nao_desliga_o_dedupe(self) -> None:
        """Um único .md acima do teto não pode virar assinatura vitalícia de
        cópia integral em todo ritual (Codex, 262E-4)."""
        gorda = self.ws / "Prumo" / "Referencias" / "gorda.md"
        gorda.write_text("x" * (curated.MAX_FILE_BYTES + 1), encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertEqual(report["skipped"], "sem-mudanca")
        self.assertEqual(report["oversized"], ["Prumo/Referencias/gorda.md"])

    def test_oversized_novo_quebra_o_dedupe(self) -> None:
        """Negativa da anterior: o conjunto MUDOU, então há o que registrar."""
        self.snapshot("2026-07-27T08-00-00")
        (self.ws / "Prumo" / "Referencias" / "gorda.md").write_text(
            "x" * (curated.MAX_FILE_BYTES + 1), encoding="utf-8"
        )
        report = self.snapshot("2026-07-27T20-00-00")
        self.assertIsNone(report["skipped"])

    def test_manifesto_corrompido_e_declarado(self) -> None:
        """História perdida em silêncio é o defeito que o módulo combate."""
        self.snapshot("2026-07-27T08-00-00")
        (self.scope_root() / "2026-07-27T08-00-00" / curated.MANIFEST_NAME).write_text(
            "{ truncado", encoding="utf-8"
        )
        self.indice().write_text("mudou\n", encoding="utf-8")
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertTrue(
            any("sem manifesto válido" in e for e in report["errors"]),
            "candidato corrompido foi ignorado sem avisar",
        )

    def test_manifesto_corrompido_nao_desliga_o_dedupe_futuro(self) -> None:
        """Degradação de história antiga não é buraco no retrato de hoje."""
        self.snapshot("t1")
        (self.scope_root() / "t1" / curated.MANIFEST_NAME).write_text("{", encoding="utf-8")
        self.snapshot("t2")
        report = self.snapshot("t3")
        self.assertEqual(report["skipped"], "sem-mudanca")


class AcervoTest(BaseTest):
    """Ficha arquivada pelo acervo vai pra `Arquivo/Acervo/` com cópia
    idêntica. Alarmar seria o produto mandar arquivar e depois tocar a sirene
    porque o usuário arquivou (Codex, 262E-3)."""

    def _ficha(self) -> Path:
        return self.ws / "Prumo" / "Referencias" / "artigo.md"

    def test_ficha_arquivada_e_rebaixada_nao_silenciada(self) -> None:
        """Gêmeo byte a byte no acervo é indício forte, não prova: o produto
        não tem proveniência da operação. Então o tom cai — some da lista de
        suspeitos e vira linha calma — mas não vira silêncio (Codex, 262F-3)."""
        self._ficha().write_text("# Artigo\n" + "conteúdo\n" * 60, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")

        acervo = self.ws / "Prumo" / "Arquivo" / "Acervo"
        acervo.mkdir(parents=True)
        shutil.move(str(self._ficha()), str(acervo / "artigo-2026-07-27.md"))
        report = self.snapshot("2026-07-27T20-00-00")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("artigo.md"))
        self.assertEqual(alerta["state"], curated.ARCHIVED)
        self.assertTrue(alerta["twin"], "não disse ONDE está a cópia")
        texto = curated.render_report(report)
        self.assertNotIn("SUMIU", texto)
        self.assertIn("cópia idêntica no acervo", texto)

    def test_delecao_permanente_continua_alarmando(self) -> None:
        """Negativa: sem gêmeo em `Arquivo/`, sumiço é sumiço."""
        self._ficha().write_text("# Artigo\n" + "conteúdo\n" * 60, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")

        self._ficha().unlink()
        report = self.snapshot("2026-07-27T20-00-00")

        alerta = next((a for a in report["alerts"] if a["path"].endswith("artigo.md")), None)
        self.assertIsNotNone(alerta, "deleção permanente passou calada")
        self.assertEqual(alerta["state"], curated.GONE)
        self.assertIn("SUMIU", curated.render_report(report))

    def test_gemeo_fora_de_acervo_nao_conta(self) -> None:
        """O índice é restrito a `Arquivo/Acervo/`, destino real do acervo.
        Cópia idêntica em qualquer outro canto de `Arquivo/` é coincidência do
        usuário, não rastro de arquivamento (Codex, 262F-3)."""
        conteudo = "# Artigo\n" + "conteúdo\n" * 60
        self._ficha().write_text(conteudo, encoding="utf-8")
        self.snapshot("t1")

        outro = self.ws / "Prumo" / "Arquivo" / "Rascunhos"
        outro.mkdir(parents=True)
        (outro / "artigo.md").write_text(conteudo, encoding="utf-8")
        self._ficha().unlink()
        report = self.snapshot("t2")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("Referencias/artigo.md"))
        self.assertEqual(alerta["state"], curated.GONE)

    def test_gemeo_diferente_nao_conta_como_arquivado(self) -> None:
        """Negativa fina: mesmo nome em `Arquivo/`, conteúdo outro."""
        self._ficha().write_text("# Artigo\n" + "original\n" * 60, encoding="utf-8")
        self.snapshot("2026-07-27T08-00-00")

        acervo = self.ws / "Prumo" / "Arquivo" / "Acervo"
        acervo.mkdir(parents=True)
        (acervo / "artigo.md").write_text("# Artigo\noutra coisa\n", encoding="utf-8")
        self._ficha().unlink()
        report = self.snapshot("2026-07-27T20-00-00")

        self.assertTrue([a for a in report["alerts"] if a["path"].endswith("artigo.md")])


class DestinoTest(BaseTest):
    def test_backups_symlinkado_recusa_escrita(self) -> None:
        """`prune_expired_backups` já recusa raiz symlinkada; o writer novo
        precisa da mesma disciplina (Codex, 262E-6)."""
        fora = Path(self._tmp.name).parent / f"fora-{Path(self._tmp.name).name}"
        fora.mkdir()
        self.addCleanup(shutil.rmtree, fora, True)
        (self.ws / ".prumo" / "backups").symlink_to(fora, target_is_directory=True)

        report = self.snapshot("2026-07-27T08-00-00")
        self.assertTrue(any("symlink" in e for e in report["errors"]))
        self.assertEqual(list(fora.iterdir()), [], "gravou fora do território")

    def test_carimbo_sobrevive_a_corrida(self) -> None:
        """Simula o outro `prumo seed` vencendo entre a decisão e a criação:
        `mkdir` estoura `FileExistsError` na primeira tentativa. Implementação
        que checa `exists()` antes e cria depois perderia o snapshot inteiro no
        boundary (Codex, 262E-5); a reserva atômica avança o sufixo."""
        scope = self.scope_root()
        scope.mkdir(parents=True)
        real = Path.mkdir
        estado = {"primeira": True}

        def mkdir_com_corrida(self, *a, **kw):
            if self.parent == scope and estado["primeira"]:
                estado["primeira"] = False
                raise FileExistsError(self)
            return real(self, *a, **kw)

        with patch.object(Path, "mkdir", mkdir_com_corrida):
            destino = curated._reserve_stamp_dir(scope, "carimbo")

        self.assertTrue(destino.is_dir())
        self.assertEqual(destino.name, "carimbo-2")


class BoundaryTest(BaseTest):
    """A promessa é 'nunca derruba o ritual'. Capturar só OSError deixava
    passar `UnicodeDecodeError` do override de thresholds (Codex, 262D-4)."""

    def test_override_com_bytes_invalidos_nao_derruba(self) -> None:
        rules = self.ws / "Prumo" / "Custom" / "rules"
        rules.mkdir(parents=True)
        (rules / "faxina-thresholds.md").write_bytes(b"- max_items: \xff\xfe10\n")

        report = curated.snapshot_curated(self.ws, stamp="2026-07-27T08-00-00")
        self.assertIsInstance(report, dict)
        self.assertTrue(report["errors"])

    def test_falha_de_threshold_nao_derruba(self) -> None:
        with patch.object(
            curated.faxina_thresholds, "effective", side_effect=ValueError("boom")
        ):
            report = curated.snapshot_curated(self.ws, stamp="2026-07-27T08-00-00")
        self.assertTrue(any("ValueError" in e for e in report["errors"]))


class PulsoInvalidoTest(BaseTest):
    """Marcador órfão fazia todo o sufixo sumir da medição — conteúdo autoral
    desaparecia da conta sem erro nem alerta (Codex, 262D-2)."""

    def test_bloco_aberto_sem_fechar_conta_o_arquivo_inteiro(self) -> None:
        texto = "# Projetos\n" + "autoral\n" * 50 + PULSO_BEGIN + "\n" + "pulso\n" * 50
        medido = curated.measured_size(texto.encode("utf-8"), curated.HYBRID)
        self.assertEqual(medido, len(texto.encode("utf-8")), "sufixo órfão sumiu da conta")

    def test_fim_sem_comeco_conta_o_arquivo_inteiro(self) -> None:
        texto = "# Projetos\n" + "autoral\n" * 10 + PULSO_END + "\n"
        self.assertEqual(
            curated.measured_size(texto.encode("utf-8"), curated.HYBRID), len(texto.encode("utf-8"))
        )

    def test_estrutura_invalida_vira_erro_reportado(self) -> None:
        projetos = self.ws / "Prumo" / "Agente" / "PROJETOS.md"
        projetos.write_text("# Projetos\n" + PULSO_BEGIN + "\nsem fim\n", encoding="utf-8")
        report = self.snapshot("2026-07-27T08-00-00")
        self.assertTrue(
            any("PROJETOS.md" in e for e in report["errors"]),
            "estrutura de pulso inválida passou calada",
        )

    def test_bloco_aninhado_conta_o_arquivo_inteiro(self) -> None:
        """Caso positivo do `BEGIN` aninhado, que não existia (Codex, 262E-7)."""
        texto = (
            "# Projetos\n" + "autoral\n" * 10
            + PULSO_BEGIN + "\n" + PULSO_BEGIN + "\npulso\n" + PULSO_END + "\n"
        )
        self.assertEqual(
            curated.measured_size(texto.encode("utf-8"), curated.HYBRID), len(texto.encode("utf-8"))
        )
        _, erro = curated._pulso_partition(texto)
        self.assertEqual(erro, "bloco de pulso aninhado")

    def test_crlf_nao_quebra_o_parser(self) -> None:
        texto = "# P\r\n" + PULSO_BEGIN + "\r\npulso\r\n" + PULSO_END + "\r\nautoral\r\n"
        medido = curated.measured_size(texto.encode("utf-8"), curated.HYBRID)
        self.assertLess(medido, len(texto.encode("utf-8")), "bloco de pulso não foi excluído")


class CercaDeCaminhoTest(BaseTest):
    """`Referencias/` symlinkado pra dentro de `.prumo/backups/` copiaria
    backup pra dentro de backup pelo arquivo final, que não é link
    (Codex, 262D-7)."""

    def test_under_backup_root_isolado(self) -> None:
        """No fluxo, `_has_symlink_ancestor` curto-circuita e esta cerca nunca
        roda — ou se testa isolada, ou ela cobra pedágio sem prestar serviço
        (Codex, 262E-7). Testada isolada: é a defesa que sobra se a primeira
        deixar passar um caminho já resolvido."""
        dentro = self.ws / ".prumo" / "backups" / "curated" / "x" / "INDICE.md"
        dentro.parent.mkdir(parents=True)
        dentro.write_text("x", encoding="utf-8")
        self.assertTrue(curated._under_backup_root(self.ws, dentro))
        self.assertFalse(curated._under_backup_root(self.ws, self.indice()))

    def test_pasta_symlinkada_pro_backup_e_recusada(self) -> None:
        alvo = self.ws / ".prumo" / "backups" / "curated" / "antigo"
        alvo.mkdir(parents=True)
        (alvo / "INDICE.md").write_text("# de dentro do backup\n", encoding="utf-8")

        referencias = self.ws / "Prumo" / "Referencias"
        shutil.rmtree(referencias)
        referencias.symlink_to(alvo, target_is_directory=True)

        report = self.snapshot("2026-07-27T08-00-00")
        self.assertNotIn("Prumo/Referencias/INDICE.md", report["copied"])
        self.assertTrue(report["errors"])


class RelatorioTest(BaseTest):
    """`errors` e `oversized` são justamente os arquivos que NÃO ganharam
    cópia — o pior momento pra o relatório ficar calado (Codex, 262D-5)."""

    def test_oversized_aparece_no_texto(self) -> None:
        report = {"alerts": [], "oversized": ["Prumo/Referencias/gorda.md"], "errors": []}
        texto = curated.render_report(report)
        self.assertIn("gorda.md", texto)
        self.assertIn("SEM cópia", texto)

    def test_erro_aparece_no_texto(self) -> None:
        report = {"alerts": [], "oversized": [], "errors": ["INDICE.md: disco cheio"]}
        self.assertIn("disco cheio", curated.render_report(report))

    def test_relatorio_limpo_e_silencioso(self) -> None:
        self.assertEqual(curated.render_report({"alerts": [], "oversized": [], "errors": []}), "")


class CarimboTest(BaseTest):
    """Ordem por nome quebra quando o relógio recua (fuso, DST); colisão de
    segundo sobrescrevia a fotografia anterior (Codex, 262D-3)."""

    def test_carimbo_colidido_nao_sobrescreve(self) -> None:
        self.indice().write_text("primeiro\n", encoding="utf-8")
        self.snapshot("mesmo-carimbo")
        self.indice().write_text("segundo\n", encoding="utf-8")
        report = self.snapshot("mesmo-carimbo")

        self.assertNotEqual(report["stamp"], "mesmo-carimbo")
        primeiro = self.scope_root() / "mesmo-carimbo" / "Prumo__Referencias__INDICE.md"
        self.assertEqual(primeiro.read_text(encoding="utf-8"), "primeiro\n")

    def test_anterior_vem_do_instante_e_nao_do_nome(self) -> None:
        """Três carimbos, porque com dois qualquer ordenação escolhe o mesmo —
        foi assim que a primeira versão deste teste passou com a mutação
        aplicada (achado da bateria).

        O carimbo capturado por ÚLTIMO tem o nome lexicograficamente MENOR,
        que é o que um relógio recuado (fuso, DST) produz. Comparar contra ele
        não dá alerta (300→250); comparar contra o de nome maior, porém mais
        velho, daria (1000→250). Silêncio é o veredito correto.
        """
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("2026-06-01T00-00-00")          # nome MAIOR, mais VELHO
        self.indice().write_text("b" * 300, encoding="utf-8")
        self.snapshot("2025-01-01T00-00-00")          # nome MENOR, mais NOVO

        self.indice().write_text("c" * 250, encoding="utf-8")
        report = self.snapshot("2027-01-01T00-00-00")

        alerta = next(
            (a for a in report["alerts"] if a["path"] == "Prumo/Referencias/INDICE.md"), None
        )
        self.assertIsNone(
            alerta,
            "comparou com o carimbo de nome maior em vez do capturado por último",
        )




class BaselineVerificadaTest(BaseTest):
    """Manifesto que se declara completo não prova que as cópias existem.
    Régua que não se verifica é papel timbrado (Codex, 262F-1)."""

    def test_copia_apagada_invalida_a_regua(self) -> None:
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        (self.scope_root() / "t1" / "Prumo__Referencias__INDICE.md").unlink()

        self.indice().unlink()
        report = self.snapshot("t2")

        self.assertIsNone(report["skipped"], "sumiço virou 'sem-mudanca'")
        self.assertTrue(
            any("não serve de régua" in e for e in report["errors"]),
            "baseline furada foi usada em silêncio",
        )

    def test_copia_adulterada_invalida_a_regua(self) -> None:
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        (self.scope_root() / "t1" / "Prumo__Referencias__INDICE.md").write_text(
            "adulterado", encoding="utf-8"
        )
        self.indice().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t2")

        self.assertTrue(any("digest" in e for e in report["errors"]))

    def test_cai_no_completo_anterior_quando_o_recente_falha(self) -> None:
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        self.indice().write_text("b" * 1000, encoding="utf-8")
        self.snapshot("t2")
        (self.scope_root() / "t2" / "Prumo__Referencias__INDICE.md").unlink()

        self.indice().write_text("c" * 100, encoding="utf-8")
        report = self.snapshot("t3")

        alerta = next(
            (a for a in report["alerts"] if a["path"] == "Prumo/Referencias/INDICE.md"), None
        )
        self.assertIsNotNone(alerta, "não caiu na régua anterior válida")
        self.assertIn("t1", alerta["previous_copy"])

    def test_sem_regua_completa_e_declarado(self) -> None:
        self.snapshot("t1")
        manifesto = json.loads(
            (self.scope_root() / "t1" / curated.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        manifesto["complete"] = False
        (self.scope_root() / "t1" / curated.MANIFEST_NAME).write_text(
            json.dumps(manifesto), encoding="utf-8"
        )
        self.indice().write_text("mudou", encoding="utf-8")
        report = self.snapshot("t2")

        self.assertTrue(
            any("detecção de encolhimento indisponível" in e for e in report["errors"])
        )


class RaizQuebradaTest(BaseTest):
    """`Referencias/` virado ARQUIVO fazia o glob devolver nada e todo
    `is_file()` dos filhos dar False: nada entrava em coleta e nascia uma
    baseline 'completa' sem referência nenhuma (Codex, 262F-2)."""

    def test_raiz_virada_arquivo_fura_a_integridade(self) -> None:
        shutil.rmtree(self.ws / "Prumo" / "Referencias")
        (self.ws / "Prumo" / "Referencias").write_text("não sou pasta", encoding="utf-8")

        report = self.snapshot("t1")
        self.assertTrue(
            any("não é diretório" in e for e in report["errors"]),
            "raiz quebrada passou calada",
        )
        manifesto = json.loads(
            (self.scope_root() / "t1" / curated.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertFalse(manifesto["complete"], "retrato sem Referencias/ se disse completo")


class JanelaDeEscritaTest(BaseTest):
    """O alerta era calculado sobre os bytes lidos e a cópia reabria o arquivo:
    se ele mudasse no meio, media um conteúdo e gravava outro, com o manifesto
    declarando completo o que ninguém conferiu (Codex, 262F-4)."""

    def test_grava_exatamente_os_bytes_medidos(self) -> None:
        """Simula a origem mudando ENTRE medir e copiar: a primeira leitura
        devolve o conteúdo íntegro, qualquer releitura devolve o mutilado. Uma
        implementação que reabre o arquivo pra copiar gravaria o mutilado e o
        declararia completo."""
        integro = ("# Índice\n" + "linha\n" * 200).encode("utf-8")
        mutilado = b"mutilado\n"
        self.indice().write_bytes(integro)

        alvo = self.indice().resolve()
        real = Path.read_bytes
        lido = {"ja": False}

        def leitura_com_corrida(self, *a, **kw):
            if self.resolve() == alvo:
                if lido["ja"]:
                    return mutilado
                lido["ja"] = True
                return integro
            return real(self, *a, **kw)

        with patch.object(Path, "read_bytes", leitura_com_corrida):
            self.snapshot("t1")

        copia = (self.scope_root() / "t1" / "Prumo__Referencias__INDICE.md").read_bytes()
        self.assertEqual(copia, integro, "gravou conteúdo diferente do que mediu")

    def test_digest_do_manifesto_bate_com_a_copia(self) -> None:
        self.indice().write_text("# Índice\nconteúdo\n", encoding="utf-8")
        self.snapshot("t1")
        manifesto = json.loads(
            (self.scope_root() / "t1" / curated.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        for flat, digest in manifesto["digests"].items():
            data = (self.scope_root() / "t1" / flat).read_bytes()
            self.assertEqual(curated._digest(data), digest, flat)

class FidelidadeDeBytesTest(BaseTest):
    """`read_text`/`write_text` normalizam quebra de linha: a cópia poderia
    diferir do original e o digest autenticaria o TEXTO, não o arquivo
    (Codex, 262G-1). Backup que não devolve os bytes não é backup."""

    def test_crlf_sobrevive_ao_snapshot(self) -> None:
        original = b"# Indice\r\n| 1 | a |\r\n\n| 2 | b |\r\n"
        self.indice().write_bytes(original)
        self.snapshot("t1")

        copia = (self.scope_root() / "t1" / "Prumo__Referencias__INDICE.md").read_bytes()
        self.assertEqual(copia, original, "quebra de linha foi normalizada na cópia")

    def test_digest_e_dos_bytes(self) -> None:
        original = b"a\r\nb\n"
        self.indice().write_bytes(original)
        self.snapshot("t1")
        manifesto = json.loads(
            (self.scope_root() / "t1" / curated.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifesto["digests"]["Prumo__Referencias__INDICE.md"], curated._digest(original)
        )


class ManifestoMalformadoTest(BaseTest):
    """Manifesto estruturalmente inválido não pode DESLIGAR o mecanismo: ele
    tem de ser degradado e ignorado, com o snapshot de hoje gravado assim
    mesmo (Codex, 262G-2)."""

    def _corromper(self, stamp: str, **campos) -> None:
        alvo = self.scope_root() / stamp / curated.MANIFEST_NAME
        manifesto = json.loads(alvo.read_text(encoding="utf-8"))
        manifesto.update(campos)
        alvo.write_text(json.dumps(manifesto), encoding="utf-8")

    def test_digests_como_lista_nao_derruba(self) -> None:
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        self._corromper("t1", digests=[])

        self.indice().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t2")

        self.assertTrue((self.scope_root() / "t2").is_dir(), "parou de gravar snapshot")
        self.assertTrue(any("sem manifesto válido" in e for e in report["errors"]))

    def test_instante_malformado_e_recusado(self) -> None:
        self.snapshot("t1")
        self._corromper("t1", captured_at_utc="ontem de manhã")
        self.indice().write_text("mudou", encoding="utf-8")
        report = self.snapshot("t2")
        self.assertTrue(any("sem manifesto válido" in e for e in report["errors"]))

    def test_instante_sem_fuso_e_recusado(self) -> None:
        self.snapshot("t1")
        self._corromper("t1", captured_at_utc="2026-07-29T08:00:00")
        self.indice().write_text("mudou", encoding="utf-8")
        report = self.snapshot("t2")
        self.assertTrue(any("sem manifesto válido" in e for e in report["errors"]))


class CarimboSeguroTest(BaseTest):
    """Carimbo é NOME de diretório: absoluto ou `../` reservaria fora do
    scope, furando a cerca (Codex, 262G-4)."""

    def test_travessia_nao_escapa_do_scope(self) -> None:
        """Afirma o FILESYSTEM, não o rótulo devolvido: a primeira versão
        deste teste conferia `report["stamp"]`, que com um carimbo absoluto
        vira só o basename e parece inocente (achado da bateria)."""
        vizinho = Path(self._tmp.name).parent / f"vizinho-{Path(self._tmp.name).name}"
        vizinho.mkdir()
        self.addCleanup(shutil.rmtree, vizinho, True)

        for malicioso in (
            "../../fora", f"{vizinho}/fora", "..", "", "sub/dir",
        ):
            with self.subTest(malicioso):
                antes = {p.name for p in self.scope_root().iterdir()} if self.scope_root().is_dir() else set()
                curated.snapshot_curated(self.ws, stamp=malicioso)

                self.assertEqual(
                    list(vizinho.iterdir()), [], f"carimbo `{malicioso}` gravou fora do workspace"
                )
                depois = {p.name for p in self.scope_root().iterdir()}
                novos = depois - antes
                for nome in novos:
                    alvo = (self.scope_root() / nome).resolve()
                    self.assertTrue(
                        alvo.is_relative_to(self.scope_root().resolve()),
                        f"carimbo `{malicioso}` escapou pra {alvo}",
                    )
                self.indice().write_text(f"muda {malicioso}", encoding="utf-8")


class AcervoSymlinkTest(BaseTest):
    """`Acervo/` symlinkado pra fora leria conteúdo externo e rebaixaria uma
    deleção REAL a arquivado (Codex, 262G-3)."""

    def test_acervo_symlinkado_nao_rebaixa(self) -> None:
        conteudo = "# Artigo\n" + "conteúdo\n" * 60
        ficha = self.ws / "Prumo" / "Referencias" / "artigo.md"
        ficha.write_text(conteudo, encoding="utf-8")
        self.snapshot("t1")

        fora = Path(self._tmp.name).parent / f"acervo-{Path(self._tmp.name).name}"
        fora.mkdir()
        self.addCleanup(shutil.rmtree, fora, True)
        (fora / "artigo.md").write_text(conteudo, encoding="utf-8")
        (self.ws / "Prumo" / "Arquivo").mkdir(parents=True)
        (self.ws / "Prumo" / "Arquivo" / "Acervo").symlink_to(fora, target_is_directory=True)

        ficha.unlink()
        report = self.snapshot("t2")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("Referencias/artigo.md"))
        self.assertEqual(alerta["state"], curated.GONE, "gêmeo externo rebaixou deleção real")


class ManifestoVenenosoTest(BaseTest):
    """Manifesto malformado não pode DESLIGAR o mecanismo: o boundary só
    registra, então uma pane repetida trava o snapshot em todo ritual
    (Codex, 262H-1)."""

    def _corromper(self, stamp: str, **campos) -> None:
        alvo = self.scope_root() / stamp / curated.MANIFEST_NAME
        manifesto = json.loads(alvo.read_text(encoding="utf-8"))
        manifesto.update(campos)
        alvo.write_text(json.dumps(manifesto), encoding="utf-8")

    def test_oversized_com_item_nao_string_nao_trava(self) -> None:
        self.snapshot("t1")
        self._corromper("t1", oversized=[{}])
        self.indice().write_text("mudou", encoding="utf-8")
        report = self.snapshot("t2")

        self.assertTrue((self.scope_root() / "t2").is_dir(), "parou de gravar snapshot")
        self.assertTrue(any("sem manifesto válido" in e for e in report["errors"]))

    def test_oversized_repetido_e_recusado(self) -> None:
        self.snapshot("t1")
        self._corromper("t1", oversized=["a.md", "a.md"])
        self.indice().write_text("mudou", encoding="utf-8")
        report = self.snapshot("t2")
        self.assertTrue(any("sem manifesto válido" in e for e in report["errors"]))


class BaselineNaoTextoTest(BaseTest):
    """Digest confere bytes, não prova que continuam sendo texto. Cópia com
    bytes inválidos e digest coerente virava régua (Codex, 262H-3)."""

    def test_copia_nao_utf8_nao_serve_de_regua(self) -> None:
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")

        copia = self.scope_root() / "t1" / "Prumo__Referencias__INDICE.md"
        veneno = b"\xff\xfe" + b"a" * 998
        copia.write_bytes(veneno)
        manifesto_path = self.scope_root() / "t1" / curated.MANIFEST_NAME
        manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
        manifesto["digests"]["Prumo__Referencias__INDICE.md"] = curated._digest(veneno)
        manifesto_path.write_text(json.dumps(manifesto), encoding="utf-8")

        self.indice().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t2")

        self.assertTrue(
            any("não é UTF-8 válido" in e for e in report["errors"]),
            "régua com bytes inválidos foi aceita",
        )
        self.assertTrue((self.scope_root() / "t2").is_dir())


class CercaAntesDoAtalhoTest(BaseTest):
    """A cerca do destino rodava DEPOIS do dedupe: com `.prumo/backups`
    symlinkado pra fora e uma baseline externa equivalente, o atalho
    `sem-mudanca` passava por baixo dela (Codex, 262H-2)."""

    def test_baseline_externa_equivalente_nao_vira_atalho(self) -> None:
        # Snapshot legítimo primeiro, pra ter uma baseline equivalente.
        self.snapshot("t1")
        externo = Path(self._tmp.name).parent / f"ext-{Path(self._tmp.name).name}"
        shutil.move(str(self.ws / ".prumo" / "backups"), str(externo))
        self.addCleanup(shutil.rmtree, externo, True)
        (self.ws / ".prumo" / "backups").symlink_to(externo, target_is_directory=True)

        report = self.snapshot("t2")

        self.assertNotEqual(
            report["skipped"], "sem-mudanca",
            "atalho passou por baixo da cerca do destino",
        )
        self.assertTrue(any("symlink" in e for e in report["errors"]))


class CresceuNaoSumiuTest(BaseTest):
    """Arquivo que CRESCEU além do teto saía de `current` e era anunciado como
    SUMIU — a sirene de perda tocando pra um arquivo que aumentou
    (Codex, 262I-1)."""

    def _ficha(self) -> Path:
        return self.ws / "Prumo" / "Referencias" / "transcricao.md"

    def test_crescer_alem_do_teto_nao_e_sumico(self) -> None:
        self._ficha().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")

        self._ficha().write_text("a" * (curated.MAX_FILE_BYTES + 10), encoding="utf-8")
        report = self.snapshot("t2")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("transcricao.md"))
        self.assertEqual(alerta["state"], curated.UNMEASURABLE)
        texto = curated.render_report(report)
        self.assertNotIn("SUMIU", texto)

    def test_falha_de_leitura_nao_e_sumico(self) -> None:
        self._ficha().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")

        alvo = self._ficha().resolve()
        real = Path.read_bytes

        def falha(self, *a, **kw):
            if self.resolve() == alvo:
                raise OSError("disco pifou")
            return real(self, *a, **kw)

        with patch.object(Path, "read_bytes", falha):
            report = self.snapshot("t2")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("transcricao.md"))
        self.assertEqual(alerta["state"], curated.UNMEASURABLE)

    def test_sumico_de_verdade_continua_sumico(self) -> None:
        """Negativa: sem o arquivo em disco, é perda."""
        self._ficha().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        self._ficha().unlink()
        report = self.snapshot("t2")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("transcricao.md"))
        self.assertEqual(alerta["state"], curated.GONE)


class PisoDoSumicoTest(BaseTest):
    """O piso protege contra ruído PROPORCIONAL. Sumiço não é proporção."""

    def test_curado_pequeno_que_some_alarma(self) -> None:
        self.snapshot("t1")  # SAUDE.md nasce com ~12 bytes
        (self.ws / "Prumo" / "Agente" / "SAUDE.md").unlink()
        report = self.snapshot("t2")

        alerta = next((a for a in report["alerts"] if a["path"].endswith("SAUDE.md")), None)
        self.assertIsNotNone(alerta, "curado pequeno sumiu sem alarme")
        self.assertEqual(alerta["state"], curated.GONE)

    def test_curado_pequeno_que_so_encolhe_nao_alarma(self) -> None:
        """Negativa: encolher pouco em arquivo minúsculo continua silencioso."""
        self.snapshot("t1")
        (self.ws / "Prumo" / "Agente" / "SAUDE.md").write_text("#", encoding="utf-8")
        report = self.snapshot("t2")
        self.assertEqual(
            [a for a in report["alerts"] if a["path"].endswith("SAUDE.md")], []
        )


class CaminhoDaCopiaTest(BaseTest):
    def test_previous_copy_aponta_o_arquivo_restauravel(self) -> None:
        """A mensagem promete 'a cópia está aqui' — tem de cumprir, não mandar
        o usuário garimpar o diretório."""
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        self.indice().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t2")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("INDICE.md"))
        copia = Path(alerta["previous_copy"])
        self.assertTrue(copia.is_file(), f"`previous_copy` não é arquivo: {copia}")
        self.assertEqual(copia.read_text(encoding="utf-8"), "a" * 1000)


class ReguaPorArquivoTest(BaseTest):
    """Um carimbo só como régua tinha buraco: arquivo que passa do teto sai do
    inventário daquele carimbo, e o carimbo continua COMPLETO (oversized é
    estado conhecido, não falha). No dia seguinte, mutilado de volta abaixo do
    teto, ele parecia não ter história — jogando fora a cópia mensurável de
    antes de ontem (Codex, 262J-1)."""

    def _ficha(self) -> Path:
        return self.ws / "Prumo" / "Referencias" / "transcricao.md"

    def test_buraco_de_oversized_nao_apaga_a_regua(self) -> None:
        self._ficha().write_text("a" * 2000, encoding="utf-8")
        self.snapshot("t1")                                   # mensurável

        self._ficha().write_text("a" * (curated.MAX_FILE_BYTES + 10), encoding="utf-8")
        self.snapshot("t2")                                   # oversized, completo

        self._ficha().write_text("a" * 100, encoding="utf-8")  # volta mutilado
        report = self.snapshot("t3")

        alerta = next(
            (a for a in report["alerts"] if a["path"].endswith("transcricao.md")), None
        )
        self.assertIsNotNone(alerta, "encolhimento de 95% passou calado pelo buraco")
        self.assertEqual(alerta["before_bytes"], 2000)
        self.assertIn("t1", alerta["previous_copy"], "não usou a régua mensurável mais recente")

    def test_regua_por_arquivo_prefere_a_mais_nova(self) -> None:
        """Negativa: com o arquivo presente em vários carimbos, vale o mais
        novo — a composição não pode virar arqueologia."""
        self._ficha().write_text("a" * 3000, encoding="utf-8")
        self.snapshot("t1")
        self._ficha().write_text("a" * 2000, encoding="utf-8")
        self.snapshot("t2")
        self._ficha().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t3")

        alerta = next(a for a in report["alerts"] if a["path"].endswith("transcricao.md"))
        self.assertEqual(alerta["before_bytes"], 2000)
        self.assertIn("t2", alerta["previous_copy"])


class RelatorioNaoMensuravelTest(BaseTest):
    """O estado existia no JSON mas o texto imprimia `antes → 0 bytes (−0%)`:
    trocar 'SUMIU' por outra ficção contábil não resolve (Codex, 262J-2)."""

    def test_texto_diz_nao_mensuravel(self) -> None:
        ficha = self.ws / "Prumo" / "Referencias" / "transcricao.md"
        ficha.write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        ficha.write_text("a" * (curated.MAX_FILE_BYTES + 10), encoding="utf-8")
        report = self.snapshot("t2")

        texto = curated.render_report(report)
        self.assertIn("fora da medição", texto)
        self.assertNotIn("SUMIU", texto)
        self.assertNotIn("0 bytes (−0%)", texto)
        self.assertIn("tinha 1000 bytes", texto)

    def test_encolhimento_de_verdade_continua_com_numeros(self) -> None:
        """Negativa: o caso normal não pode virar 'não-mensurável'."""
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        self.indice().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t2")

        texto = curated.render_report(report)
        self.assertIn("1000 → 100 bytes", texto)
        self.assertNotIn("fora da medição", texto)



class HistoricoLongoTest(BaseTest):
    """Limitar a busca aos N carimbos mais recentes só adiava o esquecimento:
    com o arquivo grande por N rituais seguidos, a cópia boa continuava retida
    em disco e fora do alcance (Codex, rodada 8)."""

    def _ficha(self) -> Path:
        return self.ws / "Prumo" / "Referencias" / "transcricao.md"

    def test_regua_atravessa_mais_de_oito_buracos(self) -> None:
        self._ficha().write_text("a" * 2000, encoding="utf-8")
        self.snapshot("t01")                                  # única cópia mensurável

        self._ficha().write_text("a" * (curated.MAX_FILE_BYTES + 10), encoding="utf-8")
        for n in range(2, 14):                                # 12 carimbos com o buraco
            self.indice().write_text(f"volta {n}\n" * 40, encoding="utf-8")
            self.snapshot(f"t{n:02d}")

        self._ficha().write_text("a" * 100, encoding="utf-8")  # volta mutilado
        report = self.snapshot("t99")

        alerta = next(
            (a for a in report["alerts"] if a["path"].endswith("transcricao.md")), None
        )
        self.assertIsNotNone(alerta, "a régua desenvolveu amnésia depois de 8 carimbos")
        self.assertEqual(alerta["before_bytes"], 2000)
        self.assertIn("t01", alerta["previous_copy"])

    def test_caso_comum_le_um_carimbo_so(self) -> None:
        """Negativa de custo: sem buraco, a caminhada para no primeiro."""
        self.indice().write_text("a" * 1000, encoding="utf-8")
        for n in range(1, 6):
            self.indice().write_text(f"volta {n}\n" * 40, encoding="utf-8")
            self.snapshot(f"t{n}")

        lidos: list[str] = []
        real = curated._validate_candidate

        def espiao(stamp_dir, manifest):
            lidos.append(stamp_dir.name)
            return real(stamp_dir, manifest)

        with patch.object(curated, "_validate_candidate", espiao):
            self.indice().write_text("a" * 100, encoding="utf-8")
            self.snapshot("t9")

        self.assertEqual(len(lidos), 1, f"leu {len(lidos)} carimbos: {lidos}")


class ManifestoMapeamentoTest(BaseTest):
    """#265, item 1: o manifesto é conferido em estrutura, digest e UTF-8, mas
    o mapeamento `flat → rel` nunca era verificado contra a função que o gerou.

    Adulteração COERENTE — `files` e `digests` internamente consistentes, com o
    nome achatado trocado — passava na validação e fazia `previous_copy`
    apontar pra um arquivo que não existe. Não é vetor prático de dano (exige
    editar o backup à mão), mas `previous_copy` é uma promessa ("a cópia está
    aqui") e promessa tem que ser verificável.
    """

    def _adulterar_flat(self, stamp: str) -> str:
        """Troca o nome achatado de uma entrada mantendo tudo o mais coerente."""
        stamp_dir = self.scope_root() / stamp
        manifest = json.loads((stamp_dir / curated.MANIFEST_NAME).read_text(encoding="utf-8"))
        flat, rel = next(iter(manifest["files"].items()))
        impostor = "Impostor__" + str(flat)
        (stamp_dir / str(flat)).rename(stamp_dir / impostor)
        manifest["files"] = {
            (impostor if k == flat else k): v for k, v in manifest["files"].items()
        }
        manifest["digests"] = {
            (impostor if k == flat else k): v for k, v in manifest["digests"].items()
        }
        (stamp_dir / curated.MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(rel)

    def test_manifesto_com_flat_trocado_nao_serve_de_regua(self) -> None:
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        self._adulterar_flat("t1")

        self.indice().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t2")

        self.assertTrue(
            any("t1" in e and "não serve de régua" in e for e in report["errors"]),
            f"manifesto adulterado passou como régua; errors={report['errors']}",
        )

    def test_manifesto_integro_continua_servindo(self) -> None:
        """Negativa: a checagem nova não pode recusar manifesto legítimo."""
        self.indice().write_text("a" * 1000, encoding="utf-8")
        self.snapshot("t1")
        self.indice().write_text("a" * 100, encoding="utf-8")
        report = self.snapshot("t2")

        self.assertEqual(
            [e for e in report["errors"] if "não serve de régua" in e],
            [],
            "manifesto íntegro foi recusado",
        )
        self.assertTrue(
            any(a["path"].endswith("INDICE.md") for a in report["alerts"]),
            "sem régua válida o encolhimento passou calado",
        )


class TetoDoAcervoTest(BaseTest):
    """#265, item 2: a coleta dos curados respeita `MAX_FILE_BYTES`, mas o
    índice do acervo lia TODO `*.md` sob `Arquivo/Acervo/` sem teto.

    Um acervo com arquivos grandes fazia o ritual pagar leitura integral deles
    só pra decidir se um sumiço foi arquivamento.
    """

    def _acervo(self) -> Path:
        raiz = self.ws / "Prumo" / "Arquivo" / "Acervo"
        raiz.mkdir(parents=True, exist_ok=True)
        return raiz

    def test_arquivo_acima_do_teto_nao_entra_no_indice(self) -> None:
        grande = self._acervo() / "transcricao-gigante.md"
        conteudo = b"z" * (curated.MAX_FILE_BYTES + 10)
        grande.write_bytes(conteudo)

        indice = curated._acervo_index(workspace_paths(self.ws))

        self.assertNotIn(
            curated._digest(conteudo),
            indice,
            "arquivo acima do teto entrou no índice — o custo de leitura foi pago",
        )

    def test_arquivo_dentro_do_teto_continua_entrando(self) -> None:
        """Negativa: o teto não pode cegar o índice pro caso normal, senão
        arquivamento legítimo volta a virar alarme de sumiço."""
        pequeno = self._acervo() / "artigo.md"
        conteudo = b"conteudo normal\n" * 10
        pequeno.write_bytes(conteudo)

        indice = curated._acervo_index(workspace_paths(self.ws))

        self.assertIn(curated._digest(conteudo), indice)


if __name__ == "__main__":
    unittest.main()
