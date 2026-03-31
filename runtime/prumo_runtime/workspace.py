from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.constants import (
    AUTHORIAL_FILES,
    DEFAULT_AGENT_NAME,
    DEFAULT_BRIEFING_TIME,
    DEFAULT_TIMEZONE,
    DERIVED_FILES,
    DIRECTORIES,
    GENERATED_FILES,
    RUNTIME_VERSION,
    SCHEMA_VERSION,
    authorial_files_for,
    derived_files_for,
    directories_for,
    generated_files_for,
    repo_root_from,
)
from prumo_runtime.apple_reminders import (
    apple_reminders_summary,
)
from prumo_runtime.capabilities import runtime_capabilities
from prumo_runtime import templates
from prumo_runtime.google_integration import google_integration_summary, render_google_integration_json
from prumo_runtime.workspace_paths import workspace_paths


def now_iso(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).replace(microsecond=0).isoformat()


def now_stamp(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).strftime("%Y%m%d-%H%M%S")


@dataclass
class WorkspaceConfig:
    workspace: Path
    user_name: str
    agent_name: str = DEFAULT_AGENT_NAME
    timezone_name: str = DEFAULT_TIMEZONE
    briefing_time: str = DEFAULT_BRIEFING_TIME
    layout_mode: str = "flat"
    wrapper_policy: str = "replace"


class WorkspaceError(RuntimeError):
    pass


def semantic_version_key(value: str) -> tuple[int, ...]:
    numbers = []
    current = ""
    for char in value:
        if char.isdigit():
            current += char
        elif current:
            numbers.append(int(current))
            current = ""
    if current:
        numbers.append(int(current))
    return tuple(numbers or [0])


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


ROOT_WRAPPERS = ("AGENT.md", "CLAUDE.md", "AGENTS.md")
WRAPPER_BLOCK_BEGIN = "<!-- prumo:begin -->"
WRAPPER_BLOCK_END = "<!-- prumo:end -->"


def backup_root_for(config: WorkspaceConfig, scope: str = "setup") -> Path:
    return config.workspace / ".prumo" / "backups" / scope / now_stamp(config.timezone_name)


def render_wrapper_merge_block(relative: str, rendered: str, config: WorkspaceConfig) -> str:
    canonical_target = "Prumo/AGENT.md" if config.layout_mode == "nested" else "AGENT.md"
    lines = [
        WRAPPER_BLOCK_BEGIN,
        f"Prumo detectado neste workspace. Para o canon, leia `{canonical_target}`.",
        'Se o usuário disser "Prumo", rode `prumo` neste diretório.',
        "Abaixo fica o bloco gerado pelo runtime. Se ele mudar, atualize só este trecho.",
        "",
        rendered.strip(),
        WRAPPER_BLOCK_END,
    ]
    return "\n".join(lines) + "\n"


def merge_wrapper_content(existing: str, relative: str, rendered: str, config: WorkspaceConfig) -> str:
    block = render_wrapper_merge_block(relative, rendered, config).rstrip()
    existing = existing.rstrip()
    if WRAPPER_BLOCK_BEGIN in existing and WRAPPER_BLOCK_END in existing:
        before, remainder = existing.split(WRAPPER_BLOCK_BEGIN, 1)
        _, after = remainder.split(WRAPPER_BLOCK_END, 1)
        rebuilt = before.rstrip()
        if rebuilt:
            rebuilt += "\n\n"
        rebuilt += block
        after = after.strip()
        if after:
            rebuilt += "\n\n" + after
        return rebuilt + "\n"
    if not existing:
        return block + "\n"
    return existing + "\n\n" + block + "\n"


