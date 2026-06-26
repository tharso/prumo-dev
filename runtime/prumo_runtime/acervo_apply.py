"""Execução segura das decisões do `acervo` (#125).

Aplica o relatório `prumo_acervo_report.v1`:
- `include_pauta` → anexa o item à `PAUTA.md` (seção Horizonte). Não-destrutivo.
- `attack_now`   → devolvido ao agente (julgamento, não mecânica).
- `delete`       → **arquiva, não apaga**: re-enumera pra localizar o item por
                   `content_hash` + `source_path`, bloqueia se mudou/sumiu/é
                   ambíguo/escapa de `Prumo/`/é operacional, registra no
                   `REGISTRO.md` e move pra `Prumo/Arquivo/Acervo/`. Deleção
                   permanente só com `permanent=True` (pedido explícito).

Travas (Codex, rodada 2): hash divergente, ocorrência ambígua, path fora de
`Prumo/`, arquivo inexistente, referência operacional inapagável, e registro
antes da remoção.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from prumo_runtime.acervo import (
    OPERATIONAL_REFERENCIAS,
    SCHEMA_VERSION,
    enumerate_limbo,
)
from prumo_runtime.workspace import read_text
from prumo_runtime.workspace_paths import workspace_paths

REPORT_SCHEMA = "prumo_acervo_report.v1"


class AcervoSafetyError(Exception):
    """Remoção bloqueada por uma trava de segurança."""


def _within_user_root(paths, source_path: str) -> Path:
    resolved = (paths.root / source_path).resolve()
    try:
        resolved.relative_to(paths.user_root)
    except ValueError:
        raise AcervoSafetyError(f"path fora de Prumo/: {source_path}")
    return resolved


def _registro_row(title: str, destino: str, today: date) -> str:
    stamp = f"{today.day:02d}/{today.month:02d}"
    safe_title = title.replace("|", "/").strip()
    return f"| {stamp} | ACERVO | {safe_title} | Arquivado | {destino} |\n"


def _append_registro(paths, title: str, destino: str, today: date) -> None:
    registro = paths.registro
    existing = read_text(registro)
    if existing and not existing.endswith("\n"):
        existing += "\n"
    registro.parent.mkdir(parents=True, exist_ok=True)
    registro.write_text(existing + _registro_row(title, destino, today), encoding="utf-8")


def _quarantine_dir(paths) -> Path:
    return paths.arquivo_root / "Acervo"


def _archive_fragment(paths, current: dict, title: str, today: date, permanent: bool) -> str:
    src = _within_user_root(paths, current["source_path"])
    lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
    start = current["line_start"] - 1
    end = current["line_end"]
    if start < 0 or end > len(lines) or start >= end:
        raise AcervoSafetyError(f"linhas fora de alcance em {current['source_path']}")
    removed = "".join(lines[start:end])
    remaining = lines[:start] + lines[end:]

    if permanent:
        destino = "permanente"
    else:
        qdir = _quarantine_dir(paths)
        qdir.mkdir(parents=True, exist_ok=True)
        quarantine = qdir / "quarentena-fragmentos.md"
        block = f"\n## {today.isoformat()} — de {current['source_path']}\n\n{removed.rstrip()}\n"
        quarantine.write_text(read_text(quarantine) + block, encoding="utf-8")
        destino = paths.relative(qdir)

    # Registro ANTES de tocar o original (ASSERT do core).
    _append_registro(paths, title, destino, today)
    src.write_text("".join(remaining), encoding="utf-8")
    return destino


def _archive_file(paths, current: dict, title: str, today: date, permanent: bool) -> str:
    src = _within_user_root(paths, current["source_path"])
    if src.name in OPERATIONAL_REFERENCIAS:
        raise AcervoSafetyError(f"referência operacional é inapagável: {src.name}")
    destino = "permanente" if permanent else paths.relative(_quarantine_dir(paths))
    _append_registro(paths, title, destino, today)
    if permanent:
        src.unlink()
        return destino
    qdir = _quarantine_dir(paths)
    qdir.mkdir(parents=True, exist_ok=True)
    src.replace(qdir / src.name)
    return destino


def _find_current(current_items: list[dict], item: dict) -> dict:
    matches = [
        c for c in current_items
        if c["content_hash"] == item.get("content_hash")
        and c["source_path"] == item.get("source_path")
    ]
    if not matches:
        raise AcervoSafetyError(
            "item mudou ou sumiu desde a geração (hash não bate) — revise antes de excluir"
        )
    if len(matches) > 1:
        raise AcervoSafetyError("ocorrência ambígua: o mesmo item aparece em mais de um lugar")
    return matches[0]


def _append_pauta_horizonte(paths, title: str, comment: str | None) -> None:
    pauta = paths.pauta
    text = read_text(pauta)
    bullet = f"- {title}"
    if comment:
        bullet += f" ({comment})"
    lines = text.splitlines()
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.strip().startswith("## ") and "Horizonte" in line:
            out.append(bullet)
            inserted = True
    if not inserted:
        if out and out[-1].strip():
            out.append("")
        out.append("## Horizonte")
        out.append(bullet)
    pauta.parent.mkdir(parents=True, exist_ok=True)
    pauta.write_text("\n".join(out) + "\n", encoding="utf-8")


def apply_report(workspace: Path, report: dict, *, permanent: bool = False, today: date | None = None) -> dict:
    """Aplica um relatório do acervo. Itens bloqueados não abortam o lote."""
    if report.get("schema") != REPORT_SCHEMA:
        raise AcervoSafetyError(f"schema inesperado: {report.get('schema')!r} (esperado {REPORT_SCHEMA})")
    today = today or date.today()
    workspace = workspace.expanduser().resolve()
    paths = workspace_paths(workspace)

    # Snapshot atual = fonte de verdade pra localizar/validar itens.
    current_items = enumerate_limbo(workspace, today=today)["items"]

    archived, included, for_agent, blocked = [], [], [], []
    for item in report.get("items", []):
        verb = item.get("verb")
        title = item.get("title") or item.get("source_path") or "(sem título)"
        try:
            if verb == "attack_now":
                for_agent.append(item)
            elif verb == "include_pauta":
                _append_pauta_horizonte(paths, title, item.get("comment"))
                included.append(title)
            elif verb == "delete":
                current = _find_current(current_items, item)
                if current["source_kind"] == "referencia":
                    destino = _archive_file(paths, current, title, today, permanent)
                else:
                    destino = _archive_fragment(paths, current, title, today, permanent)
                archived.append({"title": title, "destino": destino})
            else:
                blocked.append({"title": title, "reason": f"verbo desconhecido: {verb!r}"})
        except AcervoSafetyError as exc:
            blocked.append({"title": title, "reason": str(exc)})

    return {
        "schema_version": SCHEMA_VERSION,
        "archived": archived,
        "included": included,
        "for_agent": for_agent,
        "blocked": blocked,
    }
