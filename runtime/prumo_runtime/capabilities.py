from __future__ import annotations

from pathlib import Path

from prumo_runtime.platform_support import runtime_platform_summary
from prumo_runtime.workspace_paths import workspace_paths


def workflow_registry_path(workspace: Path) -> Path:
    return workspace_paths(workspace).workflows_index


def workflow_scaffolding_summary(workspace: Path) -> dict[str, str]:
    return {
        "status": "ready",
        "delivery": "structure-only",
        "registry_path": str(workflow_registry_path(workspace).resolve()),
    }


def runtime_capabilities(workspace: Path, google_summary: dict) -> dict:
    return {
        "platform": runtime_platform_summary(),
        "providers": {
            "google": {
                "supported": True,
                "status": str(google_summary.get("active_profile_status") or google_summary.get("status") or "disconnected"),
                "strategy": str(google_summary.get("strategy") or "direct-google-api"),
                "token_storage_supported": bool(google_summary.get("token_storage_supported", False)),
                "token_storage_secure": bool(google_summary.get("token_storage_secure", False)),
                "token_storage_backend": str(google_summary.get("token_storage_backend") or "unknown"),
            },
        },
        "daily_operation": {
            "briefing": True,
            "continuation": True,
            "documentation": True,
            "workflow_scaffolding": True,
        },
        "workflow_scaffolding": workflow_scaffolding_summary(workspace),
    }
