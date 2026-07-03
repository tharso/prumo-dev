"""Propagação de skills pro workspace (#146).

Caso real: skill nova (fim) lançada, usuário roda update, e o comando não
existe no workspace — e a skill deletada (start) fica pra sempre. Trava:
(1) install_skills PODA skills removidas da fonte (sem tocar Prumo/Custom/);
(2) repair_host_adapters PODA symlinks gerenciados de skills que sumiram
    (preservando dirs não-gerenciados);
(3) o fluxo repair completo converge o workspace pro conjunto atual.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from prumo_runtime.constants import repo_root_from
from prumo_runtime.host_adapters import create_host_adapters, repair_host_adapters
from prumo_runtime.workspace import ensure_directories, install_skills

REPO_SKILLS = sorted(
    d.name for d in (repo_root_from(Path(__file__)) / "skills").iterdir()
    if d.is_dir() and not d.name.startswith(".")
)


def _nested_ws(parent: Path) -> Path:
    ws = parent / "ws"
    (ws / "Prumo").mkdir(parents=True)
    (ws / ".prumo").mkdir(parents=True)
    return ws


class InstallSkillsPruneTests(unittest.TestCase):
    def test_prunes_skill_removed_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_ws(Path(tmp))
            zombie = ws / ".prumo" / "skills" / "zombie-skill"
            zombie.mkdir(parents=True)
            (zombie / "SKILL.md").write_text("# morta\n", encoding="utf-8")
            installed = install_skills(ws, layout_mode="nested")
            self.assertFalse(zombie.exists(), "skill removida da fonte tem que ser podada")
            self.assertEqual(sorted(installed), REPO_SKILLS)
            present = sorted(
                d.name for d in (ws / ".prumo" / "skills").iterdir()
                if d.is_dir() and not d.name.startswith(".")
            )
            self.assertEqual(present, REPO_SKILLS, "workspace converge pro conjunto da fonte")

    def test_never_touches_custom_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_ws(Path(tmp))
            custom = ws / "Prumo" / "Custom" / "skills" / "minha-skill"
            custom.mkdir(parents=True)
            (custom / "SKILL.md").write_text("# do usuário\n", encoding="utf-8")
            install_skills(ws, layout_mode="nested")
            self.assertTrue((custom / "SKILL.md").exists(), "Custom/ é do usuário — intocável")

    def test_prune_skips_dotfiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_ws(Path(tmp))
            hidden = ws / ".prumo" / "skills" / ".estado-interno"
            hidden.mkdir(parents=True)
            (hidden / "x.json").write_text("{}", encoding="utf-8")
            install_skills(ws, layout_mode="nested")
            self.assertTrue(hidden.exists(), "entradas ocultas não são skills — não podar")


class AdapterPruneTests(unittest.TestCase):
    def _ws_with_adapters(self, parent: Path, skills: list[str]) -> Path:
        ws = parent / "ws"
        skills_root = ws / ".prumo" / "skills"
        for name in skills:
            d = skills_root / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        create_host_adapters(ws)
        return ws

    def test_repair_prunes_managed_adapter_of_removed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws_with_adapters(Path(tmp), ["fim", "morta"])
            import shutil
            shutil.rmtree(ws / ".prumo" / "skills" / "morta")
            result = repair_host_adapters(ws)
            for conv in (".claude/skills", ".agent/skills"):
                stale = ws / conv / "morta"
                self.assertFalse(
                    stale.exists() or stale.is_symlink(),
                    f"{conv}/morta órfão tinha que ser podado",
                )
                self.assertTrue((ws / conv / "fim").exists(), "skill viva preservada")
            manifest = json.loads((ws / ".prumo" / "state" / "host-skills.json").read_text(encoding="utf-8"))
            skills_in_manifest = {e["skill"] for e in manifest.get("adapters", [])}
            self.assertNotIn("morta", skills_in_manifest, "manifest não pode listar adapter podado")
            self.assertGreaterEqual(result.get("pruned", 0), 2)

    def test_repair_preserves_unmanaged_dir_named_like_removed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws_with_adapters(Path(tmp), ["fim"])
            # dir REAL do usuário (não symlink, não no manifest) com nome de skill morta
            user_dir = ws / ".claude" / "skills" / "morta"
            user_dir.mkdir(parents=True)
            (user_dir / "SKILL.md").write_text("# do usuário\n", encoding="utf-8")
            repair_host_adapters(ws)
            self.assertTrue((user_dir / "SKILL.md").exists(), "dir não-gerenciado é do usuário — intocável")

    def test_full_repair_flow_converges_adapters(self) -> None:
        # O caso do Tharso: skill deletada da fonte segue como symlink no host.
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_ws(Path(tmp))
            install_skills(ws, layout_mode="nested")
            create_host_adapters(ws)
            # simula era antiga: skill fantasma + adapter dela
            ghost = ws / ".prumo" / "skills" / "start-fantasma"
            ghost.mkdir(parents=True)
            (ghost / "SKILL.md").write_text("# era antiga\n", encoding="utf-8")
            repair_host_adapters(ws)  # cria o adapter do fantasma (gerenciado)
            self.assertTrue((ws / ".claude" / "skills" / "start-fantasma").is_symlink())
            # sync: install poda a fonte; repair poda o adapter
            install_skills(ws, layout_mode="nested")
            repair_host_adapters(ws)
            stale = ws / ".claude" / "skills" / "start-fantasma"
            self.assertFalse(stale.exists() or stale.is_symlink())
            for essential in ("fim", "acervo", "menu"):
                self.assertTrue(
                    (ws / ".claude" / "skills" / essential / "SKILL.md").exists(),
                    f"{essential} tem que estar descobrível no host",
                )


class UpdateChainsRepairTests(unittest.TestCase):
    """#146: `prumo update` propaga pro workspace rodando o repair do binário novo."""

    def test_runs_repair_via_post_update_binary(self) -> None:
        from unittest import mock

        from prumo_runtime.commands.update import _run_post_update_repair

        calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return mock.Mock(returncode=0)

        with mock.patch("prumo_runtime.commands.update.shutil.which", return_value="/fake/bin/prumo"), \
             mock.patch("prumo_runtime.commands.update.subprocess.run", side_effect=fake_run):
            result = _run_post_update_repair(Path("/tmp/ws"))

        self.assertTrue(result["repair_executed"])
        self.assertEqual(calls[0][:3], ["/fake/bin/prumo", "repair", "--workspace"])
        self.assertEqual(calls[0][3], "/tmp/ws")

    def test_missing_binary_degrades_to_suggestion(self) -> None:
        from unittest import mock

        from prumo_runtime.commands.update import _run_post_update_repair

        with mock.patch("prumo_runtime.commands.update.shutil.which", return_value=None):
            result = _run_post_update_repair(Path("/tmp/ws"))
        self.assertFalse(result["repair_executed"])
        self.assertIn("repair", result["repair_note"])

    def test_repair_failure_is_reported_not_raised(self) -> None:
        from unittest import mock

        from prumo_runtime.commands.update import _run_post_update_repair

        with mock.patch("prumo_runtime.commands.update.shutil.which", return_value="/fake/bin/prumo"), \
             mock.patch(
                 "prumo_runtime.commands.update.subprocess.run",
                 side_effect=OSError("permission denied"),
             ):
            result = _run_post_update_repair(Path("/tmp/ws"))
        self.assertFalse(result["repair_executed"])
        self.assertIn("falhou", result["repair_note"])


