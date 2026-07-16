"""Backups nunca aninham backups (#178, épico #177).

Cobre o fix de raiz do aninhamento visto na auditoria de 2026-07-15:
`copy_to_backup` fazia `copytree` sem `ignore`, então qualquer árvore que
carregasse `.prumo/` ou `archive/backups/` reproduzia backup dentro de
backup. Também cobre a poda (`prune_expired_backups`), que até então não
existia em código — backups acumulavam sem limite.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from prumo_runtime.backup import (
    backup_ignore,
    copy_to_backup,
    move_with_backup,
    prune_expired_backups,
)


class CopyToBackupIgnoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_copy_to_backup_skips_dot_prumo_inside_source(self) -> None:
        source = self.tmp / "source"
        (source / ".prumo" / "state").mkdir(parents=True)
        (source / ".prumo" / "state" / "x.json").write_text("{}", encoding="utf-8")
        (source / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")

        target = self.tmp / "backups" / "scope" / "stamp" / "source"
        copy_to_backup(source, target)

        self.assertTrue((target / "PAUTA.md").exists())
        self.assertFalse(
            (target / ".prumo").exists(),
            "backup copiou `.prumo/` inteiro — é exatamente o aninhamento da auditoria",
        )

    def test_copy_to_backup_skips_nested_backup_dirs(self) -> None:
        source = self.tmp / "_state"
        (source / "archive" / "backups").mkdir(parents=True)
        (source / "archive" / "backups" / "HANDOVER.md.20260201T000000").write_text(
            "snapshot legado\n", encoding="utf-8"
        )
        (source / "archive" / "ARCHIVE-INDEX.json").write_text("{}", encoding="utf-8")
        (source / "last-briefing.json").write_text("{}", encoding="utf-8")

        target = self.tmp / "backup-copy"
        copy_to_backup(source, target)

        self.assertTrue((target / "archive" / "ARCHIVE-INDEX.json").exists())
        self.assertTrue((target / "last-briefing.json").exists())
        self.assertFalse(
            (target / "archive" / "backups").exists(),
            "backup de `_state/` copiou `archive/backups/` — backup dentro de backup",
        )

    def test_copy_to_backup_still_copies_plain_files(self) -> None:
        source = self.tmp / "AGENT.md"
        source.write_text("# AGENT\n", encoding="utf-8")
        target = self.tmp / "backups" / "scope" / "stamp" / "AGENT.md"
        copy_to_backup(source, target)
        self.assertEqual(target.read_text(encoding="utf-8"), "# AGENT\n")

    def test_backup_ignore_only_targets_backup_parents(self) -> None:
        # `backups` sob um diretório qualquer do usuário NÃO é ignorado —
        # o filtro é cirúrgico: só `.prumo`, `system` e `archive` como pai.
        kept = backup_ignore(str(self.tmp / "Referencias"), ["backups", "foto.png"])
        self.assertEqual(kept, set())
        dropped = backup_ignore(str(self.tmp / "archive"), ["backups", "ARCHIVE-INDEX.json"])
        self.assertEqual(dropped, {"backups"})
        always = backup_ignore(str(self.tmp / "qualquer"), [".prumo", "PAUTA.md"])
        self.assertEqual(always, {".prumo"})


class MoveWithBackupTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name) / "ws"
        self.ws.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def test_move_with_backup_state_root_does_not_nest_archive_backups(self) -> None:
        source = self.ws / "_state"
        (source / "archive" / "backups").mkdir(parents=True)
        (source / "archive" / "backups" / "HANDOVER.md.20260201T000000").write_text(
            "snapshot\n", encoding="utf-8"
        )
        (source / "archive" / "ARCHIVE-INDEX.json").write_text("{}", encoding="utf-8")
        destination = self.ws / ".prumo" / "state"
        backed_up: list[str] = []
        moved: list[str] = []

        move_with_backup(
            source,
            destination,
            workspace=self.ws,
            stamp="20260716T000000",
            backed_up=backed_up,
            moved=moved,
        )

        # O MOVE preserva tudo no destino — nada se perde.
        self.assertTrue(
            (destination / "archive" / "backups" / "HANDOVER.md.20260201T000000").exists()
        )
        # A cópia de segurança existe, mas sem a subárvore de backups.
        backup_copy = (
            self.ws / ".prumo" / "backups" / "runtime-migrate" / "20260716T000000" / "_state"
        )
        self.assertTrue((backup_copy / "archive" / "ARCHIVE-INDEX.json").exists())
        self.assertFalse((backup_copy / "archive" / "backups").exists())
        self.assertEqual(backed_up, ["_state"])
        self.assertEqual(moved, ["_state -> .prumo/state"])


class MigrateSkillsBackupTest(unittest.TestCase):
    def test_migrate_skills_backup_uses_ignore(self) -> None:
        from prumo_runtime.commands.migrate_skills import _execute_migration

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            (ws / "Prumo").mkdir(parents=True)
            (ws / ".prumo" / "system").mkdir(parents=True)
            source = ws / "Prumo" / "skills_OLD"
            (source / "briefing").mkdir(parents=True)
            (source / "briefing" / "SKILL.md").write_text("# skill\n", encoding="utf-8")
            (source / ".prumo" / "state").mkdir(parents=True)
            (source / ".prumo" / "state" / "junk.json").write_text("{}", encoding="utf-8")

            with patch(
                "prumo_runtime.commands.migrate_skills.repair_workspace",
                return_value={"recreated": []},
            ):
                result = _execute_migration(ws, source)

            backup_copy = Path(result["backup_dir"]) / "skills_OLD"
            self.assertTrue((backup_copy / "briefing" / "SKILL.md").exists())
            self.assertFalse(
                (backup_copy / ".prumo").exists(),
                "backup do relocate-skills copiou `.prumo/` de dentro do source",
            )


class PruneExpiredBackupsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name) / "ws"
        (self.ws / ".prumo" / "backups").mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)
        self.today = date(2026, 7, 16)

    def _make_old(self, path: Path, *, days: int) -> None:
        stamp = time.mktime((self.today - timedelta(days=days)).timetuple())
        os.utime(path, (stamp, stamp))

    def test_prune_expired_backups_removes_only_older_than_expiry(self) -> None:
        old_stamp = self.ws / ".prumo" / "backups" / "setup" / "20260101T000000"
        old_stamp.mkdir(parents=True)
        (old_stamp / "PAUTA.md").write_text("velho\n", encoding="utf-8")
        self._make_old(old_stamp, days=196)

        fresh_stamp = self.ws / ".prumo" / "backups" / "repair-version-bump" / "20260710T000000"
        fresh_stamp.mkdir(parents=True)
        (fresh_stamp / "core.md").write_text("novo\n", encoding="utf-8")

        legacy = self.ws / ".prumo" / "backup"
        legacy.mkdir()
        legacy_file = legacy / "antigo.md"
        legacy_file.write_text("legado\n", encoding="utf-8")
        self._make_old(legacy_file, days=200)

        removed = prune_expired_backups(self.ws, today=self.today, expiry_days=90)

        self.assertEqual(
            removed,
            [".prumo/backup/antigo.md", ".prumo/backups/setup/20260101T000000"],
        )
        self.assertFalse(old_stamp.exists())
        self.assertTrue(fresh_stamp.exists())
        # Escopo canônico esvaziado sai junto; o root permanece.
        self.assertFalse((self.ws / ".prumo" / "backups" / "setup").exists())
        self.assertTrue((self.ws / ".prumo" / "backups").exists())

    def test_prune_never_touches_paths_outside_backup_roots(self) -> None:
        keeper_state = self.ws / ".prumo" / "state"
        keeper_state.mkdir(parents=True)
        (keeper_state / "keep.json").write_text("{}", encoding="utf-8")
        self._make_old(keeper_state / "keep.json", days=400)
        (self.ws / "Prumo").mkdir()
        pauta = self.ws / "Prumo" / "PAUTA.md"
        pauta.write_text("# Pauta\n", encoding="utf-8")
        self._make_old(pauta, days=400)

        removed = prune_expired_backups(self.ws, today=self.today, expiry_days=90)

        self.assertEqual(removed, [])
        self.assertTrue((keeper_state / "keep.json").exists())
        self.assertTrue(pauta.exists())

    def test_prune_unlinks_escaping_symlink_without_touching_target(self) -> None:
        target_dir = self.ws / "Prumo"
        target_dir.mkdir()
        (target_dir / "PAUTA.md").write_text("# Pauta\n", encoding="utf-8")
        scope = self.ws / ".prumo" / "backups" / "setup"
        scope.mkdir(parents=True)
        link = scope / "20250101T000000"
        link.symlink_to(target_dir)
        # Envelhece o LINK (não o alvo): a poda mede idade por lstat.
        stamp = time.mktime((self.today - timedelta(days=200)).timetuple())
        os.utime(link, (stamp, stamp), follow_symlinks=False)

        removed = prune_expired_backups(self.ws, today=self.today, expiry_days=90)

        self.assertEqual(removed, [".prumo/backups/setup/20250101T000000"])
        self.assertFalse(link.exists())
        self.assertTrue((target_dir / "PAUTA.md").exists(), "poda seguiu o symlink e apagou dado do usuário")


if __name__ == "__main__":
    unittest.main()
