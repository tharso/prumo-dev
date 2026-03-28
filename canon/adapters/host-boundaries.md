# Fronteiras de Adapter

Data de extracao: 2026-03-28

Este arquivo separa o que e regra de produto do que e detalhe de host. Sem essa linha, o legado do Cowork continua infiltrando cano no predio inteiro.

## Fica no canon compartilhado

1. contrato de invocacao;
2. disciplina de interface;
3. governanca documental;
4. load policy;
5. orquestracao de briefing;
6. inbox processing;
7. comportamento de produto diante de erro e estado parcial.

## Fica em adapter ou doc operacional

1. bridge do Cowork para shell/runtime;
2. manutencao especifica de plugin;
3. runtime paths historicos;
4. marketplace e manifestos;
5. permissao local e detalhes de integracao opcional por app;
6. affordance visual e politica de autonomia de cada host;
7. detalhes de transporte seguro de update.

## Caso especial: update de versao

Ha duas camadas aqui:

### Comportamento de produto

Fica no canon:

1. checar antes do panorama;
2. avisar diferenca de versao;
3. oferecer alternativas curtas;
4. nao sequestrar o briefing por causa do updater.

### Mecanismo de transporte

Fica fora do canon:

1. qual script aplica update;
2. que allowlist de escrita existe;
3. que bridge o Cowork usa;
4. que fallback de shell ou bundle entra em cena.

## Caso especial: higiene

### Geral

Fica no canon:

1. diferenca entre limpeza segura, delegacao otimista e limpeza assistida;
2. sinais de drift;
3. exigencia de trilha e prudencia.

### Arquivo ou host especifico

Fica fora do canon:

1. `CLAUDE.md` como caso legacy especifico;
2. scripts e paths de higiene do plugin;
3. qualquer regra que so exista por causa de um wrapper.

## Regra de bolso

Se a pergunta for "isso continua valendo quando Cowork sumir da sala?", a resposta decide metade do trabalho.

Se sim, tende a ser canon.
Se nao, tende a ser adapter.
