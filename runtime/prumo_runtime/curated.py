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
import json
from datetime import datetime, timezone
from pathlib import Path

from prumo_runtime import faxina_thresholds
from prumo_runtime.backup import copy_to_backup, iter_backup_roots
from prumo_runtime.projetos import PULSO_BEGIN, PULSO_END
from prumo_runtime.workspace_paths import workspace_paths

SCOPE = "curated"
MANIFEST_NAME = "_manifest.json"
MANIFEST_SCHEMA = "prumo_curated_snapshot.v1"

# Classes de VIGILÂNCIA. O snapshot cobre todas; o alerta de encolhimento só
# faz sentido onde encolher é anomalia (Codex, design r1: taxonomia binária
# fura em arquivo híbrido).
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
# Sumiço completo é 100% de encolhimento — o caso mais grave, não o mais leve.
GONE = "ausente"


def watch_class(relative_path: str) -> str:
    name = relative_path.rsplit("/", 1)[-1]
    if name in _FLOW_NAMES:
        return FLOW
    if name in _HYBRID_NAMES:
        return HYBRID
    return ACCUMULATIVE


def _flat_name(relative_path: str) -> str:
    """Convenção `__` do runtime-migrate: `a/b/c.md` → `a__b__c.md`.

    NÃO é bijetiva (`a/b.md` e `a__b.md` colidem), e por isso o caminho de
    volta é o manifesto — nunca o nome do arquivo (mesma lição da sanitize).
    """
    return relative_path.replace("/", "__")


def _pulso_partition(text: str) -> tuple[str, str | None]:
    """Devolve (texto fora dos blocos de pulso, erro de integridade).

    Estrutura inválida — `BEGIN` aninhado, `END` órfão, `BEGIN` sem fechar —
    é FALHA CONSERVADORA: devolve o texto inteiro e nomeia o erro. Excluir o
    sufixo de um marcador órfão faria conteúdo autoral sumir da conta sem
    alarme nenhum, que é o oposto do propósito deste módulo (Codex, 262D-2).
    """
    kept: list[str] = []
    inside = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == PULSO_BEGIN:
            if inside:
                return text, "bloco de pulso aninhado"
            inside = True
            continue
        if stripped == PULSO_END:
            if not inside:
                return text, "fim de bloco de pulso sem começo"
            inside = False
            continue
        if not inside:
            kept.append(line)
    if inside:
        return text, "bloco de pulso aberto sem fechar"
    return "".join(kept), None


