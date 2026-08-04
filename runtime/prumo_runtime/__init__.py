import sys

MINIMUM_PYTHON = (3, 10)


def _require_python(version_info=None):
    """Piso de versão com erro legível, avaliado na carga do pacote — cobre o
    entry point `prumo`, `python -m prumo_runtime` e import direto. Sem isto,
    host abaixo da mínima morre num ImportError críptico de stdlib: foi assim
    que o Cowork ficou nove dias sem marcar o dia (#301)."""
    found = version_info if version_info is not None else sys.version_info
    found = (found[0], found[1])
    if found < MINIMUM_PYTHON:
        raise SystemExit(
            "prumo requer Python %d.%d ou mais novo; este interpretador é %d.%d."
            % (MINIMUM_PYTHON + found)
        )


_require_python()

__all__ = ["__version__"]

__version__ = "5.91.0"
