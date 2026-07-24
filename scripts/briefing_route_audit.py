#!/usr/bin/env python3
"""Auditoria da rota do briefing — palavras carregadas antes do 1º dado do usuário.

Contexto (#178, épico #177): a auditoria de 2026-07-15 mediu 8.332 palavras
carregadas pela rota do briefing numa instância instalada, antes do primeiro
dado operacional do usuário (CLAUDE.md wrapper + Prumo/AGENT.md + PRUMO-CORE
+ briefing/SKILL.md + briefing-procedure.md + PERFIL.md). O critério 6 do
épico exige ≥40% de redução, medida por script — este script.

Dois modos, decididos pelo `briefing/SKILL.md` do workspace:

- **manifest** (M3 em diante): o SKILL declara a tabela
  `## Mapa de carregamento por fase` (colunas `Fase | Gatilho | Arquivo |
  Seção | Tipo`). O cesto "antes do 1º dado" são as linhas F0/F1 com gatilho
  `sempre`. `Seção` aceita três formas: `(integral)`, um heading exato
  (`## Guardrails`) ou `até: <heading>` (do início do arquivo até o marcador).
- **legacy** (rota atual, pré-M3): a Pré-carga canônica pós-#195 no pior
  caso realista (Cowork + shell + Inbox4Mobile). A referência de 8.332
  palavras é HISTÓRICA — medida na composição de 15/07, pré-#195 — e fica
  fixa como baliza do critério 6.

Uso:
    python scripts/briefing_route_audit.py [--workspace PATH] [--json]
                                           [--ceiling N]

Sem `--workspace`, monta um sandbox efêmero via runtime (install_skills +
create_missing_files) num tempdir — nunca toca workspace real. O setup
materializa um `PERFIL.md` template enxuto (contado como está e declarado);
recibos oficiais de antes/depois semeiam PERFIL sintético ~1.256w (M4).

`--ceiling N` sai com código 1 se o cesto passar de N palavras (a M3 liga
isso no quality gate via métrica `briefing_f0_words`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "runtime"))

SCHEMA_VERSION = "prumo_briefing_route_audit.v1"
# Medição da auditoria de 2026-07-15 (instância DailyLife, core 5.32.0).
# Referência FIXA do critério 6 do épico #177 — não recalibrar.
REFERENCE_WORDS = 8332
MANIFEST_HEADING = "## Mapa de carregamento por fase"
_BASKET_PHASES = {"F0", "F1"}
_ALWAYS = "sempre"


@dataclass
class RouteItem:
    phase: str
    file: str
    section: str
    words: int
    exists: bool
    note: str = ""


def count_words(text: str) -> int:
    return len(text.split())


def _heading_level(line: str) -> int:
    return len(line) - len(line.lstrip("#"))


def extract_section(text: str, heading: str) -> str | None:
    """Do heading exato (linha inteira, strip) até o próximo heading de nível
    igual ou superior. `None` se o heading não existir."""
    lines = text.splitlines()
    level = _heading_level(heading.strip())
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading.strip():
            start = i
            break
    if start is None:
        return None
    body: list[str] = [lines[start]]
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("#") and _heading_level(stripped) <= level:
            break
        body.append(line)
    return "\n".join(body)


def extract_until_marker(text: str, heading: str) -> str | None:
    """Do início do arquivo até (excluindo) o heading marcador."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == heading.strip():
            return "\n".join(lines[:i])
    return None


def resolve_words(workspace: Path, file_rel: str, section: str) -> tuple[int, bool, str, bool]:
    """Devolve (palavras, arquivo_existe, nota, erro).

    Fail-closed (rounds 1–3 do Codex na série): seção declarada que não
    existe num arquivo presente é ERRO — contar zero em silêncio deixaria o
    `--ceiling` aprovar "redução" com o termômetro quebrado. Arquivo ausente
    é reportado aqui sem flag de erro; quem decide é o `measure` — e nos
    DOIS modos ele trata ausência como erro (manifesto descreve a instalação
    real; rota mandatória ausente é instalação quebrada). Marcador `até:`
    ausente conta integral — superconta, nunca subconta: seguro pro teto.
    """
    path = workspace / file_rel
    if not path.exists():
        return 0, False, "arquivo ausente no workspace", False
    text = path.read_text(encoding="utf-8")
    section = section.strip()
    if section in {"", "(integral)"}:
        return count_words(text), True, "", False
    if section.startswith("até:"):
        marker = section[len("até:") :].strip()
        sliced = extract_until_marker(text, marker)
        if sliced is None:
            return count_words(text), True, f"marcador '{marker}' ausente — contado integral", False
        return count_words(sliced), True, "", False
    sliced = extract_section(text, section)
    if sliced is None:
        return 0, True, f"seção '{section}' ausente", True
    return count_words(sliced), True, "", False


