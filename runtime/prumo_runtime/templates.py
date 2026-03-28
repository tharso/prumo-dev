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
4. Se o usuário chamar "Prumo", "bom dia, Prumo" ou equivalente, o host deve rodar `prumo` no diretório do workspace.
5. Se `prumo` não estiver no PATH do host, tente o caminho absoluto de instalação do runtime neste sistema antes de concluir que ele sumiu.
6. Se o pedido for briefing explícito, o host pode rodar `prumo briefing --workspace . --refresh-snapshot`.
7. Se precisar de briefing estruturado, pode rodar `prumo briefing --workspace . --refresh-snapshot --format json`.
8. Se o host conseguir renderizar ações próprias, preferir `prumo start --format json` em vez de reinventar onboarding na unha.
9. Ao consumir JSON estruturado, o host deve ler `adapter_contract_version`, `workspace_resolution` e `adapter_hints` antes de bancar o esperto.
10. Em `start` e `briefing` estruturados, o host deve olhar primeiro para `state_flags`, `degradation`, `next_move` e `selection_contract`. A prosa vem depois.
11. `google_status` e `apple_reminders_status` servem para estado detalhado da integração. `state_flags` serve para decisão rápida de fluxo. Não misture os dois como se fossem a mesma gaveta.
12. Se `degradation.status` vier `error` ou `partial`, preserve o que ainda presta, mostre o tropeço em uma linha curta e, se houver `action_id` útil, priorize essa recuperação antes de inventar novo ritual.
13. Não leia arquivo para simular `prumo`, `briefing` ou `start`. Primeiro execute o comando.
14. Não escreva arquivos em `_state/` fingindo ser o runtime.
15. Não fabrique JSON de `prumo start --format json` ou `prumo briefing --format json`. Ou retorna a saída real, ou assume que falhou.
16. Não rode comando extra só porque ficou curioso. Execute o que foi pedido ou o que o runtime sugeriu.
17. Se um comando falhar por uso ou argumento inválido, não repita a mesma linha cegamente.
18. Se houver falha parcial, preservar o que ainda presta e avisar em uma linha curta, sem despejar jargão técnico.
19. Quando houver escolha, prefira uma pergunta por vez e opções curtas. Produto não é formulário com perfume."""


def _render_wrapper_runtime_rules() -> str:
    return """1. Se o usuário disser "Prumo", "bom dia, Prumo" ou equivalente, rode `prumo`.
2. Se `prumo` não estiver no PATH do host, tente o caminho absoluto de instalação do runtime neste sistema antes de concluir que ele sumiu.
3. Se o pedido for briefing explícito, rode `prumo briefing --workspace . --refresh-snapshot`.
4. Se precisar de briefing estruturado, rode `prumo briefing --workspace . --refresh-snapshot --format json`.
5. Se o host souber trabalhar com JSON, prefira `prumo start --format json`.
6. Se usar JSON, leia `adapter_hints` e respeite `kind`, `shell_command` e `host_prompt`.
7. Antes de olhar `message`, leia `state_flags`, `degradation`, `next_move` e `selection_contract`.
8. Use `google_status` e `apple_reminders_status` para narrar integração. Use `state_flags` para decidir fluxo.
9. Se `degradation.status` vier `error` ou `partial`, preserve o que ainda funciona e priorize a ação de recuperação quando ela existir.
10. Não reinvente `setup`, `migrate`, `repair` ou `auth`. Deixe o runtime tomar a primeira decisão.
11. Não leia arquivo para simular briefing ou start. Primeiro execute o comando real.
12. Não escreva `_state/` fingindo ser o runtime.
13. Não rode comando extra sem necessidade.
14. Se um comando falhar por uso ou argumento inválido, não repita a mesma linha como disco riscado.
15. Em falha parcial, preserve o que ainda serve e explique o tropeço em uma linha curta, sem vazar stack trace.
16. Quando houver escolha real, faça uma pergunta por vez e ofereça opções curtas em vez de cardápio burocrático."""


def render_agent_md(
    user_name: str,
    agent_name: str,
    timezone_name: str,
    briefing_time: str,
) -> str:
    return f"""# AGENT.md

