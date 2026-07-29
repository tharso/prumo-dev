"""Thresholds da faxina: defaults + override do usuário, resolvidos (#258).

Os números moram no `faxina-thresholds.md` (doc canônico que o AGENTE lê) e
aqui em código (o que o RUNTIME aplica ao montar a semente). Duas projeções do
mesmo dado — `test_faxina_thresholds.py` trava a paridade, senão vira o bug da
#195 em outra roupa.

Por que existe: a semente declarava só `stale_days_threshold`, sempre o
default, ignorando `Prumo/Custom/rules/faxina-thresholds.md`. O contrato do
`briefing-estado.md` mandava o agente recalcular quando o efetivo divergisse do
declarado — remendo que dependia de o agente ter os defaults em contexto. Com a
semente aplicando o override, ela para de mentir e o doc sai da rota sempre-
carregada (corte D2 da #228, revertido no gate por causa disso).
"""

from __future__ import annotations

import re
from pathlib import Path

SCHEMA = "prumo_faxina_thresholds.v1"
# O literal ACEITO pelo consumidor — declarado também no `briefing-estado.md`:
# "desconhecido" sem lista de conhecidos é horóscopo, não gate (Codex).

# Espelho da tabela do `faxina-thresholds.md`. Chave nova entra nos DOIS.
DEFAULTS: dict[str, int] = {
    # Registro
    "max_items": 50,
    "archive_age_days": 30,
    # Inbox
    "processed_expiry_days": 14,
    "declared_inbox_stale_days": 14,  # caixa declarada no mapa autoral (#245)
    # Cache e backups (consumidos pela sanitize, declarados no mesmo doc)
    "backup_expiry_days": 90,
    "cache_expiry_days": 30,
    # Snapshot de arquivo curado (#262): encolhimento acima disso vira alerta
    "curated_shrink_alert_pct": 40,
    # Índices
    "referencias_subcategorize_at": 30,
    # Diário
    "diario_expiry_days": 90,
}

# Teto por chave, pra chave cujo domínio não é "qualquer inteiro >= 0".
# Percentual acima de 100 é inatingível: o alerta desligaria em silêncio, que
# é pior que não existir (achado da rodada 6 do Codex na #262).
MAXIMOS: dict[str, int] = {"curated_shrink_alert_pct": 100}

# Candidato = qualquer `- chave: valor`. A gramática da CHAVE é validada
# depois, pra que nome inválido (maiúscula, hífen) apareça em `ignored_keys`
# em vez de sumir sem rastro (Codex, diff r1).
_OVERRIDE_LINE = re.compile(r"^\s*[-*]\s*([^\s:][^:]*?)\s*:\s*(.+?)\s*$")


def override_path(workspace: Path) -> Path:
    """`Prumo/Custom/rules/faxina-thresholds.md` — o override é do usuário."""
    from prumo_runtime.workspace_paths import workspace_paths

    return workspace_paths(workspace).custom_rules_root / "faxina-thresholds.md"


def read_override(workspace: Path) -> tuple[dict[str, int], list[str]]:
    """Lê o override do usuário. Devolve (válidos, ignorados).

    Vocabulário controlado (regra do próprio doc: "apelido novo não é override,
    é dialeto"): chave fora do `DEFAULTS`, valor não-inteiro e valor fora do
    domínio da chave (ver `MAXIMOS`) são **ignorados e reportados** — nunca
    adivinhados.
    """
    path = override_path(workspace)
    if not path.is_file():
        return {}, []
    valores: dict[str, int] = {}
    ignoradas: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _OVERRIDE_LINE.match(line)
        if m is None:
            continue
        chave, bruto = m.group(1).strip().strip("`"), m.group(2).strip().strip("`")
        # case-sensitive: `MAX_ITEMS` não é `max_items` (vocabulário controlado)
        if chave not in DEFAULTS:
            ignoradas.append(chave)
            continue
        try:
            valor = int(bruto)
        except ValueError:
            ignoradas.append(chave)
            continue
        if valor < 0 or valor > MAXIMOS.get(chave, valor):
            ignoradas.append(chave)
            continue
        valores[chave] = valor
    return valores, ignoradas


def effective(workspace: Path) -> dict:
    """Thresholds que valem NESTE workspace, com a origem declarada."""
    override, ignoradas = read_override(workspace)
    valores = {**DEFAULTS, **override}
    return {
        "schema": SCHEMA,
        "values": valores,
        "source": "override" if override else "default",
        "override_keys": sorted(override),
        "ignored_keys": sorted(set(ignoradas)),
    }
