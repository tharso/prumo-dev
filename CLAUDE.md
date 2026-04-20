# Prumo

Sistema de organização de vida pessoal com IA. Transforma o Claude (ou qualquer agente) em interface para capturar, processar, lembrar e cobrar. Dados em Markdown local, sem cloud, sem lock-in.

## Stack

- **Runtime:** Python 3.11+ (`runtime/prumo_runtime/`), empacotado via hatchling
- **Skills:** Markdown com referências cruzadas (`skills/`)
- **Scripts operacionais:** Bash e Python (`scripts/`)
- **Testes:** unittest (Python) + smoke tests (Bash)
- **CI:** GitHub Actions (Ubuntu, macOS, Windows)
- **Distribuição:** marketplace do Cowork via `marketplace.json` + `plugin.json`
- **Repo:** https://github.com/tharso/prumo (público, MIT)

## Estrutura do projeto

```
skills/              ← fonte canônica das skills (portáveis, qualquer agente lê)
  prumo/             ← skill principal (setup, core, references, modules)
  briefing/          ← morning briefing
  start/             ← onboarding dump-first
  doctor/            ← diagnóstico
  faxina/            ← ciclo de vida da informação
  sanitize/          ← compactação de estado
  higiene/           ← manutenção do CLAUDE.md do workspace do usuário
runtime/             ← runtime Python (CLI local)
  prumo_runtime/     ← código do runtime
  tests/             ← unit tests
scripts/             ← scripts de operação e distribuição
  tests/             ← smoke tests
plugin.json          ← manifesto do plugin (aponta pra skills/)
marketplace.json     ← registro no marketplace do Cowork
pyproject.toml       ← empacotamento Python do runtime
```

### Diretórios removidos (não recriar)

Os seguintes diretórios e arquivos foram removidos em abril/2026 durante a consolidação skills-first. Não recriar: `cowork-plugin/`, `bridges/`, `_lixeira/`, `commands/`, `docs/`, adapter playbooks (`*-ADAPTER-PLAYBOOK.md`), ADRs avulsos na raiz.

## Planning

- Quando pedirem pra planejar: apenas o plano. Sem execução até aprovação explícita.
- Quando receberem um plano aprovado: seguir exatamente. Flagrar problemas reais e esperar.
- Para features não-triviais (3+ passos ou decisões arquiteturais): entrevistar sobre implementação, UX e tradeoffs antes de executar.
- Não construir para cenários imaginários. Simples e correto vence elaborado e especulativo.
- **Regra zero:** nunca sair codando sem um plano que alinhe expectativas antes. Isso vale pra qualquer mudança que toque mais de um arquivo ou mude comportamento observável.

## Regras operacionais

### Workflow de desenvolvimento