> Arquivo canônico de navegação do workspace de {user_name}.
> Se você é um agente, comece aqui. Não chute porta em arquivo aleatório como se estivesse num galpão escuro.

## Identidade rápida

- Nome preferido do usuário: {user_name}
- Nome do agente: {agent_name}
- Fuso: {timezone_name}
- Briefing preferencial: {briefing_time}

## Ler nesta ordem

1. `Agente/INDEX.md`
2. `PAUTA.md`
3. `INBOX.md`
4. `PRUMO-CORE.md`
5. `REGISTRO.md` (quando precisar histórico)

## Mapa do workspace

- `Agente/`: contexto modular do usuário
- `PAUTA.md`: estado vivo e pendências
- `INBOX.md`: itens ainda não processados
- `REGISTRO.md`: rastro do que aconteceu
- `PRUMO-CORE.md`: regras do motor e guardrails do sistema
- `_state/`: estado técnico e metadados do runtime

## Regras rápidas

{_render_workspace_runtime_rules()}
"""


def render_claude_wrapper(user_name: str, agent_name: str) -> str:
    return f"""# Prumo Adapter — {user_name}

> Compatibilidade para Claude/Cowork.
> Este arquivo não é a fonte canônica. Leia `AGENT.md` primeiro.

## Porta curta

{_render_wrapper_runtime_rules()}

## Instrução primária

1. Leia `AGENT.md`.
2. Use `PRUMO-CORE.md` para regras do sistema.
3. Contexto pessoal e estável mora em `Agente/`.

Agente: **{agent_name}**
"""


def render_agents_wrapper(user_name: str, agent_name: str) -> str:
    return f"""# Prumo Adapter — {user_name}

> Compatibilidade para ambientes que procuram `AGENTS.md`.
> Se você está aqui, ótimo. Mas o volante mesmo está em `AGENT.md`.

## Porta curta

{_render_wrapper_runtime_rules()}

## Instrução primária

1. Leia `AGENT.md`.
2. Leia `PRUMO-CORE.md`.
3. Contexto vivo do usuário mora em `Agente/`.

Agente: **{agent_name}**
"""


def render_agente_index(
    user_name: str,
    timezone_name: str,
    briefing_time: str,
    setup_date: str,
) -> str:
    return f"""# Índice de contexto — {user_name}

> Este diretório concentra o contexto vivo do usuário.
> Se uma informação não muda o comportamento do agente nem merece memória durável, ela não ganha aluguel aqui.

## Identidade

- Nome preferido: {user_name}
- Fuso: {timezone_name}
- Briefing padrão: {briefing_time}
- Setup inicial: {setup_date}

## Onde procurar o quê

1. `PESSOAS.md`: pessoas-chave, contexto, dados e pendências de relacionamento
2. `SAUDE.md`: saúde, exames, médicos, histórico relevante
3. `ROTINA.md`: rituais, hábitos e estrutura semanal
4. `INFRA.md`: domínios, contas, infraestrutura e sistemas
5. `PROJETOS.md`: frentes de trabalho, produtos, clientes e projetos
6. `RELACOES.md`: família, amigos, dinâmica relacional e assuntos delicados

## Jurisdição

- Pendência viva: `PAUTA.md`
- Item não processado: `INBOX.md`
- Histórico e trilha do que já foi resolvido: `REGISTRO.md`
- Regras do sistema: `PRUMO-CORE.md`
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

_Nada ainda._

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


def render_briefing_state_json() -> str:
    return '{\n  "last_briefing_at": "",\n  "interrupted_at": "",\n  "resume_point": ""\n}\n'


def render_inbox_processed_json() -> str:
    return '{\n  "version": "1.0",\n  "items": []\n}\n'


def load_prumo_core_text(repo_root: Path | None) -> str:
    if repo_root:
        candidate = repo_root / "cowork-plugin" / "skills" / "prumo" / "references" / "prumo-core.md"
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
