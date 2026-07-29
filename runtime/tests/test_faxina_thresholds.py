"""Thresholds efetivos na semente (#258).

A tentativa de tirar o `faxina-thresholds.md` da rota sempre-carregada (corte
D2 da #228) foi revertida no gate porque a semente transportava só
`stale_days_threshold`. Estes testes cobrem os três cenários exigidos na issue
— sem semente, semente sem override, semente com override — mais a paridade
entre o doc (que o agente lê) e o código (que o runtime aplica).
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "runtime"))

from prumo_runtime import faxina_thresholds  # noqa: E402

DOC = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "faxina-thresholds.md"
ESTADO = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-estado.md"
SKILL = REPO_ROOT / "skills" / "briefing" / "SKILL.md"

_ROW = re.compile(r"^\|\s*([a-z_][a-z0-9_]*)\s*\|\s*(\d+)\s*\|", re.MULTILINE)


def _ws_with_override(tmp: Path, texto: str | None) -> Path:
    ws = tmp / "ws"
    (ws / "Prumo" / "Custom" / "rules").mkdir(parents=True)
    if texto is not None:
        (ws / "Prumo" / "Custom" / "rules" / "faxina-thresholds.md").write_text(
            texto, encoding="utf-8"
        )
    return ws


class ParidadeDocCodigoTest(unittest.TestCase):
    def test_defaults_do_codigo_batem_com_a_tabela_do_doc(self) -> None:
        """Duas projeções do mesmo dado: divergir é o bug da #195 em outra roupa.

        Primeiro TODA linha de dados das tabelas tem de obedecer à gramática
        (`| chave_snake | inteiro | ... |`) — senão uma linha malformada só no
        doc passaria despercebida (Codex, diff r1). Só então compara.
        """
        texto = DOC.read_text(encoding="utf-8")
        linhas = [
            ln for ln in texto.splitlines()
            if ln.startswith("|") and not set(ln) <= {"|", "-", " ", ":"}
            and "Parâmetro" not in ln
        ]
        self.assertTrue(linhas, "nenhuma linha de dados nas tabelas do doc")
        fora_da_gramatica = [ln for ln in linhas if not _ROW.match(ln)]
        self.assertEqual(
            fora_da_gramatica, [],
            "linha de threshold fora da gramática (chave snake_case + inteiro)",
        )
        do_doc = {k: int(v) for k, v in _ROW.findall(texto)}
        self.assertEqual(len(do_doc), len(linhas), "chave duplicada nas tabelas do doc")
        self.assertEqual(
            do_doc,
            faxina_thresholds.DEFAULTS,
            "defaults do runtime ≠ tabela do faxina-thresholds.md",
        )


class FonteUnicaTest(unittest.TestCase):
    """[P2 da r5]: literal de threshold fora do módulo dono é segunda fonte de
    verdade — hoje o fluxo produtivo passa o valor, mas uma chamada futura sem
    argumento divergiria em silêncio."""

    def test_nenhum_literal_de_threshold_fora_do_dono(self) -> None:
        import re as _re
        runtime_dir = REPO_ROOT / "runtime" / "prumo_runtime"
        dono = runtime_dir / "faxina_thresholds.py"
        # Formas REAIS de consumo (Codex r6): constante de módulo, campo de
        # dataclass e default de argparse — não só duas atribuições nomeadas.
        nomes = "|".join(
            ["_PROCESSED_STALE_DAYS", "BACKUP_EXPIRY_DAYS", "CACHE_DAYS"]
            + [k.upper() for k in faxina_thresholds.DEFAULTS]
            + list(faxina_thresholds.DEFAULTS)
            + ["backup_expiry_days", "cache_days", "backup-expiry-days", "cache-days"]
        )
        valores = "|".join(str(v) for v in sorted(set(faxina_thresholds.DEFAULTS.values())))
        padroes = (
            # cobre `NOME = 90`, `nome: int = 90` (dataclass) e `nome=90`
            _re.compile(rf"^\s*({nomes})\s*(?::\s*\w+\s*)?=\s*({valores})\b", _re.M),
            _re.compile(rf"--({nomes})\"[^)]*?default\s*=\s*({valores})\b", _re.S),
        )
        offenders = []
        for py in sorted(runtime_dir.rglob("*.py")):
            if py == dono:
                continue
            texto = py.read_text(encoding="utf-8")
            for padrao in padroes:
                for m in padrao.finditer(texto):
                    offenders.append(f"{py.name}:{m.group(1)}={m.group(2)}")
        self.assertEqual(
            offenders, [], f"threshold com literal fora da fonte única: {offenders}"
        )

    def test_guard_pega_literal_reintroduzido(self) -> None:
        """Fixture negativa: as três formas reais de consumo TÊM de ser
        detectadas — guard que não pega o que existia é decoração."""
        import re as _re
        nomes = "|".join(
            ["_PROCESSED_STALE_DAYS", "BACKUP_EXPIRY_DAYS", "CACHE_DAYS"]
            + [k.upper() for k in faxina_thresholds.DEFAULTS]
            + list(faxina_thresholds.DEFAULTS)
            + ["backup_expiry_days", "cache_days", "backup-expiry-days", "cache-days"]
        )
        valores = "|".join(str(v) for v in sorted(set(faxina_thresholds.DEFAULTS.values())))
        padroes = (
            _re.compile(rf"^\s*({nomes})\s*(?::\s*\w+\s*)?=\s*({valores})\b", _re.M),
            _re.compile(rf"--({nomes})\"[^)]*?default\s*=\s*({valores})\b", _re.S),
        )
        for caso in (
            "BACKUP_EXPIRY_DAYS = 90",
            "    backup_expiry_days: int = 90",
            'sanitize.add_argument("--cache-days", type=int, default=30)',
        ):
            with self.subTest(caso=caso.strip()[:40]):
                self.assertTrue(
                    any(p.search(caso) for p in padroes),
                    f"guard não pega literal reintroduzido: {caso!r}",
                )

    def test_default_do_helper_vem_da_fonte_unica(self) -> None:
        from prumo_runtime import local_panorama
        self.assertEqual(
            local_panorama._PROCESSED_STALE_DAYS,
            faxina_thresholds.DEFAULTS["processed_expiry_days"],
        )


class OverrideTest(unittest.TestCase):
    def test_sem_override_usa_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws_with_override(Path(tmp), None)
            eff = faxina_thresholds.effective(ws)
        self.assertEqual(eff["source"], "default")
        self.assertEqual(eff["values"], faxina_thresholds.DEFAULTS)
        self.assertEqual(eff["override_keys"], [])

    def test_override_aplica_so_o_declarado(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws_with_override(
                Path(tmp),
                "# Thresholds customizados\n\n- max_items: 100\n- processed_expiry_days: 7\n",
            )
            eff = faxina_thresholds.effective(ws)
        self.assertEqual(eff["source"], "override")
        self.assertEqual(eff["values"]["max_items"], 100)
        self.assertEqual(eff["values"]["processed_expiry_days"], 7)
        # o que não foi declarado continua no default
        self.assertEqual(
            eff["values"]["diario_expiry_days"], faxina_thresholds.DEFAULTS["diario_expiry_days"]
        )
        self.assertEqual(eff["override_keys"], ["max_items", "processed_expiry_days"])

    def test_todo_candidato_invalido_aparece_em_ignored_keys(self) -> None:
        """Vocabulário controlado: apelido não é override, é dialeto — e some
        sem rastro é pior que rejeitado (Codex, diff r1). Cobre chave inventada,
        MAIÚSCULA, hífen, valor não-inteiro, negativo e float."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws_with_override(
                Path(tmp),
                "- max_items: 100\n"
                "- limite_maximo: 999\n"
                "- MAX_ITEMS: 7\n"
                "- limite-maximo: 5\n"
                "- archive_age_days: trinta\n"
                "- cache_expiry_days: -3\n"
                "- diario_expiry_days: 1.5\n",
            )
            eff = faxina_thresholds.effective(ws)
        self.assertEqual(eff["values"]["max_items"], 100)
        for chave in ("archive_age_days", "cache_expiry_days", "diario_expiry_days"):
            with self.subTest(chave=chave):
                self.assertEqual(eff["values"][chave], faxina_thresholds.DEFAULTS[chave])
        self.assertEqual(
            eff["ignored_keys"],
            ["MAX_ITEMS", "archive_age_days", "cache_expiry_days",
             "diario_expiry_days", "limite-maximo", "limite_maximo"],
        )


