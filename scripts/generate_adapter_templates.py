#!/usr/bin/env python3
"""Gera os templates de adapter do caminho manual a partir do builder (#179).

Os arquivos `skills/prumo/references/{claude,agents,agent}-md-template.md`
eram a QUARTA família de projeções das regras de porta — escritos à mão,
divergiam do que o runtime renderiza (a "Porta curta" deles tinha 3 linhas;
a do runtime, 17 regras; a fallback chain deles listava comandos aposentados
pela #172). Agora eles são GERADOS do mesmo builder que o runtime usa
(`templates.render_root_wrapper` / `render_agent_md` + `wrapper_rules`),
com placeholders `{{VARIAVEL}}` no lugar dos dados do usuário.

Os artefatos ficam COMMITADOS (skills-first: agente lê o repo sem build);
`runtime/tests/test_adapter_templates_sync.py` quebra o CI se alguém editar
um template à mão ou mudar o builder sem regenerar.

Uso:
    python scripts/generate_adapter_templates.py          # regrava os 3
    python scripts/generate_adapter_templates.py --check  # só verifica (exit 1 se drift)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "runtime"))

from prumo_runtime import templates  # noqa: E402

REFERENCES = REPO_ROOT / "skills" / "prumo" / "references"

# Paths do layout nested canônico, como o runtime os escreve.
_NESTED = dict(
    canonical_target="Prumo/AGENT.md",
    context_root="Prumo/Agente/",
    core_path=".prumo/system/PRUMO-CORE.md",
    state_path=".prumo/state/",
)

_GENERATED_NOTICE = (
    "> **Arquivo gerado** por `scripts/generate_adapter_templates.py` a partir do\n"
    "> builder do runtime (`templates.py` + `wrapper_rules.py`, #179). Não editar à\n"
    "> mão: mude a fonte e regenere — `test_adapter_templates_sync` guarda o drift."
)


def _doc(header_lines: list[str], body: str) -> str:
    header = "\n".join(header_lines)
    return f"{header}\n\n{_GENERATED_NOTICE}\n\n---\n\nINÍCIO DO TEMPLATE:\n\n---\n\n{body.strip()}\n"


def compose_claude_template() -> str:
    body = templates.render_root_wrapper(
        "claude", "{{USER_NAME}}", "{{AGENT_NAME}}", **_NESTED
    )
    return _doc(
        [
            "# Template do CLAUDE.md (ponteiro de compatibilidade)",
            "",
            "> Este template gera o arquivo `CLAUDE.md` na **raiz** do workspace.",
            "> Aponta para `Prumo/AGENT.md` e carrega a mesma Porta curta que o",
            "> runtime renderiza — manual e runtime produzem o MESMO arquivo.",
            ">",
            "> O agente de setup deve preencher `{{USER_NAME}}` e `{{AGENT_NAME}}`.",
            "> O resultado não deve conter nenhum placeholder.",
        ],
        body,
    )


def compose_agents_template() -> str:
    body = templates.render_root_wrapper(
        "agents", "{{USER_NAME}}", "{{AGENT_NAME}}", **_NESTED
    )
    return _doc(
        [
            "# Template do AGENTS.md (ponteiro de compatibilidade)",
            "",
            "> Este template gera o arquivo `AGENTS.md` na **raiz** do workspace.",
            "> Compatibilidade para agentes que procuram `AGENTS.md` (Codex, etc.).",
            "> Mesma Porta curta do runtime — manual e runtime produzem o MESMO arquivo.",
            ">",
            "> O agente de setup deve preencher `{{USER_NAME}}` e `{{AGENT_NAME}}`.",
        ],
        body,
    )


def compose_agent_md_template() -> str:
    body = templates.render_agent_md(
        user_name="{{USER_NAME}}",
        agent_name="{{AGENT_NAME}}",
        timezone_name="{{TIMEZONE}}",
        briefing_time="{{BRIEFING_TIME}}",
        core_path=_NESTED["core_path"],
        state_path=_NESTED["state_path"],
        skills_path=".prumo/skills/",
    )
    return _doc(
        [
            "# Template do Prumo/AGENT.md (fonte canônica)",
            "",
            "> Este template gera o arquivo `Prumo/AGENT.md` — a fonte canônica do",
            "> workspace. É o primeiro arquivo que qualquer agente deve ler. Todos os",
            "> ponteiros da raiz (CLAUDE.md, AGENT.md, AGENTS.md) apontam pra cá.",
            ">",
            "> O agente de setup deve preencher os placeholders `{{VARIAVEL}}`.",
            "> O resultado NÃO deve conter nenhum placeholder.",
            ">",
            "> A cadeia de fallback abaixo é DERIVADA da tabela `## Comandos",
            "> disponíveis` do core (fonte única, #172/#179) no momento da geração.",
        ],
        body,
    )


TEMPLATES: dict[str, callable] = {
    "claude-md-template.md": compose_claude_template,
    "agents-md-template.md": compose_agents_template,
    "agent-md-template.md": compose_agent_md_template,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    drift = []
    for name, compose in TEMPLATES.items():
        path = REFERENCES / name
        expected = compose()
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current == expected:
            print(f"[gen] {name}: em dia")
            continue
        if args.check:
            drift.append(name)
            print(f"[gen] {name}: DRIFT (regenerar com scripts/generate_adapter_templates.py)")
        else:
            path.write_text(expected, encoding="utf-8")
            print(f"[gen] {name}: regravado")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
