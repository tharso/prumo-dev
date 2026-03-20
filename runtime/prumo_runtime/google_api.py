from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from prumo_runtime.google_integration import (
    DEFAULT_GOOGLE_PROFILE,
    load_google_integration,
    load_oauth_bundle_from_keychain,
    store_oauth_bundle_in_keychain,
    update_profile_state,
)
from prumo_runtime.workspace import WorkspaceError, load_json, now_iso

GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GOOGLE_TASKLISTS_URL = "https://tasks.googleapis.com/tasks/v1/users/@me/lists"
LOW_SIGNAL_SENDER_RE = re.compile(
    r"(no-?reply|newsletter|notifications?|google alerts|medium daily digest|substack|beehiiv|mailchimp|noreply)",
    re.IGNORECASE,
)
LOW_SIGNAL_SUBJECT_RE = re.compile(
    r"(upgraded to a paid google cloud account|terms of service|receipt|invoice|newsletter|daily digest|billing profile|faturamento recebido|welcome to google cloud)",
    re.IGNORECASE,
)
ACTIONABLE_SUBJECT_RE = re.compile(
    r"(urgente|cancelad|cancelamento|erro|problema|faltando|verifica|verification|codigo|c[oó]digo|recovery|recupera|ajuste|confirm|deadline|prazo|falhou|failed|rejeitad|suspens|compra)",
    re.IGNORECASE,
)
LOW_SIGNAL_HINTS = (
    "upgraded to a paid google cloud account",
    "terms of service",
    "billing profile",
    "newsletter",
    "daily digest",
    "faturamento recebido",
    "welcome to google cloud",
)
GOOGLE_TASKS_SCOPE = "https://www.googleapis.com/auth/tasks.readonly"


def connected_google_profile(workspace: Path, preferred_profile: str | None = None) -> str | None:
    payload = load_google_integration(workspace)
    active = preferred_profile or str(payload.get("active_profile") or DEFAULT_GOOGLE_PROFILE)
    profiles = payload.get("profiles") or {}
    preferred = profiles.get(active)
    if isinstance(preferred, dict) and preferred.get("status") == "connected":
        return active
    for name, profile_payload in profiles.items():
        if isinstance(profile_payload, dict) and profile_payload.get("status") == "connected":
            return name
    return None


