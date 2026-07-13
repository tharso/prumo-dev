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

    def _result(self, **suggest) -> dict:
        return {
            "workspace_path": "/x",
            "signals": {
                "pauta_stalled": 4, "inbox_pending": 0, "registro_rows": 78,
                "backups_old": 6, "ephemeral_old": 5,
                "installed_version": "5.33.0", "remote_version": "5.34.0",
            },
            "suggest": {"higiene": False, "sanitize": False, "update": False, **suggest},
        }

    def test_runtime_uma_recomendacao_sem_jargao_nem_comando(self) -> None:
        from prumo_runtime.commands.fim import _render_text

        text = _render_text(self._result(higiene=True, sanitize=True))
        # Nenhum nome de comando ou de skill como proposta (review Codex: o
        # guard anterior só barrava a forma com crases e deixava "(higiene)"
        # passar). O nome não aparece de jeito NENHUM na recomendação.
        self.assertNotIn("higiene", text.lower())
        self.assertNotIn("sanitize", text.lower())
        self.assertNotIn("sanitização", text.lower())
        self.assertNotIn("prumo update", text)
        # UMA recomendação: conteúdo lidera e a técnica vira cláusula na MESMA linha.
        rec_lines = [ln for ln in text.split("\n") if "Recomendação:" in ln]
        self.assertEqual(len(rec_lines), 1)
        self.assertIn("conteúdo parado", rec_lines[0])
        self.assertIn("poeira técnica", rec_lines[0])

    def test_runtime_so_tecnica_vira_recomendacao_unica(self) -> None:
        from prumo_runtime.commands.fim import _render_text

        text = _render_text(self._result(sanitize=True))
        rec_lines = [ln for ln in text.split("\n") if "Recomendação:" in ln]
        self.assertEqual(len(rec_lines), 1)
        self.assertIn("poeira técnica", rec_lines[0])

    def test_runtime_update_pendente_sem_comando(self) -> None:
        from prumo_runtime.commands.fim import _render_text

        text = _render_text(self._result(update=True))
        self.assertIn("5.33.0", text)
        self.assertIn("5.34.0", text)
        self.assertIn("oferecer antes de fechar", text)
        self.assertNotIn("prumo update", text)

    def test_runtime_triplo_mantem_uma_recomendacao_e_update_separado(self) -> None:
        # r2 do Codex: higiene+sanitize+update não pode virar duas decisões
        # numa. O render mantém UMA linha de recomendação (conteúdo + cláusula
        # técnica) e o update como linha própria — a skill o apresenta como a
        # última pergunta, momento distinto.
        from prumo_runtime.commands.fim import _render_text

        text = _render_text(self._result(higiene=True, sanitize=True, update=True))
        rec_lines = [ln for ln in text.split("\n") if "Recomendação:" in ln]
        self.assertEqual(len(rec_lines), 1)
        self.assertIn("poeira técnica", rec_lines[0])
        update_lines = [ln for ln in text.split("\n") if "Update pendente" in ln]
        self.assertEqual(len(update_lines), 1)
        self.assertNotIn("Recomendação", update_lines[0])


if __name__ == "__main__":
    unittest.main()
