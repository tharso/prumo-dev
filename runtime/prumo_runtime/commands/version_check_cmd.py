"""`prumo version-check` — produtor explícito do cache de versão (#195).

O payload do briefing lê o cache TTL 24h sem rede; este comando é quem o
refresca quando stale (`--ensure-fresh`). Sem a flag, apenas reporta o cache —
zero rede sempre. Extensão da #158: a rede sai do implícito para um comando
explícito de preflight; o painel (`prumo briefing --format json`) segue leve.
"""
from __future__ import annotations

import argparse
import json

from prumo_runtime.version_check import ensure_fresh_status


def run_version_check(args: argparse.Namespace) -> int:
    status = ensure_fresh_status(allow_network=bool(getattr(args, "ensure_fresh", False)))
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0
