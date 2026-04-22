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
        """Skills portáveis copiadas do repo. Fallback quando CLI não está disponível."""
        return self.user_root / "skills" if self.nested_layout else self.root

    @property
    def system_skills_root(self) -> Path:
        """Alias legado. Usar skills_root."""
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
        return (
            self.relative(self.agent_index),
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