def render_files(config: WorkspaceConfig) -> dict[str, str]:
    repo_root = repo_root_from(Path(__file__))
    setup_date = templates.now_display(config.timezone_name)
    paths = workspace_paths(config.workspace, layout_mode=config.layout_mode)
    canonical_target = paths.relative(paths.canonical_agent) if paths.nested_layout else "AGENT.md"
    core_relative = paths.relative(paths.core)
    state_relative = paths.relative(paths.state_root) + "/"
    rendered: dict[str, str] = {}
    if paths.nested_layout:
        rendered["AGENT.md"] = templates.render_agent_root_wrapper(
            config.user_name,
            config.agent_name,
            canonical_target=canonical_target,
            system_root=paths.relative(paths.state_root) + "/",
        )
    else:
        rendered["AGENT.md"] = templates.render_agent_md(
            user_name=config.user_name,
            agent_name=config.agent_name,
            timezone_name=config.timezone_name,
            briefing_time=config.briefing_time,
        )
    return {
        **rendered,
        paths.relative(paths.wrappers["CLAUDE.md"]): templates.render_claude_wrapper(
            config.user_name,
            config.agent_name,
            canonical_target=canonical_target,
            context_root=paths.relative(paths.agente_root) + "/",
            core_path=core_relative,
            state_path=state_relative,
        ),
        paths.relative(paths.wrappers["AGENTS.md"]): templates.render_agents_wrapper(
            config.user_name,
            config.agent_name,
            canonical_target=canonical_target,
            context_root=paths.relative(paths.agente_root) + "/",
            core_path=core_relative,
            state_path=state_relative,
        ),
        paths.relative(paths.core): templates.load_prumo_core_text(repo_root),
        paths.relative(paths.canonical_agent): templates.render_agent_md(
            user_name=config.user_name,
            agent_name=config.agent_name,
            timezone_name=config.timezone_name,
            briefing_time=config.briefing_time,
            core_path=core_relative,
            state_path=state_relative,
        ),
        paths.relative(paths.agent_index): templates.render_agente_index(
            user_name=config.user_name,
            timezone_name=config.timezone_name,
            briefing_time=config.briefing_time,
            setup_date=setup_date,
            core_path=core_relative,
        ),
        paths.relative(paths.agente_root / "PESSOAS.md"): templates.render_people_md(),
        paths.relative(paths.agente_root / "SAUDE.md"): templates.render_health_md(),
        paths.relative(paths.agente_root / "ROTINA.md"): templates.render_routine_md(),
        paths.relative(paths.agente_root / "INFRA.md"): templates.render_infra_md(),
        paths.relative(paths.agente_root / "PROJETOS.md"): templates.render_projects_md(),
        paths.relative(paths.agente_root / "RELACOES.md"): templates.render_relationships_md(),
        paths.relative(paths.pauta): templates.render_pauta_md(setup_date),
        paths.relative(paths.inbox): templates.render_inbox_md(),
        paths.relative(paths.registro): templates.render_registro_md(),
        paths.relative(paths.ideias): templates.render_ideias_md(),
        paths.relative(paths.referencias_index): templates.render_referencias_md(setup_date),
        paths.relative(paths.workflows_index): templates.render_workflows_md(setup_date),
        paths.relative(paths.briefing_state): templates.render_briefing_state_json(),
        paths.relative(paths.google_integration): render_google_integration_json(config.workspace),
        paths.relative(paths.inbox_processed): templates.render_inbox_processed_json(),
    }


def schema_payload(config: WorkspaceConfig) -> dict:
    paths = workspace_paths(config.workspace, layout_mode=config.layout_mode)
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "created_at": now_iso(config.timezone_name),
        "user_name": config.user_name,
        "agent_name": config.agent_name,
        "timezone": config.timezone_name,
        "briefing_time": config.briefing_time,
        "layout_mode": config.layout_mode,
        "files": {
            "generated": list(paths.generated_relative_paths()),
            "authorial": list(paths.authorial_relative_paths()),
            "derived": list(paths.derived_relative_paths()),
        },
    }


def ensure_directories(workspace: Path) -> None:
    paths = workspace_paths(workspace)
    for directory in paths.directories():
        directory.mkdir(parents=True, exist_ok=True)


