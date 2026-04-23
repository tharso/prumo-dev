from __future__ import annotations

import os
import shlex
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.workspace import (
    build_config_from_existing,
    extract_section,
    filter_by_due_date,
    load_json,
    read_text,
)
from prumo_runtime.workspace_paths import workspace_paths


SHORT_ACCEPTANCE_TOKENS = ["1", "a", "aceitar", "aceitar e seguir", "seguir", "ok"]


def shell_action(
    action_id: str,
    label: str,
    shell_command: str,
    *,
    category: str,
    documentation_targets: list[str] | None = None,
    outcome: str | None = None,
    why_now: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": action_id,
        "label": label,
        "kind": "shell",
        "category": category,
        "command": shell_command,
        "shell_command": shell_command,
    }
    if documentation_targets:
        payload["documentation_targets"] = documentation_targets
    if outcome:
        payload["outcome"] = outcome
    if why_now:
        payload["why_now"] = why_now
    return payload


def host_prompt_action(
    action_id: str,
    label: str,
    host_prompt: str,
    *,
    category: str,
    documentation_targets: list[str] | None = None,
    outcome: str | None = None,
    why_now: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": action_id,
        "label": label,
        "kind": "host-prompt",
        "category": category,
        "command": host_prompt,
        "host_prompt": host_prompt,
    }
    if documentation_targets:
        payload["documentation_targets"] = documentation_targets
    if outcome:
        payload["outcome"] = outcome
    if why_now:
        payload["why_now"] = why_now
    return payload


def next_move_payload(actions: list[dict[str, object]]) -> dict[str, object] | None:
    if not actions:
        return None
    action = actions[0]
    payload = {
        "id": action["id"],
        "label": action["label"],
        "kind": action["kind"],
        "command": action["command"],
    }
    if "shell_command" in action:
        payload["shell_command"] = action["shell_command"]
    if "host_prompt" in action:
        payload["host_prompt"] = action["host_prompt"]
    if "documentation_targets" in action:
        payload["documentation_targets"] = action["documentation_targets"]
    if "outcome" in action:
        payload["outcome"] = action["outcome"]
    if "why_now" in action:
        payload["why_now"] = action["why_now"]
    if "priority" in action:
        payload["priority"] = action["priority"]
    if "recommended" in action:
        payload["recommended"] = action["recommended"]
    if "kickoff_contract" in action:
        payload["kickoff_contract"] = action["kickoff_contract"]
    if "initial_question" in action:
        payload["initial_question"] = action["initial_question"]
    return payload


def selection_contract_payload(next_move: dict[str, object] | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "accept_tokens": SHORT_ACCEPTANCE_TOKENS,
        "accept_behavior": (
            "execute next_move directly without rerunning start and without showing another menu first"
        ),
        "post_action_behavior": (
            "after executing an imperative request or accepted next_move, report concrete outcome and "
            "documentation changes before offering new options"
        ),
    }
    if next_move:
        payload["accepts_next_move"] = next_move["id"]
    return payload


