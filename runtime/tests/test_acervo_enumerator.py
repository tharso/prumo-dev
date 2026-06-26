"""Contrato do enumerador read-only do `acervo` (#125).

Trava: fontes duráveis corretas, escopo negativo de Referencias/, proveniência
completa por item (path/âncora/linhas/hash), hash estável, e nada de escrita
(read-only).
"""
from __future__ import annotations

import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

from prumo_runtime.acervo import (
    ITEM_FIELDS,
    OPERATIONAL_REFERENCIAS,
    SCHEMA_VERSION,
    enumerate_limbo,
)

TODAY = date(2026, 6, 26)


def _snapshot(root: Path) -> dict[str, float]:
    return {str(p): p.stat().st_mtime for p in root.rglob("*") if p.is_file()}


class AcervoEnumeratorTests(unittest.TestCase):
    def _build_workspace(self, root: Path) -> Path:
        (root / "_state").mkdir(parents=True, exist_ok=True)
        (root / "Referencias").mkdir(parents=True, exist_ok=True)
        (root / "IDEIAS.md").write_text(
            "# Ideias\n\n"
            "- [Produto] Ideia de feature X. (desde 01/01)\n"
            "- Pensar num nome melhor pro acervo\n",
            encoding="utf-8",
        )
        (root / "PAUTA.md").write_text(
            "# Pauta\n\n"
            "## Quente\n"
            "- [Trabalho] Item quente que NAO entra no acervo\n\n"
            "## Hibernando\n"
            "- [Pessoal] Projeto parado ha meses\n",
            encoding="utf-8",
        )
        ref = root / "Referencias"
        (ref / "INDICE.md").write_text("# Indice\n", encoding="utf-8")
        (ref / "EMAIL-CURADORIA.md").write_text("# Regras\n", encoding="utf-8")
        (ref / "WORKFLOWS.md").write_text("# Workflows\n", encoding="utf-8")
        (ref / "artigo-ia.md").write_text("# Artigo sobre IA\n\nCorpo do artigo.\n", encoding="utf-8")
        (ref / "paper.pdf").write_bytes(b"%PDF-1.4 fake bytes")
        return root

    def test_schema_and_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._build_workspace(Path(tmp))
            result = enumerate_limbo(ws, today=TODAY)
            self.assertEqual(result["schema_version"], SCHEMA_VERSION)
            self.assertEqual(result["workspace_path"], str(ws.resolve()))
            # 2 ideias + 1 hibernando + 2 referencias (operacionais excluidos)
            self.assertEqual(result["count"], 5)
            self.assertEqual(len(result["items"]), 5)

    def test_negative_scope_referencias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._build_workspace(Path(tmp))
            result = enumerate_limbo(ws, today=TODAY)
            paths = [it["source_path"] for it in result["items"]]
            for operational in OPERATIONAL_REFERENCIAS:
                self.assertFalse(
                    any(p.endswith(operational) for p in paths),
                    f"{operational} (operacional) nao pode entrar no acervo",
                )
            ref_titles = [it["title"] for it in result["items"] if it["source_kind"] == "referencia"]
            self.assertEqual(len(ref_titles), 2)

    def test_only_hibernando_from_pauta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._build_workspace(Path(tmp))
            items = enumerate_limbo(ws, today=TODAY)["items"]
            hib = [it for it in items if it["source_kind"] == "pauta_hibernando"]
            self.assertEqual(len(hib), 1)
            self.assertEqual(hib[0]["anchor"], "Hibernando")
            self.assertNotIn("quente", " ".join(it["snippet"].lower() for it in items))

    def test_provenance_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._build_workspace(Path(tmp))
            items = enumerate_limbo(ws, today=TODAY)["items"]
            required = {
                "item_id", "source_kind", "source_path", "anchor",
                "line_start", "line_end", "content_hash", "title",
                "snippet", "age_days", "tags",
            }
            self.assertEqual(required, set(ITEM_FIELDS))
            for it in items:
                self.assertEqual(set(it), set(ITEM_FIELDS), f"item fora do contrato: {it}")
                self.assertRegex(it["content_hash"], r"^[0-9a-f]{16}$")
            fragments = [it for it in items if it["source_kind"] in ("ideia", "pauta_hibernando")]
            for it in fragments:
                self.assertIsInstance(it["line_start"], int)
                self.assertIsInstance(it["line_end"], int)
                self.assertGreaterEqual(it["line_end"], it["line_start"])
            refs = [it for it in items if it["source_kind"] == "referencia"]
            for it in refs:
                self.assertIsNone(it["line_start"])
                self.assertIsNone(it["line_end"])
                self.assertIsInstance(it["age_days"], int)
                self.assertGreaterEqual(it["age_days"], 0)

    def test_tags_and_age_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._build_workspace(Path(tmp))
            items = enumerate_limbo(ws, today=TODAY)["items"]
            with_desde = next(it for it in items if "feature X" in it["snippet"])
            self.assertEqual(with_desde["tags"], ["Produto"])
            self.assertEqual(with_desde["age_days"], (TODAY - date(2026, 1, 1)).days)
            without = next(it for it in items if "nome melhor" in it["snippet"])
            self.assertIsNone(without["age_days"])

    def test_hash_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._build_workspace(Path(tmp))
            first = enumerate_limbo(ws, today=TODAY)["items"]
            second = enumerate_limbo(ws, today=TODAY)["items"]
            self.assertEqual(
                [it["content_hash"] for it in first],
                [it["content_hash"] for it in second],
            )

    def test_enumeration_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._build_workspace(Path(tmp))
            before = _snapshot(ws)
            enumerate_limbo(ws, today=TODAY)
            after = _snapshot(ws)
            self.assertEqual(before, after, "enumerador nao pode criar/alterar arquivos")

    def test_empty_workspace_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "_state").mkdir(parents=True, exist_ok=True)
            result = enumerate_limbo(ws, today=TODAY)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["items"], [])


class AcervoCliTests(unittest.TestCase):
    def test_cli_acervo_json_emits_schema_and_items(self) -> None:
        import io
        import json
        from contextlib import redirect_stdout

        from prumo_runtime.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "_state").mkdir(parents=True, exist_ok=True)
            (ws / "IDEIAS.md").write_text("# Ideias\n\n- Uma ideia parada\n", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["acervo", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
            self.assertEqual(payload["count"], 1)


if __name__ == "__main__":
    unittest.main()
