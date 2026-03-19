from __future__ import annotations

from pathlib import Path

from prumo_runtime.constants import DEFAULT_AGENT_NAME, DEFAULT_BRIEFING_TIME, DEFAULT_TIMEZONE
from prumo_runtime.workspace import (
    WorkspaceConfig,
    ensure_workspace_exists,
    infer_user_name,
    infer_user_name_from_legacy_claude,
    migrate_legacy_workspace,
)


def ask_if_missing(value: str | None, prompt: str) -> str:
    if value:
        return value.strip()
    answer = input(prompt).strip()
    if not answer:
        raise SystemExit("migrate cancelado: resposta vazia")
    return answer


def run_migrate(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    ensure_workspace_exists(workspace)

    inferred_name = infer_user_name(workspace) or infer_user_name_from_legacy_claude(workspace)
    user_name = ask_if_missing(args.user_name or inferred_name, "Como você prefere ser chamado? ")
    agent_name = args.agent_name or DEFAULT_AGENT_NAME
    timezone_name = args.timezone or DEFAULT_TIMEZONE
    briefing_time = args.briefing_time or DEFAULT_BRIEFING_TIME

    config = WorkspaceConfig(
        workspace=workspace,
        user_name=user_name,
        agent_name=agent_name,
        timezone_name=timezone_name,
        briefing_time=briefing_time,
    )
    result = migrate_legacy_workspace(config)

    print(f"{user_name}, o workspace legado foi adotado pelo runtime em: {workspace}")
    print("O que isso significa:")
    print("1. Arquivos canônicos do runtime foram materializados.")
    print("2. O que já era do usuário foi preservado.")
    print("3. O que foi sobrescrito ganhou backup antes.")
    print("")
    print(f"Backup: {result['backup_root']}")
    print(f"Arquivos sobrescritos: {len(result['overwritten'])}")
    for relative in result["overwritten"]:
        print(f"- sobrescrito com backup: {relative}")
    if result["created"]:
        print(f"Arquivos criados: {len(result['created'])}")
        for relative in result["created"]:
            print(f"- criado: {relative}")
    if result["preserved"]:
        print(f"Arquivos preservados: {len(result['preserved'])}")
        for relative in sorted(set(result["preserved"])):
            print(f"- preservado: {relative}")
    print("")
    print("Próximos passos:")
    print("1. Rode `prumo context-dump --workspace ...` para confirmar a adoção.")
    print("2. Rode `prumo briefing --workspace ...` para testar o trilho novo.")
    print("3. Se algo cheirar errado, compare com o backup antes de inventar heroísmo.")
    return 0
