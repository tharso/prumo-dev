"""Alocação de ID no INDICE.md (#244).

Em 27/07 um agente leu 32 linhas do índice, viu ID 24 e assumiu 25 — o índice
já ia a 34: dez fichas nasceram colidindo. Estes guards travam o mecanismo que
impede a repetição: rodapé como SUGESTÃO (nunca oráculo), sonda do candidato
em todo caminho, lock atômico e liberação sem deleção.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "runtime"))

from prumo_runtime import templates  # noqa: E402

SKILLS = REPO_ROOT / "skills"
FICHA = SKILLS / "prumo" / "references" / "ficha-de-fonte.md"
MULTIAGENT = SKILLS / "prumo" / "references" / "modules" / "multiagent.md"
FAXINA = SKILLS / "prumo" / "references" / "modules" / "faxina.md"
FILE_TEMPLATES = SKILLS / "prumo" / "references" / "file-templates.md"

_FOOTER = re.compile(r"<!-- proximo-id: (\d+) -->")


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class ProximoIdTest(unittest.TestCase):
    def test_renderer_nasce_com_rodape_um(self) -> None:
        rendered = templates.render_referencias_md("2026-07-27")
        m = _FOOTER.search(rendered)
        self.assertIsNotNone(m, "renderer do INDICE sem rodapé proximo-id")
        self.assertEqual(m.group(1), "1")
        self.assertTrue(
            rendered.rstrip().endswith("-->"),
            "o rodapé tem de ser a ÚLTIMA linha (o agente lê só ela)",
        )

    def test_paridade_template_manual_e_renderer(self) -> None:
        """Caminho manual e runtime geram o MESMO rodapé."""
        text = FILE_TEMPLATES.read_text(encoding="utf-8")
        bloco = re.search(
            r"## Prumo/Referencias/INDICE\.md.*?--- INÍCIO ---\n(.*?)\n--- FIM ---",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(bloco, "seção do INDICE sumiu do file-templates.md")
        manual = bloco.group(1)
        self.assertIn("<!-- proximo-id: 1 -->", manual)
        self.assertTrue(manual.rstrip().endswith("-->"))

    def test_procedimento_sonda_em_todo_caminho(self) -> None:
        flat = _flat(FICHA)
        self.assertIn("## Alocação de ID no `INDICE.md` (#244)", flat)
        self.assertIn("N é **sugestão**", flat)
        self.assertIn("Vale em TODO caminho", flat)
        self.assertIn("rodapé stale não é oráculo", flat)

    def test_recuperacao_usa_semente_nao_maximo_global(self) -> None:
        flat = _flat(FICHA)
        self.assertIn("como *semente*", flat)
        self.assertIn("nunca como máximo global", flat)
        self.assertIn("Repor o rodapé na mesma edição", flat)

    def test_lock_atomico_com_escopo_declarado(self) -> None:
        flat = _flat(MULTIAGENT)
        self.assertIn("Escopo com aquisição ATÔMICA (#244)", flat)
        self.assertIn("`Prumo/Referencias/INDICE.md`", flat)
        self.assertIn("mkdir", flat)
        self.assertIn("O_CREAT|O_EXCL", flat)
        self.assertIn("**não escrever**", flat)

    def test_liberacao_move_e_nao_deleta(self) -> None:
        flat = _flat(MULTIAGENT)
        self.assertIn("Liberação: mover, nunca deletar", flat)
        self.assertIn("sufixo determinístico", flat)
        self.assertIn("Sem retomada automática por idade", flat)

    def test_faxina_aponta_para_a_alocacao(self) -> None:
        flat = _flat(FAXINA)
        self.assertIn("alocação de ID do `ficha-de-fonte.md` (#244)", flat)


if __name__ == "__main__":
    unittest.main()
