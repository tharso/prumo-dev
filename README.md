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

Prumo é agnóstico: mesma alma (as skills em `skills/`), quatro canais de instalação. Escolha o host que você já usa.

### Runtime local (recomendado em todos os casos)

O runtime é o motor que segura estado, coordena agentes e expõe o comando `prumo`. Instala uma vez, serve todos os hosts.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.sh)
```

Windows:

```powershell
irm https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_runtime_install.ps1 | iex
```

Depois:

```bash
prumo setup --workspace /caminho/da/pasta
```

### Cowork / Claude Code

Os dois leem o mesmo manifesto (`plugin.json` + `marketplace.json` na raiz ou em `.claude-plugin/`).

```bash
claude plugin marketplace add https://github.com/tharso/prumo.git
claude plugin install prumo@prumo
```

No Cowork: adicione `https://github.com/tharso/prumo.git` como marketplace na interface e instale o plugin `prumo`.

### Codex CLI

Codex usa `.codex-plugin/plugin.json`. Registre o marketplace e instale:

```bash
codex plugin marketplace add https://github.com/tharso/prumo.git
codex plugin install prumo
```

### Antigravity (Gemini)

Antigravity lê skills direto do filesystem. Instale via script, global ou por workspace:

```bash
# Global (~/.gemini/antigravity/skills/) — disponível em qualquer workspace
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_antigravity_install.sh)

# Por workspace (<pwd>/.agent/skills/) — escopado ao diretório atual
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_antigravity_install.sh) --scope workspace
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

`5.1.1`

## Licença

MIT

---

[prumo.me](https://prumo.me)
