"""#335 — a última milha do workspace no `prumo update`.

Incidente de 11/08: `prumo update --yes` fora do workspace levou o runtime a
5.95.0 e deixou o checkout do DailyLife em 5.94.0 — em silêncio. E dentro do
workspace o review achou pior: a guarda de binário divergente escondia o
warning (só JSON) enquanto o TEXTO recomendava exatamente o repair que
sincronizaria o workspace com a fonte errada.

Contratos aqui: `last_mile` declarado fora de workspace (comando copiável só
com versão confirmada); guarda A (interpretador) imprime warning e zera
qualquer menção a repair; guarda B (PATH) substitui a recomendação genérica
pela nota específica. Update real não roda em CI — tudo mocka _execute_plan
(padrão do test_update).
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from prumo_runtime.cli import main
from prumo_runtime.commands.update import _run_post_update_repair


def setUpModule():
    if sys.version_info < (3, 11):
        raise unittest.SkipTest(
            "prumo update requer tomllib (stdlib 3.11+); na mínima 3.10 vale "
            "o gate de mensagem legível (#301)"
        )


def _write_marker(path: Path) -> None:
    marker = {
        "schema_version": "1.0",
        "installed_version": "5.3.0",
        "installed_at": "2026-05-05T20:00:00Z",
        "launcher": "manual",
        "package_manager": "pip-user",
        "source_kind": "archive",
        "source": "https://github.com/tharso/prumo/archive/refs/heads/main.tar.gz",
        "python": "/usr/bin/python3.11",
        "prumo_executable": "/home/user/.local/bin/prumo",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker), encoding="utf-8")


def _nested_workspace(root: Path, core_version: str | None = None) -> Path:
    (root / ".prumo" / "system").mkdir(parents=True)
    if core_version:
        (root / ".prumo" / "system" / "PRUMO-CORE.md").write_text(
            f"> **prumo_version: {core_version}**\n", encoding="utf-8"
        )
    return root


class UltimaMilhaTests(unittest.TestCase):
    """Fluxo completo via `main`, com o plano de execução mockado."""

    def _run_update(self, tmpdir: Path, *, cwd: Path, post_version: str | None,
                    fmt: str | None = None, extra_patches: list | None = None):
        marker = tmpdir / "install-method.json"
        _write_marker(marker)
        argv = ["update", "--yes"] + (["--format", fmt] if fmt else [])
        patches = [
            patch("prumo_runtime.commands.update.install_marker_path", return_value=marker),
            patch("prumo_runtime.commands.update.fetch_remote_version", return_value="5.99.0"),
            patch("prumo_runtime.commands.update._execute_plan", return_value=(0, "5.99.0")),
            patch("prumo_runtime.commands.update._confirm_update", return_value=True),
            patch("prumo_runtime.commands.update._get_post_update_version", return_value=post_version),
            patch("prumo_runtime.commands.update.Path.cwd", return_value=cwd),
        ] + (extra_patches or [])
        buf = io.StringIO()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            with redirect_stdout(buf):
                rc = main(argv)
        return rc, buf.getvalue()

    # --- Fora de workspace: o buraco do incidente de 11/08 ---

    def test_fora_de_workspace_declara_last_mile_com_comando_copiavel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc, out = self._run_update(root, cwd=root, post_version="5.99.0", fmt="json")
            payload = json.loads(out)
            lm = payload["post_update"]["last_mile"]
            self.assertEqual(lm["status"], "nao_sincronizado")
            self.assertIn("nenhum workspace", lm["message"])
            # Comando copiável: sem placeholders `<>` que o shell interpretaria.
            self.assertEqual(
                lm["recommended_command"], "prumo repair --workspace /caminho/do/workspace"
            )

    def test_fora_de_workspace_texto_declara_a_ultima_milha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc, out = self._run_update(root, cwd=root, post_version="5.99.0")
            self.assertIn("nenhum workspace", out)
            self.assertIn("prumo repair --workspace /caminho/do/workspace", out)

    def test_fora_de_workspace_sem_versao_confirmada_nao_prescreve_repair(self):
        """Precedência do last_mile (spec r3): guarda A disparada ⇒ a
        recuperação do runtime prevalece; zero `prumo repair` na saída."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc, out = self._run_update(root, cwd=root, post_version="5.98.0", fmt="json")
            payload = json.loads(out)
            self.assertFalse(payload["post_update"]["version_confirmed"])
            self.assertIsNone(payload["post_update"]["last_mile"]["recommended_command"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc, out = self._run_update(root, cwd=root, post_version="5.98.0")
            self.assertNotIn("prumo repair", out)

    # --- Guarda A: artefato × interpretador do update ---

    def test_guarda_a_warning_sai_no_texto_e_zera_repair(self):
        """O warning existia só no JSON (update.py:701 vs _emit) — a saída
        humana escondia exatamente o caso em que repair usaria a fonte errada.
        Fixture com core defasado prova que NEM a linha do #170 recomenda
        repair quando a versão não foi confirmada."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_workspace(Path(tmp), core_version="5.0.0")
            rc, out = self._run_update(ws, cwd=ws, post_version="5.98.0")
            self.assertIn("5.98.0", out)          # warning menciona o que o binário reporta
            self.assertIn("interpretador", out)    # recuperação da guarda A, não de PATH
            self.assertNotIn("PATH", out)          # medição via sys.executable não prova PATH
            self.assertNotIn("prumo repair", out)  # invariante: zero repair na saída inteira
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_workspace(Path(tmp), core_version="5.0.0")
            rc, out = self._run_update(ws, cwd=ws, post_version="5.98.0", fmt="json")
            payload = json.loads(out)
            self.assertFalse(payload["post_update"]["repair_suggested"])
            self.assertIn("warning", payload["post_update"])

    # --- Guarda B: nota específica substitui a recomendação genérica ---

    def test_guarda_b_nota_substitui_recomendacao_generica(self):
        """Hoje o texto imprime a nota E "Rode `prumo repair --workspace .`"
        logo depois — contraditório quando a nota diz que o binário do PATH é
        a fonte errada."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_workspace(Path(tmp))
            nota = "o `prumo` do PATH (/x/prumo) está em 5.98.0, não na recém-instalada 5.99.0"
            rc, out = self._run_update(
                ws, cwd=ws, post_version="5.99.0",
                extra_patches=[patch(
                    "prumo_runtime.commands.update._run_post_update_repair",
                    return_value={"repair_executed": False, "repair_note": nota},
                )],
            )
            self.assertIn(nota, out)
            self.assertNotIn("Rode `prumo repair --workspace .`", out)


    def test_guarda_b_zera_repair_suggested_tambem_no_json(self):
        """335-code-r2: o texto escondia a recomendação, mas o JSON seguia com
        repair_suggested: true — consumidor de JSON re-sugeriria o repair
        inseguro. A nota substitui a recomendação nos DOIS formatos."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_workspace(Path(tmp))
            rc, out = self._run_update(
                ws, cwd=ws, post_version="5.99.0", fmt="json",
                extra_patches=[patch(
                    "prumo_runtime.commands.update._run_post_update_repair",
                    return_value={"repair_executed": False, "repair_note": "fonte errada"},
                )],
            )
            payload = json.loads(out)
            self.assertFalse(payload["post_update"]["repair_suggested"])
        # PATH ausente atravessando a guarda REAL (sem mock do repair):
        with tempfile.TemporaryDirectory() as tmp:
            ws = _nested_workspace(Path(tmp))
            rc, out = self._run_update(
                ws, cwd=ws, post_version="5.99.0", fmt="json",
                extra_patches=[patch(
                    "prumo_runtime.commands.update.shutil.which", return_value=None,
                )],
            )
            payload = json.loads(out)
            self.assertFalse(payload["post_update"]["repair_suggested"])
            self.assertIn("passo 0", payload["post_update"]["repair_note"])


class RunPostUpdateRepairNotesTests(unittest.TestCase):
    """As notas da guarda B, chamando `_run_post_update_repair` direto."""

    def test_binario_ausente_orienta_passo_zero_sem_comando_contraditorio(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("prumo_runtime.commands.update.shutil.which", return_value=None):
                result = _run_post_update_repair(Path(tmp), expected_version="5.99.0")
        self.assertFalse(result["repair_executed"])
        self.assertIn("passo 0", result["repair_note"])
        self.assertIn("runtime-paths", result["repair_note"])
        # Sem `prumo` no PATH, "rode `prumo repair`" é comando que não roda.
        self.assertNotIn("rode `prumo repair", result["repair_note"])

    def test_binario_divergente_orienta_alinhar_o_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = MagicMock(returncode=0, stdout="prumo 5.98.0\n")
            with patch("prumo_runtime.commands.update.shutil.which", return_value="/x/prumo"):
                with patch(
                    "prumo_runtime.commands.update.subprocess.run", return_value=fake
                ) as run:
                    result = _run_post_update_repair(Path(tmp), expected_version="5.99.0")
        self.assertFalse(result["repair_executed"])
        self.assertIn("5.98.0", result["repair_note"])
        self.assertIn("PATH", result["repair_note"])
        # Só a sonda `--version` rodou; o repair nunca foi tentado.
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
