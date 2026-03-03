# Prumo

Prumo e um plugin de organizacao pessoal orientado a acao.

Objetivo: transformar entrada difusa em decisao clara e proximo passo executavel.

## Instalacao

### Opcao 1 (recomendada): marketplace por URL

Use a URL:

`https://raw.githubusercontent.com/tharso/prumo/main/marketplace.json`

Opcao alternativa (repositorio Git):

`https://github.com/tharso/prumo.git`

### Opcao 2: upload local (.zip)

Use o pacote local gerado para instalacao offline/manual.

## Comandos principais

- `/prumo:setup` (setup/menu do sistema)
- `/prumo:prumo` (alias legado de setup)
- `/prumo:briefing`
- `/prumo:handover`
- `/prumo:sanitize`
- `/prumo:start`

## Estrutura publica do repositorio

- `marketplace.json` e `plugin.json`: manifests publicos.
- `cowork-plugin/`: pacote de runtime consumido pelo marketplace.
- `CHANGELOG.md`: historico publico de mudancas.
- `VERSION`: versao publica atual.

## Politica de update

- Atualizacoes do pacote do plugin dependem do canal de distribuicao (marketplace ou reinstall do pacote local).
- Atualizacao do motor operacional no workspace do usuario segue o fluxo de versao descrito pelas skills do proprio plugin.

## Diagnostico rapido

Se aparecer "comando desconhecido" apos instalar/atualizar, siga o protocolo de 60 segundos:

- `COWORK-MARKETPLACE-PLAYBOOK.md` (secao "Protocolo de 60 segundos")

## Versao

Versao atual: `4.1.0`.
