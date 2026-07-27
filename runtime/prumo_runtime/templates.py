from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime import __version__
from prumo_runtime.command_table import parse_command_table, parse_intent_modules
from prumo_runtime.constants import DEFAULT_AGENT_NAME, repo_root_from
from prumo_runtime.wrapper_rules import render_rules


def now_display(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).strftime("%d/%m/%Y")


# Blurb e instrução primária por superfície de wrapper da raiz. As REGRAS
# vêm todas de wrapper_rules.render_rules (fonte única, #179) — aqui só o
# que legitimamente varia por host.
_WRAPPER_FLAVOR: dict[str, dict] = {
    "claude": {
        "blurb": (
            "> Compatibilidade para Claude/Cowork.\n"
            "> Este arquivo não é a fonte canônica. Leia `{canonical_target}` primeiro."
        ),
        "primary": (
            "1. Leia `{canonical_target}`.",
            "2. Use `{core_path}` para regras do sistema.",
            "3. Contexto pessoal e estável mora em `{context_root}`.",
        ),
    },
    "agent": {
        "blurb": (
            "> Entrada curta para hosts que procuram `AGENT.md` na raiz.\n"
            "> A fonte canônica do workspace está em `{canonical_target}`."
        ),
        "primary": (
            "1. Leia `{canonical_target}`.",
            "2. Não trate a raiz do workspace como almoxarifado do sistema.",
            "3. O estado técnico do sistema mora em `{state_path}`, não na sala.",
        ),
    },
    "agents": {
        "blurb": (
            "> Compatibilidade para ambientes que procuram `AGENTS.md`.\n"
            "> Se você está aqui, ótimo. Mas o volante mesmo está em `{canonical_target}`."
        ),
        "primary": (
            "1. Leia `{canonical_target}`.",
            "2. Leia `{core_path}`.",
            "3. Contexto vivo do usuário mora em `{context_root}`.",
        ),
    },
}


def render_root_wrapper(
    surface: str,
    user_name: str,
    agent_name: str,
    *,
    canonical_target: str = "AGENT.md",
    context_root: str = "Agente/",
    core_path: str = "PRUMO-CORE.md",
    state_path: str = "_state/",
    skills_dispatch: str = "",
    profile: str = "full",
) -> str:
    """Builder único dos 3 wrappers da raiz (#179): só blurb e instrução
    primária variam por superfície; a Porta curta é byte-igual entre eles."""
    flavor = _WRAPPER_FLAVOR[surface]
    fields = {
        "canonical_target": canonical_target,
        "context_root": context_root,
        "core_path": core_path,
        "state_path": state_path,
    }
    blurb = flavor["blurb"].format(**fields)
    primary = "\n".join(line.format(**fields) for line in flavor["primary"])
    # Perfil minimal (#180): no CLAUDE.md o bloco dinâmico de dispatch é
    # redundante — o host tem as skills pelo plugin registry, e a porta
    # canônica aponta o protocolo. AGENTS.md/AGENT.md MANTÊM o bloco mesmo
    # em minimal: são a descoberta de skills dos hosts SEM registry (#90).
    if profile == "minimal" and surface == "claude":
        skills_dispatch = ""
    dispatch_section = f"\n{skills_dispatch}\n" if skills_dispatch else ""
    return f"""# Prumo Adapter — {user_name}

{blurb}

## Porta curta

{render_rules("wrapper", state_path=state_path, profile=profile)}
{dispatch_section}
{_render_reading_perimeter(map_reference=f"do mapa do workspace em `{canonical_target}`")}

## Instrução primária

{primary}

Agente: **{agent_name}**
"""


