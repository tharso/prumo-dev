from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime import __version__
from prumo_runtime.constants import DEFAULT_AGENT_NAME


def now_display(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).strftime("%d/%m/%Y")


def _render_workspace_runtime_rules() -> str:
    return """1. Tudo que é do usuário continua legível sem o Prumo.
2. `CLAUDE.md` e `AGENTS.md` são wrappers de compatibilidade, não a fonte de verdade.
3. Se um arquivo modular faltar, usar `prumo repair` antes de inventar realidade.
4. Se o usuário chamar "Prumo" cru, "ei prumo" ou equivalente curto, consulte a tabela de skills disponíveis e leia o SKILL.md da skill `abrir`. Quando shell e runtime estiverem disponíveis, rodar `prumo` no diretório do workspace é atalho equivalente.
5. Se `prumo` não estiver no PATH do host, tente o caminho absoluto de instalação do runtime neste sistema antes de concluir que ele sumiu.
6. Se o pedido for briefing explícito, conduza a curadoria rica (skill `briefing` / `briefing-procedure.md`): email/agenda + panorama numerado único → `decidir`. O cartão do runtime é a prévia, não o briefing — não encerre nele.
7. Para o painel local estruturado (semente/backcompat), `prumo briefing --workspace . --format json`.
8. Se o host conseguir renderizar ações próprias, preferir `prumo start --format json` em vez de reinventar onboarding na unha.
9. Ao consumir JSON estruturado, o host deve ler `adapter_contract_version`, `workspace_resolution` e `adapter_hints` antes de bancar o esperto.
10. Em `start` e `briefing` estruturados, o host deve olhar primeiro para `state_flags`, `degradation`, `next_move` e `selection_contract`. A prosa vem depois.
11. Se `degradation.status` vier `error` ou `partial`, preserve o que ainda presta, mostre o tropeço em uma linha curta e, se houver `action_id` útil, priorize essa recuperação antes de inventar novo ritual.
12. Não leia arquivo para simular `prumo`, `briefing` ou `start`. Primeiro execute o comando.
13. Não escreva arquivos em `_state/` fingindo ser o runtime.
14. Não fabrique JSON de `prumo start --format json` ou `prumo briefing --workspace . --format json`. Ou retorna a saída real, ou assume que falhou.
15. Não rode comando extra só porque ficou curioso. Execute o que foi pedido ou o que o runtime sugeriu.
16. Se um comando falhar por uso ou argumento inválido, não repita a mesma linha cegamente.
17. Se houver falha parcial, preservar o que ainda presta e avisar em uma linha curta, sem despejar jargão técnico.
18. Se `next_move.id == kickoff`, prefira uma segue curta em vez de menu de confirmação.
19. Na invocação curta, não anuncie que vai rodar comando, ler JSON ou abrir arquivo. Execute primeiro e fale depois.
20. Quando houver escolha, prefira uma pergunta por vez e opções curtas. Produto não é formulário com perfume."""


def _render_wrapper_runtime_rules(*, state_path: str = "_state/") -> str:
    return f"""1. Se o usuário disser "Prumo" cru, "ei prumo" ou equivalente curto, consulte a tabela de skills disponíveis e leia o SKILL.md da skill `abrir`. Quando shell e runtime estiverem disponíveis, rodar `prumo` é atalho equivalente.
2. Se `prumo` não estiver no PATH do host, tente o caminho absoluto de instalação do runtime neste sistema antes de concluir que ele sumiu.
3. Se o pedido for briefing explícito, conduza a curadoria rica (skill `briefing` / `briefing-procedure.md`); o cartão do runtime é a prévia, não o briefing — não encerre nele.
4. Para o painel local estruturado (semente/backcompat), `prumo briefing --workspace . --format json`.
5. Se o host souber trabalhar com JSON, prefira `prumo start --format json`.
6. Se usar JSON, leia `adapter_hints` e respeite `kind`, `shell_command` e `host_prompt`.
7. Antes de olhar `message`, leia `state_flags`, `degradation`, `next_move` e `selection_contract`.
8. Se `degradation.status` vier `error` ou `partial`, preserve o que ainda funciona e priorize a ação de recuperação quando ela existir.
9. Não reinvente `setup`, `migrate`, `repair` ou `auth`. Deixe o runtime tomar a primeira decisão.
10. Não leia arquivo para simular briefing ou start. Primeiro execute o comando real.
11. Não escreva `{state_path}` fingindo ser o runtime.
12. Não rode comando extra sem necessidade.
13. Se um comando falhar por uso ou argumento inválido, não repita a mesma linha como disco riscado.
14. Em falha parcial, preserve o que ainda serve e explique o tropeço em uma linha curta, sem vazar stack trace.
15. Se `next_move.id == kickoff`, não abra cardápio de aeroporto. Faça uma segue curta e convide ao despejo inicial.
16. Na invocação curta, não narre o backstage ("vou rodar", "vou ler", "vou seguir o JSON"). Execute primeiro e fale depois.
17. Quando houver escolha real, faça uma pergunta por vez e ofereça opções curtas em vez de cardápio burocrático."""


