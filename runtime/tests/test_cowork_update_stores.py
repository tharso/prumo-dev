"""O update do Cowork enxerga a store ATIVA, não só a legada (#276).

O defeito: `collect_roots` procurava por diretórios chamados `cowork_plugins`,
que é o arranjo legado (≤março/2026). A store do Cowork atual é
`~/.claude/plugins/` e não tem nenhum diretório com esse nome — então ela era
estruturalmente invisível.

Pior que não funcionar: o script **reportava sucesso**. Atualizava a legada,
imprimia "marketplace alinhado", e quem lia concluía que o problema tinha
sido resolvido. O checkout que importa continuava parado — e o `doctor`
recomendava esse script como primeira ação para o diagnóstico que ele acabara
de fazer.

O cabeçalho culpava a camada ("alcança só checkouts git locais, camada 3"),
mas a store unificada TAMBÉM é checkout git local: tem `.git`, remoto e HEAD
rastreável. A limitação nunca foi de camada, era de padrão de busca.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "prumo_cowork_update.sh"

KNOWN = {"prumo-marketplace": {"lastUpdated": "2020-01-01T00:00:00Z"}}


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _remoto(base: Path) -> Path:
    """Um marketplace remoto de mentira, com um VERSION.

    `-b main` e o `symbolic-ref` explícito NÃO são zelo: sem eles o bare
    nasce com HEAD apontando para o `init.defaultBranch` de quem roda. Se for
    `master` — o default dos runners — o clone sai com HEAD não-nascido e o
    `rev-parse HEAD` falha com "ambiguous argument". Passava na minha máquina
    e quebrava no CI, que é exatamente para isso que o CI existe.
    """
    remoto = base / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remoto)], check=True)
    origem = base / "origem"
    origem.mkdir()
    _git("init", "-q", cwd=origem)
    _git("config", "user.email", "t@t", cwd=origem)
    _git("config", "user.name", "t", cwd=origem)
    (origem / "VERSION").write_text("9.9.9\n")
    _git("add", "-A", cwd=origem)
    _git("commit", "-qm", "v1", cwd=origem)
    _git("branch", "-M", "main", cwd=origem)
    _git("remote", "add", "origin", str(remoto), cwd=origem)
    _git("push", "-q", "origin", "main", cwd=origem)
    # Garante o HEAD do bare mesmo em git antigo, que não o move no primeiro push.
    subprocess.run(
        ["git", "--git-dir", str(remoto), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True, capture_output=True,
    )
    return remoto


def _clone(remoto: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "-q", str(remoto), str(destino)], check=True, capture_output=True
    )


class StoreDiscoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)  # mkdtemp sem limpeza vaza a cada run
        self.base = Path(tmp.name)
        self.remoto = _remoto(self.base)

    def _unificada(self) -> Path:
        """Topologia atual: ~/.claude/plugins/ — sem `cowork_plugins` nenhum."""
        raiz = self.base / "uni"
        _clone(self.remoto, raiz / "marketplaces" / "prumo-marketplace")
        (raiz / "known_marketplaces.json").write_text(json.dumps(KNOWN))
        (raiz / "installed_plugins.json").write_text(
            json.dumps(
                {"plugins": {"prumo@prumo-marketplace": [{"version": "1.0.0"}]}}
            )
        )
        return raiz

    def _legada(self) -> Path:
        """Arranjo ≤março/2026: diretório `cowork_plugins` dentro das sessões."""
        sessoes = self.base / "leg" / "sess"
        store = sessoes / "abc" / "cowork_plugins"
        _clone(self.remoto, store / "marketplaces" / "prumo-marketplace")
        (store / "known_marketplaces.json").write_text(json.dumps(KNOWN))
        return sessoes

    def _rodar(self, plugins_root: Path, sessions_root: Path):
        r = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--plugins-root",
                str(plugins_root),
                "--sessions-root",
                str(sessions_root),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        try:
            return r.returncode, json.loads(r.stdout)
        except json.JSONDecodeError:
            self.fail(f"saída não-JSON (rc={r.returncode}): {r.stdout[:300]} {r.stderr[:300]}")

    def test_a_store_unificada_e_alcancada(self) -> None:
        # O critério central da #276: ela não tem `cowork_plugins` no caminho.
        uni = self._unificada()
        code, payload = self._rodar(uni, self.base / "sem-sessoes")
        self.assertEqual(code, 0)
        self.assertTrue(payload["active_store_reached"])
        self.assertEqual([r["kind"] for r in payload["results"]], ["ativa"])
        self.assertEqual(payload["results"][0]["after_version"], "9.9.9")

    def test_ativa_vem_antes_da_legada(self) -> None:
        # Ordem importa no relatório em texto: quem lê a primeira linha tem de
        # ler sobre a store que decide o comportamento.
        code, payload = self._rodar(self._unificada(), self._legada())
        self.assertEqual(code, 0)
        self.assertEqual([r["kind"] for r in payload["results"]], ["ativa", "legada"])

    def test_so_legada_nao_e_sucesso(self) -> None:
        """O coração do defeito: atualizar a legada e dizer 'alinhado'."""
        code, payload = self._rodar(self.base / "nao-existe", self._legada())
        self.assertEqual(code, 3, "só-legada continua saindo zero — o sucesso mente")
        self.assertFalse(payload["active_store_reached"])
        self.assertEqual(payload["status"], "so_legada")
        self.assertEqual([r["kind"] for r in payload["results"]], ["legada"])

    def test_legada_e_atualizada_mesmo_assim(self) -> None:
        # Não deixar de fazer o trabalho: ela continua sendo atualizada. O que
        # muda é o relatório parar de vender isso como solução.
        _, payload = self._rodar(self.base / "nao-existe", self._legada())
        self.assertEqual(payload["results"][0]["after_version"], "9.9.9")

    def test_texto_declara_a_natureza_de_cada_store(self) -> None:
        r = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--plugins-root",
                str(self.base / "nao-existe"),
                "--sessions-root",
                str(self._legada()),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        saida = r.stdout
        self.assertIn("LEGADA", saida)
        self.assertIn("não resolve o Cowork atual", saida.replace("NÃO", "não"))
        self.assertIn("a store ATIVA (unificada) não foi encontrada", saida)
        # E aponta o reparo real da camada 5, em vez de deixar o leitor achando
        # que o trabalho acabou.
        self.assertIn("re-adicionar como owner/repo", saida)

    def test_sem_store_nenhuma_sai_diferente_de_zero(self) -> None:
        r = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--plugins-root",
                str(self.base / "nada"),
                "--sessions-root",
                str(self.base / "nada2"),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertNotEqual(r.returncode, 0)


class AlcancarNaoEAtualizarTest(unittest.TestCase):
    """A segunda camada da mesma mentira (Codex, r22).

    A primeira versão do conserto perguntava só se a store ativa APARECEU.
    Store ativa com checkout ausente, ou com `git fetch` que falhou, seguia
    saindo zero — o mesmo "sucesso" que a issue existe para remover, um passo
    adiante.
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def test_ativa_sem_checkout_nao_e_sucesso(self) -> None:
        quebrada = self.base / "quebrada"
        (quebrada / "marketplaces").mkdir(parents=True)
        (quebrada / "known_marketplaces.json").write_text(json.dumps(KNOWN))

        r = subprocess.run(
            [
                "bash", str(SCRIPT),
                "--plugins-root", str(quebrada),
                "--sessions-root", str(self.base / "nada"),
                "--json",
            ],
            capture_output=True, text=True, timeout=120,
        )
        payload = json.loads(r.stdout)
        self.assertEqual(r.returncode, 4)
        self.assertEqual(payload["status"], "ativa_falhou")
        self.assertTrue(payload["active_store_reached"])
        self.assertFalse(payload["active_store_updated"], "achar não é atualizar")

    def test_contagem_nao_conta_fracasso_como_atualizacao(self) -> None:
        quebrada = self.base / "quebrada2"
        (quebrada / "marketplaces").mkdir(parents=True)
        (quebrada / "known_marketplaces.json").write_text(json.dumps(KNOWN))
        r = subprocess.run(
            [
                "bash", str(SCRIPT),
                "--plugins-root", str(quebrada),
                "--sessions-root", str(self.base / "nada"),
                "--json",
            ],
            capture_output=True, text=True, timeout=120,
        )
        payload = json.loads(r.stdout)
        self.assertEqual(payload["stores_found"], 1)
        self.assertEqual(payload["stores_updated"], 0, "tentativa fracassada contada como update")


