"""
Leitores das fontes de instalação do `prumo update` (TOML: uv-receipt,
pyproject de candidato local, artefato extraído).

Extraído de `update.py` na #301: o arquivo estava colado no teto da catraca
(868 linhas) e o gate de Python mínimo não cabia sem estourar — primeira
parcela da #281. `tomllib` é stdlib 3.11+ e a mínima do runtime é 3.10: os
imports ficam adiados dentro das funções, e o guard de AST em
`test_python_310_support.py` garante que nenhum volta ao nível de módulo.
"""
from __future__ import annotations

import os
from pathlib import Path


def _uv_tools_dir(uv_tool_dir: Path | None = None) -> Path:
    """Diretório onde o uv guarda os tools instalados. Agnóstico de host:
    respeita `UV_TOOL_DIR`, senão o padrão do uv sob `XDG_DATA_HOME`/`~/.local/share`.
    """
    if uv_tool_dir is not None:
        return uv_tool_dir
    env = os.environ.get("UV_TOOL_DIR")
    if env:
        return Path(env)
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "uv" / "tools"


def _local_dir_from_uv_receipt(uv_tool_dir: Path | None = None) -> str | None:
    """Lê o `directory` do `uv-receipt.toml` do prumo-runtime (fonte da verdade
    do próprio uv pra instalação de diretório local). Retorna o path atual, ou
    None se não houver receipt de instalação-por-diretório."""
    receipt = _uv_tools_dir(uv_tool_dir) / "prumo-runtime" / "uv-receipt.toml"
    # tomllib é stdlib 3.11+; import adiado pra não derrubar o CLI na mínima 3.10 (#301)
    import tomllib

    try:
        data = tomllib.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    for req in data.get("tool", {}).get("requirements", []):
        if isinstance(req, dict) and req.get("name") == "prumo-runtime":
            directory = req.get("directory")
            if directory:
                return str(directory)
    return None


def _is_valid_runtime_dir(path: Path, expected_version: str) -> bool:
    """O diretório é uma fonte de prumo-runtime na versão esperada?"""
    pyproject = path / "pyproject.toml"
    import tomllib

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    project = data.get("project", {})
    return project.get("name") == "prumo-runtime" and project.get("version") == expected_version


def _staged_version(root: Path) -> str | None:
    """Versão do artefato extraído — só se for prumo-runtime de verdade, com
    a árvore mínima (pyproject coerente + runtime/ + skills/ + VERSION)."""
    import tomllib

    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project", {})
    if project.get("name") != "prumo-runtime":
        return None
    version = project.get("version")
    if not version:
        return None
    try:
        version_file = (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if version_file != version:
        return None
    if not (root / "runtime" / "prumo_runtime").is_dir() or not (root / "skills").is_dir():
        return None
    return version
