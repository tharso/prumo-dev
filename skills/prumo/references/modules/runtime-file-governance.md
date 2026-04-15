# Runtime File Governance

> **module_version: 4.17.0**
>
> Política canônica de ciclo de vida dos arquivos vivos do Prumo.

## Princípio

O problema não é “o usuário esqueceu lixo no arquivo”. O problema é deixar
arquivos de runtime sem jurisdição.

Cada arquivo existe para um tipo de informação. Quando a fronteira borra,
o sistema fica mais lento, mais confuso e mais covarde.

## Contrato por arquivo

### `CLAUDE.md`

Mora aqui:

1. identidade estável do usuário;
2. preferências de tom, linguagem e cobrança;
3. contexto operacional ainda válido hoje;
4. restrições e rotinas recorrentes que mudam o comportamento do agente.

Não mora aqui:

1. pendência datada;
2. item vencido;
3. status transitório velho;
4. changelog de migração;
5. registro de coisa resolvida.

### `PAUTA.md`

Mora aqui:

1. pendência viva;
2. ação aberta;
3. item com prazo;
4. lembrete datado que ainda precisa de resposta ou decisão.

Se tem pergunta do tipo “isso já foi resolvido?”, isso está com cara de
`PAUTA.md`, não de `CLAUDE.md`.

### `REGISTRO.md`

Mora aqui:

1. decisão tomada;
2. item concluído;
3. mudança aplicada;
4. migração encerrada;
5. observação factual com valor de trilha de auditoria.

Se já aconteceu e o sistema só precisa lembrar que aconteceu, é `REGISTRO.md`.

### Histórico / changelog

Mora aqui:

1. marcos do produto ou do setup;
2. legado importante;
3. compatibilidade histórica;
4. notas antigas que ajudam a explicar a evolução do sistema.

Histórico não deve disputar atenção com configuração viva.

## Sinais de drift

Os seguintes sinais indicam que conteúdo pode estar no arquivo errado:

1. data explícita já vencida dentro de `CLAUDE.md`;
2. status transitório com verbo de migração/transferência antigo demais;
3. bloco de histórico/changelog dentro de `CLAUDE.md`;
4. item resolvido permanecendo como se ainda guiasse o comportamento do agente;
5. duplicação de informação estável em duas seções diferentes.

## Política de ação

### Mudança automática permitida

Só quando for estruturalmente segura:

1. duplicação literal;
2. redundância óbvia com heurística conservadora;
3. normalização explícita de rodapé quando o patch for inequívoco.

### Mudança automática proibida

Nunca mover sem confirmação:

1. pendência para `PAUTA.md`;
2. resolvido para `REGISTRO.md`;
3. histórico para changelog;
4. qualquer item que dependa de verdade factual atual.

## Linguagem do diagnóstico

O produto deve falar em termos de governança, não só de limpeza:

1. “isso parece pendência viva”;
2. “isso parece histórico”;
3. “isso parece registro resolvido”;
4. “isso parece conteúdo no arquivo errado”.

Diagnóstico que só diz “achei um achado” é metade do serviço. A outra metade é
dizer para onde o conteúdo deveria ir.
