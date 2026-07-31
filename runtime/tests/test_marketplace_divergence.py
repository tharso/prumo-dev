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
    """Roda o update HERMÉTICO, sem tocar a store real da máquina.

    Desde a #276 o script também procura a store ATIVA (`~/.claude/plugins`
    por default). Sem apontar `--plugins-root` para um caminho inexistente,
    este teste faria `git fetch` na store de verdade de quem roda a suíte —
    e `results[0]` seria ela, não a fixture. Teste que mexe no ambiente do
    dono não é teste, é visita indesejada.
    """
    sem_ativa = sessions.parent / "sem-store-ativa"
    completed = subprocess.run(
        [
            "bash", str(UPDATE_SCRIPT),
            "--sessions-root", str(sessions),
            "--plugins-root", str(sem_ativa),
            "--json",
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    # Código 3 = "só achei store legada", que é exatamente o cenário destas
    # fixtures. O que não pode é o script estourar (>3) ou não emitir JSON.
    if completed.returncode not in (0, 3):
        raise AssertionError(f"update falhou: {completed.stderr}\n{completed.stdout}")
    payload = json.loads(completed.stdout)
    assert not payload["active_store_reached"], (
        "o teste alcançou uma store ATIVA — a fixture deixou de ser hermética"
    )
    return payload


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

    def test_nunca_reseta_commits_locais(self) -> None:
        """Checkout LIMPO mas com commits locais (ancestral comum existe):
        ff falha e o update NÃO pode resetar — commits não são nossos
        (achado do Codex na revisão de código, rodada 1)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "remote"
            _make_history(remote, "4.7.0")
            sessions, _store, market = _make_store(tmp_path, remote)
            # Commit LOCAL no checkout (working tree fica limpa).
            (market / "NOTA-LOCAL.md").write_text("commit meu\n", encoding="utf-8")
            _git(["add", "."], market)
            _git(["commit", "-q", "-m", "commit local no checkout"], market)
            # Remoto avança na MESMA história (ancestral comum preservado).
            (remote / "VERSION").write_text("5.25.0\n", encoding="utf-8")
            _git(["add", "."], remote)
            _git(["commit", "-q", "-m", "v5.25.0"], remote)

            payload = _run_update(sessions)
            result = payload["results"][0]
            self.assertIsNotNone(result["error"], "commits locais não podem ser descartados")
            self.assertIn("commits locais", result["error"].lower())
            self.assertTrue(
                (market / "NOTA-LOCAL.md").exists(),
                "o commit local tem que sobreviver intacto",
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
                [
                    "bash", str(DOCTOR_SCRIPT),
                    "--sessions-root", str(sessions),
                    # Sem isto o doctor LÊ as stores reais de quem roda a
                    # suíte (não muta, mas não é hermético) — Codex, r22.
                    # `--offline` NÃO entra: ele pula o ls-remote, que é
                    # exatamente o que estes testes verificam. O remoto da
                    # fixture é um bare local, então não há rede envolvida.
                    "--extra-root", str(sessions.parent / "sem-extra"),
                    "--json",
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            # Stores reais do HOME podem aparecer na varredura — mirar o fake.
            target = next(r for r in result["roots"] if r["root"] == str(_store))
            self.assertEqual(target.get("marketplace_checkout_divergence"), "divergente")
            diagnosis = " ".join(target.get("diagnosis", []))
            self.assertIn("DIVERGIU", diagnosis, f"doctor deveria nomear a divergência: {diagnosis}")

    def test_doctor_distingue_commits_locais_de_historia_reescrita(self) -> None:
        """Ancestral comum + commits locais NÃO é 'atrás' nem 'divergente' —
        é a terceira natureza, e o doctor não pode prometer ff nem reset."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "remote"
            _make_history(remote, "4.7.0")
            sessions, _store, market = _make_store(tmp_path, remote)
            (market / "NOTA-LOCAL.md").write_text("commit meu\n", encoding="utf-8")
            _git(["add", "."], market)
            _git(["commit", "-q", "-m", "commit local"], market)
            (remote / "VERSION").write_text("5.25.0\n", encoding="utf-8")
            _git(["add", "."], remote)
            _git(["commit", "-q", "-m", "v5.25.0"], remote)
            _git(["fetch", "origin", "main"], market)

            completed = subprocess.run(
                [
                    "bash", str(DOCTOR_SCRIPT),
                    "--sessions-root", str(sessions),
                    # Sem isto o doctor LÊ as stores reais de quem roda a
                    # suíte (não muta, mas não é hermético) — Codex, r22.
                    # `--offline` NÃO entra: ele pula o ls-remote, que é
                    # exatamente o que estes testes verificam. O remoto da
                    # fixture é um bare local, então não há rede envolvida.
                    "--extra-root", str(sessions.parent / "sem-extra"),
                    "--json",
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            target = next(r for r in result["roots"] if r["root"] == str(_store))
            self.assertEqual(target.get("marketplace_checkout_divergence"), "commits_locais")


if __name__ == "__main__":
    unittest.main()
