"""Defaults e pendências visíveis no Decidir (#246).

Feedback do dono após despachar 28 cards: "por que raios o motivo é
obrigatório pra descartar algo? E, se é obrigatório, isso deveria ser
informado na interface". Estes testes são COMPORTAMENTAIS (o review do Codex
recusou assert de substring pra mudança de estado JS): executam as funções
reais do template via `node` e decidem pelo JSON gerado.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = REPO_ROOT / "skills" / "decidir" / "assets" / "template.html"
ALLOWLIST = REPO_ROOT / "skills" / "decidir" / "references" / "acoes-allowlist.md"
SKILL = REPO_ROOT / "skills" / "decidir" / "SKILL.md"

_FUNCS = ("actionsOf", "actionByKey", "safeUrl", "buildReportData")

_HARNESS = """
%(funcs)s
const POINTS = %(points)s;
const state = %(state)s;
console.log(JSON.stringify(buildReportData()));
"""


def _extract(name: str, html: str) -> str:
    """Função de uma linha (`function f(p) { ... }`) ou bloco (fecha em `^}`)."""
    one_line = re.search(rf"^function {name}\(.*\}}\s*$", html, re.MULTILINE)
    if one_line is not None:
        return one_line.group(0)
    block = re.search(rf"^function {name}\([\s\S]*?^}}", html, re.MULTILINE)
    if block is None:
        raise AssertionError(f"função {name}() não encontrada no template")
    return block.group(0)


def _run(points: list[dict], state: dict) -> list[dict]:
    html = TEMPLATE.read_text(encoding="utf-8")
    funcs = "\n".join(_extract(n, html) for n in _FUNCS)
    script = _HARNESS % {
        "funcs": funcs,
        "points": json.dumps(points, ensure_ascii=False),
        "state": json.dumps(state, ensure_ascii=False),
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "h.js"
        path.write_text(script, encoding="utf-8")
        out = subprocess.run(
            ["node", str(path)], capture_output=True, text=True, timeout=30, check=False
        )
    if out.returncode != 0:
        raise AssertionError(f"harness falhou: {out.stderr[:400]}")
    return json.loads(out.stdout)


_DISCARD = {
    "key": "discard",
    "label": "Descartar",
    "effect": "discard",
    "requires": "motivo",
    "default": "não interessa mais",
}
_DELEGATE = {
    "key": "delegate",
    "label": "Delegar",
    "effect": "draft_delegation",
    "requires": "destinatário",
}


@unittest.skipUnless(shutil.which("node"), "node ausente (harness comportamental)")
class DecidirDefaultsTest(unittest.TestCase):
    def test_discard_sem_comentario_resolve_o_default(self) -> None:
        items = _run(
            [{"id": 1, "type": "despacho", "actions": [_DISCARD]}],
            {"1": {"status": "discard"}},
        )
        item = items[0]
        self.assertFalse(item["requires_missing"], "default não deveria deixar pendência")
        self.assertTrue(item["default_used"])
        self.assertEqual(item["resolved_detail"], "não interessa mais")
        self.assertIsNone(item["comment"], "comment é do texto autoral, não do default")

    def test_comentario_sobrescreve_o_default(self) -> None:
        items = _run(
            [{"id": 1, "type": "despacho", "actions": [_DISCARD]}],
            {"1": {"status": "discard", "comment": "já resolvi por fora"}},
        )
        item = items[0]
        self.assertFalse(item["default_used"])
        self.assertIsNone(item["resolved_detail"])
        self.assertEqual(item["comment"], "já resolvi por fora")

    def test_acao_sem_default_continua_pendente(self) -> None:
        items = _run(
            [{"id": 1, "type": "despacho", "actions": [_DELEGATE]}],
            {"1": {"status": "delegate"}},
        )
        self.assertTrue(items[0]["requires_missing"], "delegate sem destinatário é pendência")

    def test_comentario_zera_a_pendencia(self) -> None:
        items = _run(
            [{"id": 1, "type": "despacho", "actions": [_DELEGATE]}],
            {"1": {"status": "delegate", "comment": "pra Ana"}},
        )
        self.assertFalse(items[0]["requires_missing"])

    def test_contador_de_pendencias_no_template(self) -> None:
        """A contagem existe e é exibida ANTES do botão de copiar."""
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("function pendingCount()", html)
        self.assertIn("pendingNote", html)
        self.assertLess(
            html.index('id="pendingNote"'),
            html.index('id="copyBtn"'),
            "a pendência tem de aparecer antes do botão Copiar respostas",
        )


class DecidirContratoTest(unittest.TestCase):
    def test_allowlist_declara_default_e_rigor_por_risco(self) -> None:
        flat = re.sub(r"\s+", " ", ALLOWLIST.read_text(encoding="utf-8"))
        self.assertIn("`default`", flat)
        self.assertIn("não interessa mais", flat)
        # Rigor por risco: pauta (reversível) ≠ inbox (arquivo, quarentena).
        self.assertIn("descarte de linha de pauta", flat)
        self.assertIn("descarte de item de inbox", flat)

    def test_skill_documenta_geracao_e_consumo(self) -> None:
        flat = re.sub(r"\s+", " ", SKILL.read_text(encoding="utf-8"))
        self.assertIn("`resolved_detail`", flat)
        self.assertIn("`default_used`", flat)
        self.assertIn("motivo e tag concretos", flat, "falta o contrato de GERAÇÃO do default")


if __name__ == "__main__":
    unittest.main()
