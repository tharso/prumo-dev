#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge experimental do Cowork para o runtime local do Prumo.")
    parser.add_argument("--workspace", required=True, help="Caminho do workspace do usuario")
    parser.add_argument(
        "--command",
        required=True,
        choices=["setup", "start", "briefing", "context-dump", "repair"],
        help="Comando do runtime a ser executado",
    )
    parser.add_argument("--user-name", help="Nome preferido do usuario (setup)")
    parser.add_argument("--agent-name", help="Nome do agente (setup)")
    parser.add_argument("--timezone", help="Fuso IANA (setup)")
    parser.add_argument("--briefing-time", help="Horario de briefing (setup)")
    parser.add_argument("--format", choices=["json", "markdown", "text"], help="Formato adicional")
    return parser


def resolve_runtime(workspace: Path) -> tuple[list[str], dict[str, str]]:
    env = os.environ.copy()
    prefer_repo = str(env.get("PRUMO_BRIDGE_PREFER_REPO") or "").strip() == "1"
    installed = shutil.which("prumo")
    if installed and not prefer_repo:
        return [installed], env

    candidates = [
        workspace / "Prumo" / "runtime",
        Path(__file__).resolve().parents[1] / "runtime",
    ]
    for runtime_dir in candidates:
        if runtime_dir.exists():
            current = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = (
                f"{runtime_dir}{os.pathsep}{current}" if current else str(runtime_dir)
            )
            return [shutil.which("python3") or sys.executable, "-m", "prumo_runtime"], env

    raise RuntimeError("runtime local do Prumo não encontrado")


def workspace_enabled(workspace: Path) -> bool:
    return (workspace / "AGENT.md").exists() and (workspace / "_state" / "workspace-schema.json").exists()


def build_runtime_call(args) -> tuple[list[str], dict[str, str]]:
    workspace = Path(args.workspace).expanduser().resolve()
    command, env = resolve_runtime(workspace)

    if args.command not in {"setup", "start"} and not workspace_enabled(workspace):
        raise FileNotFoundError("workspace ainda não está no trilho novo do runtime")

    command.extend([args.command, "--workspace", str(workspace)])
    if args.user_name:
        command.extend(["--user-name", args.user_name])
    if args.agent_name:
        command.extend(["--agent-name", args.agent_name])
    if args.timezone:
        command.extend(["--timezone", args.timezone])
    if args.briefing_time:
        command.extend(["--briefing-time", args.briefing_time])
    if args.format:
        command.extend(["--format", args.format])
    return command, env


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        command, env = build_runtime_call(args)
    except FileNotFoundError as exc:
        print(f"bridge-disabled: {exc}", file=sys.stderr)
        return 12
    except RuntimeError as exc:
        print(f"bridge-error: {exc}", file=sys.stderr)
        return 13

    result = subprocess.run(command, env=env, text=True, capture_output=True)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