def _render_reading_perimeter(*, map_reference: str) -> str:
    """Seção "Perímetro de leitura" (#194).

    O workspace do usuário convive com repos de código (node_modules, .git)
    que somam centenas de milhares de arquivos — enumeração recursiva da raiz
    explode o contexto do agente. Dois escopos: perímetro automático (mapa) e
    escopo autorizado pela tarefa (expansão dirigida e rasa). A prosa daqui
    precisa manter paridade de invariantes com
    `skills/prumo/references/agent-md-template.md` (test_templates.py).
    """
    return f"""## Perímetro de leitura

O workspace pode conter outros projetos com centenas de milhares de arquivos (`node_modules`, `.git`, caches, builds) que **não** são do Prumo.

1. **Perímetro automático:** por iniciativa própria, opere apenas nos caminhos {map_reference}. Zero exploração espontânea da raiz.
2. **Nenhuma enumeração recursiva ou ilimitada** da raiz ou de pastas fora do mapa, por qualquer ferramenta (`find`, `ls -R`, `rg --files`, `tree`, glob `**/*`, APIs de filesystem). `node_modules`, `.git`, caches e builds ficam fora de qualquer listagem, em qualquer escopo — e os backups do próprio Prumo também: `.prumo/backups/` e `.prumo/backup/` são snapshots, nunca conteúdo de trabalho (#213); listagem de `.prumo/` é rasa por default.
3. **Escopo autorizado pela tarefa:** quando o usuário citar projeto ou caminho fora do mapa, expandir de forma dirigida e rasa — listar o top-level do caminho citado e aprofundar só no rastro do alvo. Ambiguidade → perguntar o caminho, não explorar.
4. **Delegação leva o perímetro junto:** o prompt de qualquer subagente inclui os caminhos permitidos e a proibição de enumerar fora deles. Nunca "explore o workspace"."""


# Comando da tabela do core → diretório da skill, quando o nome diverge.
# `setup` mora em skills/prumo/ (é a skill-CORE, #134/#135).
_COMMAND_SKILL_DIRS = {"setup": "prumo"}


def _render_fallback_chain(skills_path: str, core_text: str) -> str:
    """Cadeia de fallback DERIVADA da fonte única (#179, épico #177).

    Comandos vêm da tabela `## Comandos disponíveis` do core (a mesma que o
    `/menu` parseia); intenções sem comando (#172) vêm da subseção
    `### Manutenção sem comando próprio`. Nada hardcoded — comando que entra
    ou sai do core muda o AGENT.md renderizado sozinho.
    """
    rows = [f"| abrir | `{skills_path}abrir/SKILL.md` |"]  # entrada curta ("prumo" cru, #135)
    seen = {"abrir"}
    for cmd in parse_command_table(core_text):
        name = cmd["command"].lstrip("/")
        if name in seen:
            continue
        seen.add(name)
        skill_dir = _COMMAND_SKILL_DIRS.get(name, name)
        rows.append(f"| {name} | `{skills_path}{skill_dir}/SKILL.md` |")

    intent_rows = []
    for item in parse_intent_modules(core_text):
        module_rel = item["module"].split("skills/", 1)[-1]
        intent_rows.append(f"| {item['intent']} | `{skills_path}{module_rel}` |")

    intent_section = ""
    if intent_rows:
        intent_lines = "\n".join(intent_rows)
        intent_section = f"""

Manutenção sem comando próprio (#172) — atende por linguagem natural:

| Intenção | Módulo |
|---|---|
{intent_lines}"""

    command_lines = "\n".join(rows)
    return f"""## Cadeia de resolução de comandos

Ordem de tentativa: slash command → runtime CLI → skill direto.

Se o slash command não funcionar e o runtime tiver subcomando homônimo,
tentar `prumo <comando>` no terminal (nem todo comando tem — `/higiene`,
por exemplo, vive só como skill; nesse caso, pular direto pra skill).
Se o runtime não estiver no PATH, ler a skill correspondente no workspace
(tabela derivada da fonte única `## Comandos disponíveis` do core):

| Comando | Skill |
|---|---|
{command_lines}{intent_section}"""


