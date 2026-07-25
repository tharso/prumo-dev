"""Templates de adapter commitados == saída do generator (#179, épico #177).

Os `*-md-template.md` do caminho manual são GERADOS do builder do runtime.
Editar um deles à mão, ou mudar o builder sem regenerar, quebra aqui —
mesmo molde do `test_version_sync` (N projeções de um dado devem casar).
Correção: `python scripts/generate_adapter_templates.py`.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "generate_adapter_templates", REPO_ROOT / "scripts" / "generate_adapter_templates.py"
)
gen = importlib.util.module_from_spec(_SPEC)
sys.modules["generate_adapter_templates"] = gen
_SPEC.loader.exec_module(gen)


class AdapterTemplatesSyncTest(unittest.TestCase):
    def test_adapter_reference_templates_match_builder(self) -> None:
        for name, compose in gen.TEMPLATES.items():
            with self.subTest(template=name):
                current = (gen.REFERENCES / name).read_text(encoding="utf-8")
                self.assertEqual(
                    current,
                    compose(),
                    f"{name} divergiu do builder — rode scripts/generate_adapter_templates.py",
                )

    def test_generated_templates_keep_placeholders(self) -> None:
        for name in gen.TEMPLATES:
            text = (gen.REFERENCES / name).read_text(encoding="utf-8")
            self.assertIn("{{USER_NAME}}", text)
            self.assertIn("{{AGENT_NAME}}", text)
            self.assertIn("INÍCIO DO TEMPLATE:", text)

    def test_agent_md_template_fallback_is_derived(self) -> None:
        text = (gen.REFERENCES / "agent-md-template.md").read_text(encoding="utf-8")
        # Derivada da fonte única: comandos vivos presentes, aposentados na
        # tabela de intenções (nunca como Comando).
        for cmd in ("| fim |", "| acervo |", "| menu |"):
            self.assertIn(cmd, text)
        self.assertNotIn("| faxina | `.prumo/skills/prumo/references/modules", text.split("| Intenção | Módulo |")[0])
        self.assertIn("| Intenção | Módulo |", text)


if __name__ == "__main__":
    unittest.main()
