"""
Trava anti-drift do diário do dia (#141, épico #138).

O diário é a emenda mais delicada do épico: o `/fim` passa a gerar UM
artefato narrativo contratado (projeção confirmada de fatos gravados),
enquanto a proibição da #68/#125-126 (narrativa de memória, artefatos de
coordenação entre agentes) continua de pé. Este teste trava as duas
pontas: o contrato novo existe E as proibições antigas não afrouxaram.

Também trava o layout: `Prumo/Diario/` nasce no primeiro `/fim` — o
setup NÃO pré-cria (tensão setup×primeiro-uso apontada pelo Codex na
revisão de design, rodada 1).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIM_SKILL = REPO_ROOT / "skills" / "fim" / "SKILL.md"
FAXINA_SKILL = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "faxina.md"
FILE_TEMPLATES = (
    REPO_ROOT / "skills" / "prumo" / "references" / "file-templates.md"
)
AGENT_TEMPLATE = (
    REPO_ROOT / "skills" / "prumo" / "references" / "agent-md-template.md"
)
SETUP_SKILL = REPO_ROOT / "skills" / "prumo" / "SKILL.md"


class DiarioTests(unittest.TestCase):
    def test_fim_carrega_o_contrato_do_diario(self) -> None:
        """O /fim gera o diário com o contrato: projeção de fatos + confirmação integral + append."""
        text = FIM_SKILL.read_text(encoding="utf-8")
        self.assertIn("Diario/", text)
        # Confirmação do texto integral antes de gravar.
        self.assertIn("texto completo", text.lower())
        # Múltiplos /fim no mesmo dia anexam seção, nunca sobrescrevem.
        self.assertIn("anexar", text.lower())
        # Sem retro-geração de dias passados.
        self.assertIn("retro", text.lower())

    def test_fim_mantem_proibicoes_da_68(self) -> None:
        """A emenda não afrouxa o resto: coordenação entre agentes segue vedada."""
        text = FIM_SKILL.read_text(encoding="utf-8")
        self.assertIn("HANDOVER", text)
        self.assertIn("PENDING_VALIDATION", text)
        # A distinção central da emenda: narrativa de memória continua proibida.
        self.assertIn("memória", text)

    def test_faxina_rotaciona_diario_por_nome(self) -> None:
        """Rotação por data no nome do arquivo, sem ler conteúdo (faxina nunca julga)."""
        text = FAXINA_SKILL.read_text(encoding="utf-8")
        self.assertIn("Diario", text)
        self.assertIn("Arquivo/Diario", text)
        self.assertIn("90", text)
        self.assertIn("nome", text.lower())

    def test_layout_documenta_diario_sem_pre_criar(self) -> None:
        """file-templates e AGENT.md documentam a pasta com a anotação 'nasce no primeiro uso'."""
        templates = FILE_TEMPLATES.read_text(encoding="utf-8")
        agent = AGENT_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("Diario/", templates)
        self.assertIn("não pré-cria", templates)
        self.assertIn("Diario/", agent)

    def test_runtime_agent_md_inclui_diario_no_mapa(self) -> None:
        """O AGENT.md gerado pelo RUNTIME também lista Diario/ — o template
        markdown e o render do runtime são duas cópias do mesmo mapa (drift
        pego pelo Codex na revisão de código da #141)."""
        from prumo_runtime.templates import render_agent_md

        rendered = render_agent_md(
            user_name="Teste",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="9h",
        )
        self.assertIn("Diario/", rendered)
        # E a pasta continua fora da criação: o mapa documenta, o setup não cria.
        self.assertIn("nasce no primeiro uso", rendered)

    def test_setup_nao_pre_cria_diario(self) -> None:
        """O bloco 'Criar estrutura de diretórios' do setup não inclui Diario/."""
        text = SETUP_SKILL.read_text(encoding="utf-8")
        match = re.search(
            r"Criar estrutura de diretórios:(.*?)(?:\n\d+\.|\n###)", text, re.S
        )
        self.assertIsNotNone(match, "bloco de criação de diretórios não encontrado no setup")
        self.assertNotIn(
            "Diario",
            match.group(1),
            "o setup NÃO deve pré-criar Prumo/Diario/ — a pasta nasce no primeiro /fim",
        )


if __name__ == "__main__":
    unittest.main()
