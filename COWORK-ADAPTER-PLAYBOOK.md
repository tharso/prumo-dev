# Playbook Operacional: Adapter Cowork

Este documento existe para impedir um autoengano particularmente sedutor: achar que, porque o `Cowork` consegue rodar `prumo` quando você dita a linha inteira, então ele já entendeu o Prumo como produto.

Não entendeu.

## 1. Estado atual deste host

Hoje, a situação do `Cowork` é esta:

1. como casca fina de shell, ele já provou que consegue executar o runtime;
2. como rota curta/nativa (`Prumo`, `/prumo` ou equivalente), ele continua pouco confiável;
3. o ecossistema plugin-first dele ainda age como mordomo do prédio antigo: aparece antes da porta nova e adora se meter no caminho.

## 1.1. Resultado da validação de campo (2026-03-22)

O teste real no `Cowork` mostrou um retrato bem específico:

1. ao receber `Prumo`, o host não rodou `prumo`;
2. declarou que o binário "não estava disponível", apesar de já haver testes anteriores mostrando `Cowork` executando `prumo` como shell fino;
3. caiu em skill/plugin/fluxo legado;
4. leu arquivos por conta própria;
5. puxou calendário e email por fora do runtime;
6. atualizou `briefing-state.json` sem passar pelo `prumo briefing`.

Conclusão prática:

1. `Cowork` está aprovado como host `shell-thin`;
2. `Cowork` está reprovado, por enquanto, como invocação curta/nativa;
3. `Cowork` continua arriscado quando o plugin/skill registry resolve bancar o protagonista.

## 2. Fontes que importam

1. Base documental da família Claude: [code.claude.com/docs/en/overview](https://code.claude.com/docs/en/overview)
2. Playbook operacional do marketplace/plugin neste projeto: [COWORK-MARKETPLACE-PLAYBOOK.md](/Users/tharsovieira/Documents/DailyLife/Prumo/COWORK-MARKETPLACE-PLAYBOOK.md)

O que isso autoriza assumir:

1. `Cowork` vive perto do ecossistema Claude, mas com superfície operacional própria;
2. store, skill registry e bootstrap de sessão são parte do problema real;
3. testar `Cowork` como se fosse só `Claude Code` com outro figurino é um ótimo jeito de perder tempo com confiança alta.

## 3. O que ele não é

`Cowork` não deve ser tratado como:

1. sinônimo de `Claude Code`;
2. host que merece confiança nativa só porque consegue shell em alguns cenários;
3. plataforma onde plugin antigo, skill atual e runtime local convivem em paz só por decreto.

## 4. Porta canônica

Para `Cowork`, o contrato ideal continua sendo este:

1. `Prumo` -> `prumo`
2. `/prumo` -> bridge para `prumo` ou `prumo start`
3. briefing explícito -> `prumo briefing --workspace . --refresh-snapshot`
4. rota estruturada -> `prumo start --format json`

Mas o teste de campo já mostrou que, hoje, a rota confiável é mais estreita:

1. pedir explicitamente que o host rode `prumo ...` no shell;
2. desconfiar de qualquer fluxo que passe antes pelo plugin/skill registry;
3. tratar a affordance curta como pendência real, não como detalhe cosmético.

## 5. Regras práticas

1. Se o host conseguir shell local, prefira `prumo` ao invés de ressuscitar fluxo legado.
2. Não trate skill/plugin como prova de que a porta curta do runtime está funcionando.
3. Não leia arquivo para simular `briefing` ou `start`.
4. Não escreva `_state/` por conta própria.
5. Se o host disser que `prumo` não existe, isso precisa ser tratado como falha do adapter ou da sessão, não como licença para improvisar produto.

## 6. Checklist de aceite

Status atual do checklist:

1. `Prumo` vira `prumo` -> `NAO`
2. briefing explícito vira `prumo briefing --workspace . --refresh-snapshot` -> `SIM`, quando o usuário dita o comando inteiro
3. `prumo start --format json` volta com estrutura íntegra e o host a respeita -> `SIM`, quando a execução vai pelo shell
4. o host não improvisa briefing fora do runtime -> `NAO`
5. o host não cai em plugin/skill legado quando a porta curta falha -> `NAO`
6. o host funciona como casca fina de shell -> `SIM`

## 7. Próximo passo neste host

1. tratar `Cowork` oficialmente como `shell-thin host` até prova em contrário;
2. manter a rota curta/nativa como pendência aberta;
3. não reabrir romance com plugin-first só porque o host adora trazer flores murchas da sessão anterior.
