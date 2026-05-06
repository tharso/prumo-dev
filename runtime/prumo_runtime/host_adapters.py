"""
Host adapters — symlinks de convenção de host pra .prumo/skills/ (#85).

Cria e repara adapters em .claude/skills/ e .agent/skills/ apontando
para .prumo/skills/ via symlink relativo. Fallback copy se symlink falhar.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Any

from prumo_runtime import __version__

HOST_CONVENTIONS: dict[str, str] = {
    "claude": ".claude/skills",
    "antigravity": ".agent/skills",
}

MANIFEST_RELATIVE = ".prumo/state/host-skills.json"


def create_host_adapters(
    workspace: Path,
    *,
    hosts: list[str] | None = None,
) -> dict[str, Any]:
    """Cria adapters de host apontando pra .prumo/skills/."""
    skills_root = workspace / ".prumo" / "skills"
    if not skills_root.is_dir():
        return {"hosts_created": [], "adapters_created": 0}

    skills = sorted(
        d.name for d in skills_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    if not skills:
        return {"hosts_created": [], "adapters_created": 0}

    target_hosts = hosts if hosts else list(HOST_CONVENTIONS.keys())
    adapters: list[dict[str, Any]] = []
    hosts_created: list[str] = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for host in target_hosts:
        if host not in HOST_CONVENTIONS:
            continue
        convention_path = HOST_CONVENTIONS[host]
        host_skills_dir = workspace / convention_path
        host_skills_dir.mkdir(parents=True, exist_ok=True)
        hosts_created.append(host)

        for skill_name in skills:
            adapter_path = host_skills_dir / skill_name
            target_path = skills_root / skill_name
            relative_target = os.path.relpath(target_path, adapter_path.parent)

            mode = _create_adapter(adapter_path, relative_target, target_path)
            adapters.append({
                "host": host,
                "skill": skill_name,
                "adapter_path": str(Path(convention_path) / skill_name),
                "target_path": f".prumo/skills/{skill_name}",
                "mode": mode,
                "runtime_version": __version__,
                "created_at": now,
            })

    _write_manifest(workspace, adapters)
    return {
        "hosts_created": hosts_created,
        "adapters_created": len(adapters),
    }


def repair_host_adapters(workspace: Path) -> dict[str, Any]:
    """Valida e repara adapters existentes. Cria se não existem."""
    manifest_path = workspace / MANIFEST_RELATIVE
    skills_root = workspace / ".prumo" / "skills"

    if not skills_root.is_dir():
        return {"repaired": 0, "status": "no skills"}

    if not manifest_path.exists():
        result = create_host_adapters(workspace)
        return {"repaired": result["adapters_created"], "status": "created from scratch"}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repaired = 0

    skills = sorted(
        d.name for d in skills_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    for host, convention_path in HOST_CONVENTIONS.items():
        host_skills_dir = workspace / convention_path
        host_skills_dir.mkdir(parents=True, exist_ok=True)

        for skill_name in skills:
            adapter_path = host_skills_dir / skill_name
            target_path = skills_root / skill_name
            relative_target = os.path.relpath(target_path, adapter_path.parent)

            needs_repair = False
            if not adapter_path.exists():
                needs_repair = True
            elif adapter_path.is_symlink():
                if not adapter_path.resolve().exists():
                    needs_repair = True
            # copy adapters: check if target has newer content
            elif adapter_path.is_dir() and not adapter_path.is_symlink():
                pass  # copy mode — refresh handled by full recreate

            if needs_repair:
                if adapter_path.is_symlink():
                    adapter_path.unlink()
                elif adapter_path.is_dir():
                    shutil.rmtree(adapter_path)
                _create_adapter(adapter_path, relative_target, target_path)
                repaired += 1

    if repaired > 0:
        create_host_adapters(workspace)

    return {"repaired": repaired, "status": "ok"}


def _create_adapter(adapter_path: Path, relative_target: str, absolute_target: Path) -> str:
    """Cria symlink ou copy. Retorna mode."""
    if adapter_path.is_symlink():
        adapter_path.unlink()
    elif adapter_path.is_dir():
        shutil.rmtree(adapter_path)

    try:
        os.symlink(relative_target, str(adapter_path))
        return "symlink"
    except OSError:
        shutil.copytree(str(absolute_target), str(adapter_path))
        return "copy"


def _write_manifest(workspace: Path, adapters: list[dict[str, Any]]) -> None:
    manifest_path = workspace / MANIFEST_RELATIVE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": "1.0",
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "runtime_version": __version__,
        "adapters": adapters,
    }
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
