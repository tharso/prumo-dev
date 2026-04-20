# Changelog — skill de setup

### v4.19.0 (20/04/2026)
- **HANDOVER sai do produto (issue #68)**: remoção do artefato `HANDOVER.md` e do comando `/prumo:handover` do escopo do usuário. Coordenação entre agentes continua via `agent-lock.json`. Handover como prática fica restrito ao desenvolvimento do próprio Prumo.
- **Sanitize refocalizada**: escopo agora é exclusivamente `.prumo/` (sistema). Arquivos do usuário ficam com faxina e higiene. Triade limpa: `sanitize` (sistema, automático), `faxina` (usuário, automático), `higiene` (usuário, assistida).

### v4.0 (26/02/2026)
- **Progressive discovery**: SKILL.md refatorado de 487 para ~300 linhas. Feedback loop, regras de proteção de arquivos e changelog extraídos para `references/`.
- **Estrutura de plugin**: skills reorganizadas em `skills/<nome>/SKILL.md` compatível com deploy no Cowork.
- **Skill start (dump-first)**: nova skill de onboarding alternativo via dump-first. Coexiste com o setup wizard.

### v3.4 (19/02/2026)
- **Paridade sem shell no briefing**: fallback oficial para runtimes sem shell/Gemini CLI mantendo curadoria por ação (`Responder`, `Ver`, `Sem ação`) com prioridade `P1/P2/P3`.
- **Estado temporal explícito**: setup passa a gerar `.prumo/state/briefing-state.json` para suportar janela "desde o último briefing" em qualquer runtime.
- **Template de automação local**: `references/prumo-google-dual-snapshot.sh` incorporado como ativo de produto (modo avançado opcional).

### v3.3 (19/02/2026)
- **Curadoria de email no briefing**: troca do critério "não lidos mais recentes" por triagem orientada à ação (`Responder`, `Ver`, `Sem ação`) com justificativa objetiva.
- **Janela temporal de briefing**: integração com estado `.prumo/state/briefing-state.json` para analisar emails desde o último briefing concluído.
- **Integração Google dual opcional**: suporte a script local (`scripts/prumo_google_dual_snapshot.sh`) gerado via setup quando o usuário habilitar modo avançado com Gemini CLI.

### v3.2 (19/02/2026)
- **Adapter AGENT.md**: Setup agora gera `AGENT.md` como ponteiro para `Prumo/Agente/PERFIL.md` + `.prumo/system/PRUMO-CORE.md` (sem duplicação de conteúdo).
- **Comando canônico**: `/prumo:briefing` definido como padrão; `/briefing` mantido como alias legado.
- **Estado operacional**: setup cria pasta `.prumo/state/` para lock entre agentes e estado temporal do briefing.

### v3.1 (14/02/2026)
- **Trigger `/Prumo`**: Comando principal de ativação trocado de "quero organizar minha vida" para `/Prumo`. Mais claro, sem soar autoajuda.
- **Etapa 0 reescrita (detectar, não instruir)**: A Etapa 0 anterior tentava guiar a seleção de pasta no meio da conversa, o que é impossível no Cowork (pasta precisa ser escolhida ANTES de iniciar a sessão). Nova versão detecta automaticamente se a pasta é real ou temporária. Se for temporária, manda o usuário fechar, selecionar a pasta, e voltar. Sem workarounds.
- **Localização correta do seletor**: Corrigido de "ícone de pasta na barra lateral" para "abaixo e à esquerda da caixa de input".

### v3.0 (14/02/2026)
- **Etapa 0 — Verificação de pasta**: Setup agora começa verificando se o Cowork tem uma pasta real selecionada. Se não tem, guia o usuário a selecionar antes de qualquer pergunta. Se o usuário já tem estrutura organizada, adapta-se ao que existe.
- **Uma pergunta por vez**: Todas as etapas do setup agora fazem uma pergunta por mensagem. Opções claras via AskUserQuestion, mínimo de digitação. UX radicalmente melhorada.
- **Decisões reversíveis**: Comunicado desde o início que todas as escolhas do setup podem ser ajustadas depois. "O Prumo vai te conhecendo melhor com o uso."
- **Tom mais acessível**: Removido "sócio chato", "Admin". Linguagem amigável durante setup ("amigo que te lembra de tudo na hora certa").
- **Terminologia clara**: "Admin" → "Burocracias do dia a dia".

### v2.1 (13/02/2026)
- **Proteção de arquivos no setup**: Etapa 9 agora verifica se arquivos já existem antes de gerar. Dados acumulados (PAUTA, REGISTRO, IDEIAS, READMEs) nunca são sobrescritos. CLAUDE.md ganha backup automático antes de regenerar. Seguro para re-setup, migração e reconfiguração.

### v2.0 (13/02/2026)
- **Arquitetura de dois arquivos**: PERFIL.md (pessoal, imutável) + PRUMO-CORE.md (sistema, atualizável). Permite updates sem perder personalizações.
- **Auto-update**: PRUMO-CORE.md verifica versão no GitHub e oferece atualização automática. Mensagem explícita de que dados/personalizações não são afetados.
- **Comando /briefing**: Skill dedicada que executa o morning briefing completo (7 passos). Legado; atual canônico é `/prumo:briefing`.
- **Arquivo VERSION no repo**: Controle de versão simplificado para o mecanismo de update.

### v1.2 (13/02/2026)
- **Datas em itens pendentes**: Regra 3 agora exige `(desde DD/MM)` ao mover itens pro destino. Torna o envelhecimento visível.
- **Links clicáveis**: Regra 1 agora exige `computer://` links ao referenciar arquivos na conversa. Entregar, não só informar.
- **Seção de concluídos na PAUTA**: Template da PAUTA agora inclui "Semana atual — Concluídos" e "Semana passada — Concluídos". Rotação automática na revisão semanal.
- **Renomeação descritiva**: Regra 3 agora exige renomeação autoexplicativa ao mover qualquer arquivo do inbox (não só referências).

### v1.1 (13/02/2026)
- Feedback loop nativo (regra 13 no CLAUDE.md)
- Feedback proativo (detecção de sinais + sugestão automática)
- Template do CLAUDE.md com regra 13

### v1.0 (12/02/2026)
- Setup wizard com 10 etapas
- Templates: CLAUDE.md, PAUTA.md, INBOX.md, REGISTRO.md, IDEIAS.md, PESSOAS.md
- 3 tons de comunicação (direto, equilibrado, gentil)
- Captura mobile (iOS shortcut + email)
- Integrações: Gmail, Google Calendar