def refresh_google_access_token(workspace: Path, profile: str, timezone_name: str) -> tuple[str, dict]:
    try:
        bundle = load_oauth_bundle_from_keychain(workspace, profile)
    except RuntimeError as exc:
        raise WorkspaceError(str(exc)) from exc

    client = bundle.get("oauth_client") or {}
    token_payload = bundle.get("token_payload") or {}
    refresh_token = str(token_payload.get("refresh_token") or "").strip()
    if not refresh_token:
        raise WorkspaceError("refresh_token ausente no Keychain; a integracao nasceu sem perna para andar sozinha")

    token_uri = str(client.get("token_uri") or "").strip()
    client_id = str(client.get("client_id") or "").strip()
    client_secret = str(client.get("client_secret") or "").strip()
    if not token_uri or not client_id:
        raise WorkspaceError("oauth client incompleto no Keychain; sem isso o refresh vira figuracao")

    form = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    request = urllib.request.Request(
        token_uri,
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            refreshed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        body_lower = body.lower()
        if exc.code in {400, 401} and (
            "invalid_grant" in body_lower
            or "invalid_client" in body_lower
            or "unauthorized_client" in body_lower
        ):
            integration = load_google_integration(workspace)
            profile_payload = integration["profiles"].get(profile, {})
            account_email = str(profile_payload.get("account_email") or "")
            scopes = list(profile_payload.get("scopes") or [])
            update_profile_state(
                workspace,
                profile,
                status="needs_reauth",
                account_email=account_email,
                scopes=scopes,
                last_error="Google recusou o refresh token; rode `prumo auth google --workspace ...` de novo.",
            )
            raise WorkspaceError(
                "Google pediu reautenticacao; rode `prumo auth google --workspace ...` antes de culpar o briefing"
            ) from exc
        raise WorkspaceError(f"falha refrescando token Google: HTTP {exc.code} {body}") from exc

    access_token = str(refreshed.get("access_token") or "").strip()
    if not access_token:
        raise WorkspaceError("Google nao devolveu access_token; parece piada interna da API, mas e so erro mesmo")

    updated_token = dict(token_payload)
    updated_token.update(refreshed)
    if "refresh_token" not in refreshed:
        updated_token["refresh_token"] = refresh_token
    bundle["token_payload"] = updated_token
    store_oauth_bundle_in_keychain(workspace, profile, bundle)

    integration = load_google_integration(workspace)
    profile_payload = integration["profiles"].get(profile, {})
    account_email = str(profile_payload.get("account_email") or "")
    scopes = list(profile_payload.get("scopes") or [])
    update_profile_state(
        workspace,
        profile,
        status="connected",
        account_email=account_email,
        scopes=scopes,
        last_refresh_at=now_iso(timezone_name),
        last_error="",
    )
    return access_token, integration["profiles"].get(profile, {})


def google_api_get_json(url: str, access_token: str, timeout: int = 20) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise WorkspaceError(f"falha consultando Google API: HTTP {exc.code} {body}") from exc


def google_api_path(path: str, base_url: str) -> str:
    if base_url.endswith("/"):
        return base_url + path.lstrip("/")
    return base_url + "/" + path.lstrip("/")


def format_event_time(item: dict, timezone_name: str) -> tuple[str, datetime]:
    start = item.get("start") or {}
    end = item.get("end") or {}
    tz = ZoneInfo(timezone_name)
    if start.get("dateTime"):
        start_dt = datetime.fromisoformat(str(start["dateTime"]).replace("Z", "+00:00")).astimezone(tz)
        label = start_dt.strftime("%H:%M")
        if end.get("dateTime"):
            end_dt = datetime.fromisoformat(str(end["dateTime"]).replace("Z", "+00:00")).astimezone(tz)
            label = f"{label}-{end_dt.strftime('%H:%M')}"
        return label, start_dt
    if start.get("date"):
        start_day = datetime.fromisoformat(str(start["date"])).replace(tzinfo=tz)
        return "dia inteiro", start_day
    fallback = datetime.now(tz)
    return "horário indefinido", fallback


def fetch_calendar_events(access_token: str, timezone_name: str, profile: str) -> tuple[list[str], list[str]]:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    day_after_start = today_start + timedelta(days=2)

    params = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "timeMin": today_start.isoformat(),
        "timeMax": day_after_start.isoformat(),
        "timeZone": timezone_name,
    }
    base_url = os.environ.get("PRUMO_GOOGLE_CALENDAR_EVENTS_URL", GOOGLE_CALENDAR_EVENTS_URL).strip()
    payload = google_api_get_json(f"{base_url}?{urllib.parse.urlencode(params)}", access_token)

    agenda_today: list[tuple[datetime, str]] = []
    agenda_tomorrow: list[tuple[datetime, str]] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        label, start_dt = format_event_time(item, timezone_name)
        summary = str(item.get("summary") or "Evento sem titulo").strip()
        rendered = f"{label} | {profile} | {summary}"
        if start_dt.date() == today_start.date():
            agenda_today.append((start_dt, rendered))
        elif start_dt.date() == tomorrow_start.date():
            agenda_tomorrow.append((start_dt, rendered))

    agenda_today.sort(key=lambda item: item[0])
    agenda_tomorrow.sort(key=lambda item: item[0])
    return [item[1] for item in agenda_today], [item[1] for item in agenda_tomorrow]


def parse_google_due_datetime(value: str, timezone_name: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo(timezone_name))
    except ValueError:
        return None


