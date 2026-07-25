"""Panorama local estruturado — a semente determinística do briefing (#197).

O agente pagava duas vezes pela mesma informação: o runtime montava o painel
e o procedure mandava reler `PAUTA.md`/`INBOX.md` integrais mesmo assim. Este
módulo entrega o bloco `local_panorama` (versionado) com TUDO que o panorama
local consome dos arquivos — itens por seção incluindo `Hibernando`, marker
de cobrança parseado com fail-open, cauda do `REGISTRO.md` (ponte
associativa), contagem do INBOX e sinais mecânicos de faxina — e o bloco
`payload_completeness` por fonte: o agente confia na semente fonte a fonte, e
faz fallback POR FONTE incompleta, nunca releitura integral por alerta
técnico genérico.

Orçamento do contrato (r1 da issue: paridade lossless que embrulha a PAUTA
inteira troca o prato, não a refeição): cada item carrega `display_text`
(exibição, teto de `_DISPLAY_MAX_CHARS`) e `text` (a LINHA integral do item,
contexto-sob-sinalização pra curadoria/ponte associativa — nunca o arquivo
inteiro); a cauda do REGISTRO é limitada a `_REGISTRO_TAIL_LINES` linhas;
prosa fora de itens (headers, comentários soltos) fica de fora por design.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from prumo_runtime.pauta_parsing import cobrar_state, extract_section

PANORAMA_SCHEMA_VERSION = "prumo_local_panorama.v1"

PAUTA_SECTIONS: tuple[tuple[str, str], ...] = (
    ("quente", "Quente"),
    ("em_andamento", "Em andamento"),
    ("agendado", "Agendado"),
    ("hibernando", "Hibernando"),
)

_DISPLAY_MAX_CHARS = 200
_REGISTRO_TAIL_LINES = 10
_PROCESSED_STALE_DAYS = 14


def _mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(
            timespec="seconds"
        )
    except OSError:
        return None


def _source_status(path: Path, *, complete: bool, error: str | None = None) -> dict:
    return {
        "present": path.exists(),
        "complete": complete,
        "error": error,
        "mtime": _mtime_iso(path) if path.exists() else None,
    }


def _display_text(item: str) -> str:
    text = item.strip()
    if text.startswith("- "):
        text = text[2:].strip()
    if len(text) > _DISPLAY_MAX_CHARS:
        return text[: _DISPLAY_MAX_CHARS].rstrip() + "..."
    return text


def build_pauta_block(pauta_text: str, today: date) -> dict:
    sections = []
    for section_id, heading in PAUTA_SECTIONS:
        raw_items = extract_section(pauta_text, heading)
        items = []
        for raw in raw_items:
            cobrar = cobrar_state(raw, today)
            item: dict = {
                "text": raw,
                "visible_today": True if cobrar is None else cobrar["visible_today"],
            }
            # Orçamento: display_text só existe quando DIFERE do text (item
            # cortado no teto) e cobrar só quando há marker — item curto sem
            # marker custa uma chave, não quatro.
            display = _display_text(raw)
            if display != raw.strip().removeprefix("- ").strip():
                item["display_text"] = display
            if cobrar is not None:
                item["cobrar"] = cobrar
            items.append(item)
        sections.append(
            {
                "id": section_id,
                "label": heading,
                "items": items,
                "count": len(items),
                "visible_count": sum(1 for item in items if item["visible_today"]),
            }
        )
    return {"sections": sections}


def _count_inbox_items(inbox_text: str) -> int:
    count = 0
    for line in inbox_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("- ", "* ")):
            count += 1
        elif stripped[:2].isdigit() and stripped[2:4] == ". ":
            count += 1
    return count


def _registro_tail(registro_text: str, limit: int = _REGISTRO_TAIL_LINES) -> list[str]:
    lines = [line.rstrip() for line in registro_text.splitlines() if line.strip()]
    return lines[-limit:]


def _registro_table_rows(registro_text: str) -> int:
    rows = 0
    for line in registro_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and not set(stripped) <= {"|", "-", " ", ":"}:
            rows += 1
    # Desconta a linha de header quando a tabela existe (rows conta header +
    # dados; separador já ficou de fora pelo filtro de charset).
    return max(rows - 1, 0) if rows else 0


def _processed_signals(processed_path: Path, today: date) -> tuple[int, int, str | None]:
    """(total, stale, error). Arquivo AUSENTE é estado legítimo (nada
    processado ainda) → (0, 0, None); corrompido ou com schema inválido é
    fonte INCOMPLETA → error preenchido (a semente nunca declara faxina
    limpa em cima de lixo ilegível)."""
    if not processed_path.exists():
        return 0, 0, None
    try:
        payload = json.loads(processed_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return 0, 0, f"_processed.json ilegível: {exc}"
    items = payload.get("items", []) if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return 0, 0, "_processed.json sem lista `items`"
    total = 0
    stale = 0
    invalid = 0
    cutoff = today - timedelta(days=_PROCESSED_STALE_DAYS)
    for item in items:
        if not isinstance(item, dict):
            invalid += 1
            continue
        total += 1
        processed_at = str(item.get("processed_at") or "")
        try:
            when = datetime.fromisoformat(processed_at).date()
        except ValueError:
            invalid += 1
            continue
        if when < cutoff:
            stale += 1
    error = None
    if invalid:
        # Fail-visible: contagens dos válidos ficam, mas a fonte não pode se
        # declarar completa — entrada ilegível pode esconder processado vencido.
        error = f"{invalid} entrada(s) inválida(s) em _processed.json"
    return total, stale, error


def build_local_panorama(
    *,
    pauta_path: Path,
    inbox_path: Path,
    registro_path: Path,
    processed_path: Path,
    preview: dict,
    today: date,
) -> tuple[dict, dict]:
    """Monta (`local_panorama`, `payload_completeness`).

    Cada fonte falha SOZINHA: erro de leitura vira `complete: false` +
    `error` naquela fonte, com as demais intactas — o consumidor faz
    fallback por fonte, não releitura integral.
    """
    completeness: dict[str, dict] = {}

    pauta_block: dict = {"sections": []}
    if pauta_path.exists():
        try:
            pauta_block = build_pauta_block(
                pauta_path.read_text(encoding="utf-8"), today
            )
            completeness["pauta"] = _source_status(pauta_path, complete=True)
        except (OSError, UnicodeDecodeError) as exc:
            completeness["pauta"] = _source_status(pauta_path, complete=False, error=str(exc))
    else:
        completeness["pauta"] = _source_status(pauta_path, complete=False, error="arquivo ausente")

    inbox_count = 0
    if inbox_path.exists():
        try:
            inbox_count = _count_inbox_items(inbox_path.read_text(encoding="utf-8"))
            completeness["inbox"] = _source_status(inbox_path, complete=True)
        except (OSError, UnicodeDecodeError) as exc:
            completeness["inbox"] = _source_status(inbox_path, complete=False, error=str(exc))
    else:
        completeness["inbox"] = _source_status(inbox_path, complete=False, error="arquivo ausente")

    registro_tail: list[str] = []
    registro_rows = 0
    if registro_path.exists():
        try:
            registro_text = registro_path.read_text(encoding="utf-8")
            registro_tail = _registro_tail(registro_text)
            registro_rows = _registro_table_rows(registro_text)
            completeness["registro"] = _source_status(registro_path, complete=True)
        except (OSError, UnicodeDecodeError) as exc:
            completeness["registro"] = _source_status(registro_path, complete=False, error=str(exc))
    else:
        completeness["registro"] = _source_status(
            registro_path, complete=False, error="arquivo ausente"
        )

    processed_total, processed_stale, processed_error = _processed_signals(
        processed_path, today
    )
    completeness["processed"] = _source_status(
        processed_path, complete=processed_error is None, error=processed_error
    )

    preview_status = str(preview.get("status") or "ausente")
    completeness["inbox4mobile"] = {
        # present = o ÍNDICE existe de fato (não derivado do status — um scan
        # inconclusivo sem índice é ausente E indeterminado ao mesmo tempo).
        "present": bool(preview.get("index_present")),
        "complete": preview_status == "gerado",
        "error": str(preview.get("note") or "") or None,
        "mtime": (preview.get("freshness") or {}).get("index_mtime"),
    }

    panorama = {
        "schema_version": PANORAMA_SCHEMA_VERSION,
        "generated_for": today.isoformat(),
        "pauta": pauta_block,
        "inbox": {"count": inbox_count},
        "registro": {"tail": registro_tail, "table_rows": registro_rows},
        "inbox4mobile": {
            "status": preview_status,
            "count": int(preview.get("count") or 0),
            "freshness": preview.get("freshness") or {},
        },
        "faxina": {
            "registro_table_rows": registro_rows,
            "processed_entries": processed_total,
            "processed_stale_entries": processed_stale,
            "stale_days_threshold": _PROCESSED_STALE_DAYS,
        },
        "budget": {
            "display_max_chars": _DISPLAY_MAX_CHARS,
            "registro_tail_lines": _REGISTRO_TAIL_LINES,
            "sparse_fields": "display_text só quando truncado; cobrar só com marker",
        },
    }
    return panorama, completeness