def render_agent_md(
    user_name: str,
    agent_name: str,
    timezone_name: str,
    briefing_time: str,
    *,
    core_path: str = "PRUMO-CORE.md",
    state_path: str = "_state/",
    skills_path: str | None = None,
    core_text: str | None = None,
) -> str:
    fallback_section = ""
    if skills_path:
        if core_text is None:
            # Deriva da fonte única mesmo quando o caller não passa o core
            # (ex.: render fora do fluxo de setup). Em wheel, repo_root_from
            # cai no _bundled/; no pior caso o fallback literal rende uma
            # cadeia mínima (só `abrir`), nunca uma lista hardcoded paralela.
            core_text = load_prumo_core_text(repo_root_from(Path(__file__)))
        fallback_section = "\n" + _render_fallback_chain(skills_path, core_text) + "\n"

    opening_reads = [
        "1. Este `AGENT.md` (você já está lendo).",
        f"2. `{core_path}` — Parte 1 (identidade e interação).",
    ]
    if skills_path:
        opening_reads.append(
            f"3. `{skills_path}prumo/references/modules/dispatch.md` — protocolo de abertura por intenção (scan leve de PAUTA + REGISTRO e saudação proativa com opções)."
        )
    else:
        opening_reads.append(
            "3. Scan leve: cabeçalhos de `PAUTA.md` + últimas 5-10 linhas de `REGISTRO.md`. Dispatch por intenção define o que carregar a seguir."
        )
    reading_order = "\n".join(opening_reads)

    on_demand_items = ["- `Agente/PERFIL.md`, `Agente/PESSOAS.md`, `Agente/ROTINA.md` e demais módulos do `Agente/` quando o playbook precisar de contexto pessoal."]
    if skills_path:
        on_demand_items.append(
            "- `PAUTA.md` integral, `INBOX.md`, `REGISTRO.md` quando a intenção exigir (briefing, curadoria de email, revisão semanal, etc.)."
        )
        on_demand_items.append(
            f"- `{core_path}` — Parte 2 (playbooks operacionais) e demais módulos da tabela em `{core_path}`."
        )
    else:
        on_demand_items.append(
            "- `PAUTA.md` integral, `INBOX.md`, `REGISTRO.md` quando a intenção exigir."
        )
        on_demand_items.append(f"- `{core_path}` — Parte 2 e módulos operacionais conforme necessidade.")
    on_demand_section = "\n".join(on_demand_items)

    logs_path = state_path.replace("state", "logs")
    map_items = [
        "- `Agente/`: contexto modular do usuário (PERFIL, PESSOAS, ROTINA, SAUDE, INFRA, PROJETOS, RELACOES)",
        "- `PAUTA.md`: estado vivo e pendências",
        "- `INBOX.md`: itens ainda não processados",
        "- `REGISTRO.md`: rastro do que aconteceu",
        "- `IDEIAS.md`: ideias sem ação imediata",
        "- `Referencias/`: material de referência",
        "- `Inbox4Mobile/`: captura mobile",
        "- `Diario/`: diários do dia gerados pelo `/fim` (a pasta nasce no primeiro uso)",
    ]
    if skills_path:
        map_items.append(f"- `{skills_path}`: skills do Prumo (fallback quando CLI não existe)")
    map_items.extend([
        f"- `{core_path}`: regras do motor e guardrails do sistema",
        f"- `{state_path}`: estado técnico e metadados do runtime",
        f"- `{logs_path}`: registros de revisão",
    ])
    workspace_map = "\n".join(map_items)

    return f"""# AGENT.md

> Arquivo canônico de navegação do workspace de {user_name}.
> Se você é um agente, comece aqui.

## Identidade rápida

- Nome preferido do usuário: {user_name}
- Nome do agente: {agent_name}
- Fuso: {timezone_name}
- Briefing preferencial: {briefing_time}
{fallback_section}
## Abertura de sessão (leitura mínima)

{reading_order}

Fora disso, abertura não abre mais nada. A saudação vem proativa, com 2-4 opções concretas ancoradas no scan + uma fuga explícita (`outra coisa`). Briefing não é default: só entra se o usuário expressar intenção de briefing.

## Leitura sob demanda (conforme a intenção)

{on_demand_section}

## Mapa do workspace

> Fonte canônica de navegação do workspace. Se outra árvore divergir desta, esta prevalece.

{workspace_map}

{_render_reading_perimeter(map_reference="do mapa acima")}

## Regras rápidas

{render_rules("workspace", state_path=state_path)}
"""


def render_agent_root_wrapper(
    user_name: str,
    agent_name: str,
    *,
    canonical_target: str = "AGENT.md",
    system_root: str = "_state/",
    skills_dispatch: str = "",
    profile: str = "full",
) -> str:
    # AGENT.md da raiz serve hosts SEM plugin registry — segue full por
    # default (#180): contrato de invocação e dispatch moram aqui pra eles.
    return render_root_wrapper(
        "agent",
        user_name,
        agent_name,
        canonical_target=canonical_target,
        state_path=system_root,
        skills_dispatch=skills_dispatch,
        profile=profile,
    )


def render_claude_wrapper(
    user_name: str,
    agent_name: str,
    *,
    canonical_target: str = "AGENT.md",
    context_root: str = "Agente/",
    core_path: str = "PRUMO-CORE.md",
    state_path: str = "_state/",
    skills_dispatch: str = "",
    profile: str = "minimal",
) -> str:
    # Default MINIMAL (#180, decisão do dono em 16/07): o CLAUDE.md serve
    # host COM plugin registry — é porta, não manual; regras completas na
    # porta canônica e no core. É o único wrapper no cesto F0 do briefing.
    return render_root_wrapper(
        "claude",
        user_name,
        agent_name,
        canonical_target=canonical_target,
        context_root=context_root,
        core_path=core_path,
        state_path=state_path,
        skills_dispatch=skills_dispatch,
        profile=profile,
    )