class DryRunHonestoTest(unittest.TestCase):
    """O dry-run não pode ganhar diploma por não comparecer à aula (Codex, r23).

    `error is None` num dry-run significa "nada deu errado porque nada foi
    tentado". Sem distinguir, ele saía com `active_store_updated: true`,
    `stores_updated: 1` e veredito "store ATIVA atualizada" — certificando
    uma atualização que não aconteceu.
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.remoto = _remoto(self.base)
        self.uni = self.base / "uni"
        _clone(self.remoto, self.uni / "marketplaces" / "prumo-marketplace")
        (self.uni / "known_marketplaces.json").write_text(json.dumps(KNOWN))

    def _dry(self):
        r = subprocess.run(
            [
                "bash", str(SCRIPT),
                "--plugins-root", str(self.uni),
                "--sessions-root", str(self.base / "nada"),
                "--dry-run", "--json",
            ],
            capture_output=True, text=True, timeout=120,
        )
        return r.returncode, json.loads(r.stdout)

    def test_dry_run_nao_declara_atualizacao(self) -> None:
        code, payload = self._dry()
        self.assertEqual(code, 0, "simulação bem-sucedida não é erro")
        self.assertEqual(payload["status"], "simulacao")
        self.assertFalse(payload["active_store_updated"])
        self.assertEqual(payload["stores_updated"], 0)

    def test_veredito_do_dry_run_diz_que_nada_foi_escrito(self) -> None:
        _, payload = self._dry()
        self.assertIn("SIMULAÇÃO", payload["verdict"])
        self.assertIn("nada foi escrito", payload["verdict"])


class InspecaoQuebradaTest(unittest.TestCase):
    """O contrato dos estados vale mesmo quando a leitura falha.

    JSON malformado ou `.git` corrompido estourava ANTES do `try` e derrubava
    o script com traceback e rc 1 — sem JSON válido e sem veredito. Contrato
    que só vale quando nada dá errado não é contrato (Codex, r23).
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def _rodar(self, store: Path):
        r = subprocess.run(
            [
                "bash", str(SCRIPT),
                "--plugins-root", str(store),
                "--sessions-root", str(self.base / "nada"),
                "--json",
            ],
            capture_output=True, text=True, timeout=120,
        )
        try:
            return r.returncode, json.loads(r.stdout)
        except json.JSONDecodeError:
            self.fail(f"não emitiu JSON (rc={r.returncode}): {r.stdout[:200]} {r.stderr[:300]}")

    def test_installed_plugins_malformado_vira_veredito(self) -> None:
        store = self.base / "ruim"
        (store / "marketplaces").mkdir(parents=True)
        (store / "known_marketplaces.json").write_text(json.dumps(KNOWN))
        (store / "installed_plugins.json").write_text("NAO E JSON")
        code, payload = self._rodar(store)
        self.assertEqual(code, 4)
        self.assertEqual(payload["status"], "ativa_falhou")
        self.assertIn("inspeção do store falhou", payload["results"][0]["error"])

    def test_known_marketplaces_malformado_vira_veredito(self) -> None:
        store = self.base / "ruim2"
        (store / "marketplaces").mkdir(parents=True)
        (store / "known_marketplaces.json").write_text("{{{")
        code, payload = self._rodar(store)
        self.assertEqual(code, 4)
        self.assertEqual(payload["status"], "ativa_falhou")

    def test_git_corrompido_vira_veredito(self) -> None:
        store = self.base / "ruim3"
        checkout = store / "marketplaces" / "prumo-marketplace"
        (checkout / ".git").mkdir(parents=True)
        (checkout / ".git" / "HEAD").write_text("lixo")
        (store / "known_marketplaces.json").write_text(json.dumps(KNOWN))
        code, payload = self._rodar(store)
        self.assertEqual(code, 4)
        self.assertIsNotNone(payload["results"][0]["error"])


