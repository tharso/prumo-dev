# Exemplos de cards — o que separa um card útil de um inútil

Calibragem de qualidade, não template literal. Os IDs reusam a numeração do panorama do briefing.

## Card de despacho — BOM

```js
{
  id: '7', sec: 'emails', type: 'despacho',
  badges: [{label:'P1', tone:'red'}],
  link: { label: 'thread', href: '...' },
  title: 'Acme pede retorno sobre o orçamento até hoje',
  contexto: 'Thread aberta ontem 18h. <span class="ref">de: ana@acme.com</span> Pergunta se o prazo de entrega muda com o escopo novo. <span class="q">"conseguimos manter a entrega no dia 30?"</span>',
  actions: [
    { key:'reply',    label:'Responder', tone:'green', effect:'draft_reply',      requires:'o que responder' },
    { key:'snooze',   label:'Adiar',     tone:'amber', effect:'snooze',           requires:'até quando' },
    { key:'delegate', label:'Delegar',   tone:'blue',  effect:'draft_delegation', requires:'destinatário' },
    { key:'archive',  label:'Arquivar',  tone:'slate', effect:'archive' },
  ],
  sugestao: 'Confirmar prazo mantido e propor call de 15min se o escopo crescer.'
}
```

Por que funciona: o contexto traz **evidência citável** (remetente, trecho literal), as ações vêm da allowlist do tipo "email que pede resposta", cada uma com `effect` e `requires` corretos (`Delegar` exige destinatário), e a sugestão é executável. O usuário decide em segundos.

## Card de despacho — RUIM

```js
{
  id: '7', type: 'despacho',
  title: 'Email do cliente',
  contexto: 'Tem um email do cliente que talvez precise de atenção.',
  actions: [
    { key:'reply', label:'Responder', tone:'green' },
    { key:'maybe', label:'Talvez depois', tone:'slate' },
  ]
}
```

Por que falha: contexto sem evidência (qual cliente? o que pede? cite), ação inventada fora da allowlist (`Talvez depois` não é despacho — é procrastinação com nome bonito), ações sem `effect` (o Prumo não sabe o que executar). O usuário não tem como dar um despacho informado.

## Card de escolha — BOM

```js
{
  id: '9', sec: 'decisoes', type: 'escolha',
  title: 'Foco principal de hoje',
  contexto: 'Três frentes competem. Escolha uma — o resto vira pano de fundo.',
  options: [
    { key:'A', rec:true, label:'Fechar a proposta da Acme',
      desc:'Destrava receita e o email P1 acima (item 7).', effect:'focus_acme' },
    { key:'B', label:'Avançar o artigo sobre pricing',
      desc:'Trabalho profundo, mas sem prazo hoje.', effect:'focus_artigo' },
    { key:'C', label:'Limpar a inbox inteira',
      desc:'Sensação de controle, baixo impacto real.', effect:'focus_inbox' },
  ]
}
```

Por que funciona: as opções têm **texto final** (escolher = decidir), cada `desc` explica o trade-off real (inclusive amarrando ao item 7), há uma recomendação marcada, e cada opção traz `effect` para o Prumo agir sobre a escolha. Recomendar é parte do trabalho — ficar em cima do muro terceiriza a decisão de volta pro usuário.

## Card de escolha — RUIM

```js
{
  id: '9', type: 'escolha',
  title: 'O que fazer hoje',
  options: [
    { key:'A', label:'Trabalhar', desc:'Focar no trabalho.' },
    { key:'B', label:'Organizar', desc:'Organizar as coisas.' },
  ]
}
```

Por que falha: opções vagas que descrevem categorias em vez de conter a decisão. O usuário escolhe "A" e nada fica resolvido — você ainda vai ter que perguntar "trabalhar em quê?". A rodada perdeu o propósito.

## Padrões que elevam o despacho

- **Agrupe o barato, separe o caro.** Cinco emails informativos com a mesma cara podem virar cards curtos; uma cobrança que vira atrito merece card próprio com contexto.
- **Evidência no contexto.** Remetente, trecho literal (`.q`), referência (`.ref`), prazo. Despacho sem evidência vira chute.
- **Só ofereça ações que cabem.** `Delegar` sem destinatário, `Confirmar` num evento sem RSVP — botão de neblina. Tire da lista do card.
- **Reuse o número do panorama.** O item `12` do chat é o card `id: '12'`. O usuário responde no número que viu.
- **Marque o que tem risco.** Ações de remoção (`archive`/`discard` de inbox, `discard` de pendência) usam `tone:'red'` e `requires` de motivo — e ao executar, confirmam antes (ASSERT do core).
