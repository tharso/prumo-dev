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
    if not result.stdout or not result.stdout.strip():
        print(f"[qg]   ruff não emitiu JSON (exit={result.returncode})", file=sys.stderr)
        if result.stderr:
            print(f"[qg]   ruff stderr: {result.stderr[:300]}", file=sys.stderr)
        return -1
    try:
        data = json.loads(result.stdout)
        return len(data)
    except json.JSONDecodeError:
        print(f"[qg]   ruff emitiu saída não-JSON: {result.stdout[:200]}", file=sys.stderr)
        return -1


def collect_coverage() -> float:
    """Roda pytest com coverage e retorna o percentual total.

    Usa a configuração de [tool.coverage.run] do pyproject.toml
    (source = ["prumo_runtime"]) via --rcfile. Parseia a linha
    TOTAL do coverage report.
    """
    import re

    cov_dir = Path("/tmp/prumo_qg_cov")
    cov_dir.mkdir(exist_ok=True)
    data_file = cov_dir / ".coverage"
    rcfile = REPO_ROOT / "pyproject.toml"

    run_result = subprocess.run(
        [
            sys.executable, "-m", "coverage", "run",
            f"--data-file={data_file}",
            f"--rcfile={rcfile}",
            "-m", "unittest", "discover",
            "-s", str(REPO_ROOT / "runtime" / "tests"),
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    print(f"[qg]   coverage run exit={run_result.returncode} data_file_exists={data_file.exists()}")
    if run_result.stderr:
        # Mostrar apenas linhas relevantes (warnings do coverage)
        for ln in run_result.stderr.splitlines()[:10]:
            if "warn" in ln.lower() or "error" in ln.lower() or "no data" in ln.lower():
                print(f"[qg]   coverage run: {ln}")

    report_result = subprocess.run(
        [sys.executable, "-m", "coverage", "report",
         f"--data-file={data_file}", f"--rcfile={rcfile}"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    for line in report_result.stdout.splitlines():
        m = re.match(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", line)
        if m:
            return float(m.group(1))

    # Diagnóstico: mostrar o que coverage report devolveu
    print(f"[qg]   coverage report exit={report_result.returncode}")
    if report_result.stdout:
        print(f"[qg]   coverage report stdout: {report_result.stdout[:300]}")
    if report_result.stderr:
        print(f"[qg]   coverage report stderr: {report_result.stderr[:300]}")

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
    if violations < 0:
        print("[qg] ERRO: ruff falhou sem emitir resultados válidos.", file=sys.stderr)
        return 1
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
