"""Precedência de roteamento (#243) — contratos ancorados, não vocabulário.

O incidente de 27/07 (3 artefatos do mesmo artigo em 2 diretórios, por
obediência à fonte errada) não foi improviso: era empate real entre três
fontes. Estes guards travam a ESCALA (ordem completa, dono único, ponteiros
em vez de cópias) e a gramática do marcador de contrato.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"
CANAIS = SKILLS / "prumo" / "references" / "modules" / "briefing-canais.md"
LOAD_POLICY = SKILLS / "prumo" / "references" / "modules" / "load-policy.md"
FILE_TEMPLATES = SKILLS / "prumo" / "references" / "file-templates.md"


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


# Os 4 marcos da escala, na ordem. Cópia = todos presentes NESTA sequência.
_DEGRAUS = (
    "Contrato autoral",
    "EMAIL-CURADORIA.md",
    "PERFIL.md",
    "AGENT.md",
)


def _copia_da_escala(flat: str) -> bool:
    pos = -1
    for marco in _DEGRAUS:
        found = flat.find(marco, pos + 1)
        if found == -1:
            return False
        pos = found
    return True


class PrecedenciaRoteamentoTest(unittest.TestCase):
    def test_escala_completa_na_ordem_certa(self) -> None:
        """Os 4 degraus, na sequência — contrato > EMAIL-CURADORIA > PERFIL > AGENT."""
        flat = _flat(CANAIS.read_text(encoding="utf-8"))
        self.assertIn("Precedência de roteamento (#243)", flat)
        marcos = [
            "Contrato autoral do usuário",
            "`Prumo/Referencias/EMAIL-CURADORIA.md`",
            "`Prumo/Agente/PERFIL.md`",
            "`Prumo/AGENT.md`",
        ]
        pos = [flat.find(m, flat.find("Precedência de roteamento")) for m in marcos]
        for m, p in zip(marcos, pos):
            self.assertNotEqual(p, -1, f"degrau ausente da escala: {m}")
        self.assertEqual(pos, sorted(pos), f"degraus fora de ordem: {list(zip(marcos, pos))}")

    def test_desempate_por_especificidade_declarado(self) -> None:
        flat = _flat(CANAIS.read_text(encoding="utf-8"))
        self.assertIn("empate de cobertura, ganha a mais específica", flat)

    def test_divergencia_e_mencionada_sem_travar(self) -> None:
        flat = _flat(CANAIS.read_text(encoding="utf-8"))
        self.assertIn("mencionar a divergência em uma linha", flat)

    def test_escala_declarada_uma_vez_so(self) -> None:
        """Dono único: nenhum outro módulo repete a escala (ponteiro, não cópia).

        Detecta a COEXISTÊNCIA ORDENADA dos 4 marcos, sem depender de pontuação
        nem de distância — uma cópia literal da seção tem os quatro na ordem, e
        a versão anterior deste guard (regex com janela de 120 chars e
        `precedência` DEPOIS dos degraus) deixava passar (Codex, diff r1).
        """
        offenders = []
        for md in sorted(SKILLS.rglob("*.md")):
            if md == CANAIS:
                continue
            if _copia_da_escala(_flat(md.read_text(encoding="utf-8"))):
                offenders.append(str(md.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [], f"escala duplicada fora do dono: {offenders}")

    def test_guard_de_copia_reprova_copia_literal(self) -> None:
        """Fixture negativa: a seção do dono, copiada, TEM de ser detectada —
        senão o guard acima é decoração."""
        secao = _flat(CANAIS.read_text(encoding="utf-8"))
        inicio = secao.find("**Precedência de roteamento (#243)")
        copia = secao[inicio : inicio + 1200]
        self.assertTrue(
            _copia_da_escala(copia),
            "o guard não detecta uma cópia literal da escala — é decoração",
        )
        self.assertFalse(
            _copia_da_escala(
                "A escala completa mora em `briefing-canais.md` → Precedência de roteamento."
            ),
            "ponteiro legítimo não pode ser confundido com cópia",
        )

    def test_marcador_de_contrato_na_gramatica_fechada(self) -> None:
        flat = _flat(LOAD_POLICY.read_text(encoding="utf-8"))
        self.assertIn("marcadores reservados", flat)
        self.assertIn("`(contrato: <path>)`", flat)
        self.assertIn("abre em F2, nunca na abertura", flat)
        self.assertIn("Match **exato** do marcador", flat)

    def test_template_da_curadoria_aponta_para_a_escala(self) -> None:
        flat = _flat(FILE_TEMPLATES.read_text(encoding="utf-8"))
        self.assertIn('a escala completa mora em `briefing-canais.md`', flat)


if __name__ == "__main__":
    unittest.main()
