# Preflight de versão (F1)

> **module_version: 1.0.0**
>
> O MÍNIMO pra decidir se existe update e com que severidade. O protocolo
> completo (respostas, anti-nag, execução, diagnóstico por elo) mora em
> `version-update.md`, que só carrega **quando a oferta aciona**
> (`warning`/`alert`) ou quando o usuário responde — o preflight RODA
> sempre; o manual só abre quando tem trabalho (#180).

## Transporte da comparação (quem produz, #195)

- **Com runtime no PATH:** rodar `prumo version-check --ensure-fresh`. É o **produtor** do cache de versão: busca a rede **no máximo 1x/24h** (falha re-tenta em 1h) e grava o cache que o payload do briefing lê. Nos demais briefings do dia, responde do cache — zero rede. Não fazer WebFetch quando o JSON voltar `fresh: true`.
- **Sem runtime:** buscar o `VERSION` público (`raw.githubusercontent.com/tharso/prumo/main/VERSION`) — sem cache agent-owned (o agente não escreve estado fingindo ser runtime, #214). **Ordem por host:** em Cowork/host containerizado, **WebFetch PRIMEIRO** — "tem shell" ≠ "tem internet" (o shell que alcança a máquina do usuário pode não ter rede). Falha de rede num transporte = **tentar o outro**; "não consegui checar" só depois de esgotar os dois.
- Não parar no drift local: "comparar só o core do workspace contra si mesmo" não é a checagem de versão.
- **Remoto MENOR que o local é resposta SUSPEITA (#215)** — cache de CDN mentiu no caso real (5.18 servido quando o real era 5.49). Protocolo COMPLETO aqui mesmo (este caso pode nunca acionar a oferta, então o dono grande pode nunca carregar): (1) re-tentar UMA vez com **cache-busting** (query string nova, ex. `?cb=<timestamp>`); (2) se persistir menor, **declarar status desconhecido** em uma linha (*"não consegui confirmar a versão pública — resposta suspeita do CDN"*); (3) **nunca** ler "remoto menor" como "estou em dia".

## Severidade → o que fazer

1. Comparar as três pontas quando disponíveis — **incluindo a comparação remota**: remoto público × `Prumo/VERSION` local × `prumo_version` do core do workspace. Qualquer elo atrás aciona o **gatilho graduado** (#174): severidade `info` → avisar a diferença em uma linha e seguir; `warning`/`alert` → **oferta no topo** (abaixo). Não bloquear em nenhum caso.
2. Se `Prumo/VERSION` local for maior que o `prumo_version` do core (core do workspace defasado), aplicar o mesmo gatilho graduado: `info` → avisar em uma linha e seguir; `warning`/`alert` → oferta no topo (o canônico cobre este caso em "workspace core defasado").
3. Checagem falhou → registrar em uma linha e seguir. **Nunca dizer "versão em dia" sem ter comparado.**

## Oferta no topo (`warning`/`alert` — #158/#174; com o dois-tempos da #196, "no topo" = abrindo o PRIMEIRO TEMPO)

**Neste ponto, carregar `version-update.md`** e abrir o primeiro tempo com a oferta — **o briefing segue logo abaixo, na MESMA resposta** (não-bloqueante; a pergunta fica respondível a qualquer momento):

> Saiu a 5.34 (você está na 5.31) — quer que eu atualize? a) **atualizar agora**; b) **depois** — sigo e te lembro no `/fim`; c) **ver diagnóstico** primeiro.
>
> [briefing segue aqui, na mesma resposta]

Sem transporte seguro, o `a` sai da oferta (orientação por elo + `b`/`c`). A semântica das respostas, o anti-nag e o caso "sem transporte" são **canônicos no Passo 4 do `version-update.md`** — sem cópia aqui (duplicar o protocolo foi o que fez os módulos divergirem no r1 da #174). `skills_missing` não-vazio → avisar `prumo repair` (a origem do "Habilidade desconhecida").
