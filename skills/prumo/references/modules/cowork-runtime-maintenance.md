# Cowork Runtime Maintenance

> **module_version: 4.19.0**
>
> Fonte canônica para instalação, diagnóstico e atualização do Prumo no Cowork.

## Instalação recomendada no Cowork

Para o Cowork, o caminho canônico do marketplace é a forma **`owner/repo`** no
formulário da UI:

```text
tharso/prumo
```

O formulário atual **rejeita URL raw** ("Este host não é suportado") — aceita
só `owner/repo` ou URL git de github.com/gitlab/bitbucket (#190). `raw
marketplace.json` sobrevive apenas como debug fora da UI.

## As 5 camadas da propagação (#190)

Do dev até a skill rodando numa sessão do Cowork:

1. **repo dev** (`tharso/prumo-dev`) → 2. **espelho público** (`tharso/prumo`,
   gerado pelo workflow de mirror) → 3. **checkout local do marketplace**
   (`marketplaces/<nome>/` no store) → 4. **plugin instalado no store do host**
   → 5. **registro server-side da conta claude.ai**, que as sessões do Cowork
   materializam em `<sessão>/<id>/rpm/plugin_<id>/` (com um `manifest.json`
   índice em `rpm/` trazendo `updatedAt` por plugin).

A camada 5 é a que a sessão REALMENTE executa — as sessões do Cowork atual
**não leem** o store local. E atenção à store: o Cowork de hoje opera sobre a
**store unificada `~/.claude/plugins`** (a mesma da CLI); `~/.claude/cowork_plugins`
é resquício da era ≤março/2026, morto — o doctor o marca como legado e nunca o
usa como alvo.

## O que o produto deve assumir

1. O botão `Atualizar` da UI do Cowork é sinal fraco, não fonte da verdade.
2. O estado local mora no store unificado:
   - `known_marketplaces.json`
   - `installed_plugins.json`
   - checkout em `marketplaces/<marketplace-name>/`
   E o estado **da conta** mora no registro server-side (camada 5) — visível
   só pelo `rpm/manifest.json` das sessões.
3. Se o checkout do marketplace congelar num commit velho, a UI pode:
   - mostrar versão antiga;
   - deixar `Atualizar` desabilitado;
   - parecer sincronizada sem estar.
4. O congelamento tem **três naturezas** (#145), e a diferença importa:
   - **atrás do remoto**: fast-forward resolve — caso comum;
   - **divergente** (sem ancestral comum — a história do espelho foi
     reescrita): fast-forward **nunca** vai funcionar; o
     `prumo_cowork_update.sh` detecta e recupera com reset seguro do
     checkout **limpo** para o remoto;
   - **commits locais** (ancestral comum existe, mas o checkout tem
     commits próprios): estado anômalo para um cache de espelho — o
     update **não** reseta nem descarta; aborta e explica. O mesmo vale
     para modificação local não-commitada: nada é resetado por cima.
5. Existe um **quarto modo de falha, na camada 5** (#190, incidente real de
   2026-07-15/16): o registro server-side da conta congela num snapshot velho
   (na máquina do incidente: parado desde a reescrita de história do espelho).
   Sintoma: desinstalar+reinstalar pela UI **re-vincula o registro congelado**
   e devolve o mesmo catálogo fóssil — com a descrição do plugin atualizada,
   o que engana. O `prumo_cowork_update.sh` **não alcança** essa camada.
   **Reparo validado:** remover o marketplace INTEIRO na UI → re-adicionar
   como `owner/repo` (identidade nova no servidor força clone fresco) →
   reinstalar o plugin → testar em **sessão nova**. O doctor detecta esse modo
   comparando a versão materializada na sessão com o marketplace e nomeia o
   diagnóstico com o `updatedAt` do registro.

## Scripts canônicos

- `prumo_cowork_doctor.sh`
  Diagnostica store local, checkout do marketplace, versão instalada e drift de catálogo.

- `prumo_cowork_update.sh`
  Atualiza os checkouts do marketplace do Prumo usados pelo Cowork e renova o timestamp de sync. Fast-forward por padrão; quando a história do espelho divergiu e o checkout está limpo, recupera com reset para o remoto (reportando a recuperação). Nunca reseta por cima de modificação local. **Escopo (#190): alcança só a camada 3 (checkouts git locais)** — o cenário dominante do Cowork atual é a store unificada + registro server-side, onde o reparo é o re-add `owner/repo` na UI.

## Política de update

1. Primeiro diagnosticar.
2. Se o checkout do marketplace estiver defasado, atualizar o checkout.
3. Só depois discutir reinstalação do plugin.
4. Não editar `installed_plugins.json` na marra como atalho de produto. Isso é cirurgia no escuro.

## Regra operacional

Se o runtime do Cowork e o catálogo local divergirem, o Prumo deve apontar o drift com nome e sobrenome.
Usuário não deveria precisar discutir com botão cinza para descobrir que o checkout do marketplace está preso no passado.