def ensure_directories_for_layout(workspace: Path, layout_mode: str) -> None:
    paths = workspace_paths(workspace, layout_mode=layout_mode)
    for directory in paths.directories():
        directory.mkdir(parents=True, exist_ok=True)


def read_schema(workspace: Path) -> dict:
    return load_json(workspace_paths(workspace).workspace_schema)


def write_schema(config: WorkspaceConfig, preserve_created_at: str | None = None) -> None:
    payload = schema_payload(config)
    if preserve_created_at:
        payload["created_at"] = preserve_created_at
    write_json(workspace_paths(config.workspace).workspace_schema, payload)


def create_missing_files(config: WorkspaceConfig) -> dict[str, list[str]]:
    ensure_directories_for_layout(config.workspace, config.layout_mode)
    rendered = render_files(config)
    paths = workspace_paths(config.workspace, layout_mode=config.layout_mode)
    created: list[str] = []
    preserved: list[str] = []
    overwritten: list[str] = []
    merged: list[str] = []
    backed_up: list[str] = []
    backup_root: Path | None = None
    for relative, content in rendered.items():
        target = config.workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if relative in ROOT_WRAPPERS and config.layout_mode == "nested":
                policy = config.wrapper_policy
                if policy in {"replace", "merge"}:
                    if backup_root is None:
                        backup_root = backup_root_for(config)
                        backup_root.mkdir(parents=True, exist_ok=True)
                    backup_target = backup_root / relative.replace("/", "__")
                    shutil.copy2(target, backup_target)
                    backed_up.append(relative)
                    if policy == "replace":
                        target.write_text(content, encoding="utf-8")
                        overwritten.append(relative)
                    else:
                        merged_content = merge_wrapper_content(
                            target.read_text(encoding="utf-8"),
                            relative,
                            content,
                            config,
                        )
                        target.write_text(merged_content, encoding="utf-8")
                        merged.append(relative)
                    continue
                preserved.append(relative)
                continue
            preserved.append(relative)
            continue
        target.write_text(content, encoding="utf-8")
        created.append(relative)

    schema_path = paths.workspace_schema
    existing_schema = read_schema(config.workspace)
    created_at = existing_schema.get("created_at")
    if schema_path.exists():
        preserved.append(paths.relative(schema_path))
    write_schema(config, preserve_created_at=created_at)
    if not schema_path.exists():
        created.append(paths.relative(schema_path))
    result = {
        "created": created,
        "preserved": preserved,
        "overwritten": overwritten,
        "merged": merged,
        "backed_up": backed_up,
    }
    if backup_root is not None:
        result["backup_root"] = str(backup_root)
    return result


def install_skills(workspace: Path, *, layout_mode: str = "nested") -> list[str]:
    """Copy base skills from repo into .prumo/system/skills/ in the workspace."""
    from prumo_runtime.workspace_paths import workspace_paths as ws_paths

    paths = ws_paths(workspace, layout_mode=layout_mode)
    if not paths.nested_layout:
        return []
    repo = repo_root_from(Path(__file__))
    source = repo / "skills"
    if not source.is_dir():
        return []
    target = paths.system_skills_root
    installed: list[str] = []
    for skill_dir in sorted(source.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        dest = target / skill_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)
        installed.append(skill_dir.name)
    return installed


def install_custom_readme(workspace: Path, *, layout_mode: str = "nested") -> None:
    """Create a README in Prumo/Custom/ explaining what it's for."""
    from prumo_runtime.workspace_paths import workspace_paths as ws_paths

    paths = ws_paths(workspace, layout_mode=layout_mode)
    if not paths.nested_layout:
        return
    readme = paths.custom_root / "README.md"
    if readme.exists():
        return
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(
        "# Custom\n\n"
        "Personalizações do Prumo moram aqui. "
        "Regras, preferências, overrides de skills.\n\n"
        "O que estiver aqui tem precedência sobre o sistema base "
        "(`.prumo/system/`). Updates do Prumo nunca tocam nesta pasta.\n\n"
        "## Estrutura\n\n"
        "- `skills/` — overrides de skills (ex: briefing customizado)\n"
        "- `rules/` — regras e preferências leves "
        "(ex: mostrar agenda da família primeiro)\n",
        encoding="utf-8",
    )


