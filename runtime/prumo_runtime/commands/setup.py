from __future__ import annotations

from pathlib import Path

from prumo_runtime.constants import DEFAULT_AGENT_NAME, DEFAULT_BRIEFING_TIME, DEFAULT_TIMEZONE
from prumo_runtime.workspace import (
    WorkspaceConfig,
    create_missing_files,
    ensure_workspace_exists,
    install_custom_readme,
    install_skills,
    is_already_workspace,
)


def ask_if_missing(value: str | None, prompt: str) -> str:
    if value:
        return value.strip()
    answer = input(prompt).strip()
    if not answer:
        raise SystemExit("setup cancelado: resposta vazia")
    return answer


def prompt_choice(prompt: str, options: dict[str, str], *, default: str | None = None) -> str:
    while True:
        print(prompt)
        for key, label in options.items():
            suffix = " (padrao)" if default == key else ""
            print(f"{key}) {label}{suffix}")
        answer = input("> ").strip().lower()
        if not answer and default:
            return default
        if answer in options:
            return answer
        print("Escolha uma das opcoes visiveis. Produto nao e quiz de adivinhacao.")


def ask_workspace_path(value: str | None) -> Path:
    path_value = ask_if_missing(value, "Em qual pasta o workspace deve morar? ")
    return Path(path_value).expanduser().resolve()


def detect_setup_mode(workspace: Path, explicit_mode: str | None) -> str:
    if workspace.exists() and not workspace.is_dir():
        raise SystemExit(f"setup cancelado: `{workspace}` existe, mas não é diretório")
    if explicit_mode in {"new", "adopt"}:
        return explicit_mode
    if not workspace.exists():
        return "new"
    if not any(workspace.iterdir()):
        return "new"
    return "adopt"


def ask_wrapper_policy(mode: str) -> str:
    if mode != "adopt":
        return "replace"
    choice = prompt_choice(
        "Se a raiz já tiver `AGENT.md`, `AGENTS.md` ou `CLAUDE.md`, como o Prumo deve agir?",
        {
            "a": "Mesclar um bloco curto do Prumo nos arquivos existentes (recomendado)",
            "b": "Fazer backup e substituir pelos wrappers do Prumo",
            "c": "Não tocar nesses arquivos agora",
        },
        default="a",
    )
    return {"a": "merge", "b": "replace", "c": "skip"}[choice]


def run_setup(args) -> int:
    print("Etapa 1 de 4: identidade")
    user_name = ask_if_missing(args.user_name, "Como você prefere ser chamado? ")

    print("")
    print("Etapa 2 de 4: escolher o terreno")
    workspace = ask_workspace_path(args.workspace)

    # Gatekeeper: pasta que já é workspace não pode ser re-setada.
    # Isso protege a identidade de sobrescritas silenciosas.
    if is_already_workspace(workspace):
        print("")
        print(f"`{workspace}` já tem um workspace do Prumo configurado.")
        print("Rodar setup aqui de novo pisaria na identidade existente.")
        print("")
        print("Caminhos possíveis:")
        print("- Usar `prumo repair --workspace ...` pra restaurar wrappers/índices")
        print("  sem reconfigurar do zero.")
        print("- Se você quer mesmo reconfigurar a personalidade, edite")
        print("  `Prumo/Agente/PERFIL.md` direto ou peça reconfiguração pelo agente.")
        print("- Se quer um workspace novo, escolha outra pasta.")
        raise SystemExit(1)

    mode = detect_setup_mode(workspace, getattr(args, "mode", None))

    if mode == "new":
        target_choice = prompt_choice(
            f"Vou preparar um workspace novo em `{workspace}`.",
            {
                "a": "Criar o workspace novo aqui",
                "b": "Cancelar por enquanto",
            },
            default="a",
        )
        if target_choice != "a":
            raise SystemExit("setup cancelado pelo usuario")
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        target_choice = prompt_choice(
            f"`{workspace}` ja tem conteudo, mas nao e workspace do Prumo. Como quer seguir?",
            {
                "a": "Adotar esta pasta como workspace do Prumo (Prumo vai morar aqui)",
                "b": "Cancelar para escolher outro caminho depois",
            },
            default="b",
        )
        if target_choice != "a":
            raise SystemExit("setup cancelado pelo usuario")
        ensure_workspace_exists(workspace)
    wrapper_policy = ask_wrapper_policy(mode)

    print("")
    print("Etapa 3 de 4: nomear o workspace")
    print("Esse nome aparece no briefing diário e nos logs.")
    print("Exemplos: 'Vida Tharso', 'Pessoal', 'Prumo Casa'. Pode mudar depois.")
    workspace_name = ask_if_missing(
        getattr(args, "workspace_name", None),
        "Como quer chamar esse workspace? ",
    )

    print("")
    print("Etapa 4 de 4: materializar a estrutura")
    agent_name = args.agent_name or DEFAULT_AGENT_NAME
    timezone_name = args.timezone or DEFAULT_TIMEZONE
    briefing_time = args.briefing_time or DEFAULT_BRIEFING_TIME

    config = WorkspaceConfig(
        workspace=workspace,
        user_name=user_name,
        agent_name=agent_name,
        timezone_name=timezone_name,
        briefing_time=briefing_time,
        layout_mode="nested",
        wrapper_policy=wrapper_policy,
        workspace_name=workspace_name,
    )
    result = create_missing_files(config)
    installed_skills = install_skills(workspace, layout_mode="nested")
    install_custom_readme(workspace, layout_mode="nested")

    print(f"{user_name}, o workspace do Prumo agora mora em: {workspace}")
    print("O que isso significa:")
    print("1. A raiz fica leve para descoberta por host.")
    print("2. A memória viva do usuário mora em `Prumo/`.")
    print("3. A infraestrutura atualizável do sistema mora em `/.prumo/`.")
    print("")
    print(f"Arquivos criados: {len(result['created'])}")
    for relative in result["created"]:
        print(f"- criado: {relative}")
    if result["preserved"]:
        print(f"Arquivos preservados: {len(result['preserved'])}")
        for relative in sorted(set(result["preserved"])):
            print(f"- preservado: {relative}")
    if result["merged"]:
        print(f"Wrappers mesclados: {len(result['merged'])}")
        for relative in sorted(set(result["merged"])):
            print(f"- mesclado com bloco do Prumo: {relative}")
    if result["overwritten"]:
        print(f"Wrappers substituidos: {len(result['overwritten'])}")
        for relative in sorted(set(result["overwritten"])):
            print(f"- substituido com backup: {relative}")
    if result["backed_up"]:
        print(f"Backups criados: {len(result['backed_up'])}")
        for relative in sorted(set(result["backed_up"])):
            print(f"- backup: {relative}")
    if result.get("backup_root"):
        print(f"Backup root: {result['backup_root']}")
    print("")
    print("Próximos passos:")
    print("1. Entre no workspace e rode `prumo`.")
    print("2. Em workspace novo, a primeira sessão deve começar pedindo matéria-prima, não empurrando um mapa vazio.")
    print("3. Se apagar wrapper ou índice por acidente, rode `prumo repair --workspace ...`.")
    return 0