def fetch_tasks_today(
    access_token: str,
    timezone_name: str,
    profile: str,
) -> list[str]:
    base_url = os.environ.get("PRUMO_GOOGLE_TASKLISTS_URL", GOOGLE_TASKLISTS_URL).strip()
    tasklists_payload = google_api_get_json(base_url, access_token)
    tasklists = tasklists_payload.get("items", []) or []
    tz = ZoneInfo(timezone_name)
    today = datetime.now(tz).date()
    rendered_items: list[tuple[datetime, str]] = []

    for tasklist in tasklists[:10]:
        if not isinstance(tasklist, dict):
            continue
        tasklist_id = str(tasklist.get("id") or "").strip()
        if not tasklist_id:
            continue
        tasklist_title = str(tasklist.get("title") or "Lista").strip()
        params = {
            "showCompleted": "false",
            "showHidden": "false",
            "showDeleted": "false",
            "maxResults": "20",
        }
        tasks_url = google_api_path(
            f"{urllib.parse.quote(tasklist_id, safe='')}/tasks?{urllib.parse.urlencode(params)}",
            base_url,
        )
        tasks_payload = google_api_get_json(tasks_url, access_token)
        for item in tasks_payload.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("status") or "").strip() == "completed":
                continue
            due_value = parse_google_due_datetime(str(item.get("due") or ""), timezone_name)
            if due_value is None or due_value.date() != today:
                continue
            title = str(item.get("title") or "Tarefa sem titulo").strip()
            rendered_items.append(
                (
                    due_value,
                    f"dia inteiro | {profile} | [Tasks] {title} ({tasklist_title})",
                )
            )

    rendered_items.sort(key=lambda pair: (pair[0], pair[1].lower()))
    return [item[1] for item in rendered_items]


def gmail_since_query(workspace: Path, timezone_name: str) -> str:
    state = load_json(workspace / "_state" / "briefing-state.json")
    last_briefing_at = str(state.get("last_briefing_at") or "").strip()
    if not last_briefing_at:
        return "in:inbox newer_than:2d -category:promotions -category:social"
    try:
        dt_value = datetime.fromisoformat(last_briefing_at)
    except ValueError:
        return "in:inbox newer_than:2d -category:promotions -category:social"
    ts = int(dt_value.timestamp())
    return f"in:inbox after:{ts} -category:promotions -category:social"


