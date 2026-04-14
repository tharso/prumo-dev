# Regras de proteção de arquivos

Antes de gerar QUALQUER arquivo, verificar se ele já existe na pasta do usuário. Isso é crítico em cenários de reconfiguração, migração, ou re-setup onde a pasta já contém dados acumulados.

## Regras de proteção

| Arquivo | Se já existir |
|---------|---------------|
| CLAUDE.md | **Não sobrescrever silenciosamente.** Em setup inicial pode criar; em reconfiguração, pedir confirmação explícita antes de regenerar. Em higiene assistida, sempre mostrar patch e criar backup em `_backup/CLAUDE.md.YYYY-MM-DD-HHMMSS` antes de aplicar. Conteúdo histórico, pendência vencida e item resolvido devem ser tratados como drift de governança, não como “mais um bloco” no mesmo arquivo. |
| AGENT.md | **Não sobrescrever silenciosamente.** Se existir, pedir confirmação explícita ou passar por repair/setup consciente. É índice canônico do workspace, não bilhete descartável. |
| PRUMO-CORE.md | **Sobrescrever** apenas em atualização de motor ou setup explícito. Sempre criar backup em `_backup/PRUMO-CORE.md.YYYY-MM-DD-HHMMSS` antes da troca. |
| AGENTS.md | **Não sobrescrever silenciosamente.** Se existir, pedir confirmação explícita, criar backup em `_backup/AGENTS.md.YYYY-MM-DD-HHMMSS` e só então atualizar. |
| PAUTA.md, INBOX.md, REGISTRO.md, IDEIAS.md | **NÃO sobrescrever.** Informar: "Encontrei [arquivo] com conteúdo existente. Mantendo o atual." |
| Agente/INDEX.md, Agente/PESSOAS.md, Referencias/INDICE.md | **NÃO sobrescrever.** Informar: "Encontrei [arquivo] com conteúdo existente. Mantendo o atual." |
| [Area]/README.md | **NÃO sobrescrever.** Informar: "A pasta [Area] já tem um README com contexto. Mantendo." |
| Pastas (_logs/, Inbox4Mobile/, Referencias/, _state/) | **Criar apenas se não existirem.** |

## Resumo pós-geração

Ao final da geração de arquivos, mostrar resumo claro:
- **Criados** (novos): listar arquivos que não existiam
- **Mantidos** (existentes): listar arquivos preservados
- **Sobrescritos**: apenas arquivos com confirmação explícita (sempre indicando backup e motivo)

## Tabela de arquivos a gerar

| Arquivo | Fonte | Descrição |
|---------|-------|-----------|
| AGENT.md | Gerar dinamicamente | Índice canônico do workspace e porta de entrada principal. |
| CLAUDE.md | claude-md-template.md | Configuração pessoal. Nunca atualizado automaticamente. |
| PRUMO-CORE.md | prumo-core.md | Motor do sistema. Atualizável automaticamente. |
| AGENTS.md | agents-md-template.md | Adapter para Codex e outros agentes não-Cowork; aponta para AGENT.md + PRUMO-CORE.md. |
| PAUTA.md | file-templates.md | Estado atual. Itens quentes, andamento, agendados. |
| INBOX.md | file-templates.md | Itens não processados. |
| REGISTRO.md | file-templates.md | Audit trail de itens processados. |
| IDEIAS.md | file-templates.md | Ideias sem ação imediata. |
| Agente/INDEX.md | file-templates.md | Índice modular do contexto vivo do usuário. |
| Agente/PESSOAS.md | file-templates.md | Tracking de pessoas e pendências de relacionamento. |
| [Area]/README.md | Gerar dinamicamente | Um README por área/projeto com nome e descrição breve. |
| _logs/ | Criar pasta vazia | Para registros semanais de revisão. |
| _state/ | Criar pasta vazia | Estado operacional (lock + handover). |
| _state/briefing-state.json | Gerar JSON inicial | Estado de referência temporal do briefing (`last_briefing_at`). |

| scripts/prumo_sanitize_state.py | Gerar arquivo | Sanitização de estado operacional (`HANDOVER`). |
| scripts/prumo_auto_sanitize.py | Gerar arquivo | Autosanitização por gatilhos com cooldown e calibração. |
| scripts/prumo_archive_cold_files.py | Gerar arquivo | Archive conservador de arquivos frios com índice global. |
| Inbox4Mobile/ | Criar pasta vazia | Para notas/arquivos do celular. |
| Referencias/ | Criar pasta vazia | Para material de referência. |
| Referencias/INDICE.md | file-templates.md | Índice de material de referência. |
