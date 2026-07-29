"""Snapshot de arquivo curado (#262 — P8+P9 do relatório de incidente de 29/07).

Por que existe: em 27/07 uma sessão reescreveu `Prumo/Referencias/INDICE.md`
com escrita INTEGRAL querendo acrescentar quatro linhas — 48 entradas viraram
5, e o dano ficou invisível por dois dias. Todo backup que o produto tinha era
disparado por comando do runtime (`setup`, `migrate`, `repair`, `sanitize`);
nenhum cobria o caminho de edição comum. O que o produto sabe recriar sozinho
tinha cópia; o que era insubstituível não tinha nenhuma.

Onde o snapshot mora: o Prumo NÃO tem gancho na ferramenta de escrita do agente
hospedeiro, então "antes de cada escrita" só existiria como regra que o agente
precisa lembrar — a proteção que falhou. A cópia pega carona nos rituais que o
runtime já é dono (`prumo seed` e `prumo briefing`), o que dá garantia mecânica
ao custo de a cópia ficar no máximo uma sessão atrasada.

Módulo folha: importa apenas `workspace_paths`, `projetos` (só as marcas de
pulso), `faxina_thresholds` e `backup` — todos folhas. Nunca `workspace.py`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from prumo_runtime import faxina_thresholds
from prumo_runtime.backup import copy_to_backup
from prumo_runtime.projetos import PULSO_BEGIN, PULSO_END
from prumo_runtime.workspace_paths import workspace_paths

SCOPE = "curated"

# Classes de VIGILÂNCIA. O snapshot cobre todas; o alerta de encolhimento só
# faz sentido onde encolher é anomalia (Codex r1: taxonomia binária fura em
# arquivo híbrido).
FLOW = "fluxo"                 # existe pra ser drenado — encolher é o contrato
HYBRID = "hibrido"             # parte gerada, parte autoral
ACCUMULATIVE = "acumulativo"   # catálogo: encolher brusco é suspeito

# `PAUTA` esvazia pro REGISTRO, `INBOX` esvazia ao ser processado, `REGISTRO`
# rotaciona pelo `max_items`, `IDEIAS` amadurece e sai. Alarmar aqui seria
# ruído que ensina a ignorar o alarme.
_FLOW_NAMES = frozenset({"PAUTA.md", "INBOX.md", "REGISTRO.md", "IDEIAS.md"})
# `PROJETOS.md`: só o miolo dos blocos de pulso é reescrito pelo
# `projetos --sync` (exceção cirúrgica da #201); todo byte fora deles é
# autoral. O alerta mede só o autoral.
_HYBRID_NAMES = frozenset({"PROJETOS.md"})

# Teto por arquivo: acima disso a cópia diária deixa de ser barata. O que passa
# é REPORTADO, nunca descartado em silêncio.
MAX_FILE_BYTES = 512 * 1024
# Piso do alerta: em arquivo minúsculo qualquer edição é percentualmente
# enorme. Sem piso, o alarme viraria ruído no primeiro dia de workspace novo.
MIN_ALERT_BYTES = 200


def watch_class(relative_path: str) -> str:
    name = relative_path.rsplit("/", 1)[-1]
    if name in _FLOW_NAMES:
        return FLOW
    if name in _HYBRID_NAMES:
        return HYBRID
    return ACCUMULATIVE


def _flat_name(relative_path: str) -> str:
    """Convenção `__` do runtime-migrate: `a/b/c.md` → `a__b__c.md`."""
    return relative_path.replace("/", "__")


def measured_size(text: str, klass: str) -> int:
    """Bytes que o alerta vigia.

    No híbrido, o miolo dos blocos de pulso sai da conta: ele encolhe por
    contrato a cada `projetos --sync`, e contá-lo produziria falso alarme
    justamente no comando que o produto oferece.
    """
    if klass != HYBRID:
        return len(text.encode("utf-8"))
    kept: list[str] = []
    inside = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == PULSO_BEGIN:
            inside = True
            continue
        if stripped == PULSO_END:
            inside = False
            continue
        if not inside:
            kept.append(line)
    return len("".join(kept).encode("utf-8"))


def _latest_previous_stamp(scope_root: Path) -> Path | None:
    try:
        if not scope_root.is_dir():
            return None
        stamps = sorted(p for p in scope_root.iterdir() if p.is_dir() and not p.is_symlink())
    except OSError:
        return None
    return stamps[-1] if stamps else None


def _read_current(paths, errors: list[str]) -> tuple[dict[str, str], list[str]]:
    """Lê os curados existentes. Devolve (texto por path, oversized)."""
    current: dict[str, str] = {}
    oversized: list[str] = []
    for rel in paths.curated_relative_paths():
        source = paths.root / rel
        try:
            if not source.is_file() or source.is_symlink():
                continue
            if source.stat().st_size > MAX_FILE_BYTES:
                oversized.append(rel)
                continue
            current[rel] = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: {exc}")
    return current, oversized


def _read_previous(stamp_dir: Path | None, wanted: list[str]) -> dict[str, str]:
    if stamp_dir is None:
        return {}
    previous: dict[str, str] = {}
    for rel in wanted:
        copy = stamp_dir / _flat_name(rel)
        try:
            if copy.is_file():
                previous[rel] = copy.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return previous


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_alerts(
    current: dict[str, str],
    previous: dict[str, str],
    previous_stamp: Path | None,
    shrink_pct: int,
) -> list[dict]:
    alerts: list[dict] = []
    for rel, text in sorted(current.items()):
        klass = watch_class(rel)
        if klass == FLOW or rel not in previous:
            # Sem cópia anterior não há delta — só ausência de história.
            continue
        before = measured_size(previous[rel], klass)
        after = measured_size(text, klass)
        if before < MIN_ALERT_BYTES or after >= before:
            continue
        shrink = (before - after) * 100 // before
        if shrink < shrink_pct:
            continue
        alerts.append(
            {
                "path": rel,
                "watch_class": klass,
                "before_bytes": before,
                "after_bytes": after,
                "shrink_pct": shrink,
                "previous_copy": str(previous_stamp) if previous_stamp else "",
            }
        )
    return alerts


def snapshot_curated(workspace: Path, *, stamp: str, shrink_pct: int | None = None) -> dict:
    """Copia os curados pra `.prumo/backups/<SCOPE>/<stamp>/` e mede encolhimento.

    NUNCA levanta: falha de I/O entra em `errors` e o ritual segue. Backup que
    derruba o briefing é pior que o problema que ele resolve.
    """
    errors: list[str] = []
    report: dict = {
        "scope": SCOPE,
        "stamp": stamp,
        "copied": [],
        "oversized": [],
        "alerts": [],
        "errors": errors,
        "skipped": None,
    }
    try:
        workspace = Path(workspace).expanduser().resolve()
        paths = workspace_paths(workspace)
        scope_root = workspace / ".prumo" / "backups" / SCOPE

        current, oversized = _read_current(paths, errors)
        report["oversized"] = oversized

        previous_stamp = _latest_previous_stamp(scope_root)
        previous = _read_previous(previous_stamp, list(current))

        if shrink_pct is None:
            shrink_pct = faxina_thresholds.effective(workspace)["values"][
                "curated_shrink_alert_pct"
            ]
        report["alerts"] = _build_alerts(current, previous, previous_stamp, shrink_pct)

        # Nada mudou → nenhum carimbo novo. Dia sem edição não vira lixo.
        same_set = set(current) == set(previous)
        same_text = all(_digest(current[r]) == _digest(previous.get(r, "")) for r in current)
        if previous_stamp is not None and same_set and same_text:
            report["skipped"] = "sem-mudanca"
            return report

        target_root = scope_root / stamp
        target_root.mkdir(parents=True, exist_ok=True)
        for rel in sorted(current):
            try:
                copy_to_backup(paths.root / rel, target_root / _flat_name(rel))
                report["copied"].append(rel)
            except OSError as exc:
                errors.append(f"{rel}: {exc}")
    except OSError as exc:
        errors.append(str(exc))
    return report


def render_alerts(report: dict) -> str:
    """Linha por arquivo encolhido, com os dois tamanhos e onde está a cópia.

    Nomear é o ponto: só o usuário sabe que aquele índice era de fevereiro.
    """
    if not report.get("alerts"):
        return ""
    linhas = [
        "[curado] encolhimento suspeito desde a última cópia — "
        "confira antes de seguir:",
    ]
    for a in report["alerts"]:
        linhas.append(
            f"  - `{a['path']}`: {a['before_bytes']} → {a['after_bytes']} bytes "
            f"(−{a['shrink_pct']}%). Cópia anterior em `{a['previous_copy']}`."
        )
    return "\n".join(linhas)
