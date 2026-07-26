"""#179 PR9: doctor com drift plugin↔workspace, caches enumerados e --offline.

O doctor é o diagnóstico do cenário SEM runtime — por isso continua script
bash com python3 embutido, e o guard garante que nunca importa prumo_runtime.
Os testes rodam o script real via subprocess, sempre com --offline (herméticos,
zero rede).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from prumo_runtime.constants import repo_root_from

SCRIPT = repo_root_from(Path(__file__)) / "scripts" / "prumo_cowork_doctor.sh"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@unittest.skipUnless(__import__("os").name == "posix", "doctor é script bash (macOS/Linux)")
class DoctorDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.sessions = self.base / "sessions-vazio"
        self.sessions.mkdir()
        self.store = self.base / "store"
        self.checkout = self.base / "checkout"

    def _build_store(
        self,
        *,
        installed_version: str = "5.40.0",
        checkout_version: str = "5.54.0",
        extra_cache_versions: tuple[str, ...] = (),
        installed_skill_content: str | None = None,
        checkout_skill_content: str = "# skill do checkout\n",
    ) -> Path:
        install_path = self.store / "cache" / "prumo-marketplace" / "prumo" / installed_version
        skill_file = install_path / "skills" / "prumo" / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(installed_skill_content or checkout_skill_content, encoding="utf-8")

        for version in extra_cache_versions:
            payload = self.store / "cache" / "prumo-marketplace" / "prumo" / version / "payload.bin"
            payload.parent.mkdir(parents=True, exist_ok=True)
            payload.write_bytes(b"x" * 2048)

        _write_json(
            self.store / "installed_plugins.json",
            {
                "version": 2,
                "plugins": {
                    "prumo@prumo-marketplace": [
                        {
                            "scope": "user",
                            "installPath": str(install_path),
                            "version": installed_version,
                            "installedAt": "2026-07-01T10:00:00.000Z",
                            "lastUpdated": "2026-07-01T10:00:00.000Z",
                        }
                    ]
                },
            },
        )
        _write_json(
            self.store / "known_marketplaces.json",
            {
                "prumo-marketplace": {
                    "installLocation": str(self.checkout),
                    "source": {"source": "github", "repo": "tharso/prumo"},
                    "lastUpdated": "2026-07-01T10:00:00.000Z",
                }
            },
        )

        (self.checkout / "skills" / "prumo").mkdir(parents=True, exist_ok=True)
        (self.checkout / "VERSION").write_text(checkout_version + "\n", encoding="utf-8")
        (self.checkout / "skills" / "prumo" / "SKILL.md").write_text(checkout_skill_content, encoding="utf-8")
        _write_json(
            self.checkout / "marketplace.json",
            {"plugins": [{"name": "prumo", "version": checkout_version}]},
        )
        return install_path

    def _build_workspace(self, core_version: str) -> Path:
        workspace = self.base / "workspace"
        core = workspace / ".prumo" / "system" / "PRUMO-CORE.md"
        core.parent.mkdir(parents=True, exist_ok=True)
        core.write_text(
            f"# PRUMO-CORE\n\nprumo_version: {core_version}\n\nASSERT: exemplo\n",
            encoding="utf-8",
        )
        return workspace

    def _run_doctor(self, *args: str) -> dict:
        completed = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--sessions-root",
                str(self.sessions),
                "--extra-root",
                str(self.store),
                "--offline",
                "--json",
                *args,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_plugin_workspace_drift_true_when_versions_differ(self) -> None:
        self._build_store(installed_version="5.40.0")
        workspace = self._build_workspace("5.53.0")
        result = self._run_doctor("--workspace", str(workspace))
        self.assertEqual(result["workspace_core_version"], "5.53.0")
        self.assertIs(result["plugin_workspace_drift"], True)
        self.assertIn("5.40.0", result["workspace_note"])
        self.assertIn("5.53.0", result["workspace_note"])
        self.assertTrue(result["workspace_action"])

    def test_plugin_workspace_drift_false_when_aligned(self) -> None:
        self._build_store(installed_version="5.53.0")
        workspace = self._build_workspace("5.53.0")
        result = self._run_doctor("--workspace", str(workspace))
        self.assertIs(result["plugin_workspace_drift"], False)
        self.assertIsNone(result["workspace_action"])

    def test_workspace_without_core_is_visible_not_silent(self) -> None:
        workspace = self.base / "workspace-vazio"
        workspace.mkdir()
        self._build_store()
        result = self._run_doctor("--workspace", str(workspace))
        self.assertIsNone(result["plugin_workspace_drift"])
        self.assertIn("não foi lido", result["workspace_note"])

    def test_stale_caches_enumerated_with_bytes_and_remove_command(self) -> None:
        install_path = self._build_store(
            installed_version="5.40.0", extra_cache_versions=("5.30.0",)
        )
        result = self._run_doctor()
        stale = result["stale_caches"]
        self.assertEqual(len(stale), 1)
        entry = stale[0]
        self.assertEqual(entry["version"], "5.30.0")
        self.assertEqual(entry["bytes"], 2048)
        self.assertEqual(entry["status"], "stale")
        self.assertIn("rm -rf ", entry["remove_command"])
        self.assertIn("5.30.0", entry["remove_command"])

        in_use = [c for c in result["caches"] if c["version"] == "5.40.0"]
        self.assertEqual(len(in_use), 1)
        self.assertEqual(in_use[0]["status"], "em_uso")
        self.assertIsNone(in_use[0]["remove_command"])
        self.assertEqual(Path(in_use[0]["path"]), install_path)

    def test_skills_content_drift_flagged_when_same_version_differs(self) -> None:
        self._build_store(
            installed_version="5.54.0",
            checkout_version="5.54.0",
            installed_skill_content="# conteúdo editado à mão\n",
        )
        result = self._run_doctor()
        target = next(r for r in result["roots"] if r["root"] == str(self.store))
        self.assertIs(target["skills_content_drift"], True)
        diagnosis = " ".join(target["diagnosis"])
        self.assertIn("DIFEREM", diagnosis)

    def test_skills_content_drift_false_when_content_matches(self) -> None:
        self._build_store(installed_version="5.54.0", checkout_version="5.54.0")
        result = self._run_doctor()
        target = next(r for r in result["roots"] if r["root"] == str(self.store))
        self.assertIs(target["skills_content_drift"], False)
        self.assertEqual(target["checkout_skills_hash"], target["installed_skills_hash"])

    def test_offline_skips_network_probe(self) -> None:
        # source github + --offline: nenhum ls-remote → remote_head fica None
        # e o doctor não trava esperando rede.
        self._build_store()
        result = self._run_doctor()
        self.assertTrue(result["offline"])
        target = next(r for r in result["roots"] if r["root"] == str(self.store))
        self.assertIsNone(target["marketplace_remote_head"])
        self.assertIsNone(target["marketplace_checkout_stale"])


class DoctorScriptContractTests(unittest.TestCase):
    def test_doctor_script_never_imports_prumo_runtime(self) -> None:
        # O doctor diagnostica exatamente o cenário onde o runtime NÃO está
        # instalado — importar prumo_runtime mataria o caso de uso central.
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("import prumo_runtime", text)
        self.assertNotIn("from prumo_runtime", text)


if __name__ == "__main__":
    unittest.main()
