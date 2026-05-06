"""
Host adapters — symlinks de convenção de host pra .prumo/skills/ (#85).

Cria e repara adapters em .claude/skills/ e .agent/skills/ apontando
para .prumo/skills/ via symlink relativo. Fallback copy se symlink falhar.
Respeita paths não gerenciados (preserva com warning).
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
        return {"hosts_created": [], "adapters_created": 0, "skipped": []}

    skills = sorted(
        d.name for d in skills_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    if not skills:
        return {"hosts_created": [], "adapters_created": 0, "skipped": []}

    target_hosts = hosts if hosts else list(HOST_CONVENTIONS.keys())
    existing_manifest = _read_manifest(workspace)
    adapters: list[dict[str, Any]] = []
    skipped: list[str] = []
    hosts_created: list[str] = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Preservar entries de hosts não incluídos nesta chamada
    if existing_manifest and hosts:
        for entry in existing_manifest.get("adapters", []):
            if entry["host"] not in target_hosts:
                adapters.append(entry)

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

            if _is_unmanaged(adapter_path, relative_target, existing_manifest, host, skill_name):
                skipped.append(f"{convention_path}/{skill_name}")
                continue

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
        "adapters_created": len([a for a in adapters if a.get("created_at") == now]),
        "skipped": skipped,
    }


def repair_host_adapters(workspace: Path) -> dict[str, Any]:
    """Valida e repara adapters existentes. Cria se não existem."""
    skills_root = workspace / ".prumo" / "skills"

    if not skills_root.is_dir():
        return {"repaired": 0, "status": "no skills"}

    manifest = _read_manifest(workspace)

    if manifest is None:
        result = create_host_adapters(workspace)
        return {"repaired": result["adapters_created"], "status": "created from scratch"}

    repaired = 0
    needs_manifest_update = False

    skills = sorted(
        d.name for d in skills_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    managed_entries = {(e["host"], e["skill"]): e for e in manifest.get("adapters", [])}

    for host, convention_path in HOST_CONVENTIONS.items():
        host_skills_dir = workspace / convention_path
        host_skills_dir.mkdir(parents=True, exist_ok=True)

        for skill_name in skills:
            adapter_path = host_skills_dir / skill_name
            target_path = skills_root / skill_name
            relative_target = os.path.relpath(target_path, adapter_path.parent)
            entry = managed_entries.get((host, skill_name))

            if not entry:
                if adapter_path.exists() and not adapter_path.is_symlink():
                    continue  # Não gerenciado, pular
                mode = _create_adapter(adapter_path, relative_target, target_path)
                needs_manifest_update = True
                repaired += 1
                continue

            needs_repair = False
            if not adapter_path.exists():
                needs_repair = True
            elif adapter_path.is_symlink():
                if not adapter_path.resolve().exists():
                    needs_repair = True
            elif entry.get("mode") == "copy":
                # Copy mode: verificar se runtime_version diverge
                if entry.get("runtime_version") != __version__:
                    needs_repair = True

            if needs_repair:
                if adapter_path.is_symlink():
                    adapter_path.unlink()
                elif adapter_path.is_dir():
                    shutil.rmtree(adapter_path)
                _create_adapter(adapter_path, relative_target, target_path)
                needs_manifest_update = True
                repaired += 1

    if needs_manifest_update:
        _rebuild_manifest_from_filesystem(workspace, skills_root)

    return {"repaired": repaired, "status": "ok"}


def _rebuild_manifest_from_filesystem(workspace: Path, skills_root: Path) -> None:
    """Reconstrói manifest a partir dos adapters existentes no filesystem."""
    adapters: list[dict[str, Any]] = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for host, convention_path in HOST_CONVENTIONS.items():
        host_skills_dir = workspace / convention_path
        if not host_skills_dir.is_dir():
            continue
        for skill_dir in sorted(host_skills_dir.iterdir()):
            if not skill_dir.name or skill_dir.name.startswith("."):
                continue
            target_path = skills_root / skill_dir.name
            if not target_path.is_dir():
                continue
            if skill_dir.is_symlink():
                mode = "symlink"
            elif skill_dir.is_dir():
                mode = "copy"
            else:
                continue
            adapters.append({
                "host": host,
                "skill": skill_dir.name,
                "adapter_path": str(Path(convention_path) / skill_dir.name),
                "target_path": f".prumo/skills/{skill_dir.name}",
                "mode": mode,
                "runtime_version": __version__,
                "created_at": now,
            })

    _write_manifest(workspace, adapters)


def _is_unmanaged(
    adapter_path: Path,
    expected_target: str,
    manifest: dict | None,
    host: str,
    skill_name: str,
) -> bool:
    """Verifica se um path existente é não-gerenciado pelo Prumo."""
    if not adapter_path.exists() and not adapter_path.is_symlink():
        return False

    # Se é symlink pro target esperado, é gerenciado
    if adapter_path.is_symlink():
        try:
            current_target = os.readlink(str(adapter_path))
            if current_target == expected_target:
                return False
        except OSError:
            pass
        # Symlink pra outro lugar — verificar manifest
        if manifest:
            for entry in manifest.get("adapters", []):
                if entry["host"] == host and entry["skill"] == skill_name:
                    return False  # Registrado no manifest = gerenciado
        return True  # Symlink desconhecido = não tocar

    # Diretório real — verificar se está no manifest
    if manifest:
        for entry in manifest.get("adapters", []):
            if entry["host"] == host and entry["skill"] == skill_name:
                return False  # Registrado como copy = gerenciado

    return True  # Diretório não registrado = não gerenciado, preservar


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


def _read_manifest(workspace: Path) -> dict[str, Any] | None:
    manifest_path = workspace / MANIFEST_RELATIVE
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, json.JSONDecodeError, ValueError):
        return None


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
