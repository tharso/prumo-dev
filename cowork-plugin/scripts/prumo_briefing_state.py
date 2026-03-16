#!/usr/bin/env python3
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def now_iso(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).replace(microsecond=0).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Prumo briefing state safely.")
    parser.add_argument("--workspace", default=".", help="Workspace root that contains _state/")
    parser.add_argument("--timezone", default="America/Sao_Paulo", help="IANA timezone name")
    parser.add_argument("--mode", choices=["start", "complete", "interrupt", "expire"], required=True)
    parser.add_argument("--resume-point", default="", help="Resume point used for interrupt mode")
    args = parser.parse_args()

    state_path = Path(args.workspace) / "_state" / "briefing-state.json"
    state = load_state(state_path)

    if args.mode == "start":
        state["last_briefing_at"] = now_iso(args.timezone)
        state.pop("interrupted_at", None)
        state.pop("resume_point", None)
    elif args.mode == "complete":
        state.pop("interrupted_at", None)
        state.pop("resume_point", None)
        if not state.get("last_briefing_at"):
            state["last_briefing_at"] = now_iso(args.timezone)
    elif args.mode == "interrupt":
        if not state.get("last_briefing_at"):
            state["last_briefing_at"] = now_iso(args.timezone)
        state["interrupted_at"] = now_iso(args.timezone)
        state["resume_point"] = args.resume_point or "bloco2_proposta"
    elif args.mode == "expire":
        state.pop("interrupted_at", None)
        state.pop("resume_point", None)

    write_state(state_path, state)
    print(state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