def render_action_menu_lines(
    actions: list[dict[str, object]],
    next_move: dict[str, object] | None,
    workspace: Path,
) -> list[str]:
    """Menu humano: recomendação visível + alternativas nomeadas.

    Sem colapsar em 'Ver lista completa': quando há next_move, a primeira opção
    é 'Aceitar', e as próximas listam alternativas pelo nome real. Align-core
    sempre aparece pelo nome quando presente, para que drift do motor não fique
    escondido em menu genérico.
    """
    lines: list[str] = []
    letters = list("abcdefghij")

    if not next_move:
        for letter, action in zip(letters, actions):
            lines.append(f"{letter}) {action['label']}")
            lines.append(f"   `{action['command']}`")
        return lines

    next_move_id = str(next_move.get("id") or "")
    actions_by_id = {str(action["id"]): action for action in actions}

    alt_priority = [
        "align-core",
        "briefing",
        "continue",
        "process-inbox",
        "organize-day",
        "repair",
        "kickoff",
    ]
    alternatives: list[dict[str, object]] = []
    for alt_id in alt_priority:
        if alt_id == next_move_id:
            continue
        action = actions_by_id.get(alt_id)
        if action is None:
            continue
        alternatives.append(action)
    alternatives = alternatives[:5]

    lines.append(f"{letters[0]}) Aceitar: {next_move['label']}")
    offset = 1
    for index, action in enumerate(alternatives):
        letter = letters[offset + index]
        lines.append(f"{letter}) {action['label']}")
        lines.append(f"   `{action['command']}`")
    offset += len(alternatives)

    context_letter = letters[offset]
    lines.append(f"{context_letter}) Ver estado técnico")
    lines.append(f"   `prumo context-dump --workspace {workspace} --format json`")
    offset += 1

    final_letter = letters[min(offset, len(letters) - 1)]
    lines.append(f"{final_letter}) Tá bom por hoje")

    return lines


def kickoff_contract_payload(workspace: Path) -> dict[str, object]:
    docs = documentation_targets(workspace)
    return {
        "mode": "new-workspace",
        "conversation_style": "dump-first",
        "ask_one_question_at_a_time": True,
        "show_value_before_menu": True,
        "avoid_empty_briefing": True,
        "initial_invitation": (
            "Me conta as coisas que estao ocupando sua cabeca agora. Pode ser compromisso, projeto, pendencia, ideia, "
            "email que precisa resposta ou qualquer outra coisa puxando sua atencao. Nao precisa organizar nem explicar "
            "tudo direito. Vai despejando que eu vou te ajudando a separar isso no caminho."
        ),
        "capture_targets": {
            "pauta": docs["pauta"],
            "inbox": docs["inbox"],
            "registro": docs["registro"],
        },
        "first_reflection_contract": {
            "reflect_back_before_classifying_deeply": True,
            "max_blocks": 4,
            "prefer_concrete_labels": True,
            "end_with_one_follow_up_question": True,
            "avoid_menu_before_reflection": True,
            "avoid_long_recap": True,
        },
        "suggested_flow": [
            "abrir explicando em uma linha que o workspace ainda esta cru, mas a sessao vai montar o primeiro mapa util",
            "convidar o usuario a fazer um despejo mental curto, sem exigir classificacao previa",
            "organizar o material em blocos ou frentes e refletir isso de volta de forma curta, em no maximo 4 blocos",
            "fazer uma pergunta de afunilamento so depois da primeira devolucao",
            "registrar o minimo util em documentacao viva",
            "encerrar com um proximo movimento plausivel",
        ],
        "success_definition": (
            "deixar o workspace com alguma frente, prioridade ou nota inicial registrada, mostrando que o Prumo consegue organizar o caos antes de pedir formulario"
        ),
        "follow_up_rule": (
            "depois da primeira devolucao organizada, fazer uma unica pergunta curta para afunilar prioridade, urgencia ou foco"
        ),
    }


def pauta_candidates(workspace: Path) -> tuple[list[str], list[str]]:
    config = build_config_from_existing(workspace)
    today = datetime.now(ZoneInfo(config.timezone_name)).date()
    pauta = read_text(workspace_paths(workspace).pauta)
    hot = filter_by_due_date(extract_section(pauta, "Quente"), today)
    ongoing = filter_by_due_date(extract_section(pauta, "Em andamento"), today)
    clean_hot = [item for item in hot if "_Nada ainda._" not in item and "Nada ainda." not in item]
    clean_ongoing = [item for item in ongoing if "_Nada ainda._" not in item and "Nada ainda." not in item]
    return clean_hot, clean_ongoing


def clean_pauta_item(value: str | None) -> str:
    text = str(value or "").strip()
    if text.startswith("- "):
        text = text[2:].strip()
    return text


def choose_continue_item(workspace: Path) -> str | None:
    hot, ongoing = pauta_candidates(workspace)
    if hot:
        return hot[0]
    if ongoing:
        return ongoing[0]
    return None


