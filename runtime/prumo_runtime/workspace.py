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
    repo_root_from,
)
from prumo_runtime.apple_reminders import (
    apple_reminders_summary,
    render_apple_reminders_json,
    render_apple_reminders_snapshot_json,
)
from prumo_runtime import templates
from prumo_runtime.google_integration import google_integration_summary, render_google_integration_json


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


def render_files(config: WorkspaceConfig) -> dict[str, str]:
    repo_root = repo_root_from(Path(__file__))
    setup_date = templates.now_display(config.timezone_name)
    return {
        "AGENT.md": templates.render_agent_md(
            user_name=config.user_name,
            agent_name=config.agent_name,
            timezone_name=config.timezone_name,
            briefing_time=config.briefing_time,
        ),
        "CLAUDE.md": templates.render_claude_wrapper(config.user_name, config.agent_name),
        "AGENTS.md": templates.render_agents_wrapper(config.user_name, config.agent_name),
        "PRUMO-CORE.md": templates.load_prumo_core_text(repo_root),
        "Agente/INDEX.md": templates.render_agente_index(
            user_name=config.user_name,
            timezone_name=config.timezone_name,
            briefing_time=config.briefing_time,
            setup_date=setup_date,
        ),
        "Agente/PESSOAS.md": templates.render_people_md(),
        "Agente/SAUDE.md": templates.render_health_md(),
        "Agente/ROTINA.md": templates.render_routine_md(),
        "Agente/INFRA.md": templates.render_infra_md(),
        "Agente/PROJETOS.md": templates.render_projects_md(),
        "Agente/RELACOES.md": templates.render_relationships_md(),
        "PAUTA.md": templates.render_pauta_md(setup_date),
        "INBOX.md": templates.render_inbox_md(),
        "REGISTRO.md": templates.render_registro_md(),
        "IDEIAS.md": templates.render_ideias_md(),
        "Referencias/INDICE.md": templates.render_referencias_md(setup_date),
        "_state/briefing-state.json": templates.render_briefing_state_json(),
        "_state/google-integration.json": render_google_integration_json(config.workspace),
        "_state/apple-reminders-integration.json": render_apple_reminders_json(),
        "_state/apple-reminders-snapshot.json": render_apple_reminders_snapshot_json(),
        "Inbox4Mobile/_processed.json": templates.render_inbox_processed_json(),
    }


def schema_payload(config: WorkspaceConfig) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "created_at": now_iso(config.timezone_name),
        "user_name": config.user_name,
        "agent_name": config.agent_name,
        "timezone": config.timezone_name,
        "briefing_time": config.briefing_time,
        "files": {
            "generated": list(GENERATED_FILES),
            "authorial": list(AUTHORIAL_FILES),
            "derived": list(DERIVED_FILES),
        },
    }


def ensure_directories(workspace: Path) -> None:
    for relative in DIRECTORIES:
        (workspace / relative).mkdir(parents=True, exist_ok=True)


def read_schema(workspace: Path) -> dict:
    return load_json(workspace / "_state" / "workspace-schema.json")


def write_schema(config: WorkspaceConfig, preserve_created_at: str | None = None) -> None:
    payload = schema_payload(config)
    if preserve_created_at:
        payload["created_at"] = preserve_created_at
    write_json(config.workspace / "_state" / "workspace-schema.json", payload)


def create_missing_files(config: WorkspaceConfig) -> dict[str, list[str]]:
    ensure_directories(config.workspace)
    rendered = render_files(config)
    created: list[str] = []
    preserved: list[str] = []
    for relative, content in rendered.items():
        target = config.workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            preserved.append(relative)
            continue
        target.write_text(content, encoding="utf-8")
        created.append(relative)

    schema_path = config.workspace / "_state" / "workspace-schema.json"
    existing_schema = read_schema(config.workspace)
    created_at = existing_schema.get("created_at")
    if schema_path.exists():
        preserved.append("_state/workspace-schema.json")
    write_schema(config, preserve_created_at=created_at)
    if not schema_path.exists():
        created.append("_state/workspace-schema.json")
    return {"created": created, "preserved": preserved}


def detect_missing(workspace: Path) -> dict[str, list[str]]:
    schema = read_schema(workspace)
    files = schema.get("files") or {
        "generated": list(GENERATED_FILES),
        "authorial": list(AUTHORIAL_FILES),
        "derived": list(DERIVED_FILES),
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
    index_path = workspace / "Agente" / "INDEX.md"
    if not index_path.exists():
        return None
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Nome preferido:"):
            return line.split(":", 1)[1].strip()
    return None


def infer_user_name_from_legacy_claude(workspace: Path) -> str | None:
    claude_path = workspace / "CLAUDE.md"
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


def ensure_workspace_exists(workspace: Path) -> None:
    if not workspace.exists():
        raise WorkspaceError(f"workspace não encontrado: {workspace}")
    if not workspace.is_dir():
        raise WorkspaceError(f"workspace não é diretório: {workspace}")


def looks_like_wrapper(text: str) -> bool:
    return "Leia `AGENT.md` primeiro." in text or "Compatibilidade para Claude/Cowork." in text


def backup_path_for(workspace: Path, relative: str, stamp: str) -> Path:
    safe_name = relative.replace("/", "__")
    return workspace / "_backup" / "runtime-migrate" / stamp / safe_name


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
    )


