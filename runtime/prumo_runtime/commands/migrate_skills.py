from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.commands.setup import prompt_choice
from prumo_runtime.workspace import repair_workspace
from prumo_runtime.workspace_paths import workspace_paths


# Estados detectáveis em relação à migração de skills (#77).
STATE_ALREADY_MIGRATED = "already_migrated"
STATE_HAS_PRUMO_SKILLS = "has_prumo_skills"
STATE_HAS_PRUMO_SKILLS_OLD = "has_prumo_skills_old"
STATE_NO_SKILLS = "no_skills"
STATE_AMBIGUOUS = "ambiguous"


def detect_skills_state(workspace: Path) -> tuple[str, Path | None]:
    """Detecta em que estado o workspace está em relação à migração de skills.

    Retorna (state, source_path) onde source_path é a pasta a mover (ou None).
    """
    paths = workspace_paths(workspace)
    target = paths.skills_root  # .prumo/skills/
    legacy_skills = workspace / "Prumo" / "skills"
    legacy_skills_old = workspace / "Prumo" / "skills_OLD"

    has_target = target.is_dir() and any(target.iterdir())
    has_legacy = legacy_skills.is_dir() and any(legacy_skills.iterdir())
    has_legacy_old = legacy_skills_old.is_dir() and any(legacy_skills_old.iterdir())

    if has_target and not has_legacy and not has_legacy_old:
        return STATE_ALREADY_MIGRATED, None
    if has_target and (has_legacy or has_legacy_old):
        return STATE_AMBIGUOUS, None
    if has_legacy and has_legacy_old:
        return STATE_AMBIGUOUS, None
    if not has_target and not has_legacy and not has_legacy_old:
        return STATE_NO_SKILLS, None
    if has_legacy:
        return STATE_HAS_PRUMO_SKILLS, legacy_skills
    if has_legacy_old:
        return STATE_HAS_PRUMO_SKILLS_OLD, legacy_skills_old
    return STATE_NO_SKILLS, None


_DECISION_BLOCK = re.compile(
    r"^## (\d{4}-\d{2}-\d{2}) — (.+?)$\n(.*?)(?=^## \d{4}-\d{2}-\d{2}|\Z)",
    re.MULTILINE | re.DOTALL,
)


