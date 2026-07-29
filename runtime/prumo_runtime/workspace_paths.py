from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    nested_layout: bool

    @property
    def user_root(self) -> Path:
        return self.root / "Prumo" if self.nested_layout else self.root

    @property
    def system_root(self) -> Path:
        return self.root / ".prumo" if self.nested_layout else self.root

    @property
    def state_root(self) -> Path:
        return self.system_root / "state" if self.nested_layout else self.root / "_state"

    @property
    def logs_root(self) -> Path:
        return self.system_root / "logs" if self.nested_layout else self.root / "_logs"

    @property
    def custom_root(self) -> Path:
        return self.user_root / "Custom"

    @property
    def custom_skills_root(self) -> Path:
        return self.custom_root / "skills"

    @property
    def custom_rules_root(self) -> Path:
        return self.custom_root / "rules"

    @property
    def skills_root(self) -> Path:
        """Skills portáveis copiadas do repo. Fallback quando o runtime CLI não
        está disponível.

        Mora em `.prumo/skills/` (pasta de infraestrutura invisível, alinhada
        com workspace-first). Decisão registrada em DECISIONS.md
        (2026-05-04, #77) — substitui parcialmente a decisão de 2026-04-15
        (#65) que escolhia `Prumo/skills/` (visível). Justificativa: skills
        são infra, não dado do usuário; preservar cadeia de fallback sem
        poluir o workspace visível.
        """
        return self.system_root / "skills" if self.nested_layout else self.root

    @property
    def system_skills_root(self) -> Path:
        """Alias legado. Usar `skills_root`."""
        return self.skills_root

    @property
    def arquivo_root(self) -> Path:
        return self.user_root / "Arquivo"

    @property
    def wrappers(self) -> dict[str, Path]:
        return {
            "AGENT.md": self.root / "AGENT.md",
            "AGENTS.md": self.root / "AGENTS.md",
            "CLAUDE.md": self.root / "CLAUDE.md",
        }

    @property
    def canonical_agent(self) -> Path:
        return self.user_root / "AGENT.md"

    @property
    def core_candidates(self) -> tuple[Path, ...]:
        candidates: list[Path] = []
        if self.nested_layout:
            candidates.extend(
                [
                    self.system_root / "system" / "PRUMO-CORE.md",
                    self.system_root / "PRUMO-CORE.md",
                ]
            )
        candidates.append(self.root / "PRUMO-CORE.md")
        return tuple(candidates)

    @property
    def core(self) -> Path:
        for candidate in self.core_candidates:
            if candidate.exists():
                return candidate
        return self.core_candidates[0]

    @property
    def agente_root(self) -> Path:
        return self.user_root / "Agente"

    @property
    def referencias_root(self) -> Path:
        return self.user_root / "Referencias"

    @property
    def inbox4mobile_root(self) -> Path:
        return self.user_root / "Inbox4Mobile"

    @property
    def pauta(self) -> Path:
        return self.user_root / "PAUTA.md"

    @property
    def inbox(self) -> Path:
        return self.user_root / "INBOX.md"

    @property
    def registro(self) -> Path:
        return self.user_root / "REGISTRO.md"

    @property
    def ideias(self) -> Path:
        return self.user_root / "IDEIAS.md"

    @property
    def agent_index(self) -> Path:
        return self.agente_root / "INDEX.md"

    @property
    def workflows_index(self) -> Path:
        return self.referencias_root / "WORKFLOWS.md"

    @property
    def referencias_index(self) -> Path:
        return self.referencias_root / "INDICE.md"

    @property
    def last_briefing(self) -> Path:
        return self.state_root / "last-briefing.json"

    @property
    def legacy_briefing_state(self) -> Path:
        return self.state_root / "briefing-state.json"

    @property
    def workspace_schema(self) -> Path:
        return self.state_root / "workspace-schema.json"

    @property
    def inbox_processed(self) -> Path:
        return self.inbox4mobile_root / "_processed.json"

    @property
    def inbox_preview_index(self) -> Path:
        return self.inbox4mobile_root / "_preview-index.json"

    def generated_relative_paths(self) -> tuple[str, ...]:
        items = [self.relative(path) for path in self.wrappers.values()]
        if self.nested_layout:
            items.append(self.relative(self.canonical_agent))
        items.append(self.relative(self.core))
        return tuple(items)

    def authorial_relative_paths(self) -> tuple[str, ...]:
        # `agent_index` (Agente/INDEX.md) foi aposentado na Fase 2 (#97):
        # não é mais arquivo esperado. A propriedade `agent_index` permanece
        # apenas como path de compatibilidade (leitura legada / tombstone).
        return (
            self.relative(self.agente_root / "PERFIL.md"),
            self.relative(self.agente_root / "MAPA-AUTORAL.md"),
            self.relative(self.agente_root / "PESSOAS.md"),
            self.relative(self.agente_root / "SAUDE.md"),
            self.relative(self.agente_root / "ROTINA.md"),
            self.relative(self.agente_root / "INFRA.md"),
            self.relative(self.agente_root / "PROJETOS.md"),
            self.relative(self.agente_root / "RELACOES.md"),
            self.relative(self.pauta),
            self.relative(self.inbox),
            self.relative(self.registro),
            self.relative(self.ideias),
            self.relative(self.referencias_index),
            self.relative(self.workflows_index),
        )

    def curated_relative_paths(self) -> tuple[str, ...]:
        """Arquivos que o snapshot da #262 copia: autoral + EMAIL-CURADORIA +
        fichas.

        COMPÕE `authorial_relative_paths()` em vez de estendê-lo: aquele método
        alimenta `files.authorial` do `workspace-schema.json`, que é contrato
        publicado, e uma segunda lista escrita à mão seria a "duas projeções do
        mesmo dado" que a #195 e a #258 passaram meses corrigindo.

        Fichas entram por REGRA, nunca por nome congelado — a ficha de amanhã
        é justamente o arquivo insubstituível que uma lista manual perderia.
        """
        items = list(self.authorial_relative_paths())
        items.append(self.relative(self.referencias_root / "EMAIL-CURADORIA.md"))
        seen = set(items)
        if self.referencias_root.is_dir():
            for path in sorted(self.referencias_root.glob("*.md")):
                # `_` e `.` são infraestrutura da pasta, não ficha (mesma
                # convenção do acervo).
                if path.name.startswith((".", "_")):
                    continue
                relative = self.relative(path)
                if relative not in seen:
                    items.append(relative)
                    seen.add(relative)
        return tuple(items)

    def curated_flow_paths(self) -> frozenset[str]:
        """Curados que existem PRA SER drenados — encolher é o contrato deles.

        Paths completos, nunca basename: uma ficha chamada `Referencias/PAUTA.md`
        é catálogo do usuário e some sem alarme se a classificação olhar só o
        nome do arquivo (Codex, 262F-5).
        """
        return frozenset(
            self.relative(p) for p in (self.pauta, self.inbox, self.registro, self.ideias)
        )

    def curated_hybrid_paths(self) -> frozenset[str]:
        """Parte gerada, parte autoral: só o miolo dos blocos de pulso é
        reescrito pelo `projetos --sync` (#201)."""
        return frozenset({self.relative(self.agente_root / "PROJETOS.md")})

    def curated_roots(self) -> tuple[Path, ...]:
        """Diretórios de onde os curados saem. Se um deles existir e NÃO for
        diretório, o inventário nasce furado — e sem esta checagem ele se
        declararia completo (Codex, 262F-2)."""
        return (self.user_root, self.agente_root, self.referencias_root)

    def derived_relative_paths(self) -> tuple[str, ...]:
        return (
            self.relative(self.workspace_schema),
            self.relative(self.last_briefing),
            self.relative(self.inbox_processed),
        )

    def directories(self) -> tuple[Path, ...]:
        dirs = [
            self.agente_root,
            self.inbox4mobile_root,
            self.referencias_root,
            self.logs_root,
            self.state_root,
        ]
        if self.nested_layout:
            dirs.extend([
                self.custom_root,
                self.custom_skills_root,
                self.custom_rules_root,
                self.arquivo_root,
                self.skills_root,
            ])
        return tuple(dirs)

    def relative(self, path: Path) -> str:
        return str(path.relative_to(self.root))


