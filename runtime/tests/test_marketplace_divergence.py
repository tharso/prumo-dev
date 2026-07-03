"""
Checkout do marketplace divergente (#145).

Caso real (máquina do Tharso, 2026-07-02): o espelho público reescreveu
história; o checkout do marketplace no store do Cowork ficou órfão (sem
ancestral comum com o remoto). O `prumo_cowork_update.sh` usava só
fast-forward — falhava pra sempre — e o doctor chamava tudo de "defasado",
recomendando um update que não ia funcionar.

Travas:
(1) o update recupera checkout divergente LIMPO com reset pro remoto;
(2) o update NUNCA reseta por cima de modificação local — aborta com
    mensagem clara;
(3) o caminho feliz (fast-forward) segue intacto, sem reset;
(4) o doctor nomeia a divergência quando consegue classificá-la.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UPDATE_SCRIPT = REPO_ROOT / "scripts" / "prumo_cowork_update.sh"
DOCTOR_SCRIPT = REPO_ROOT / "scripts" / "prumo_cowork_doctor.sh"

GIT_ID = ["-c", "user.email=teste@prumo.local", "-c", "user.name=Teste Prumo"]


def _git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *GIT_ID, *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _make_history(remote: Path, version: str) -> None:
    """(Re)cria o repo 'remoto' com uma história NOVA — simula o espelho reescrito."""
    remote.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(remote / ".git", ignore_errors=True)
    _git(["init", "-q", "-b", "main"], remote)
    (remote / "VERSION").write_text(version + "\n", encoding="utf-8")
    _git(["add", "."], remote)
    _git(["commit", "-q", "-m", f"v{version}"], remote)


def _make_store(tmp: Path, remote: Path) -> tuple[Path, Path, Path]:
    """Store fake do Cowork com o checkout do marketplace clonado do remoto."""
    sessions = tmp / "sessions"
    store = sessions / "sess-a" / "sess-b" / "cowork_plugins"
    market = store / "marketplaces" / "prumo-marketplace"
    market.parent.mkdir(parents=True)
    subprocess.run(
        ["git", *GIT_ID, "clone", "-q", str(remote), str(market)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    (store / "known_marketplaces.json").write_text(
        json.dumps(
            {
                "prumo-marketplace": {
                    "source": {"source": "git", "url": str(remote)},
                    "lastUpdated": "2026-03-19T10:46:02Z",
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return sessions, store, market


def _run_update(sessions: Path) -> dict:
    completed = subprocess.run(
        ["bash", str(UPDATE_SCRIPT), "--sessions-root", str(sessions), "--json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"update falhou: {completed.stderr}\n{completed.stdout}")
    return json.loads(completed.stdout)


@unittest.skipUnless(__import__("os").name == "posix", "scripts bash (macOS/Linux)")
class UpdateDivergenceTests(unittest.TestCase):
    def test_recupera_checkout_divergente_limpo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "remote"
            _make_history(remote, "4.7.0")
            sessions, store, market = _make_store(tmp_path, remote)
            _make_history(remote, "5.25.0")  # espelho reescreve a história

            payload = _run_update(sessions)
            result = payload["results"][0]
            self.assertIsNone(result["error"], f"update deveria recuperar: {result['error']}")
            self.assertEqual(result["after_version"], "5.25.0")
            self.assertTrue(
                result.get("recovered"),
                "recuperação de divergência deveria ser reportada no resultado",
            )
            known = json.loads((store / "known_marketplaces.json").read_text())
            self.assertNotEqual(
                known["prumo-marketplace"]["lastUpdated"],
                "2026-03-19T10:46:02Z",
                "timestamp de sync deveria ter sido renovado",
            )

    def test_nunca_reseta_checkout_com_modificacao_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "remote"
            _make_history(remote, "4.7.0")
            sessions, _store, market = _make_store(tmp_path, remote)
            _make_history(remote, "5.25.0")
            (market / "VERSION").write_text("4.7.0-editado-na-mao\n", encoding="utf-8")

            payload = _run_update(sessions)
            result = payload["results"][0]
            self.assertIsNotNone(result["error"], "checkout sujo não pode ser resetado no escuro")
            self.assertIn("modificaç", result["error"].lower())
            self.assertEqual(
                (market / "VERSION").read_text(encoding="utf-8").strip(),
                "4.7.0-editado-na-mao",
                "a modificação local tem que sobreviver intacta",
            )

    def test_caminho_feliz_fast_forward_sem_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "remote"
            _make_history(remote, "4.7.0")
            sessions, _store, _market = _make_store(tmp_path, remote)
            # História PRESERVADA: só um commit novo em cima (ff possível).
            (remote / "VERSION").write_text("5.25.0\n", encoding="utf-8")
            _git(["add", "."], remote)
            _git(["commit", "-q", "-m", "v5.25.0"], remote)

            payload = _run_update(sessions)
            result = payload["results"][0]
            self.assertIsNone(result["error"])
            self.assertEqual(result["after_version"], "5.25.0")
            self.assertFalse(
                result.get("recovered"),
                "fast-forward limpo não é recuperação — caminho feliz intacto",
            )


@unittest.skipUnless(__import__("os").name == "posix", "scripts bash (macOS/Linux)")
class DoctorDivergenceTests(unittest.TestCase):
    def test_doctor_nomeia_a_divergencia(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "remote"
            _make_history(remote, "4.7.0")
            sessions, _store, market = _make_store(tmp_path, remote)
            _make_history(remote, "5.25.0")
            # Fetch prévio (como na máquina real): o objeto remoto existe
            # localmente, então o doctor consegue classificar sem mutar nada.
            _git(["fetch", "origin", "main"], market)

            completed = subprocess.run(
                ["bash", str(DOCTOR_SCRIPT), "--sessions-root", str(sessions), "--json"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            # Stores reais do HOME podem aparecer na varredura — mirar o fake.
            target = next(r for r in result["roots"] if r["root"] == str(_store))
            self.assertEqual(target.get("marketplace_checkout_divergence"), "divergente")
            diagnosis = " ".join(target.get("diagnosis", []))
            self.assertIn("DIVERGIU", diagnosis, f"doctor deveria nomear a divergência: {diagnosis}")


if __name__ == "__main__":
    unittest.main()
