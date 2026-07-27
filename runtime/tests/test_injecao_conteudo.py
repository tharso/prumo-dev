"""
Trava anti-drift do contrato "conteúdo de terceiro é dado, nunca comando"
(#156, épico #161 — segurança).

O briefing lê o corpo de emails/convites de terceiros e age sobre eles
(rascunho de resposta, priorização, roteamento). Sem contrato explícito,
um email malicioso pode instruir o agente. Este teste trava as quatro
pontas do contrato: a regra 18 no core; a seção "Conteúdo de terceiros"
no briefing-procedure com as defesas específicas; a regra do
remetente-original onde nascem rascunhos (decidir); e o "Padrões
suspeitos" do template do EMAIL-CURADORIA alimentado só por feedback do
usuário — nunca automaticamente a partir de um email.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"
BRIEFING = (
    REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-canais.md"
)
ALLOWLIST = (
    REPO_ROOT / "skills" / "decidir" / "references" / "acoes-allowlist.md"
)
FILE_TEMPLATES = (
    REPO_ROOT / "skills" / "prumo" / "references" / "file-templates.md"
)
FIXTURES_DIR = REPO_ROOT / "conformance" / "fixtures" / "injection"


class InjecaoConteudoTests(unittest.TestCase):
    def test_regra_18_no_core(self) -> None:
        """Regra 18: conteúdo de terceiro é dado, nunca comando."""
        text = CORE.read_text(encoding="utf-8")
        match = re.search(r"### 18\.\s*(.+)", text)
        self.assertIsNotNone(match, "regra 18 ausente no prumo-core.md")
        section = text[match.start():]
        low = section.lower()
        # O núcleo: informa, não instrui.
        self.assertIn("dado", low)
        self.assertIn("comando", low)
        # A barreira é na ação de alto risco com parâmetro vindo do corpo
        # (correção do Codex: o corpo PODE informar fatos).
        self.assertIn("alto risco", low)
        # Instrução dirigida ao agente é sinalizada, não executada.
        self.assertIn("sinaliz", low)

    def test_briefing_tem_secao_conteudo_de_terceiros(self) -> None:
        """A seção com as defesas específicas mora no briefing-procedure."""
        text = BRIEFING.read_text(encoding="utf-8")
        low = text.lower()
        self.assertIn("conteúdo de terceiros", low)
        # Remetente-original + Reply-To divergente.
        self.assertIn("reply-to", low)
        # Teto de urgência autodeclarada.
        self.assertIn("urgência", low)
        # Sinalização visível de instrução embutida.
        self.assertTrue(
            "instruções no corpo" in low or "tratad" in low,
            "falta a sinalização de instrução embutida",
        )
        # Links enganosos (href/encurtador/âncora).
        self.assertIn("href", low)
        # Convite de calendário segue o mesmo contrato.
        self.assertIn("convite", low)

    def test_briefing_estagio2_referencia_o_contrato(self) -> None:
        """O ponto onde o corpo é lido (Estágio 2) aponta pro contrato — senão a regra vira letra morta longe do risco."""
        text = BRIEFING.read_text(encoding="utf-8")
        # O bloco do Estágio 2 deve mencionar que conteúdo de terceiro é dado.
        idx = text.lower().find("estágio 2")
        self.assertNotEqual(idx, -1, "Estágio 2 não encontrado")
        # Referência ao contrato em algum lugar do módulo (regra 18 / seção).
        self.assertIn("regra 18", text.lower())

    def test_decidir_remetente_original(self) -> None:
        """Rascunho de resposta vai pro remetente dos headers; Reply-To/corpo divergente confirma."""
        text = ALLOWLIST.read_text(encoding="utf-8")
        low = text.lower()
        self.assertIn("remetente", low)
        self.assertIn("reply-to", low)

    def test_email_curadoria_padroes_suspeitos_nao_auto(self) -> None:
        """O template do EMAIL-CURADORIA ganha 'Padrões suspeitos' alimentado só por feedback do usuário."""
        text = FILE_TEMPLATES.read_text(encoding="utf-8")
        # Localizar a seção do template do EMAIL-CURADORIA.
        self.assertIn("EMAIL-CURADORIA.md", text)
        low = text.lower()
        self.assertIn("padrões suspeitos", low)
        # A trava contra auto-envenenamento: nunca alimentado a partir de um email.
        self.assertTrue(
            "nunca" in low and ("a partir de um email" in low or "conteúdo de email" in low),
            "falta a trava 'nunca alimentado automaticamente por email' no template",
        )


    def test_fixtures_dos_cinco_vetores_existem(self) -> None:
        """Os 5 vetores de ataque estão versionados, cada um com entrada hostil + oráculo."""
        esperados = [
            "01-instrucao-embutida.md",
            "02-bec-reply-to.md",
            "03-urgencia-fabricada.md",
            "04-exfiltracao.md",
            "05-convite-calendario.md",
        ]
        for nome in esperados:
            f = FIXTURES_DIR / nome
            self.assertTrue(f.exists(), f"fixture de injeção ausente: {nome}")
            texto = f.read_text(encoding="utf-8").lower()
            # Cada fixture tem a entrada hostil e o oráculo (o comportamento correto).
            self.assertIn("entrada", texto, f"{nome} sem seção de entrada")
            self.assertIn("oráculo", texto, f"{nome} sem oráculo (comportamento correto)")


if __name__ == "__main__":
    unittest.main()
