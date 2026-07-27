# PACKAGING — onde cada artefato vive, em que forma, e quem sincroniza

> M4 do épico #177 (#181). Este arquivo existe pra que a **próxima divergência
> de empacotamento seja decisão, nunca acidente**: antes de mudar o que vai
> em qual superfície, registrar a decisão no `DECISIONS.md` e atualizar as
> tabelas abaixo. O teste `runtime/tests/test_packaging_doc.py` valida este
> doc contra o `plugin.json` e a árvore `skills/` — doc que mente quebra o CI.
>
> Fica na RAIZ de propósito: dentro de `skills/` embarcaria no wheel e no
> espelho público (e, dentro de uma skill, seria vendorado pro workspace) —
> é doc de manutenção do repo, não do produto.

## As superfícies

| # | Superfície | O que é | Quem escreve lá |
|---|---|---|---|
| 1 | **Source** (`tharso/prumo-dev` → `skills/`) | Fonte canônica única (skills-first) | Desenvolvimento (PRs) |
| 2 | **Espelho público** (`tharso/prumo`) | Subset distribuível, história preservada (#159) | Workflow `mirror-to-prumo.yml` — NUNCA commit direto |
| 3 | **Store do host** | As camadas 3–5 da propagação (subtabela abaixo) | Host (UI/CLI de plugins) |
| 4 | **Wheel** (`prumo_runtime/_bundled/`) | `skills/` + `plugin.json` + `VERSION` embarcados no pacote Python | hatchling (`force-include` no `pyproject.toml`) — gerado em build |
| 5 | **Workspace** (`.prumo/skills/` e `.prumo/system/`) | Cópia local das skills (fallback sem CLI) + o CORE REAL | Runtime: `install_skills` (setup) e `repair` |

### A cadeia de propagação em 5 camadas (#190 — o drift mora ENTRE os elos)

| Camada | Onde | Modo de falha conhecido |
|---|---|---|
| 1. Repo dev | `tharso/prumo-dev` | — |
| 2. Espelho público | `tharso/prumo` (mirror workflow) | história reescrita congela consumidores (#145/#159) |
| 3. Checkout do marketplace | `marketplaces/<nome>/` no store | preso no passado (três naturezas, #145) |
| 4. Plugin instalado | store unificada `~/.claude/plugins` (`cowork_plugins` é legado morto) | era pré-5.x; caches órfãos (#146/#190) |
| 5. Registro da conta → sessão | server-side → `<sessão>/<id>/rpm/` | registro congelado re-vinculado pela reinstalação (#190) |

O doctor diagnostica os elos 3–5; o drift plugin↔workspace fecha o circuito com o elo 5→workspace.

## Artefato → superfície → forma → sincronizador

| Artefato | Source | Espelho | Store do host | Wheel `_bundled` | Workspace |
|---|---|---|---|---|---|
| Skills top-level (8) | completo | completo (mirror) | completo (host install) | completo (hatchling) | completo em `.prumo/skills/` (`install_skills`/`repair`) |
| Módulos (`skills/prumo/references/modules/`) | completo | completo | completo | completo | completo em `.prumo/skills/prumo/references/modules/` |
| `prumo-core.md` | completo | completo | completo | completo | **stub-ponteiro** em `.prumo/skills/.../references/` (`<!-- prumo-core-stub: v1 -->`, `_stub_vendored_core`, #179) — o core REAL vive em `.prumo/system/PRUMO-CORE.md` |
| Wrappers da raiz (`CLAUDE.md`/`AGENT.md`/`AGENTS.md`) | templates em `templates.py` (+ `generate_adapter_templates.py` gera os `.md` de referência) | — | — | via código do wheel | gerado por template + merge in-place (blocos autorais preservados); `CLAUDE.md` = perfil minimal, `AGENT.md`/`AGENTS.md` = full (#180) |
| Porta canônica (`Prumo/AGENT.md`) | template em `templates.py` | — | — | via código | gerado por template (`render_agent_md`), regenerado com backup no `repair` |
| `plugin.json` / `VERSION` | completo | completo | lido pelo host | completo | `VERSION` não vai; a versão do workspace é o `prumo_version` do core |

## Skill × módulo, por superfície

**Skills top-level (8 — exatamente as do `plugin.json`):** `abrir`, `acervo`,
`briefing`, `decidir`, `fim`, `higiene`, `menu`, `prumo`. Aparecem no picker
dos hosts e existem como diretório em `skills/<nome>/SKILL.md`.

**Módulos de intenção (não são skills — #172):** `faxina`, `sanitize` e
`doctor` atendem por linguagem natural via tabela do `dispatch.md` e vivem em
`skills/prumo/references/modules/*.md`. Não têm diretório top-level nem
entrada no picker; a sanitização tem executor no runtime (`prumo sanitize`),
faxina e doctor seguem 100% módulo (o doctor roda script bash que NUNCA
importa o runtime).

**Nota sobre `start`:** a skill top-level foi removida na #134; o **comando de
runtime** `prumo start` continua vivo (a prévia). Não recriar a skill.

## Quem sincroniza o quê (resumo)

- **hatchling** — embala `skills/`+`plugin.json`+`VERSION` no wheel a cada build.
- **mirror-to-prumo.yml** — source → espelho público a cada push na main.
- **Host install** (UI/CLI) — espelho → checkout do marketplace → plugin
  instalado → (Cowork) registro server-side da conta → `rpm/` das sessões.
- **`install_skills` / `repair`** — bundle → `.prumo/skills/` do workspace
  (com poda do que não veio da fonte e re-stub do core vendored).
- **`generate_adapter_templates.py`** — templates `.md` de referência a partir
  do `templates.py` (paridade md↔py; script versionado em `scripts/`).

## A regra

Divergência nova de empacotamento (artefato mudando de forma ou de
superfície) é **decisão de arquitetura**: entrada no `DECISIONS.md` (com o
checklist do CLAUDE.md) e atualização DESTE arquivo no mesmo PR. O
`test_packaging_doc.py` existe pra transformar esquecimento em CI vermelho.