def detect_missing(workspace: Path) -> dict[str, list[str]]:
    schema = read_schema(workspace)
    files = schema.get("files") or {
        "generated": list(generated_files_for(workspace)),
        "authorial": list(authorial_files_for(workspace)),
        "derived": list(derived_files_for(workspace)),
    }
    missing = {"generated": [], "authorial": [], "derived": []}
    for group in ("generated", "authorial", "derived"):
        for relative in files.get(group, []):
            if not (workspace / relative).exists():
                missing[group].append(relative)
    return missing


def infer_user_name(workspace: Path) -> str | None:
    schema = read_schema(workspace)
    if schema.get("user_name"):
        return str(schema["user_name"])
    index_path = workspace_paths(workspace).agent_index
    if not index_path.exists():
        return None
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Nome preferido:"):
            return line.split(":", 1)[1].strip()
    return None


def infer_user_name_from_legacy_claude(workspace: Path) -> str | None:
    claude_path = workspace_paths(workspace).wrappers["CLAUDE.md"]
    if not claude_path.exists():
        return None
    text = claude_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("- nome preferido:"):
            return stripped.split(":", 1)[1].strip()
        if stripped.lower().startswith("nome preferido:"):
            return stripped.split(":", 1)[1].strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# Prumo") and "—" in stripped:
            candidate = stripped.split("—", 1)[1].strip()
            if candidate:
                return candidate
    return None


def infer_agent_name(workspace: Path) -> str:
    schema = read_schema(workspace)
    value = schema.get("agent_name")
    return str(value) if value else DEFAULT_AGENT_NAME


def infer_timezone(workspace: Path) -> str:
    schema = read_schema(workspace)
    value = schema.get("timezone")
    return str(value) if value else DEFAULT_TIMEZONE


def infer_briefing_time(workspace: Path) -> str:
    schema = read_schema(workspace)
    value = schema.get("briefing_time")
    return str(value) if value else DEFAULT_BRIEFING_TIME


def infer_layout_mode(workspace: Path) -> str:
    schema = read_schema(workspace)
    value = str(schema.get("layout_mode") or "").strip().lower()
    if value in {"flat", "nested"}:
        return value
    return "nested" if workspace_paths(workspace).nested_layout else "flat"


def ensure_workspace_exists(workspace: Path) -> None:
    if not workspace.exists():
        raise WorkspaceError(f"workspace não encontrado: {workspace}")
    if not workspace.is_dir():
        raise WorkspaceError(f"workspace não é diretório: {workspace}")


def looks_like_wrapper(text: str) -> bool:
    return "Leia `AGENT.md` primeiro." in text or "Compatibilidade para Claude/Cowork." in text


def backup_path_for(workspace: Path, relative: str, stamp: str) -> Path:
    safe_name = relative.replace("/", "__")
    return workspace / ".prumo" / "backups" / "runtime-migrate" / stamp / safe_name


def build_config_from_existing(workspace: Path) -> WorkspaceConfig:
    ensure_workspace_exists(workspace)
    user_name = infer_user_name(workspace)
    if not user_name:
        raise WorkspaceError(
            "workspace sem identidade canônica. Rode `prumo setup --workspace ...` primeiro."
        )
    return WorkspaceConfig(
        workspace=workspace,
        user_name=user_name,
        agent_name=infer_agent_name(workspace),
        timezone_name=infer_timezone(workspace),
        briefing_time=infer_briefing_time(workspace),
        layout_mode=infer_layout_mode(workspace),
    )


def copy_to_backup(source: Path, backup_target: Path) -> None:
    backup_target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, backup_target)
        return
    shutil.copy2(source, backup_target)


