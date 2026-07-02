# Ficha de fonte

> **module_version: 1.0.0**
>
> Template canônico da ficha de catalogação de conteúdo — fontes de terceiros
> (artigo, vídeo, livro, podcast, post) e textos do próprio usuário.
> Consumida pelo fluxo de inbox (`modules/inbox-processing.md`, seção
> "Material de referência"), indexada pela `faxina` e enumerada pelo `acervo`.

## Princípio: catalogar, não armazenar

A ficha aponta pra onde o conteúdo mora — o Prumo é o fichário, não o depósito.
As estantes ficam onde o usuário preferir (vault do Obsidian, Google Docs, URL,
arquivo local). Copiar conteúdo externo pro workspace só com pedido explícito.
Uma ficha = um arquivo em `Prumo/Referencias/`.

## Template

```markdown
# [Título da fonte]

- **Tipo:** artigo | vídeo | livro | podcast | post | texto próprio
- **Autor:** [quem fez — "eu" para conteúdo próprio]
- **Onde mora:** [URL, caminho externo ou arquivo em Referencias/]
- **Por que guardei:** [obrigatório — motivo real, não "parece útil"]
- **Entrada:** DD/MM/AAAA
- **Keywords:** kw1, kw2, kw3

## Pontos-chave

- [3 a 5 pontos que valem a releitura — o suficiente pra decidir se vale voltar à fonte]

## Conexões

- [[outra ficha ou ideia]] — por que conversa com esta
```

## Exemplo preenchido

```markdown
# Atomic Habits — o argumento do ambiente

- **Tipo:** livro
- **Autor:** James Clear
- **Onde mora:** notas em [vault]/Livros/Atomic Habits.md (livro físico na estante)
- **Por que guardei:** base pro redesenho da rotina matinal — o capítulo de ambiente muda como eu organizo meus espaços
- **Entrada:** 02/07/2026
- **Keywords:** hábitos, ambiente, gatilhos

## Pontos-chave

- Mudar o ambiente remove a decisão: o gatilho ambiental vence a força de vontade.
- Hábito novo cola melhor empilhado num existente (habit stacking).
- Fricção mínima pro hábito bom, fricção máxima pro ruim.

## Conexões

- [[Sistemas batem disciplina quando o gatilho é ambiental]] — a ideia destilada que nasceu desta leitura
```

## Regras

1. **"Por que guardei" é obrigatório** (`keep_with_reason`, #109/#110): sem
   motivo, não vira ficha. Se o porquê não for inferível do contexto, o agente
   pergunta — uma pergunta curta. Guardar sem motivo é entulho, não acervo.
2. **A ficha é sempre oferta.** O agente propõe a catalogação; nunca cria no
   escuro (regra 16 do core: estrutura nasce de demanda).
3. **Conexões usam `[[wikilink]]`** (decisão do dono, 2026-07-02) — conveniência
   de editor: quem abre a pasta no Obsidian ganha grafo e backlinks. **Nenhum
   fluxo do Prumo depende dos wikilinks**: eles degradam como texto entre
   colchetes em qualquer editor, e a busca do agente é por significado, com ou
   sem link. Prosa ("Veja também: X") é fallback válido.
4. **Indexação (faxina):** a ficha vira linha no `Referencias/INDICE.md` com o
   mapeamento — Título = cabeçalho da ficha; Arquivo = nome do arquivo; Data =
   campo Entrada; Descrição = "Por que guardei" (resumido); Keywords = campo
   Keywords.
5. **Arquivos operacionais nunca viram ficha** nem entram no índice:
   `INDICE.md`, `WORKFLOWS.md`, `EMAIL-CURADORIA.md` são infraestrutura de
   `Referencias/`, não referência catalogável (mesma lista de exclusão do
   `acervo` e do runtime).
6. **Acervo e a ficha-ponteiro:** "excluir" no acervo arquiva **a ficha**
   (quarentena em `Prumo/Arquivo/Acervo/`, fluxo normal) e **nunca toca o
   conteúdo externo** apontado — o Prumo cataloga, não é dono das estantes.
