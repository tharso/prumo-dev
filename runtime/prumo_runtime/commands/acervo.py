from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.acervo import enumerate_limbo, safe_items_json
from prumo_runtime.acervo_apply import AcervoSafetyError, apply_report

_KIND_LABEL = {
    "ideia": "ideias soltas",
    "pauta_hibernando": "pauta hibernando",
    "referencia": "referencias",
}


def _render_text(result: dict) -> str:
    lines = [
        f"1. Acervo do workspace `{result['workspace_path']}`.",
        f"2. Itens no limbo: `{result['count']}`.",
    ]
    by_kind: dict[str, int] = {}
    for item in result["items"]:
        by_kind[item["source_kind"]] = by_kind.get(item["source_kind"], 0) + 1
    n = 3
    for kind, count in by_kind.items():
        lines.append(f"{n}. {_KIND_LABEL.get(kind, kind)}: {count} item(ns).")
        n += 1
    if not result["items"]:
        lines.append(f"{n}. Limbo vazio — nada parado pra revisitar.")
    else:
        lines.append(f"{n}. Use `--format html-items` pra alimentar o template da skill `acervo` (gera o HTML navegável).")
    return "\n".join(lines)


def run_acervo(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    result = enumerate_limbo(workspace)
    fmt = getattr(args, "format", "text")
    if fmt == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
    elif fmt == "html-items":
        # Pronto pra colar em /*__ITEMS__*/ do template (escapa <,>,& contra XSS).
        print(safe_items_json(result["items"]))
    else:
        print(_render_text(result))
    return 0


def _render_apply_text(result: dict) -> str:
    lines = [
        f"1. Incluídos na pauta: {len(result['included'])}.",
        f"2. Arquivados: {len(result['archived'])}.",
        f"3. Pra atacar agora (com o agente): {len(result['for_agent'])}.",
        f"4. Bloqueados (revisar): {len(result['blocked'])}.",
    ]
    for b in result["blocked"]:
        lines.append(f"   - {b['title']}: {b['reason']}")
    return "\n".join(lines)


def run_acervo_apply(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        result = apply_report(workspace, report, permanent=getattr(args, "permanent", False))
    except AcervoSafetyError as exc:
        print(f"erro: {exc}")
        return 2
    if getattr(args, "format", "text") == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(_render_apply_text(result))
    return 0