- TDD contextual: features em produção seguem TDD (testes antes do código). Protótipos e explorações podem ter testes depois, mas antes de qualquer merge.
- Commitar com mensagens descritivas em português. Prefixos: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`.
- Bumpar versão em `plugin.json`, `pyproject.toml`, `marketplace.json` e `VERSION` simultaneamente. Versão fora de sincronia é bug.

### Issues e documentação

- Issues no GitHub como unidade de trabalho: toda feature, bug ou refactor vira issue antes da implementação.
- O agente cria a issue com critérios de aceite claros e assina como ele mesmo (não em nome do Tharso).
- Toda ação relevante numa issue deve ter comentário explicando o que foi feito e por quê.
- Issues submetidas pelo usuário ficam como "review" após resolução (Tharso fecha). Issues criadas pelo agente podem ser fechadas por ele se passaram nos testes e critérios de aceite.

### Governança agente/humano

- Features novas: criar issue e aguardar aprovação antes de implementar.
- Bugs triviais e refactors pequenos (< 3 arquivos, sem mudança de comportamento): pode executar direto.
- Qualquer mudança que altere a experiência do usuário final do Prumo: precisa de aprovação.
- Qualquer mudança em `plugin.json`, `marketplace.json` ou `pyproject.toml`: precisa de aprovação.

### Restrições

- **Nunca** reintroduzir a camada de plugin como intermediária entre skills e consumidor. O Prumo é skills-first.
- **Nunca** criar novos playbooks de adapter. Essa fase acabou.
- **Nunca** commitar direto na main sem CI verde.
- **Nunca** deletar arquivos sem verificar referências.
- **Nunca** mudar configs de produção sem explicação na issue.

## Edit Safety (código)

- Reler o arquivo antes e depois de editar. O tool de edição falha silenciosamente quando o trecho mudou desde a última leitura.
- Em qualquer rename ou mudança de assinatura: buscar chamadas diretas, referências de tipo, imports, re-exports, mocks de teste. Grep não é AST, assumir que sempre perdeu algo e verificar.
- Verificar que nada referencia um arquivo antes de deletá-lo.
- Refactors em fases: máximo 5 arquivos por rodada, depois verificar e obter aprovação.
- Antes de refatorar arquivo grande (>300 LOC): remover código morto e imports não usados primeiro. Commitar limpeza separadamente.
- Comentários: default é não comentar. Só quando o PORQUÊ não é óbvio.

## Integridade referencial (conteúdo/skills)

- Antes de editar um arquivo que referencia outros (ou é referenciado), verificar que as referências existem e estão corretas.
- Reler antes e depois de editar. Compactação de contexto destrói memória de conteúdo textual.
- Reorganização em fases, por área/tema. Reorganizações grandes quebram referências implícitas.
- Manter tom e formato existentes nos arquivos. Não reescrever conteúdo num estilo diferente sem aprovação.

## Configuração e secrets

- `.env`, credentials, tokens ficam fora do repo. Verificar `.gitignore` antes de qualquer commit.
- Qualquer mudança em arquivo de config deve ter comentário na issue explicando o que mudou e por quê.

## Context Management

- Após 10+ mensagens: reler qualquer arquivo antes de editá-lo. Compactação automática pode ter destruído memória do conteúdo.
- Se notar degradação de contexto: rodar /compact proativamente. Escrever estado da sessão para que forks possam continuar.
- Cada leitura de arquivo é limitada a 2.000 linhas. Para arquivos com mais de 500 linhas: usar offset e limit para ler em chunks.

## Self-Correction

- Após qualquer correção do usuário: registrar o padrão em gotchas.md. Converter erros em regras.
- Se um fix não funcionar após duas tentativas: parar. Ler a seção inteira relevante de cima a baixo. Declarar onde o modelo mental estava errado.

## Communication

- Quando o usuário disser "sim", "faz", "manda": executar. Não repetir o plano.
- Quando apontarem código ou conteúdo existente como referência: estudar e replicar os padrões.
- Trabalhar a partir de dados concretos. Não chutar. Se falta informação, perguntar.

## Comunicação entre agentes (ambiente de desenvolvimento)

Handover é ferramenta de coordenação entre agentes **dentro do desenvolvimento do Prumo**. Não é feature do produto do usuário final (ver issue #68 e DECISIONS.md de 2026-04-20).

Regras:

- **Artefatos de handover vivem em `dev-archive/`** (gitignored). Nada de handover deve aparecer em `skills/`, `runtime/` ou `scripts/`.
- **Lock entre agentes no produto final**: coordenação no workspace do usuário acontece exclusivamente via `.prumo/state/agent-lock.json`. Sem narrativa, sem PENDING_VALIDATION.
- **Validações cruzadas entre Codex/Cowork/Gemini/Claude durante dev**: podem usar os artefatos em `dev-archive/` como registro histórico ou continuar a prática localmente, desde que não vaze nada disso pra dentro das skills ou do runtime.
- Se uma próxima geração do produto precisar de um contrato de handover de volta, vira issue nova e decisão arquitetural explícita. Não é "reverter a remoção".

## Decisões arquiteturais

Ver DECISIONS.md para o log completo. Ao tomar uma decisão relevante, registrar lá com data, contexto, decisão e alternativas consideradas. Antes de tomar uma decisão que possa contradizer algo já registrado, consultar DECISIONS.md.

## Direção atual do projeto

O Prumo passou por três fases: skill → plugin → runtime. Cada transição deixou resíduos. A direção atual é **skills-first**: a alma do produto vive nas skills (portáveis, legíveis por qualquer agente), o runtime é infraestrutura de suporte. A consolidação foi executada em abril/2026: `cowork-plugin/`, adapter playbooks, ADRs avulsos, `bridges/`, `docs/` e `_lixeira/` foram removidos. `skills/` é a fonte canônica única.
