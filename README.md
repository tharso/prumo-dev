# Prumo

**Despeja o caos, ele organiza.**

Prumo é um sistema de organização de vida pessoal que funciona com IA. Você despeja tudo que está na sua cabeça — pendências, projetos, ideias, compromissos — e ele separa, organiza, lembra e cobra. Sem dashboard pra manter, sem card pra arrastar, sem mais um app que vira pendência.

Seus dados ficam em arquivos Markdown no seu computador. Sem cloud, sem conta, sem lock-in.

## O problema

Você tem 47 coisas na cabeça. O email que precisa responder, a reunião que precisa preparar, o exame que depende do pedido médico que você ainda não pediu. Aí você baixa um app de produtividade — e duas semanas depois ele virou mais uma pendência na lista.

Prumo funciona diferente:

1. **Captura** — despeje tudo. Texto, áudio, foto, email. Do computador ou do celular.
2. **Processamento** — Prumo separa, categoriza e extrai próximas ações.
3. **Briefing diário** — todo dia, traz o que importa: pendências, prazos, emails sem resposta, compromissos.
4. **Resolve** — não só lista. Ajuda a resolver: pesquisa, rascunha, organiza, cobra.
5. **Documenta** — enquanto te ajuda, registra tudo. A documentação acontece como efeito colateral do uso.
6. **Adapta** — com o tempo, Prumo te conhece. Sabe que você procrastina com fricção, que prefere resolver antes de catalogar, que odeia cardápio longo.

## Instalação

```bash
# macOS / Linux
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.sh)

# Windows
irm https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.ps1 | iex
```

Depois, crie seu workspace:

```bash
prumo setup --workspace /caminho/da/pasta
```

`prumo setup` instala as skills e cria as conexões de filesystem que cada host descobre por convenção. Após o setup, abra qualquer host compatível no diretório do workspace e ele encontra o Prumo automaticamente.

| Host | Descoberta | Status |
|------|-----------|--------|
| Claude Code | `.claude/skills/` | symlinks criados; discovery por host validado em uso |
| Cowork | `.claude/skills/` | symlinks criados; discovery por host validado em uso |
| Antigravity (Gemini) | `.agent/skills/` | symlinks criados; smoke pendente |
| Codex CLI | plugin marketplace | via plugin (filesystem por projeto em investigação) |

> **Nota de segurança:** os comandos de instalação acima apontam pra branch `main` (mutável). Pra instalação verificável, use uma tag específica: `bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/v5.3.0/scripts/prumo_runtime_install.sh)`, substituindo `v5.3.0` pela versão desejada.

Para atualizar: `prumo update`. Para reparar workspace: `prumo repair --workspace .`

### Discoverability via marketplace (canal opcional)

Usuários que preferem descobrir o Prumo via marketplace do host podem instalar pelo respectivo plugin manager. A funcionalidade é equivalente — atalho de discovery, não dependência.

**Cowork / Claude Code:**

```bash
claude plugin marketplace add https://github.com/tharso/prumo.git
claude plugin install prumo@prumo
```

**Codex CLI:**

```bash
codex plugin marketplace add https://github.com/tharso/prumo.git
codex plugin install prumo
```

