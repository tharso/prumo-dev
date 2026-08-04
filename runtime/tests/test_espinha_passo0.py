"""A escada de F1 conhece o runtime embarcado (#322).

O relatório da rodada 18h de 03/08: `command -v prumo` ausente e a rota
declarou o runtime inalcançável — enquanto o bundle carregava o runtime
completo e o REGISTRO do meio-dia provava que ele roda na VM. O Passo 0
existia (`runtime-paths.md`, #302), mas a ESCADA DE TRANSPORTES do
`briefing-estado.md` — onde a decisão de fato acontece — pulava do
"runtime no PATH" direto pro arquivo-semente, sem nunca apontá-lo.

Pergunta de mutação que estes guards respondem: que edição errada
preservaria as palavras? Reordenar a escada (fallback antes do Passo 0)
ou recuar o degrau pro texto de fora dos transportes — por isso os
asserts de POSIÇÃO, não só de presença.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULES = REPO_ROOT / "skills" / "prumo" / "references" / "modules"
ESTADO = (MODULES / "briefing-estado.md").read_text(encoding="utf-8")
PROCEDURE = (MODULES / "briefing-procedure.md").read_text(encoding="utf-8")
RUNTIME_PATHS = (MODULES / "runtime-paths.md").read_text(encoding="utf-8")


class EscadaConhecePasso0(unittest.TestCase):
    def test_transporte_1_cobre_path_E_embarcado(self) -> None:
        # O degrau 1 não é mais "runtime no PATH": é runtime ALCANÇÁVEL,
        # pelos dois caminhos do Passo 0.
        self.assertIn("PATH ou embarcado (Passo 0, `runtime-paths.md`)", ESTADO)

    def test_fallback_exige_passo_0_esgotado(self) -> None:
        # Leitura direta só depois de esgotar os DOIS caminhos — declarar
        # "inalcançável" com uma sonda só foi o que custou nove dias.
        self.assertIn("Passo 0 esgotado (PATH e embarcado)", ESTADO)

    def test_ordem_da_escada_sobrevive(self) -> None:
        # Posição, não só presença: o Passo 0 aparece no degrau 1, ANTES do
        # arquivo-semente, e o esgotamento no degrau 3, depois dele.
        degrau1 = ESTADO.index("PATH ou embarcado (Passo 0")
        semente_arquivo = ESTADO.index("local-panorama.json")
        esgotado = ESTADO.index("Passo 0 esgotado")
        self.assertLess(degrau1, semente_arquivo, "Passo 0 saiu do degrau 1")
        self.assertLess(semente_arquivo, esgotado, "esgotamento saiu do degrau 3")

    def test_espinha_aponta_o_passo_0_no_gate(self) -> None:
        self.assertIn("(runtime alcançável — Passo 0)", PROCEDURE)

    def test_passo_0_existe_na_fonte_canonica(self) -> None:
        # A escada aponta; a fonte precisa continuar existindo com os dois
        # caminhos nomeados (#302).
        self.assertIn("## Passo 0", RUNTIME_PATHS)
        self.assertIn("PYTHONPATH=", RUNTIME_PATHS)


class StagingAgrupado(unittest.TestCase):
    BRIEFING_SKILL = (
        REPO_ROOT / "skills" / "briefing" / "SKILL.md"
    ).read_text(encoding="utf-8")

    def test_regra_de_batching_no_material_pre_staging(self) -> None:
        # 8 chamadas de staging onde 3–4 bastavam (relatório 18h, atrito 4).
        # A regra precisa estar em contexto ANTES do primeiro staging — e o
        # único material garantido nesse momento é o corpo da própria skill,
        # carregado na invocação (Codex, 322-r1: em briefing-estado.md, F1,
        # ela chegava DEPOIS do staging de F0 que deveria governar).
        self.assertIn(
            "staging agrupado — inventário conhecido numa chamada, pós-gate noutra",
            self.BRIEFING_SKILL,
        )
        self.assertIn("nunca arquivo a arquivo", self.BRIEFING_SKILL)

    def test_batching_nao_regrediu_pro_modulo_de_f1(self) -> None:
        # A mutação barata: alguém "organiza" a regra de volta pro estado
        # (F1) — onde ela não governa nada. Uma casa só (duas listas, uma
        # é drift).
        self.assertNotIn("staging agrupado", ESTADO)


if __name__ == "__main__":
    unittest.main()
