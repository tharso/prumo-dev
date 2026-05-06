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
_MANAGED_MARKER = ".prumo-managed"


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
        for entry in _safe_adapters_list(existing_manifest):
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
    managed_set: set[tuple[str, str]] = set()

    skills = sorted(
        d.name for d in skills_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    managed_entries = {(e["host"], e["skill"]): e for e in _safe_adapters_list(manifest)}

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
                _create_adapter(adapter_path, relative_target, target_path)
                managed_set.add((host, skill_name))
                needs_manifest_update = True
                repaired += 1
                continue

            managed_set.add((host, skill_name))

            needs_repair = False
            if not adapter_path.exists():
                needs_repair = True
            elif adapter_path.is_symlink():
                if not adapter_path.resolve().exists():
                    needs_repair = True
            elif entry.get("mode") == "copy":
                if entry.get("runtime_version") != __version__:
                    needs_repair = True

            if needs_repair:
                if adapter_path.is_symlink():
                    adapter_path.unlink()
                elif adapter_path.is_dir():
                    # Checar marcador antes de destruir — dir sem marcador
                    # pode ser conteúdo do usuário substituindo cópia gerenciada.
                    # Manifest stale não basta pra autorizar destruição (#89).
                    if not (adapter_path / _MANAGED_MARKER).is_file():
                        managed_set.discard((host, skill_name))
                        needs_manifest_update = True
                        continue
                    shutil.rmtree(adapter_path)
                _create_adapter(adapter_path, relative_target, target_path)
                needs_manifest_update = True
                repaired += 1

    if needs_manifest_update:
        _rebuild_manifest(workspace, skills_root, managed_set)

    return {"repaired": repaired, "status": "ok"}


def _rebuild_manifest(
    workspace: Path,
    skills_root: Path,
    managed_set: set[tuple[str, str]],
) -> None:
    """Reconstrói manifest apenas com adapters gerenciados."""
    adapters: list[dict[str, Any]] = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for host, convention_path in HOST_CONVENTIONS.items():
        host_skills_dir = workspace / convention_path
        if not host_skills_dir.is_dir():
            continue
        for skill_dir in sorted(host_skills_dir.iterdir()):
            if (host, skill_dir.name) not in managed_set:
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
    """Verifica se um path existente é não-gerenciado pelo Prumo.

    Regra de produto: nunca sobrescrever customização do usuário.
    - Symlinks: confia no manifest ou no target esperado.
    - Diretórios reais: precisa de marcador explícito (.prumo-managed)
      pra distinguir cópia do Prumo de dir do usuário. Manifest stale
      não é autoridade suficiente (#89 Finding 3).
    """
    if not adapter_path.exists() and not adapter_path.is_symlink():
        return False

    if adapter_path.is_symlink():
        try:
            current_target = os.readlink(str(adapter_path))
            if current_target == expected_target:
                return False
        except OSError:
            pass
        if manifest:
            for entry in _safe_adapters_list(manifest):
                if entry["host"] == host and entry["skill"] == skill_name:
                    return False
        return True

    # Diretório real (não symlink): verificar marcador explícito.
    # Manifest stale NÃO basta — o usuário pode ter substituído o adapter
    # por dir próprio enquanto o manifest ainda registra como gerenciado.
    if adapter_path.is_dir():
        if (adapter_path / _MANAGED_MARKER).is_file():
            return False
        return True

    return True


def _create_adapter(adapter_path: Path, relative_target: str, absolute_target: Path) -> str:
    """Cria symlink ou copy. Retorna mode.

    Em copy mode, escreve marcador `.prumo-managed` dentro do diretório
    copiado pra distinguir cópia gerenciada de diretório do usuário (#89).
    """
    if adapter_path.is_symlink():
        adapter_path.unlink()
    elif adapter_path.is_dir():
        shutil.rmtree(adapter_path)

    try:
        os.symlink(relative_target, str(adapter_path))
        return "symlink"
    except OSError:
        shutil.copytree(str(absolute_target), str(adapter_path))
        (adapter_path / _MANAGED_MARKER).write_text(
            f"managed by prumo runtime {__version__}\n",
            encoding="utf-8",
        )
        return "copy"


def _safe_adapters_list(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai lista de adapters do manifest com validação de shape."""
    adapters = manifest.get("adapters")
    if not isinstance(adapters, list):
        return []
    return [
        e for e in adapters
        if isinstance(e, dict)
        and isinstance(e.get("host"), str) and e["host"]
        and isinstance(e.get("skill"), str) and e["skill"]
    ]


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
