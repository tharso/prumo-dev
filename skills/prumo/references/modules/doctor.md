# Doctor do Runtime (módulo do core)

> Era a skill top-level `doctor` até a 5.31 — a #172 tirou o diagnóstico do
> picker. Roda a pedido em linguagem natural ("diagnostica o runtime",
> "o plugin tá saudável?", "roda o doctor") ou direto pelo script.

Aqui é diagnóstico: checar se o runtime, o marketplace e o plugin estão no lugar certo.

## Carregamento obrigatório

1. Leia `.prumo/system/PRUMO-CORE.md` se existir no workspace.
2. Leia:
   - `skills/prumo/references/modules/cowork-runtime-maintenance.md`
   - `skills/prumo/references/modules/runtime-paths.md`

## Fluxo

1. Rodar `prumo_cowork_doctor.sh` resolvendo scripts pela ordem definida em `runtime-paths.md`.
2. Responder em 4 blocos curtos numerados continuamente, **cada elo com semáforo** (`🟢 ok` / `🟡 defasado` / `🔴 quebrado`) na frente, pra a saúde saltar aos olhos:
   - `Runtime` — versão do CLI vs. core.
   - `Marketplace` — checkout: `🟢` em dia; `🟡` atrás (ff resolve); `🔴` divergente (história reescrita, #145) ou com commits locais.
   - `Plugin` — instalado vs. catálogo; `🔴` se pré-5.x (era pré-skills-first, #146).
   - `Próxima ação` — a ação exata do elo mais grave.
3. Se o checkout do marketplace estiver congelado, explicar isso explicitamente.
4. Se a versão instalada estiver atrás do catálogo local, dizer isso sem drama.
5. Só sugerir `prumo_cowork_update.sh` ou reinstalação do plugin quando o diagnóstico apontar drift real.
6. Quando houver ação do usuário, oferecer alternativas curtas.
7. O semáforo usa os campos que o script já computa (`marketplace_checkout_stale`, `marketplace_checkout_divergence`, `marketplace_last_updated`, versão instalada) — o doctor é a fonte de verdade do elo "checkout do marketplace" e do "M dias parada" (`lastUpdated`); a distância de versão do workspace é do briefing (`version_status`). Ver `version-update.md` → fonte de verdade por elo.

## Cuidados

- Só dizer que tem bug no plugin depois de olhar o store real do Cowork.
- “Reinicia e torce” não é diagnóstico — encontrar o problema de verdade.
- Não editar o cache do Cowork por conta própria.
- Se não achar o store, dizer isso claramente.