def detect_nested_layout(workspace: Path) -> bool:
    # Flat-layout marker takes precedence: if _state/workspace-schema.json
    # exists at the root, this is definitely a flat workspace. Without this
    # check, a dev repo named "Prumo/" inside the workspace would incorrectly
    # trigger nested-layout detection.
    if (workspace / "_state" / "workspace-schema.json").exists():
        return False
    return (workspace / "Prumo").exists() or (workspace / ".prumo").exists()


def workspace_paths(workspace: Path, *, layout_mode: str | None = None) -> WorkspacePaths:
    root = workspace.expanduser().resolve()
    nested_layout = detect_nested_layout(root) if layout_mode is None else layout_mode == "nested"
    return WorkspacePaths(root=root, nested_layout=nested_layout)


def _real_marker_inside(root: Path, candidate: Path) -> bool:
    """Marcador vale como identidade só se for arquivo REAL dentro da raiz.

    `.exists()` segue symlink e `.exists()` também é True para diretório. Um
    `_state/workspace-schema.json` que fosse symlink para fora faria o guard
    aceitar a pasta, e o `repair` que o `prumo update` dispara sozinho passaria
    a escrever pelo symlink, sobrescrevendo arquivo fora do workspace. A
    sanitize já trata symlink como fronteira de segurança; o guard não pode
    reabrir a janela por outra porta (Codex, r1).
    """
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return False
        candidate.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def is_prumo_workspace(workspace: Path) -> bool:
    """A pasta é um workspace do Prumo, em QUALQUER layout (#268).

    Substitui o atalho `(workspace / ".prumo").is_dir()` herdado da #179, que
    perguntava "isto é um workspace?" olhando um caminho exclusivo do NESTED e
    por isso recusava todo workspace flat legítimo.

    Identidade é marcador canônico — `workspace-schema.json` do layout ou o
    core — como arquivo real dentro da raiz. As posições aceitas do core são as
    do layout DETECTADO: `core_candidates` inclui a posição flat (raiz) como
    fallback de leitura, e aceitá-la aqui deixaria entrar um flat quebrado que
    os consumidores tratariam como nested — porteiro que aceita e manda o
    visitante pro prédio errado (Codex, r1).
    """
    root = Path(workspace).expanduser()
    if not root.is_dir():
        return False
    paths = workspace_paths(root)
    markers = [paths.workspace_schema]
    if paths.nested_layout:
        markers.append(paths.system_root / "system" / "PRUMO-CORE.md")
        markers.append(paths.system_root / "PRUMO-CORE.md")
    else:
        markers.append(root / "PRUMO-CORE.md")
    if any(_real_marker_inside(root, marker) for marker in markers):
        return True
    # Workspace meio-construído (infra criada, core ainda não) continua valendo
    # — mas SÓ no nested, e não por compatibilidade: `.prumo/` é nome exclusivo
    # do Prumo, então encontrá-lo já é identidade. No flat a infra se chama
    # `_state/`/`_logs/`, nomes que qualquer projeto pode ter; aceitá-los como
    # identidade faria `prumo update` rodar `repair` automático (update.py:742)
    # dentro de projeto alheio que só tivesse um `_logs/`. A assimetria não é
    # descuido: é o flat não ter namespace próprio (Codex, r1).
    return paths.nested_layout and paths.system_root.is_dir() and not paths.system_root.is_symlink()