**Antigravity (Gemini)** — script standalone para ambientes sem runtime:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_antigravity_install.sh)
```

## Primeiros passos

Três gestos. É isso.

- **"Bom dia"** — briefing do dia
- **Despeja** — qualquer informação que estiver na sua cabeça
- **"Revisão"** — varredura semanal pra nada cair do radar

Se preferir ir direto: abra uma conversa e diga o que está na sua cabeça. Prumo organiza na hora.

## O workspace

O Prumo é **workspace-first**. Toda a identidade (perfil, pessoas, tom, história, curadoria, inbox) mora dentro de **uma** pasta escolhida por você. O plugin (Cowork, Claude Code, Codex, Antigravity, CLI) é executor: sem estado próprio, sem home oculto, sem registro global de workspaces.

Consequências práticas:

- Você escolhe conscientemente a pasta que vira casa do Prumo. Nenhuma pasta vira workspace por acidente: o setup exige confirmação nomeada antes de criar qualquer arquivo.
- Se rodar o Prumo em outra pasta vazia, ele não adota silencioso — propõe criar novo workspace ali ou fechar e voltar pra pasta original. Nunca duplica a vida.
- Workspace é portátil: mover a pasta pra outra máquina leva tudo junto. Paths absolutos em estado persistido são bugs.

Quer duas instâncias (ex: pessoal vs. trabalho)? É opt-in declarado: rode `/prumo:setup` na outra pasta e nomeie. São dois workspaces que não se conversam por design.

## Comandos

| Comando | O que faz |
|---------|-----------|
| `/setup` | Configura o Prumo (wizard conversacional, ~15 min) |
| `/start` | Onboarding rápido — despeje e o sistema organiza |
| `/briefing` | Briefing diário |
| `/sanitize` | Compacta estado e arquiva histórico |
| `/higiene` | Diagnostica e propõe limpeza do CLAUDE.md |
| `/doctor` | Diagnóstico técnico do runtime |

Pelo runtime CLI também: `prumo setup`, `prumo start`, `prumo briefing`, `prumo migrate` (workspaces flat → nested), `prumo migrate-skills` (workspaces pré-5.2.0 → estrutura nova; ver seção abaixo) e `prumo repair` (regenera arquivos recriáveis).

## Migração entre layouts

A estrutura do workspace evoluiu duas vezes em 2026:

- **Era pré-#65 (até 14/04):** workspace flat — `PAUTA.md`, `INBOX.md` e afins na raiz, estado em `_state/`.
- **Era #65 (15/04):** estrutura nested — dados em `Prumo/`, infra em `.prumo/`, skills em `Prumo/skills/`.
- **Era #77 (5.2.0, 04/05):** skills mudam de `Prumo/skills/` (visível) pra `.prumo/skills/` (oculto, infra de sistema). Mantém cadeia de fallback, alinha com workspace-first.

Cada salto tem comando dedicado:

```bash
# workspace flat (pré-#65) → nested (#65). Wizard interativo.
prumo migrate --workspace /caminho/do/workspace --user-name "Seu Nome"

# workspace nested-#65 → nested-#77 (skills em .prumo/). Pre-flight obrigatório.
prumo migrate-skills --workspace /caminho/do/workspace
```

`prumo migrate-skills` é idempotente: rodar em workspace já migrado, sem skills locais ou em estado ambíguo sai limpo (exit 0 com mensagem). Faz backup automático em `.prumo/backups/relocate-skills/<timestamp>/` antes de mover, e re-renderiza `Prumo/AGENT.md` e `.prumo/system/PRUMO-CORE.md` com os caminhos novos. Em CI ou automação, passe `--yes` pra pular o prompt de confirmação.

## Princípios

- **Tudo local.** Arquivos Markdown no seu computador. Abra com qualquer editor.
- **Sem lock-in.** Deletou o plugin? Seus arquivos continuam lá.
- **Uma entrada.** Sua vida não tem departamentos. Prumo também não.
- **Workspace-first.** Identidade mora no workspace, nunca no plugin. Zero estado global.
- **Proativo.** Não espera você checar. Traz o que importa na hora certa.
- **Resolve, não lista.** Outros sistemas viram mais um trabalho. Prumo tira trabalho.

## Estrutura

```
├── skills/                 # Alma do produto (portáteis entre hosts)
├── runtime/                # Motor mecânico (setup, auth, estado)
├── scripts/                # Instaladores (runtime + hosts específicos)
├── .claude-plugin/         # Manifesto para Cowork e Claude Code
├── .codex-plugin/          # Manifesto para Codex CLI
├── plugin.json             # Manifesto raiz (espelha .claude-plugin/)
├── marketplace.json        # Marketplace raiz
├── CHANGELOG.md            # Histórico
└── VERSION                 # Versão atual
```

## Versão

`5.3.0`

## Licença

MIT

---

[prumo.me](https://prumo.me)
