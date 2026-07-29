# Escrita em arquivo curado

> Carregue este arquivo antes de **substituir integralmente** um arquivo que já
> existe no workspace. O gatilho está na regra 6 do core.

## O que é arquivo curado

Conteúdo que o usuário escreveu e que o produto **não sabe recriar**:

- `Prumo/`: `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md`
- `Prumo/Agente/`: `PERFIL.md`, `PESSOAS.md`, `ROTINA.md`, `SAUDE.md`, `INFRA.md`, `PROJETOS.md`, `RELACOES.md`, `MAPA-AUTORAL.md`
- `Prumo/Referencias/`: `INDICE.md`, `WORKFLOWS.md`, `EMAIL-CURADORIA.md` e **as fichas**

Com runtime, a mesma lista vive em `WorkspacePaths.curated_relative_paths()`.

## A regra

**Acrescentar é a operação sancionada. Reescrever o arquivo inteiro é exceção.**

Em 27/07 uma sessão quis acrescentar quatro linhas ao `INDICE.md` e usou escrita
integral com apenas as linhas novas. O arquivo passou de 48 entradas para 5, e
o dano ficou invisível por dois dias — markdown com quatro linhas de tabela é
markdown legítimo. As descrições eram autorais, de cinco meses, e só
sobreviveram porque outra operação as tinha copiado vinte minutos antes.

Então:

1. **Para acrescentar, acrescente.** Use edição pontual, nunca escrita do
   arquivo inteiro. Não é necessário ler o arquivo todo pra isso — no
   `INDICE.md`, a alocação de ID lê só a última linha (contrato da #244, em
   `ficha-de-fonte.md`, que **continua valendo**).
2. **Para reescrever tudo, leia tudo antes.** Reescrita integral só depois de
   ler a versão atual inteira **na mesma sessão**, e só quando a operação exige
   mesmo — o caso real é o reagrupamento por tema da faxina.
3. **No `INDICE.md`, reescrita integral acontece sob o lock.** Adquirir o lock
   do escopo (`multiagent.md` → "Escopo com aquisição atômica"), ler inteiro,
   reagrupar **preservando todas as linhas, IDs e descrições**, escrever,
   liberar. O lock fica adquirido durante a janela inteira: ler e escrever em
   momentos diferentes sem lock reabre a corrida que a #244 fechou.
4. **Na dúvida, não reescreva.** Estado que você não entende vira conversa com
   o usuário, não escrita.

## O que este contrato NÃO é

Não é trava mecânica. O Prumo não tem gancho na ferramenta de escrita do agente
hospedeiro — nenhum texto aqui impede uma escrita. O que existe de mecânico é
outra coisa, e vale conhecer:

- **Cópia**: o `prumo seed` e o `prumo briefing` fotografam os curados em
  `.prumo/backups/curated/` e avisam quando algum encolhe (#262). Onde há
  runtime, dano recente é recuperável.
- **Detecção**: a faxina bloqueia o reparo automático do índice quando o estado
  é suspeito, em vez de "consertar" por cima (#261).

Esta regra é a camada que funciona em qualquer host — inclusive onde as outras
duas não rodam.
