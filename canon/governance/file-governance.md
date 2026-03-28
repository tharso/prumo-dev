# Governanca de Arquivos Vivos

Data de extracao: 2026-03-28

Este arquivo define a jurisdicao dos arquivos vivos do Prumo no workspace do usuario. O problema nunca foi "arquivo baguncado". O problema sempre foi deixar especies diferentes de informacao dividindo a mesma gaiola.

## Principio

Cada arquivo vivo existe para um tipo de informacao. Quando a fronteira borra, o sistema fica:

1. mais lento;
2. mais confuso;
3. mais covarde;
4. mais tentado a fingir memoria onde so ha entulho.

## Contrato por arquivo

### `AGENT.md`

Mora aqui:

1. mapa canonico do workspace;
2. identidade rapida;
3. ordem de leitura;
4. regras de entrada e acesso ao motor.

Nao mora aqui:

1. pendencia datada;
2. historico resolvido;
3. changelog de uso;
4. status transitório do dia.

### `PAUTA.md`

Mora aqui:

1. pendencia viva;
2. acao aberta;
3. item com prazo;
4. lembrete que ainda pede resposta ou decisao.

### `INBOX.md`

Mora aqui:

1. captura ainda nao processada;
2. item bruto;
3. material que ainda nao foi roteado para pauta, referencia ou registro.

### `REGISTRO.md`

Mora aqui:

1. decisao tomada;
2. item concluido;
3. mudanca aplicada;
4. observacao factual com valor de trilha.

### Contexto modular (`Agente/*.md`)

Mora aqui:

1. contexto estavel que muda comportamento do agente;
2. informacao duravel por dominio;
3. memoria pessoal ou operacional que nao e pendencia nem historico do dia.

### `PRUMO-CORE.md`

Mora aqui:

1. regras do motor expostas ao workspace;
2. guardrails estaveis do sistema;
3. referencias para modulos canonicos.

Nao mora aqui:

1. nota operacional do dia;
2. pendencia do usuario;
3. workaround de host.

## Sinais de drift

Os sinais abaixo indicam conteudo no arquivo errado:

1. data vencida em arquivo de contexto estavel;
2. item resolvido ainda tratado como pendencia;
3. historico brigando com configuracao viva;
4. mesma regra ou fato repetido em dois arquivos sem motivo;
5. inbox que ja esta roteado mas continua bruto;
6. bloco inteiro que so faz sentido como registro ou pauta.

## Politica de acao

### Mudanca automatica permitida

So quando a operacao for estruturalmente segura:

1. duplicacao literal;
2. redundancia obvia;
3. regeneracao de indice ou rodape;
4. arquivo derivado recriavel.

### Mudanca automatica proibida

Nao mover silenciosamente quando houver:

1. decisao semantica de destino;
2. verdade factual a confirmar;
3. possivel perda de contexto;
4. risco de apagar o rastro do usuario.

## Linguagem do diagnostico

O sistema deve falar em termos de jurisdicao, nao so de limpeza:

1. "isso parece pendencia viva";
2. "isso parece registro resolvido";
3. "isso parece contexto estavel";
4. "isso parece conteudo no arquivo errado".

Diagnostico sem destino e so fofoca com interface.
