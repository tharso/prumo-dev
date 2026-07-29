# Template do Prumo/AGENT.md (fonte canônica)

> Este template gera o arquivo `Prumo/AGENT.md` — a fonte canônica do
> workspace. É o primeiro arquivo que qualquer agente deve ler. Todos os
> ponteiros da raiz (CLAUDE.md, AGENT.md, AGENTS.md) apontam pra cá.
>
> O agente de setup deve preencher os placeholders `{{VARIAVEL}}`.
> O resultado NÃO deve conter nenhum placeholder.
>
> A cadeia de fallback abaixo é DERIVADA da tabela `## Comandos
> disponíveis` do core (fonte única, #172/#179) no momento da geração.

> **Arquivo gerado** por `scripts/generate_adapter_templates.py` a partir do
> builder do runtime (`templates.py` + `wrapper_rules.py`, #179). Não editar à
> mão: mude a fonte e regenere — `test_adapter_templates_sync` guarda o drift.

---

INÍCIO DO TEMPLATE:

---

# AGENT.md

> Arquivo canônico de navegação do workspace de {{USER_NAME}}.
> Se você é um agente, comece aqui.

## Identidade rápida

- Nome preferido do usuário: {{USER_NAME}}
- Nome do agente: {{AGENT_NAME}}
- Fuso: {{TIMEZONE}}
- Briefing preferencial: {{BRIEFING_TIME}}

## Cadeia de resolução de comandos

Ordem de tentativa: slash command → runtime CLI → skill direto.

Se o slash command não funcionar e o runtime tiver subcomando homônimo,
tentar `prumo <comando>` no terminal (nem todo comando tem — `/higiene`,
por exemplo, vive só como skill; nesse caso, pular direto pra skill).
Se o runtime não estiver no PATH, ler a skill correspondente no workspace
(tabela derivada da fonte única `## Comandos disponíveis` do core):

| Comando | Skill |
|---|---|
| abrir | `.prumo/skills/abrir/SKILL.md` |
| briefing | `.prumo/skills/briefing/SKILL.md` |
| acervo | `.prumo/skills/acervo/SKILL.md` |
| menu | `.prumo/skills/menu/SKILL.md` |
| fim | `.prumo/skills/fim/SKILL.md` |
| setup | `.prumo/skills/prumo/SKILL.md` |
| higiene | `.prumo/skills/higiene/SKILL.md` |

Manutenção sem comando próprio (#172) — atende por linguagem natural:

| Intenção | Módulo |
|---|---|
| faxina (automática — roda no briefing e no `/fim`) | `.prumo/skills/prumo/references/modules/faxina.md` |
| sanitização técnica | `.prumo/skills/prumo/references/modules/sanitize.md` |
| diagnóstico da instalação (doctor) | `.prumo/skills/prumo/references/modules/doctor.md` |

## Abertura de sessão (leitura mínima)

1. Este `AGENT.md` (você já está lendo).
2. `.prumo/system/PRUMO-CORE.md` — Parte 1 (identidade e interação).
3. `.prumo/skills/prumo/references/modules/dispatch.md` — **até `## Roteamento por intenção`**: protocolo de abertura (scan leve de PAUTA + REGISTRO e saudação proativa). A seção de roteamento carrega quando o usuário falar.

Fora disso, abertura não abre mais nada. A saudação vem proativa, com 2-4 opções concretas ancoradas no scan + uma fuga explícita (`outra coisa`). Briefing não é default: só entra se o usuário expressar intenção de briefing.

## Leitura sob demanda (conforme a intenção)

- Módulos do `Agente/` (PERFIL, PESSOAS, ROTINA...) quando o playbook precisar de contexto pessoal.
- `PAUTA.md` integral, `INBOX.md`, `REGISTRO.md`.
- `.prumo/system/PRUMO-CORE.md` — Parte 2 (playbooks) e módulos da tabela de lá.

## Mapa do workspace

> Fonte canônica de navegação do workspace. Se outra árvore divergir desta, esta prevalece — e o mapa autoral soma-se a ela.

- `Agente/`: contexto modular do usuário (PERFIL, PESSOAS, ROTINA, SAUDE, INFRA, PROJETOS, RELACOES)
- `PAUTA.md`: estado vivo e pendências
- `INBOX.md`: itens ainda não processados
- `REGISTRO.md`: rastro do que aconteceu
- `IDEIAS.md`: ideias sem ação imediata
- `Referencias/`: material de referência
- `Inbox4Mobile/`: captura mobile
- `Diario/`: diários do dia gerados pelo `/fim` (a pasta nasce no primeiro uso)
- `.prumo/skills/`: skills do Prumo (fallback quando CLI não existe)
- `.prumo/system/PRUMO-CORE.md`: regras do motor e guardrails do sistema
- `.prumo/state/`: estado e metadados do runtime (`rascunho/`: seus intermediários, descartáveis)
- `.prumo/logs/`: registros de revisão

## Perímetro de leitura

O workspace pode conter outros projetos com centenas de milhares de arquivos (`node_modules`, `.git`, caches, builds) que **não** são do Prumo.

1. **Perímetro automático:** por iniciativa própria, opere apenas nos caminhos do mapa acima, somados aos declarados em `Prumo/Agente/MAPA-AUTORAL.md` (leia-o na abertura, quando existir). Zero exploração espontânea da raiz — **inclusive na descoberta**: as pastas do Prumo são sempre `Prumo/` e `.prumo/`; vá direto a elas, nunca liste a raiz pra "descobrir o workspace".
2. **Nenhuma enumeração recursiva ou ilimitada** da raiz ou de pastas fora do mapa, por qualquer ferramenta (`find`, `ls -R`, `rg --files`, `tree`, glob `**/*`, APIs de filesystem). `node_modules`, `.git`, caches e builds ficam fora de qualquer listagem, em qualquer escopo — e os backups do próprio Prumo também: `.prumo/backups/` e `.prumo/backup/` são snapshots, nunca conteúdo de trabalho (#213); listagem de `.prumo/` é rasa por default.
3. **Escopo autorizado pela tarefa:** quando o usuário citar projeto ou caminho fora do mapa, expandir de forma dirigida e rasa — listar o top-level do caminho citado e aprofundar só no rastro do alvo. Ambiguidade → perguntar o caminho, não explorar.
4. **Delegação leva o perímetro junto:** o prompt de qualquer subagente inclui os caminhos permitidos e a proibição de enumerar fora deles. Nunca "explore o workspace".

## Regras rápidas

1. Tudo que é do usuário continua legível sem o Prumo.
2. `CLAUDE.md` e `AGENTS.md` são wrappers de compatibilidade, não a fonte de verdade.
3. Se um arquivo modular faltar, usar `prumo repair` antes de inventar realidade.
4. Se o usuário chamar "Prumo" cru, "ei prumo" ou equivalente curto, consulte a tabela de skills disponíveis e leia o SKILL.md da skill `abrir`. Quando shell e runtime estiverem disponíveis, rodar `prumo` no diretório do workspace é atalho equivalente.
5. Se `prumo` não estiver no PATH do host, tente o caminho absoluto de instalação do runtime neste sistema antes de concluir que ele sumiu.
6. Se o pedido for briefing explícito, conduza a curadoria rica (skill `briefing` / `briefing-procedure.md`): email/agenda + panorama numerado único → `decidir`. O cartão do runtime é a prévia, não o briefing — não encerre nele.
7. Antes de invocar QUALQUER comando `prumo` (start, briefing, repair, setup, migrate...), carregue `.prumo/skills/prumo/references/modules/runtime-consumo.md` — escolha de formato e contrato de invocação moram lá (#228).
8. Em falha parcial, preserve o que ainda presta e explique o tropeço em uma linha curta, sem vazar stack trace nem jargão técnico.
9. Na invocação curta, não anuncie que vai rodar comando, ler JSON ou abrir arquivo. Execute primeiro e fale depois.
10. Quando houver escolha, prefira uma pergunta por vez e opções curtas. Produto não é formulário com perfume.
