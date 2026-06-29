# Escrita no Calendário

> **module_version: 1.0.0**
>
> Contrato canônico de quando e como o Prumo **cria** um evento de calendário a partir de um ritual com hora. Por padrão o Prumo só **lê** o calendário; ações sobre eventos que já existem (RSVP, remarcar) vivem na `decidir`. A **criação** de evento é a escrita deste contrato — e é sempre **oferecida**, nunca silenciosa.

## Princípio

O Prumo nunca escreve no calendário do usuário sem aprovação explícita. Criar evento existe para um caso só: transformar um **ritual com hora marcada** em uma **série recorrente** na agenda, tirando-o do `PERFIL.md`/`ROTINA.md`. A agenda passa a ser o estado vivo do ritual (recorrência, "passou", deletar a série) — o Prumo lê de lá.

## Quando oferecer

Onde um ritual **com hora** é identificado:

- no **onboarding** (`prumo/SKILL.md`);
- na **migração assistida** (`claude-hygiene.md`, ritual legado da seção "Lembretes recorrentes" do PERFIL);
- quando o usuário **menciona um novo ritual com hora** no chat ou no briefing.

Sempre **oferecer**, nunca criar sozinho. Com vários de uma vez, oferecer **em lote**: "Crio esses 3 na agenda? `a) sim / b) escolher quais / c) não`". Criar evento sem terceiros é ação nova mas de baixo risco — uma confirmação cobre. (Eventos **com** terceiros seguem o contrato de confirmação do `decidir`.)

## Idempotência — não duplicar entre hosts

Antes de oferecer criar, checar em **dois** lugares:

1. **`REGISTRO.md`** — existe a linha de migração deste ritual (Origem=`ritual`, Resumo=`<nome do ritual>`, Ação=`migrado para agenda`, Destino=`calendário` — o formato gravado no passo "Ao criar")? Se sim, já foi migrado; não oferecer de novo.
2. **Calendário** — já há um evento equivalente? Comparar por **título normalizado** (minúsculas, sem acento) **+ dias da semana + horário de início**, no calendário e fuso do usuário. Equivalência aproximada conta (ex.: "Ginástica" ≅ "ginástica" ter/qui 18h se dias e horário batem) — na dúvida, **perguntar antes de criar**, nunca duplicar no escuro.

A dupla checagem cobre o caso sequencial (o comum, incluindo a troca de host). O caso raro de **dois hosts criando no mesmo instante** sobra como race residual aceitável e documentado — não vale um lock só para isso.

## Ao criar (com aprovação)

1. Criar uma **série recorrente** — não eventos soltos: título do ritual + recorrência (ex.: "ter/qui 18h"), via a capacidade de criação de evento do **Calendar MCP do host**.
2. **Registrar o tombstone** no `REGISTRO.md`: `| DD/MM | ritual | <nome do ritual> | migrado para agenda | calendário |`.
3. **Remover o ritual** do `PERFIL.md`/`ROTINA.md` — exclusividade: agora mora só na agenda. A remoção está coberta pela aprovação única da criação, mas **antes de editar** fazer backup conforme `file-protection-rules.md` (PERFIL e os módulos do `Agente/` não são sobrescritos no escuro). O tombstone do passo 2 é o rastro da migração.

## Sem escrita disponível (Calendar MCP read-only ou ausente)

Não inventar e não mascarar. **Orientar** o usuário a criar o evento à mão, com os detalhes prontos para colar (título, dias, horário, recorrência). Manter o ritual no `ROTINA.md` como contexto **até** haver escrita disponível — quando houver, migrar (criar + tombstone + remover do ROTINA).

Enquanto **não** virou evento, ficar no `ROTINA.md` **não** fere a exclusividade: ela vale para o ritual que já é evento. O ROTINA é a casa de espera; a agenda é o destino.

## Guardrails

1. Nunca criar sem aprovação explícita do usuário.
2. Nunca criar sem checar a idempotência (REGISTRO + calendário).
3. Série recorrente, nunca N eventos soltos.
4. Sempre registrar o tombstone no `REGISTRO.md` ao criar (rastro da migração — regra 6 do core).
5. Sem capacidade de escrita: orientar, nunca silenciar.
