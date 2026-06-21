#!/usr/bin/env python3
"""Guard de bump de versão (regra do Tharso, 2026-06-21; ver gotchas.md).

Falha quando um PR muda `skills/` ou `runtime/prumo_runtime/` sem bumpar
`VERSION`. Sem o bump, o preflight de update do briefing compara o
`prumo_version` do workspace com o `VERSION` remoto, vê que são iguais, e
nenhum usuário recebe a atualização ao abrir o Prumo.

Combina com `test_version_sync` (que garante as 11 fontes em sync com
`__version__`): VERSION mudou + sync verde => bump completo e consistente.

Uso: python scripts/version_bump_guard.py [base_ref]
  base_ref default: origin/main
"""

from __future__ import annotations

import subprocess
import sys

WATCHED = ("skills/", "runtime/prumo_runtime/")


def changed_files(base: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    base = argv[1] if len(argv) > 1 else "origin/main"
    files = changed_files(base)
    touches_system = [f for f in files if f.startswith(WATCHED)]
    bumped = "VERSION" in files

    if touches_system and not bumped:
        print(f"::error::Mudança em skills/ ou runtime/ sem bump de VERSION (base {base}).")
        print("Arquivos do sistema tocados:")
        for path in touches_system[:20]:
            print(f"  - {path}")
        print("")
        print("Toda atualização do sistema precisa subir a versão nas 11 fontes")
        print("canônicas (VERSION + pyproject + __init__ + plugin.json ×3 +")
        print("marketplace.json ×2 + prumo_version do core + module_version de")
        print("dispatch/load-policy) + CHANGELOG. Senão a atualização não chega")
        print("aos usuários (o preflight compara versões iguais). Ver gotchas.md.")
        return 1

    print(
        f"version-bump-guard: ok (base {base}, {len(files)} arquivo(s); "
        f"sistema tocado: {bool(touches_system)}; VERSION bumpada: {bumped})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