def measured_size(text: str, klass: str) -> int:
    """Bytes que o alerta vigia.

    No híbrido, o miolo dos blocos de pulso sai da conta: ele encolhe por
    contrato a cada `projetos --sync`, e contá-lo produziria falso alarme
    justamente no comando que o produto oferece.
    """
    if klass != HYBRID:
        return len(text.encode("utf-8"))
    kept, _ = _pulso_partition(text)
    return len(kept.encode("utf-8"))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _under_backup_root(workspace: Path, source: Path) -> bool:
    """Origem que cai dentro de qualquer raiz de backup não é conteúdo de
    trabalho — copiá-la aninharia backup em backup (#178). Compara os
    caminhos RESOLVIDOS, porque o vetor real é `Referencias/` ser symlink
    pra dentro de `.prumo/backups/` (Codex, 262D-7)."""
    try:
        resolved = source.resolve()
    except OSError:
        return True
    for root in iter_backup_roots(workspace):
        try:
            resolved.relative_to(root.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


def _has_symlink_ancestor(workspace: Path, relative: str) -> bool:
    """Cerca da leitura, no molde do `_require_clean_target` da semente
    (#189): nenhum componente entre o workspace e a origem pode ser link."""
    probe = workspace
    for part in Path(relative).parts:
        probe = probe / part
        try:
            if probe.is_symlink():
                return True
        except OSError:
            return True
    return False


def _read_current(paths, errors: list[str]) -> tuple[dict[str, str], list[str]]:
    """Lê os curados existentes. Devolve (texto por path, oversized)."""
    current: dict[str, str] = {}
    oversized: list[str] = []
    for rel in paths.curated_relative_paths():
        source = paths.root / rel
        try:
            if _has_symlink_ancestor(paths.root, rel) or _under_backup_root(paths.root, source):
                errors.append(f"{rel}: caminho atravessa link ou cai dentro do backup")
                continue
            if not source.is_file():
                continue
            if source.stat().st_size > MAX_FILE_BYTES:
                oversized.append(rel)
                continue
            current[rel] = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: {exc}")
    return current, oversized


def _manifest_of(stamp_dir: Path) -> dict | None:
    try:
        raw = json.loads((stamp_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or raw.get("schema") != MANIFEST_SCHEMA:
        return None
    if not isinstance(raw.get("files"), dict):
        return None
    return raw


def _latest_previous(scope_root: Path) -> tuple[Path | None, dict | None]:
    """Escolhe o carimbo anterior pelo instante UTC do manifesto, NUNCA pela
    ordem lexicográfica do nome: relógio que recua (fuso, DST) produziria nome
    menor que o de um snapshot mais velho (Codex, 262D-3)."""
    try:
        if not scope_root.is_dir():
            return None, None
        candidates = [p for p in scope_root.iterdir() if p.is_dir() and not p.is_symlink()]
    except OSError:
        return None, None
    melhor: tuple[str, Path, dict] | None = None
    for stamp_dir in candidates:
        manifest = _manifest_of(stamp_dir)
        if manifest is None:
            continue
        captured = str(manifest.get("captured_at_utc", ""))
        if melhor is None or captured > melhor[0]:
            melhor = (captured, stamp_dir, manifest)
    if melhor is None:
        return None, None
    return melhor[1], melhor[2]


def _read_previous(stamp_dir: Path | None, manifest: dict | None) -> dict[str, str]:
    """Inventário COMPLETO do snapshot anterior — não só os paths que existem
    agora. Ler apenas a interseção com o presente fazia o arquivo apagado
    sumir dos dois lados e o dedupe declarar "sem mudança" justamente no caso
    mais grave (Codex, 262D-1)."""
    if stamp_dir is None or manifest is None:
        return {}
    previous: dict[str, str] = {}
    for flat, rel in manifest["files"].items():
        copy = stamp_dir / str(flat)
        try:
            if copy.is_file():
                previous[str(rel)] = copy.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return previous


def _build_alerts(
    current: dict[str, str],
    previous: dict[str, str],
    previous_stamp: Path | None,
    shrink_pct: int,
) -> list[dict]:
    alerts: list[dict] = []
    for rel in sorted(set(current) | set(previous)):
        klass = watch_class(rel)
        if klass == FLOW or rel not in previous:
            # Sem cópia anterior não há delta — só ausência de história.
            continue
        before = measured_size(previous[rel], klass)
        if before < MIN_ALERT_BYTES:
            continue
        if rel not in current:
            # Sumiu inteiro: o caso mais grave, não um caso a ignorar.
            alerts.append(
                {
                    "path": rel,
                    "watch_class": klass,
                    "before_bytes": before,
                    "after_bytes": 0,
                    "shrink_pct": 100,
                    "state": GONE,
                    "previous_copy": str(previous_stamp) if previous_stamp else "",
                }
            )
            continue
        after = measured_size(current[rel], klass)
        if after >= before:
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
                "state": "encolheu",
                "previous_copy": str(previous_stamp) if previous_stamp else "",
            }
        )
    return alerts


def _integrity_errors(current: dict[str, str]) -> list[str]:
    problemas = []
    for rel, text in sorted(current.items()):
        if watch_class(rel) != HYBRID:
            continue
        _, erro = _pulso_partition(text)
        if erro:
            problemas.append(f"{rel}: {erro} — alerta medido sobre o arquivo inteiro")
    return problemas


def _unique_stamp_dir(scope_root: Path, stamp: str) -> Path:
    """Carimbo colidido não sobrescreve fotografia anterior: ganha sufixo."""
    candidate = scope_root / stamp
    suffix = 2
    while candidate.exists():
        candidate = scope_root / f"{stamp}-{suffix}"
        suffix += 1
    return candidate


def snapshot_curated(
    workspace: Path, *, stamp: str | None = None, shrink_pct: int | None = None
) -> dict:
    """Copia os curados pra `.prumo/backups/<SCOPE>/<stamp>/` e mede encolhimento.

    O carimbo nasce AQUI, em UTC, e não do fuso configurado: ele é só rótulo
    de diretório — a ordem cronológica vem do `captured_at_utc` do manifesto.
    Assim o snapshot não depende de `build_config_from_existing`, e workspace
    sem identidade canônica ganha cópia em vez de exceção.

    NUNCA levanta: qualquer falha entra em `errors` e o ritual segue. Backup
    que derruba o briefing é pior que o problema que ele resolve.
    """
    if stamp is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
        errors.extend(_integrity_errors(current))

        previous_stamp, previous_manifest = _latest_previous(scope_root)
        previous = _read_previous(previous_stamp, previous_manifest)

        if shrink_pct is None:
            shrink_pct = faxina_thresholds.effective(workspace)["values"][
                "curated_shrink_alert_pct"
            ]
        report["alerts"] = _build_alerts(current, previous, previous_stamp, shrink_pct)

        # Coleta incompleta nunca vira baseline nem justifica pular: promover
        # um retrato furado apagaria a comparação futura (Codex, 262D-1).
        complete = not errors and not oversized
        previous_complete = bool(previous_manifest and previous_manifest.get("complete"))
        unchanged = set(current) == set(previous) and all(
            _digest(current[r]) == _digest(previous.get(r, "")) for r in current
        )
        if previous_stamp is not None and complete and previous_complete and unchanged:
            report["skipped"] = "sem-mudanca"
            return report

        target_root = _unique_stamp_dir(scope_root, stamp)
        target_root.mkdir(parents=True)
        gravados: dict[str, str] = {}
        for rel in sorted(current):
            try:
                copy_to_backup(paths.root / rel, target_root / _flat_name(rel))
                report["copied"].append(rel)
                gravados[_flat_name(rel)] = rel
            except (OSError, ValueError) as exc:
                errors.append(f"{rel}: {exc}")
        report["stamp"] = target_root.name
        (target_root / MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "schema": MANIFEST_SCHEMA,
                    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                    "complete": complete and len(gravados) == len(current),
                    "files": gravados,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 — boundary: o ritual nunca cai por causa do backup
        errors.append(f"{type(exc).__name__}: {exc}")
    return report


def render_report(report: dict) -> str:
    """Linhas pro usuário: encolhimento, o que não coube e o que falhou.

    Nomear é o ponto — só o usuário sabe que aquele índice era de fevereiro —
    e `errors`/`oversized` também aparecem: são exatamente os arquivos que
    NÃO ganharam cópia, o pior momento pra ficar calado (Codex, 262D-5).
    """
    linhas: list[str] = []
    for a in report.get("alerts", []):
        if not linhas:
            linhas.append(
                "[curado] mudança suspeita desde a última cópia — confira antes de seguir:"
            )
        if a.get("state") == GONE:
            linhas.append(
                f"  - `{a['path']}`: SUMIU (tinha {a['before_bytes']} bytes). "
                f"Cópia em `{a['previous_copy']}`."
            )
        else:
            linhas.append(
                f"  - `{a['path']}`: {a['before_bytes']} → {a['after_bytes']} bytes "
                f"(−{a['shrink_pct']}%). Cópia anterior em `{a['previous_copy']}`."
            )
    naocopiados = list(report.get("oversized", []))
    if naocopiados:
        linhas.append("[curado] acima do teto de tamanho, SEM cópia:")
        linhas.extend(f"  - `{rel}`" for rel in naocopiados)
    if report.get("errors"):
        linhas.append("[curado] falhas no snapshot (o ritual seguiu):")
        linhas.extend(f"  - {erro}" for erro in report["errors"])
    return "\n".join(linhas)
