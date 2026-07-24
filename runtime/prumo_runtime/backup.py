"""Backup do workspace: cópia, movimento e poda sob `.prumo/backups/`.

Módulo folha — nunca importa `workspace.py`. Convenção canônica de destino:
`.prumo/backups/<scope>/<timestamp>/` (#81 P3.8).

Regra de ouro (#178, épico #177): backup nunca contém backup. O
`backup_ignore` fica sempre ativo nas cópias de diretório porque os vetores
reais de aninhamento eram árvores legítimas de origem carregando `.prumo/`
ou `archive/backups/` pra dentro da cópia. O conteúdo ignorado não se perde:
quem move (`move_with_backup`) leva a árvore inteira pro destino — só a
cópia redundante de backup é que não nasce.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

# Mesmo limiar do `/fim` (fim.BACKUP_EXPIRY_DAYS): backup mais velho que
# isso é poeira. A poda só roda quando chamada (sanitize) — nunca automática.
BACKUP_EXPIRY_DAYS = 90

_BACKUP_DIR_NAMES = {"backup", "backups"}
def backup_ignore(dirpath: str, names: list[str]) -> set[str]:
    """Callable de `ignore` pro copytree: backup nunca copia `.prumo` nem
    diretórios de backup aninhados. Cirúrgico de verdade (Codex, série #178):
    a exclusão de `backup(s)` só vale nos contextos TÉCNICOS documentados —
    `.prumo/`, `.prumo/system/` (legado pré-#81) e `<state>/archive/`
    (snapshots, flat `_state/` incluso). `backups` em pasta comum do usuário
    (ex.: `Referencias/backups/` ou `Referencias/archive/backups/`) continua
    sendo copiado — basename sozinho não caracteriza contexto técnico.
    """
    p = Path(dirpath)
    parent, grand = p.name, p.parent.name
    technical_context = (
        parent == ".prumo"
        or (parent == "system" and grand == ".prumo")
        or (parent == "archive" and grand in {"state", "_state"})
    )
    ignored = {name for name in names if name == ".prumo"}
    if technical_context:
        ignored.update(name for name in names if name in _BACKUP_DIR_NAMES)
    return ignored


def backup_path_for(workspace: Path, relative: str, stamp: str) -> Path:
    safe_name = relative.replace("/", "__")
    return workspace / ".prumo" / "backups" / "runtime-migrate" / stamp / safe_name


def copy_to_backup(source: Path, backup_target: Path) -> None:
    """Copia preservando symlinks COMO links (Codex série r2): dereferenciar
    permitiria a um link de nome neutro contornar o `backup_ignore` e trazer
    `.prumo/backups` (ou qualquer diretório externo) pra dentro da cópia."""
    backup_target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        backup_target.symlink_to(source.readlink())
        return
    if source.is_dir():
        shutil.copytree(source, backup_target, ignore=backup_ignore, symlinks=True)
        return
    shutil.copy2(source, backup_target, follow_symlinks=False)


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


def iter_backup_roots(workspace: Path) -> list[Path]:
    """Raízes onde backups vivem: canônica + legados documentados (#81)."""
    return [
        workspace / ".prumo" / "backups",
        workspace / ".prumo" / "backup",
        workspace / ".prumo" / "system" / "backup",
    ]


def _prunable_entries(root: Path) -> list[Path]:
    # Na raiz canônica a unidade de poda é o carimbo (`<scope>/<timestamp>`);
    # nos legados, sem estrutura garantida, é o filho direto. Scope symlinkado
    # não é atravessado: `glob("*/*")` seguiria o link e a poda apagaria
    # conteúdo fora do backup (Codex, série #178).
    if root.name == "backups":
        entries: list[Path] = []
        for scope in sorted(root.glob("*")):
            if scope.is_symlink() or not scope.is_dir():
                continue
            entries.extend(sorted(scope.glob("*")))
        return entries
    return sorted(root.glob("*"))


def prune_expired_backups(
    workspace: Path,
    *,
    today: date,
    expiry_days: int = BACKUP_EXPIRY_DAYS,
) -> list[str]:
    """Remove entradas de backup mais velhas que `expiry_days`.

    Idade por mtime (lstat pra symlink — a idade é do link, e apagar o link
    nunca segue até o alvo). Retorna paths relativos removidos, ordenados.
    """
    removed: list[str] = []
    for root in iter_backup_roots(workspace):
        # Root symlinkado não é raiz de backup: recusar sem atravessar —
        # deletar através do link apagaria conteúdo externo ao backup.
        if root.is_symlink() or not root.is_dir():
            continue
        for entry in _prunable_entries(root):
            stat = entry.lstat() if entry.is_symlink() else entry.stat()
            age = (today - date.fromtimestamp(stat.st_mtime)).days
            if age <= expiry_days:
                continue
            if entry.is_symlink():
                entry.unlink()
            elif entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            removed.append(str(entry.relative_to(workspace)))
        if root.name == "backups":
            for scope in root.glob("*"):
                if scope.is_symlink():
                    continue
                if scope.is_dir() and not any(scope.iterdir()):
                    scope.rmdir()
    return sorted(removed)