def parse_manifest(skill_text: str) -> tuple[list[dict], list[str]] | None:
    """Parseia a tabela sob `## Mapa de carregamento por fase`.

    Colunas: `Fase | Gatilho | Arquivo | Seção | Tipo`. Mesma disciplina do
    `parse_command_table`: só a tabela contígua após o heading. `None` quando
    o heading não existe (modo legacy). Devolve `(rows, invalid_lines)` —
    linha de tabela que não parseia é ERRO do chamador, nunca descarte
    silencioso (fail-closed, Codex série r2): uma linha engolida subcontaria
    a rota com o restante válido.
    """
    lines = skill_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == MANIFEST_HEADING:
            start = i + 1
            break
    if start is None:
        return None
    rows: list[dict] = []
    invalid: list[str] = []
    started = False
    backtick = re.compile(r"`([^`]+)`")
    for line in lines[start:]:
        s = line.strip()
        if s.startswith("#"):
            break
        if not s.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [c.strip() for c in s.strip("|").split("|")]
        structural = cells and (
            set(cells[0]) <= set("-: ") and cells[0] != "" or cells[0].lower() == "fase"
        )
        if structural:
            continue
        if len(cells) < 5 or not all(cells[:5]):
            invalid.append(s)
            continue
        file_cell = cells[2]
        m = backtick.search(file_cell)
        rows.append(
            {
                "phase": cells[0],
                "trigger": cells[1],
                "file": m.group(1).strip() if m else file_cell,
                "section": backtick.sub(lambda x: x.group(1), cells[3]),
                "type": cells[4],
            }
        )
    return rows, invalid


# Rota mandatória ATUAL (pré-M3) — a Pré-carga canônica da #195 (lista única
# do briefing-procedure) no pior caso realista: Cowork com shell e
# Inbox4Mobile ativo (o ambiente da instância auditada). Os três últimos são
# condicionais no procedure, mas SEMPRE disparam nesse ambiente. Atualizada
# no round 1 do Codex na série (a versão anterior era pré-#195 e subcontava).
_MODULES = ".prumo/skills/prumo/references/modules"
LEGACY_ROUTE: list[tuple[str, str, str, str]] = [
    ("F0", "CLAUDE.md", "(integral)", "wrapper da raiz"),
    ("F0", "Prumo/AGENT.md", "(integral)", "porta canônica"),
    ("F0", ".prumo/system/PRUMO-CORE.md", "(integral)", "o SKILL atual manda ler inteiro"),
    ("F1", ".prumo/skills/briefing/SKILL.md", "(integral)", "entrada da skill"),
    (
        "F1",
        f"{_MODULES}/briefing-procedure.md",
        "(integral)",
        "procedure inteiro (carrega a Pré-carga canônica, #195)",
    ),
    ("F1", "Prumo/Agente/PERFIL.md", "(integral)", "config do usuário"),
    ("F1", "Prumo/Agente/ROTINA.md", "(integral)", "config do usuário"),
    ("F1", "Prumo/Agente/PESSOAS.md", "(integral)", "predicado de remetente (#195)"),
    ("F1", f"{_MODULES}/load-policy.md", "(integral)", "pré-carga canônica (#195)"),
    ("F1", f"{_MODULES}/version-update.md", "(integral)", "pré-carga canônica (#195)"),
    ("F1", f"{_MODULES}/interaction-format.md", "(integral)", "pré-carga canônica (#195)"),
    ("F1", f"{_MODULES}/runtime-paths.md", "(integral)", "condicional: shell (sempre no Cowork)"),
    ("F1", f"{_MODULES}/cowork-runtime-bridge.md", "(integral)", "condicional: Cowork com shell"),
    ("F1", f"{_MODULES}/inbox-processing.md", "(integral)", "condicional: Inbox4Mobile com itens novos"),
]


