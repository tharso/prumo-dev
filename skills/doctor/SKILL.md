---
name: doctor
description: >
  Diagnóstico do runtime do Prumo no Cowork. Inspeciona store local, checkout
  do marketplace, versão instalada e drift de catálogo. Use com /doctor.
---

# Doctor do Runtime (Prumo)

Você está rodando o `/doctor`.

Aqui é diagnóstico: checar se o runtime, o marketplace e o plugin estão no lugar certo.

## Carregamento obrigatório

1. Leia `.prumo/system/PRUMO-CORE.md` se existir no workspace.
2. Leia:
   - `skills/prumo/references/modules/cowork-runtime-maintenance.md`
   - `skills/prumo/references/modules/runtime-paths.md`

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

## Cuidados

- Só dizer que tem bug no plugin depois de olhar o store real do Cowork.
- “Reinicia e torce” não é diagnóstico — encontrar o problema de verdade.
- Não editar o cache do Cowork por conta própria.
- Se não achar o store, dizer isso claramente.