class DryRunNaoPrometeAtualizabilidadeTest(unittest.TestCase):
    """A promessa que a simulação não testa (Codex, r24).

    "Seria atualizável" prometia o que a simulação não testa (Codex, r24).

    O dry-run pula `fetch`, `checkout` e `pull` — então remoto inacessível,
    branch inexistente, checkout sujo e commits locais passariam como 0.
    Provar de verdade exigiria escrever referências, que é justamente o que
    um dry-run não faz. O veredito honesto é "checkout local acessível;
    atualização NÃO testada".
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.remoto = _remoto(self.base)

    def _uni(self) -> Path:
        uni = self.base / "uni"
        _clone(self.remoto, uni / "marketplaces" / "prumo-marketplace")
        (uni / "known_marketplaces.json").write_text(json.dumps(KNOWN))
        return uni

    def _legada(self) -> Path:
        sess = self.base / "leg" / "sess"
        store = sess / "abc" / "cowork_plugins"
        _clone(self.remoto, store / "marketplaces" / "prumo-marketplace")
        (store / "known_marketplaces.json").write_text(json.dumps(KNOWN))
        return sess

    def _rodar(self, plugins_root: Path, sessions_root: Path, json_out: bool):
        cmd = [
            "bash", str(SCRIPT),
            "--plugins-root", str(plugins_root),
            "--sessions-root", str(sessions_root),
            "--dry-run",
        ] + (["--json"] if json_out else [])
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    def test_veredito_nao_promete_atualizabilidade(self) -> None:
        r = self._rodar(self._uni(), self.base / "nada", True)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["status"], "simulacao")
        self.assertIn("NÃO testada", payload["verdict"])
        self.assertNotIn("seria atualizável", payload["verdict"])

    def test_nenhuma_linha_do_texto_diz_alinhado(self) -> None:
        # O ramo por store dizia "marketplace alinhado" mesmo no dry-run.
        r = self._rodar(self._uni(), self.base / "nada", False)
        self.assertIn("SIMULAÇÃO", r.stdout)
        self.assertNotIn("alinhado", r.stdout)
        self.assertNotIn("catálogo foi atualizado", r.stdout)

    def test_dry_run_sem_ativa_e_so_legada_nao_ativa_falhou(self) -> None:
        # O ramo da simulação vinha ANTES de `not tem_ativa`, então um
        # dry-run sem store ativa virava `ativa_falhou` — contradizendo o
        # contrato: ativa ausente é `so_legada` em qualquer modo.
        r = self._rodar(self.base / "nao-existe", self._legada(), True)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["status"], "so_legada")
        self.assertEqual(r.returncode, 3)
        self.assertIn("nada foi escrito", payload["verdict"])


class VereditoBaseadoNoResultadoTest(unittest.TestCase):
    """O veredito de `so_legada` não pode narrar o que não aconteceu.

    Ele afirmava "só atualizei store LEGADA" sem consultar os erros das
    legadas — com checkout ausente ou git falhando, prometia atualização
    sobre uma store que também não tinha sido atualizada (Codex, r25).
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def test_legada_quebrada_nao_recebe_recibo_de_atualizacao(self) -> None:
        sess = self.base / "sess"
        store = sess / "abc" / "cowork_plugins"
        (store / "marketplaces").mkdir(parents=True)
        (store / "known_marketplaces.json").write_text(json.dumps(KNOWN))

        r = subprocess.run(
            [
                "bash", str(SCRIPT),
                "--plugins-root", str(self.base / "nao-existe"),
                "--sessions-root", str(sess),
                "--json",
            ],
            capture_output=True, text=True, timeout=120,
        )
        payload = json.loads(r.stdout)
        self.assertEqual(payload["status"], "so_legada")
        self.assertEqual(payload["stores_updated"], 0)
        self.assertIn("0 atualizada(s), 1 com erro", payload["verdict"])
        self.assertNotIn("só atualizei store LEGADA", payload["verdict"])


