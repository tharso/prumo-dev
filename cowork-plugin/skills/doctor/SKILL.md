---
name: doctor
description: >
  Diagnóstico do runtime do Prumo no Cowork. Inspeciona store local, checkout
  do marketplace, versão instalada e drift de catálogo. Use com /doctor.
---

# Doctor do Runtime (Prumo)

Você está executando o comando `/doctor`.

Isto não é setup nem sanitização.
É diagnóstico do runtime do Prumo no Cowork.

## Carregamento obrigatório

1. Leia `PRUMO-CORE.md` se existir no workspace.
2. Leia:
   - `Prumo/cowork-plugin/skills/prumo/references/modules/cowork-runtime-maintenance.md`
   - `Prumo/cowork-plugin/skills/prumo/references/modules/runtime-paths.md`

## Fluxo

1. Rodar `prumo_cowork_doctor.sh` resolvendo scripts pela ordem definida em `runtime-paths.md`.
2. Responder em 4 blocos curtos numerados continuamente:
   - `Runtime`
   - `Marketplace`
   - `Plugin`
   - `Próxima ação`
3. Se o checkout do marketplace estiver congelado, explicar isso explicitamente.
4. Se a versão instalada estiver atrás do catálogo local, dizer isso sem drama.
5. Só sugerir `prumo_cowork_update.sh` ou reinstalação do plugin quando o diagnóstico apontar drift real.
6. Quando houver ação do usuário, oferecer alternativas curtas.

## Guardrails

- Não inferir bug do plugin sem olhar o store real do Cowork.
- Não mandar o usuário “reiniciar e torcer” como se isso fosse diagnóstico.
- Não editar o cache do Cowork por conta própria a partir deste comando.
- Se o store do Cowork não puder ser localizado, dizer isso claramente.