class SementeTest(unittest.TestCase):
    def _panorama(self, override: str | None) -> dict:
        from prumo_runtime import faxina_thresholds as ft
        from prumo_runtime.local_panorama import build_local_panorama

        with tempfile.TemporaryDirectory() as tmp:
            ws = _ws_with_override(Path(tmp), override)
            (ws / "Prumo").mkdir(exist_ok=True)
            for nome, conteudo in (
                ("PAUTA.md", "# Pauta\n\n## Quente\n\n- item\n"),
                ("INBOX.md", "# Inbox\n"),
                ("REGISTRO.md", "# Registro\n\n| Data | Origem |\n|---|---|\n| 01/07 | x |\n"),
            ):
                (ws / "Prumo" / nome).write_text(conteudo, encoding="utf-8")
            panorama, _ = build_local_panorama(
                pauta_path=ws / "Prumo" / "PAUTA.md",
                inbox_path=ws / "Prumo" / "INBOX.md",
                registro_path=ws / "Prumo" / "REGISTRO.md",
                processed_path=ws / "Prumo" / "Inbox4Mobile" / "_processed.json",
                preview={},
                today=__import__("datetime").date(2026, 7, 28),
                thresholds=ft.effective(ws),
            )
            return panorama

    def test_semente_sem_override_declara_default(self) -> None:
        faxina = self._panorama(None)["faxina"]
        self.assertEqual(faxina["schema"], faxina_thresholds.SCHEMA)
        self.assertEqual(faxina["thresholds_source"], "default")
        self.assertEqual(faxina["thresholds"], faxina_thresholds.DEFAULTS)
        self.assertEqual(
            faxina["stale_days_threshold"],
            faxina_thresholds.DEFAULTS["processed_expiry_days"],
        )

    def test_semente_com_override_transporta_o_efetivo(self) -> None:
        """O buraco que reverteu o D2: `max_items` e `diario_expiry_days` agora
        viajam na semente, não só o de processados."""
        faxina = self._panorama(
            "- max_items: 100\n- diario_expiry_days: 30\n- processed_expiry_days: 7\n"
        )["faxina"]
        self.assertEqual(faxina["thresholds_source"], "override")
        self.assertEqual(faxina["thresholds"]["max_items"], 100)
        self.assertEqual(faxina["thresholds"]["diario_expiry_days"], 30)
        self.assertEqual(faxina["stale_days_threshold"], 7, "o efetivo tem de mandar")
        self.assertEqual(
            faxina["override_keys"],
            ["diario_expiry_days", "max_items", "processed_expiry_days"],
        )

    def test_contagem_de_processados_usa_o_efetivo(self) -> None:
        """Antes o pré-cálculo usava sempre o default: a semente declarava um
        número e contava por outro. Teste COMPORTAMENTAL — item de 5 dias é
        fresco no default (14) e velho com override de 1."""
        from datetime import date, timedelta
        from prumo_runtime import faxina_thresholds as ft
        from prumo_runtime.local_panorama import build_local_panorama

        hoje = date(2026, 7, 28)
        processados = json.dumps({
            "version": "1.0",
            "items": [{
                "filename": "x.txt",
                "processed_at": (hoje - timedelta(days=5)).isoformat(),
                "status": "processed",
            }],
        })
        for override, esperado_stale, esperado_thr in (
            (None, 0, 14),
            ("- processed_expiry_days: 1\n", 1, 1),
        ):
            with self.subTest(override=override):
                with tempfile.TemporaryDirectory() as tmp:
                    ws = _ws_with_override(Path(tmp), override)
                    proc = ws / "Prumo" / "Inbox4Mobile" / "_processed.json"
                    proc.parent.mkdir(parents=True, exist_ok=True)
                    proc.write_text(processados, encoding="utf-8")
                    panorama, _ = build_local_panorama(
                        pauta_path=ws / "Prumo" / "PAUTA.md",
                        inbox_path=ws / "Prumo" / "INBOX.md",
                        registro_path=ws / "Prumo" / "REGISTRO.md",
                        processed_path=proc,
                        preview={},
                        today=hoje,
                        thresholds=ft.effective(ws),
                    )
                f = panorama["faxina"]
                self.assertEqual(f["processed_stale_entries"], esperado_stale)
                self.assertEqual(f["stale_days_threshold"], esperado_thr)