def migrate_legacy_workspace(config: WorkspaceConfig) -> dict[str, list[str] | str]:
    ensure_directories(config.workspace)
    rendered = render_files(config)
    stamp = now_stamp(config.timezone_name)
    backup_root = config.workspace / "_backup" / "runtime-migrate" / stamp
    backup_root.mkdir(parents=True, exist_ok=True)

    backed_up: list[str] = []
    created: list[str] = []
    overwritten: list[str] = []
    preserved: list[str] = []

    claude_path = config.workspace / "CLAUDE.md"
    legacy_import_path = config.workspace / "Agente" / "LEGADO-CLAUDE.md"
    if claude_path.exists():
        current = claude_path.read_text(encoding="utf-8")
        if current.strip() and not looks_like_wrapper(current) and not legacy_import_path.exists():
            legacy_import_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_import_path.write_text(current, encoding="utf-8")
            created.append("Agente/LEGADO-CLAUDE.md")

    for relative in ("AGENT.md", "CLAUDE.md", "AGENTS.md", "PRUMO-CORE.md"):
        target = config.workspace / relative
        backup_target = backup_path_for(config.workspace, relative, stamp)
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, backup_target)
            backed_up.append(relative)
            target.write_text(rendered[relative], encoding="utf-8")
            overwritten.append(relative)
        else:
            target.write_text(rendered[relative], encoding="utf-8")
            created.append(relative)

    for relative, content in rendered.items():
        if relative in ("AGENT.md", "CLAUDE.md", "AGENTS.md", "PRUMO-CORE.md"):
            continue
        target = config.workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            preserved.append(relative)
            continue
        target.write_text(content, encoding="utf-8")
        created.append(relative)

    schema_path = config.workspace / "_state" / "workspace-schema.json"
    existing_schema = read_schema(config.workspace)
    created_at = existing_schema.get("created_at")
    if schema_path.exists():
        backed_up.append("_state/workspace-schema.json")
        backup_target = backup_path_for(config.workspace, "_state/workspace-schema.json", stamp)
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(schema_path, backup_target)
    write_schema(config, preserve_created_at=created_at)
    if not schema_path.exists():
        created.append("_state/workspace-schema.json")

    return {
        "backup_root": str(backup_root),
        "backed_up": backed_up,
        "created": created,
        "overwritten": overwritten,
        "preserved": preserved,
    }


def repair_workspace(workspace: Path) -> dict[str, list[str]]:
    config = build_config_from_existing(workspace)
    ensure_directories(workspace)
    rendered = render_files(config)
    missing = detect_missing(workspace)
    recreated: list[str] = []
    reported_authorial = list(missing["authorial"])

    for relative in [*missing["generated"], *missing["derived"]]:
        content = rendered.get(relative)
        if content is None and relative == "_state/workspace-schema.json":
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
    core_path = workspace / "PRUMO-CORE.md"
    if not core_path.exists():
        return None
    for line in core_path.read_text(encoding="utf-8").splitlines():
        if "prumo_version:" in line:
            return line.split("prumo_version:", 1)[1].replace("*", "").replace(">", "").strip()
    return None


def update_briefing_state(workspace: Path, timezone_name: str) -> None:
    state_path = workspace / "_state" / "briefing-state.json"
    state = load_json(state_path)
    state["last_briefing_at"] = now_iso(timezone_name)
    state.pop("interrupted_at", None)
    state.pop("resume_point", None)
    write_json(state_path, state)


def workspace_overview(workspace: Path) -> dict:
    config = build_config_from_existing(workspace)
    schema = read_schema(workspace)
    missing = detect_missing(workspace)
    core_version = parse_core_version(workspace)
    runtime_key = semantic_version_key(RUNTIME_VERSION)
    core_key = semantic_version_key(core_version or "0")
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
        "google_integration": google_integration_summary(workspace),
        "apple_reminders": apple_reminders_summary(workspace),
        "missing": missing,
        "pauta_exists": (workspace / "PAUTA.md").exists(),
        "inbox_exists": (workspace / "INBOX.md").exists(),
        "registro_exists": (workspace / "REGISTRO.md").exists(),
    }


def append_registro(workspace: Path, origin: str, summary: str, action: str, destination: str) -> None:
    registro_path = workspace / "REGISTRO.md"
    if not registro_path.exists():
        return
    today = datetime.now().strftime("%d/%m")
    line = f"| {today} | {origin} | {summary} | {action} | {destination} |\n"
    with registro_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
