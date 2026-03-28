from __future__ import annotations

import json
import os
from shutil import which as shutil_which
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.constants import RUNTIME_VERSION, repo_root_from
from prumo_runtime.constants import ADAPTER_CONTRACT_VERSION, canonical_refs_from
from prumo_runtime.daily_operator import (
    build_daily_actions,
    daily_operation_payload,
    next_move_payload,
    selection_contract_payload,
)
from prumo_runtime.google_api import (
    connected_google_profile,
    fetch_google_workspace_snapshot,
    is_actionworthy_triage_item,
)
from prumo_runtime.google_integration import google_integration_summary
from prumo_runtime.inbox_preview import find_existing_path, load_inbox_preview, summarize_inbox_entry
from prumo_runtime.workspace import (
    build_config_from_existing,
    extract_section,
    load_json,
    parse_core_version,
    read_text,
    semantic_version_key,
    update_briefing_state,
    workspace_overview,
    write_json,
)


def list_or_placeholder(items: list[str], fallback: str) -> str:
    if not items:
        return fallback
    return "; ".join(items[:3])


def count_inbox_items(inbox_text: str) -> int:
    count = 0
    for line in inbox_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("- ", "* ")):
            count += 1
        elif stripped[:2].isdigit() and stripped[2:4] == ". ":
            count += 1
    return count


def snapshot_script_path(workspace: Path, repo_root: Path | None) -> Path | None:
    env_path = os.environ.get("PRUMO_RUNTIME_SNAPSHOT_SCRIPT")
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.append(workspace / "scripts" / "prumo_google_dual_snapshot.sh")
    if repo_root is not None:
        candidates.append(
            repo_root
            / "cowork-plugin"
            / "skills"
            / "prumo"
            / "references"
            / "prumo-google-dual-snapshot.sh"
        )
    return find_existing_path(candidates)


def snapshot_cache_path(workspace: Path) -> Path:
    return workspace / "_state" / "google-dual-snapshot.json"