def relevant_decisions_summary(repo_root: Path | None = None) -> str:
    """Lê `DECISIONS.md` do repo e extrai entradas tocando `skills-distribution`
    ou `workspace-layout`.

    Implementação manual de busca por tópico no índice temático: regex captura
    cada bloco "## YYYY-MM-DD — Título" e seu corpo, e filtra pelos tópicos
    relevantes ou pela palavra "skills" no título. Retorna lista formatada.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    decisions_path = repo_root / "DECISIONS.md"
    if not decisions_path.exists():
        return "(DECISIONS.md não encontrado neste repo. Pulando consulta.)"

    text = decisions_path.read_text(encoding="utf-8")
    relevant: list[str] = []
    for match in _DECISION_BLOCK.finditer(text):
        date, title, body = match.groups()
        body_lower = body.lower()
        title_lower = title.lower()
        if (
            "skills-distribution" in body_lower
            or "workspace-layout" in body_lower
            or "skills" in title_lower
        ):
            relevant.append(f"  - {date} — {title.strip()}")
    if not relevant:
        return "(Nenhuma entrada de DECISIONS.md tocando skills-distribution ou workspace-layout.)"
    return "\n".join(relevant)


def _format_size(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} B"
    kb = byte_count / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb / 1024:.1f} MB"


def render_plan(source: Path, target: Path, workspace: Path) -> str:
    lines = ["Plano de migração:"]
    src_rel = source.relative_to(workspace) if source.is_relative_to(workspace) else source
    tgt_rel = target.relative_to(workspace) if target.is_relative_to(workspace) else target
    lines.append(f"  - Mover: `{src_rel}` → `{tgt_rel}`")
    if source.is_dir():
        files = [f for f in source.rglob("*") if f.is_file()]
        size = sum(f.stat().st_size for f in files)
        lines.append(f"  - Conteúdo: {len(files)} arquivos, {_format_size(size)}")
    lines.append("  - Backup automático em: `.prumo/backup/relocate-skills-<timestamp>/`")
    lines.append("  - Re-renderizar: `Prumo/AGENT.md`, `.prumo/system/PRUMO-CORE.md`")
    lines.append("  - Log da operação: `.prumo/logs/architectural-ops.log`")
    return "\n".join(lines)


def log_architectural_op(workspace: Path, op: str, message: str) -> None:
    """Registra uma op arquitetural em `.prumo/logs/architectural-ops.log`.

    Formato: `<ISO timestamp>\\t<op>\\t<message>\\n`. Append-only.
    """
    paths = workspace_paths(workspace)
    log_path = paths.logs_root / "architectural-ops.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(ZoneInfo("UTC")).isoformat()
    line = f"{timestamp}\t{op}\t{message}\n"
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(line)


def _execute_migration(workspace: Path, source: Path) -> dict:
    """Executa a migração propriamente dita. Pré-condição: pre-flight aprovado."""
    paths = workspace_paths(workspace)
    target = paths.skills_root

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = paths.system_root / "backup" / f"relocate-skills-{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup do source antes de mover.
    shutil.copytree(source, backup_dir / source.name)

    # Move skills pra .prumo/skills/.
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))

    # Backup e remoção dos generated pra forçar re-render via repair.
    agent_md = workspace / "Prumo" / "AGENT.md"
    core_md = paths.system_root / "system" / "PRUMO-CORE.md"
    if agent_md.exists():
        shutil.copy(agent_md, backup_dir / "Prumo-AGENT.md.bak")
        agent_md.unlink()
    if core_md.exists():
        shutil.copy(core_md, backup_dir / "PRUMO-CORE.md.bak")
        core_md.unlink()

    repair_result = repair_workspace(workspace)
    return {
        "backup_dir": backup_dir,
        "recreated": repair_result.get("recreated", []),
    }


def run_migrate_skills(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        print(f"erro: workspace não existe ou não é diretório: {workspace}")
        return 2

    state, source = detect_skills_state(workspace)
    paths = workspace_paths(workspace)
    target = paths.skills_root

    # Idempotência: já migrado.
    if state == STATE_ALREADY_MIGRATED:
        print("Workspace já tem skills em `.prumo/skills/`. Nada a fazer.")
        return 0

    # Sem skills locais.
    if state == STATE_NO_SKILLS:
        print("Workspace não tem skills locais (nem em `Prumo/skills/`, `Prumo/skills_OLD/`, ou `.prumo/skills/`).")
        print("Rode `prumo setup` (workspace novo) ou `prumo migrate` (workspace legacy) pra instalar.")
        return 0

    # Estado ambíguo exige intervenção humana.
    if state == STATE_AMBIGUOUS:
        print("Estado ambíguo: encontrei skills em mais de um lugar.")
        for candidate in [
            workspace / "Prumo" / "skills",
            workspace / "Prumo" / "skills_OLD",
            target,
        ]:
            if candidate.is_dir() and any(candidate.iterdir()):
                print(f"  - {candidate.relative_to(workspace) if candidate.is_relative_to(workspace) else candidate}")
        print("Limpe manualmente antes de migrar. Não vou adivinhar qual fonte usar.")
        return 1

    # Estado migrável: HAS_PRUMO_SKILLS ou HAS_PRUMO_SKILLS_OLD.
    assert source is not None  # garantia do detect_skills_state
    print("Migração de skills (#77): mover de `Prumo/` pra `.prumo/`.")
    print("")
    print("Decisões arquiteturais relevantes em DECISIONS.md:")
    print(relevant_decisions_summary())
    print("")
    print(render_plan(source, target, workspace))
    print("")

    if getattr(args, "yes", False):
        print("[--yes informada: prosseguindo sem prompt de confirmação.]")
        confirmed = True
    else:
        choice = prompt_choice(
            "Aplicar migração agora?",
            {"a": "Sim, mover skills e re-renderizar", "b": "Cancelar"},
            default="b",
        )
        confirmed = choice == "a"

    if not confirmed:
        print("Migração cancelada. Nada foi alterado.")
        return 0

    result = _execute_migration(workspace, source)
    backup_dir = result["backup_dir"]
    recreated = result["recreated"]

    log_architectural_op(
        workspace,
        "relocate-skills",
        f"{source.name} -> .prumo/skills/. backup={backup_dir.name}. recreated={len(recreated)}",
    )

    print("Migração concluída.")
    print(f"  - Skills agora em: `.prumo/skills/`")
    print(f"  - Backup: `{backup_dir.relative_to(workspace)}`")
    if recreated:
        print(f"  - Re-renderizados: {', '.join(recreated)}")
    print(f"  - Log: `.prumo/logs/architectural-ops.log`")
    return 0