class PontaAPontaTest(unittest.TestCase):
    """[P2-3 do gate]: provar os CALL SITES produtivos, não só os helpers com o
    threshold passado à mão — senão briefing/seed poderiam parar de passá-lo e
    a suíte seguiria verde."""

    def _ws(self, tmp: Path, *, com_override: bool = True) -> Path:
        from prumo_runtime.workspace import (
            WorkspaceConfig, create_missing_files, ensure_directories, install_skills,
        )
        ws = tmp / "ws"
        cfg = WorkspaceConfig(
            workspace=ws, user_name="T", agent_name="Prumo",
            timezone_name="America/Sao_Paulo", briefing_time="09:00",
            layout_mode="nested", workspace_name="W",
        )
        ensure_directories(ws)
        install_skills(ws, layout_mode="nested")
        create_missing_files(cfg)
        (ws / "Prumo" / "Custom" / "rules").mkdir(parents=True, exist_ok=True)
        if com_override:
            (ws / "Prumo" / "Custom" / "rules" / "faxina-thresholds.md").write_text(
                "- max_items: 99\n- processed_expiry_days: 1\n", encoding="utf-8"
            )
        from datetime import date, timedelta
        proc = ws / "Prumo" / "Inbox4Mobile" / "_processed.json"
        proc.parent.mkdir(parents=True, exist_ok=True)
        proc.write_text(json.dumps({"version": "1.0", "items": [{
            "filename": "x.txt",
            "processed_at": (date.today() - timedelta(days=3)).isoformat(),
            "status": "processed",
        }]}), encoding="utf-8")
        return ws

    def test_semente_persistida_transporta_o_efetivo(self) -> None:
        from argparse import Namespace
        from prumo_runtime.commands.seed import run_seed
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            with redirect_stdout(io.StringIO()):
                run_seed(Namespace(workspace=str(ws), format="json"))
            payload = json.loads(
                (ws / ".prumo" / "state" / "local-panorama.json").read_text(encoding="utf-8")
            )
        faxina = payload["local_panorama"]["faxina"]
        self.assertEqual(faxina["thresholds"]["max_items"], 99)
        self.assertEqual(faxina["stale_days_threshold"], 1)
        self.assertEqual(faxina["thresholds_source"], "override")
        # a CONTAGEM segue o efetivo: item de 3 dias é velho com override de 1
        self.assertEqual(faxina["processed_stale_entries"], 1)
        # [P1-1]: o override é FONTE no controle de frescor
        self.assertIn("faxina_override", payload["source_mtimes"])
        self.assertIsNotNone(payload["source_mtimes"]["faxina_override"])

    def test_semente_persistida_sem_override_conta_pelo_default(self) -> None:
        """[P1 da r3]: o MESMO item de 3 dias tem de ficar FRESCO no default 14
        — pela semente persistida, não pelo helper chamado à mão."""
        from argparse import Namespace
        from contextlib import redirect_stdout
        import io
        from prumo_runtime.commands.seed import run_seed

        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp), com_override=False)
            with redirect_stdout(io.StringIO()):
                run_seed(Namespace(workspace=str(ws), format="json"))
            faxina = json.loads(
                (ws / ".prumo" / "state" / "local-panorama.json").read_text(encoding="utf-8")
            )["local_panorama"]["faxina"]
        self.assertEqual(faxina["thresholds_source"], "default")
        self.assertEqual(faxina["stale_days_threshold"], 14)
        self.assertEqual(
            faxina["processed_stale_entries"], 0,
            "item de 3 dias tem de ser FRESCO sob o default de 14",
        )

    def test_editar_override_depois_do_seed_e_detectavel(self) -> None:
        """[P1 da r2]: o zumbi morre quando a divergência é VISÍVEL ao
        consumidor — mtime do override na semente ≠ mtime atual."""
        from argparse import Namespace
        from contextlib import redirect_stdout
        import io, os, time
        from prumo_runtime.commands.seed import run_seed

        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            with redirect_stdout(io.StringIO()):
                run_seed(Namespace(workspace=str(ws), format="json"))
            semente = json.loads(
                (ws / ".prumo" / "state" / "local-panorama.json").read_text(encoding="utf-8")
            )
            antes = semente["source_mtimes"]["faxina_override"]
            override = ws / "Prumo" / "Custom" / "rules" / "faxina-thresholds.md"
            time.sleep(0.01)
            override.write_text("- max_items: 7\n", encoding="utf-8")
            agora = os.stat(override).st_mtime_ns
        self.assertNotEqual(
            antes["mtime_ns"], agora,
            "editar o override depois do seed tem de ser detectável pelo frescor",
        )

    def test_remover_override_depois_do_seed_e_detectavel(self) -> None:
        from argparse import Namespace
        from contextlib import redirect_stdout
        import io
        from prumo_runtime.commands.seed import run_seed

        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            with redirect_stdout(io.StringIO()):
                run_seed(Namespace(workspace=str(ws), format="json"))
            semente = json.loads(
                (ws / ".prumo" / "state" / "local-panorama.json").read_text(encoding="utf-8")
            )
            override = ws / "Prumo" / "Custom" / "rules" / "faxina-thresholds.md"
            override.rename(override.with_suffix(".md.bak"))  # remover = mover (#242)
            ainda_existe = override.exists()
        self.assertIsNotNone(semente["source_mtimes"]["faxina_override"])
        self.assertFalse(ainda_existe)

    def test_contrato_manda_invalidar_o_bloco_faxina(self) -> None:
        """Detectar sem mandar recompor deixaria o consumidor com número velho."""
        flat = re.sub(r"\s+", " ", ESTADO.read_text(encoding="utf-8"))
        self.assertIn("invalida o bloco `faxina` inteiro", flat)
        self.assertIn("recontar", flat)


