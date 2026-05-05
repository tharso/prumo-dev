# Version Update

> **module_version: 4.21.0**
>
> Fonte canônica do fluxo de verificação e aplicação de atualização do Prumo.

## Objetivo

Separar claramente:

1. detectar que existe versão nova;
2. verificar se há transporte seguro de aplicação;
3. aplicar update apenas quando isso for seguro.

No briefing, esta checagem não é opcional.
Ela deve acontecer como preflight antes do panorama principal.

## Passo 1: descobrir a versão local

1. Ler `prumo_version` no topo do `.prumo/system/PRUMO-CORE.md`.
2. Ler `VERSION` do repositório quando existir no runtime.
3. Se `VERSION` do repo local for maior que `prumo_version` do workspace, tratar como motor do workspace defasado.
4. Se `prumo_version` do workspace for maior que `VERSION` do repo local, tratar como inconsistência de ambiente e avisar isso explicitamente.
5. Só tratar como falha de release quando houver conflito impossível de explicar por drift normal de workspace.

## Passo 2: comparar com a versão remota

Fonte remota permitida para comparação:

- `https://raw.githubusercontent.com/tharso/prumo/main/VERSION`

Regra dura:

- Nunca use WebFetch, preview remoto, leitor inteligente ou resumo interpretado para reescrever `.prumo/system/PRUMO-CORE.md`.

## Passo 3: descobrir transporte seguro de aplicação

Transportes válidos:

1. fonte local bruta no workspace:
   - `Prumo/VERSION`
   - `skills/prumo/references/prumo-core.md`
   - `.prumo/skills/prumo/references/prumo-core.md`
2. updater via runtime: `prumo` CLI quando disponível (instalação pip, caminho preferido).

Sem transporte seguro de aplicação:

- informar a limitação;
- não bloquear o briefing;
- orientar atualização/reinstalação do plugin ou uso de ambiente com shell/repo local.

## Passo 4: aviso ao usuário

Se houver versão nova e transporte seguro:

1. parar antes do briefing;
2. avisar a diferença `v[local] -> v[remota]`;
3. dizer que a atualização toca apenas o motor;
4. se não houver changelog local seguro, falar apenas "nova versão do motor";
5. esperar decisão do usuário.

Quando o gatilho for o briefing, oferecer alternativas curtas:

- `a) atualizar agora`
- `b) seguir mesmo assim`
- `c) ver diagnóstico`

Se houver versão nova, mas não houver transporte seguro:

1. avisar isso explicitamente;
2. oferecer `b)` e `c)` do mesmo jeito;
3. não sequestrar o briefing por causa do updater.

Se o caso for `workspace core defasado`:

1. dizer isso com nome e sobrenome;
2. mencionar a diferença entre `.prumo/system/PRUMO-CORE.md` do workspace e `Prumo/VERSION` local;
3. tratar isso como condição operacional esperável, não como release corrompida;
4. no briefing, parar antes do panorama e pedir decisão do usuário.

## Passo 5: aplicação segura

### Se houver fonte local válida

1. criar backup em `.prumo/backups/version-update/<YYYYMMDDTHHMMSS>/PRUMO-CORE.md`;
2. substituir somente `.prumo/system/PRUMO-CORE.md`;
3. reler o core atualizado;
4. confirmar que a nova `prumo_version` é a esperada.

### Se houver runtime instalado

1. executar `prumo` com o subcomando de update quando existir;
2. reler o core;
3. validar a versão final.

## Allowlist de escrita

Durante atualização, os únicos destinos permitidos são:

1. `.prumo/system/PRUMO-CORE.md`
2. `.prumo/backups/<scope>/<timestamp>/...` (qualquer subdiretório de scope dentro de `backups/`)

Qualquer tentativa de tocar `Prumo/Agente/PERFIL.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`, `AGENT.md` ou arquivos de áreas do usuário deve abortar o update.
