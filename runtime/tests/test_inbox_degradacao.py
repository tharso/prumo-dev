"""O nó do Inbox4Mobile e o cache-busting do preflight (#289, #291).

No briefing de 30/07 o preview estava com índice de 25/07 contra arquivos de
30/07, e os 9 itens novos viraram UMA CONTAGEM — sem triagem, sem nomes.

Duas causas, e nenhuma delas era o fallback:

1. Dois donos discordando. `inbox-processing.md` mandava "apenas o link e a
   contagem"; `briefing-montagem.md` exigia "a contagem E a triagem". A frase
   de desarme morava no módulo OUTRO, sem contra-ponteiro — seguir o primeiro
   ao pé da letra produzia exatamente o comportamento reclamado.
2. Um ponteiro que nunca teria o gerador: mandava regenerar "pelos paths de
   `runtime-paths.md`", e o gerador vive dentro do pacote `prumo_runtime`.
   `Prumo/scripts/` não é populado por instalador nenhum.

A causa RAIZ do preview velho — ninguém regenera, porque a semente lê com
`allow_regen=False` — é da #290, não daqui. Aqui se garante que, com o
preview velho, o briefing degrada com honestidade em vez de emudecer.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULES = REPO_ROOT / "skills" / "prumo" / "references" / "modules"
INBOX = MODULES / "inbox-processing.md"
MONTAGEM = MODULES / "briefing-montagem.md"
RUNTIME_PATHS = MODULES / "runtime-paths.md"
PREFLIGHT = MODULES / "version-preflight.md"


def _read(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class DoisDonosTest(unittest.TestCase):
    """A contradição que licenciava entregar só um número."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.inbox = _read(INBOX)
        cls.montagem = _read(MONTAGEM)

    def test_inbox_nao_manda_mostrar_apenas_link_e_contagem(self) -> None:
        # A redação exata que, com preview stale, degenerava em contagem seca.
        # Variantes, não só a string exata: "apenas/só ... contagem" no
        # panorama é a FORMA do defeito, e reescrever com sinônimo não deixa
        # de ser o defeito (lição do guard de caixa exata na #284).
        import re

        padrao = re.compile(r"(apenas|só|somente)\s+(o\s+)?link e a contagem", re.I)
        self.assertIsNone(
            padrao.search(self.inbox),
            "voltou a formulação que fez os 9 itens de 30/07 virarem um número",
        )

    def test_inbox_aponta_o_dono_do_formato(self) -> None:
        # Sem contra-ponteiro, cada módulo dizia o seu e o agente escolhia.
        self.assertIn("o formato do panorama é do `briefing-montagem.md`", self.inbox)

    def test_montagem_continua_exigindo_contagem_E_triagem(self) -> None:
        # A outra ponta: se ela afrouxar, o ponteiro acima aponta pro vazio.
        self.assertIn("apresentar a contagem e a triagem", self.montagem.casefold())
        self.assertIn("itens de triagem numeram", self.montagem.casefold())


class PonteiroPenduradoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inbox = _read(INBOX)
        cls.paths = _read(RUNTIME_PATHS)

    def test_inbox_nao_manda_regenerar_por_path_de_script(self) -> None:
        # `runtime-paths.md` não lista o gerador, e não pode listar: ele vive
        # dentro do pacote. Mandar procurar é pior que declarar a limitação.
        self.assertNotIn(
            "usando os paths válidos definidos em `runtime-paths.md`",
            self.inbox,
            "o ponteiro pendurado voltou — manda procurar o que não existe",
        )

    def test_inbox_aponta_o_comando_e_declara_o_limite(self) -> None:
        self.assertIn("prumo inbox preview", self.inbox)
        self.assertIn("em host sem runtime não há como", self.inbox)

    def test_runtime_paths_declara_que_nao_e_destino_do_gerador(self) -> None:
        # Sem isto, o próximo módulo que precisar do preview aponta pra cá
        # de novo e o ciclo recomeça.
        self.assertIn("nenhum instalador o popula", self.paths)
        self.assertIn("aponta o COMANDO", self.paths)


class DegradacaoHonestaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inbox = _read(INBOX)

    def test_preview_velho_nao_suspende_a_triagem(self) -> None:
        self.assertIn("Preview velho ou ausente não suspende a triagem", self.inbox)

    def test_manda_dar_nomes_e_idade(self) -> None:
        # O que sustenta decisão: contagem sozinha não sustenta. E `mtime` no
        # inventário, senão "idade do mais antigo" seria pedido sem fonte.
        self.assertIn("com nome e `mtime`", self.inbox)
        self.assertIn("idade do item mais antigo", self.inbox)
        self.assertIn("idade está indisponível", self.inbox)

    def test_proibe_inventar_prioridade(self) -> None:
        # A degradação só é honesta se ela não fingir o que não tem. Sem esta
        # proibição, "classifique com o que houver" convida a chutar P1.
        self.assertIn("Nunca `P1/P2/P3` de arquivo que ninguém abriu", self.inbox)
        self.assertIn("prioridade sem evidência é chute", self.inbox)

    def test_o_passo_da_classificacao_nao_contradiz_a_degradacao(self) -> None:
        """A contradição que eu mesmo criei ao consertar a outra (Codex, r14).

        O passo 3 proibia inventar prioridade e o passo 5, duas linhas
        depois, exigia `P1/P2/P3` para CADA item novo — e no fallback todos
        são novos. É a mesma forma do bug original (o agente escolhe qual
        regra desobedecer), agora dentro de um arquivo só.
        """
        bruto = INBOX.read_text(encoding="utf-8")
        passo5 = bruto[bruto.index("5. **Para cada item novo**") :]
        passo5 = passo5[: passo5.index("### Estágio B")]

        # A exigência de P1/P2/P3 tem de estar SOB um ramo condicionado a
        # evidência, e o outro ramo tem de existir com a saída alternativa.
        self.assertIn("**Com evidência**", passo5)
        self.assertIn("**Sem evidência**", passo5)
        self.assertLess(
            passo5.index("**Com evidência**"),
            passo5.index("`P1`, `P2`, `P3`"),
            "a exigência de prioridade voltou a valer incondicionalmente",
        )
        self.assertIn("`não determinada`", passo5)

    def test_evidencia_e_do_item_nao_frescor_da_fonte(self) -> None:
        """Índice fresco não é evidência (Codex, r15).

        O índice guarda `filename`, `kind`, `size_bytes`, `mtime_iso`,
        `fingerprint` e `first_url` — metadata, nada de conteúdo. Isso não
        sustenta `P1` para um `IMG_1234.jpg`. Pior: `load_inbox_preview`
        declara `gerado` comparando o mtime do índice com o dos arquivos, sem
        conferir se o `inbox-preview.html` existe — então "fresco" convivia
        com "preview ausente" e produzia prioridade cenográfica.
        """
        self.assertIn("evidência material do ITEM", self.inbox)
        self.assertIn("Metadata", self.inbox)
        self.assertIn("não é evidência", self.inbox)
        self.assertIn("não confere se o `inbox-preview.html` existe", self.inbox)

        # O ramo de cima não pode convidar por NENHUMA forma de metadata.
        # O guard estreito pegava só "índice fresco" e deixava `first_url`,
        # "status gerado" e "índice atualizado" entrarem pela janela.
        bruto = INBOX.read_text(encoding="utf-8")
        com = bruto[bruto.index("**Com evidência**") :]
        com = com[: com.index("**Sem evidência**")]
        for isca in ("índice fresco", "índice atualizado", "first_url", "gerado", "mtime"):
            self.assertNotIn(isca, com, f"'{isca}' voltou a valer como evidência")

    def test_url_sozinha_nao_e_evidencia(self) -> None:
        # `first_url` vem do PRÓPRIO índice: aceitá-la reintroduzia metadata
        # pela janela. Um link de YouTube identifica a fonte, não a urgência.
        self.assertIn("URL sozinha identifica a FONTE", self.inbox)
        self.assertIn("sustenta os três campos", self.inbox)

    def test_link_do_preview_depende_do_HTML_nao_do_indice(self) -> None:
        # O predicado era a existência do ÍNDICE, e o índice pode estar
        # fresco com o HTML ausente — mandava linkar um fantasma. O ASSERT do
        # core tinha o mesmo defeito; consertar só o módulo criaria
        # discordância nova, que é o bug que esta issue conserta.
        core = " ".join(
            (REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md")
            .read_text(encoding="utf-8")
            .split()
        )
        self.assertIn(
            "Se existir Prumo/Inbox4Mobile/inbox-preview.html utilizável, linkar",
            core,
        )
        self.assertNotIn("_preview-index.json, linkar", core)
        self.assertIn("só se ele existir e estiver utilizável", self.inbox)

    def test_fallback_continua_entregando_triagem_numerada(self) -> None:
        # Degradar a certeza é legítimo; degradar a ENTREGA é o defeito de
        # 30/07. O texto tem de dizer qual das duas cede.
        self.assertIn("degrada a certeza, nunca a entrega", self.inbox)

    def test_lembra_que_o_ASSERT_proibe_o_bruto_nao_a_classificacao(self) -> None:
        # O relatório de 30/07 propôs abrir exceção no ASSERT. Não decorre
        # dos fatos — e o texto agora diz por quê, no lugar onde a dúvida nasce.
        self.assertIn("classificar por nome sempre foi permitido", self.inbox)


class CacheBustingTest(unittest.TestCase):
    """#291: a primeira ida também merece query nova."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.preflight = _read(PREFLIGHT)

    def test_caminho_sem_runtime_busta_na_primeira_ida(self) -> None:
        self.assertIn("com `?cb=<timestamp>` **já na primeira ida**", self.preflight)

    def test_caminho_com_runtime_nao_mudou(self) -> None:
        # Lá quem faz a rede é o CLI, com cache de 24h; o agente não tem onde
        # enfiar query string, e forçar rede a cada briefing seria regressão.
        self.assertIn("rodar `prumo version-check --ensure-fresh`", self.preflight)
        self.assertIn("busca a rede **no máximo 1x/24h**", self.preflight)

    def test_protocolo_215_intacto(self) -> None:
        # A mudança acrescenta condição na bifurcação; não reescreve o
        # protocolo, que segue dono da regra do remoto suspeito.
        for ancora in (
            "resposta SUSPEITA (#215)",
            "re-tentar UMA vez com **cache-busting**",
            "**declarar status desconhecido** em uma linha",
            '**nunca** ler "remoto menor" como "estou em dia"',
        ):
            self.assertIn(ancora, self.preflight, f"âncora do #215 sumiu: {ancora}")

    def test_ordem_por_host_intacta(self) -> None:
        self.assertIn("em Cowork/host containerizado, **WebFetch PRIMEIRO**", self.preflight)
        self.assertIn('"não consegui checar" só depois de esgotar os dois', self.preflight)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
