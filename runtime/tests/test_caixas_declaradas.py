"""Caixas de entrada declaradas (#245).

30 itens apodreceram 5 meses numa rota morta e 10 nos Clippings desde junho
porque só o `Inbox4Mobile/` era contado. Estes guards travam: a gramática do
marcador (dona única), o bootstrap fásico que quebra o ciclo (a gramática
carrega ANTES do gate que depende dela), o escopo (inventário e cobrança, sem
processamento automático) e o detector da higiene.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"
LOAD_POLICY = SKILLS / "prumo" / "references" / "modules" / "load-policy.md"
CANAIS = SKILLS / "prumo" / "references" / "modules" / "briefing-canais.md"
MONTAGEM = SKILLS / "prumo" / "references" / "modules" / "briefing-montagem.md"
HIGIENE = SKILLS / "higiene" / "SKILL.md"
BRIEFING_SKILL = SKILLS / "briefing" / "SKILL.md"


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class CaixasDeclaradasTest(unittest.TestCase):
    def test_marcador_na_lista_fechada_com_excecao_delimitada(self) -> None:
        flat = _flat(LOAD_POLICY)
        self.assertIn("`(caixa de entrada)`", flat)
        self.assertIn("contagem da listagem plana + metadata rasa (nome e mtime)", flat)
        self.assertIn("**nunca conteúdo**", flat)
        self.assertIn("antiga caixa de entrada", flat, "falta o exemplo de match exato")

    def test_gramatica_carrega_antes_do_gate(self) -> None:
        """[P5-3]: bootstrap circular quebrado — a linha F2 da gramática vem
        ANTES da linha do briefing-canais no mapa fásico."""
        text = BRIEFING_SKILL.read_text(encoding="utf-8")
        gramatica = text.find("gramática dos marcadores")
        canais = text.find("briefing-canais.md")
        self.assertNotEqual(gramatica, -1, "linha F2 da gramática ausente do manifesto")
        self.assertLess(gramatica, canais, "gramática tem de carregar antes do gate")
        self.assertIn("de caixa declarada OU de abrir email/agenda", text)

    def test_gramatica_declarada_uma_vez_so(self) -> None:
        """Dona única: nenhum outro módulo repete a lista de marcadores."""
        offenders = []
        for md in sorted(SKILLS.rglob("*.md")):
            if md == LOAD_POLICY:
                continue
            flat = re.sub(r"\s+", " ", md.read_text(encoding="utf-8"))
            if "(caixa de entrada)" in flat and "marcadores reservados" in flat:
                offenders.append(str(md.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [], f"gramática duplicada fora da dona: {offenders}")

    def test_canais_conta_itens_presentes_sem_processar(self) -> None:
        flat = _flat(CANAIS)
        self.assertIn("Caixas de entrada declaradas (#245)", flat)
        self.assertIn("contagem dos itens presentes", flat)
        self.assertIn("Nenhum processamento automático", flat)
        self.assertIn(
            "`_processed.json` é contrato exclusivo do `Inbox4Mobile/`",
            flat,
            "falta declarar que caixa genérica não tem ledger",
        )

    def test_montagem_apresenta_contagem(self) -> None:
        flat = _flat(MONTAGEM)
        self.assertIn("Caixas declaradas (#245)", flat)
        self.assertIn("sem despejar itens", flat)

    def test_higiene_sinaliza_caixa_envelhecida(self) -> None:
        flat = _flat(HIGIENE)
        self.assertIn("Caixa declarada envelhecida (#245)", flat)
        self.assertIn("14 dias", flat)
        self.assertIn("sinalizar, nunca reorganizar", flat)


if __name__ == "__main__":
    unittest.main()
