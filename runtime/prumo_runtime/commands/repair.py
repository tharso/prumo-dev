from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.workspace import repair_workspace


def run_repair(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    result = repair_workspace(workspace)

    from prumo_runtime.host_adapters import repair_host_adapters
    adapter_result = repair_host_adapters(workspace)
    result["host_adapters"] = adapter_result

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0

    print(f"Workspace reparado: {workspace}")

    drift = result.get("version_drift")
    if drift:
        print(
            f"Drift de versão detectado: {drift['from']} → {drift['to']}. "
            f"Arquivos canônicos antigos movidos pra backup."
        )
        if drift.get("backup_root"):
            print(f"Backup em: {drift['backup_root']}")

    if result["recreated"]:
        print("Arquivos recriados:")
        for relative in result["recreated"]:
            print(f"- {relative}")

    if result.get("merged"):
        print("Wrappers atualizados via merge (custom blocks preservados):")
        for relative in result["merged"]:
            print(f"- {relative}")

    if not result["recreated"] and not result.get("merged"):
        print("Nada recriável precisava de reparo.")

    if adapter_result.get("repaired", 0) > 0:
        print(f"Host adapters reparados: {adapter_result['repaired']}")

    if result["missing_authorial"]:
        print("")
        print("Arquivos autorais ausentes (o runtime não inventou conteúdo no seu lugar):")
        for relative in result["missing_authorial"]:
            print(f"- {relative}")
        print("Use backup ou recrie manualmente o que fizer sentido.")
    return 0
