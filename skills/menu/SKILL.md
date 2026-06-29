---
name: menu
description: >
  Manual de instruções do Prumo. Quando o usuário diz "/menu", "ajuda", "como
  funciona", "quais são os comandos", "o que você faz", "manual", "help", a skill
  apresenta todos os comandos do Prumo com uma explicação curta de cada um e
  fecha perguntando, de forma proativa, se o usuário tem alguma dúvida sobre o
  funcionamento — ficando pronta pra responder. É uma porta de ajuda, não um
  dump: apresenta E abre conversa.
---

# Menu

Manual de instruções conversacional do Prumo. Mostra o que o sistema faz e
convida o usuário a perguntar. Resolve o "como isso funciona?" no meio da sessão.

## Fonte única dos comandos

A lista de comandos vem de **uma fonte só**: a tabela `## Comandos disponíveis`
do `PRUMO-CORE.md` do workspace. Nunca manter uma segunda cópia da lista aqui —
se um comando entra ou sai do core, o `/menu` acompanha sozinho.

- **Com runtime:** `prumo menu --workspace <ws> --format json` devolve
  `{commands: [{command, description}], ...}` lendo e parseando o core.
- **Sem runtime (fallback portável):** ler a seção `## Comandos disponíveis` do
  core direto (`.prumo/system/PRUMO-CORE.md` ou o equivalente do bundle) e
  apresentar os mesmos comandos.

## Como apresentar

1. **Abertura curta** — uma linha situando: o Prumo é uma interface única pra
   capturar, processar, lembrar e cobrar; estes são os gestos disponíveis.
2. **Manual** — listar cada comando com a explicação curta da fonte (o que faz).
   Quando fizer sentido, agrupar (entrada/dia a dia/manutenção) sem inventar
   comando que não está no core.
3. **Fechar proativo (obrigatório)** — terminar perguntando se o usuário tem
   alguma dúvida sobre como o Prumo funciona, com um convite concreto a
   responder. Ex.: *"Quer que eu detalhe algum desses, ou tem outra dúvida sobre
   como o Prumo funciona?"* Alinhado à regra "Proatividade obrigatória" do core:
   não despejar e sumir — apresentar e abrir conversa.

## Responder dúvidas

Depois da pergunta proativa, o usuário pode pedir detalhe de um comando ou
perguntar sobre o funcionamento (onde ficam os dados, como capturar, como o
briefing funciona...). Responder com base no core e nos módulos canônicos
(`prumo-core.md`, `dispatch.md`, módulos de `references/modules/`), sem inventar.
Se a dúvida virar uma ação ("então roda o briefing"), despachar pela intenção
normal (ver `dispatch.md`).

## O que o `/menu` NÃO é

- Não é onboarding/setup (isso é `/prumo:setup`, que cobre wizard e modo rápido).
- Não executa comando sozinho — apresenta e, se o usuário pedir, despacha pela
  intenção.
- Não mantém lista própria de comandos — deriva do core (fonte única).

## Referências

- `prumo menu --workspace <ws> --format json` — manual derivado do core (read-only).
- Fonte canônica da lista: `## Comandos disponíveis` em
  `skills/prumo/references/prumo-core.md`.
