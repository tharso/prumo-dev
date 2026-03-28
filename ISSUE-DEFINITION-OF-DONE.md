# Definition of Done por tipo de issue

Este arquivo existe para matar um hábito caro: chamar de "feito" o que ainda está pela metade só porque cansou de olhar para a própria cara no espelho.

## Regra geral

Uma issue só fecha quando:

1. o estado final está versionado no GitHub;
2. a fonte de verdade mudou de fato (código, contrato, doc ou issue comment canônico);
3. o critério de aceite dela foi atendido ou explicitamente supersedido;
4. o que restar foi empurrado para outra issue com dono claro.

Fechar por alívio emocional não conta como entrega.

## 1. Feature

Fecha quando:

1. o comportamento existe de verdade;
2. a rota de uso ou de integração está documentada;
3. testes ou validação compatíveis com o risco foram executados, ou a ausência deles foi registrada;
4. rollback, guardrails ou limitações relevantes ficaram explícitos;
5. changelog foi atualizado se houve mudança perceptível de comportamento.

Nao fecha quando:

1. existe só spec;
2. a UX ainda depende de telepatia do host;
3. o código entrou, mas o contrato ficou oral.

## 2. Bug

Fecha quando:

1. a causa provável foi identificada;
2. a correção entrou;
3. há evidência de que o sintoma foi neutralizado;
4. o risco de regressão foi coberto por teste, smoke ou nota explícita.

Nao fecha quando:

1. o sintoma sumiu uma vez e virou fé;
2. trocamos de erro e chamamos isso de progresso;
3. a causa continua desconhecida e a issue só ganhou silêncio.

## 3. Dívida técnica

Fecha quando:

1. a ambiguidade, duplicação ou acoplamento caiu materialmente;
2. a fonte de autoridade ficou mais clara do que estava antes;
3. o diff reduziu complexidade real, não só mudou móveis de lugar;
4. a nova forma está documentada o bastante para não depender de memória tribal.

Nao fecha quando:

1. só houve renome bonito;
2. o problema mudou de pasta e continuou vivo;
3. a limpeza deixou mais arqueologia do que antes.

## 4. Arquitetura / ADR

Fecha quando:

1. a decisão foi registrada em artefato rastreável;
2. escopo, não-escopo, tradeoff e consequência estão explícitos;
3. o backlog ou a execução foram realinhados com a decisão;
4. deixou de existir dúvida estrutural que impeça seguir construindo.

Nao fecha quando:

1. o texto só descreve desejo;
2. a arquitetura "aprova" algo sem mudar a ordem da obra;
3. a decisão ainda permite duas leituras incompatíveis.

## 5. Validação

Fecha quando:

1. houve evidência suficiente de `APPROVED` ou `REJECTED`;
2. a validação produziu consequência clara:
   - fechar issue origem;
   - abrir regressão;
   - registrar limitação;
   - ou matar uma premissa ruim.

Nao fecha quando:

1. ficou só em "parece bom";
2. não há evidência mínima;
3. a issue continua aberta depois de o contexto morrer.

## 6. Issue supersedida

Fecha quando:

1. a trilha nova está indicada;
2. ficou explícito por que o escopo antigo perdeu sentido;
3. o histórico útil foi preservado em comentário ou referência.

Issue velha não é patrimônio histórico. É ruído, a menos que alguém diga por que ela ainda respira.
