"""Regressão da #123: o subset que o mirror espelha pro público precisa conter
todos os arquivos que o build do wheel exige via `force-include`.

Quando o mirror deixou de copiar `plugin.json`, o build do runtime a partir do
público passou a falhar com `Forced include not found: plugin.json` — sem o CI
pegar, porque ele builda via sdist (que inclui o arquivo). Este teste compara,
de forma estática, o `force-include` do `pyproject.toml` com os `cp ... "$STAGE`
do workflow do mirror, e falha se algum arquivo exigido não for espelhado.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
MIRROR = REPO_ROOT / ".github" / "workflows" / "mirror-to-prumo.yml"

# Captura o caminho de origem de cada `cp [-R] <src> "$STAGE/...` do staging.
_CP_PATTERN = re.compile(r'^\s*cp\s+(?:-R\s+)?(\S+)\s+"\$STAGE', re.MULTILINE)


def _root_segment(path: str) -> str:
    """Primeiro segmento do caminho (ex: 'scripts/x.sh' -> 'scripts')."""
    return path.split("/", 1)[0]


class MirrorDistConsistencyTests(unittest.TestCase):
    def test_wheel_force_include_sources_are_mirrored(self) -> None:
        data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        force_include = data["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
        required = {_root_segment(src) for src in force_include}

        mirror_text = MIRROR.read_text(encoding="utf-8")
        copied = {_root_segment(src) for src in _CP_PATTERN.findall(mirror_text)}

        missing = required - copied
        self.assertEqual(
            missing,
            set(),
            f"O mirror não copia {sorted(missing)} pro público, mas o build do "
            f"wheel exige (force-include). Adicione o `cp` correspondente em "
            f"{MIRROR.relative_to(REPO_ROOT)} — ver #123.",
        )


if __name__ == "__main__":
    unittest.main()
