"""
Frescor do clone da store ativa (#324) — a detecção da última milha.

O incidente de 03/08: espelho público servindo 5.89.0, runtime local
atualizável — e o botão "Atualizar" do app DESABILITADO. Causa: o clone do
marketplace em `~/.claude/plugins/marketplaces/` congelado (FETCH_HEAD de
3 dias antes); o app compara o instalado contra a fotocópia velha e conclui
"nada a atualizar". O refresh do clone é do app — fora do nosso alcance.
A DETECÇÃO é nossa: sem ela a última milha falha em silêncio e o usuário
fica preso numa versão velha achando que está em dia.

Módulo folha, funções puras com raiz injetável: os testes montam stores de
mentira em tmp e nunca tocam a `$HOME` real.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def _default_store_root() -> Path:
    """A store unificada dos hosts Claude (app desktop e Claude Code)."""
    return Path.home() / ".claude" / "plugins"


def _clone_do_espelho(path: Path) -> bool:
    """Um clone do espelho do Prumo se reconhece pela árvore: VERSION na
    raiz + skills/prumo (a fonte canônica que só o Prumo carrega)."""
    return (path / "VERSION").is_file() and (path / "skills" / "prumo").is_dir()


def locate_prumo_clone(store_root: Path | None = None) -> Path | None:
    """Onde está o clone do marketplace do Prumo na store ativa.

    Fonte primária: `known_marketplaces.json` — é como o PRÓPRIO app resolve
    (entrada cuja source.url aponta pro espelho). Fallback: varredura rasa de
    `marketplaces/` pela árvore do espelho. Nada encontrado → None (host sem
    store não é defeito)."""
    root = store_root if store_root is not None else _default_store_root()

    registry = root / "known_marketplaces.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = None
    if isinstance(data, dict):
        for entry in data.values():
            if not isinstance(entry, dict):
                continue
            source = entry.get("source")
            # O registry usa DUAS formas de fonte: {"source": "git",
            # "url": "https://github.com/tharso/prumo.git"} e {"source":
            # "github", "repo": "tharso/prumo"}. Só a url deixava a forma
            # repo cair em falso "ausente" quando o installLocation vive
            # fora de marketplaces/ (Codex, 324-r1).
            alvo = ""
            if isinstance(source, dict):
                alvo = f"{source.get('url', '')} {source.get('repo', '')}"
            location = entry.get("installLocation")
            if location and "tharso/prumo" in alvo:
                candidate = Path(location)
                if candidate.is_dir():
                    return candidate

    base = root / "marketplaces"
    try:
        candidatos = sorted(p for p in base.iterdir() if p.is_dir())
    except OSError:
        return None
    for candidato in candidatos:
        if _clone_do_espelho(candidato):
            return candidato
    return None


def collect(
    store_root: Path | None = None,
    remote_version: str | None = None,
    now: float | None = None,
) -> dict:
    """Retrato factual do clone: versão, idade do último fetch e veredito.

    Vereditos: `ausente` (host sem store — declarado, não é erro),
    `fresca` (clone == remoto), `defasada` (clone != remoto) e
    `indeterminada` (sem remoto pra comparar — afirmar "em dia" sem olhar
    seria a classe de mentira que o preflight já mata, #215)."""
    clone = locate_prumo_clone(store_root)
    if clone is None:
        return {"found": False, "status": "ausente"}

    try:
        version = (clone / "VERSION").read_text(encoding="utf-8").strip() or None
    except OSError:
        version = None

    # A idade do FETCH_HEAD é a evidência de quando o app TENTOU sincronizar
    # pela última vez — no incidente, 3 dias antes. Ausente → desconhecida.
    fetch_age_days: float | None = None
    try:
        mtime = (clone / ".git" / "FETCH_HEAD").stat().st_mtime
        agora = now if now is not None else time.time()
        fetch_age_days = round(max(0.0, agora - mtime) / 86400, 1)
    except OSError:
        pass

    if remote_version is None:
        status = "indeterminada"
    elif version == remote_version:
        status = "fresca"
    else:
        status = "defasada"

    return {
        "found": True,
        "path": str(clone),
        "version": version,
        "fetch_age_days": fetch_age_days,
        "remote_version": remote_version,
        "status": status,
    }