class ContratoTest(unittest.TestCase):
    def test_estado_le_da_semente_com_fallback_declarado(self) -> None:
        flat = re.sub(r"\s+", " ", ESTADO.read_text(encoding="utf-8"))
        self.assertIn("`faxina.thresholds` da semente", flat)
        self.assertIn("sem semente", flat.lower())
        self.assertNotIn(
            "(F1, já carregado)", flat, "promessa órfã: o doc não carrega mais sempre"
        )

    def test_schema_aceito_e_publicado_pro_agente(self) -> None:
        """[P1-2]: "desconhecido" sem lista de conhecidos é horóscopo."""
        flat = re.sub(r"\s+", " ", ESTADO.read_text(encoding="utf-8"))
        self.assertIn(faxina_thresholds.SCHEMA, flat)
        self.assertIn("único aceito", flat)
        self.assertIn("faxina_override", flat.replace("override de thresholds", "faxina_override"))

    def test_manifesto_volta_a_condicionar_o_doc(self) -> None:
        texto = SKILL.read_text(encoding="utf-8")
        linha = [ln for ln in texto.splitlines() if "faxina-thresholds.md" in ln and "Custom" not in ln]
        self.assertTrue(linha, "linha do faxina-thresholds sumiu do manifesto")
        self.assertIn("sem semente", linha[0].lower(), "o doc voltou a carregar sempre")