class RevParsePosOperacaoTest(unittest.TestCase):
    """`check=False` fazia o rev-parse falhar ABERTO (Codex, r25).

    Retorno não-zero não levantava: `after_head` virava None, `error` ficava
    vazio e a store ATIVA saía certificada como `ok`. Um shim de `git` que
    falha só no segundo `rev-parse` prova o caminho.
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def test_rev_parse_que_falha_depois_do_update_nao_vira_ok(self) -> None:
        remoto = _remoto(self.base)
        uni = self.base / "uni"
        _clone(remoto, uni / "marketplaces" / "prumo-marketplace")
        (uni / "known_marketplaces.json").write_text(json.dumps(KNOWN))

        # Shim: o SEGUNDO `rev-parse` (o pós-operação) falha.
        bin_dir = self.base / "bin"
        bin_dir.mkdir()
        contador = self.base / "n"
        shim = bin_dir / "git"
        corpo = "\n".join(
            [
                "#!/usr/bin/env bash",
                'if [ "$1" = "rev-parse" ] || [ "$2" = "rev-parse" ]; then',
                f'  n=$(cat "{contador}" 2>/dev/null || echo 0)',
                f'  echo $((n+1)) > "{contador}"',
                '  if [ "$n" -ge 1 ]; then echo "shim: rev-parse quebrado" >&2; exit 128; fi',
                "fi",
                'exec /usr/bin/git "$@"',
                "",
            ]
        )
        shim.write_text(corpo)
        shim.chmod(0o755)

        import os

        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
        r = subprocess.run(
            [
                "bash", str(SCRIPT),
                "--plugins-root", str(uni),
                "--sessions-root", str(self.base / "nada"),
                "--json",
            ],
            capture_output=True, text=True, timeout=120, env=env,
        )
        payload = json.loads(r.stdout)
        self.assertNotEqual(
            payload["status"], "ok", "git falhando saiu certificado como sucesso"
        )
        self.assertFalse(payload["active_store_updated"])


class ParidadeTextoJsonTest(unittest.TestCase):
    """Texto e JSON não podem discordar sobre o que aconteceu (Codex, r22).

    Antes: sem store nenhuma, o texto saía 1 e o JSON saía 3 — porque o JSON
    retornava antes de chegar no ramo do texto. Dois formatos, dois vereditos.
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def _codigos(self, plugins_root: Path, sessions_root: Path):
        base_cmd = [
            "bash", str(SCRIPT),
            "--plugins-root", str(plugins_root),
            "--sessions-root", str(sessions_root),
        ]
        texto = subprocess.run(base_cmd, capture_output=True, text=True, timeout=120)
        js = subprocess.run(base_cmd + ["--json"], capture_output=True, text=True, timeout=120)
        return texto.returncode, js.returncode, json.loads(js.stdout) if js.stdout.strip() else {}

    def test_sem_store_nenhuma_concorda(self) -> None:
        ct, cj, payload = self._codigos(self.base / "a", self.base / "b")
        self.assertEqual(ct, cj)
        self.assertEqual(ct, 1)
        self.assertEqual(payload.get("status"), "sem_store")

    def test_json_carrega_o_veredito_em_texto(self) -> None:
        # O JSON não oferecia o reparo da camada 5 que o texto oferecia:
        # quem automatiza ficava sem a instrução que o humano recebia.
        _, _, payload = self._codigos(self.base / "a", self.base / "b")
        self.assertIn("verdict", payload)
        self.assertTrue(payload["verdict"])


