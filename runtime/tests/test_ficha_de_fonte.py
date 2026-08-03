"""
Trava anti-drift do fichário de fontes (#140, épico #138).

A ficha de fonte é um contrato entre três skills: o template canônico
(`references/ficha-de-fonte.md`), o fluxo de inbox que a cria
(`modules/inbox-processing.md`), a faxina que a indexa e o acervo que a
enumera/arquiva. Este teste falha se qualquer ponta do contrato sumir ou
desalinhar — a categoria de bug que a #97 chamou de "manutenção morta"
(artefato mantido que nenhum fluxo lê) e o caso inverso (fluxo apontando
pra referência que não existe).

Também trava a exclusão dos operacionais de `Referencias/` — que desde a
#305 tem dois mecanismos deliberadamente distintos: o acervo (skill +
runtime) mantém a lista de infraestrutura (`OPERATIONAL_REFERENCIAS`),
enquanto faxina e índice excluem pela convenção de ficha
(`referencias_convencao`) — e a convenção garante, por construção, que
nenhum operacional vira ficha.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from prumo_runtime.acervo import OPERATIONAL_REFERENCIAS
from prumo_runtime.referencias_convencao import is_ficha_filename


REPO_ROOT = Path(__file__).resolve().parents[2]
FICHA_REF = REPO_ROOT / "skills" / "prumo" / "references" / "ficha-de-fonte.md"
INBOX_MODULE = (
    REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "inbox-processing.md"
)
GOVERNANCE_MODULE = (
    REPO_ROOT
    / "skills"
    / "prumo"
    / "references"
    / "modules"
    / "runtime-file-governance.md"
)
FAXINA_SKILL = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "faxina.md"
ACERVO_SKILL = REPO_ROOT / "skills" / "acervo" / "SKILL.md"

OPERATIONAL_FILES = {"INDICE.md", "EMAIL-CURADORIA.md", "WORKFLOWS.md"}


class FichaDeFonteTests(unittest.TestCase):
    def test_ficha_reference_exists_with_required_fields(self) -> None:
        """O template canônico da ficha existe e carrega os campos do contrato."""
        self.assertTrue(FICHA_REF.exists(), f"faltando: {FICHA_REF}")
        text = FICHA_REF.read_text(encoding="utf-8")
        for field in (
            "Tipo:",
            "Autor:",
            "Onde mora:",
            "Por que guardei:",
            "Entrada:",
            "Keywords:",
        ):
            self.assertIn(field, text, f"campo '{field}' ausente na ficha-de-fonte.md")
        # Conexões em wikilink (decisão do dono, 2026-07-02) com exemplo concreto.
        self.assertIn("[[", text, "ficha-de-fonte.md sem exemplo de [[wikilink]]")
        # Princípio aprovado: catalogar, não armazenar.
        self.assertIn("catalogar, não armazenar", text.lower().replace("**", ""))

    def test_inbox_processing_references_ficha(self) -> None:
        """O fluxo de inbox aponta pro template — sem isso a ficha é manutenção morta."""
        text = INBOX_MODULE.read_text(encoding="utf-8")
        self.assertIn("ficha-de-fonte.md", text)
        # Os dois caminhos do contrato: mover pra dentro vs. ficha-ponteiro.
        self.assertIn("ficha-ponteiro", text)

    def test_governance_admits_ficha_ponteiro(self) -> None:
        """O contrato de Referencias/ admite ficha que aponta (emenda declarada na #140)."""
        text = GOVERNANCE_MODULE.read_text(encoding="utf-8")
        self.assertIn("ficha", text.lower())
        self.assertIn("ficha-de-fonte.md", text)

    def test_operational_files_excluded_everywhere(self) -> None:
        """Acervo mantém a lista de infraestrutura; faxina/índice excluem por
        convenção (#305) — e nenhum operacional pode casar a convenção."""
        self.assertEqual(set(OPERATIONAL_REFERENCIAS), OPERATIONAL_FILES)
        acervo = ACERVO_SKILL.read_text(encoding="utf-8")
        for name in sorted(OPERATIONAL_FILES):
            self.assertIn(name, acervo, f"acervo não exclui {name}")
            self.assertFalse(
                is_ficha_filename(name),
                f"{name} não pode casar a convenção de ficha",
            )
        faxina = FAXINA_SKILL.read_text(encoding="utf-8")
        self.assertIn(
            "Autor_Assunto_AAAA-MM-DD",
            faxina,
            "faxina.md sem a convenção de ficha (#305)",
        )

    def test_acervo_delete_never_touches_external_content(self) -> None:
        """Semântica da ficha-ponteiro no acervo: excluir arquiva a ficha, nunca o conteúdo externo."""
        text = ACERVO_SKILL.read_text(encoding="utf-8")
        self.assertIn("conteúdo externo", text)


if __name__ == "__main__":
    unittest.main()
