# Load Policy

Data de extracao: 2026-03-28

Esta e a politica canonica de hidratacao de contexto do Prumo. Ler tudo sempre e tao inteligente quanto despejar o armario inteiro no chao para procurar uma meia.

## Principios

1. ler primeiro o minimo necessario para decidir;
2. preferir resumo incremental quando existir;
3. abrir conteudo pesado apenas quando houver necessidade objetiva de acao.

## Camadas

### Base

Ler sempre:

1. `AGENT.md`
2. `PAUTA.md`
3. `INBOX.md`
4. `PRUMO-CORE.md`

### Leve

Preferir quando disponivel:

1. previews e indices de inbox;
2. resumos de handover ou equivalentes de desenvolvimento, quando o fluxo pedir;
3. snapshots estruturados;
4. indices tematicos e catalogos.

### Profunda

Abrir sob demanda:

1. arquivos brutos longos;
2. transcricoes extensas;
3. anexos e binarios;
4. historicos completos.

## Heuristica de aprofundamento

Abrir bruto imediatamente se qualquer condicao for verdadeira:

1. risco legal, financeiro ou documental;
2. vencimento em ate 72h;
3. item `P1`;
4. ambiguidade que impeca acao segura.

## Proibicoes uteis

1. nao abrir arquivo bruto so por curiosidade;
2. nao pular direto para profundidade se um resumo ja responde a decisao;
3. nao fingir que preview e contexto completo sao a mesma coisa.