class ContratoDoCabecalhoTest(unittest.TestCase):
    """O texto do script precisa parar de culpar a camada errada."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fonte = SCRIPT.read_text(encoding="utf-8")

    def test_documenta_a_flag_da_store_ativa(self) -> None:
        self.assertIn("--plugins-root", self.fonte)

    def test_explica_por_que_a_unificada_era_invisivel(self) -> None:
        # Sem isso, o próximo a ler `rglob("cowork_plugins")` acha que é
        # limitação de camada, que era o que o cabeçalho dizia.
        self.assertIn("era de padrão de busca", self.fonte)

    def test_nao_procura_mais_so_por_cowork_plugins(self) -> None:
        # A busca legada continua existindo — o que não pode é ser a única.
        self.assertIn("_e_store", self.fonte)
        self.assertIn("plugins_base", self.fonte)


class DoctorEUpdateConcordamTest(unittest.TestCase):
    """Critério 6 da #276: o doctor sabia e o script não.

    O doctor já listava `~/.claude/plugins` em `EXTRA_ROOTS` e classificava as
    outras como legado morto. O update procurava só `cowork_plugins`. Duas
    ferramentas do mesmo produto discordando sobre qual store decide o
    comportamento é como o painel recomendar o que a ferramenta não executa
    (#268) — e foi assim que o doctor prescreveu, como primeira ação, um
    script que não alcançava o que ele acabara de diagnosticar.
    """

    def test_ambos_reconhecem_a_store_unificada(self) -> None:
        doctor = (REPO_ROOT / "scripts" / "prumo_cowork_doctor.sh").read_text(
            encoding="utf-8"
        )
        update = SCRIPT.read_text(encoding="utf-8")
        for fonte, nome in ((doctor, "doctor"), (update, "update")):
            self.assertIn(
                ".claude/plugins",
                fonte,
                f"{nome} deixou de conhecer a store unificada",
            )

    def test_ambos_tratam_cowork_plugins_como_legado(self) -> None:
        doctor = (REPO_ROOT / "scripts" / "prumo_cowork_doctor.sh").read_text(
            encoding="utf-8"
        )
        update = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("LEGADO", doctor.upper())
        self.assertIn("legada", update)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
