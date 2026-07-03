# Weekly Review

> **module_version: 4.19.0**
>
> Fonte canônica da revisão semanal do Prumo.

## Objetivo

Revisar a pauta inteira sem a miopia do briefing diário.

## Checklist

1. Ler `PAUTA.md` inteira.
2. Mostrar todos os agendados, mesmo com `| cobrar: DD/MM` futuro.
3. Perguntar:
   - o que avançou?
   - o que travou?
   - o que deve sair da frente?
4. Revisar `README.md` das áreas com contexto novo.
5. Revisar `IDEIAS.md`:
   - ideia amadureceu -> vira ação;
   - ideia ainda é só ideia -> fica onde está.
   - **Garimpo associativo** (hook da regra 17 do core): ao revisar as ideias
     (e as fichas de `Referencias/`), propor conexões entre itens que
     conversam — "X e Y tratam de Z; ligo?". Regras:
     - Conexão aprovada é escrita **nos próprios itens**, como `[[wikilink]]`
       ou prosa "Veja também:", com **confirmação verificável**: antes de
       gravar, mostrar arquivo, item-alvo e o **texto exato** a inserir
       ("em `IDEIAS.md`, no item 'X', acrescento ` — veja também [[Y]]`.
       OK?"). Nada de aprovação em lote sem o texto à vista.
     - **Nenhum índice materializado de pontes** (lição da #97): as conexões
       moram nos itens; não existe arquivo/mapa/índice de conexões.
     - A varredura associativa pesada mora **aqui** (semanal) — não no
       briefing (load-policy) e não na faxina (que nunca julga).
     - Efeito no `acervo`: conexão escrita muda o `content_hash` do item;
       relatório antigo do acervo fica bloqueado para delete daquele item
       (hash divergente → pede revisão) — proteção correta, não bug.
6. Revisar `Agente/PESSOAS.md` quando existir:
   - follow-ups;
   - quem sumiu;
   - pendências de relacionamento.
7. Revisar `Agente/ROTINA.md` quando existir (poda de contexto — contenção do ROTINA):
   - rotina que mudou ou morreu (não é mais verdade);
   - ritual com hora que deveria estar só na agenda (não duplicar no ROTINA);
   - virou histórico de ocorrências em vez de padrão estável;
   - propor remoção do que não muda mais nenhuma decisão (sempre com confirmação).
8. Calcular mini-resumo de fluxo:
   - itens entrados;
   - itens completados;
   - itens descartados;
   - item mais antigo parado.
9. Mover "Semana atual — Concluídos" para "Semana passada — Concluídos".
10. Limpar semana passada anterior.
11. Registrar resumo em `.prumo/logs/YYYY-WXX.md`.

## Tom

Revisão semanal não é faxina passiva. É poda. O objetivo é deixar menos item fingindo prioridade.
