"""Regressão da #123: o subset que o mirror espelha pro público precisa conter
todos os arquivos que o build do wheel exige via `force-include`.

Quando o mirror deixou de copiar `plugin.json`, o build do runtime a partir do
público passou a falhar com `Forced include not found: plugin.json` — sem o CI
pegar, porque ele builda via sdist (que inclui o arquivo).

Limitação consciente: este teste verifica *convenção textual* — que cada origem
de `force-include` aparece entre os `cp ... "$STAGE` do workflow. Ele NÃO builda
o staging de verdade; se o mirror trocar `cp` por `rsync`/`install`, o teste
acusa falso-vermelho (alerta seguro, não mascara). Um smoke que monte o staging
e rode `python -m build` seria a prova definitiva — ver discussão na #123.
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

# Origem de cada `cp [-R] <src> "$STAGE/...` do staging do mirror.
_CP_PATTERN = re.compile(r'^\s*cp\s+(?:-R\s+)?(\S+)\s+"\$STAGE', re.MULTILINE)


def _is_covered(required: str, copied: set[str]) -> bool:
    """Coberto se o caminho é copiado exatamente ou está sob um diretório copiado.

    Comparação por caminho completo (não só o primeiro segmento): copiar
    `scripts/outro.sh` NÃO satisfaz um `force-include` de `scripts/foo.sh`.
    """
    return any(required == src or required.startswith(f"{src}/") for src in copied)


class MirrorDistConsistencyTests(unittest.TestCase):
    def test_wheel_force_include_sources_are_mirrored(self) -> None:
        data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        required = list(data["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"])

        copied = set(_CP_PATTERN.findall(MIRROR.read_text(encoding="utf-8")))

        missing = [src for src in required if not _is_covered(src, copied)]
        self.assertEqual(
            missing,
            [],
            f"O mirror não espelha {missing} pro público, mas o build do wheel "
            f"exige (force-include). Adicione o `cp` correspondente em "
            f"{MIRROR.relative_to(REPO_ROOT)} — ver #123.",
        )


if __name__ == "__main__":
    unittest.main()
