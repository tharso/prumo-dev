"""Executor `prumo sanitize` (#179, épico #177, critério 5).

Fixture reproduz o lixo real da auditoria de 15/07: HANDOVERs legados
(pré-#68), HTMLs efêmeros do decidir, backups aninhados (`.prumo/` inteiro
dentro de `.prumo/backups/`), backups expirados, legado `.prumo/backup/`
singular, cache velho e fonte duplicada — mais iscas em `Prumo/` que NUNCA
podem ser tocadas. O apply consome o PLANO APROVADO do dry-run: item novo,
alterado ou sumido desde a aprovação fica `blocked`.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from prumo_runtime.sanitize import (
    SanitizeError,
    Thresholds,
    _append_archive_index,
    apply_plan,
    build_plan,
    iter_handover_files,
    iter_nested_backup_dirs,
)

TODAY = date(2026, 7, 16)


def _old(path: Path, days: int) -> None:
    stamp = time.mktime((TODAY - timedelta(days=days)).timetuple())
    os.utime(path, (stamp, stamp))


def _write(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def build_dirty_workspace(root: Path) -> Path:
    ws = root / "ws"
    dot = ws / ".prumo"

    # Iscas do usuário — intocáveis.
    _write(ws / "Prumo" / "PAUTA.md", "# Pauta\n")
    velho = _write(ws / "Prumo" / "Referencias" / "velho.md", "conteúdo antigo\n")
    _old(velho, 400)

    # Estado ativo do runtime — preservado.
    _write(dot / "state" / "workspace-schema.json", "{}")
    _write(dot / "state" / "agent-lock.json", "{}")

    # 1. HANDOVERs legados (#68): flat legado e dentro do archive.
    h1 = _write(ws / "_state" / "HANDOVER.md", "handover\n")
    h2 = _write(dot / "state" / "archive" / "backups" / "HANDOVER.md.20260215T101010", "snap\n")
    h3 = _write(dot / "state" / "HANDOVER.summary.md", "resumo\n")
    for h in (h1, h2, h3):
        _old(h, 120)

    # 2. Efêmeros do decidir/acervo: velhos saem, recentes ficam.
    old_html = _write(dot / "state" / "decidir" / "despacho-2026-03-01.html", "<html>Boliand.otf</html>")
    _old(old_html, 60)
    # O fresco NÃO referencia a fonte — deixa o asset_dedupe elegível.
    _write(dot / "state" / "decidir" / "despacho-hoje.html", "<html>novo</html>")
    old_acervo = _write(dot / "state" / "acervo" / "acervo-velho.html", "<html></html>")
    _old(old_acervo, 45)

    # 3. Backup aninhado: .prumo inteiro dentro de um stamp.
    nested = dot / "backups" / "setup" / "20260401T000000" / ".prumo" / "state"
    _write(nested / "junk.json", "{}")
    _write(dot / "backups" / "setup" / "20260401T000000" / "PAUTA.md", "backup legítimo\n")

    # 4. Backup expirado (scope/stamp velho) + um fresco.
    expired = dot / "backups" / "runtime-migrate" / "20260101T000000"
    _write(expired / "arquivo.md", "velho\n")
    _old(expired, 190)
    _write(dot / "backups" / "repair-version-bump" / "20260714T000000" / "core.md", "novo\n")

    # 5. Legado singular sobrevivente (não expirado).
    legacy = _write(dot / "backup" / "sobrevivente.md", "legado\n")
    _old(legacy, 30)

    # 6. Cache velho.
    cache = _write(dot / "cache" / "resposta.json", "{}")
    _old(cache, 90)

    # 7. Fonte duplicada: vendored + cópia em state (recente, hash igual,
    #    referenciada só pelo HTML velho que VAI sair) + cópia divergente.
    font_bytes = b"FONTEFAKE-BOLIAND"
    vendored = dot / "skills" / "decidir" / "assets" / "Boliand.otf"
    vendored.parent.mkdir(parents=True, exist_ok=True)
    vendored.write_bytes(font_bytes)
    state_font = dot / "state" / "decidir" / "Boliand.otf"
    state_font.write_bytes(font_bytes)
    other_font = dot / "state" / "decidir" / "Outra.otf"
    other_font.write_bytes(b"OUTRA")

    return ws


def _approved(ws: Path, **kwargs) -> dict:
    return build_plan(ws, today=TODAY, thresholds=Thresholds(), **kwargs)


class BuildPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="prumo-sanitize-")
        cls.ws = build_dirty_workspace(Path(cls._tmp.name))
        cls.plan = build_plan(cls.ws, today=TODAY, thresholds=Thresholds())
        cls.by_rule = {}
        for item in cls.plan["items"]:
            cls.by_rule.setdefault(item["rule"], []).append(item["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_dry_run_lists_handover_snapshots(self) -> None:
        paths = self.by_rule.get("handover_legacy", [])
        self.assertIn("_state/HANDOVER.md", paths)
        self.assertIn(".prumo/state/archive/backups/HANDOVER.md.20260215T101010", paths)
        self.assertIn(".prumo/state/HANDOVER.summary.md", paths)

    def test_dry_run_lists_old_ephemerals_and_keeps_recent(self) -> None:
        paths = self.by_rule.get("decidir_ephemeral", [])
        self.assertIn(".prumo/state/decidir/despacho-2026-03-01.html", paths)
        self.assertIn(".prumo/state/acervo/acervo-velho.html", paths)
        all_paths = [item["path"] for item in self.plan["items"]]
        self.assertNotIn(".prumo/state/decidir/despacho-hoje.html", all_paths)

    def test_dry_run_detects_nested_backup_subtrees(self) -> None:
        paths = self.by_rule.get("nested_backups", [])
        self.assertEqual(paths, [".prumo/backups/setup/20260401T000000/.prumo"])

    def test_dry_run_detects_expired_backup_scopes(self) -> None:
        self.assertEqual(
            self.by_rule.get("expired_backups", []),
            [".prumo/backups/runtime-migrate/20260101T000000"],
        )

    def test_dry_run_consolidates_legacy_survivors(self) -> None:
        self.assertEqual(
            self.by_rule.get("legacy_backup_consolidation", []),
            [".prumo/backup/sobrevivente.md"],
        )

    def test_dry_run_lists_old_cache(self) -> None:
        self.assertEqual(self.by_rule.get("workspace_cache", []), [".prumo/cache/resposta.json"])

    def test_asset_dedupe_only_when_hash_matches_and_unreferenced(self) -> None:
        paths = self.by_rule.get("asset_dedupe", [])
        # A Boliand de state/ só é referenciada pelo HTML velho (que sai no
        # mesmo plano) → deduplicável. A Outra.otf tem hash divergente → fica.
        self.assertIn(".prumo/state/decidir/Boliand.otf", paths)
        self.assertNotIn(".prumo/state/decidir/Outra.otf", paths)

    def test_asset_dedupe_keeps_font_referenced_by_surviving_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = build_dirty_workspace(Path(tmp))
            # HTML FRESCO passa a referenciar a fonte → ela sobrevive.
            fresh = ws / ".prumo" / "state" / "decidir" / "despacho-hoje.html"
            fresh.write_text("<html>usa Boliand.otf</html>", encoding="utf-8")
            plan = build_plan(ws, today=TODAY, thresholds=Thresholds())
            paths = [i["path"] for i in plan["items"] if i["rule"] == "asset_dedupe"]
            self.assertNotIn(
                ".prumo/state/decidir/Boliand.otf",
                paths,
                "fonte referenciada por HTML sobrevivente não pode ser removida",
            )

    def test_plan_never_touches_user_root_or_runtime_state(self) -> None:
        all_paths = [item["path"] for item in self.plan["items"]]
        for path in all_paths:
            self.assertFalse(path.startswith("Prumo/"), f"plano tocou dado do usuário: {path}")
        self.assertNotIn(".prumo/state/workspace-schema.json", all_paths)
        self.assertNotIn(".prumo/state/agent-lock.json", all_paths)

    def test_dry_run_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = build_dirty_workspace(Path(tmp))
            before = sorted(str(p.relative_to(ws)) for p in ws.rglob("*"))
            build_plan(ws, today=TODAY, thresholds=Thresholds())
            after = sorted(str(p.relative_to(ws)) for p in ws.rglob("*"))
            self.assertEqual(before, after)

    def test_report_schema_totals_and_fingerprint_fields(self) -> None:
        self.assertEqual(self.plan["schema_version"], "prumo_sanitize_report.v1")
        self.assertEqual(self.plan["mode"], "dry-run")
        self.assertEqual(self.plan["totals"]["count"], len(self.plan["items"]))
        self.assertIn("by_rule", self.plan["totals"])
        for item in self.plan["items"]:
            self.assertIn("mtime_ns", item, "fingerprint do apply depende do mtime_ns no item")
            self.assertIn("sha256", item, "todo item carrega identidade de conteúdo")

    def test_empty_rules_selection_is_an_error(self) -> None:
        with self.assertRaises(SanitizeError):
            build_plan(self.ws, today=TODAY, rules=[])
        with self.assertRaises(SanitizeError):
            build_plan(self.ws, today=TODAY, rules=["", ""])

    def test_unknown_rule_is_controlled_error(self) -> None:
        with self.assertRaises(SanitizeError):
            build_plan(self.ws, today=TODAY, rules=["regra_inventada"])

    def test_negative_threshold_is_controlled_error(self) -> None:
        with self.assertRaises(SanitizeError):
            build_plan(self.ws, today=TODAY, thresholds=Thresholds(cache_days=-1))

    def test_symlinked_ancestor_is_never_enumerated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = build_dirty_workspace(Path(tmp))
            outside = Path(tmp) / "fora"
            fugitive = _write(outside / "fugitivo-velho.html", "<html></html>")
            _old(fugitive, 400)
            acervo = ws / ".prumo" / "state" / "acervo"
            import shutil as _sh

            _sh.rmtree(acervo)
            acervo.symlink_to(outside)
            plan = build_plan(ws, today=TODAY, thresholds=Thresholds())
            paths = [i["path"] for i in plan["items"]]
            self.assertNotIn(".prumo/state/acervo/fugitivo-velho.html", paths)
            self.assertTrue(fugitive.exists(), "detecção leu através de symlink ancestral")

    def test_symlinked_dir_inside_scope_is_not_descended(self) -> None:
        # Symlink de diretório NO MEIO da árvore varrida: o walker não pode
        # nem descer nele pra descobrir filhos.
        with tempfile.TemporaryDirectory() as tmp:
            ws = build_dirty_workspace(Path(tmp))
            outside = Path(tmp) / "fora-interna"
            fugitive = _write(outside / "interno-velho.html", "<html></html>")
            _old(fugitive, 400)
            (ws / ".prumo" / "state" / "decidir" / "atalho").symlink_to(outside)
            plan = build_plan(ws, today=TODAY, thresholds=Thresholds())
            paths = [i["path"] for i in plan["items"]]
            self.assertNotIn(".prumo/state/decidir/atalho/interno-velho.html", paths)
            self.assertNotIn(".prumo/state/decidir/atalho", paths)
            self.assertTrue(fugitive.exists())


class ApplyPlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="prumo-sanitize-apply-")
        self.ws = build_dirty_workspace(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)

    def test_apply_moves_handover_to_single_backup_root(self) -> None:
        report = apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        backup_root = self.ws / report["apply"]["backup_root"]
        # Convenção achatada `__` (mesma do runtime-migrate): restaurável
        # pelo journal/índice e sem recriar árvore de backups no backup.
        self.assertTrue((backup_root / "_state__HANDOVER.md").exists())
        self.assertFalse((self.ws / "_state" / "HANDOVER.md").exists())

    def test_apply_backup_root_never_contains_backup_roots(self) -> None:
        report = apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        backup_root = self.ws / report["apply"]["backup_root"]
        offenders = [
            p for p in backup_root.rglob("*")
            if p.is_dir() and p.name in {".prumo", "backups", "backup"}
        ]
        self.assertEqual(offenders, [], f"backup do sanitize aninhou backups: {offenders}")

    def test_apply_writes_write_ahead_journal(self) -> None:
        report = apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        backup_root = self.ws / report["apply"]["backup_root"]
        journal = json.loads((backup_root / "SANITIZE-JOURNAL.json").read_text(encoding="utf-8"))
        self.assertEqual(journal["schema_version"], "prumo_sanitize_journal.v1")
        self.assertTrue(journal["planned"])
        self.assertIsNotNone(journal["results"])

    def test_apply_deletes_nested_and_expired_without_copying(self) -> None:
        apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        self.assertFalse(
            (self.ws / ".prumo/backups/setup/20260401T000000/.prumo").exists()
        )
        self.assertTrue(
            (self.ws / ".prumo/backups/setup/20260401T000000/PAUTA.md").exists(),
            "conteúdo legítimo do stamp não podia sumir",
        )
        self.assertFalse((self.ws / ".prumo/backups/runtime-migrate/20260101T000000").exists())

    def test_apply_consolidates_legacy_backup_dir(self) -> None:
        apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        legacy_root = self.ws / ".prumo" / "backups" / "legacy"
        moved = list(legacy_root.rglob("sobrevivente.md"))
        self.assertEqual(len(moved), 1)
        self.assertFalse((self.ws / ".prumo" / "backup" / "sobrevivente.md").exists())

    def test_apply_updates_archive_index_with_relative_paths(self) -> None:
        apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        index = json.loads(
            (self.ws / ".prumo/state/archive/ARCHIVE-INDEX.json").read_text(encoding="utf-8")
        )
        self.assertTrue(index["entries"])
        for entry in index["entries"]:
            self.assertFalse(entry["from"].startswith("/"), entry)
        md = (self.ws / ".prumo/state/archive/ARCHIVE-INDEX.md").read_text(encoding="utf-8")
        self.assertIn("sanitize:", md)

    def test_archive_index_rejects_absolute_paths(self) -> None:
        with self.assertRaises(ValueError):
            _append_archive_index(
                self.ws,
                [{"at": "2026-07-16T00:00:00", "op": "sanitize:x", "from": "/Users/x/abs.md", "to": None, "bytes": 1}],
            )

    def test_corrupted_archive_index_aborts_before_any_mutation(self) -> None:
        index = self.ws / ".prumo" / "state" / "archive" / "ARCHIVE-INDEX.json"
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text("{corrompido", encoding="utf-8")
        plan = _approved(self.ws)
        before = sorted(
            str(p.relative_to(self.ws))
            for p in self.ws.rglob("*")
            if ".prumo/backups/sanitize" not in str(p)
        )
        with self.assertRaises(SanitizeError):
            apply_plan(self.ws, plan=plan, today=TODAY)
        after = sorted(
            str(p.relative_to(self.ws))
            for p in self.ws.rglob("*")
            if ".prumo/backups/sanitize" not in str(p)
        )
        self.assertEqual(before, after, "índice corrompido tem que abortar SEM mutação")
        self.assertEqual(index.read_text(encoding="utf-8"), "{corrompido", "índice não pode ser sobrescrito")

    def test_apply_preserves_user_root_and_runtime_state(self) -> None:
        before_pauta = (self.ws / "Prumo" / "PAUTA.md").read_text(encoding="utf-8")
        apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        self.assertEqual((self.ws / "Prumo" / "PAUTA.md").read_text(encoding="utf-8"), before_pauta)
        self.assertTrue((self.ws / "Prumo" / "Referencias" / "velho.md").exists())
        self.assertTrue((self.ws / ".prumo/state/workspace-schema.json").exists())
        self.assertTrue((self.ws / ".prumo/state/agent-lock.json").exists())

    def test_rules_filter_applies_subset_only(self) -> None:
        apply_plan(self.ws, plan=_approved(self.ws), today=TODAY, rules=["handover_legacy"])
        self.assertFalse((self.ws / "_state" / "HANDOVER.md").exists())
        self.assertTrue(
            (self.ws / ".prumo/cache/resposta.json").exists(),
            "regra fora do filtro não podia executar",
        )

    def test_item_changed_since_plan_is_blocked(self) -> None:
        plan = _approved(self.ws)
        target = self.ws / "_state" / "HANDOVER.md"
        target.write_text("handover EDITADO depois da aprovação\n", encoding="utf-8")
        _old(target, 119)  # mtime/size mudam → fingerprint diverge
        report = apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertTrue(target.exists(), "item alterado desde o plano não podia executar")
        blocked = {b["path"]: b["reason"] for b in report["apply"]["blocked"]}
        self.assertIn("_state/HANDOVER.md", blocked)
        self.assertIn("mudou", blocked["_state/HANDOVER.md"])

    def test_rewrite_with_same_size_and_mtime_is_blocked_by_content_hash(self) -> None:
        # Bypass clássico de fingerprint fraco: reescrever com MESMO tamanho
        # e restaurar o mtime_ns exato. Só o hash de conteúdo pega.
        plan = _approved(self.ws)
        target = self.ws / "_state" / "HANDOVER.md"
        stat = target.lstat()
        original = target.read_bytes()
        target.write_bytes(b"handovEr\n"[: len(original)].ljust(len(original), b"!"))
        os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        report = apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertTrue(target.exists(), "conteúdo trocado com mesmo size/mtime tinha que bloquear")
        blocked = {b["path"]: b["reason"] for b in report["apply"]["blocked"]}
        self.assertIn("_state/HANDOVER.md", blocked)

    def test_directory_internal_change_is_blocked_by_manifest_hash(self) -> None:
        # Diretório aprovado pra delete cujo conteúdo INTERNO muda depois do
        # plano (mantendo mtime do dir) não pode mais executar.
        plan = _approved(self.ws)
        nested = self.ws / ".prumo/backups/setup/20260401T000000/.prumo"
        dir_stat = nested.lstat()
        inner = nested / "state" / "junk.json"
        inner_stat = inner.lstat()
        inner.write_text('{"mudou": true}', encoding="utf-8")
        os.utime(inner, ns=(inner_stat.st_atime_ns, inner_stat.st_mtime_ns))
        os.utime(nested, ns=(dir_stat.st_atime_ns, dir_stat.st_mtime_ns))
        report = apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertTrue(nested.exists(), "árvore alterada desde o plano não podia ser deletada")
        blocked = {b["path"]: b["reason"] for b in report["apply"]["blocked"]}
        self.assertIn(".prumo/backups/setup/20260401T000000/.prumo", blocked)

    def test_dir_with_internal_symlink_never_enters_plan(self) -> None:
        expired = self.ws / ".prumo" / "backups" / "com-link" / "20260101T000000"
        _write(expired / "arquivo.md", "velho\n")
        (expired / "atalho").symlink_to(self.ws / "Prumo")
        _old(expired, 190)
        plan = _approved(self.ws)
        self.assertNotIn(
            ".prumo/backups/com-link/20260101T000000",
            [i["path"] for i in plan["items"]],
            "dir com symlink descendente nunca pode ser candidato",
        )

    def test_symlink_appearing_inside_approved_dir_blocks_at_boundary(self) -> None:
        # O manifesto não denuncia (link não muda mtime restaurado): é a
        # revalidação na fronteira da mutação que tem que segurar.
        plan = _approved(self.ws)
        nested = self.ws / ".prumo/backups/setup/20260401T000000/.prumo"
        state_dir = nested / "state"
        dir_stat = state_dir.lstat()
        top_stat = nested.lstat()
        (state_dir / "atalho-tardio").symlink_to(self.ws / "Prumo" / "PAUTA.md")
        os.utime(state_dir, ns=(dir_stat.st_atime_ns, dir_stat.st_mtime_ns))
        os.utime(nested, ns=(top_stat.st_atime_ns, top_stat.st_mtime_ns))
        report = apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertTrue(nested.exists(), "árvore com symlink novo não podia ser deletada")
        self.assertTrue((self.ws / "Prumo" / "PAUTA.md").exists())
        blocked = {b["path"]: b["reason"] for b in report["apply"]["blocked"]}
        self.assertIn(".prumo/backups/setup/20260401T000000/.prumo", blocked)
        self.assertIn("symlink", blocked[".prumo/backups/setup/20260401T000000/.prumo"])

    def test_archive_index_md_symlinked_out_aborts(self) -> None:
        outside = Path(self._tmp.name) / "md-externo.md"
        outside.write_text("# fora\n", encoding="utf-8")
        archive = self.ws / ".prumo" / "state" / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        (archive / "ARCHIVE-INDEX.md").symlink_to(outside)
        plan = _approved(self.ws)
        with self.assertRaises(SanitizeError):
            apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertEqual(outside.read_text(encoding="utf-8"), "# fora\n")
        self.assertTrue((self.ws / "_state" / "HANDOVER.md").exists(), "nada podia executar")

    def test_preplanted_tmp_symlink_is_never_followed(self) -> None:
        outside = Path(self._tmp.name) / "alvo-do-tmp.json"
        archive = self.ws / ".prumo" / "state" / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        (archive / "ARCHIVE-INDEX.json.tmp").symlink_to(outside)
        apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        self.assertFalse(outside.exists(), "escrita atômica seguiu um .tmp plantado")
        index = json.loads((archive / "ARCHIVE-INDEX.json").read_text(encoding="utf-8"))
        self.assertTrue(index["entries"])

    def test_symlinked_backups_root_blocks_apply_without_external_writes(self) -> None:
        plan = _approved(self.ws)
        outside = Path(self._tmp.name) / "backups-reais"
        backups = self.ws / ".prumo" / "backups"
        import shutil as _sh

        _sh.move(str(backups), str(outside))
        backups.symlink_to(outside)
        external_before = sorted(str(p) for p in outside.rglob("*"))
        with self.assertRaises(SanitizeError):
            apply_plan(self.ws, plan=plan, today=TODAY)
        external_after = sorted(str(p) for p in outside.rglob("*"))
        self.assertEqual(external_before, external_after, "apply escreveu através do symlink")
        self.assertTrue((self.ws / "_state" / "HANDOVER.md").exists(), "nada podia executar")

    def test_archive_index_entries_must_be_a_list(self) -> None:
        index = self.ws / ".prumo" / "state" / "archive" / "ARCHIVE-INDEX.json"
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text('{"schema_version": "1.0", "entries": "corrompido"}', encoding="utf-8")
        plan = _approved(self.ws)
        with self.assertRaises(SanitizeError):
            apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertTrue((self.ws / "_state" / "HANDOVER.md").exists(), "abortou tarde demais")
        self.assertIn("corrompido", index.read_text(encoding="utf-8"))

    def test_plan_without_workspace_path_is_rejected(self) -> None:
        plan = _approved(self.ws)
        del plan["workspace_path"]
        with self.assertRaises(SanitizeError):
            apply_plan(self.ws, plan=plan, today=TODAY)

    def test_apply_report_is_not_a_valid_plan(self) -> None:
        plan = _approved(self.ws)
        plan["mode"] = "apply"
        with self.assertRaises(SanitizeError):
            apply_plan(self.ws, plan=plan, today=TODAY)

    def test_item_new_since_plan_is_blocked(self) -> None:
        plan = _approved(self.ws)
        novo = _write(self.ws / "_state" / "HANDOVER-novo.md", "surgiu depois\n")
        _old(novo, 120)
        report = apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertTrue(novo.exists(), "item fora do plano aprovado não podia executar")
        blocked = {b["path"]: b["reason"] for b in report["apply"]["blocked"]}
        self.assertIn("_state/HANDOVER-novo.md", blocked)
        self.assertIn("plano aprovado", blocked["_state/HANDOVER-novo.md"])
        self.assertFalse((self.ws / "_state" / "HANDOVER.md").exists(), "aprovado intacto executa")

    def test_item_gone_since_plan_is_blocked(self) -> None:
        plan = _approved(self.ws)
        (self.ws / "_state" / "HANDOVER.md").unlink()
        report = apply_plan(self.ws, plan=plan, today=TODAY)
        blocked = {b["path"]: b["reason"] for b in report["apply"]["blocked"]}
        self.assertIn("_state/HANDOVER.md", blocked)
        self.assertIn("sumiu", blocked["_state/HANDOVER.md"])

    def test_plan_for_other_workspace_is_rejected(self) -> None:
        plan = _approved(self.ws)
        plan["workspace_path"] = "/algum/outro/lugar"
        with self.assertRaises(SanitizeError):
            apply_plan(self.ws, plan=plan, today=TODAY)

    def test_flatten_collision_blocks_instead_of_overwriting(self) -> None:
        a = _write(self.ws / ".prumo" / "state" / "decidir" / "a" / "b.html", "<html>1</html>")
        b = _write(self.ws / ".prumo" / "state" / "decidir" / "a__b.html", "<html>2</html>")
        _old(a, 60)
        _old(b, 60)
        report = apply_plan(self.ws, plan=_approved(self.ws), today=TODAY)
        moved_targets = [m.split(" -> ")[1] for m in report["apply"]["moved"]]
        flat = [t for t in moved_targets if t.endswith("__state__decidir__a__b.html")]
        self.assertEqual(len(flat), 1, "os dois paths achatam igual — só um podia mover")
        blocked = {b_["path"]: b_["reason"] for b_ in report["apply"]["blocked"]}
        survivors = [p for p in (a, b) if p.exists()]
        self.assertEqual(len(survivors), 1, "o colidido tinha que ficar no lugar")
        rel_survivor = survivors[0].relative_to(self.ws).as_posix()
        self.assertIn(rel_survivor, blocked)
        self.assertIn("colisão", blocked[rel_survivor])

    def test_symlink_is_never_a_candidate(self) -> None:
        target = self.ws / "Prumo" / "PAUTA.md"
        link = self.ws / ".prumo" / "cache" / "escape.otf"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        stamp = time.mktime((TODAY - timedelta(days=200)).timetuple())
        os.utime(link, (stamp, stamp), follow_symlinks=False)
        plan = _approved(self.ws)
        self.assertNotIn(
            ".prumo/cache/escape.otf",
            [i["path"] for i in plan["items"]],
            "symlink nunca entra no plano",
        )
        apply_plan(self.ws, plan=plan, today=TODAY)
        self.assertTrue(target.exists(), "symlink escapando não pode alcançar dado do usuário")
        self.assertTrue(link.is_symlink(), "o link em si não estava aprovado — fica intacto")


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="prumo-sanitize-cli-")
        self.ws = build_dirty_workspace(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)

    def _run(self, *argv: str) -> tuple[int, str]:
        import io
        from contextlib import redirect_stdout

        from prumo_runtime.cli import main

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(list(argv))
        return code, buffer.getvalue()

    def _plan_file(self) -> Path:
        plan = build_plan(self.ws, thresholds=Thresholds())
        path = Path(self._tmp.name) / "plano.json"
        path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        return path

    def test_cli_sanitize_default_is_dry_run(self) -> None:
        code, out = self._run("sanitize", "--workspace", str(self.ws), "--format", "json")
        self.assertEqual(code, 0)
        report = json.loads(out[out.index("{") :])
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["schema_version"], "prumo_sanitize_report.v1")
        self.assertTrue((self.ws / "_state" / "HANDOVER.md").exists(), "dry-run mexeu em arquivo")

    def test_cli_text_dry_run_never_writes_version_cache(self) -> None:
        # `sanitize` está em SUPPRESS_COMMANDS: nem o banner de update pode
        # escrever `last_notified_at` num dry-run (zero mutação de verdade).
        with mock.patch(
            "prumo_runtime.version_check._write_cache",
            side_effect=AssertionError("dry-run escreveu cache de versão"),
        ):
            code, _ = self._run("sanitize", "--workspace", str(self.ws))
        self.assertEqual(code, 0)

    def test_cli_sanitize_apply_requires_yes(self) -> None:
        code, out = self._run("sanitize", "--workspace", str(self.ws), "--apply")
        self.assertEqual(code, 2)
        self.assertIn("--yes", out)
        self.assertTrue((self.ws / "_state" / "HANDOVER.md").exists())

    def test_cli_sanitize_apply_requires_plan(self) -> None:
        code, out = self._run("sanitize", "--workspace", str(self.ws), "--apply", "--yes")
        self.assertEqual(code, 2)
        self.assertIn("--plan", out)
        self.assertTrue((self.ws / "_state" / "HANDOVER.md").exists())

    def test_cli_sanitize_apply_with_plan_and_yes_executes(self) -> None:
        plan_path = self._plan_file()
        code, _ = self._run(
            "sanitize", "--workspace", str(self.ws), "--apply", "--yes",
            "--plan", str(plan_path), "--format", "json",
        )
        self.assertEqual(code, 0)
        self.assertFalse((self.ws / "_state" / "HANDOVER.md").exists())

    def test_cli_empty_rules_is_exit_2_not_everything(self) -> None:
        plan_path = self._plan_file()
        code, out = self._run(
            "sanitize", "--workspace", str(self.ws), "--apply", "--yes",
            "--plan", str(plan_path), "--rules", ",",
        )
        self.assertEqual(code, 2)
        self.assertIn("--rules", out)
        self.assertTrue(
            (self.ws / "_state" / "HANDOVER.md").exists(),
            "`--rules ,` não pode virar aprovação de tudo",
        )

    def test_cli_unknown_rule_is_exit_2_without_traceback(self) -> None:
        code, out = self._run(
            "sanitize", "--workspace", str(self.ws), "--rules", "regra_inventada"
        )
        self.assertEqual(code, 2)
        self.assertIn("regra desconhecida", out)

    def test_cli_unreadable_plan_is_exit_2(self) -> None:
        code, out = self._run(
            "sanitize", "--workspace", str(self.ws), "--apply", "--yes",
            "--plan", str(Path(self._tmp.name) / "nao-existe.json"),
        )
        self.assertEqual(code, 2)
        self.assertIn("ilegível", out)


if __name__ == "__main__":
    unittest.main()
