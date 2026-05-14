#!/usr/bin/env python3
"""
Quality Gate do Prumo.

Coleta métricas reais do projeto e compara com baseline.json.
Falha (exit 1) se qualquer métrica regredir.

Uso:
    python scripts/quality_gate.py [--write-summary PATH]

O --write-summary gera um Markdown com o resultado completo,
útil para postar como comentário no PR.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RUNTIME_SRC = REPO_ROOT / "runtime" / "prumo_runtime"
BASELINE_PATH = Path(__file__).parent / "baseline.json"

ICONS = {"ok": "✅", "fail": "❌", "warn": "⚠️"}


# ---------------------------------------------------------------------------
# Coleta de métricas
# ---------------------------------------------------------------------------

def collect_ruff_violations() -> int:
    result = subprocess.run(
        ["ruff", "check", str(RUNTIME_SRC), "--output-format=json"],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout or "[]")
        return len(data)
    except json.JSONDecodeError:
        return 0


def collect_coverage() -> float:
    """Roda pytest com coverage e retorna o percentual total.

    Usa --source=prumo_runtime (nome do módulo) em vez de path de
    filesystem, para funcionar tanto com PYTHONPATH quanto com
    pip install -e. Parseia a linha TOTAL do coverage report em vez
    de depender de --format=total (adicionado só no coverage 7.3).
    """
    import re

    cov_dir = Path("/tmp/prumo_qg_cov")
    cov_dir.mkdir(exist_ok=True)
    data_file = cov_dir / ".coverage"

    run_env = {**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT / "runtime")}
    subprocess.run(
        [
            sys.executable, "-m", "coverage", "run",
            f"--data-file={data_file}",
            "--source=prumo_runtime",
            "-m", "pytest", str(REPO_ROOT / "runtime" / "tests"), "-q",
        ],
        capture_output=True,
        cwd=REPO_ROOT,
        env=run_env,
    )

    result = subprocess.run(
        [sys.executable, "-m", "coverage", "report",
         f"--data-file={data_file}"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=run_env,
    )

    # Parseia a linha TOTAL: "TOTAL   1234   200    84%"
    for line in result.stdout.splitlines():
        m = re.match(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", line)
        if m:
            return float(m.group(1))

    # Fallback: tenta --format=total (coverage >= 7.3)
    result2 = subprocess.run(
        [sys.executable, "-m", "coverage", "report",
         f"--data-file={data_file}", "--format=total"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=run_env,
    )
    try:
        return float(result2.stdout.strip())
    except ValueError:
        return 0.0


def collect_largest_file() -> tuple[int, str]:
    """Retorna (linhas, caminho relativo) do maior arquivo Python no runtime."""
    py_files = list(RUNTIME_SRC.rglob("*.py"))
    if not py_files:
        return 0, ""
    counts = [(len(f.read_text(encoding="utf-8").splitlines()), f) for f in py_files]
    lines, path = max(counts)
    return lines, str(path.relative_to(REPO_ROOT))


# ---------------------------------------------------------------------------
# Comparação com baseline
# ---------------------------------------------------------------------------

def check_metric(
    name: str,
    label: str,
    current: float,
    baseline: float,
    lower_is_better: bool,
) -> dict:
    if lower_is_better:
        passed = current <= baseline
        direction = "↑" if current > baseline else ("↓" if current < baseline else "=")
    else:
        passed = current >= baseline
        direction = "↓" if current < baseline else ("↑" if current > baseline else "=")

    return {
        "name": name,
        "label": label,
        "current": current,
        "baseline": baseline,
        "passed": passed,
        "direction": direction,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def render_summary(results: list[dict], overall_ok: bool) -> str:
    header = "## Quality Gate — Prumo\n\n"
    status_line = (
        f"**{ICONS['ok']} Passou** — nenhuma regressão detectada.\n\n"
        if overall_ok
        else f"**{ICONS['fail']} Falhou** — uma ou mais métricas regrediram.\n\n"
    )

    rows = ["| Métrica | Baseline | Atual | Status |", "| --- | --- | --- | --- |"]
    for r in results:
        icon = ICONS["ok"] if r["passed"] else ICONS["fail"]
        fmt = ".0f" if isinstance(r["current"], float) and r["current"] == int(r["current"]) else ".1f"
        cur = f"{r['current']:{fmt}}"
        base = f"{r['baseline']:{fmt}}"
        rows.append(f"| {r['label']} | {base} | {cur} {r['direction']} | {icon} |")

    return header + status_line + "\n".join(rows) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Quality Gate do Prumo")
    parser.add_argument("--write-summary", metavar="PATH", help="Salvar sumário Markdown")
    args = parser.parse_args()

    if not BASELINE_PATH.exists():
        print(f"[qg] ERRO: baseline não encontrado em {BASELINE_PATH}", file=sys.stderr)
        return 1

    baseline = json.loads(BASELINE_PATH.read_text())

    print("[qg] Coletando métricas...")

    violations = collect_ruff_violations()
    print(f"[qg]   ruff_violations  : {violations}")

    coverage = collect_coverage()
    print(f"[qg]   coverage_pct     : {coverage:.1f}%")

    largest_lines, largest_file = collect_largest_file()
    print(f"[qg]   largest_file     : {largest_lines} linhas ({largest_file})")

    results = [
        check_metric(
            "ruff_violations", "Violações ruff",
            violations, baseline["ruff_violations"],
            lower_is_better=True,
        ),
        check_metric(
            "coverage_pct", "Cobertura de testes (%)",
            coverage, baseline["coverage_pct"],
            lower_is_better=False,
        ),
        check_metric(
            "largest_file_lines", "Maior arquivo (linhas)",
            largest_lines, baseline["largest_file_lines"],
            lower_is_better=True,
        ),
    ]

    overall_ok = all(r["passed"] for r in results)
    summary = render_summary(results, overall_ok)

    print()
    print(summary)

    if args.write_summary:
        Path(args.write_summary).write_text(summary)
        print(f"[qg] Sumário salvo em {args.write_summary}")

    if not overall_ok:
        print("[qg] ❌ Quality gate falhou — PR não pode ser mergeado.", file=sys.stderr)
        return 1

    print("[qg] ✅ Quality gate passou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
