"""Manual de comandos do `/menu` (#130).

Trava: o parser da tabela "Comandos disponíveis" (escopo de seção, cabeçalho e
separadora), o manual read-only e a CLI.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from prumo_runtime.cli import main
from prumo_runtime.menu import SCHEMA_VERSION, command_manual, parse_command_table

_CORE = """# Prumo Core

## Estrutura
- bla

## Comandos disponíveis

| Comando | Função |
|---|---|
| `/setup` | Configura o sistema |
| `/menu` | Manual de instruções |
| `/fim` | Encerra a sessão |

## Outra seção

| Comando | Função |
|---|---|
| `/naoconta` | fora da seção de comandos |
"""


class MenuParserTests(unittest.TestCase):
    def test_parses_only_command_section(self) -> None:
        cmds = parse_command_table(_CORE)
        commands = [c["command"] for c in cmds]
        self.assertEqual(commands, ["/setup", "/menu", "/fim"])
        self.assertNotIn("/naoconta", commands)  # tabela de outra seção não entra

    def test_skips_header_and_separator(self) -> None:
        cmds = parse_command_table(_CORE)
        for c in cmds:
            self.assertTrue(c["command"].startswith("/"))
            self.assertNotIn(c["command"].lower(), ("comando", "---"))
        self.assertEqual(cmds[0]["description"], "Configura o sistema")

    def test_empty_core_is_safe(self) -> None:
        self.assertEqual(parse_command_table(""), [])

    def test_subtable_within_section_is_not_parsed(self) -> None:
        # Regressão (review Codex): só a 1ª tabela contígua após o heading entra;
        # uma sub-tabela (### Notas) dentro da seção NÃO vira comando.
        core = (
            "## Comandos disponíveis\n\n"
            "| Comando | Função |\n|---|---|\n| `/setup` | Configura |\n\n"
            "### Notas\n\n"
            "| Aviso | Detalhe |\n|---|---|\n| `/fake` | não é comando |\n"
        )
        commands = [c["command"] for c in parse_command_table(core)]
        self.assertEqual(commands, ["/setup"])
        self.assertNotIn("/fake", commands)


class MenuManualTests(unittest.TestCase):
    def test_command_manual_reads_workspace_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "PRUMO-CORE.md").write_text(_CORE, encoding="utf-8")  # layout flat
            result = command_manual(ws)
            self.assertEqual(result["schema_version"], SCHEMA_VERSION)
            self.assertEqual(result["count"], 3)
            self.assertIn("/menu", [c["command"] for c in result["commands"]])

    def test_cli_menu_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "PRUMO-CORE.md").write_text(_CORE, encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(["menu", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["count"], 3)

    def test_cli_menu_text_has_proactive_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "PRUMO-CORE.md").write_text(_CORE, encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                main(["menu", "--workspace", str(ws), "--format", "text"])
            out = buffer.getvalue().lower()
            self.assertIn("/setup", out)
            self.assertIn("dúvida", out)  # fecha proativo


if __name__ == "__main__":
    unittest.main()