def documentation_targets(workspace: Path) -> dict[str, str]:
    paths = workspace_paths(workspace)
    return {
        "pauta": str(paths.pauta.resolve()),
        "inbox": str(paths.inbox.resolve()),
        "registro": str(paths.registro.resolve()),
        "workflow_registry": str(paths.workflows_index.resolve()),
    }


def count_markdown_items(markdown: str) -> int:
    count = 0
    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(">") or stripped.startswith("_"):
            continue
        if stripped.startswith(("- ", "* ")):
            count += 1
        elif len(stripped) >= 4 and stripped[:2].isdigit() and stripped[2:4] == ". ":
            count += 1
    return count


def registro_entry_count(markdown: str) -> int:
    count = 0
    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("| Data |") or stripped.startswith("|------"):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            count += 1
    return count


def inbox_item_count(workspace: Path) -> int:
    paths = workspace_paths(workspace)
    preview_payload = load_json(paths.inbox_preview_index)
    preview_items = preview_payload.get("items")
    if isinstance(preview_items, list) and preview_items:
        return len(preview_items)
    return count_markdown_items(read_text(paths.inbox))


def is_fresh_workspace(workspace: Path) -> bool:
    paths = workspace_paths(workspace)
    hot, ongoing = pauta_candidates(workspace)
    if hot or ongoing:
        return False
    if inbox_item_count(workspace) > 0:
        return False
    if registro_entry_count(read_text(paths.registro)) > 0:
        return False
    if count_markdown_items(read_text(paths.ideias)) > 0:
        return False
    return True


def suggest_core_alignment_action(workspace: Path, overview: dict) -> dict[str, object]:
    workspace_str = shlex.quote(str(workspace))
    user_name = shlex.quote(str(overview["user_name"]))
    agent_name = shlex.quote(str(overview["agent_name"]))
    timezone_name = shlex.quote(str(overview["timezone"]))
    briefing_time = shlex.quote(str(overview["briefing_time"]))
    core_version = str(overview.get("core_version") or "ausente")
    runtime_version = str(overview.get("runtime_version") or "atual")
    label = f"Atualizar o motor (core {core_version} → runtime {runtime_version})"
    return shell_action(
        "align-core",
        label,
        (
            f"prumo migrate --workspace {workspace_str} --user-name {user_name} "
            f"--agent-name {agent_name} --timezone {timezone_name} --briefing-time {briefing_time}"
        ),
        category="workspace-alignment",
        outcome="Core e wrappers canônicos reaplicados com backup, para o host parar de tropeçar em placa antiga.",
        why_now="Drift entre runtime e core costuma render comportamento fantasma, e fantasma em produto diário só serve para atrasar café.",
    )


def daily_operation_payload(workspace: Path) -> dict[str, object]:
    docs = documentation_targets(workspace)
    return {
        "mode": "daily-operator",
        "supports": [
            "briefing",
            "continuation",
            "inbox-triage",
            "documentation",
            "workflow-scaffolding",
        ],
        "documentation_targets": list(docs.values())[:3],
        "workflow_registry_path": docs["workflow_registry"],
        "documentation_contract": {
            "update_pauta": docs["pauta"],
            "update_inbox": docs["inbox"],
            "append_registro": docs["registro"],
            "register_workflows": docs["workflow_registry"],
        },
        "quality_bar": {
            "briefing_is_not_enough": True,
            "must_support_continuation": True,
            "must_leave_useful_documentation": True,
        },
        "documentation_rules": {
            "touch_lightly": True,
            "do_not_rewrite_whole_files_without_need": True,
            "separate_source_from_decision": True,
            "log_decisions_in_registro": True,
            "keep_workflow_registry_structure": True,
        },
        "conversation_rules": {
            "lead_with_next_move_when_obvious": True,
            "avoid_menu_dump_when_one_path_is_clearly_hotter": True,
            "prefer_execution_plus_documentation_over_commentary": True,
            "short_acceptance_executes_next_move": True,
            "after_explicit_execution_do_not_return_with_menu": True,
        },
    }


