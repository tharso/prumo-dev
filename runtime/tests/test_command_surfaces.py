"""Paridade das projeções da tabela de comandos (#179, épico #177).

A tabela `## Comandos disponíveis` do core é a fonte única (#172; o `/menu`
já deriva dela). Estes testes garantem que as DEMAIS projeções derivam ou
batem com ela: a cadeia de fallback do AGENT.md (renderizada em render-time
a partir do core), os manifestos de plugin e a subseção de intenções
(faxina/sanitize/doctor — módulos, nunca "Comando").
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from prumo_runtime import templates
from prumo_runtime.command_table import parse_command_table, parse_intent_modules

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_TEXT = (
    REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"
).read_text(encoding="utf-8")

RETIRED_COMMANDS = {"faxina", "sanitize", "doctor", "start"}
SKILLS_PATH = ".prumo/skills/"


def _render_fallback(core_text: str = CORE_TEXT) -> str:
    return templates._render_fallback_chain(SKILLS_PATH, core_text)


def _table_rows(rendered: str, header: str) -> list[tuple[str, str]]:
    """Extrai (col1, col2) da tabela contígua que segue a linha de header."""
    lines = rendered.splitlines()
    rows: list[tuple[str, str]] = []
    started = False
    for line in lines:
        s = line.strip()
        if s == header:
            started = True
            continue
        if not started:
            continue
        if not s.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        rows.append((cells[0], cells[1]))
    return rows


class IntentModulesTest(unittest.TestCase):
    def test_parse_intent_modules_reads_core(self) -> None:
        intents = parse_intent_modules(CORE_TEXT)
        names = " ".join(item["intent"] for item in intents).lower()
        self.assertEqual(len(intents), 3, intents)
        for expected in ("faxina", "sanitiza", "doctor"):
            self.assertIn(expected, names)

    def test_intent_module_paths_exist_in_skills_tree(self) -> None:
        for item in parse_intent_modules(CORE_TEXT):
            rel = item["module"].split("skills/", 1)[-1]
            self.assertTrue(
                (REPO_ROOT / "skills" / rel).exists(),
                f"módulo de intenção aponta pra arquivo inexistente: {item['module']}",
            )


class FallbackChainTest(unittest.TestCase):
    def test_fallback_chain_covers_every_core_command(self) -> None:
        rendered = _render_fallback()
        listed = {row[0] for row in _table_rows(rendered, "| Comando | Skill |")}
        for cmd in parse_command_table(CORE_TEXT):
            name = cmd["command"].lstrip("/")
            self.assertIn(
                name,
                listed,
                f"comando `{name}` está na tabela canônica do core mas sumiu da fallback chain",
            )

    def test_fallback_chain_paths_exist_in_skills_tree(self) -> None:
        rendered = _render_fallback()
        paths = re.findall(rf"`{re.escape(SKILLS_PATH)}([^`]+)`", rendered)
        self.assertTrue(paths)
        for rel in paths:
            self.assertTrue(
                (REPO_ROOT / "skills" / rel).exists(),
                f"fallback chain aponta pra arquivo inexistente: skills/{rel}",
            )

    def test_intent_modules_labeled_as_intencao_never_comando(self) -> None:
        rendered = _render_fallback()
        commands = {row[0] for row in _table_rows(rendered, "| Comando | Skill |")}
        intents = " ".join(
            row[0] for row in _table_rows(rendered, "| Intenção | Módulo |")
        ).lower()
        for retired in ("faxina", "sanitiza", "doctor"):
            self.assertNotIn(
                retired,
                " ".join(commands).lower(),
                f"`{retired}` voltou a aparecer como Comando — a #172 aposentou isso",
            )
        for expected in ("faxina", "sanitiza", "doctor"):
            self.assertIn(expected, intents)

    def test_retired_names_never_appear_as_commands(self) -> None:
        core_commands = {c["command"].lstrip("/") for c in parse_command_table(CORE_TEXT)}
        self.assertFalse(core_commands & RETIRED_COMMANDS)

    def test_render_agent_md_derives_fallback_from_repo_core(self) -> None:
        rendered = templates.render_agent_md(
            user_name="Teste",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
            skills_path=SKILLS_PATH,
        )
        for name in ("fim", "acervo", "menu"):
            self.assertIn(
                f"| {name} |",
                rendered,
                f"`{name}` existe na tabela do core mas não chegou no AGENT.md renderizado",
            )


class PluginManifestParityTest(unittest.TestCase):
    def test_plugin_manifest_covers_all_skills_dirs(self) -> None:
        skills_dirs = {
            p.name for p in (REPO_ROOT / "skills").iterdir() if p.is_dir()
        }
        for manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            data = json.loads((REPO_ROOT / manifest).read_text(encoding="utf-8"))
            declared = {entry.rstrip("/").split("/")[-1] for entry in data["skills"]}
            self.assertEqual(
                declared,
                skills_dirs,
                f"{manifest} divergiu da árvore skills/ — mudança em manifesto exige aprovação do dono",
            )

    def test_codex_plugin_points_to_whole_skills_dir(self) -> None:
        data = json.loads(
            (REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(data["skills"], "./skills/")


if __name__ == "__main__":
    unittest.main()
