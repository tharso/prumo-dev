# Canon do Produto

Esta pasta guarda a inteligencia compartilhada do Prumo que:

1. vale para mais de um host;
2. nao deve depender do `cowork-plugin/`;
3. tambem nao deve ficar sequestrada dentro do runtime;
4. merece uma casa menos improvisada do que README, wrapper e playbook.

## O que entra aqui

1. contratos de invocacao e interface;
2. orquestracao compartilhada de fluxos centrais;
3. governanca documental e politica de leitura;
4. procedimentos de produto que ainda nao sao detalhe de host.

## O que nao entra aqui

1. estado vivo do usuario;
2. handovers de desenvolvimento;
3. notes especificas de host;
4. shell paths e workarounds de distribuicao;
5. qualquer regra que exista so por causa de Cowork, Antigravity ou outro adapter.

## Estrutura

```text
canon/
  contracts/
  orchestration/
  governance/
  operations/
  adapters/
```

## Relacao com o resto do repo

1. `runtime/` implementa capacidades e consome este canon;
2. `cowork-plugin/` pode continuar distribuindo e adaptando, mas nao e mais a casa principal da inteligencia compartilhada;
3. docs de topo podem explicar, mas nao devem competir com os arquivos daqui.

Se o produto voltar a espalhar a mesma regra entre plugin, runtime, wrapper e manifesto, esta pasta vira museu. E museu e bonito. So nao costuma dirigir produto.