def move_with_backup(
    source: Path,
    destination: Path,
    *,
    workspace: Path,
    stamp: str,
    backed_up: list[str],
    moved: list[str],
) -> None:
    if not source.exists():
        return
    relative = str(source.relative_to(workspace))
    backup_target = backup_path_for(workspace, relative, stamp)
    copy_to_backup(source, backup_target)
    backed_up.append(relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    moved.append(f"{relative} -> {destination.relative_to(workspace)}")


def remove_if_empty(path: Path) -> None:
    if path.exists() and path.is_dir() and not any(path.iterdir()):
        path.rmdir()


def migrate_legacy_workspace(config: WorkspaceConfig) -> dict[str, list[str] | str]:
    if infer_layout_mode(config.workspace) == "nested":
        raise WorkspaceError(
            "workspace já está no layout novo. `migrate` aqui seria retrofit com marreta."
        )

    nested_config = WorkspaceConfig(
        workspace=config.workspace,
        user_name=config.user_name,
        agent_name=config.agent_name,
        timezone_name=config.timezone_name,
        briefing_time=config.briefing_time,
        layout_mode="nested",
        wrapper_policy="replace",
    )
    stamp = now_stamp(config.timezone_name)
    backup_root = config.workspace / ".prumo" / "backups" / "runtime-migrate" / stamp
    backup_root.mkdir(parents=True, exist_ok=True)
    flat_paths = workspace_paths(config.workspace, layout_mode="flat")
    nested_paths = workspace_paths(config.workspace, layout_mode="nested")

    backed_up: list[str] = []
    created: list[str] = []
    overwritten: list[str] = []
    preserved: list[str] = []
    moved: list[str] = []
    legacy_claude_text: str | None = None

    claude_path = flat_paths.wrappers["CLAUDE.md"]
    legacy_import_path = nested_paths.agente_root / "LEGADO-CLAUDE.md"
    if claude_path.exists():
        current = claude_path.read_text(encoding="utf-8")
        if current.strip() and not looks_like_wrapper(current) and not legacy_import_path.exists():
            legacy_claude_text = current

    move_pairs = [
        (flat_paths.pauta, nested_paths.pauta),
        (flat_paths.inbox, nested_paths.inbox),
        (flat_paths.registro, nested_paths.registro),
        (flat_paths.ideias, nested_paths.ideias),
        (flat_paths.agente_root, nested_paths.agente_root),
        (flat_paths.referencias_root, nested_paths.referencias_root),
        (flat_paths.inbox4mobile_root, nested_paths.inbox4mobile_root),
        (flat_paths.state_root, nested_paths.state_root),
        (flat_paths.logs_root, nested_paths.logs_root),
    ]
    for source, destination in move_pairs:
        if source.exists() and destination.exists():
            preserved.append(str(destination.relative_to(config.workspace)))
            continue
        move_with_backup(
            source,
            destination,
            workspace=config.workspace,
            stamp=stamp,
            backed_up=backed_up,
            moved=moved,
        )

    for relative in ("AGENT.md", "CLAUDE.md", "AGENTS.md", "PRUMO-CORE.md"):
        target = config.workspace / relative
        if not target.exists():
            continue
        backup_target = backup_path_for(config.workspace, relative, stamp)
        copy_to_backup(target, backup_target)
        backed_up.append(relative)
        target.unlink()

    migrated = create_missing_files(nested_config)
    created.extend(migrated["created"])
    preserved.extend(migrated["preserved"])
    overwritten.extend(migrated["overwritten"])
    if "backup_root" in migrated:
        preserved.append("setup backup também criado")

    if legacy_claude_text and not legacy_import_path.exists():
        legacy_import_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_import_path.write_text(legacy_claude_text, encoding="utf-8")
        created.append("Prumo/Agente/LEGADO-CLAUDE.md")

    remove_if_empty(config.workspace / "_state")
    remove_if_empty(config.workspace / "_logs")

    return {
        "backup_root": str(backup_root),
        "backed_up": backed_up,
        "created": created,
        "overwritten": overwritten,
        "preserved": preserved,
        "moved": moved,
    }


def repair_workspace(workspace: Path) -> dict[str, list[str]]:
    config = build_config_from_existing(workspace)
    ensure_directories(workspace)
    rendered = render_files(config)
    missing = detect_missing(workspace)
    paths = workspace_paths(workspace)
    recreated: list[str] = []
    reported_authorial = list(missing["authorial"])

    for relative in [*missing["generated"], *missing["derived"]]:
        content = rendered.get(relative)
        if content is None and relative == paths.relative(paths.workspace_schema):
            write_schema(config, preserve_created_at=read_schema(workspace).get("created_at"))
            recreated.append(relative)
            continue
        if content is None:
            continue
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        recreated.append(relative)

    write_schema(config, preserve_created_at=read_schema(workspace).get("created_at"))
    return {
        "recreated": recreated,
        "missing_authorial": reported_authorial,
        "missing_generated": missing["generated"],
        "missing_derived": missing["derived"],
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def extract_section(markdown: str, heading: str) -> list[str]:
    lines = markdown.splitlines()
    capture = False
    collected: list[str] = []
    marker = f"## {heading}"
    for line in lines:
        if line.startswith("## "):
            if capture:
                break
            capture = line.strip() == marker
            continue
        if capture:
            stripped = line.strip()
            if not stripped or stripped.startswith("_"):
                continue
            collected.append(stripped)
    return collected


def parse_core_version(workspace: Path) -> str | None:
    core_path = workspace_paths(workspace).core
    if not core_path.exists():
        return None
    for line in core_path.read_text(encoding="utf-8").splitlines():
        if "prumo_version:" in line:
            return line.split("prumo_version:", 1)[1].replace("*", "").replace(">", "").strip()
    return None


def update_briefing_state(workspace: Path, timezone_name: str) -> None:
    state_path = workspace_paths(workspace).briefing_state
    state = load_json(state_path)
    state["last_briefing_at"] = now_iso(timezone_name)
    state.pop("interrupted_at", None)
    state.pop("resume_point", None)
    write_json(state_path, state)


def workspace_overview(workspace: Path) -> dict:
    config = build_config_from_existing(workspace)
    schema = read_schema(workspace)
    missing = detect_missing(workspace)
    paths = workspace_paths(workspace)
    core_version = parse_core_version(workspace)
    runtime_key = semantic_version_key(RUNTIME_VERSION)
    core_key = semantic_version_key(core_version or "0")
    google_summary = google_integration_summary(workspace)
    apple_summary = apple_reminders_summary(workspace)
    capabilities = runtime_capabilities(workspace, google_summary)
    return {
        "workspace_path": str(workspace.resolve()),
        "user_name": config.user_name,
        "agent_name": config.agent_name,
        "timezone": config.timezone_name,
        "briefing_time": config.briefing_time,
        "runtime_version": RUNTIME_VERSION,
        "schema_version": schema.get("schema_version") or SCHEMA_VERSION,
        "workspace_created_at": schema.get("created_at", ""),
        "core_version": core_version or "",
        "core_outdated": bool(core_version and core_key < runtime_key),
        "platform": capabilities["platform"],
        "capabilities": capabilities,
        "google_integration": google_summary,
        "apple_reminders": apple_summary,
        "missing": missing,
        "pauta_exists": paths.pauta.exists(),
        "inbox_exists": paths.inbox.exists(),
        "registro_exists": paths.registro.exists(),
    }


def append_registro(workspace: Path, origin: str, summary: str, action: str, destination: str) -> None:
    registro_path = workspace_paths(workspace).registro
    if not registro_path.exists():
        return
    today = datetime.now().strftime("%d/%m")
    line = f"| {today} | {origin} | {summary} | {action} | {destination} |\n"
    with registro_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
