# Decisões do projeto

Log de decisões arquiteturais e de processo. Cada entrada registra o contexto, a decisão e as alternativas consideradas. Antes de tomar uma decisão que possa contradizer algo já registrado, consultar este arquivo via **índice temático abaixo** — não confiar só em busca por palavra-chave.

## Índice temático

Use o tópico para encontrar decisões ativas na sua área antes de propor mudança nova. Atualizar esta tabela ao adicionar entrada nova.

| Tópico                | Entradas                                                                                  |
|-----------------------|-------------------------------------------------------------------------------------------|
| `workspace-layout`    | 2026-04-15 (#65), 2026-04-22 (workspace-first), 2026-05-04 (#77), 2026-06-21 (#97 mapas), 2026-06-25 (#114 perfil modular) |
| `skills-distribution` | 2026-04-14 (skills-first), 2026-04-15 (#65), 2026-04-21 (tharso-voice), 2026-05-04 (#77), 2026-06-23 (#102 decidir), 2026-06-24 (#109/#110 decidir conteúdo) |
| `governance`          | 2026-04-14 (CLAUDE.md), 2026-04-20 (#68 HANDOVER), 2026-04-22 (workspace-first), 2026-05-06 (quality-gate) |
| `distribution`        | 2026-04-14 (skills-first), 2026-04-21 (tharso-voice), 2026-04-22 (multi-cliente), 2026-04-22 (split dev/dist), 2026-06-24 (#110 não-bundle) |
| `dispatch-bootstrap`  | 2026-04-21 (#69 despacho), 2026-06-23 (#104 briefing rico)                                |
| `multiagent-coord`    | 2026-04-20 (#68 HANDOVER)                                                                 |
| `documentation`       | 2026-04-14 (CLAUDE.md), 2026-06-21 (#97 mapas)                                            |
| `integrations`        | 2026-04-14 (Google Drive snapshots)                                                       |
| `briefing`            | 2026-04-14 (Google Drive snapshots), 2026-04-21 (#69 despacho), 2026-06-23 (#102 decidir), 2026-06-23 (#104 briefing rico), 2026-06-25 (#114 perfil modular) |
| `personalization`     | 2026-04-21 (tharso-voice)                                                                 |
| `code-quality`        | 2026-05-06 (quality-gate), 2026-06-25 (#122 baseline 1061→930)                             |
| `touchpoint`          | 2026-05-18 (landing page sync)                                                            |

## Vocabulário controlado de tópicos

Lista inicial. Tópico novo entra após justificativa explícita na entrada que o introduz (parágrafo curto explicando por que o vocabulário existente não cabia).

- `workspace-layout` — estrutura de pastas e contratos do workspace do usuário (Prumo/, .prumo/).
- `skills-distribution` — onde skills moram, install/update, cadeia de fallback (slash → CLI → skill direto).
- `governance` — decisões, rastros, processos de desenvolvimento.
- `distribution` — como o produto chega ao usuário (plugins, marketplace, repos público/dev).
- `dispatch-bootstrap` — abertura de sessão e resolução de intenção do usuário.
- `multiagent-coord` — coordenação entre agentes em runtime do produto final.
- `documentation` — contratos textuais (CLAUDE.md, AGENT.md, DECISIONS.md, gotchas.md).
- `integrations` — Gmail, Calendar, MCPs externos, snapshots, conectores.
- `briefing` — fluxo do briefing matinal e seus módulos.
- `personalization` — skills/conteúdo específico de um usuário (não distribuído).
- `touchpoint` — pontos de contato com o usuário final fora do produto (landing page, docs públicas, README do repo público). Sincronização entre produto e superfície externa.

## Formato das entradas

A partir de 2026-05-04 (#78), toda entrada nova segue o formato:

```markdown
## YYYY-MM-DD — [Título descritivo]

**Tópicos:** lista de termos do vocabulário controlado, separados por vírgula.
**Issues relacionadas:** #N (papel: revoga / estende / mantém / bloqueia / desbloqueia / ortogonal), ou "nenhuma".
**Relações com decisões anteriores:** entradas prévias deste arquivo que esta entrada toca, com o papel (revoga, estende parcialmente, mantém, complementa). Se nenhuma, escrever explicitamente "nenhuma identificada após consulta ao índice temático" — isso documenta que a consulta foi feita.

**Contexto:** ...
**Decisão:** ...
**Alternativas consideradas:** ...
```

Entradas anteriores a 2026-05-04 não usam o campo "Relações com decisões anteriores" (introduzido na #78). Quando um conflito retrospectivo for descoberto, anotar a relação na entrada nova que o resolve — não reescrever entradas antigas.

- `code-quality` — métricas de qualidade do codebase, quality gate, baseline.

---

## 2026-06-25 — Baseline de `largest_file` apertado de 1061 para 930 (#122)

**Tópicos:** code-quality

**Issues relacionadas:** #122 (executa), #114 (origem — o refactor é follow-up da Fatia 5).

**Relações com decisões anteriores:** estende 2026-05-06 (quality gate com baseline congelado), que estabeleceu que o baseline só anda apertando e que toda atualização vira entrada aqui.

**Contexto:** A Fatia 5 da #114 levou o `workspace.py` ao teto do baseline (1061), forçando código espremido pra caber. O #122 extraiu o parsing de pauta/markdown para `pauta_parsing.py`, derrubando o `workspace.py` para 928 linhas — o maior arquivo do runtime passou a ter folga.

**Decisão:** Apertar `largest_file_lines` de 1061 para 930 (folga de 2 sobre o novo maior arquivo). A catraca anda só no sentido de apertar; 930 fica abaixo do baseline original (945, de 2026-05-06). Ruff e cobertura mantidos (11 / 81%) — a cobertura medida subiu para 82% com a extração, mas o aperto desse eixo fica para decisão futura. Proposto pelo agente, aprovado pelo Tharso.

**Alternativas consideradas:** manter em 1061 (descartado — esconderia a melhoria e deixaria margem para o arquivo voltar a inchar); apertar até 928 exato (descartado — zero folga quebraria o CI na primeira linha nova legítima).

---

## 2026-06-25 — Convergência do perfil para o `Agente/` modular; ritual reclassificado por natureza (#114)

**Tópicos:** workspace-layout, briefing
**Issues relacionadas:** #114 (issue-mãe, executa em fatias), #112 (Fatia 1 — ritual), #111 (diagnóstico que originou).
**Relações com decisões anteriores:**
- **Estende:** 2026-06-21 (#97 — consolidação dos mapas). A #97 oficializou os módulos `Agente/` (PESSOAS, SAUDE, ROTINA, INFRA, PROJETOS, RELACOES) como auto-descritivos. Esta decisão completa o movimento: as skills convergem para esse modelo modular e o `PERFIL.md` monolítico é reduzido ao núcleo identidade/tom.
- **Mantém e estende:** 2026-06-23 (#104 — briefing rico). O princípio "sem MCP, o briefing declara email/agenda indisponíveis e não mascara" passa a valer também para os rituais-evento.
- **Mantém:** 2026-04-22 (workspace-first — identidade mora no workspace). A reorganização é interna ao workspace; nada migra para fora dele.
- Nenhuma decisão revogada. A coexistência `PERFIL.md` monolítico (skills) vs `Agente/` modular (runtime) era **resíduo de evolução não-registrado**, não escolha — confirmado por consulta ao índice temático. Esta entrada reconcilia o vazio.

**Contexto:** O spike #111 diagnosticou que rituais recorrentes (lanche da Nina, ginástica, Roda Viva) ressuscitam entre hosts (Cowork ↔ Codex). O review de design do Codex na #112, verificado no código, achou a causa de fundo: o ritual está espalhado em três moradas (`PERFIL.md` "Lembretes recorrentes", `PAUTA.md` "Agendado/Lembretes", `Agente/ROTINA.md`) porque duas arquiteturas de perfil coexistem — o `PERFIL.md` monolítico que as skills assumem e o `Agente/` modular que o runtime gera (sem nem materializar `PERFIL.md`, ver `runtime/prumo_runtime/workspace.py:180-202`). O ritual-com-hora é, no fundo, um evento de calendário disfarçado de traço de perfil: guardá-lo estático no perfil recria à mão o estado (recorrência, ocorrência, "passou") que o calendário dá nativamente.

**Decisão:**
1. **Perfil modular vence.** As skills (setup, start, briefing, templates, governança) convergem para o `Agente/` modular. O `PERFIL.md` é **reduzido** ao núcleo sem aba própria (identidade, tom, áreas de vida) — não deletado. O contexto temático migra para as abas (`ROTINA`, `PESSOAS`, `SAUDE`, etc.). Migração dos workspaces instalados é **assistida** (skill `higiene`, com confirmação + backup + REGISTRO; nunca autosanitização — respeita o ASSERT do core).
2. **Ritual reclassificado por natureza** (teste de 3 saídas): com hora e compromisso → **agenda** (Calendar MCP); sem hora mas informa o julgamento → **contexto** (`ROTINA.md`); não muda decisão nenhuma → **poda**. Dissolve a categoria "lembrete recorrente estável sem hora e sem baixa". A seção "Agendado / Lembretes" do `PAUTA.md` deixa de ser destino de lembrete recorrente — **mantém o nome** (compat de `extract_section`), muda a semântica para pendência datada pontual.
3. **Calendário: o Prumo oferece, o usuário aprova, o Prumo cria — com idempotência** (checa se o evento já existe antes de oferecer, para não duplicar entre hosts). Nunca escreve sem aprovação explícita.
4. **Sem Calendar MCP: alertar e orientar, nunca mascarar.** O briefing declara a agenda indisponível e orienta reestabelecer o acesso (ou checar manual). O `ROTINA.md` guarda o ritual de forma durável, mas não substitui o alerta — porque a falta de acesso esconde também eventos reais não lidos (falha barulhenta > silêncio gracioso).
5. **Contenção do `ROTINA.md` (anti-inflação).** O `ROTINA` não pode virar a nova lixeira que a seção "Lembretes recorrentes" do PERFIL era — trocar o endereço da gaveta não resolve. Duas portas, não uma: **entrada** rigorosa (o teste de natureza do ponto 2 — só entra o que não tem hora *e* muda alguma decisão do Prumo) e **saída** por poda/revisão (a baixa do contexto é revisão, não conclusão). A saída reusa ganchos existentes: a **revisão semanal** (que já é poda; hoje revisa `PESSOAS.md`, não `ROTINA`) estendida ao `ROTINA`, e a **higiene** (que já diagnostica duplicações/redundâncias com confirmação e backup) com escopo ampliado de `PERFIL.md`-only para os módulos do `Agente/`. A **faxina não toca** o `ROTINA` — conteúdo pessoal exige julgamento, não baixa por idade/status. Três regras de contrato: (a) **exclusividade** — ritual com hora mora só na agenda; o Prumo infere a indisponibilidade lendo o calendário, nunca duplica no `ROTINA`; (b) **padrão, não log** — uma linha por verdade estável, não histórico de ocorrências; (c) **sem sobreposição entre abas** — pessoa → `PESSOAS.md`, cadência de projeto → `PROJETOS.md`. Tudo assistido: nada apaga sozinho (preserva o mojo). Encaixe nas fatias da #114: entrada na F1; higiene dos módulos `Agente/` na F3; exclusividade na F4; revisão semanal estendida na F5.

**Alternativas consideradas:**
- *Reclassificar o ritual dentro do `PERFIL.md`* (proposta original da #112) → rejeitado: mira o modelo errado; o runtime já modularizou e tem `ROTINA.md`.
- *Eliminar o `PERFIL.md`* → rejeitado: identidade/tom/áreas de vida não têm aba modular; reduzir, não deletar.
- *Prumo cria o evento automaticamente* → rejeitado: escrita no calendário do usuário é sensível e duplica entre hosts; oferecer + idempotência cobre sem o risco.
- *Fallback gracioso sem calendário (ritual vira contexto silenciosamente)* → rejeitado pelo Tharso: mascara a falta de acesso e esconde eventos reais não lidos.

**Touchpoint (prumo.me):** a reavaliar na Fatia 2 (onboarding) e Fatia 4 (calendário) — verificar se a landing descreve o setup/perfil ou a leitura de agenda antes do merge dessas fatias. Fatia 1 é interna (templates + governança), sem mudança de instalação/comandos/filosofia visível.

---

## 2026-06-24 — `decidir` com ações por conteúdo + extração de vídeo sem API paga (#109/#110)

**Tópicos:** skills-distribution, distribution, briefing
**Issues relacionadas:** #109 (executa — decidir por conteúdo, Fatia 1), #110 (decide — soft-hook de vídeo).
**Relações com decisões anteriores:**
- **Estende:** 2026-06-23 (#102 — decidir). As ações deixam de ser só por tipo de item e passam a ser por **conteúdo** (vídeo/artigo/imagem/nota); corrige a regra offline que eu havia super-apertado (ela vale para a mecânica, não para os links de conteúdo).
- **Mantém e aplica:** 2026-04-22 (multi-cliente — feature não pode depender de capacidade exclusiva de host / precisa caber em Markdown + runtime Python). Por isso a `youtube-extractor` **não** é empacotada (depende de yt-dlp + youtube-transcript-api + Gemini API); a extração vira **soft-hook** com fallback gratuito.

**Contexto:** Feedback de uso real do Tharso: a `decidir` prometia "ações contextuais" mas entregava menu genérico para itens de inbox (vídeo, artigo, imagem e nota recebiam o mesmo "rotear / virar referência"); links vinham inertes; e "virar referência" era buraco negro. Além disso, a `youtube-extractor` (que faria o gancho de vídeo) depende de API paga e binários externos.

**Decisão:**
1. **Ações por conteúdo** na `decidir` (allowlist + SKILL.md): vídeo → extrair/transcrever/resumir/abrir/ver-até; artigo → resumir/debater/ler-com-prazo; imagem → descrever/OCR; nota → tarefa/pauta/ideia. **Links de conteúdo ativos** (`<a target="_blank">`); a regra offline protege só a mecânica (fontes/JS).
2. **"Virar referência" passivo removido.** Guardar é committal (motivo + tag); fragmento sem próxima ação vira ideia (`IDEIAS.md`), não pauta — alinhado a "Ideias não são ações" (core, regra 5).
3. **Extração de vídeo sem API paga (soft-hook):** `extract_transcript` usa `youtube-transcript-api` (legendas grátis, sem key) quando disponível; senão metadados via fetch; senão abrir + tarefa. **Sem Gemini, sem yt-dlp, sem Whisper.** Quem resume/analisa é o Claude. A `youtube-extractor` **não** entra no Prumo (portabilidade).

**Alternativas consideradas:**
- *Empacotar a `youtube-extractor` as-is* → rejeitado: depende de API do Google + binários → fere a regra multi-cliente.
- *Bundlar versão leve (só `youtube-transcript-api`)* → adiado: ainda adiciona dep pip; por ora, soft-hook degradável cobre sem inflar o core. Pode virar dependência do runtime numa fatia futura.
- *Manter "virar referência"* → rejeitado: é o anti-padrão "acumular o que nunca será visto", contra a própria filosofia do Prumo.

**Touchpoint (prumo.me):** sem impacto imediato; ações por conteúdo são refinamento interno da `decidir` (que ainda nem está na landing). Reavaliar quando a `decidir` virar argumento de produto.

---

## 2026-06-23 — O briefing é a curadoria rica, não o cartão do runtime (#104, Modelo A, Fatia 1)

**Tópicos:** briefing, dispatch-bootstrap
**Issues relacionadas:** #104 (executa esta decisão, Fatia 1). Fatias seguintes: renomear copy da CLI, semente `--format json` read-only, ajustar o script do bridge.
**Relações com decisões anteriores:**
- **Refina:** 2026-06-23 (#102 — decidir / "Fase 2: runtime gera decidir"). A "Fase 2" original (runtime gera o HTML da decidir) foi **descartada por construir na altitude errada** — o runtime não cura email/agenda. Em vez disso: o runtime **semeia** (painel local determinístico), o **agente rico gera** o briefing e a decidir. A decidir continua alcançável, agora pelo caminho certo.
- **Refina (não revoga):** o bridge experimental (`cowork-runtime-bridge.md`). A regra "rodar o runtime, devolver a saída e encerrar" passa a valer **só para a prévia** (`start` / invocação curta), **não para o briefing**. O "runtime-first" para a prévia continua.
- **Estende e obedece melhor:** 2026-04-21 (#69 — despacho por intenção). O `dispatch.md` já dizia que a intenção "briefing" carrega `briefing-procedure.md` e que abertura não é briefing; esta decisão alinha o runtime a isso.
- **Mantém integralmente:** o contrato `interaction-format` (panorama numerado único) e os ASSERTs do core.

**Contexto:** Investigando o produto (não o workspace de ninguém), descobriu-se que no caminho feliz do runtime o briefing dava um **beco sem saída**: o cartão do runtime (`prumo briefing`) entrega um resumo enxuto local e encerra; a ação "briefing" do menu rodava `prumo briefing` de novo (circular); e a curadoria rica de email/agenda (`briefing-procedure.md`) — coração do "separa, lembra e cobra" — só rodava quando o bridge falhava. Ou seja: **quando o runtime funcionava, o briefing rico nunca acontecia**, e o Prumo perdia metade do valor. Design fechado com o Tharso (Modelo A) e revisado pelo Codex (review de design + de implementação na #104).

**Decisão (Modelo A):** dois gestos distintos. A **prévia** (`prumo start` / `prumo:abrir`) é o retrato rápido local + opções; entrega e encerra. O **briefing** é sempre a curadoria rica do agente (email/agenda via MCP quando disponível → panorama numerado único → `decidir` se 6+ itens). A ação `briefing` do `build_daily_actions` vira `host_prompt_action` que cede a vez ao agente (conserta a prévia e o cartão de uma vez). `prumo briefing --format json` segue como **painel local/semente**; o texto deixa de ser anunciado como "briefing explícito". A marcação "briefing feito hoje" passa a ser `prumo briefing --mark-done` ao final da curadoria. **Sem MCP**, o briefing entrega o panorama local e declara email/agenda indisponíveis (governança multi-cliente), nunca caindo de volta no cartão.

**Fatia 1 (esta):** ação → host-prompt, flag `--mark-done`, adapter_hints, docs (`briefing/SKILL.md`, `briefing-procedure.md`, `cowork-runtime-bridge.md`) e templates, + testes. **Depois:** renomear copy da CLI, tornar a semente `--format json` read-only, mexer no script do bridge.

**Alternativas consideradas:**
- *Runtime gera a decidir (Fase 2 original)* → rejeitado: altitude errada (runtime não cura email/agenda); construía uma decidir parcial ao custo de sistema.
- *Briefing como um gesto só, com "aprofundar" (Modelo B)* → rejeitado: mantém "briefing" significando duas coisas; menos limpo que dois gestos nomeados.
- *Manter o cartão enxuto e só linkar o rico* → rejeitado: continua deixando o rico como caminho secundário; o valor central ficava órfão.

**Touchpoint (prumo.me):** a reavaliar na fatia final — com o briefing rico de volta ao centro (e a decidir alcançável), pode reforçar a narrativa da landing.

---

## 2026-06-23 — Skill `decidir`: superfície de decisão interativa no briefing (#102, Fase 1)

**Tópicos:** briefing, skills-distribution
**Issues relacionadas:** #102 (executa esta decisão, Fase 1). Fase 2 (geração automática pelo runtime) vira issue separada.
**Relações com decisões anteriores:**
- **Estende:** 2026-04-21 (#69 — despacho por intenção). A `decidir` é a materialização visual do despacho em lote: quando há muitos itens, o usuário despacha item a item num HTML em vez de em prosa. Mantém o princípio "zero adivinhação" — cada despacho é explícito.
- **Mantém integralmente:** o contrato de interface (`interaction-format.md` v4.19.0) e o ASSERT do core "panorama numerado único, sem blocos progressivos". O HTML é **aditivo**, não substitutivo: o panorama em chat continua a camada base e reusa os mesmos números; o HTML é camada rica opcional acima de 6 itens, com override do usuário e fallback em chat. Nenhuma decisão revogada.
- **Mantém:** 2026-05-04 (#77 — skills/infra em `.prumo/`). O artefato efêmero vive em `.prumo/state/decidir/` (infra invisível); a limpeza é do `sanitize` (escopo exclusivo `.prumo/`), não da faxina.

**Contexto:** O briefing entrega um panorama numerado e o usuário despacha em lote ("3, 7, 12"). Despacho em prosa mistura decisões e força o Prumo a adivinhar o aprovado — o mesmo problema que a skill `crivo` resolve para crítica de artefatos. Itens diferentes pedem ações diferentes (responder email ≠ confirmar evento ≠ descartar cobrança), e o chat não dá um veredito clicável por item. Revisão cruzada com o Codex (2 rodadas via CLI, registradas na #102) apontou: (a) "briefing gera automático" exige runtime, não só skills — por isso o faseamento; (b) a generalização da mecânica `verdicts`-global → `actions`-por-card é segura com diff disciplinado; (c) os efeitos destrutivos (enviar, recusar com terceiros, remover inbox) não podem executar sem confirmação, ancorado em ASSERT do core.

**Decisão:** Criar a skill `prumo:decidir` (`skills/decidir/`), forkada da mecânica verificada do `crivo`, com tema escuro alinhado à landing e 100% offline. Ações são **contextuais por item**, escolhidas de uma allowlist por tipo (`references/acoes-allowlist.md`) — o Prumo seleciona, não inventa verbos. O relatório carrega um bloco JSON parseável (`prumo_decidir_report.v1`) além do markdown humano. A execução é em camadas: rascunhar/registrar/arquivar-com-destino direto; enviar/recusar-com-terceiros/remover-inbox confirmam antes (ASSERT do core).

**Fase 1 (esta issue):** a skill + integração no nível da skill `briefing` (gera o HTML quando o briefing roda pelo caminho markdown/skill, acima de 6 itens acionáveis). **Sem tocar runtime.** **Fase 2 (issue separada):** o runtime (`commands/briefing.py`) passa a gerar/linkar o artefato no payload, fazendo o automático valer no fast-path.

**Alternativas consideradas:**
- *HTML substitui o panorama em chat* → rejeitado: viola o ASSERT do core (panorama único) e a portabilidade (nem todo momento justifica abrir browser). O HTML é aditivo.
- *Ações fixas globais (como no crivo)* → rejeitado: item de briefing pede ação contextual (responder ≠ confirmar ≠ descartar). Allowlist por tipo resolve sem virar criatividade por execução.
- *Incluir o runtime na mesma issue* → adiado: expande o blast radius para `runtime/` (mudança de sistema). Fatiado em 2 fases para entregar valor incremental e testável.
- *Embutir a fonte como base64 no HTML* → rejeitado p/ Fase 1: copiar `Boliand.otf` pra junto do arquivo mantém offline sem inflar o template. Fallback de sistema se a cópia faltar.

**Touchpoint (prumo.me):** avaliado (2026-06-23). A landing apresenta o briefing como interação em chat ("Você pede o dia. Prumo faz o resto.") e não enumera skills; a `decidir` é aditiva (opcional, acima de 6 itens, com fallback em chat) e não muda instalação, comandos nem filosofia — **sem mudança necessária na Fase 1**. Reavaliar na Fase 2: quando a geração automática pelo runtime tornar o modo visual parte da experiência diária, pode virar argumento de produto na landing.

---

## 2026-06-21 — Consolidação dos mapas do workspace e aposentadoria do `Agente/INDEX.md` (#97)

**Tópicos:** workspace-layout, documentation
**Issues relacionadas:** #97 (executa esta decisão), #98 (PR da Fase 1).
**Relações com decisões anteriores:**
- **Mantém e reforça:** 2026-04-21 (#69 — despacho por intenção). Aposentar o INDEX como mapa reduz leitura especulativa na abertura, no espírito da #69.
- **Estende:** 2026-04-20 (#68 — tríade de limpeza). A faxina deixa de manter o INDEX (trabalho morto removido); seu escopo (`Prumo/`) permanece.
- **Complementa:** 2026-05-04 (#77 — skills em `.prumo/`). A Fase 1 corrigiu o drift `Prumo/skills/` → `.prumo/skills/` que ainda existia nas árvores de `prumo-core.md` e `file-templates.md`.
- Nenhuma decisão revogada.

**Contexto:** O workspace mantinha representações sobrepostas de "onde mora o quê": o `## Mapa do workspace` do `AGENT.md`, a `## Estrutura do workspace` do `PRUMO-CORE`, o `## Onde procurar o quê` do `Agente/INDEX.md`, mais uma árvore em `file-templates.md` e a versão dinâmica do runtime. Risco de drift (mapas discordando) e manutenção morta (a faxina reconciliava um INDEX que nenhum fluxo de skill lia). O INDEX não era órfão no runtime: era gerado e consumido como fallback de identidade. Revisão cruzada com o Codex (6 rodadas via CLI, registradas na #97) confirmou diagnóstico, escopo e implementação.

**Decisão:** O `## Mapa do workspace` do `Prumo/AGENT.md` é a fonte canônica única de navegação. O `Agente/INDEX.md` é aposentado em duas fases:
- **Fase 1 (#98):** remoção da leitura recomendada (skill + runtime) e do escopo da faxina; papéis declarados (navegação × árvore física × governança de gravação); correção do drift #77; `runtime-file-governance.md` completado com os destinos faltantes.
- **Fase 2:** o runtime para de gerar o INDEX; a identidade passa a resolver pela cadeia schema → `AGENT.md` → INDEX legado (compat); a migração converte o INDEX existente em **tombstone** apontando o `AGENT.md`, com backup e identidade extraída antes; o fluxo de skill (`file-templates.md`) também para de criá-lo.

Workspaces existentes preservam o INDEX como tombstone (nunca deletado no escuro). A propriedade `agent_index` permanece como path de compatibilidade. Os módulos de `Agente/` (`PESSOAS`, `SAUDE`, `ROTINA`, `INFRA`, `PROJETOS`, `RELACOES`) são auto-descritivos (cabeçalho próprio) e dispensam índice dedicado.

**Alternativas consideradas:**
- *Criar um "mapa-mestre" unificado (Rota A)* → rejeitado: adicionaria um quarto artefato e mais superfície de drift — o oposto do objetivo.
- *Fundir navegação e governança de gravação num só documento* → rejeitado: faria mal as duas coisas. Mantidos separados (`AGENT.md` × `runtime-file-governance.md`).
- *Deletar o INDEX em workspaces existentes* → rejeitado: tombstone com backup preserva trabalho do usuário e auditabilidade.
- *Manter o INDEX só no runtime para identidade* → rejeitado: a identidade migra para o `AGENT.md` (que já carrega o nome), eliminando a dependência.

**Touchpoint (prumo.me):** avaliado. A aposentadoria do INDEX é interna (arquivo que o usuário não abre; nenhum comando, fluxo de instalação ou filosofia muda). Sem impacto na landing.

---

## 2026-05-06 — Quality gate com baseline congelado no CI

**Tópicos:** governance, code-quality
**Issues relacionadas:** nenhuma (setup inicial, sem issue prévia).
**Relações com decisões anteriores:** nenhuma identificada após consulta ao índice temático.

**Contexto:** Com agentes de IA contribuindo código continuamente, revisão manual de PR virou gargalo. Sem controle automático, métricas como cobertura de testes e violações de lint tendem a regredir gradualmente sem que ninguém perceba.

**Decisão:** Introduzir um quality gate no CI (`scripts/quality_gate.py`) que congela três métricas em `scripts/baseline.json` — violações de ruff, cobertura de testes e tamanho do maior arquivo. Todo PR que regredir qualquer métrica quebra o CI antes de mergear. Baseline inicial: 12 violações, 81% cobertura, 945 linhas. O baseline só pode ser atualizado com aprovação explícita do Tharso; o agente propõe, Tharso decide. Quando atualizado, registrar nova entrada aqui.

**Alternativas consideradas:** SonarCloud (custo e complexidade desnecessários para um projeto solo), pre-commit hooks locais (não pegam código escrito por agentes remotos no CI), ignorar o problema (descartado — a experiência do Lucas Montano mostrou exatamente o que acontece em seis meses sem catraca).

---

## 2026-05-04 — Skills moram em `.prumo/skills/` (oculto), preservando cadeia de fallback (issue #77)

**Tópicos:** workspace-layout, skills-distribution

**Issues relacionadas:** #77 (executa esta decisão), #73 (desbloqueia — Fase Operacional ficava aguardando destino articulado), #65 (revoga parcialmente), #78 (estabeleceu o formato com este campo de Relações).

**Relações com decisões anteriores:**
- **Revoga parcialmente:** 2026-04-15 — Nova estrutura de workspace com fallback skills-first (#65). A decisão de copiar skills para `Prumo/skills/` (visível) é substituída por copiar para `.prumo/skills/` (invisível). Tudo o mais da #65 fica mantido.
- **Estende:** 2026-04-22 — Prumo e workspace-first. O princípio "infra invisível em `.prumo/`, dados visíveis em `Prumo/`" se aplica também às skills.
- **Mantém integralmente:** o princípio de cadeia de fallback (slash → CLI → skill direto), a regra "ler skill localmente é operação legítima, não simulação", a rejeição da alternativa "depender só do plugin" (era 1, pré-#65, continua rejeitada).

**Contexto:** A validação operacional da #73 em 2026-05-04 expôs que a Fase Operacional daquela issue (renomear `Prumo/skills/` → `Prumo/skills_OLD/` no DailyLife do Tharso) revogava silenciosamente a decisão de 2026-04-15 (#65) — sem articular destino para as skills. O Codex sinalizou drift no briefing matinal: AGENT.md referenciava `Prumo/skills/` que não existia mais. Post-mortem identificou seis falhas de sinalização (formalizadas na #78), e duas decisões adjacentes (workspace-first em 22/04 + estrutura skills-first em 15/04) tocando o mesmo território sem cross-reference.

A questão central: skills são *infra* (mecânica, atualizada via `prumo update`) ou *dado* (autoral, parte do workspace do usuário)? A #65 escolheu *dado* implicitamente ao colocar em `Prumo/`. A #73 escolheu *infra* sem articular. Esta decisão articula: skills são infra, moram em `.prumo/`.

**Decisão:** Skills (cópia das skills canônicas do repo) moram em `.prumo/skills/` no workspace do usuário. `workspace_paths.skills_root` aponta para `system_root / "skills"`. Templates, instalação via `prumo setup`, atualização via `prumo update`/`prumo migrate`, e cadeia de fallback do AGENT.md gerado pelo runtime usam o novo path. Migração de workspaces existentes via comando `prumo migrate skills-to-system` (a ser implementado em release subsequente, com pre-flight obrigatório).

**Alternativas consideradas:**
- *Manter `Prumo/skills/` (caminho da #65)* → rejeitado, contradiz workspace-first. Skills são infra atualizada via runtime, não dado autoral do usuário.
- *Voltar a era 1 — skills só no plugin instalado* → rejeitado, alternativa explícita rejeitada na #65 e mantida rejeitada aqui. Amarra a host específico, derruba cadeia de fallback.
- *Manter ambos `.prumo/skills/` e `Prumo/skills/` durante transição* → rejeitado, drift garantido. Uma fonte de verdade.
- *Usar identificadores abstratos (`prumo://modules/dispatch.md`)* → rejeitado, exige resolver custom em cada agente. Path simples e transparente vence simbolismo.

---

## 2026-04-22 — Prumo e workspace-first: identidade mora no workspace, plugin e stateless

**Contexto:** Debate sobre o risco de fragmentacao acidental. Hoje o plugin descobre o workspace por CWD + marcadores (`.prumo/state/workspace-schema.json`, `Prumo/`, `.prumo/`) e oferece onboarding silencioso em pasta vazia. Se o usuario abrir o Cowork numa pasta errada e disser "bom dia", o Prumo cria estrutura ali e comeca um workspace paralelo. Depois de alguns dias, o DailyLife real fica congelado no tempo enquanto o duplicado acumula registro novo. A fragmentacao nao e por copia, e por bifurcacao silenciosa.

Pesquisa em BMAD-METHOD (bmad-code-org) e Agent OS (buildermethods) mostrou dois modelos opostos. Agent OS faz instalacao em duas fases (`~/agent-os/` com identidade global + `project/agent-os/` com conteudo por projeto), mantendo identidade transversal. BMAD mantem tudo dentro do projeto (`_bmad/` no root, sem home directory), cada projeto autocontido e visivel. O Prumo nasceu mais proximo do BMAD — `.prumo/` e `Prumo/` vivem dentro da pasta do usuario. Forcar identidade global em `~/.prumo/` seria retrofit contra o DNA do produto.

**Decisao:** O Prumo e workspace-first. Identidade (voz, perfil, pessoas, regras de curadoria, historico) mora inteira dentro do workspace escolhido pelo usuario. Plugin (Cowork, Claude Code, Codex, Antigravity, runtime CLI) e executor stateless: nenhum estado persistente em `~/.prumo/` ou equivalente. O Prumo nao memoriza workspaces entre sessoes. O que o usuario ve na pasta e o que existe.

**Regras:**

1. CWD-discovery silencioso morre como porta de entrada. Skills `start` e `setup` ganham gatekeeper explicito: pasta vazia ou sem marcadores canonicos nunca vira workspace sem confirmacao ativa do usuario (nome do workspace + confirmacao da pasta antes do primeiro toque em disco).
2. O trigger da skill `start` por "qualquer interacao sem CLAUDE.md" e removido. Dispara apenas quando o usuario pede explicitamente ou quando o gatekeeper oferece como opcao.
3. Em pasta nao-workspace, as unicas opcoes do gatekeeper sao (a) criar workspace nomeado aqui, ou (b) fechar e reabrir onde o Prumo mora. Nao ha "procurar Prumo existente em outra pasta" — isso exigiria persistir estado sobre workspaces conhecidos, o que contradiz a decisao.
4. Segundo workspace e opt-in declarado. Criacao exige nome, confirmacao da pasta e ato deliberado. Nao ha heranca automatica de perfil entre workspaces. Se um dia precisar, vira comando explicito (`prumo fork-from <caminho>`).
5. Workspace e portatil por contrato. Paths absolutos persistidos em qualquer arquivo de estado sao bugs. Debito conhecido no fechamento desta decisao: `Prumo/Inbox4Mobile/_preview-index.json` ainda escreve `inbox_dir` absoluto. Cleanup obrigatorio.
6. Nao ha registry global de workspaces. `~/.prumo/` nao existe. Se um dia alguem propuser recriar, esta decisao e o freio.

**Alternativas consideradas:**

- *Agent OS-style* (identidade em `~/.prumo/profiles/` + workspaces que herdam): rejeitado. Cria metafisica de "Prumo canonico alem do workspace" que nao existe. A identidade do Prumo e o conteudo do workspace; separar os dois e ficcao arquitetural. Alem disso, agrega superficie de bug (sync entre `~/.prumo/` e workspace) sem ganho proporcional.
- *Status quo + registry central de workspaces conhecidos* (`~/.prumo/workspaces.json`): rejeitado. Muleta que resolve sintoma sem atacar a causa. Acrescenta estado global pra compensar a falta de identidade central — ou seja, pior dos dois mundos.
- *Status quo sem mudanca*: rejeitado. O risco de fragmentacao acidental e real e previsivel antes de qualquer reporte de usuario. Deixar o buraco aberto porque "ninguem caiu ainda" e decisao ruim.

---

## 2026-04-22 — Distribuicao multi-cliente: Cowork, Claude Code, Codex CLI, Antigravity como targets de primeira classe

**Contexto:** Ate o v4.x, o Prumo documentava instalacao primaria via Claude Code/Cowork e tratava os outros hosts como "compativeis em tese". Na pratica: `.claude-plugin/` era o unico manifesto distribuivel, Codex CLI e Antigravity nao tinham caminho testado. Risco: virar produto de ecossistema unico. A skill e portavel (SKILL.md + YAML frontmatter eh padrao aberto), mas cada host tem conveniencias diferentes (manifesto, marketplace, path de skills no disco). Sem tratar cada um como cidadao de primeira classe, o usuario fica dependente de terceiros reempacotarem o Prumo.

**Decisao:** Prumo passa a distribuir explicitamente em quatro canais, cada um com caminho de instalacao documentado, testado e espelhado:

1. **Cowork / Claude Code** — manifesto `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` (e espelhos na raiz por retrocompatibilidade). Instalacao via `claude plugin marketplace add https://github.com/tharso/prumo.git`.
2. **Codex CLI** — manifesto `.codex-plugin/plugin.json` + `.codex-plugin/marketplace.json`, schema especifico do Codex (source url, policy, category). Instalacao via `codex plugin marketplace add ...`.
3. **Antigravity (Gemini)** — sem manifesto. Cada skill em `skills/` eh standalone e compativel direto. Script `scripts/prumo_antigravity_install.sh --scope global|workspace` copia `skills/*` pra `~/.gemini/antigravity/skills/` ou `<pwd>/.agent/skills/`.
4. **Runtime standalone** — `prumo_runtime_install.sh|.ps1` instala o CLI `prumo` via uv ou pip. Serve qualquer host e eh recomendado como base de todos eles.

Todos leem a mesma fonte canonica: `skills/` + `runtime/prumo_runtime/`. Zero divergencia de comportamento entre hosts. O mirror workflow (`tharso/prumo-dev` -> `tharso/prumo`) espelha `.claude-plugin/`, `.codex-plugin/`, `skills/`, `runtime/` e os cinco scripts (4 runtime + 1 antigravity).

**Regras:**
- Adicionar novo host de primeira classe exige: manifesto proprio (ou caminho de instalacao documentado), script de instalacao ou receita no README, inclusao explicita no mirror workflow, linha dedicada no CHANGELOG.
- Nenhum host pode receber feature que dependa de capacidade exclusiva dele. Se a feature nao cabe em Markdown + runtime Python, nao entra.
- Skills nao podem assumir host especifico. Se precisarem, ramificam por deteccao em runtime, nunca por arquivo condicional.

**Alternativas consideradas:**
- Deixar Codex e Antigravity como "best effort" sem manifesto proprio -> rejeitado. Sem manifesto, Codex CLI nao descobre o plugin. Usuario teria que clonar na mao. Friccao mata adocao.
- Publicar cada host como plugin separado (prumo-claude, prumo-codex, prumo-antigravity) -> rejeitado. Duplica manutencao de versao, CHANGELOG, skills. Mesmo produto, quatro forks virtuais.
- Deixar Antigravity fora do escopo por ser mais novo -> rejeitado. Skills ja sao compativeis, custo zero de adicao. Script e cinco minutos.
- Exigir runtime como pre-requisito de todos os hosts -> rejeitado. Antigravity funciona sem runtime pra quem so quer briefing manual e despejar texto. Runtime e recomendado, nao obrigatorio.

---

## 2026-04-22 — Split dev/dist: `tharso/prumo-dev` desenvolve, `tharso/prumo` distribui

**Contexto:** O repositorio `tharso/prumo` acumulava dois contratos incompativeis: (1) repo de desenvolvimento com issues, history completo, documentos internos (DECISIONS.md, CLAUDE.md, AGENT.md, gotchas.md, `.github/`, `dev-archive/`, HANDOVER historico) e (2) repo publico instalavel via marketplace Cowork, Claude Code e `pip install prumo-runtime`. Consequencia: quem clonava ou instalava recebia um pacote poluido com arquivos de trabalho interno, dificil de auditar, com muitos sinais que nao sao contrato do produto. Auditoria mostrou: o `source: url` do marketplace do Cowork clona o repo inteiro, sem filtro. Arquivos sensiveis de desenvolvimento ficavam visiveis no cache do usuario.

**Decisao:** Separar desenvolvimento e distribuicao em dois repositorios distintos. O repo existente foi renomeado para `tharso/prumo-dev` (preserva issues, stars, URL redirects) e virou o repo de desenvolvimento. Um novo `tharso/prumo` vazio foi criado pra ser o espelho publico limpo, populado automaticamente por GitHub Action (`.github/workflows/mirror-to-prumo.yml`) a cada push em `prumo-dev/main`. O workflow faz force-push do subset distribuivel (`skills/`, `runtime/prumo_runtime/`, `.claude-plugin/`, README, LICENSE, CHANGELOG, VERSION, pyproject, 4 scripts de runtime) pra `tharso/prumo/main`. URL publica nao muda: quem instalava via `tharso/prumo` continua apontando pra la.

**Regras:**
- Desenvolvimento acontece exclusivamente em `tharso/prumo-dev`. PRs, issues, commits, reviews, tudo la.
- `tharso/prumo` e so-leitura pra humanos. Qualquer commit, PR ou tag nesse repo e sobrescrito no proximo espelhamento. Nao tem merito, so perde tempo.
- O espelho usa `git init` + force-push (nao preserva history publica). Se alguem quiser ver o history do desenvolvimento, vai em `prumo-dev`.
- Major bump justificado (4.20 -> 5.0): quebra contrato apenas pra quem tinha clone direto de `tharso/prumo.git` antes do split (history reescrita via force-push). Instalacao via plugin manager e `pip` continua transparente.

**Alternativas consideradas:**
- Manter um repo so e filtrar via `.gitignore` ou `.gitattributes` no marketplace -> rejeitado. O Cowork `source: url` clona tudo. `.gitignore` nao filtra o que ja foi commitado. Filtro em tempo de build exigiria infraestrutura no cliente, nao no autor.
- Usar `git-subdir` pra expor so um subdiretorio do mesmo repo -> rejeitado como escopo desta fase. Overhead de manter a estrutura `/dist/` no repo de dev nao compensa agora. O vazamento nao era critico de seguranca, so de higiene.
- Tornar o repo `tharso/prumo` privado e distribuir via releases tarball -> rejeitado, fricciona instalacao via marketplace (que espera URL publica) e via `pip` do GitHub.
- Renomear o repo publico pra `prumo-public` e deixar `tharso/prumo` como dev -> rejeitado. Quebraria todas as URLs de instalacao que ja estao por ai (marketplace, docs, curls). URL publica e contrato com o mundo, nao com o time.

---

## 2026-04-21 — Despacho por intencao substitui bootstrap just-in-case (issue #69)

**Contexto:** O bootstrap do Prumo lia na abertura `AGENT.md`, `PRUMO-CORE.md` inteiro, `PERFIL.md`, `EMAIL-CURADORIA.md`, `briefing-procedure.md`, `PAUTA.md` e `REGISTRO.md` presumindo que a tarefa e briefing matinal. Tres problemas: (1) Prumo virou ferramenta quase exclusiva de briefing, subutilizado para projetos, artigos, brainstorms e analises; (2) cada sessao nascia com ~10-15K tokens gastos em leitura especulativa; (3) abertura passiva ("bom dia, como posso ajudar?") sem se invocar como Prumo.

**Decisao:** Substituir bootstrap just-in-case por despacho por intencao (just-in-time). Abertura carrega so o minimo (AGENT.md + PRUMO-CORE Parte 1) e faz scan leve de PAUTA (cabecalhos) e REGISTRO (ultimas 5-10 linhas). Agente cumprimenta proativamente com 2-4 opcoes concretas ancoradas no scan + fuga explicita (`outra coisa`). Modulos operacionais (briefing, curar email, analise, etc.) sao carregados sob demanda conforme a intencao do usuario. Dispatch hibrido: tabela de gatilhos + pergunta de refinamento em caso de zero match ou dois matches. Zero adivinhacao silenciosa. "Bom dia" sozinho nao dispara briefing.

**Alternativas consideradas:**
- Manter bootstrap e so enxugar leitura inicial -> rejeitado, o problema nao e tamanho da leitura, e a presuncao de intencao. Briefing como default bloqueia os outros usos.
- Dispatch puramente por tabela de palavras-chave -> rejeitado, fragil com linguagem natural. Ambiguidade resolvida com pergunta curta vence heuristica sofisticada.
- Abertura minimalista sem scan ("bom dia. sobre o que vamos trabalhar?") -> rejeitado, regressao de interface. Parceiro de trabalho real usa o contexto que tem para sugerir, nao fica esperando comando. Scan leve (nao briefing) ancora as opcoes na realidade.

---

## 2026-04-21 — tharso-voice nao distribuido com produto publico

**Contexto:** Durante o design do modulo de dispatch (issue #69), a intencao "escrever artigo" naturalmente precisa ativar alguma skill de voz editorial. No workspace do Tharso existe `tharso-voice` (skill pessoal que captura o estilo editorial dele). Risco: referenciar `tharso-voice` dentro do produto publico do Prumo significaria que todo usuario que instalar o plugin receberia uma skill especifica do Tharso, seja via bundle, seja via dependencia declarada em `plugin.json`/`marketplace.json`.

**Decisao:** Skills pessoais ficam categoricamente separadas do produto publico. No modulo de dispatch, a intencao "escrever artigo" referencia a capacidade genericamente ("se existir skill pessoal de voz no workspace, ativa-la"), nunca nomeando `tharso-voice` ou qualquer outra skill pessoal especifica. Nenhuma skill pessoal entra em `skills/`, `plugin.json`, `marketplace.json` ou como dependencia declarada. Cada usuario traz sua propria skill de voz (ou nenhuma) para o workspace dele.

**Alternativas consideradas:**
- Incluir `tharso-voice` como skill opcional do bundle com flag de ativacao -> rejeitado, opcional instalado por padrao ainda e distribuicao. Resolve nada.
- Renomear `tharso-voice` para algo generico ("personal-voice") e distribuir vazia -> rejeitado, skill vazia nao tem utilidade e confunde usuarios. Cada pessoa precisa construir a propria.
- Documentar em README que usuarios podem adicionar skill de voz propria -> aceito como complemento, nao como substituto da regra. O produto tem que funcionar sem skill de voz instalada.

---

## 2026-04-20 — HANDOVER sai do produto do usuario (issue #68)

**Contexto:** `HANDOVER.md` nasceu como ferramenta de coordenacao entre agentes no desenvolvimento do proprio Prumo (Codex, Cowork, Gemini validando codigo um do outro). A pratica vazou pro produto final: cada workspace de usuario carregava um artefato narrativo pesado, com status `PENDING_VALIDATION`/`APPROVED`/`REJECTED`/`CLOSED`, logica de validacao cruzada, comando `/prumo:handover`, regras de briefing que chamavam handover e politicas de leitura que carregavam o arquivo todo. Usuario final nao orquestra dois agentes validando codigo um do outro. O artefato era peso morto no briefing e no contexto.

**Decisao:** Remover HANDOVER.md e `/prumo:handover` do produto do usuario. Coordenacao entre agentes no produto final passa a acontecer exclusivamente via `.prumo/state/agent-lock.json` (lock curto, sem narrativa). Handover como pratica de dev continua existindo, mas restrita a `dev-archive/` (gitignored) no repositorio de desenvolvimento. Triade de limpeza ficou clara: `sanitize` cuida de sistema (`.prumo/`, automatico com cooldown), `faxina` cuida de arquivos do usuario (`Prumo/`, automatica no briefing), `higiene` cuida de manutencao assistida do workspace do usuario (pergunta antes de mexer).

**Alternativas consideradas:**
- Manter HANDOVER como feature avancada opcional → rejeitado, peso morto na leitura de briefing e violacao do principio de que o produto e agnostico de multiagente no nivel de produto final.
- Matar sanitize junto com HANDOVER (achavam que `sanitize` era so sobre compactar handover) → rejeitado, verificacao do codigo mostrou que sanitize cuida de todo o territorio tecnico do sistema (`.prumo/backups/`, `.prumo/cache/`, `.prumo/state/`). Descobriu-se sobreposicao com faxina; solucao foi refocalizar sanitize em `.prumo/` e faxina em `Prumo/`.
- Deletar todo o historico de validacoes cruzadas de marco/2026 → rejeitado, 122KB com 30 validacoes reais entre agentes sao valor historico do desenvolvimento. Preservados em `DEV_Prumo/dev-archive/HANDOVER-2026-03.md` fora do produto e fora do repo publico.

---

## 2026-04-15 — Nova estrutura de workspace com fallback skills-first (issue #65)

**Contexto:** Quando o runtime CLI nao esta disponivel (Cowork sandbox, maquina sem instalacao), o agente trava porque o AGENT.md proibe ler arquivos para "simular" e nao oferece fallback. As skills nao sao copiadas para o workspace durante a instalacao, entao mesmo a rota de fallback nao tem material para operar.

**Decisao:** Adotar a estrutura PrumoPilot como padrao: raiz e territorio do usuario, `Prumo/` contem dados operacionais + copia das skills, `.prumo/` contem infraestrutura do sistema (state, logs, PRUMO-CORE.md). AGENT.md ganha cadeia de fallback: slash command -> runtime CLI -> skill direto. A regra "nao leia arquivo para simular" e substituida pela cadeia de fallback (skill direto e operacao legitima, nao simulacao).

**Alternativas consideradas:**
- Symlink de skills para o repo de dev -> rejeitado, acopla workspace de usuario ao repo de desenvolvimento. Mudancas no repo quebram o workspace instantaneamente.
- Manter tudo na raiz (estrutura DailyLife atual) -> rejeitado, mistura arquivos do sistema com arquivos do usuario e nao escala.
- Depender exclusivamente do plugin para carregar skills -> rejeitado, amarra a uma plataforma (Cowork) e contradiz skills-first.

---

## 2026-04-14 — Skills-first: descontinuar cowork-plugin/ e consolidar skills/ como fonte canonica

**Contexto:** O Prumo evoluiu de skill para plugin para runtime. Cada transicao criou uma copia das skills (`cowork-plugin/skills/`) que foi divergindo da fonte original (`skills/`). O resultado: duas copias quase identicas com versoes diferentes (4.17.0 vs 4.16.6), confusao sobre qual editar, e agentes sem saber qual e a fonte canonica.

**Decisao:** `skills/` e a fonte canonica unica. `cowork-plugin/` sera removido apos migracao dos smoke tests e atualizacao do CI. O `plugin.json` na raiz ja aponta para `skills/`, entao o marketplace continua funcionando.

**Alternativas consideradas:**
- Manter as duas pastas com script de sync automatico → rejeitado, complexidade sem beneficio.
- Mover tudo pra `cowork-plugin/` → rejeitado, o nome amarra ao Cowork e contradiz a direcao skills-first.

---

## 2026-04-14 — Remocao do mecanismo de Google Drive snapshots

**Contexto:** O briefing usava Google Docs como cache intermediario para emails e calendario (via Apps Script rodando a cada 15 min no Drive de cada conta). O mecanismo nunca foi configurado pelo usuario e o briefing perdia ~45s tentando ler snapshots inexistentes antes de cair no fallback (Gmail/Calendar MCP direto).

**Decisao:** Remover toda a camada de snapshots. Gmail MCP e Calendar MCP sao a fonte primaria. Arquivos de Apps Script, referencias no core, e o ASSERT que priorizava snapshots foram removidos.

**Alternativas consideradas:**
- Manter como fallback opcional → rejeitado, codigo morto que confunde agentes e desperdiça tempo de briefing.
- Configurar os Apps Scripts de verdade → rejeitado, o MCP direto funciona e e mais simples.

---

## 2026-04-14 — Criacao do CLAUDE.md como contrato operacional

**Contexto:** O projeto tinha 4 ADRs, playbooks de adapter, e documentos de jurisdicao, mas nenhum arquivo que dissesse a um agente "como se comportar aqui dentro" de forma unificada. Cada agente precisava descobrir as regras por conta propria.

**Decisao:** Criar CLAUDE.md na raiz como contrato operacional unico. AGENT.md e AGENTS.md sao ponteiros. Decisoes vao no DECISIONS.md.

**Alternativas consideradas:**
- Usar apenas ADRs → rejeitado, ADRs documentam decisoes pontuais mas nao dao instrucoes operacionais.
- Colocar regras no README → rejeitado, README e pra humanos entenderem o projeto, nao pra agentes operarem.

---

## 2026-05-18 — Sincronização obrigatória entre produto e landing page (prumo.me)

**Tópicos:** touchpoint, governance
**Issues relacionadas:** #63 (ortogonal — durante teste de first experience, ficou evidente que produto e página precisam andar juntos).
**Relações com decisões anteriores:** nenhuma identificada após consulta ao índice temático. Tópico `touchpoint` é novo — introduzido porque nenhum tópico existente cobre a relação produto ↔ superfície externa voltada ao usuário final. `distribution` cobre como o produto chega ao usuário (marketplace, repo, pip), mas não cobre a comunicação pública (landing page, filosofia, instruções de instalação visíveis).

**Contexto:** Durante o teste da issue #63 (first experience), ao simular o caminho completo de um usuário novo (prumo.me → curl → setup → host), ficou claro que mudanças no produto (comandos, fluxo de instalação, filosofia) podem desincronizar silenciosamente da landing page. O usuário final vê prumo.me primeiro — se a página promete algo que o produto não entrega mais, a primeira experiência quebra antes de começar.

**Decisão:** Toda mudança no produto que afete usabilidade, comandos, fluxo de instalação ou filosofia deve ser verificada contra prumo.me. Se a página não reflete a realidade do produto, ajustar antes de considerar a mudança concluída. Isso inclui:
- Mudança de comandos de instalação ou setup
- Alteração de pré-requisitos (hosts suportados, versões)
- Evolução da proposta de valor ou filosofia do produto
- Mudança no fluxo de onboarding

Referências operacionais:
- Landing page: https://prumo.me
- Repo: `tharso/prumo_landing-page` (Vercel auto-deploy)
- Local: `/Users/tharsovieira/Documents/DailyLife/Projetos/Prumo_LandingPage`

Regra correspondente adicionada ao `CLAUDE.md` na seção de governança.

**Alternativas consideradas:**
- Checar só em releases → rejeitado, mudanças incrementais na main já podem desincronizar antes de um release formal.
- Automatizar via CI → considerado para o futuro, mas hoje o volume de mudanças não justifica. A regra manual no CLAUDE.md garante que agentes e humanos lembrem.