def render_agents_wrapper(
    user_name: str,
    agent_name: str,
    *,
    canonical_target: str = "AGENT.md",
    context_root: str = "Agente/",
    core_path: str = "PRUMO-CORE.md",
    state_path: str = "_state/",
    skills_dispatch: str = "",
    profile: str = "full",
) -> str:
    # AGENTS.md (Codex CLI e afins) = host sem registry — full por default.
    return render_root_wrapper(
        "agents",
        user_name,
        agent_name,
        canonical_target=canonical_target,
        context_root=context_root,
        core_path=core_path,
        state_path=state_path,
        skills_dispatch=skills_dispatch,
        profile=profile,
    )


def render_agente_index_tombstone() -> str:
    """Conteúdo de aposentadoria do `Agente/INDEX.md` (Fase 2 da #97).

    Preservado por compatibilidade em workspaces migrados; aponta a navegação
    canônica para o `AGENT.md`. Sem o contrato de identidade legado
    (`- Nome preferido:`), que agora vive no `AGENT.md`/schema.
    """
    return """# Índice de contexto (aposentado)

> Este arquivo foi preservado por compatibilidade com workspaces antigos.
> A navegação canônica do workspace agora mora em `Prumo/AGENT.md`.

Para contexto pessoal, use os módulos em `Prumo/Agente/` — cada um se
descreve no próprio cabeçalho:

- `PERFIL.md` e `PESSOAS.md`: configuração pessoal e pessoas-chave
- `SAUDE.md`, `ROTINA.md`, `INFRA.md`, `PROJETOS.md`, `RELACOES.md`: contexto temático
"""


def render_people_md() -> str:
    return """# Pessoas

> Pessoas-chave, contexto, dados importantes e pendências de relacionamento.

## Pessoas-chave

_Adicionar conforme a vida real for aparecendo. Melhor isso do que ficar perguntando CPF de filha como se fosse trivia de auditório._
"""


def render_health_md() -> str:
    return """# Saúde

> Saúde, exames, médicos, medicações, histórico clínico e rotinas relevantes.

## Estado atual

_Sem informações registradas ainda._
"""


def render_perfil_md() -> str:
    return """# Perfil

> Configuração pessoal: identidade, áreas de vida e tom. Núcleo estável do perfil.
> Rituais com hora vão para a agenda; sem hora, para `ROTINA.md`. Pendência datada vai para `PAUTA.md`.

## Identidade

_Preencher no setup._

## Áreas de vida

_Preencher no setup._

## Tom

_Preencher no setup._
"""


def render_routine_md() -> str:
    return """# Rotina

> Rituais, horários, hábitos, cadências de trabalho e pontos de atrito do cotidiano.

## Estado atual

_Sem informações registradas ainda._
"""


def render_infra_md() -> str:
    return """# Infra

> Contas, domínios, ferramentas, serviços e infraestrutura digital que ainda importam.

## Estado atual

_Sem informações registradas ainda._
"""


def render_projects_md() -> str:
    return """# Projetos

> Projetos, clientes, frentes de trabalho e produtos em andamento ou hibernando.

## Estado atual

_Sem informações registradas ainda._

## Projetos registrados

> Projetos com caminho no disco que o Prumo acompanha (#201). Registre com
> `### Nome` + `- Caminho: /absoluto/ou/~/relativo-ao-home` e rode
> `prumo projetos --sync` — o pulso (git/atividade) entra no bloco gerenciado
> de cada seção; todo o resto é seu e nunca é tocado. Narrativa rica vive no
> `.prumo-contexto.md` na raiz de cada projeto (template nas references).

_Nenhum projeto registrado ainda._
"""


def render_relationships_md() -> str:
    return """# Relações

> Família, amigos e dinâmicas relacionais que merecem contexto vivo.

## Estado atual

_Sem informações registradas ainda._
"""


def render_pauta_md(setup_date: str) -> str:
    return f"""# Pauta

> Estado atual das coisas. Atualizado a cada interação relevante.

## Quente (precisa de atenção agora)

_Nada ainda._

## Em andamento

_Nada ainda._

## Agendado / Lembretes

_Compromissos e pendências com data específica. Rituais recorrentes não moram aqui — com hora vão para a agenda, sem hora para `Agente/ROTINA.md`._

## Horizonte

_Nada ainda._

## Hibernando

_Nada ainda._

---

*Última atualização: {setup_date}*
"""


def render_inbox_md() -> str:
    return """# Inbox

> Itens não processados.

_Inbox limpo._
"""


