from __future__ import annotations

from pathlib import Path

from prumo_runtime.constants import DEFAULT_AGENT_NAME, DEFAULT_BRIEFING_TIME, DEFAULT_TIMEZONE
from prumo_runtime.workspace import WorkspaceConfig, create_missing_files, ensure_workspace_exists


def ask_if_missing(value: str | None, prompt: str) -> str:
    if value:
        return value.strip()
    answer = input(prompt).strip()
    if not answer:
        raise SystemExit("setup cancelado: resposta vazia")
    return answer


def run_setup(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    ensure_workspace_exists(workspace)

    user_name = ask_if_missing(args.user_name, "Como você prefere ser chamado? ")
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
    result = create_missing_files(config)

    print(f"{user_name}, o workspace do Prumo agora mora em: {workspace}")
    print("O que isso significa:")
    print("1. Esta pasta vira a base legível do sistema.")
    print("2. O Prumo só cria e organiza os arquivos dele aqui.")
    print("3. Se um dia você parar de usar o Prumo, basta desinstalar. Nada do que é seu desaparece.")
    print("")
    print(f"Arquivos criados: {len(result['created'])}")
    for relative in result["created"]:
        print(f"- criado: {relative}")
    if result["preserved"]:
        print(f"Arquivos preservados: {len(result['preserved'])}")
        for relative in sorted(set(result["preserved"])):
            print(f"- preservado: {relative}")
    print("")
    print("Próximos passos:")
    print("1. Rode `prumo context-dump --workspace ...` para inspecionar a estrutura.")
    print("2. Rode `prumo briefing --workspace ...` para testar o trilho novo.")
    print("3. Se apagar wrapper ou índice por acidente, rode `prumo repair --workspace ...`.")
    return 0
