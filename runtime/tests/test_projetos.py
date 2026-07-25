"""#201: índice de projetos com pulso determinístico puxado.

Design fechado com o Codex (2 rodadas, registradas na issue): gramática com
contêiner explícito, escrita transacional com zero-escrita em erro, caminhos
registrados delimitados (materialização do escopo autorizado da #194),
staleness que nunca declara `fresh` sob dúvida, e conteúdo vindo dos
projetos tratado como dado (regra 18) — sanitizado, jamais capaz de fechar
ou abrir blocos gerenciados.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from prumo_runtime import projetos
from prumo_runtime.projetos import (
    PULSO_BEGIN,
    PULSO_END,
    collect_folder_pulse,
    collect_git_pulse,
    compute_staleness,
    parse_projects_index,
    read_narrative,
    render_pulse_lines,
    resolve_registered_path,
    sanitize_text,
    sync_index_text,
)

NOW = datetime(2026, 7, 24, 20, 0, 0, tzinfo=timezone.utc)


def _make_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "T"], check=True)
    (repo / "a.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    return repo


def _index(body: str) -> str:
    return "# Projetos\n\n> cabeçalho autoral\n\n" + body


class ParseGrammarTests(unittest.TestCase):
    def test_sections_only_inside_container(self) -> None:
        text = _index(
            "## Estado atual\n\nnotas autorais soltas\n\n"
            "## Projetos registrados\n\n"
            "### Intercept\n- Caminho: ~/Code/intercept\n\n"
            f"{PULSO_BEGIN}\nvelho\n{PULSO_END}\n\n"
            "### Site\n- Caminho: /Volumes/SSD/site\n\n"
            "## Outra seção autoral\n\n### Isto não é projeto\n"
        )
        result = parse_projects_index(text)
        self.assertEqual(result.errors, [])
        self.assertEqual([e.name for e in result.entries], ["Intercept", "Site"])

    def test_no_container_means_no_entries_no_error(self) -> None:
        result = parse_projects_index(_index("## Estado atual\n\n_Nada._\n"))
        self.assertEqual(result.entries, [])
        self.assertEqual(result.errors, [])

    def test_duplicate_path_line_is_structural_error(self) -> None:
        text = _index(
            "## Projetos registrados\n\n### X\n- Caminho: /a\n- Caminho: /b\n"
        )
        result = parse_projects_index(text)
        self.assertTrue(any("Caminho" in e for e in result.errors))

    def test_duplicate_names_and_paths_are_errors(self) -> None:
        dup_name = _index(
            "## Projetos registrados\n\n### X\n- Caminho: /a\n\n### X\n- Caminho: /b\n"
        )
        self.assertTrue(parse_projects_index(dup_name).errors)
        dup_path = _index(
            "## Projetos registrados\n\n### A\n- Caminho: /igual\n\n### B\n- Caminho: /igual\n"
        )
        self.assertTrue(parse_projects_index(dup_path).errors)

    def test_orphan_inverted_or_duplicated_markers_are_errors(self) -> None:
        cases = [
            f"## Projetos registrados\n\n### X\n- Caminho: /a\n{PULSO_BEGIN}\nsem fim\n",
            f"## Projetos registrados\n\n### X\n- Caminho: /a\n{PULSO_END}\n{PULSO_BEGIN}\n",
            (
                "## Projetos registrados\n\n### X\n- Caminho: /a\n"
                f"{PULSO_BEGIN}\n{PULSO_END}\n{PULSO_BEGIN}\n{PULSO_END}\n"
            ),
        ]
        for body in cases:
            with self.subTest(body=body[:60]):
                self.assertTrue(parse_projects_index(_index(body)).errors)

    def test_section_without_path_is_noted_not_error(self) -> None:
        result = parse_projects_index(
            _index("## Projetos registrados\n\n### SóNota\ntexto autoral\n")
        )
        self.assertEqual(result.errors, [])
        self.assertEqual(result.entries[0].path_raw, None)


class ResolvePathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path("/Users/batata")
        self.ws = Path("/Users/batata/Documents/Vida")

    def _resolve(self, raw: str):
        return resolve_registered_path(raw, home=self.home, workspace=self.ws)

    def test_accepts_absolute_and_tilde(self) -> None:
        resolved, err = self._resolve("/Volumes/SSD/projeto")
        self.assertIsNone(err)
        self.assertEqual(resolved, Path("/Volumes/SSD/projeto"))
        resolved, err = self._resolve("~/Code/x")
        self.assertIsNone(err)
        self.assertEqual(resolved, self.home / "Code" / "x")

    def test_rejects_relative_glob_variable_empty(self) -> None:
        for raw in ("Code/x", "~/Code/*", "$HOME/x", "", "~/a?b", "~/a[1]"):
            with self.subTest(raw=raw):
                resolved, err = self._resolve(raw)
                self.assertIsNone(resolved)
                self.assertIsNotNone(err)

    def test_rejects_broad_roots_and_ancestors_of_home_or_workspace(self) -> None:
        for raw in ("/", "/Users", "/Users/batata", "/Users/batata/Documents", str(self.ws)):
            with self.subTest(raw=raw):
                resolved, err = self._resolve(raw)
                self.assertIsNone(resolved, raw)
                self.assertIsNotNone(err)


class GitPulseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "T")

    def _git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def _commit(self, name: str, message: str) -> None:
        (self.repo / name).write_text("x\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-q", "-m", message)

    def test_clean_repo_pulse(self) -> None:
        self._commit("a.md", "primeiro commit")
        pulse = collect_git_pulse(self.repo, now=NOW)
        self.assertEqual(pulse["kind"], "git")
        self.assertEqual(pulse["branch"], "main")
        self.assertFalse(pulse["dirty"])
        self.assertEqual(len(pulse["commits"]), 1)
        self.assertIn("primeiro commit", pulse["commits"][0]["subject"])
        self.assertIsNotNone(pulse["last_commit_at"])
        self.assertTrue(pulse["complete"])

    def test_dirty_repo_reports_working_tree_activity(self) -> None:
        self._commit("a.md", "base")
        (self.repo / "b.md").write_text("novo\n", encoding="utf-8")
        pulse = collect_git_pulse(self.repo, now=NOW)
        self.assertTrue(pulse["dirty"])
        self.assertIsNotNone(pulse["working_tree_activity_at"])

    def test_untracked_collapsed_dir_marks_incomplete(self) -> None:
        self._commit("a.md", "base")
        sub = self.repo / "nova-pasta"
        sub.mkdir()
        (sub / "dentro.md").write_text("x\n", encoding="utf-8")
        pulse = collect_git_pulse(self.repo, now=NOW)
        self.assertTrue(pulse["dirty"])
        self.assertFalse(pulse["complete"])

    def test_unborn_repo_is_graceful(self) -> None:
        pulse = collect_git_pulse(self.repo, now=NOW)
        self.assertEqual(pulse["commits"], [])
        self.assertIsNone(pulse["last_commit_at"])

    def test_not_a_repo_returns_none(self) -> None:
        plain = Path(self._tmp.name) / "plain"
        plain.mkdir()
        self.assertIsNone(collect_git_pulse(plain, now=NOW))

    def test_hostile_subject_is_sanitized_in_render(self) -> None:
        self._commit("a.md", f"traidor {PULSO_END} tenta fechar o bloco\x07")
        pulse = collect_git_pulse(self.repo, now=NOW)
        lines = "\n".join(render_pulse_lines(pulse, staleness="indeterminate", synced_at="2026-07-24"))
        self.assertNotIn(PULSO_END, lines)
        self.assertNotIn("\x07", lines)


class FolderPulseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "docs"
        self.root.mkdir()

    def test_shallow_scan_finds_latest_activity(self) -> None:
        old = self.root / "velho.md"
        old.write_text("x\n", encoding="utf-8")
        os.utime(old, (1000000000, 1000000000))
        sub = self.root / "sub"
        sub.mkdir()
        recent = sub / "novo.md"
        recent.write_text("x\n", encoding="utf-8")
        pulse = collect_folder_pulse(self.root, now=NOW)
        self.assertEqual(pulse["kind"], "folder")
        self.assertFalse(pulse["truncated"])
        self.assertEqual(
            pulse["last_activity_at"],
            datetime.fromtimestamp(recent.stat().st_mtime, tz=timezone.utc).isoformat(),
        )

    def test_excluded_dirs_do_not_count(self) -> None:
        nm = self.root / "node_modules"
        nm.mkdir()
        fresh = nm / "recentissimo.js"
        fresh.write_text("x\n", encoding="utf-8")
        base = self.root / "base.md"
        base.write_text("x\n", encoding="utf-8")
        os.utime(base, (1200000000, 1200000000))
        pulse = collect_folder_pulse(self.root, now=NOW)
        self.assertEqual(
            pulse["last_activity_at"],
            datetime.fromtimestamp(1200000000, tz=timezone.utc).isoformat(),
        )

    def test_symlink_is_not_traversed(self) -> None:
        outside = Path(self._tmp.name) / "fora"
        outside.mkdir()
        bomb = outside / "explosivo.md"
        bomb.write_text("x\n", encoding="utf-8")
        (self.root / "atalho").symlink_to(outside)
        stable = self.root / "base.md"
        stable.write_text("x\n", encoding="utf-8")
        os.utime(stable, (1200000000, 1200000000))
        os.utime(self.root / "atalho", (1000000000, 1000000000), follow_symlinks=False)
        pulse = collect_folder_pulse(self.root, now=NOW)
        self.assertEqual(
            pulse["last_activity_at"],
            datetime.fromtimestamp(1200000000, tz=timezone.utc).isoformat(),
        )

    def test_cap_marks_truncated(self) -> None:
        for i in range(30):
            (self.root / f"f{i:03d}.md").write_text("x\n", encoding="utf-8")
        pulse = collect_folder_pulse(self.root, now=NOW, max_entries=10)
        self.assertTrue(pulse["truncated"])
        self.assertFalse(pulse["complete"])


class NarrativeAndStalenessTests(unittest.TestCase):
    def _ctx(self, tmp: Path, content: str) -> Path:
        f = tmp / ".prumo-contexto.md"
        f.write_text(content, encoding="utf-8")
        return f

    def test_frontmatter_rfc3339_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._ctx(Path(tmp), "---\nupdated: 2026-07-24T10:00:00-03:00\n---\n# X\n")
            narrative = read_narrative(Path(tmp))
        self.assertTrue(narrative["exists"])
        self.assertEqual(narrative["source"], "frontmatter")
        self.assertIn("2026-07-24", narrative["updated_at"])

    def test_missing_or_invalid_frontmatter_gives_no_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._ctx(Path(tmp), "# Sem frontmatter\n")
            narrative = read_narrative(Path(tmp))
        self.assertIsNone(narrative["updated_at"])
        self.assertIsNone(narrative["source"])
        self.assertIsNotNone(narrative["file_mtime"])  # exposto, mas nunca substitui

    def test_absent_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            narrative = read_narrative(Path(tmp))
        self.assertFalse(narrative["exists"])

    def test_staleness_semantics(self) -> None:
        fresh = compute_staleness(
            narrative_updated_at="2026-07-24T19:00:00+00:00",
            last_activity_at="2026-07-24T10:00:00+00:00",
            complete=True,
            date_only=False,
            now=NOW,
        )
        self.assertEqual(fresh, "fresh")
        stale = compute_staleness(
            narrative_updated_at="2026-07-10T10:00:00+00:00",
            last_activity_at="2026-07-24T10:00:00+00:00",
            complete=True,
            date_only=False,
            now=NOW,
        )
        self.assertEqual(stale, "stale")
        # Sem narrativa, coleta incompleta, ou date-only no mesmo dia: nunca fresh.
        self.assertEqual(
            compute_staleness(narrative_updated_at=None, last_activity_at="x", complete=True, date_only=False, now=NOW),
            "indeterminate",
        )
        self.assertEqual(
            compute_staleness(
                narrative_updated_at="2026-07-24T19:00:00+00:00",
                last_activity_at="2026-07-24T10:00:00+00:00",
                complete=False,
                date_only=False,
                now=NOW,
            ),
            "indeterminate",
        )
        self.assertEqual(
            compute_staleness(
                narrative_updated_at="2026-07-24",
                last_activity_at="2026-07-24T10:00:00+00:00",
                complete=True,
                date_only=True,
                now=NOW,
            ),
            "indeterminate",
        )


class StalenessHardeningTests(unittest.TestCase):
    """Codex diff r1: futuro, naive e ordem cronológica."""

    def test_future_narrative_is_never_fresh(self) -> None:
        verdict = compute_staleness(
            narrative_updated_at="2099-01-01T00:00:00+00:00",
            last_activity_at="2026-07-24T10:00:00+00:00",
            complete=True,
            date_only=False,
            now=NOW,
        )
        self.assertEqual(verdict, "indeterminate")

    def test_naive_timestamp_is_rejected(self) -> None:
        verdict = compute_staleness(
            narrative_updated_at="2026-07-24T19:00:00",
            last_activity_at="2026-07-24T10:00:00+00:00",
            complete=True,
            date_only=False,
            now=NOW,
        )
        self.assertEqual(verdict, "indeterminate")

    def test_cross_offset_comparison_is_chronological(self) -> None:
        # 19:00-03:00 == 22:00Z > atividade 21:00Z → fresh (lexical falharia:
        # "2026-07-24T19" < "2026-07-24T21").
        verdict = compute_staleness(
            narrative_updated_at="2026-07-24T19:00:00-03:00",
            last_activity_at="2026-07-24T21:00:00+00:00",
            complete=True,
            date_only=False,
            now=datetime(2026, 7, 24, 23, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(verdict, "fresh")


class GrammarHardeningTests(unittest.TestCase):
    """Codex diff r1: contêiner único e marcadores reservados no doc inteiro."""

    def test_duplicated_container_is_error(self) -> None:
        text = _index(
            "## Projetos registrados\n\n### A\n- Caminho: /Volumes/x/a\n\n"
            "## Outra\n\n## Projetos registrados\n\n### B\n- Caminho: /Volumes/x/b\n"
        )
        self.assertTrue(parse_projects_index(text).errors)

    def test_marker_outside_container_is_error(self) -> None:
        text = _index(
            f"## Notas\n{PULSO_BEGIN}\n{PULSO_END}\n\n"
            "## Projetos registrados\n\n### A\n- Caminho: /Volumes/x/a\n"
        )
        self.assertTrue(parse_projects_index(text).errors)

    def test_broad_roots_volumes_tmp_rejected(self) -> None:
        home, ws = Path("/Users/batata"), Path("/Users/batata/Vida")
        for raw in ("/Volumes", "/tmp", "/private"):
            with self.subTest(raw=raw):
                resolved, err = resolve_registered_path(raw, home=home, workspace=ws)
                self.assertIsNone(resolved)
                self.assertIsNotNone(err)

    def test_canonical_duplicate_is_structural_zero_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "alvo"
            target.mkdir()
            text = _index(
                "## Projetos registrados\n\n"
                f"### A\n- Caminho: {target}\n\n"
                f"### B\n- Caminho: {target}/\n"
            )
            new_text, report = sync_index_text(
                text, home=Path(tmp) / "h", workspace=Path(tmp) / "ws", now=NOW
            )
        self.assertIsNone(new_text)
        self.assertTrue(report["structural"])


class NarrativeHardeningTests(unittest.TestCase):
    def test_symlinked_context_is_refused_visibly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "proj"
            project.mkdir()
            real = Path(tmp) / "fora.md"
            real.write_text("---\nupdated: 2026-07-24T10:00:00+00:00\n---\n", encoding="utf-8")
            (project / ".prumo-contexto.md").symlink_to(real)
            narrative = read_narrative(project)
        self.assertTrue(narrative["exists"])
        self.assertIsNone(narrative["updated_at"])
        self.assertIn("symlink", narrative["error"])

    def test_invalid_encoding_degrades_visibly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "proj"
            project.mkdir()
            (project / ".prumo-contexto.md").write_bytes(b"\xff\xfe caos")
            narrative = read_narrative(project)
        self.assertIn("encoding", narrative["error"])


class CrlfRoundtripTests(unittest.TestCase):
    def test_crlf_document_preserves_authorial_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            body = (
                "# Projetos\r\n\r\nnota autoral\r\n\r\n"
                "## Projetos registrados\r\n\r\n"
                f"### Repo\r\n- Caminho: {repo}\r\n"
            )
            new_text, report = sync_index_text(
                body, home=Path(tmp) / "h", workspace=Path(tmp) / "ws", now=NOW
            )
        self.assertEqual(report["errors"], [])
        self.assertTrue(new_text.startswith("# Projetos\r\n\r\nnota autoral\r\n"))
        self.assertIn(PULSO_BEGIN + "\r\n", new_text)


class BindingMatrixTests(unittest.TestCase):
    """Codex diff r2, achado 9: as condições declaradas viram fixtures."""

    def test_detached_head_is_reported_not_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            sha = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--detach", sha], check=True)
            pulse = collect_git_pulse(repo, now=NOW)
        self.assertEqual(pulse["branch"], "(detached)")
        self.assertTrue(pulse["complete"])

    def test_git_timeout_is_visible_error(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            with mock.patch.object(projetos, "_run_git", return_value=None):
                pulse = collect_git_pulse(repo, now=NOW)
        self.assertFalse(pulse["complete"])
        self.assertTrue(pulse["errors"])

    def test_lstat_permission_failure_is_visible(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            (repo / "novo.md").write_text("x\n", encoding="utf-8")
            with mock.patch.object(projetos.os, "lstat", side_effect=OSError("negado")):
                pulse = collect_git_pulse(repo, now=NOW)
        self.assertTrue(pulse["dirty"])
        self.assertFalse(pulse["complete"])
        self.assertTrue(any("stat" in e for e in pulse["errors"]))

    def test_mode_only_change_counts_as_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            target = repo / "a.md"
            os.utime(target, (1000000000, 1000000000))
            os.chmod(target, 0o755)  # mode muda → porcelain acusa; ctime recente
            pulse = collect_git_pulse(repo, now=NOW)
        self.assertTrue(pulse["dirty"])
        self.assertIsNotNone(pulse["working_tree_activity_at"])
        self.assertGreater(pulse["working_tree_activity_at"], "2020-01-01")

    def test_sync_does_not_touch_git_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            (repo / "sujo.md").write_text("x\n", encoding="utf-8")
            index = repo / ".git" / "index"
            before = index.read_bytes()
            collect_git_pulse(repo, now=NOW)
            after = index.read_bytes()
        self.assertEqual(before, after, "git status atualizou o index — sync deixou de ser read-only no projeto")

    def test_multi_section_sync_is_literally_stable_outside_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_a = _make_repo(Path(tmp) / "a")
            repo_b = _make_repo(Path(tmp) / "b")
            text = (
                "# Projetos\n\nprosa autoral 1\n\n"
                "## Projetos registrados\n\n"
                f"### A\n- Caminho: {repo_a}\n- Nota: alfa\n\n"
                f"### B\n- Caminho: {repo_b}\n- Nota: beta\n\n"
                "## Rodapé autoral\n\nfim\n"
            )
            new_text, report = sync_index_text(
                text, home=Path(tmp) / "h", workspace=Path(tmp) / "ws", now=NOW
            )
            self.assertEqual(report["errors"], [])
            # Remove os blocos gerados e compara o restante LITERALMENTE.
            import re as _re
            stripped = _re.sub(
                rf"{_re.escape(PULSO_BEGIN)}.*?{_re.escape(PULSO_END)}\n",
                "",
                new_text,
                flags=_re.DOTALL,
            )
        self.assertEqual(stripped, text, "bytes autorais mudaram fora dos blocos")

    def test_repair_preserves_authorial_projetos_md(self) -> None:
        import re as _re
        from prumo_runtime.workspace import (
            WorkspaceConfig, create_missing_files, ensure_directories,
            install_skills, repair_workspace,
        )
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            config = WorkspaceConfig(
                workspace=ws, user_name="T", layout_mode="nested", workspace_name="W"
            )
            ensure_directories(ws)
            install_skills(ws, layout_mode="nested")
            create_missing_files(config)
            projetos_md = ws / "Prumo" / "Agente" / "PROJETOS.md"
            custom = "# Projetos\n\nconteúdo 100% autoral do usuário\n"
            projetos_md.write_text(custom, encoding="utf-8")
            core = ws / ".prumo" / "system" / "PRUMO-CORE.md"
            core.write_text(
                _re.sub(r"prumo_version:\s*[0-9.]+", "prumo_version: 5.0.0",
                        core.read_text(encoding="utf-8"), count=1),
                encoding="utf-8",
            )
            repair_workspace(ws)
            after = projetos_md.read_text(encoding="utf-8")
        self.assertEqual(after, custom, "repair tocou o PROJETOS.md autoral")

    def test_projetos_command_never_writes_version_cache(self) -> None:
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        from prumo_runtime import version_check
        from prumo_runtime.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            agente = ws / "Prumo" / "Agente"
            agente.mkdir(parents=True)
            (agente / "PROJETOS.md").write_text(_index(""), encoding="utf-8")
            boom = mock.patch.object(
                version_check, "_write_cache",
                side_effect=AssertionError("banner escreveu cache no `projetos`"),
            )
            with boom, mock.patch.object(version_check, "_should_suppress", wraps=version_check._should_suppress):
                with redirect_stdout(io.StringIO()):
                    rc = main(["projetos", "--workspace", str(ws), "--format", "json"])
        self.assertEqual(rc, 0)


class Round3Tests(unittest.TestCase):
    def test_removed_path_replaces_old_pulse_with_note(self) -> None:
        text = _index(
            "## Projetos registrados\n\n### SemCaminho\n\n"
            f"{PULSO_BEGIN}\n(pulso gerado ... frescor: fresh)\nvelho\n{PULSO_END}\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            new_text, report = sync_index_text(
                text, home=Path(tmp) / "h", workspace=Path(tmp) / "ws", now=NOW
            )
        self.assertIsNotNone(new_text)
        self.assertNotIn("frescor: fresh", new_text)
        self.assertIn("sem caminho registrado", new_text)

    def test_revparse_timeout_is_error_not_unborn(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            real = projetos._run_git

            def selective(path, *args):
                if args and args[0] == "log":
                    return subprocess.CompletedProcess(args, 1, "", "boom")
                if args and args[0] == "rev-parse":
                    return None  # timeout
                return real(path, *args)

            with mock.patch.object(projetos, "_run_git", side_effect=selective):
                pulse = collect_git_pulse(repo, now=NOW)
        self.assertFalse(pulse["complete"])
        self.assertTrue(any("rev-parse" in e for e in pulse["errors"]))

    def test_insertion_adds_only_marker_delimited_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            text = _index(
                "## Projetos registrados\n\n"
                f"### Repo\n- Caminho: {repo}\n"  # sem blank no fim
            )
            new_text, report = sync_index_text(
                text, home=Path(tmp) / "h", workspace=Path(tmp) / "ws", now=NOW
            )
            import re as _re
            stripped = _re.sub(
                rf"{_re.escape(PULSO_BEGIN)}.*?{_re.escape(PULSO_END)}\n",
                "",
                new_text,
                flags=_re.DOTALL,
            )
        self.assertEqual(stripped, text, "inserção adicionou bytes fora dos delimitadores")

    def test_windows_absolute_path_is_accepted_as_format(self) -> None:
        resolved, err = resolve_registered_path(
            "C:/Users/dono/Code/proj", home=Path("/Users/b"), workspace=Path("/Users/b/V")
        )
        self.assertIsNone(err, "formato absoluto do Windows não pode ser rejeitado")


class SanitizeTests(unittest.TestCase):
    def test_removes_controls_and_neutralizes_markers(self) -> None:
        dirty = f"a\x07b {PULSO_BEGIN} c <!-- livre --> d"
        clean = sanitize_text(dirty)
        self.assertNotIn("\x07", clean)
        self.assertNotIn(PULSO_BEGIN, clean)
        self.assertNotIn("<!--", clean)


class SyncTransactionalTests(unittest.TestCase):
    def _repo_fixture(self, tmp: Path) -> Path:
        return _make_repo(tmp)

    def test_sync_fills_block_and_preserves_authorial_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo_fixture(Path(tmp))
            head = "# Projetos\n\n  nota autoral com indentação  \n\n"
            tail = "\n## Reflexões soltas\n\nfica intacto\n\n\n"
            body = (
                "## Projetos registrados\n\n"
                f"### Repo\n- Caminho: {repo}\n- Nota: autoral na seção\n\n"
                f"{PULSO_BEGIN}\nconteúdo velho\n{PULSO_END}\n"
            )
            text = head + body + tail
            new_text, report = sync_index_text(
                text, home=Path(tmp), workspace=Path(tmp) / "ws", now=NOW
            )
        self.assertEqual(report["errors"], [])
        self.assertTrue(new_text.startswith(head))
        self.assertTrue(new_text.endswith(tail))
        self.assertIn("- Nota: autoral na seção", new_text)
        self.assertNotIn("conteúdo velho", new_text)
        self.assertIn("branch", new_text)
        self.assertEqual(new_text.count(PULSO_BEGIN), 1)
        self.assertEqual(new_text.count(PULSO_END), 1)

    def test_sync_inserts_block_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo_fixture(Path(tmp))
            text = _index(
                "## Projetos registrados\n\n"
                f"### Repo\n- Caminho: {repo}\n"
            )
            new_text, report = sync_index_text(
                text, home=Path(tmp), workspace=Path(tmp) / "ws", now=NOW
            )
        self.assertEqual(report["errors"], [])
        self.assertEqual(new_text.count(PULSO_BEGIN), 1)

    def test_structural_error_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = _index(
                "## Projetos registrados\n\n### X\n- Caminho: /a\n- Caminho: /b\n"
            )
            new_text, report = sync_index_text(
                text, home=Path(tmp), workspace=Path(tmp) / "ws", now=NOW
            )
        self.assertIsNone(new_text)
        self.assertTrue(report["structural"])

    def test_missing_registered_path_is_visible_error_but_partial_sync_proceeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo_fixture(Path(tmp))
            text = _index(
                "## Projetos registrados\n\n"
                f"### Ok\n- Caminho: {repo}\n\n"
                "### Sumido\n- Caminho: /Volumes/nao-existe-xyz\n"
            )
            new_text, report = sync_index_text(
                text, home=Path(tmp), workspace=Path(tmp) / "ws", now=NOW
            )
        self.assertIsNotNone(new_text)
        self.assertTrue(any("Sumido" in e for e in report["errors"]))


class CliTests(unittest.TestCase):
    def test_report_mode_reads_only_and_sync_writes(self) -> None:
        import io
        from contextlib import redirect_stdout
        from prumo_runtime.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            agente = ws / "Prumo" / "Agente"
            agente.mkdir(parents=True)
            repo = _make_repo(Path(tmp))
            index = agente / "PROJETOS.md"
            index.write_text(
                _index(
                    "## Projetos registrados\n\n"
                    f"### Repo\n- Caminho: {repo}\n"
                ),
                encoding="utf-8",
            )
            before = index.read_text(encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["projetos", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 0)
            self.assertEqual(index.read_text(encoding="utf-8"), before, "report não pode escrever")
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["schema_version"], "prumo_projetos.v1")

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["projetos", "--sync", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 0)
            after = index.read_text(encoding="utf-8")
            self.assertNotEqual(after, before)
            self.assertIn(PULSO_BEGIN, after)

    def test_partial_sync_exits_1_structural_exits_2(self) -> None:
        import io
        from contextlib import redirect_stdout
        from prumo_runtime.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            agente = ws / "Prumo" / "Agente"
            agente.mkdir(parents=True)
            index = agente / "PROJETOS.md"

            index.write_text(
                _index("## Projetos registrados\n\n### S\n- Caminho: /Volumes/x-nao-existe\n"),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                rc = main(["projetos", "--sync", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 1)

            broken = _index("## Projetos registrados\n\n### X\n- Caminho: /a\n- Caminho: /b\n")
            index.write_text(broken, encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                rc = main(["projetos", "--sync", "--workspace", str(ws), "--format", "json"])
            self.assertEqual(rc, 2)
            self.assertEqual(index.read_text(encoding="utf-8"), broken, "estrutura inválida: zero escrita")


class SkillGuardsTests(unittest.TestCase):
    REPO_ROOT = Path(__file__).resolve().parents[2]

    def test_revue_hardcode_never_returns_to_canonical(self) -> None:
        procedure = (
            self.REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-procedure.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Revue", procedure, "path pessoal do dono vazou de volta pro canônico")
        self.assertIn("Roteamento de conteúdo", procedure)
        # O template REAL do setup (file-templates) também precisa da seção —
        # sem ela, workspace novo nasce sem o lugar do registro (Codex r1.9).
        file_templates = (
            self.REPO_ROOT / "skills" / "prumo" / "references" / "file-templates.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Roteamento de conteúdo", file_templates)

    def test_contexto_template_reference_exists_with_frontmatter(self) -> None:
        template = (
            self.REPO_ROOT / "skills" / "prumo" / "references" / "contexto-projeto-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn(".prumo-contexto.md", template)
        self.assertIn("updated:", template)


if __name__ == "__main__":
    unittest.main()