def render_registro_md() -> str:
    return """# Registro

> Audit trail do que entrou, mudou e saiu do radar.

| Data | Origem | Resumo | Ação | Destino |
|------|--------|--------|------|---------|
"""


def render_ideias_md() -> str:
    return """# Ideias

> Ideias sem próxima ação imediata.

_Nenhuma ideia registrada ainda._
"""


def render_referencias_md(setup_date: str) -> str:
    return f"""# Índice de referências

> Material de referência salvo.

| # | Título | Arquivo | Data | Descrição | Keywords |
|---|--------|---------|------|-----------|----------|

_Última atualização: {setup_date}_
"""


def render_workflows_md(setup_date: str) -> str:
    return f"""# Workflows do Prumo

> Registro dos padrões de trabalho que podem virar workflows do Prumo.
> Nesta fase, a entrega é **structure-only**: a casa fica pronta. Os workflows concretos entram depois.

## Como usar este arquivo

Registre aqui:

1. tarefas repetíveis
2. gatilhos claros
3. documentação necessária
4. pontos em que proatividade do Prumo geraria valor

## Candidatos

_Nenhum candidato registrado ainda._

## Critérios de admissão

Um workflow bom para o Prumo tende a ter:

1. repetibilidade
2. valor real para trabalho ou organização
3. necessidade de contexto/documentação
4. ganho claro com proatividade

_Última atualização: {setup_date}_
"""


def render_last_briefing_json() -> str:
    return '{\n  "at": ""\n}\n'


def render_inbox_processed_json() -> str:
    return '{\n  "version": "1.0",\n  "items": []\n}\n'


# Marcador machine-readable do stub do core vendored (#179, critério 1 do
# épico #177). Testes, doctor e o Passo 5 do version-update reconhecem por ele.
CORE_STUB_MARKER = "<!-- prumo-core-stub: v1 -->"


def render_core_stub() -> str:
    """Stub-ponteiro que substitui o core vendored em `.prumo/skills/`.

    Neste workspace o core canônico é `.prumo/system/PRUMO-CORE.md` — a casa
    que a allowlist do update manual escreve, que `parse_core_version` lê e
    de onde o `/menu` deriva. A cópia vendored virava a segunda casa (drift
    latente: update manual só atualizava a primeira). Propriedades defensivas
    do stub: sem `prumo_version:` (nenhum scanner o confunde com core; a
    validação do Passo 5 do `version-update.md` o reprova como fonte) e sem
    `## Comandos disponíveis` (`parse_command_table` devolve vazio).
    """
    return f"""# Prumo Core — ponteiro (stub)

{CORE_STUB_MARKER}
<!-- gerado por install_skills. Não editar; não copiar por cima do core. -->

Este arquivo NÃO é o core. Neste workspace, o core canônico mora em
`.prumo/system/PRUMO-CORE.md` — leia e aplique as regras de lá.

Fora de um workspace (repo clonado ou plugin instalado no host), a fonte é o
`skills/prumo/references/prumo-core.md` do próprio bundle — lá ele é completo.

1. Nunca copiar este stub por cima de `.prumo/system/PRUMO-CORE.md`. Ele não
   declara versão de propósito: usado como fonte de update manual, a
   validação do Passo 5 do `version-update.md` falha.
2. Os módulos vizinhos (`references/modules/*.md`) continuam completos e
   canônicos — só o core virou ponteiro.
"""


def load_prumo_core_text(repo_root: Path | None) -> str:
    if repo_root:
        candidate = repo_root / "skills" / "prumo" / "references" / "prumo-core.md"
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            return re.sub(
                r"prumo_version:\s*[0-9.]+",
                f"prumo_version: {__version__}",
                text,
                count=1,
            )

    return f"""# Prumo Core — Motor do sistema

> **prumo_version: {__version__}**
>
> Este é um fallback mínimo. Se você está lendo isso, o bundle canônico não veio junto e alguém montou o palco sem trazer a peça inteira.

## Comandos

1. `prumo setup`
2. `prumo briefing`
3. `prumo context-dump`
4. `prumo repair`

## Regras estáveis

1. Sempre começar por `AGENT.md`.
2. O contexto pessoal mora em `Agente/`.
3. Pendência viva vai para `PAUTA.md`.
4. Histórico resolvido vai para `REGISTRO.md`.
5. `CLAUDE.md` e `AGENTS.md` são wrappers, não a fonte da verdade.

Agente padrão: {DEFAULT_AGENT_NAME}
"""