def is_legacy_flat_workspace(workspace: Path) -> bool:
    """Workspace do Prumo no layout ANTIGO (flat), onde escrever é proibido.

    Decisão do dono (29/07, #268): no flat a LEITURA funciona — diagnóstico,
    panorama, status de versão — e a ESCRITA para, oferecendo `prumo migrate`.

    A razão não é preguiça de suportar dois layouts: é que os destinos de
    escrita do runtime (archive, backups, journal, semente, snapshot dos
    curados) são `.prumo/` literal em 39 pontos, e o `setup` não cria flat
    desde a era skills-first. Gravar num flat criaria uma árvore `.prumo/`
    DENTRO dele — os dois layouts misturados na mesma pasta, que é pior que
    recusar. O caminho do produto pra quem está no layout antigo é `migrate`.
    """
    return is_prumo_workspace(workspace) and not workspace_paths(workspace).nested_layout


LEGACY_FLAT_POST_UPDATE_NOTE = (
    "workspace no layout antigo (flat): o repair pós-update não roda aqui porque "
    "converteria o layout sem você pedir. Rode `prumo migrate --workspace .` "
    "quando quiser migrar."
)


def legacy_flat_refusal(workspace: Path, verbo: str) -> str:
    """Recado único da recusa de escrita no flat — mesmo texto em todo comando."""
    return (
        f"workspace no layout antigo (flat): {workspace} — nada a {verbo} aqui até migrar. "
        f"Gravar agora criaria um `.prumo/` dentro dele e misturaria os dois layouts. "
        f"Rode `prumo migrate --workspace {workspace}` primeiro; o diagnóstico "
        f"(`prumo sanitize` sem `--apply`) já funciona sem migrar."
    )