def now_iso(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).replace(microsecond=0).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def age_in_minutes(value: str | None, timezone_name: str) -> int | None:
    dt_value = parse_iso_datetime(value)
    if dt_value is None:
        return None
    now = datetime.now(ZoneInfo(timezone_name))
    return max(0, int((now - dt_value).total_seconds() // 60))


def humanize_age_minutes(age_minutes: int | None) -> str | None:
    if age_minutes is None:
        return None
    if age_minutes < 60:
        return f"{age_minutes} min atrás"
    hours = age_minutes // 60
    minutes = age_minutes % 60
    return f"{hours}h{minutes:02d} atrás" if minutes else f"{hours}h atrás"


def short_clock(value: str | None, timezone_name: str) -> str | None:
    dt_value = parse_iso_datetime(value)
    if dt_value is None:
        return None
    return dt_value.astimezone(ZoneInfo(timezone_name)).strftime("%H:%M")


def same_local_day(value: str | None, timezone_name: str) -> bool:
    dt_value = parse_iso_datetime(value)
    if dt_value is None:
        return False
    now = datetime.now(ZoneInfo(timezone_name))
    return dt_value.astimezone(ZoneInfo(timezone_name)).date() == now.date()


def parse_snapshot_output(output: str) -> dict:
    result = {"profiles": {}, "ok_profiles": 0}
    current_profile: str | None = None
    current_section: str | None = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## Perfil:"):
            current_profile = line.split(":", 1)[1].strip()
            result["profiles"][current_profile] = {
                "status": "unknown",
                "account": "desconhecido",
                "agenda_today": [],
                "agenda_tomorrow": [],
                "emails_total": 0,
                "triage_reply": [],
                "triage_view": [],
                "triage_no_action": [],
                "errors": [],
            }
            current_section = None
            continue
        if current_profile is None:
            continue

        profile = result["profiles"][current_profile]
        if line.startswith("- Status:"):
            status = line.split(":", 1)[1].strip()
            profile["status"] = status
            if status.startswith("OK") or status.startswith("AVISO"):
                result["ok_profiles"] += 1
            continue
        if line.startswith("CONTA:"):
            profile["account"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("EMAILS_DESDE_ULTIMO_BRIEFING_TOTAL:"):
            raw_value = line.split(":", 1)[1].strip()
            try:
                profile["emails_total"] = int(raw_value)
            except ValueError:
                profile["emails_total"] = 0
            continue
        if line.endswith(":") and line in {
            "AGENDA_HOJE:",
            "AGENDA_AMANHA:",
            "TRIAGEM_RESPONDER:",
            "TRIAGEM_VER:",
            "TRIAGEM_SEM_ACAO:",
            "ERROS:",
        }:
            current_section = line[:-1]
            continue
        if line.startswith("- ") and current_section:
            payload = line[2:].strip()
            if payload.lower() == "nenhum":
                continue
            if current_section == "AGENDA_HOJE":
                profile["agenda_today"].append(payload)
            elif current_section == "AGENDA_AMANHA":
                profile["agenda_tomorrow"].append(payload)
            elif current_section == "TRIAGEM_RESPONDER":
                profile["triage_reply"].append(payload)
            elif current_section == "TRIAGEM_VER":
                profile["triage_view"].append(payload)
            elif current_section == "TRIAGEM_SEM_ACAO":
                profile["triage_no_action"].append(payload)
            elif current_section == "ERROS" and payload.lower() != "nenhum":
                profile["errors"].append(payload)

    return result


def load_snapshot_cache(workspace: Path, timezone_name: str) -> dict | None:
    payload = load_json(snapshot_cache_path(workspace))
    if not payload:
        return None
    cached_at = payload.get("cached_at")
    age = age_in_minutes(cached_at, timezone_name)
    cached_note = str(payload.get("note") or "").strip()
    source = str(payload.get("source") or "google-dual-snapshot")
    base_label = "snapshot dual" if source == "google-dual-snapshot" else "snapshot"
    human_age = humanize_age_minutes(age)
    cache_prefix = (
        f"{base_label} reaproveitado do cache local ({human_age})"
        if human_age is not None
        else f"{base_label} reaproveitado do cache local"
    )
    payload["status"] = "cache"
    payload["note"] = (
        f"{cached_note} {cache_prefix}."
        if cached_note
        else f"{cache_prefix}."
    )
    payload["cache_age_minutes"] = age
    return payload


def write_snapshot_cache(workspace: Path, timezone_name: str, snapshot: dict) -> None:
    payload = {
        "cached_at": now_iso(timezone_name),
        "ok_profiles": snapshot.get("ok_profiles", 0),
        "profiles": snapshot.get("profiles", {}),
        "source": "google-dual-snapshot",
        "note": snapshot.get("note", ""),
        "email_note": snapshot.get("email_note", ""),
        "email_display": snapshot.get("email_display", ""),
    }
    if snapshot.get("source"):
        payload["source"] = snapshot["source"]
    write_json(snapshot_cache_path(workspace), payload)


def resolve_snapshot_data(
    workspace: Path,
    repo_root: Path | None,
    refresh_snapshot: bool = False,
) -> dict:
    timezone_name = infer_timezone_name(workspace)
    cached = load_snapshot_cache(workspace, timezone_name)
    if cached and not refresh_snapshot:
        return cached
    google = google_integration_summary(workspace)
    connected_profile = connected_google_profile(workspace)
    if not connected_profile and google.get("active_profile_status") == "needs_reauth":
        note = "Google pediu reautenticacao; rode `prumo auth google --workspace ...`."
        if cached:
            cached["note"] = f"{cached['note']} {note}"
            return cached
        return {
            "status": "needs_reauth",
            "note": note,
            "email_note": "Nenhum email novo por enquanto; a integracao Google esta pedindo reauth.",
            "profiles": {},
            "ok_profiles": 0,
            "source": "google-direct-api",
        }
    if connected_profile:
        try:
            direct_snapshot = fetch_google_workspace_snapshot(
                workspace,
                timezone_name,
                profile=connected_profile,
            )
            write_snapshot_cache(workspace, timezone_name, direct_snapshot)
            direct_snapshot["cached_at"] = now_iso(timezone_name)
            return direct_snapshot
        except Exception as exc:
            if cached:
                cached["note"] = f"{cached['note']} Google API falhou ({exc}); usei cache."
                return cached
            fallback_snapshot = run_dual_snapshot(workspace, repo_root)
            if fallback_snapshot.get("ok_profiles", 0):
                fallback_snapshot["note"] = (
                    f"Google API falhou ({exc}). "
                    f"{fallback_snapshot.get('note') or 'Segui pelo fallback que ainda respirava.'}"
                )
                return fallback_snapshot
            return {
                "status": "error",
                "note": f"Google API falhou ({exc})",
                "email_note": "email direto via Gmail API ainda nao entrou; briefing segue sem isso por enquanto.",
                "email_display": "Nenhum email novo por enquanto.",
                "profiles": {},
                "ok_profiles": 0,
                "source": "google-direct-api",
            }
    fallback_snapshot = run_dual_snapshot(workspace, repo_root)
    return fallback_snapshot


def run_dual_snapshot(workspace: Path, repo_root: Path | None) -> dict:
    timezone_name = infer_timezone_name(workspace)
    if os.environ.get("PRUMO_RUNTIME_DISABLE_SNAPSHOT") == "1":
        cached = load_snapshot_cache(workspace, timezone_name)
        if cached:
            cached["note"] = f"{cached['note']} Fonte ao vivo desligada por ambiente."
            return cached
        return {"status": "disabled", "note": "snapshot dual desligado por ambiente", "profiles": {}, "ok_profiles": 0}

    script_path = snapshot_script_path(workspace, repo_root)
    if script_path is None:
        cached = load_snapshot_cache(workspace, timezone_name)
        if cached:
            cached["note"] = f"{cached['note']} Script dual indisponível."
            return cached
        return {"status": "unavailable", "note": "script dual indisponível", "profiles": {}, "ok_profiles": 0}

    if shutil_which("gemini") is None:
        cached = load_snapshot_cache(workspace, timezone_name)
        if cached:
            cached["note"] = f"{cached['note']} Gemini CLI ausente; usei memória local."
            return cached
        return {"status": "unavailable", "note": "gemini CLI ausente; sem snapshot dual", "profiles": {}, "ok_profiles": 0}

    env = os.environ.copy()
    env["TZ_NAME"] = env.get("TZ_NAME", "America/Sao_Paulo")
    env["STATE_FILE"] = str(workspace / "_state" / "briefing-state.json")
    env["GEMINI_TIMEOUT_SEC"] = env.get("GEMINI_TIMEOUT_SEC", "15")
    process_timeout = int(env.get("PRUMO_SNAPSHOT_PROCESS_TIMEOUT_SEC", "25"))

    try:
        completed = subprocess.run(
            ["bash", str(script_path)],
            cwd=str(workspace),
            check=True,
            capture_output=True,
            text=True,
            timeout=process_timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        partial_output = exc.stdout or ""
        if isinstance(partial_output, bytes):
            partial_output = partial_output.decode("utf-8", errors="replace")
        parsed = parse_snapshot_output(partial_output or "")
        if parsed.get("ok_profiles"):
            parsed["status"] = "partial"
            parsed["note"] = "snapshot dual terminou pela metade; preservei o que chegou antes do estouro."
            write_snapshot_cache(workspace, timezone_name, parsed)
            return parsed
        cached = load_snapshot_cache(workspace, timezone_name)
        if cached:
            cached["note"] = f"{cached['note']} Fonte ao vivo passou do limite."
            return cached
        return {"status": "timeout", "note": "snapshot dual passou do limite e foi deixado pra lá", "profiles": {}, "ok_profiles": 0}
    except subprocess.CalledProcessError as exc:
        output = (exc.stdout or "") + ("\n" + exc.stderr if exc.stderr else "")
        parsed = parse_snapshot_output(output)
        parsed["status"] = "partial" if parsed.get("ok_profiles") else "error"
        parsed["note"] = "snapshot dual respondeu torto; preservei o que prestava." if parsed.get("ok_profiles") else "snapshot dual falhou."
        if parsed.get("ok_profiles"):
            write_snapshot_cache(workspace, timezone_name, parsed)
            return parsed
        cached = load_snapshot_cache(workspace, timezone_name)
        if cached:
            cached["note"] = f"{cached['note']} Fonte ao vivo falhou."
            return cached
        return parsed

    parsed = parse_snapshot_output(completed.stdout)
    parsed["status"] = "ok" if parsed.get("ok_profiles") else "empty"
    parsed["note"] = "snapshot dual sem contas úteis." if not parsed.get("ok_profiles") else ""
    if parsed.get("ok_profiles"):
        write_snapshot_cache(workspace, timezone_name, parsed)
        parsed["cached_at"] = now_iso(timezone_name)
    return parsed


def infer_timezone_name(workspace: Path) -> str:
    schema = load_json(workspace / "_state" / "workspace-schema.json")
    value = schema.get("timezone")
    return str(value) if value else "America/Sao_Paulo"


def summarize_agenda(snapshot: dict) -> str:
    items: list[str] = []
    for profile_name, profile in snapshot.get("profiles", {}).items():
        for event in profile.get("agenda_today", [])[:3]:
            items.append(f"[{profile_name}] {event}")
    if not items:
        note = snapshot.get("note") or "Sem agenda consolidada via snapshot local."
        return note
    summary = "; ".join(items[:4])
    if snapshot.get("note"):
        summary = f"{summary}. {snapshot['note']}"
    return summary


def compact_triage_item(value: str) -> str:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) >= 4:
        return f"{parts[0]} {parts[2]} — {parts[3]}"
    return value


def summarize_emails(snapshot: dict) -> str:
    email_note = snapshot.get("email_note")
    email_display = snapshot.get("email_display")
    if snapshot.get("ok_profiles", 0) == 0:
        note = email_display or email_note or snapshot.get("note") or "Sem email consolidado via snapshot local."
        return note

    total = 0
    reply: list[str] = []
    view: list[str] = []
    no_action = 0
    for profile in snapshot.get("profiles", {}).values():
        total += int(profile.get("emails_total") or 0)
        reply.extend(profile.get("triage_reply", []))
        view.extend(profile.get("triage_view", []))
        no_action += len(profile.get("triage_no_action", []))

    if total == 0:
        display = email_display or "Nenhum email novo."
        return f"{display} {email_note}".strip() if email_note else display

    highlights = [compact_triage_item(item) for item in (reply + view)[:3]]
    parts = [
        f"{total} email(ns) desde a última janela",
        f"Responder: {len(reply)}",
        f"Ver: {len(view)}",
        f"Sem ação: {no_action}",
    ]
    if highlights:
        parts.append("Destaques: " + "; ".join(highlights))
    if email_display:
        parts.append(email_display)
    elif email_note:
        parts.append(email_note)
    elif snapshot.get("status") == "cache":
        note = snapshot.get("note")
        if note:
            parts.append(note)
    return ". ".join(parts) + "."


def summarize_google_status(workspace: Path, timezone_name: str) -> str:
    google = google_integration_summary(workspace)
    status = str(google.get("active_profile_status") or google.get("status") or "disconnected")
    account = str(google.get("active_account_email") or "").strip()
    last_refresh = short_clock(str(google.get("active_last_refresh_at") or ""), timezone_name)
    last_refresh_age = age_in_minutes(str(google.get("active_last_refresh_at") or ""), timezone_name)
    last_auth = short_clock(str(google.get("active_last_authenticated_at") or ""), timezone_name)
    last_error = str(google.get("active_last_error") or "").strip()

    if status == "connected":
        who = account or str(google.get("active_profile") or "perfil ativo")
        if last_refresh:
            age_suffix = ""
            human_age = humanize_age_minutes(last_refresh_age)
            if human_age:
                age_suffix = f", {human_age}"
            return f"conectado ({who}, ultimo refresh {last_refresh}{age_suffix})"
        if last_auth:
            return f"conectado ({who}, auth {last_auth})"
        return f"conectado ({who})"

    if status == "needs_reauth":
        who = account or str(google.get("active_profile") or "perfil ativo")
        detail = f" precisa reautenticar ({who})"
        if last_error:
            detail = f"{detail}. {last_error}"
        return detail + " Rode `prumo auth google --workspace ...`."

    if status == "disconnected":
        return "desconectado. Rode `prumo auth google --workspace ...` se quiser agenda e email diretos."

    return f"{status}. Rode `prumo context-dump --workspace ... --format json` antes de chutar a parede."


def build_inbox_line(workspace: Path, inbox_text: str, preview: dict) -> str:
    inbox_count = count_inbox_items(inbox_text)
    preview_count = int(preview.get("count") or 0)
    preview_path = preview.get("preview_path")
    preview_hint = ""
    if isinstance(preview_path, Path) and preview_path.exists():
        preview_hint = f" Preview: `{preview_path}`."

    if preview_count == 0 and (preview.get("status") in {"gerado", "stale"}):
        note = preview.get("note") or "Inbox4Mobile sem itens novos."
        return f"Inbox4Mobile: 0 item(ns). {note}{preview_hint}".strip()

    if preview_count == 0:
        if inbox_count == 0 or "_Inbox limpo._" in inbox_text:
            return "Inbox4Mobile: 0 item(ns). Inbox limpa."
        return f"INBOX.md acusa {inbox_count} item(ns), mas o preview local não trouxe vitrine.{preview_hint}"

    top_items = [summarize_inbox_entry(item) for item in preview.get("items", [])[:3]]
    summary = "; ".join(top_items) if top_items else "há item, mas sem resumo leve decente."
    note = f" {preview.get('note')}" if preview.get("note") else ""
    return f"Inbox4Mobile: {preview_count} item(ns). {summary}.{note}{preview_hint}"


def build_briefing_degradation(
    *,
    core_outdated: bool,
    snapshot: dict,
    overview: dict,
    next_move: dict[str, object] | None,
) -> dict[str, object]:
    alerts: list[dict[str, object]] = []
    if core_outdated:
        alerts.append(
            {
                "id": "core-outdated",
                "level": "warning",
                "summary": "O core do workspace está defasado em relação ao runtime.",
                "action_id": "align-core",
            }
        )

    snapshot_status = str(snapshot.get("status") or "")
    snapshot_note = str(snapshot.get("note") or "").strip()
    if snapshot_status in {"partial", "cache", "needs_reauth", "timeout", "unavailable", "disabled"}:
        alerts.append(
            {
                "id": f"snapshot-{snapshot_status}",
                "level": "warning",
                "summary": snapshot_note or f"Snapshot em estado {snapshot_status}.",
                "action_id": next_move["id"] if next_move and next_move["id"] in {"briefing", "auth-google", "auth-google-help"} else None,
            }
        )
    elif snapshot_status == "error":
        alerts.append(
            {
                "id": "snapshot-error",
                "level": "error",
                "summary": snapshot_note or "A coleta principal do briefing falhou sem fallback útil.",
                "action_id": next_move["id"] if next_move else None,
            }
        )

    google_status = str(overview["google_integration"]["active_profile_status"] or "")
    if google_status == "needs_reauth":
        alerts.append(
            {
                "id": "google-needs-reauth",
                "level": "warning",
                "summary": "Google pede reautenticação; briefing segue, mas a integração direta está manca.",
                "action_id": "auth-google",
            }
        )

    status = "ok"
    if any(alert["level"] == "error" for alert in alerts):
        status = "error"
    elif alerts:
        status = "partial"

    return {
        "status": status,
        "alerts": alerts,
    }


def choose_proposal(quente: list[str], agendado: list[str], andamento: list[str], snapshot: dict) -> str:
    if quente:
        return quente[0]
    if agendado:
        return agendado[0]
    for profile in snapshot.get("profiles", {}).values():
        triage_reply = profile.get("triage_reply", []) or []
        if triage_reply:
            return compact_triage_item(triage_reply[0])
        triage = [item for item in (profile.get("triage_view", []) or []) if is_actionworthy_triage_item(item)]
        if triage:
            return compact_triage_item(triage[0])
    if andamento:
        return andamento[0]
    for profile in snapshot.get("profiles", {}).values():
        triage_view = profile.get("triage_view", []) or []
        if triage_view:
            return compact_triage_item(triage_view[0])
    return "Fazer um dump real de pendências antes que o sistema vire paisagem."


def build_briefing_payload(workspace: Path, refresh_snapshot: bool = False) -> dict:
    workspace = workspace.expanduser().resolve()
    config = build_config_from_existing(workspace)
    repo_root = repo_root_from(Path(__file__))
    overview = workspace_overview(workspace)

    pauta_text = read_text(workspace / "PAUTA.md")
    inbox_text = read_text(workspace / "INBOX.md")
    quente = extract_section(pauta_text, "Quente (precisa de atenção agora)")
    andamento = extract_section(pauta_text, "Em andamento")
    agendado = extract_section(pauta_text, "Agendado / Lembretes")

    preview = load_inbox_preview(workspace, repo_root)
    snapshot = resolve_snapshot_data(
        workspace,
        repo_root,
        refresh_snapshot=refresh_snapshot,
    )

    update_briefing_state(workspace, config.timezone_name)
    briefing_state = load_json(workspace / "_state" / "briefing-state.json")
    last_briefing_at = str(briefing_state.get("last_briefing_at") or "").strip()
    has_briefed_today = same_local_day(last_briefing_at, config.timezone_name)

    core_version = parse_core_version(workspace)
    core_outdated = bool(core_version and semantic_version_key(core_version) < semantic_version_key(RUNTIME_VERSION))

    preflight_text = (
        f"o runtime está em {RUNTIME_VERSION}, mas o core do workspace está em {core_version}. "
        "Não é tragédia nuclear, mas é drift e merece atenção."
        if core_outdated
        else "runtime e workspace parecem minimamente alinhados."
    )
    google_text = summarize_google_status(workspace, config.timezone_name)
    agenda_text = summarize_agenda(snapshot)
    inbox_mobile_text = build_inbox_line(workspace, inbox_text, preview)
    emails_text = summarize_emails(snapshot)

    pauta_counts = {
        "quente": len(quente),
        "em_andamento": len(andamento),
        "agendado": len(agendado),
    }
    hottest = list_or_placeholder(quente or andamento or agendado, "Pauta sem tração aparente.")
    panorama_text = (
        f"Quente {pauta_counts['quente']} | Em andamento {pauta_counts['em_andamento']} | "
        f"Agendado {pauta_counts['agendado']}. {hottest}"
    )
    actions = build_daily_actions(workspace, overview, has_briefed_today=has_briefed_today)
    next_move = next_move_payload(actions)
    proposal = choose_proposal(quente, agendado, andamento, snapshot)
    daily_operation = daily_operation_payload(workspace)
    degradation = build_briefing_degradation(
        core_outdated=core_outdated,
        snapshot=snapshot,
        overview=overview,
        next_move=next_move,
    )

    sections = [
        {"id": "preflight", "label": "Preflight", "text": preflight_text},
        {"id": "google", "label": "Google", "text": google_text},
        {"id": "agenda", "label": "Agenda", "text": agenda_text},
        {"id": "inbox_mobile", "label": "Inbox mobile", "text": inbox_mobile_text},
        {"id": "emails", "label": "Emails", "text": emails_text},
        {"id": "panorama_local", "label": "Panorama local", "text": panorama_text},
        {
            "id": "proposta_do_dia",
            "label": "Proposta do dia",
            "text": (
                f"seguir por `{next_move['label']}`."
                if next_move
                else f"atacar primeiro `{proposal}`."
            ),
        },
        {
            "id": "operacao_do_dia",
            "label": "Operação do dia",
            "text": (
                "O briefing é só a porta. O trabalho de verdade é continuar, organizar e registrar "
                "o que muda no workspace sem transformar o host em comentarista de si mesmo."
            ),
        },
    ]

    lines: list[str] = []
    for index, section in enumerate(sections, start=1):
        lines.append(f"{index}. {section['label']}: {section['text']}")
    if next_move:
        lines.append(f"{len(sections) + 1}. Próximo movimento recomendado: {next_move['label']}")
        lines.append(f"   `{next_move['command']}`")
        if next_move.get("why_now"):
            lines.append(f"   Motivo: {next_move['why_now']}")
        lines.append(
            "   Resposta curta aceita: `1`, `a` ou `aceitar` deve executar esse próximo movimento sem reabrir menu."
        )
    if next_move:
        lines.append("a) Aceitar e seguir")
        lines.append("b) Ver lista completa")
        lines.append("c) Ver estado técnico")
        lines.append(f"   `prumo context-dump --workspace {workspace} --format json`")
        lines.append("d) Tá bom por hoje")
    else:
        option_labels = list("abcdef")
        for label, action in zip(option_labels, actions[:4]):
            lines.append(f"{label}) {action['label']}")
            lines.append(f"   `{action['command']}`")
        lines.append("a) Aceitar e seguir")
        lines.append("b) Ajustar")
        lines.append("c) Ver lista completa")
        lines.append("d) Tá bom por hoje")

    return {
        "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
        "workspace_path": str(workspace),
        "runtime_version": RUNTIME_VERSION,
        "core_version": core_version or "",
        "core_outdated": core_outdated,
        "platform": overview["platform"],
        "capabilities": overview["capabilities"],
        "daily_operation": daily_operation,
        "next_move": next_move,
        "selection_contract": selection_contract_payload(next_move),
        "last_briefing_at": last_briefing_at,
        "actions": actions,
        "sections": sections,
        "proposal": {
            "text": proposal,
            "next_move": next_move,
            "options": [
                {
                    "id": action["id"],
                    "label": action["label"],
                    "kind": action["kind"],
                    "command": action["command"],
                }
                for action in actions[:4]
            ],
        },
        "snapshot": {
            "status": str(snapshot.get("status") or ""),
            "source": str(snapshot.get("source") or ""),
            "ok_profiles": int(snapshot.get("ok_profiles") or 0),
            "note": str(snapshot.get("note") or ""),
            "email_note": str(snapshot.get("email_note") or ""),
            "email_display": str(snapshot.get("email_display") or ""),
        },
        "integration_status": {
            "google": {
                "status": str(overview["google_integration"]["active_profile_status"] or ""),
                "summary": google_text,
            },
        },
        "degradation": degradation,
        "canonical_refs": canonical_refs_from(Path(__file__)),
        "message": "\n".join(lines),
    }


def run_briefing(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    payload = build_briefing_payload(
        workspace,
        refresh_snapshot=bool(getattr(args, "refresh_snapshot", False)),
    )
    if getattr(args, "format", "text") == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
    return 0
