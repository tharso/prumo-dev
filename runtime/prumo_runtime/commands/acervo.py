from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.acervo import enumerate_limbo

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
        lines.append(f"{n}. Use `--format json` pra alimentar a skill `acervo` (gera o HTML navegável).")
    return "\n".join(lines)


def run_acervo(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    result = enumerate_limbo(workspace)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(_render_text(result))
    return 0
