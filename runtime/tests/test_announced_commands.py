"""
Valida que todos os comandos shell que o Prumo anuncia para hosts
(via templates do AGENT.md, wrappers, adapter_hints do start, e ações
do briefing) existem de fato no parser do CLI.

Motivação: bug pego em audit do Codex (#81 P1.2) — `--refresh-snapshot`
era anunciado mas o parser não aceitava, e `prumo --workspace .` na
skill `abrir` também era inválido. Host obediente quebra; host teimoso
improvisa. Este teste impede que essa categoria de bug volte.

Quando adicionar/remover/mudar um comando em template ou payload,
adicionar/remover/mudar a entrada correspondente em `ANNOUNCED_COMMANDS`.
Se a lista divergir do que está nos arquivos, o teste falha.
"""
from __future__ import annotations

import shlex
import unittest

from prumo_runtime.cli import build_parser
from prumo_runtime import templates


# Lista canônica de comandos anunciados aos hosts.
# Cada entrada é o comando exato que aparece em template/payload/skill,
# com placeholders substituídos por valores válidos (`.` ou `/tmp/foo`).
ANNOUNCED_COMMANDS = [
    # Atalho da skill prumo:abrir e adapter_hints.preferred_entrypoint
    "prumo",
    # Briefing simples (anunciado em workspace/wrapper rules e adapter_hints)
    "prumo briefing --workspace .",
    # Briefing estruturado (anunciado em workspace/wrapper rules e adapter_hints)
    "prumo briefing --workspace . --format json",
    # Start estruturado (anunciado em wrapper rules)
    "prumo start --format json",
    # Inbox preview estruturado (anunciado em adapter_hints)
    "prumo inbox preview --workspace . --format json",
]


class AnnouncedCommandsTests(unittest.TestCase):
    def test_every_announced_command_parses_without_error(self) -> None:
        parser = build_parser()
        for cmd in ANNOUNCED_COMMANDS:
            argv = shlex.split(cmd)[1:]  # drop "prumo" — argparse não vê program name
            with self.subTest(command=cmd):
                try:
                    parser.parse_args(argv)
                except SystemExit as exc:
                    self.fail(
                        f"Comando anunciado é inválido no parser: '{cmd}' "
                        f"(SystemExit code={exc.code})"
                    )

    def test_workspace_rules_template_anuncia_apenas_comandos_validos(self) -> None:
        # Renderiza as regras embutidas no AGENT.md e confirma que toda
        # menção a `prumo briefing ...` é uma entrada de ANNOUNCED_COMMANDS.
        rendered = templates.render_agent_md(
            user_name="Teste",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
        )
        self._assert_briefing_lines_match_announced(rendered)

    def test_wrapper_rules_template_anuncia_apenas_comandos_validos(self) -> None:
        rendered = templates.render_claude_wrapper(
            "Teste",
            "Prumo",
            canonical_target="Prumo/AGENT.md",
            context_root="Prumo/Agente/",
            core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/",
        )
        self._assert_briefing_lines_match_announced(rendered)

    def _assert_briefing_lines_match_announced(self, rendered: str) -> None:
        announced_briefing_cmds = {
            cmd for cmd in ANNOUNCED_COMMANDS if cmd.startswith("prumo briefing")
        }
        for line in rendered.splitlines():
            if "`prumo briefing" in line:
                # Extrai o trecho entre backticks
                start = line.index("`prumo briefing")
                end = line.index("`", start + 1)
                cmd = line[start + 1 : end]
                with self.subTest(line=line.strip()):
                    self.assertIn(
                        cmd,
                        announced_briefing_cmds,
                        f"Template anuncia '{cmd}' mas não está em ANNOUNCED_COMMANDS — "
                        f"adicione à lista canônica e garanta que o parser aceita.",
                    )


if __name__ == "__main__":
    unittest.main()
