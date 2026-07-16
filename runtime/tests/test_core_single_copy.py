"""Critério 1 do épico #177: uma cópia completa do core por workspace (#179).

A auditoria de 15/07 achou o core byte-idêntico em DUAS casas na instância
(`.prumo/system/PRUMO-CORE.md` + `.prumo/skills/prumo/references/prumo-core.md`),
com drift latente: o update manual sem runtime só atualiza a primeira. Agora
`install_skills` substitui a cópia vendored por um stub-ponteiro — o core
canônico da instância é só o de `.prumo/system/`.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from prumo_runtime.command_table import parse_command_table
from prumo_runtime.skills_install import install_skills
from prumo_runtime.templates import CORE_STUB_MARKER, render_core_stub
from prumo_runtime.workspace import WorkspaceConfig, create_missing_files, repair_workspace

FULL_CORE_SIGNATURE = "# Prumo Core — Motor do sistema"

_BACKUP_HOMES = {"backup", "backups"}


def _under_backup(workspace: Path, path: Path) -> bool:
    rel = path.relative_to(workspace).parts
    return len(rel) >= 2 and rel[0] == ".prumo" and rel[1] in _BACKUP_HOMES


def _build_workspace(root: Path) -> Path:
    workspace = root / "ws"
    workspace.mkdir(parents=True)
    config = WorkspaceConfig(workspace=workspace, user_name="Teste", layout_mode="nested")
    install_skills(workspace, layout_mode="nested")
    create_missing_files(config)
    return workspace


class CoreSingleCopyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="prumo-core-stub-")
        cls.ws = _build_workspace(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_install_skills_writes_pointer_stub_for_vendored_core(self) -> None:
        vendored = self.ws / ".prumo" / "skills" / "prumo" / "references" / "prumo-core.md"
        text = vendored.read_text(encoding="utf-8")
        self.assertIn(CORE_STUB_MARKER, text)
        self.assertNotIn("prumo_version:", text)
        self.assertNotIn("## Comandos disponíveis", text)

    def test_workspace_has_exactly_one_active_full_core(self) -> None:
        """O contrato real é "uma cópia completa ATIVA": backups legítimos
        podem carregar cores completos, não contam e sobrevivem byte a byte
        ao `repair` (que converte o vendored ativo, nunca o histórico)."""
        backup_core = (
            self.ws / ".prumo" / "backups" / "pre-update" / "20990101T000000" / "PRUMO-CORE.md"
        )
        backup_core.parent.mkdir(parents=True, exist_ok=True)
        original_bytes = (self.ws / ".prumo" / "system" / "PRUMO-CORE.md").read_bytes()
        backup_core.write_bytes(original_bytes)
        try:
            repair_workspace(self.ws)
            full_copies = [
                path
                for path in self.ws.rglob("*.md")
                if not _under_backup(self.ws, path)
                and FULL_CORE_SIGNATURE in path.read_text(encoding="utf-8", errors="ignore")
                and "## Comandos disponíveis" in path.read_text(encoding="utf-8", errors="ignore")
            ]
            self.assertEqual(
                [p.relative_to(self.ws) for p in full_copies],
                [Path(".prumo/system/PRUMO-CORE.md")],
                "deveria existir exatamente UMA cópia completa ATIVA do core no workspace",
            )
            self.assertEqual(
                backup_core.read_bytes(),
                original_bytes,
                "core completo dentro de backup é legítimo e não pode ser tocado pelo repair",
            )
        finally:
            shutil.rmtree(self.ws / ".prumo" / "backups" / "pre-update")

    def test_stub_never_parses_as_command_source(self) -> None:
        self.assertEqual(parse_command_table(render_core_stub()), [])

    def test_vendored_modules_stay_complete(self) -> None:
        # Só o CORE vira ponteiro — os módulos vizinhos seguem completos
        # (a cadeia de fallback da #77 depende deles).
        briefing_module = (
            self.ws
            / ".prumo"
            / "skills"
            / "prumo"
            / "references"
            / "modules"
            / "briefing-procedure.md"
        )
        self.assertGreater(len(briefing_module.read_text(encoding="utf-8").split()), 500)
        skill_md = self.ws / ".prumo" / "skills" / "briefing" / "SKILL.md"
        self.assertIn("briefing", skill_md.read_text(encoding="utf-8"))


class RepairConvertsLegacyTest(unittest.TestCase):
    def test_repair_converts_legacy_full_vendored_core_to_stub(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prumo-legacy-core-") as tmp:
            ws = _build_workspace(Path(tmp))
            vendored = ws / ".prumo" / "skills" / "prumo" / "references" / "prumo-core.md"
            # Simula instância pré-stub: cópia completa (e defasada) no vendored.
            system_core = ws / ".prumo" / "system" / "PRUMO-CORE.md"
            vendored.write_text(
                system_core.read_text(encoding="utf-8").replace(
                    "prumo_version:", "prumo_version_antiga_qualquer:"
                )
                + "\n# Prumo Core — Motor do sistema\n## Comandos disponíveis\n",
                encoding="utf-8",
            )
            repair_workspace(ws)
            text = vendored.read_text(encoding="utf-8")
            self.assertIn(CORE_STUB_MARKER, text)
            self.assertNotIn("## Comandos disponíveis", text)


if __name__ == "__main__":
    unittest.main()
