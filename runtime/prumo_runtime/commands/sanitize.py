"""`prumo sanitize` — motor determinístico do módulo `sanitize.md` (#179).

Dry-run é o default (read-only; salve o JSON pra virar plano). `--apply`
exige `--plan <arquivo>` (o relatório aprovado do dry-run) e `--yes`: a
aprovação do usuário acontece na conversa (o agente apresenta o dry-run,
colhe o sim) e o que executa é EXATAMENTE o plano aprovado — item novo ou
alterado desde então fica `blocked`. Nada roda automático (#172/#126).
"""

from __future__ import annotations

import json
from pathlib import Path

from prumo_runtime.sanitize import SanitizeError, Thresholds, apply_plan, build_plan


def _print_text(report: dict) -> None:
    print(f"[sanitize] modo: {report['mode']} — workspace {report['workspace_path']}")
    if not report["items"]:
        print("[sanitize] nada a fazer — `.prumo/` está enxuto.")
    for item in report["items"]:
        print(
            f"[sanitize]   {item['rule']:<28} {item['action']:<15} "
            f"{item['size_bytes']:>8}b  {item['path']}  ({item['reason']})"
        )
    totals = report["totals"]
    print(f"[sanitize] total: {totals['count']} item(ns), {totals['bytes']} bytes")
    if report["mode"] == "dry-run":
        print(
            "[sanitize] próximo passo: salve este relatório em JSON "
            "(`--format json > plano.json`), colha a aprovação e rode "
            "`prumo sanitize --apply --plan plano.json --yes`."
        )
    apply_info = report.get("apply")
    if apply_info:
        print(
            f"[sanitize] apply: {len(apply_info['moved'])} movido(s) → "
            f"{apply_info['backup_root'] or 'sem backup necessário'}, "
            f"{len(apply_info['deleted'])} removido(s), "
            f"{len(apply_info['blocked'])} bloqueado(s)"
        )
        for entry in apply_info["blocked"]:
            print(f"[sanitize]   bloqueado: {entry['path']} — {entry['reason']}")


def run_sanitize(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    if not (workspace / ".prumo").is_dir():
        print(f"workspace sem `.prumo/`: {workspace} — nada a sanitizar aqui.")
        return 1

    rules = None
    if args.rules is not None:
        rules = [rule.strip() for rule in args.rules.split(",") if rule.strip()]
        if not rules:
            print("`--rules` vazio não é \"tudo\" — nomeie as regras ou omita a flag.")
            return 2

    if args.apply and not args.yes:
        print(
            "`--apply` move/remove arquivos e exige aprovação explícita: "
            "rode o dry-run, colha o sim do usuário e repita com `--yes`."
        )
        return 2
    if args.apply and not args.plan:
        print(
            "`--apply` executa um plano aprovado: rode o dry-run "
            "(`prumo sanitize --format json > plano.json`), colha o sim e "
            "repita com `--plan plano.json`."
        )
        return 2

    try:
        if args.apply:
            try:
                plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"plano ilegível ({args.plan}): {exc}")
                return 2
            report = apply_plan(workspace, plan=plan, rules=rules)
        else:
            thresholds = Thresholds(
                ephemeral_days=args.ephemeral_days,
                backup_expiry_days=args.backup_expiry_days,
                cache_days=args.cache_days,
            )
            report = build_plan(workspace, thresholds=thresholds, rules=rules)
    except SanitizeError as exc:
        print(f"[sanitize] {exc}")
        return 2

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 0
