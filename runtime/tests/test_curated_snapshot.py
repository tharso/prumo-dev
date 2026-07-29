"""Snapshot de arquivo curado (#262, P8+P9 do relatório de incidente de 29/07).

Em 27/07 uma sessão reescreveu `Prumo/Referencias/INDICE.md` com escrita
integral querendo acrescentar 4 linhas: 48 entradas viraram 5. O dano ficou
invisível por dois dias e nenhum backup do produto cobria o caminho de edição
comum — todos os scopes existentes são disparados por comando do runtime.

Cada teste aqui cobre uma obrigação do contrato; os negativos existem porque
guard que não reprova o que proíbe é decoração (série #241/#248/#258).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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
        self.assertEqual(curated.watch_class("Prumo/REGISTRO.md"), curated.FLOW)
        self.assertEqual(curated.watch_class("Prumo/Agente/PROJETOS.md"), curated.HYBRID)
        self.assertEqual(
            curated.watch_class("Prumo/Referencias/INDICE.md"), curated.ACCUMULATIVE
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
    descoberto — o achado que reabriu o desenho na revisão."""

    def test_seed_dispara_o_snapshot(self) -> None:
        from prumo_runtime.commands import seed as seed_cmd

        self.assertIn(
            "snapshot_curated", seed_cmd.run_seed.__code__.co_names,
            "a rota do Cowork (`prumo seed`) não dispara o snapshot",
        )

    def test_briefing_dispara_o_snapshot(self) -> None:
        from prumo_runtime.commands import briefing as briefing_cmd

        self.assertIn(
            "snapshot_curated", briefing_cmd.run_briefing.__code__.co_names,
            "`prumo briefing` não dispara o snapshot",
        )

    def test_construtores_de_payload_nao_escrevem(self) -> None:
        """Codex r1: 'consulta com efeito colateral é casca de banana
        arquitetural'. O snapshot é chamada explícita do comando, nunca efeito
        escondido em função de construção."""
        from prumo_runtime.commands import briefing as briefing_cmd
        from prumo_runtime.commands import seed as seed_cmd

        for fn in (briefing_cmd.build_briefing_payload, seed_cmd.build_seed_payload):
            self.assertNotIn(
                "snapshot_curated", fn.__code__.co_names,
                f"{fn.__name__} ganhou escrita surpresa",
            )


if __name__ == "__main__":
    unittest.main()
