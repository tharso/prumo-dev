# Templates dos arquivos auxiliares do Prumo

> Cada seção abaixo é um arquivo separado a ser gerado no workspace do usuário.
> Copiar o conteúdo entre as marcações `--- INÍCIO ---` e `--- FIM ---`.
>
> **Estrutura de workspace v2 (2026-04):** Raiz é território do usuário com ponteiros.
> `Prumo/` contém dados operacionais + skills. `.prumo/` contém infraestrutura do sistema.

---

## Estrutura de workspace

```text
[Workspace]/
├── CLAUDE.md              ← ponteiro → Prumo/AGENT.md
├── AGENT.md               ← ponteiro → Prumo/AGENT.md
├── AGENTS.md              ← ponteiro → Prumo/AGENT.md
├── Prumo/
│   ├── AGENT.md           ← fonte canônica (navegação, fallback, regras)
│   ├── PAUTA.md
│   ├── INBOX.md
│   ├── REGISTRO.md
│   ├── IDEIAS.md
│   ├── Agente/
│   │   ├── INDEX.md       ← índice do contexto modular
│   │   ├── PERFIL.md      ← config pessoal (áreas, tom, lembretes)
│   │   └── PESSOAS.md
│   ├── Referencias/
│   │   ├── INDICE.md
│   │   └── EMAIL-CURADORIA.md  ← regras aprendidas de curadoria de email
│   ├── Inbox4Mobile/
│   │   └── _processed.json
│   └── skills/            ← cópia das skills do repo (portáveis)
└── .prumo/
    ├── state/
    │   ├── agent-lock.json
    │   └── archive/
    │       ├── ARCHIVE-INDEX.json
    │       └── ARCHIVE-INDEX.md
    ├── system/
    │   └── PRUMO-CORE.md  ← motor do sistema (atualizável)
    └── logs/
```

---

## Prumo/PAUTA.md

--- INÍCIO ---

# Pauta

> Estado atual das coisas. Atualizado a cada interação relevante.

## Quente (precisa de atenção agora)

_Nada ainda. Faça seu primeiro dump pra popular._

## Em andamento

_Itens que têm progresso ativo. Formato: `- [Tag] Descrição. Próxima ação: X. (desde DD/MM)`_

## Agendado / Lembretes

_Itens com data específica ou lembretes recorrentes._
_Quando houver agendamento futuro, registrar semântica de cobrança no próprio item:_
_`- **25/02 (Qua)**: [Tag] Item... | cobrar: 25/02`_
_`- **30/03 (Seg) 9h**: [Tag] Item... | cobrar: 28/03`_

{{LEMBRETES_RECORRENTES_LISTA}}

## Horizonte (importante mas não urgente)

_Coisas que precisam acontecer, mas não essa semana._

## Hibernando (existe mas não está ativo)

_Projetos ou tarefas que existem mas não estão recebendo atenção agora._

## Semana atual — Concluídos (DD/MM-DD/MM)

_Itens concluídos nesta semana. Visibilidade do progresso._

## Semana passada — Concluídos (DD/MM-DD/MM)

_Concluídos da semana anterior. Limpo automaticamente na revisão semanal._

---

*Última atualização: {{DATA_SETUP}}*

--- FIM ---

---

## Prumo/INBOX.md

--- INÍCIO ---

# Inbox

> Itens não processados. Tudo que entra passa por aqui antes de ir pro lugar certo.
> Objetivo: este arquivo deve estar VAZIO após cada sessão de processamento.

_Inbox limpo._

--- FIM ---

---

## Prumo/REGISTRO.md

--- INÍCIO ---

# Registro

> Audit trail de todos os itens processados. Permite rastrear "aquele link que entrou semana passada, onde foi parar?"

| Data | Origem | Resumo | Ação | Destino |
|------|--------|--------|------|---------|

--- FIM ---

---

## Prumo/IDEIAS.md

--- INÍCIO ---

# Ideias

> Ideias sem ação imediata. Revisado na revisão semanal.
> Se uma ideia amadureceu e tem próxima ação concreta, migrar para PAUTA.md.

_Nenhuma ideia registrada ainda._

--- FIM ---

---

## Prumo/Agente/PESSOAS.md

--- INÍCIO ---

# Pessoas

> Tracking de pessoas-chave e pendências de relacionamento.
> Atualizado no briefing quando há novidade. Revisado sistematicamente na revisão semanal.

## Pessoas-chave

_Adicione pessoas conforme forem aparecendo nas interações._

| Pessoa | Contexto | Última interação | Pendência |
|--------|----------|------------------|-----------|

## Follow-ups pendentes

_Quem precisa de resposta, retorno, ou atenção._

--- FIM ---

---

## Prumo/Agente/INDEX.md

--- INÍCIO ---

# Índice de contexto

> Porta modular do contexto vivo do usuário.
> Este diretório concentra o que muda comportamento. Não é almoxarifado de entulho narrativo.

## Onde procurar o quê

1. `Prumo/Agente/PERFIL.md`: configuração pessoal (áreas, tom, lembretes)
2. `Prumo/Agente/PESSOAS.md`: pessoas-chave e pendências de relacionamento
3. `Prumo/PAUTA.md`: pendência viva
4. `Prumo/INBOX.md`: captura ainda não processada
5. `Prumo/REGISTRO.md`: trilha do que já aconteceu

--- FIM ---

---

## Prumo/Referencias/INDICE.md

--- INÍCIO ---

# Índice de referências