@unittest.skipUnless(__import__("os").name == "posix", "doctor é script bash (macOS/Linux)")
class DoctorStoreDiscoveryTests(unittest.TestCase):
    """#146: o doctor tem que achar o store GLOBAL (~/.claude/*) e flagrar
    plugin de era pré-skills-first — o caso real era um 4.1.0 de março
    invisível pro doctor ('nada urgente')."""

    SCRIPT = repo_root_from(Path(__file__)) / "scripts" / "prumo_cowork_doctor.sh"

    def _fake_store(self, root: Path, *, installed_version: str | None) -> Path:
        store = root / "fake_store"
        store.mkdir(parents=True)
        plugins: dict = {}
        if installed_version:
            plugins["prumo@prumo-marketplace"] = [{
                "scope": "user",
                "installPath": str(store / "cache" / "prumo-marketplace" / "prumo" / installed_version),
                "version": installed_version,
                "installedAt": "2026-03-03T16:14:07.009Z",
                "lastUpdated": "2026-03-03T16:14:07.009Z",
            }]
        (store / "installed_plugins.json").write_text(
            json.dumps({"version": 2, "plugins": plugins}), encoding="utf-8"
        )
        return store

    def _run_doctor(self, sessions_root: Path, extra: Path) -> dict:
        import subprocess

        completed = subprocess.run(
            ["bash", str(self.SCRIPT), "--sessions-root", str(sessions_root),
             "--extra-roots", str(extra), "--json"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_finds_global_store_and_flags_ancient_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sessions = base / "sessions-vazio"
            sessions.mkdir()
            store = self._fake_store(base, installed_version="4.1.0")
            result = self._run_doctor(sessions, store)
            self.assertGreaterEqual(result["roots_found"], 1)
            target = next(r for r in result["roots"] if r["root"] == str(store))
            self.assertTrue(target["plugin_installed"])
            self.assertEqual(target["plugin_version"], "4.1.0")
            diagnosis = " ".join(target["diagnosis"])
            self.assertIn("pré-skills-first", diagnosis)
            actions = " ".join(target["recommended_actions"])
            self.assertIn("reinstale", actions)

    def test_target_prefers_store_with_installed_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # store de sessão SEM instalação (mais recente) + global COM 4.1.0
            sessions = base / "sessions"
            empty_store = sessions / "abc" / "cowork_plugins"
            empty_store.mkdir(parents=True)
            (empty_store / "installed_plugins.json").write_text(
                json.dumps({"version": 2, "plugins": {}}), encoding="utf-8"
            )
            global_store = self._fake_store(base, installed_version="4.1.0")
            result = self._run_doctor(sessions, global_store)
            self.assertEqual(result["roots_found"], 2)
            self.assertEqual(
                result["target_root"], str(global_store),
                "o alvo tem que ser o store onde o plugin está INSTALADO",
            )

    def test_marketplace_path_that_is_a_file_does_not_crash(self) -> None:
        # Regressão vista na máquina real: marketplaces/<nome> era um ARQUIVO;
        # o doctor estourava NotADirectoryError no run_git.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sessions = base / "s"
            sessions.mkdir()
            store = self._fake_store(base, installed_version="4.1.0")
            marketplaces = store / "marketplaces"
            marketplaces.mkdir()
            (marketplaces / "prumo-marketplace").write_text("não sou um diretório", encoding="utf-8")
            result = self._run_doctor(sessions, store)  # não pode crashar
            target = next(r for r in result["roots"] if r["root"] == str(store))
            self.assertTrue(target["plugin_installed"])

    def test_modern_plugin_not_flagged_as_ancient(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sessions = base / "s"
            sessions.mkdir()
            store = self._fake_store(base, installed_version="5.21.0")
            result = self._run_doctor(sessions, store)
            target = next(r for r in result["roots"] if r["root"] == str(store))
            self.assertNotIn("pré-skills-first", " ".join(target["diagnosis"]))


if __name__ == "__main__":
    unittest.main()
