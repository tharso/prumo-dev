---
name: abrir
description: >
  Porta de entrada do Prumo para invocação curta. Use APENAS quando o
  usuário disser "prumo" cru, "ei prumo", "olá prumo", "prumo, vamos lá",
  "/prumo:abrir", ou equivalente curto sem intenção específica. Carrega
  identidade mínima, faz scan leve do contexto e devolve saudação
  proativa com opções concretas ancoradas no estado real do workspace.
  Não dispara em "configurar prumo" (use setup), "quero começar o prumo"
  (use start), "briefing"/"painel do dia"/"começar o dia" (use briefing),
  nem em descrição longa de problema (use setup).
---

# Prumo Abrir — porta de entrada do despacho

Esta é a maçaneta. O motor está no módulo `dispatch.md` do bundle do
plugin (em `skills/prumo/references/modules/dispatch.md`). Esta skill é
curta de propósito: carrega quando o usuário toca a campainha, executa o
protocolo, devolve controle.

## Atalho via runtime (preferencial quando disponível)

Se o host tem shell e o runtime do Prumo está instalado, o atalho é
rodar `prumo` no diretório do workspace. Sem subcomando, o runtime
abre a porta de entrada (equivalente a `prumo start`):

```bash
prumo
```

A saída do runtime é fonte primária — JSON ou prosa formatada com
identidade, scan de PAUTA, próximos movimentos. Quando ela vier limpa,
use direto.

## Protocolo manual (sem shell ou runtime)

Quando o atalho não está disponível, executar o protocolo descrito em
`skills/prumo/references/modules/dispatch.md`. Resumo:

1. **Identidade mínima**: ler `Prumo/AGENT.md` + Parte 1 de
   `.prumo/system/PRUMO-CORE.md`.
2. **Scan leve**: cabeçalhos e totais de `Prumo/PAUTA.md` + últimas
   5–10 linhas de `Prumo/REGISTRO.md`. Nunca expandir PAUTA inteira
   nem ler `PERFIL.md`.
3. **Saudação proativa**: cumprimento pelo relógio + 2–4 opções
   ancoradas no scan + fuga explícita ("outra coisa"). Nunca cumprimento
   passivo + "como posso ajudar?".

Detalhe completo do protocolo, exemplos de saudação e tabela de
intenções estão em `dispatch.md`. Esta skill não duplica esse conteúdo —
referencia.

## Regras

1. **Maçaneta, não cérebro.** Esta skill abre a sessão e devolve
   controle. Não conduz briefing, setup, ou processamento de inbox.
2. **Não improvisar lendo CLAUDE.md ou outros arquivos fora do
   protocolo.** Se o protocolo diz "leia AGENT.md + scan leve", é isso.
   Não dilatar.
3. **Saudação proativa, nunca passiva.** "Bom dia, como posso ajudar?"
   é regressão de interface — sempre oferecer opções concretas.
4. **Em ambiguidade real**, perguntar com 2–3 opções curtas. Nunca
   adivinhar silenciosamente.

## Quando NÃO usar esta skill

- Usuário disse "configurar prumo", "setup" → `prumo:setup`.
- Usuário disse "quero começar o prumo", "/prumo:start" → `prumo:start`.
- Usuário disse "briefing", "painel do dia", "o que tem pra hoje" →
  `prumo:briefing`.
- Usuário descreveu problema longo ("tô perdido", "me ajuda a
  organizar minha vida") → `prumo:setup` (a description longa indica
  setup, não invocação curta).
