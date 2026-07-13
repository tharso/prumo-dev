"""Copy do encerramento do /fim (#175).

Report do dono: o /fim fechou com "a) /higiene b) /sanitize c) nada" — menu de
jargão. Travas: o SKILL especifica UMA recomendação em linguagem de gente
(prioridade conteúdo > técnica; sinal secundário vira cláusula; comando nunca é
opção; adiar deixa rastro), e o texto do runtime não imprime comando como
proposta.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIM_SKILL = REPO_ROOT / "skills" / "fim" / "SKILL.md"


class FimCopyContract(unittest.TestCase):
    def _text(self) -> str:
        return FIM_SKILL.read_text(encoding="utf-8")

    def _flat(self) -> str:
        # Normaliza quebras de linha do markdown pra casar frases inteiras.
        return " ".join(self._text().lower().split())

    def test_uma_recomendacao_prioridade_conteudo(self) -> None:
        text = self._flat()
        self.assertIn("uma recomendação em linguagem de gente", text)
        self.assertIn("conteúdo > técnica", text)
        # O sinal secundário não vira segunda pergunta.
        self.assertIn("cláusula", text)

    def test_comando_nunca_e_opcao(self) -> None:
        self.assertIn("comando nunca é opção", self._flat())

    def test_tem_exemplo_bom_e_ruim(self) -> None:
        text = self._text()
        self.assertIn("Exemplo bom", text)
        self.assertIn("Exemplo ruim", text)
        # O anti-padrão exato do report fica documentado como proibido.
        self.assertIn("a) /higiene", text)

    def test_adiar_deixa_rastro_pro_briefing(self) -> None:
        text = self._text().lower()
        self.assertIn("rastro", text)
        self.assertIn("pauta", text)

    def test_runtime_nao_imprime_comando_como_proposta(self) -> None:
        from prumo_runtime.commands.fim import _render_text

        result = {
            "workspace_path": "/x",
            "signals": {
                "pauta_stalled": 4, "inbox_pending": 0, "registro_rows": 78,
                "backups_old": 6, "ephemeral_old": 5,
                "installed_version": "5.33.0", "remote_version": "5.33.0",
            },
            "suggest": {"higiene": True, "sanitize": True, "update": False},
        }
        text = _render_text(result)
        self.assertNotIn("`/higiene`", text)
        self.assertNotIn("`/sanitize`", text)
        # Em linguagem de gente, com o comando fora do papel de opção.
        self.assertIn("conteúdo parado", text)
        self.assertIn("infra acumulada", text)


if __name__ == "__main__":
    unittest.main()