def build_daily_actions(
    workspace: Path,
    overview: dict,
    *,
    has_briefed_today: bool,
) -> list[dict[str, object]]:
    workspace_str = str(workspace)
    missing = overview["missing"]
    continue_item = clean_pauta_item(choose_continue_item(workspace))
    docs = documentation_targets(workspace)
    inbox_count = inbox_item_count(workspace)
    fresh_workspace = is_fresh_workspace(workspace)

    actions_by_id: dict[str, dict[str, object]] = {}

    def register(action: dict[str, object] | None) -> None:
        if action is None:
            return
        actions_by_id[str(action["id"])] = action

    if missing["generated"] or missing["derived"]:
        register(
            shell_action(
                "repair",
                "Consertar a estrutura antes de brincar de produtividade",
                f"prumo repair --workspace {workspace_str}",
                category="repair",
                documentation_targets=[docs["pauta"], docs["inbox"], docs["registro"]],
                outcome="Workspace consistente o bastante para o Prumo não tropeçar na própria sandália.",
                why_now="Sem estrutura minimamente inteira, qualquer produtividade aqui vira teatro com cenário caindo.",
            )
        )

    if overview.get("core_outdated"):
        register(suggest_core_alignment_action(workspace, overview))

    if not has_briefed_today and fresh_workspace:
        kickoff_contract = kickoff_contract_payload(workspace)
        register(
            host_prompt_action(
                "kickoff",
                "Abrir sessão de arranque por despejo assistido",
                (
                    "O workspace acabou de nascer e ainda nao tem tracao real. "
                    f"Conduza uma sessao curta de arranque usando `{docs['pauta']}`, `{docs['inbox']}` e "
                    f"`{docs['registro']}` como destino. Nao comece pedindo classificacao. Comece por: "
                    f"\"{kickoff_contract['initial_invitation']}\". Organize o material em blocos curtos, "
                    "devolva o que entendeu em no maximo quatro blocos e so depois afunile com uma pergunta por vez."
                ),
                category="onboarding",
                documentation_targets=[docs["pauta"], docs["inbox"], docs["registro"]],
                outcome="Primeiras frentes e prioridades capturadas sem fingir que o vazio ja e contexto.",
                why_now="Briefing de apartamento vazio so prova que ainda nao ha moveis. Sessao de arranque pelo menos compra utilidade.",
            )
        )
        actions_by_id["kickoff"]["kickoff_contract"] = kickoff_contract
        actions_by_id["kickoff"]["initial_question"] = kickoff_contract["initial_invitation"]
    else:
        register(
            shell_action(
                "briefing",
                "Rodar o briefing agora" if not has_briefed_today else "Rodar o briefing de novo",
                f"prumo briefing --workspace {workspace_str} --refresh-snapshot",
                category="briefing",
                documentation_targets=[docs["pauta"], docs["inbox"], docs["registro"]],
                outcome="Panorama atualizado com proposta do dia e contexto suficiente para seguir trabalhando.",
                why_now=(
                    "Ainda não houve briefing hoje; antes de acelerar, convém olhar o painel do carro."
                    if not has_briefed_today
                    else "Vale reabrir o radar quando o contexto já esquentou ou mudou desde o último briefing."
                ),
            )
        )

    if continue_item:
        register(
            host_prompt_action(
                "continue",
                f"Retomar o que já estava quente: {continue_item}",
                (
                    "Continue pelo item da pauta: "
                    f"{continue_item}. Enquanto avança, registre decisões, próximos passos e pendências "
                    f"em `{docs['pauta']}` e `{docs['registro']}` sem inventar contexto."
                ),
                category="continuation",
                documentation_targets=[docs["pauta"], docs["registro"]],
                outcome="Trabalho retomado com próximos passos e decisão registrada em documentação viva.",
                why_now="O custo de retomar algo já quente costuma ser menor do que abrir uma nova gaveta por esporte.",
            )
        )

    if inbox_count:
        register(
            host_prompt_action(
                "process-inbox",
                f"Processar a fila que está encostada ({inbox_count} item(ns))",
                (
                    f"Processe a fila atual do workspace. Triague itens de `{docs['inbox']}` "
                    "e, se houver preview de Inbox4Mobile, use isso para priorizar. "
                    f"Atualize `{docs['pauta']}` com próximos passos, limpe o que for resolvido de `{docs['inbox']}` "
                    f"e registre decisões em `{docs['registro']}`."
                ),
                category="inbox-triage",
                documentation_targets=[docs["pauta"], docs["inbox"], docs["registro"]],
                outcome="Inbox menor, pauta mais clara e rastro do que foi decidido.",
                why_now="Fila encostada tende a apodrecer rápido e depois cobra juros em contexto perdido.",
            )
        )

    register(
        host_prompt_action(
            "organize-day",
            "Organizar o dia e a documentação viva",
            (
                f"Organize o dia a partir de `{docs['pauta']}`, `{docs['inbox']}` e `{docs['registro']}`. "
                "Atualize próximos passos, pendências, decisões e pontos de bloqueio sem inventar contexto."
            ),
            category="documentation",
            documentation_targets=[docs["pauta"], docs["inbox"], docs["registro"]],
            outcome="Workspace mais respirável, com pendências, decisões e foco do dia explicitados.",
            why_now="Se o workspace continuar bagunçado, o resto do dia vira caça ao contexto com lanterna fraca.",
        )
    )

    if os.environ.get("PRUMO_ENABLE_WORKFLOW_SCAFFOLD_ACTIONS") == "1":
        register(
            host_prompt_action(
                "workflow-scaffold",
                "Preparar candidatos a workflow sem fechar nada à força",
                (
                    f"Revise o trabalho atual e registre em `{docs['workflow_registry']}` padrões repetíveis, gatilhos, "
                    "documentação necessária e pontos de proatividade que pareçam bons candidatos a workflow do Prumo. "
                    "Não transforme isso em workflow fechado ainda."
                ),
                category="workflow-scaffolding",
                documentation_targets=[docs["workflow_registry"], docs["registro"]],
                outcome="Candidatos a workflow registrados sem vender promessa de automação antes da hora.",
                why_now="Padrão repetido sem registro é só deja vu desperdiçado.",
            )
        )

    register(
        shell_action(
            "context",
            "Ver o estado técnico sem poesia",
            f"prumo context-dump --workspace {workspace_str} --format json",
            category="diagnostics",
            documentation_targets=[docs["pauta"], docs["inbox"], docs["registro"]],
            outcome="Estado técnico explícito para host ou diagnóstico humano sem telepatia.",
            why_now="Diagnóstico é útil quando há dúvida real, não como aquecimento obrigatório antes de agir.",
        )
    )

    order: list[str] = []
    if "repair" in actions_by_id:
        order.append("repair")
    if not has_briefed_today:
        order.extend(["kickoff", "briefing", "continue", "process-inbox", "organize-day"])
    elif continue_item:
        order.extend(["continue", "process-inbox", "organize-day", "briefing"])
    elif inbox_count:
        order.extend(["process-inbox", "organize-day", "briefing"])
    else:
        order.extend(["organize-day", "briefing"])
    if "align-core" in actions_by_id:
        order.append("align-core")
    order.extend(["workflow-scaffold", "context"])

    ordered: list[dict[str, object]] = []
    seen: set[str] = set()
    for action_id in order:
        action = actions_by_id.get(action_id)
        if action is None or action_id in seen:
            continue
        ordered.append(action)
        seen.add(action_id)

    for index, action in enumerate(ordered, start=1):
        action["priority"] = max(1, 100 - (index * 10))
        action["recommended"] = index == 1

    return ordered[:8]