if __name__ == "__main__":
    unittest.main()


class DominioPorChaveTest(unittest.TestCase):
    """Percentual acima de 100 é inatingível: o alerta da #262 desligaria em
    silêncio, que é pior que não existir. Fora do domínio é ignorado E
    reportado, como qualquer outro valor inválido do vocabulário controlado."""

    def _override(self, texto: str):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            rules = ws / "Prumo" / "Custom" / "rules"
            rules.mkdir(parents=True)
            (rules / "faxina-thresholds.md").write_text(texto, encoding="utf-8")
            return faxina_thresholds.read_override(ws)

    def test_percentual_acima_de_cem_e_ignorado_e_reportado(self) -> None:
        valores, ignoradas = self._override("- curated_shrink_alert_pct: 150\n")
        self.assertNotIn("curated_shrink_alert_pct", valores)
        self.assertIn("curated_shrink_alert_pct", ignoradas)

    def test_percentual_no_limite_e_aceito(self) -> None:
        valores, ignoradas = self._override("- curated_shrink_alert_pct: 100\n")
        self.assertEqual(valores["curated_shrink_alert_pct"], 100)
        self.assertEqual(ignoradas, [])

    def test_chave_sem_teto_nao_ganha_limite(self) -> None:
        """Negativa: o teto é POR CHAVE, não global."""
        valores, _ = self._override("- max_items: 5000\n")
        self.assertEqual(valores["max_items"], 5000)
