#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TMP_DIR="$(mktemp -d)"
WORKSPACE="$TMP_DIR/ws"
SERVICE_PREFIX="prumo.calendar.$RANDOM.$RANDOM"
PROVIDER_PID=""

cleanup() {
  if [[ -n "$PROVIDER_PID" ]]; then
    kill "$PROVIDER_PID" >/dev/null 2>&1 || true
    wait "$PROVIDER_PID" >/dev/null 2>&1 || true
  fi
  if [[ -f "$WORKSPACE/_state/google-integration.json" ]]; then
    SERVICE="$(python3 - <<'PY' "$WORKSPACE/_state/google-integration.json"
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
profile = payload["profiles"]["pessoal"]
print(profile["token_storage"]["service"])
print(profile["token_storage"]["account"])
PY
)"
    if [[ -n "$SERVICE" ]]; then
      SERVICE_NAME="$(echo "$SERVICE" | sed -n '1p')"
      ACCOUNT_NAME="$(echo "$SERVICE" | sed -n '2p')"
      security delete-generic-password -a "$ACCOUNT_NAME" -s "$SERVICE_NAME" >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

mkdir -p "$WORKSPACE"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime setup \
  --workspace "$WORKSPACE" \
  --user-name "Batata" \
  --agent-name "Prumo" \
  --timezone "America/Sao_Paulo" \
  --briefing-time "09:00" >/dev/null

cat >"$TMP_DIR/fake_google_calendar.py" <<'PY'
import json
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def iso_at(days: int, hour: int, minute: int) -> str:
    now = datetime.now(timezone.utc)
    base = now + timedelta(days=days)
    base = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base.isoformat().replace("+00:00", "Z")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_POST(self):
        if self.path != "/token":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(
            {
                "access_token": "ya29.fake-calendar-token",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/calendar/events"):
            body = json.dumps(
                {
                    "items": [
                        {
                            "summary": "Levar Nina à escola",
                            "start": {"dateTime": iso_at(0, 7, 0)},
                            "end": {"dateTime": iso_at(0, 7, 30)},
                        },
                        {
                            "summary": "Jantar laboratório",
                            "start": {"dateTime": iso_at(0, 20, 0)},
                            "end": {"dateTime": iso_at(0, 22, 0)},
                        },
                        {
                            "summary": "Exame amanhã",
                            "start": {"dateTime": iso_at(1, 9, 0)},
                            "end": {"dateTime": iso_at(1, 10, 0)},
                        },
                    ]
                }
            ).encode("utf-8")
        elif self.path.startswith("/gmail/messages?"):
            body = json.dumps(
                {
                    "messages": [
                        {"id": "m1"},
                        {"id": "m2"}
                    ]
                }
            ).encode("utf-8")
        elif self.path.startswith("/gmail/messages/m1"):
            body = json.dumps(
                {
                    "id": "m1",
                    "internalDate": "1768870800000",
                    "snippet": "Confirmar mudança no site antes de publicar",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Ajuste urgente no site"},
                            {"name": "From", "value": "Danilo <danilo@example.com>"},
                            {"name": "Date", "value": "Thu, 19 Mar 2026 10:00:00 -0300"}
                        ]
                    }
                }
            ).encode("utf-8")
        elif self.path.startswith("/gmail/messages/m2"):
            body = json.dumps(
                {
                    "id": "m2",
                    "internalDate": "1768874400000",
                    "snippet": "Resumo semanal das notícias",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Newsletter semanal"},
                            {"name": "From", "value": "News Bot <newsletter@example.com>"},
                            {"name": "Date", "value": "Thu, 19 Mar 2026 11:00:00 -0300"},
                            {"name": "List-Id", "value": "newsletter.example.com"}
                        ]
                    }
                }
            ).encode("utf-8")
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
PY

python3 "$TMP_DIR/fake_google_calendar.py" >"$TMP_DIR/provider.port" 2>"$TMP_DIR/provider.log" &
PROVIDER_PID="$!"

for _ in $(seq 1 50); do
  [[ -s "$TMP_DIR/provider.port" ]] && break
  sleep 0.1
done
[[ -s "$TMP_DIR/provider.port" ]] || fail "provedor Calendar fake nao subiu"
PROVIDER_PORT="$(head -n1 "$TMP_DIR/provider.port" | tr -d '[:space:]')"

python3 - <<'PY' "$WORKSPACE" "$PROVIDER_PORT" "$SERVICE_PREFIX"
import json
import os
import subprocess
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
provider_port = sys.argv[2]
service_prefix = sys.argv[3]
integration_path = workspace / "_state" / "google-integration.json"
payload = json.loads(integration_path.read_text(encoding="utf-8"))
profile = payload["profiles"]["pessoal"]
profile["status"] = "connected"
profile["account_email"] = "batata@example.com"
profile["last_authenticated_at"] = "2026-03-19T18:30:00-03:00"
profile["token_storage"]["service"] = service_prefix
payload["status"] = "connected"
payload["active_profile"] = "pessoal"
integration_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

bundle = {
    "oauth_client": {
        "client_id": "fake-client-id.apps.googleusercontent.com",
        "client_secret": "fake-client-secret",
        "auth_uri": f"http://127.0.0.1:{provider_port}/auth",
        "token_uri": f"http://127.0.0.1:{provider_port}/token",
    },
    "token_payload": {
        "refresh_token": "1//fake-refresh-token"
    },
}
command = [
    "security",
    "add-generic-password",
    "-a",
    profile["token_storage"]["account"],
    "-s",
    profile["token_storage"]["service"],
    "-w",
    json.dumps(bundle, ensure_ascii=True),
    "-U",
]
subprocess.run(command, check=True, capture_output=True, text=True)
PY

PRUMO_GOOGLE_CALENDAR_EVENTS_URL="http://127.0.0.1:${PROVIDER_PORT}/calendar/events" \
PRUMO_GOOGLE_GMAIL_MESSAGES_URL="http://127.0.0.1:${PROVIDER_PORT}/gmail/messages" \
PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime snapshot-refresh \
  --workspace "$WORKSPACE" >"$TMP_DIR/snapshot.out"

grep -Fq "status: ok" "$TMP_DIR/snapshot.out" || fail "snapshot-refresh nao trouxe status ok via Calendar API"
grep -Fq "conta=batata@example.com" "$TMP_DIR/snapshot.out" || fail "snapshot-refresh nao trouxe a conta conectada"
grep -Fq "agenda_hoje=2" "$TMP_DIR/snapshot.out" || fail "snapshot-refresh nao trouxe eventos de hoje"
grep -Fq "emails=2" "$TMP_DIR/snapshot.out" || fail "snapshot-refresh nao trouxe o total de emails via Gmail API"

PYTHONPATH="$ROOT_DIR/runtime" python3 -m prumo_runtime briefing \
  --workspace "$WORKSPACE" >"$TMP_DIR/briefing.out"

grep -Fq "Levar Nina à escola" "$TMP_DIR/briefing.out" || fail "briefing nao usou eventos vindos da Calendar API"
grep -Fq "agenda veio direto da Google Calendar API" "$TMP_DIR/briefing.out" || fail "briefing nao explicou a fonte da agenda"
grep -Eq "Email veio direto da Gmail API|email veio direto da Gmail API" "$TMP_DIR/briefing.out" || fail "briefing nao explicou a fonte do email"
grep -Fq "Ajuste urgente no site" "$TMP_DIR/briefing.out" || fail "briefing nao destacou email relevante vindo da Gmail API"

echo "ok: local runtime google calendar smoke"
