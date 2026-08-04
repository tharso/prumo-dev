"""Frescor do clone da store ativa no doctor (#324).

O incidente de 03/08: espelho servindo 5.89.0, runtime local atualizável —
e o botão "Atualizar" do app DESABILITADO, porque o clone do marketplace em
`~/.claude/plugins/marketplaces/` estava congelado no commit de 31/07
(FETCH_HEAD de 3 dias antes). O app compara o instalado contra a fotocópia
velha e conclui "nada a atualizar". O refresh é do app; a DETECÇÃO é nossa —
até aqui, nenhum instrumento nomeava esse estado e a última milha falhava em
silêncio.

Vizinhas: #299 (a outra perna da divergência de fontes), #275 (o achado sai
em texto E json — alerta que só existe no JSON não conta), #291 (a ida ao
remoto vai com cache-busting — o CDN já mentiu duas vezes).
"""

import argparse
import contextlib
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from prumo_runtime.commands import doctor, store_clone


def _args(**kw):
    base = {"host": True, "format": "text", "network_timeout": 0.1}
    base.update(kw)
    return argparse.Namespace(**base)


def _montar_store(registry: dict | None = None, clone_de_verdade: bool = True) -> Path:
    """Uma store unificada de mentira: known_marketplaces.json + clone."""
    root = Path(tempfile.mkdtemp())
    clone = root / "marketplaces" / "prumo-marketplace"
    if clone_de_verdade:
        (clone / "skills" / "prumo").mkdir(parents=True)
        (clone / "VERSION").write_text("5.83.2\n", encoding="utf-8")
        (clone / ".git").mkdir()
        (clone / ".git" / "FETCH_HEAD").write_text("x", encoding="utf-8")
    if registry is not None:
        if registry == "auto":
            registry = {
                "prumo-marketplace": {
                    "source": {"source": "git", "url": "https://github.com/tharso/prumo.git"},
                    "installLocation": str(clone),
                }
            }
        (root / "known_marketplaces.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
    return root


class LocalizadorTest(unittest.TestCase):
    def test_registry_e_a_fonte_primaria(self) -> None:
        root = _montar_store(registry="auto")
        clone = store_clone.locate_prumo_clone(store_root=root)
        self.assertIsNotNone(clone)
        self.assertTrue(str(clone).endswith("prumo-marketplace"))

    def test_sem_registry_cai_na_varredura(self) -> None:
        # O registry é como o APP resolve; sem ele, um clone do espelho se
        # reconhece pela árvore (VERSION + skills/prumo).
        root = _montar_store(registry=None)
        self.assertIsNotNone(store_clone.locate_prumo_clone(store_root=root))

    def test_registry_apontando_pro_nada_cai_na_varredura(self) -> None:
        root = _montar_store(registry=None)
        (root / "known_marketplaces.json").write_text(
            json.dumps({"prumo-marketplace": {
                "source": {"url": "https://github.com/tharso/prumo.git"},
                "installLocation": str(root / "nao-existe"),
            }}),
            encoding="utf-8",
        )
        self.assertIsNotNone(store_clone.locate_prumo_clone(store_root=root))

    def test_host_sem_store_e_ausente(self) -> None:
        vazio = Path(tempfile.mkdtemp())
        self.assertIsNone(store_clone.locate_prumo_clone(store_root=vazio))


class ColetorTest(unittest.TestCase):
    def test_fresca_quando_clone_bate_com_o_remoto(self) -> None:
        root = _montar_store(registry="auto")
        retrato = store_clone.collect(store_root=root, remote_version="5.83.2")
        self.assertTrue(retrato["found"])
        self.assertEqual(retrato["status"], "fresca")
        self.assertEqual(retrato["version"], "5.83.2")

    def test_defasada_nomeia_versao_e_idade_do_fetch(self) -> None:
        # O caso real: clone 5.83.2, remoto 5.89.0, FETCH_HEAD de 3 dias.
        root = _montar_store(registry="auto")
        agora = time.time()
        fetch_head = root / "marketplaces" / "prumo-marketplace" / ".git" / "FETCH_HEAD"
        os.utime(fetch_head, (agora - 3 * 86400, agora - 3 * 86400))
        retrato = store_clone.collect(store_root=root, remote_version="5.89.0", now=agora)
        self.assertEqual(retrato["status"], "defasada")
        self.assertEqual(retrato["remote_version"], "5.89.0")
        self.assertAlmostEqual(retrato["fetch_age_days"], 3.0, places=1)

    def test_sem_rede_e_indeterminada_nunca_fresca(self) -> None:
        # Sem comparação não há veredito — afirmar "em dia" sem olhar o
        # remoto é a classe de mentira que o preflight já mata (#215).
        root = _montar_store(registry="auto")
        retrato = store_clone.collect(store_root=root, remote_version=None)
        self.assertEqual(retrato["status"], "indeterminada")

    def test_sem_fetch_head_declara_idade_desconhecida(self) -> None:
        root = _montar_store(registry="auto")
        (root / "marketplaces" / "prumo-marketplace" / ".git" / "FETCH_HEAD").unlink()
        retrato = store_clone.collect(store_root=root, remote_version="5.89.0")
        self.assertIsNone(retrato["fetch_age_days"])
        self.assertEqual(retrato["status"], "defasada")

    def test_host_sem_store_e_ausente_sem_erro(self) -> None:
        # Host sem app/store (CI, VM) não é defeito — é ausência declarada.
        retrato = store_clone.collect(store_root=Path(tempfile.mkdtemp()), remote_version="1.0.0")
        self.assertFalse(retrato["found"])
        self.assertEqual(retrato["status"], "ausente")


class DoctorIntegracaoTest(unittest.TestCase):
    def _rodar(self, fmt: str, retrato: dict, remoto: str | None) -> str:
        stdout = io.StringIO()
        with mock.patch.object(doctor, "_fetch_remote", return_value=remoto):
            with mock.patch.object(doctor, "_collect_store", return_value=retrato):
                with contextlib.redirect_stdout(stdout):
                    rc = doctor.run_doctor(_args(format=fmt))
        self.assertEqual(rc, 0)
        return stdout.getvalue()

    def test_achado_sai_em_json_E_em_texto(self) -> None:
        # #275: alerta que só existe no JSON não conta.
        retrato = {
            "found": True, "path": "/x", "version": "5.83.2",
            "fetch_age_days": 3.0, "remote_version": "5.89.0", "status": "defasada",
        }
        payload = json.loads(self._rodar("json", retrato, "5.89.0"))
        self.assertEqual(payload["store_clone"]["status"], "defasada")
        texto = self._rodar("text", retrato, "5.89.0")
        self.assertIn("DEFASADA", texto)
        self.assertIn("5.89.0", texto)
        self.assertIn("re-sync", texto)

    def test_sem_rede_degrada_declarado(self) -> None:
        retrato = {
            "found": True, "path": "/x", "version": "5.83.2",
            "fetch_age_days": None, "remote_version": None, "status": "indeterminada",
        }
        texto = self._rodar("text", retrato, None)
        self.assertIn("sem rede", texto)

    def test_ida_ao_remoto_leva_cache_busting(self) -> None:
        # #291: o CDN mentiu duas vezes; a primeira ida já vai com ?cb=.
        with mock.patch.object(doctor, "fetch_remote_version", return_value="9.9.9") as fetch:
            with mock.patch.object(doctor, "_collect_store", return_value={"found": False, "status": "ausente"}):
                with contextlib.redirect_stdout(io.StringIO()):
                    doctor.run_doctor(_args(format="json"))
        url_usada = fetch.call_args.kwargs.get("url") or fetch.call_args.args[0]
        self.assertIn("?cb=", url_usada)


if __name__ == "__main__":
    unittest.main()
