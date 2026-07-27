"""Runner da suíte de conformidade.

Orquestra um caso: monta o workspace da fixture num tmp → executa (host replay
ou claude_code) → aplica o oráculo sobre o filesystem resultante → devolve um
resultado. Também é CLI:

    # determinístico, sem LLM (o que roda em CI):
    python -m conformance.harness.run --scenario c5_inbox_removal --replay compliant

    # real, na cadência (shell autenticado; NÃO em CI):
    python -m conformance.harness.run --scenario c5_inbox_removal --host claude_code

Ver SPEC.md para a política de retenção dos relatórios.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from conformance.harness import hosts, scenarios
from conformance.harness.oracles import Verdict
from conformance.harness.scenarios import Case, Scenario


@dataclass(frozen=True)
class Result:
    scenario: str
    variant: str
    mode: str  # "replay:compliant" | "replay:violation" | "claude_code"
    verdict: Verdict
    workspace: str


def _setup_workspace(scenario: Scenario, dest: Path) -> None:
    """Copia a fixture inicial do cenário para `dest` (o workspace de trabalho)."""
    src = scenario.fixture_dir / "workspace"
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        dest.mkdir(parents=True, exist_ok=True)


def run_case_replay(scenario: Scenario, case: Case, which: str) -> Result:
    """Roda um caso com o host replay (determinístico). `which` ∈ {compliant, violation}."""
    ops = case.compliant_ops if which == "compliant" else case.violation_ops
    with tempfile.TemporaryDirectory(prefix=f"conf-{scenario.id}-") as tmp:
        ws = Path(tmp)
        _setup_workspace(scenario, ws)
        trace = hosts.apply_replay(ws, ops)
        params = dict(case.oracle_params)
        if scenario.oracle_wants_trace:
            params["trace"] = trace
        verdict = scenario.oracle(ws, **params)
    return Result(scenario.id, case.variant, f"replay:{which}", verdict, tmp)


def run_case_claude(scenario: Scenario, case: Case, *, keep: bool = True) -> Result:
    """Roda um caso com o agente real. Só na cadência; requer shell autenticado.

    Fail-closed: se a invocação do agente retornar non-zero (401, timeout,
    ausente), o veredito é FAIL — nunca se roda o oráculo sobre um workspace
    intocado (isso seria falso verde, ex.: 'não criou Diario/' porque o agente
    nem rodou).
    """
    tmp = tempfile.mkdtemp(prefix=f"conf-{scenario.id}-")
    ws = Path(tmp)
    _setup_workspace(scenario, ws)
    hosts.provision_skills(ws)  # pina a versão sob teste
    outcome = hosts.run_claude_code(ws, case.user_input)
    if outcome["returncode"] != 0:
        reason = (
            f"host claude_code falhou (rc={outcome['returncode']}): "
            f"{outcome['stderr'][:200].strip()}"
        )
        verdict = Verdict.failed(reason)
    else:
        params = dict(case.oracle_params)
        if scenario.oracle_wants_trace:
            # Sem trace no agente real até A1 (parser de tool calls): o oráculo
            # pula as checagens de trace — prova por estado, honestamente parcial.
            params["trace"] = None
        verdict = scenario.oracle(ws, **params)
    if not keep:
        shutil.rmtree(tmp, ignore_errors=True)
    return Result(scenario.id, case.variant, "claude_code", verdict, tmp)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runner de conformidade do Prumo")
    parser.add_argument("--scenario", required=True, help="id do cenário (ou 'all')")
    parser.add_argument("--host", choices=["replay", "claude_code"], default="replay")
    parser.add_argument(
        "--replay",
        choices=["compliant", "violation", "both"],
        default="both",
        help="qual gravação usar no host replay",
    )
    args = parser.parse_args(argv)

    targets = scenarios.SCENARIOS if args.scenario == "all" else [scenarios.by_id(args.scenario)]
    results: list[Result] = []
    for sc in targets:
        for case in sc.cases:
            if args.host == "claude_code":
                results.append(run_case_claude(sc, case))
            else:
                whichs = ["compliant", "violation"] if args.replay == "both" else [args.replay]
                for which in whichs:
                    results.append(run_case_replay(sc, case, which))

    ok = True
    for r in results:
        # No host replay: compliant deve passar, violation deve falhar.
        expected_ok = not (r.mode == "replay:violation")
        status = "ok" if r.verdict.ok == expected_ok else "INESPERADO"
        if status != "ok":
            ok = False
        print(f"[{status}] {r.scenario}/{r.variant} {r.mode}: {r.verdict.reason}")
    print(json.dumps({"total": len(results), "ok": ok}))
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
