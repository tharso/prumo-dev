# Version Update

> **module_version: 4.5.0**
>
> Fonte canônica do fluxo de verificação e aplicação de atualização do Prumo.

## Objetivo

Separar claramente:

1. detectar que existe versão nova;
2. verificar se há transporte seguro de aplicação;
3. aplicar update apenas quando isso for seguro.

## Passo 1: descobrir a versão local

1. Ler `prumo_version` no topo do `PRUMO-CORE.md`.
2. Ler `VERSION` do repositório quando existir no runtime.
3. Se `VERSION` e `prumo_version` divergirem, tratar como falha de release.

## Passo 2: comparar com a versão remota

Fonte remota permitida para comparação:

- `https://raw.githubusercontent.com/tharso/prumo/main/VERSION`

Regra dura:

- Nunca use WebFetch, preview remoto, leitor inteligente ou resumo interpretado para reescrever `PRUMO-CORE.md`.

## Passo 3: descobrir transporte seguro de aplicação

Transportes válidos:

1. fonte local bruta no workspace:
   - `Prumo/VERSION`
   - `Prumo/cowork-plugin/skills/prumo/references/prumo-core.md`
   - `Prumo/skills/prumo/references/prumo-core.md`
2. updater via shell:
   - nome oficial: `safe_core_update.sh`
   - paths válidos definidos em `runtime-paths.md`

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

## Passo 5: aplicação segura

### Se houver fonte local válida

1. criar backup em `_backup/PRUMO-CORE.md.YYYY-MM-DD-HHMMSS`;
2. substituir somente `PRUMO-CORE.md`;
3. reler o core atualizado;
4. confirmar que a nova `prumo_version` é a esperada.

### Se houver updater via shell

1. executar o updater seguro;
2. reler o core;
3. validar a versão final.

## Allowlist de escrita

Durante atualização, os únicos destinos permitidos são:

1. `PRUMO-CORE.md`
2. `_backup/PRUMO-CORE.md.*`

Qualquer tentativa de tocar `CLAUDE.md`, `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`, `AGENTS.md` ou arquivos de áreas do usuário deve abortar o update.