def measure(workspace: Path) -> dict:
    skill_path = workspace / ".prumo" / "skills" / "briefing" / "SKILL.md"
    manifest = None
    if skill_path.exists():
        manifest = parse_manifest(skill_path.read_text(encoding="utf-8"))

    items: list[RouteItem] = []
    errors: list[str] = []
    if manifest is not None:
        mode = "manifest"
        rows, invalid_lines = manifest
        if not rows:
            # Heading presente com tabela vazia/malformada NÃO é "rota zerada":
            # é manifesto quebrado (fail-closed, Codex série r1).
            errors.append("manifesto declarado mas vazio/malformado — termômetro quebrado")
        for bad in invalid_lines:
            errors.append(f"linha de manifesto inválida: {bad}")
        for row in rows:
            if row["phase"] not in _BASKET_PHASES or row["trigger"].lower() != _ALWAYS:
                continue
            words, exists, note, error = resolve_words(workspace, row["file"], row["section"])
            items.append(
                RouteItem(row["phase"], row["file"], row["section"], words, exists, note)
            )
            if error:
                errors.append(f"{row['file']}: {note}")
            elif not exists:
                # No modo manifest o arquivo declarado TEM que existir — o
                # manifesto descreve a instalação real (Codex série r2).
                errors.append(f"{row['file']}: arquivo declarado no manifesto está ausente")
    else:
        mode = "legacy"
        for phase, file_rel, section, note in LEGACY_ROUTE:
            words, exists, extra, error = resolve_words(workspace, file_rel, section)
            final_note = extra or note
            items.append(RouteItem(phase, file_rel, section, words, exists, final_note))
            if error:
                errors.append(f"{file_rel}: {extra}")
            elif not exists:
                # Rota mandatória com arquivo ausente é instalação quebrada —
                # zero silencioso aprovaria "redução" falsa (Codex série r3).
                errors.append(f"{file_rel}: arquivo da rota mandatória ausente")

    total = sum(item.words for item in items)
    if total == 0 and not errors:
        errors.append("rota mediu zero palavras — termômetro quebrado")
    reduction_pct = round(100 * (1 - total / REFERENCE_WORDS), 1)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "workspace_path": str(workspace),
        "items": [asdict(item) for item in items],
        "errors": errors,
        "total_before_first_user_data": total,
        "reference_words": REFERENCE_WORDS,
        "reduction_pct_vs_reference": reduction_pct,
    }


def build_sandbox(root: Path) -> Path:
    from prumo_runtime.skills_install import install_skills
    from prumo_runtime.workspace import WorkspaceConfig, create_missing_files

    workspace = root / "ws"
    workspace.mkdir(parents=True)
    config = WorkspaceConfig(
        workspace=workspace,
        user_name="Auditoria",
        layout_mode="nested",
    )
    install_skills(workspace, layout_mode="nested")
    create_missing_files(config)
    return workspace


def _print_report(report: dict, ceiling: int | None) -> None:
    print(f"[audit] rota do briefing — modo {report['mode']}")
    print(f"[audit] workspace: {report['workspace_path']}")
    for item in report["items"]:
        note = f"  ({item['note']})" if item["note"] else ""
        print(
            f"[audit]   {item['phase']:<3} {item['words']:>6}w  {item['file']}"
            f" [{item['section']}]{note}"
        )
    total = report["total_before_first_user_data"]
    print(f"[audit] total antes do 1º dado do usuário: {total} palavras")
    print(
        f"[audit] vs referência da auditoria ({report['reference_words']}): "
        f"{report['reduction_pct_vs_reference']}% de redução"
    )
    if ceiling is not None:
        status = "OK" if total <= ceiling else "ESTOURO"
        print(f"[audit] teto {ceiling}: {status}")
    for error in report.get("errors", []):
        print(f"[audit] ERRO: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--ceiling", type=int, default=None)
    args = parser.parse_args(argv)

    if args.workspace is not None:
        report = measure(args.workspace.expanduser().resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="prumo-route-audit-") as tmp:
            report = measure(build_sandbox(Path(tmp)))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report, args.ceiling)

    if report.get("errors"):
        # Fail-closed: rota quebrada nunca "passa" — nem sem --ceiling.
        return 2
    if args.ceiling is not None and report["total_before_first_user_data"] > args.ceiling:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
