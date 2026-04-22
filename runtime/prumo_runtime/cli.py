from __future__ import annotations

import argparse

from prumo_runtime import __version__
from prumo_runtime.commands import (
    run_briefing,
    run_context_dump,
    run_inbox_preview,
    run_migrate,
    run_repair,
    run_setup,
    run_start,
)
from prumo_runtime.workspace import WorkspaceError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prumo local runtime")
    parser.add_argument("--version", action="version", version=f"prumo {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    setup = subparsers.add_parser("setup", help="Preparar ou inicializar um workspace")
    setup.add_argument("--workspace", help="Caminho do workspace")
    setup.add_argument("--user-name", help="Nome preferido do usuario")
    setup.add_argument(
        "--workspace-name",
        help="Nome do workspace (ex: 'Vida Tharso', 'Pessoal'). Aparece no briefing e logs.",
    )
    setup.add_argument("--agent-name", default="Prumo", help="Nome do agente")
    setup.add_argument("--timezone", default="America/Sao_Paulo", help="Fuso IANA")
    setup.add_argument("--briefing-time", default="09:00", help="Horario preferido do briefing")
    setup.add_argument(
        "--mode",
        choices=["new", "adopt"],
        help="Forcar criacao em pasta nova ou adocao de pasta existente",
    )
    setup.set_defaults(handler=run_setup)

    start = subparsers.add_parser("start", help="Abrir a porta de entrada do Prumo no workspace")
    start.add_argument(
        "--workspace",
        help="Caminho do workspace (padrao: diretorio atual ou pai reconhecivel)",
    )
    start.add_argument("--format", choices=["text", "json"], default="text")
    start.set_defaults(handler=run_start)

    migrate = subparsers.add_parser("migrate", help="Adotar um workspace legado no trilho novo")
    migrate.add_argument("--workspace", required=True, help="Caminho do workspace")
    migrate.add_argument("--user-name", help="Nome preferido do usuario")
    migrate.add_argument("--agent-name", default="Prumo", help="Nome do agente")
    migrate.add_argument("--timezone", default="America/Sao_Paulo", help="Fuso IANA")
    migrate.add_argument("--briefing-time", default="09:00", help="Horario preferido do briefing")
    migrate.set_defaults(handler=run_migrate)

    context_dump = subparsers.add_parser("context-dump", help="Resumir o workspace para hosts")
    context_dump.add_argument("--workspace", required=True, help="Caminho do workspace")
    context_dump.add_argument("--format", choices=["json", "markdown"], default="json")
    context_dump.set_defaults(handler=run_context_dump)

    inbox = subparsers.add_parser("inbox", help="Operar a fila e o preview do inbox local")
    inbox_subparsers = inbox.add_subparsers(dest="inbox_command", required=True)

    inbox_preview = inbox_subparsers.add_parser(
        "preview",
        help="Gerar e resumir a vitrine local do Inbox4Mobile",
    )
    inbox_preview.add_argument("--workspace", required=True, help="Caminho do workspace")
    inbox_preview.add_argument("--format", choices=["text", "json"], default="text")
    inbox_preview.set_defaults(handler=run_inbox_preview)

    repair = subparsers.add_parser("repair", help="Validar e reparar arquivos recriaveis do workspace")
    repair.add_argument("--workspace", required=True, help="Caminho do workspace")
    repair.add_argument("--format", choices=["json", "text"], default="text")
    repair.set_defaults(handler=run_repair)

    briefing = subparsers.add_parser("briefing", help="Rodar um briefing local minimo")
    briefing.add_argument("--workspace", required=True, help="Caminho do workspace")
    briefing.add_argument("--format", choices=["text", "json"], default="text")
    briefing.set_defaults(handler=run_briefing)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) is None:
        args = argparse.Namespace(command="start", workspace=None, format="text", handler=run_start)
    try:
        return args.handler(args)
    except WorkspaceError as exc:
        parser.exit(2, f"erro: {exc}\n")
