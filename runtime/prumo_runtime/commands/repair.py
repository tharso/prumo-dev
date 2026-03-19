from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.workspace import repair_workspace


def run_repair(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    result = repair_workspace(workspace)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0

    print(f"Workspace reparado: {workspace}")
    if result["recreated"]:
        print("Arquivos recriados:")
        for relative in result["recreated"]:
            print(f"- {relative}")
    else:
        print("Nada recriável precisava de reparo.")

    if result["missing_authorial"]:
        print("")
        print("Arquivos autorais ausentes (o runtime não inventou conteúdo no seu lugar):")
        for relative in result["missing_authorial"]:
            print(f"- {relative}")
        print("Use backup ou recrie manualmente o que fizer sentido.")
    return 0
