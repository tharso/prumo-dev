"""
Trava anti-drift das ideias que amadurecem (#147, épico #138).

Três comportamentos de destilação no processamento do inbox
(título-afirmação, dividir item duplo, adensar sob demanda) + a convenção
do sub-bullet datado INDENTADO no template de `IDEIAS.md`. A indentação é
contrato, não estilo: o acervo captura "bullet + linhas indentadas" como
um fragmento só — sub-bullet datado sem indentação viraria item novo aos
olhos do acervo (achado do Codex na revisão de design, rodada 1).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INBOX_MODULE = (
    REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "inbox-processing.md"
)
FILE_TEMPLATES = (
    REPO_ROOT / "skills" / "prumo" / "references" / "file-templates.md"
)


class IdeiasAmadurecemTests(unittest.TestCase):
    def test_inbox_processing_tem_os_tres_comportamentos(self) -> None:
        """Destilação: título-afirmação (oferta), dividir item duplo, adensar sob demanda."""
        text = INBOX_MODULE.read_text(encoding="utf-8")
        self.assertIn("afirma", text.lower(), "título-afirmação ausente")
        self.assertIn("duas ideias", text.lower(), "divisão de item duplo ausente")
        self.assertIn("adensar", text.lower(), "adensamento sob demanda ausente")

    def test_adensamento_tem_os_freios(self) -> None:
        """Na dúvida separado; sem varredura automática; poda é da higiene."""
        text = INBOX_MODULE.read_text(encoding="utf-8")
        self.assertIn("na dúvida", text.lower())
        self.assertIn("varredura", text.lower())
        self.assertIn("higiene", text.lower())

    def test_adensamento_documenta_efeito_no_acervo(self) -> None:
        """Adensar muda o content_hash — relatório antigo do acervo bloqueia delete (correto)."""
        text = INBOX_MODULE.read_text(encoding="utf-8")
        self.assertIn("content_hash", text)

    def test_exemplo_de_adensamento_e_indentado(self) -> None:
        """O exemplo canônico no módulo mostra sub-bullet datado INDENTADO sob o pai."""
        text = INBOX_MODULE.read_text(encoding="utf-8")
        self.assertTrue(
            re.search(r"^ +- \d{2}/\d{2}:", text, re.M),
            "exemplo de sub-bullet datado indentado ausente no inbox-processing",
        )

    def test_template_ideias_documenta_convencao_indentada(self) -> None:
        """O template gerado de IDEIAS.md ensina a convenção com exemplo indentado."""
        text = FILE_TEMPLATES.read_text(encoding="utf-8")
        ideias_section = text.split("## Prumo/IDEIAS.md", 1)
        self.assertEqual(len(ideias_section), 2, "seção do IDEIAS.md não encontrada")
        section = ideias_section[1].split("--- FIM ---", 1)[0]
        self.assertIn("sub-bullet datado", section.lower())
        # Exemplo indentado dentro do blockquote do template (linhas "> ..."),
        # onde o acervo não o confunde com item real.
        self.assertTrue(
            re.search(r"^> +- DD/MM:", section, re.M),
            "exemplo indentado (dentro de blockquote) ausente no template do IDEIAS",
        )


if __name__ == "__main__":
    unittest.main()