def header_map(payload: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for header in payload.get("payload", {}).get("headers", []):
        if not isinstance(header, dict):
            continue
        name = str(header.get("name") or "").strip().lower()
        value = str(header.get("value") or "").strip()
        if name:
            result[name] = value
    return result


def compact_message_time(detail: dict, timezone_name: str) -> str:
    internal_date = str(detail.get("internalDate") or "").strip()
    if internal_date.isdigit():
        dt_value = datetime.fromtimestamp(int(internal_date) / 1000, tz=ZoneInfo(timezone_name))
        return dt_value.strftime("%H:%M")
    headers = header_map(detail)
    if headers.get("date"):
        try:
            dt_value = parsedate_to_datetime(headers["date"]).astimezone(ZoneInfo(timezone_name))
            return dt_value.strftime("%H:%M")
        except Exception:
            pass
    return "??:??"


def is_low_signal_sender(sender: str, subject: str, headers: dict[str, str]) -> bool:
    haystack = " ".join([sender, subject, headers.get("list-id", ""), headers.get("precedence", "")])
    return bool(LOW_SIGNAL_SENDER_RE.search(haystack) or LOW_SIGNAL_SUBJECT_RE.search(subject))


def is_actionable_subject(subject: str, snippet: str = "") -> bool:
    haystack = f"{subject} {snippet}".strip()
    return bool(ACTIONABLE_SUBJECT_RE.search(haystack))


def is_actionworthy_triage_item(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith("p1 |"):
        return True
    return not any(hint in lowered for hint in LOW_SIGNAL_HINTS)


def compact_sender(sender: str) -> str:
    if "<" in sender:
        return sender.split("<", 1)[0].strip().strip('"') or sender
    return sender


def fetch_gmail_triage(
    access_token: str,
    workspace: Path,
    timezone_name: str,
) -> tuple[int, list[str], list[str], list[str], str, str]:
    base_url = os.environ.get("PRUMO_GOOGLE_GMAIL_MESSAGES_URL", GOOGLE_GMAIL_MESSAGES_URL).strip()
    query = gmail_since_query(workspace, timezone_name)
    params = {"maxResults": "10", "q": query}
    listing = google_api_get_json(f"{base_url}?{urllib.parse.urlencode(params)}", access_token)
    messages = listing.get("messages", []) or []
    if not messages:
        return (
            0,
            [],
            [],
            [],
            "Gmail API respondeu vazio; pelo menos desta vez foi vazio honesto.",
            "Nenhum email novo.",
        )

    view_items: list[str] = []
    no_action_items: list[str] = []
    reply_items: list[str] = []
    total = len(messages)
    for item in messages[:10]:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        detail_url = f"{base_url}/{item['id']}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date&metadataHeaders=List-Id&metadataHeaders=Precedence"
        detail = google_api_get_json(detail_url, access_token)
        headers = header_map(detail)
        subject = headers.get("subject") or "(sem assunto)"
        sender = compact_sender(headers.get("from") or "remetente desconhecido")
        snippet = str(detail.get("snippet") or "").replace("\n", " ").strip()
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        priority = "P1" if is_actionable_subject(subject, snippet) else "P2"
        rendered = f"{priority} | {compact_message_time(detail, timezone_name)} | {sender} | {subject} | {snippet or 'sem preview'}"
        if is_low_signal_sender(headers.get("from", ""), subject, headers):
            no_action_items.append(rendered)
        else:
            view_items.append(rendered)

    email_note = "email veio direto da Gmail API (triagem conservadora; melhor isso do que teatralidade confiante)."
    email_display = "Email veio direto da Gmail API."
    return total, reply_items, view_items, no_action_items, email_note, email_display


def fetch_google_workspace_snapshot(
    workspace: Path,
    timezone_name: str,
    *,
    profile: str | None = None,
) -> dict:
    selected_profile = connected_google_profile(workspace, profile)
    if not selected_profile:
        raise WorkspaceError("nenhum perfil Google conectado no runtime")

    access_token, profile_payload = refresh_google_access_token(workspace, selected_profile, timezone_name)
    account_email = str(profile_payload.get("account_email") or "desconhecido")
    scopes = list(profile_payload.get("scopes") or [])

    agenda_today, agenda_tomorrow = fetch_calendar_events(access_token, timezone_name, selected_profile)
    tasks_note = ""
    if GOOGLE_TASKS_SCOPE in scopes:
        try:
            tasks_today = fetch_tasks_today(access_token, timezone_name, selected_profile)
            agenda_today.extend(tasks_today)
        except WorkspaceError as exc:
            error_text = str(exc).lower()
            if "http 403" in error_text or "insufficient" in error_text or "permission" in error_text:
                tasks_note = (
                    "Tasks API recusou acesso; alguns lembretes do Google ainda podem ficar de fora. "
                    "Rode `prumo auth google --workspace ...` de novo se quiser alinhá-la."
                )
            else:
                tasks_note = (
                    "Tasks API respondeu torto; ignorei o tropeço para o briefing não virar teatro de desastre."
                )
    else:
        tasks_note = (
            "Tasks API ainda não está conectada neste perfil; alguns lembretes do Google podem ficar de fora. "
            "Rode `prumo auth google --workspace ...` de novo para incluir isso."
        )
    emails_total, triage_reply, triage_view, triage_no_action, email_note, email_display = fetch_gmail_triage(
        access_token,
        workspace,
        timezone_name,
    )

    agenda_note = "agenda veio direto da Google Calendar API."
    if tasks_note:
        agenda_note = f"{agenda_note} {tasks_note}"

    return {
        "status": "ok",
        "note": agenda_note,
        "email_note": email_note,
        "email_display": email_display,
        "source": "google-direct-api",
        "ok_profiles": 1,
        "profiles": {
            selected_profile: {
                "status": "OK",
                "account": account_email,
                "agenda_today": agenda_today,
                "agenda_tomorrow": agenda_tomorrow,
                "emails_total": emails_total,
                "triage_reply": triage_reply,
                "triage_view": triage_view,
                "triage_no_action": triage_no_action,
                "errors": [],
            }
        },
    }
