# Regras de proteção de arquivos

Antes de gerar QUALQUER arquivo, verificar se ele já existe na pasta do usuário. Isso é crítico em cenários de reconfiguração, migração, ou re-setup onde a pasta já contém dados acumulados.

## Regras de proteção

| Arquivo | Se já existir |
|---------|---------------|
| CLAUDE.md (raiz) | **Não sobrescrever silenciosamente.** Em setup inicial pode criar; em reconfiguração, pedir confirmação explícita antes de regenerar. É ponteiro, mas pode ter sido customizado. |
| AGENT.md (raiz) | **Não sobrescrever silenciosamente.** Ponteiro de compatibilidade. Pedir confirmação se já existir. |
| AGENTS.md (raiz) | **Não sobrescrever silenciosamente.** Ponteiro de compatibilidade. Pedir confirmação se já existir. |
| Prumo/AGENT.md | **Não sobrescrever silenciosamente.** Fonte canônica do workspace. Em reconfiguração, pedir confirmação explícita ou passar por repair/setup consciente. |
| .prumo/system/PRUMO-CORE.md | **Sobrescrever** apenas em atualização de motor ou setup explícito. Sempre criar backup em `.prumo/backup/PRUMO-CORE.md.YYYY-MM-DD-HHMMSS` antes da troca. |
| Prumo/Agente/PERFIL.md | **Não sobrescrever silenciosamente.** Em setup inicial pode criar; em reconfiguração, pedir confirmação explícita. Conteúdo histórico e drift de governança devem ser tratados pela higiene assistida, com backup em `.prumo/backup/PERFIL.md.YYYY-MM-DD-HHMMSS`. |
| Prumo/PAUTA.md, Prumo/INBOX.md, Prumo/REGISTRO.md, Prumo/IDEIAS.md | **NÃO sobrescrever.** Informar: "Encontrei [arquivo] com conteúdo existente. Mantendo o atual." |
| Prumo/Agente/INDEX.md, Prumo/Agente/PESSOAS.md, Prumo/Referencias/INDICE.md, Prumo/Referencias/EMAIL-CURADORIA.md | **NÃO sobrescrever.** Informar: "Encontrei [arquivo] com conteúdo existente. Mantendo o atual." |
| [Area]/README.md | **NÃO sobrescrever.** Informar: "A pasta [Area] já tem um README com contexto. Mantendo." |
| Pastas (.prumo/logs/, .prumo/state/, Prumo/Inbox4Mobile/, Prumo/Referencias/) | **Criar apenas se não existirem.** |

## Resumo pós-geração

Ao final da geração de arquivos, mostrar resumo claro:
- **Criados** (novos): listar arquivos que não existiam
- **Mantidos** (existentes): listar arquivos preservados
- **Sobrescritos**: apenas arquivos com confirmação explícita (sempre indicando backup e motivo)

## Tabela de arquivos a gerar

| Arquivo | Fonte | Descrição |
|---------|-------|-----------|
| CLAUDE.md (raiz) | claude-md-template.md | Ponteiro de compatibilidade para Claude Code/Cowork. |
| AGENT.md (raiz) | Gerar dinamicamente | Ponteiro de compatibilidade (mesmo conteúdo do CLAUDE.md na raiz, com texto adaptado). |
| AGENTS.md (raiz) | agents-md-template.md | Ponteiro de compatibilidade para Codex e outros agentes. |
| Prumo/AGENT.md | agent-md-template.md | Fonte canônica: navegação, fallback chain, regras do workspace. |
| Prumo/Agente/PERFIL.md | perfil-template.md | Configuração pessoal: áreas, tom, lembretes, integrações. Nunca atualizado automaticamente. |
| .prumo/system/PRUMO-CORE.md | prumo-core.md | Motor do sistema. Atualizável automaticamente. |
| Prumo/PAUTA.md | file-templates.md | Estado atual. Itens quentes, andamento, agendados. |
| Prumo/INBOX.md | file-templates.md | Itens não processados. |
| Prumo/REGISTRO.md | file-templates.md | Audit trail de itens processados. |
| Prumo/IDEIAS.md | file-templates.md | Ideias sem ação imediata. |
| Prumo/Agente/INDEX.md | file-templates.md | Índice modular do contexto vivo do usuário. |
| Prumo/Agente/PESSOAS.md | file-templates.md | Tracking de pessoas e pendências de relacionamento. |
| Prumo/Referencias/INDICE.md | file-templates.md | Índice de material de referência. |
| Prumo/Referencias/EMAIL-CURADORIA.md | file-templates.md | Regras aprendidas de curadoria de email (feedback loop). |
| [Area]/README.md | Gerar dinamicamente | Um README por área/projeto com nome e descrição breve. |
| .prumo/state/ | Criar pasta | Estado operacional (lock entre agentes). |
| .prumo/logs/ | Criar pasta | Registros de revisão. |
| .prumo/backup/ | Criar pasta | Backups de arquivos sobrescritos. |
| Prumo/Inbox4Mobile/ | Criar pasta | Para notas/arquivos do celular. |
| Prumo/Inbox4Mobile/_processed.json | file-templates.md | Registro de itens processados do mobile. |
| Prumo/Referencias/ | Criar pasta | Para material de referência. |
| Prumo/skills/ | Copiar do repo | Skills portáveis (fallback quando CLI não existe). |