def _render_fallback_chain(skills_path: str) -> str:
    return f"""## Cadeia de resolução de comandos

Ordem de tentativa: slash command → runtime CLI → skill direto.

Se o slash command não funcionar, tentar `prumo <comando>` no terminal.
Se o runtime não estiver no PATH, ler a skill correspondente no workspace:

| Comando | Skill |
|---|---|
| abrir | `{skills_path}abrir/SKILL.md` |
| briefing | `{skills_path}briefing/SKILL.md` |
| setup | `{skills_path}prumo/SKILL.md` |
| faxina | `{skills_path}faxina/SKILL.md` |
| higiene | `{skills_path}higiene/SKILL.md` |
| sanitize | `{skills_path}sanitize/SKILL.md` |
| doctor | `{skills_path}doctor/SKILL.md` |"""


def render_agent_md(
    user_name: str,
    agent_name: str,
    timezone_name: str,
    briefing_time: str,
    *,
    core_path: str = "PRUMO-CORE.md",
    state_path: str = "_state/",
    skills_path: str | None = None,
) -> str:
    fallback_section = ""
    if skills_path:
        fallback_section = "\n" + _render_fallback_chain(skills_path) + "\n"

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

## Regras rápidas

{_render_workspace_runtime_rules()}
"""


def render_agent_root_wrapper(
    user_name: str,
    agent_name: str,
    *,
    canonical_target: str = "AGENT.md",
    system_root: str = "_state/",
    skills_dispatch: str = "",
) -> str:
    dispatch_section = ""
    if skills_dispatch:
        dispatch_section = f"\n{skills_dispatch}\n"

    return f"""# Prumo Adapter — {user_name}

> Entrada curta para hosts que procuram `AGENT.md` na raiz.
> A fonte canônica do workspace está em `{canonical_target}`.

## Porta curta

{_render_wrapper_runtime_rules(state_path=system_root)}
{dispatch_section}
## Instrução primária

1. Leia `{canonical_target}`.
2. Não trate a raiz do workspace como almoxarifado do sistema.
3. O estado técnico do sistema mora em `{system_root}`, não na sala.

Agente: **{agent_name}**
"""


def render_claude_wrapper(
    user_name: str,
    agent_name: str,
    *,
    canonical_target: str = "AGENT.md",
    context_root: str = "Agente/",
    core_path: str = "PRUMO-CORE.md",
    state_path: str = "_state/",
    skills_dispatch: str = "",
) -> str:
    dispatch_section = ""
    if skills_dispatch:
        dispatch_section = f"\n{skills_dispatch}\n"

    return f"""# Prumo Adapter — {user_name}

> Compatibilidade para Claude/Cowork.
> Este arquivo não é a fonte canônica. Leia `{canonical_target}` primeiro.

## Porta curta

{_render_wrapper_runtime_rules(state_path=state_path)}
{dispatch_section}
## Instrução primária

1. Leia `{canonical_target}`.
2. Use `{core_path}` para regras do sistema.
3. Contexto pessoal e estável mora em `{context_root}`.

Agente: **{agent_name}**
"""


def render_agents_wrapper(
    user_name: str,
    agent_name: str,
    *,
    canonical_target: str = "AGENT.md",
    context_root: str = "Agente/",
    core_path: str = "PRUMO-CORE.md",
    state_path: str = "_state/",
    skills_dispatch: str = "",
) -> str:
    dispatch_section = ""
    if skills_dispatch:
        dispatch_section = f"\n{skills_dispatch}\n"

    return f"""# Prumo Adapter — {user_name}

> Compatibilidade para ambientes que procuram `AGENTS.md`.
> Se você está aqui, ótimo. Mas o volante mesmo está em `{canonical_target}`.

## Porta curta

{_render_wrapper_runtime_rules(state_path=state_path)}
{dispatch_section}
## Instrução primária

1. Leia `{canonical_target}`.
2. Leia `{core_path}`.
3. Contexto vivo do usuário mora em `{context_root}`.

Agente: **{agent_name}**
"""


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
