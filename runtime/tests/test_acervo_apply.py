"""Travas de execução destrutiva do `acervo` (#125, Codex rodada 2).

Casos perigosos: hash divergente, ocorrência ambígua, path fora de Prumo/,
arquivo inexistente, referência operacional inapagável, registro antes da
remoção, e o caminho não-destrutivo (arquivar) vs permanente.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from prumo_runtime.acervo import enumerate_limbo
from prumo_runtime.acervo_apply import (
    AcervoSafetyError,
    _within_user_root,
    apply_report,
)
from prumo_runtime.workspace_paths import workspace_paths

TODAY = date(2026, 6, 26)


def _report(items: list[dict]) -> dict:
    return {"schema": "prumo_acervo_report.v1", "items": items}


def _as_report_item(enum_item: dict, verb: str, comment: str | None = None) -> dict:
    keep = ("item_id", "source_kind", "source_path", "anchor", "line_start", "line_end", "content_hash", "title")
    out = {k: enum_item[k] for k in keep}
    out["verb"] = verb
    out["comment"] = comment
    return out


class AcervoApplyTests(unittest.TestCase):
    def _ws(self, root: Path, *, dup: bool = False) -> Path:
        (root / "_state").mkdir(parents=True, exist_ok=True)
        (root / "Referencias").mkdir(parents=True, exist_ok=True)
        ideias = "# Ideias\n\n- Ideia unica de feature\n- Outra ideia qualquer\n"
        if dup:
            ideias = "# Ideias\n\n- Ideia repetida\n- Coisa no meio\n- Ideia repetida\n"
        (root / "IDEIAS.md").write_text(ideias, encoding="utf-8")
        (root / "PAUTA.md").write_text("# Pauta\n\n## Horizonte\n- Item ja existente\n", encoding="utf-8")
        (root / "REGISTRO.md").write_text(
            "# Registro\n\n| Data | Origem | Resumo | Acao | Destino |\n|---|---|---|---|---|\n",
            encoding="utf-8",
        )
        (root / "Referencias" / "INDICE.md").write_text("# Indice\n", encoding="utf-8")
        (root / "Referencias" / "artigo.md").write_text("# Artigo\n\nCorpo.\n", encoding="utf-8")
        return root

    def _enum(self, ws: Path) -> list[dict]:
        return enumerate_limbo(ws, today=TODAY)["items"]

    def _find(self, ws: Path, predicate) -> dict:
        return next(it for it in self._enum(ws) if predicate(it))

    def test_delete_fragment_archives_and_registers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: "unica" in it["snippet"])
            result = apply_report(ws, _report([_as_report_item(item, "delete")]), today=TODAY)
            self.assertEqual(len(result["archived"]), 1)
            self.assertEqual(result["blocked"], [])
            # removido do original
            self.assertNotIn("unica", (ws / "IDEIAS.md").read_text(encoding="utf-8"))
            # foi pra quarentena
            quar = ws / "Arquivo" / "Acervo" / "quarentena-fragmentos.md"
            self.assertTrue(quar.exists())
            self.assertIn("unica", quar.read_text(encoding="utf-8"))
            # registrado ANTES de remover
            self.assertIn("ACERVO", (ws / "REGISTRO.md").read_text(encoding="utf-8"))

    def test_delete_blocks_on_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: "unica" in it["snippet"])
            report = _report([_as_report_item(item, "delete")])
            # o arquivo muda DEPOIS de gerar o relatório
            (ws / "IDEIAS.md").write_text("# Ideias\n\n- Texto totalmente diferente\n", encoding="utf-8")
            result = apply_report(ws, report, today=TODAY)
            self.assertEqual(result["archived"], [])
            self.assertEqual(len(result["blocked"]), 1)
            self.assertIn("mudou ou sumiu", result["blocked"][0]["reason"])

    def test_delete_blocks_on_ambiguous_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp), dup=True)
            item = self._find(ws, lambda it: "repetida" in it["snippet"])
            result = apply_report(ws, _report([_as_report_item(item, "delete")]), today=TODAY)
            self.assertEqual(result["archived"], [])
            self.assertIn("ambígua", result["blocked"][0]["reason"])

    def test_delete_nonexistent_or_operational_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            # operacional nem é enumerado → sem match → bloqueado
            fake = {
                "item_id": "x", "verb": "delete", "source_kind": "referencia",
                "source_path": "Referencias/INDICE.md", "anchor": "INDICE.md",
                "line_start": None, "line_end": None, "content_hash": "deadbeefdeadbeef",
                "title": "INDICE", "comment": None,
            }
            result = apply_report(ws, _report([fake]), today=TODAY)
            self.assertEqual(result["archived"], [])
            self.assertEqual(len(result["blocked"]), 1)

    def test_within_user_root_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "_state").mkdir(parents=True, exist_ok=True)
            paths = workspace_paths(ws)
            with self.assertRaises(AcervoSafetyError):
                _within_user_root(paths, "../../etc/passwd")

    def test_include_pauta_appends_horizonte(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: "Outra ideia" in it["snippet"])
            result = apply_report(
                ws, _report([_as_report_item(item, "include_pauta", "prazo semana que vem")]), today=TODAY
            )
            self.assertEqual(len(result["included"]), 1)
            pauta = (ws / "PAUTA.md").read_text(encoding="utf-8")
            self.assertIn("Outra ideia", pauta)
            self.assertIn("prazo semana que vem", pauta)
            # não removeu o original (include é não-destrutivo)
            self.assertIn("Outra ideia", (ws / "IDEIAS.md").read_text(encoding="utf-8"))

    def test_attack_now_goes_to_for_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            before = (ws / "IDEIAS.md").read_text(encoding="utf-8")
            item = self._find(ws, lambda it: "unica" in it["snippet"])
            result = apply_report(ws, _report([_as_report_item(item, "attack_now")]), today=TODAY)
            self.assertEqual(len(result["for_agent"]), 1)
            self.assertEqual((ws / "IDEIAS.md").read_text(encoding="utf-8"), before)

    def test_permanent_deletes_reference_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: it["source_kind"] == "referencia")
            result = apply_report(ws, _report([_as_report_item(item, "delete")]), permanent=True, today=TODAY)
            self.assertEqual(len(result["archived"]), 1)
            self.assertFalse((ws / "Referencias" / "artigo.md").exists())
            self.assertFalse((ws / "Arquivo" / "Acervo" / "artigo.md").exists())

    def test_reference_archived_to_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: it["source_kind"] == "referencia")
            apply_report(ws, _report([_as_report_item(item, "delete")]), today=TODAY)
            self.assertFalse((ws / "Referencias" / "artigo.md").exists())
            self.assertTrue((ws / "Arquivo" / "Acervo" / "artigo.md").exists())

    def test_schema_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            with self.assertRaises(AcervoSafetyError):
                apply_report(ws, {"schema": "wrong.v9", "items": []}, today=TODAY)

    def test_two_deletes_same_file_remove_the_right_lines(self) -> None:
        # Regressão do achado crítico #1 do Codex: snapshot único do lote usaria
        # line_start/end velhos no 2º delete e cortaria o trecho errado.
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "_state").mkdir(parents=True, exist_ok=True)
            (ws / "REGISTRO.md").write_text("# Registro\n", encoding="utf-8")
            (ws / "IDEIAS.md").write_text(
                "# Ideias\n\n- alpha primeira\n- beta meio\n- gamma terceira\n", encoding="utf-8"
            )
            items = enumerate_limbo(ws, today=TODAY)["items"]
            alpha = next(it for it in items if "alpha" in it["snippet"])
            gamma = next(it for it in items if "gamma" in it["snippet"])
            result = apply_report(
                ws, _report([_as_report_item(alpha, "delete"), _as_report_item(gamma, "delete")]), today=TODAY
            )
            self.assertEqual(len(result["archived"]), 2)
            self.assertEqual(result["blocked"], [])
            remaining = (ws / "IDEIAS.md").read_text(encoding="utf-8")
            self.assertNotIn("alpha", remaining)
            self.assertNotIn("gamma", remaining)
            self.assertIn("beta", remaining)  # o trecho do meio NÃO foi cortado por engano

    def test_reference_collision_does_not_overwrite(self) -> None:
        # Regressão do #4: arquivar duas referências de mesmo nome não sobrescreve.
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: it["source_kind"] == "referencia")
            apply_report(ws, _report([_as_report_item(item, "delete")]), today=TODAY)
            # nova referência de mesmo nome, conteúdo diferente
            (ws / "Referencias" / "artigo.md").write_text("# Artigo v2\n\nOutro corpo.\n", encoding="utf-8")
            item2 = self._find(ws, lambda it: it["source_kind"] == "referencia")
            apply_report(ws, _report([_as_report_item(item2, "delete")]), today=TODAY)
            quarantined = list((ws / "Arquivo" / "Acervo").glob("*.md"))
            self.assertEqual(len(quarantined), 2, "a segunda referência não pode sobrescrever a primeira")

    def test_reference_collision_same_content_gets_unique_name(self) -> None:
        # Mesmo nome + mesmo conteúdo + mesmo dia: nome único (contador), não bloqueia.
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            same = "# Artigo\n\nCorpo.\n"  # conteúdo idêntico ao do _ws
            item = self._find(ws, lambda it: it["source_kind"] == "referencia")
            r1 = apply_report(ws, _report([_as_report_item(item, "delete")]), today=TODAY)
            (ws / "Referencias" / "artigo.md").write_text(same, encoding="utf-8")
            item2 = self._find(ws, lambda it: it["source_kind"] == "referencia")
            r2 = apply_report(ws, _report([_as_report_item(item2, "delete")]), today=TODAY)
            self.assertEqual(len(r1["archived"]), 1)
            self.assertEqual(len(r2["archived"]), 1)
            self.assertEqual(r2["blocked"], [])  # não bloqueou
            self.assertEqual(len(list((ws / "Arquivo" / "Acervo").glob("*.md"))), 2)
            # terceira colisão idêntica → ramo do contador (-2), ainda sem bloqueio
            (ws / "Referencias" / "artigo.md").write_text(same, encoding="utf-8")
            item3 = self._find(ws, lambda it: it["source_kind"] == "referencia")
            r3 = apply_report(ws, _report([_as_report_item(item3, "delete")]), today=TODAY)
            self.assertEqual(r3["blocked"], [])
            quar = list((ws / "Arquivo" / "Acervo").glob("*.md"))
            self.assertEqual(len(quar), 3)
            self.assertTrue(any(p.stem.endswith("-2") for p in quar), "contador -2 não foi usado")

    def test_include_pauta_normalizes_newlines(self) -> None:
        # Regressão do #6: comentário com newline não injeta heading/bullet na PAUTA.
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: "Outra ideia" in it["snippet"])
            evil = "ok\n## Hacked\n- bullet injetado"
            apply_report(ws, _report([_as_report_item(item, "include_pauta", evil)]), today=TODAY)
            # comentário E título com newline são normalizados
            evil_title = _as_report_item(item, "include_pauta")
            evil_title["title"] = "titulo\n## TitHeading\n- tit bullet"
            apply_report(ws, _report([evil_title]), today=TODAY)
            for line in (ws / "PAUTA.md").read_text(encoding="utf-8").splitlines():
                self.assertFalse(line.strip().startswith("## Hacked"), "comentário injetou heading")
                self.assertFalse(line.strip().startswith("## TitHeading"), "título injetou heading")
                self.assertNotEqual(line.strip(), "- bullet injetado", "comentário injetou bullet")
                self.assertNotEqual(line.strip(), "- tit bullet", "título injetou bullet")

    def test_registro_written_before_removal(self) -> None:
        # Regressão do #9: prova de ordem — se o write do original falha, o
        # registro já existe e o original fica intacto (registrou ANTES de cortar).
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(Path(tmp))
            item = self._find(ws, lambda it: "unica" in it["snippet"])
            real_write = Path.write_text

            def fake_write(self, *a, **k):
                if self.name == "IDEIAS.md":
                    raise OSError("disco cheio simulado")
                return real_write(self, *a, **k)

            with mock.patch.object(Path, "write_text", fake_write):
                with self.assertRaises(OSError):
                    apply_report(ws, _report([_as_report_item(item, "delete")]), today=TODAY)
            self.assertIn("ACERVO", (ws / "REGISTRO.md").read_text(encoding="utf-8"))
            self.assertIn("unica", (ws / "IDEIAS.md").read_text(encoding="utf-8"))  # original intacto


if __name__ == "__main__":
    unittest.main()
