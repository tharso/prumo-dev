from __future__ import annotations

import argparse

from prumo_runtime import __version__
from prumo_runtime.commands import (
    run_auth_apple_reminders,
    run_auth_google,
    run_briefing,
    run_config_apple_reminders,
    run_context_dump,
    run_migrate,
    run_repair,
    run_setup,
    run_snapshot_refresh,
    run_start,
)
from prumo_runtime.workspace import WorkspaceError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prumo local runtime")
    parser.add_argument("--version", action="version", version=f"prumo {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Preparar ou inicializar um workspace")
    setup.add_argument("--workspace", required=True, help="Caminho do workspace")
    setup.add_argument("--user-name", help="Nome preferido do usuario")
    setup.add_argument("--agent-name", default="Prumo", help="Nome do agente")
    setup.add_argument("--timezone", default="America/Sao_Paulo", help="Fuso IANA")
    setup.add_argument("--briefing-time", default="09:00", help="Horario preferido do briefing")
    setup.set_defaults(handler=run_setup)

    start = subparsers.add_parser("start", help="Abrir a porta de entrada do Prumo no workspace")
    start.add_argument(
        "--workspace",
        help="Caminho do workspace (padrao: diretorio atual ou pai reconhecivel)",
    )
    start.add_argument("--format", choices=["text", "json"], default="text")
    start.set_defaults(handler=run_start)

    auth = subparsers.add_parser("auth", help="Conectar integracoes externas ao runtime")
    auth_subparsers = auth.add_subparsers(dest="auth_provider", required=True)

    auth_google = auth_subparsers.add_parser("google", help="Conectar Google via browser OAuth")
    auth_google.add_argument("--workspace", required=True, help="Caminho do workspace")
    auth_google.add_argument(
        "--client-secrets",
        help="JSON OAuth do Google Desktop App (nao comita isso, por favor)",
    )
    auth_google.add_argument("--client-id", help="Client ID OAuth do Google Desktop App")
    auth_google.add_argument("--client-secret", help="Client secret OAuth do Google Desktop App")
    auth_google.add_argument("--project-id", help="Project ID Google (opcional, para metadado)")
    auth_google.add_argument(
        "--profile",
        default="pessoal",
        choices=["pessoal", "trabalho"],
        help="Perfil logico da conta no workspace",
    )
    auth_google.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Segundos esperando o callback do navegador",
    )
    auth_google.add_argument(
        "--no-open",
        action="store_true",
        help="Nao abre o navegador automaticamente; so imprime a URL",
    )
    auth_google.add_argument("--auth-uri", help=argparse.SUPPRESS)
    auth_google.add_argument("--token-uri", help=argparse.SUPPRESS)
    auth_google.set_defaults(handler=run_auth_google)

    auth_apple = auth_subparsers.add_parser(
        "apple-reminders",
        help="Conectar Apple Reminders localmente via EventKit (macOS)",
    )
    auth_apple.add_argument("--workspace", required=True, help="Caminho do workspace")
    auth_apple.add_argument(
        "--list",
        dest="observe_lists",
        action="append",
        help="Lista de lembretes a observar. Pode repetir a flag; sem isso, tenta ver tudo e sofre por isso.",
    )
    auth_apple.set_defaults(handler=run_auth_apple_reminders)

    config_parser = subparsers.add_parser("config", help="Ajustar configuracoes do runtime")
    config_subparsers = config_parser.add_subparsers(dest="config_target", required=True)

    config_apple = config_subparsers.add_parser(
        "apple-reminders",
        help="Mostrar ou ajustar listas observadas de Apple Reminders",
    )
    config_apple.add_argument("--workspace", required=True, help="Caminho do workspace")
    config_apple.add_argument(
        "--list",
        dest="observe_lists",
        action="append",
        help="Lista de lembretes para observar. Pode repetir.",
    )
    config_apple.add_argument(
        "--all",
        dest="all_lists",
        action="store_true",
        help="Voltar a observar todas as listas visíveis.",
    )
    config_apple.set_defaults(handler=run_config_apple_reminders)

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

    repair = subparsers.add_parser("repair", help="Validar e reparar arquivos recriaveis do workspace")
    repair.add_argument("--workspace", required=True, help="Caminho do workspace")
    repair.add_argument("--format", choices=["json", "text"], default="text")
    repair.set_defaults(handler=run_repair)

    briefing = subparsers.add_parser("briefing", help="Rodar um briefing local minimo")
    briefing.add_argument("--workspace", required=True, help="Caminho do workspace")
    briefing.add_argument(
        "--refresh-snapshot",
        action="store_true",
        help="Tentar refresh ao vivo do snapshot dual antes de responder",
    )
    briefing.set_defaults(handler=run_briefing)

    snapshot_refresh = subparsers.add_parser(
        "snapshot-refresh",
        help="Atualizar o cache local de agenda/email a partir do snapshot dual",
    )
    snapshot_refresh.add_argument("--workspace", required=True, help="Caminho do workspace")
    snapshot_refresh.add_argument(
        "--profile",
        choices=["pessoal", "trabalho"],
        help="Atualizar apenas um perfil e deixar o outro em paz",
    )
    snapshot_refresh.add_argument("--format", choices=["json", "text"], default="text")
    snapshot_refresh.set_defaults(handler=run_snapshot_refresh)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except WorkspaceError as exc:
        parser.exit(2, f"erro: {exc}\n")
