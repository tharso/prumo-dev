# Template do CLAUDE.md (ponteiro de compatibilidade)

> Este template gera o arquivo `CLAUDE.md` na **raiz** do workspace.
> Aponta para `Prumo/AGENT.md` e carrega a mesma Porta curta que o
> runtime renderiza — manual e runtime produzem o MESMO arquivo.
>
> O agente de setup deve preencher `{{USER_NAME}}` e `{{AGENT_NAME}}`.
> O resultado não deve conter nenhum placeholder.

> **Arquivo gerado** por `scripts/generate_adapter_templates.py` a partir do
> builder do runtime (`templates.py` + `wrapper_rules.py`, #179). Não editar à
> mão: mude a fonte e regenere — `test_adapter_templates_sync` guarda o drift.

---

INÍCIO DO TEMPLATE:

---

# Prumo Adapter — {{USER_NAME}}

> Compatibilidade para Claude/Cowork.
> Este arquivo não é a fonte canônica. Leia `Prumo/AGENT.md` primeiro.

## Porta curta

1. Se o usuário chamar "Prumo" cru, "ei prumo" ou equivalente curto, consulte a tabela de skills disponíveis e leia o SKILL.md da skill `abrir`. Quando shell e runtime estiverem disponíveis, rodar `prumo` no diretório do workspace é atalho equivalente.
2. Se `prumo` não estiver no PATH do host, tente o caminho absoluto de instalação do runtime neste sistema antes de concluir que ele sumiu.
3. Se o pedido for briefing explícito, conduza a curadoria rica (skill `briefing` / `briefing-procedure.md`): email/agenda + panorama numerado único → `decidir`. O cartão do runtime é a prévia, não o briefing — não encerre nele.
4. Para o painel local estruturado (semente/backcompat), `prumo briefing --workspace . --format json`.
5. Se o host souber trabalhar com JSON, prefira `prumo start --format json`.
6. Se usar JSON, leia `adapter_hints` e respeite `kind`, `shell_command` e `host_prompt`.
7. Antes de olhar `message`, leia `state_flags`, `degradation`, `next_move` e `selection_contract`. A prosa vem depois.
8. Se `degradation.status` vier `error` ou `partial`, preserve o que ainda presta, mostre o tropeço em uma linha curta e, se houver `action_id` útil, priorize essa recuperação antes de inventar novo ritual.
9. Não reinvente `setup`, `migrate`, `repair` ou `auth`. Deixe o runtime tomar a primeira decisão.
10. Não leia arquivo para simular `prumo`, `briefing` ou `start`. Primeiro execute o comando real.
11. Não escreva `.prumo/state/` fingindo ser o runtime.
12. Não rode comando extra só porque ficou curioso. Execute o que foi pedido ou o que o runtime sugeriu.
13. Se um comando falhar por uso ou argumento inválido, não repita a mesma linha como disco riscado.
14. Em falha parcial, preserve o que ainda presta e explique o tropeço em uma linha curta, sem vazar stack trace nem jargão técnico.
15. Se `next_move.id == kickoff`, não abra cardápio de aeroporto. Faça uma segue curta e convide ao despejo inicial.
16. Na invocação curta, não anuncie que vai rodar comando, ler JSON ou abrir arquivo. Execute primeiro e fale depois.
17. Quando houver escolha, prefira uma pergunta por vez e opções curtas. Produto não é formulário com perfume.

## Perímetro de leitura

O workspace pode conter outros projetos com centenas de milhares de arquivos (`node_modules`, `.git`, caches, builds) que **não** são do Prumo.

1. **Perímetro automático:** por iniciativa própria, opere apenas nos caminhos do mapa do workspace em `Prumo/AGENT.md`. Zero exploração espontânea da raiz.
2. **Nenhuma enumeração recursiva ou ilimitada** da raiz ou de pastas fora do mapa, por qualquer ferramenta (`find`, `ls -R`, `rg --files`, `tree`, glob `**/*`, APIs de filesystem). `node_modules`, `.git`, caches e builds ficam fora de qualquer listagem, em qualquer escopo.
3. **Escopo autorizado pela tarefa:** quando o usuário citar projeto ou caminho fora do mapa, expandir de forma dirigida e rasa — listar o top-level do caminho citado e aprofundar só no rastro do alvo. Ambiguidade → perguntar o caminho, não explorar.
4. **Delegação leva o perímetro junto:** o prompt de qualquer subagente inclui os caminhos permitidos e a proibição de enumerar fora deles. Nunca "explore o workspace".

## Instrução primária

1. Leia `Prumo/AGENT.md`.
2. Use `.prumo/system/PRUMO-CORE.md` para regras do sistema.
3. Contexto pessoal e estável mora em `Prumo/Agente/`.

Agente: **{{AGENT_NAME}}**