> Material de referência salvo. Artigos, relatórios, links, PDFs.
> Atualizado sempre que novo material é adicionado.

| # | Título | Arquivo | Data | Descrição | Keywords |
|---|--------|---------|------|-----------|----------|

_Última atualização: {{DATA_SETUP}}_

--- FIM ---

---

## Prumo/Referencias/EMAIL-CURADORIA.md

--- INÍCIO ---

# Curadoria de email — regras aprendidas

> Atualizado pelo agente com feedback do usuário.
> Consultado a cada briefing antes de filtrar emails.
> Viés explícito: na dúvida, trazer. Melhor ruído que perda.

## Setup inicial

Este arquivo está vazio porque a curadoria aprende com o uso. No primeiro briefing com email:

1. **Verificar acesso ao Gmail MCP.** Tentar `gmail_get_profile` pra confirmar que a conta está conectada. Se não estiver, orientar o usuário a configurar o conector de Gmail no Cowork (Settings → Connectors → Gmail) ou no Claude Code (MCP config).
2. **Identificar as contas.** Perguntar ao usuário quantas contas de email ele usa e quais endereços. Entender como chegam na caixa: direto, redirect, fetch ou alias.
3. **Verificar cobertura.** Se o Gmail MCP acessa uma conta principal mas o usuário tem outras, o agente deve guiar a consolidação:
   - Perguntar: "Todas as contas já chegam nessa caixa, ou tem alguma separada?"
   - Se houver contas separadas, pesquisar na web (proativamente, sem esperar o usuário pedir) as instruções atualizadas do Gmail para configurar fetch de outras contas (Gmail → Settings → Accounts → Check mail from other accounts) ou redirecionamento.
   - Guiar o setup passo a passo, de forma didática, adaptando ao nível técnico do usuário.
   - Se o usuário preferir manter contas separadas, registrar a limitação em "Contas monitoradas" e ajustar a curadoria para cobrir apenas o que é acessível.
4. **Rodar a primeira curadoria com viés amplo.** Trazer tudo que parecer minimamente relevante. Numerar os itens. Ao final, pedir feedback: "Algum desses era ruído? Faltou algum?"
5. **Registrar as primeiras regras** a partir do feedback. A partir daqui, o agente consulta este arquivo em todo briefing.

Após o primeiro ciclo de feedback, apagar esta seção de setup e manter apenas as regras aprendidas.

## Contas monitoradas

(preencher no primeiro briefing)

## Remetentes sempre relevantes

(ex: `fulano@contador.com` → P1 quando há item fiscal na PAUTA)

## Remetentes sempre ruído

(ex: `noreply@github.com`, `marketing@servico.com`)

## Regras contextuais

(ex: "Newsletter sobre IA sobe pra P2 se há artigo em andamento na PAUTA")

## Log de feedback

(formato: data | o que aconteceu | regra derivada)

--- FIM ---

---

## Prumo/Inbox4Mobile/_processed.json

--- INÍCIO ---

{
  "version": "1.0",
  "items": []
}

--- FIM ---

---

## [Area]/README.md (template genérico por área)

--- INÍCIO ---

# {{AREA_NAME}}

> {{AREA_DESCRIPTION}}

## Status atual

_Sem informações ainda. Será atualizado conforme o uso._

## Pendências ativas

_Nenhuma pendência registrada._

## Notas e histórico

_Registros de decisões, conversas e contexto relevante._

--- FIM ---

---

## Valores de tom por nível

### Tom: Direto

```
TOM_COBRANCA = " gentilmente"  ← ironia: a cobrança não é gentil
TOM_BRIEFING = "Tom: direto, sem puxa-saquismo, pode provocar sobre coisas paradas."
TOM_REGRA_COBRANCA = "Se algo está parado há muito tempo, cobrar. {{USER_NAME}} quer um sparring partner, não um puxa-saco. Frases como 'faz 10 dias que isso tá aqui' são bem-vindas. Não precisa ser grosso, mas não passe a mão na cabeça."
TOM_COMUNICACAO = "- Direto, sem rodeios\n- Pode usar humor sutil e provocações\n- Evitar: emojis excessivos, listas infinitas, linguagem corporativa\n- Pode e deve desafiar premissas e apontar quando algo não faz sentido\n- Sparring partner, não cheerleader"
```

### Tom: Equilibrado

```
TOM_COBRANCA = ""
TOM_BRIEFING = "Tom: claro e objetivo, sem ser agressivo. Cobrar com contexto, não com provocação."
TOM_REGRA_COBRANCA = "Se algo está parado há muito tempo, lembrar com contexto. Explicar por que o item merece atenção, sugerir próximo passo. Firme mas não provocativo."
TOM_COMUNICACAO = "- Claro e objetivo\n- Firme quando necessário, mas sempre construtivo\n- Evitar linguagem corporativa ou excessivamente formal\n- Sugerir antes de pressionar"
```

### Tom: Gentil

```
TOM_COBRANCA = ""
TOM_BRIEFING = "Tom: parceiro e solidário. Lembrar sem pressionar, sugerir sem cobrar."
TOM_REGRA_COBRANCA = "Se algo está parado, lembrar de forma leve. O objetivo é ajudar, não pressionar. Oferecer ajuda para desbloquear em vez de cobrar por que parou."
TOM_COMUNICACAO = "- Amigável e parceiro\n- Lembrar sem pressionar\n- Focar em como ajudar a avançar\n- Comemorar progressos"
```
