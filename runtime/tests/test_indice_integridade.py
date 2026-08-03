"""Integridade do `Referencias/INDICE.md` (#261).

A diferença de conjuntos que a faxina §3 já fazia mandava ADICIONAR o que
faltava, sem teto e em silêncio. Depois do truncamento de 27/07 (48 entradas
viraram 5), qualquer briefing dos dois dias seguintes teria reinserido 37
fichas com IDs novos e reportado sucesso.

Os testes exercitam o CAMINHO PRODUTIVO (o bloco da semente), não só o helper:
cálculo que apenas os testes chamam prova um modelo paralelo, não o produto
(Codex, 261-7). As fronteiras têm negativa porque guard que não reprova o que
proíbe é decoração.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from prumo_runtime import faxina_thresholds, indice_integridade
from prumo_runtime.local_panorama import build_local_panorama

GAP = faxina_thresholds.DEFAULTS["referencias_id_gap_alert_pct"]
BULK = faxina_thresholds.DEFAULTS["referencias_bulk_reindex_at"]


def _tabela(ids, arquivo=lambda n: f"Autor_Ficha-{n}_2026-01-01.md") -> str:
    linhas = "".join(
        f"| {n} | Ficha {n} | {arquivo(n)} | 01/02/2026 | descrição autoral | tag |\n"
        for n in ids
    )
    return "# Índice\n\n| # | Título | Arquivo | Data | Descrição | Keywords |\n|---|---|---|---|---|---|\n" + linhas


class BaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "Referencias"
        self.root.mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def indice(self) -> Path:
        return self.root / "INDICE.md"

    def escrever(self, texto: str) -> None:
        self.indice().write_text(texto, encoding="utf-8")

    def escrever_coerente(self, ids, extra: str = "") -> None:
        """Tabela + as fichas que ela declara. Sem isto, toda linha viraria
        entrada órfã e a decisão nunca seria `ok` — o check de órfã é novo
        (Codex, r5)."""
        self.escrever(_tabela(ids) + extra)
        self.fichas(ids)

    def fichas(self, ids) -> None:
        for n in ids:
            (self.root / f"Autor_Ficha-{n}_2026-01-01.md").write_text(f"# Ficha {n}\n", encoding="utf-8")

    def avaliar(self, **kw) -> dict:
        return indice_integridade.avaliar(
            self.root,
            self.indice(),
            gap_alert_pct=kw.get("gap", GAP),
            bulk_reindex_at=kw.get("bulk", BULK),
        )


class PavioTest(BaseTest):
    """`slots = N-1`; ocupados = IDs distintos em 1..slots. ID >= N não
    preenche lacuna (rodapé é sugestão e pode estar atrasado, #244)."""

    def test_o_caso_real_do_dono_nao_alarma(self) -> None:
        """11 buracos em 48 = 22,9%. Buraco de ID é a REGRA, não a exceção."""
        presentes = [n for n in range(1, 49) if n not in
                     {1, 2, 10, 13, 15, 22, 27, 28, 29, 30, 31}]
        self.escrever(_tabela(presentes) + "\n<!-- proximo-id: 49 -->\n")
        self.fichas(presentes)

        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 23)
        self.assertEqual(r["decisao"], indice_integridade.OK)

    def test_o_truncamento_real_bloqueia(self) -> None:
        """48 entradas viram 4: 91,7% de lacuna."""
        self.escrever_coerente([45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n")
        self.fichas(range(1, 49))

        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 92)
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)

    def test_fronteira_abaixo_do_limiar(self) -> None:
        """49,x% não dispara — o limiar é `>=`."""
        self.escrever_coerente(range(1, 51), "\n<!-- proximo-id: 100 -->\n")
        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 49)
        self.assertEqual(r["decisao"], indice_integridade.OK)

    def test_fronteira_no_limiar(self) -> None:
        self.escrever_coerente(range(1, 50), "\n<!-- proximo-id: 99 -->\n")
        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 50)
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)

    def test_sem_rodape_pavio_indisponivel(self) -> None:
        """Negativa: workspace legado não tem rodapé, e ausência NUNCA é
        alarme por si."""
        self.escrever_coerente([1, 2, 3])
        r = self.avaliar()
        self.assertIsNone(r["lacunas_pct"])
        self.assertEqual(r["decisao"], indice_integridade.OK)

    def test_rodape_malformado_nao_alarma(self) -> None:
        self.escrever_coerente([1, 2, 3], "\n<!-- proximo-id: abacaxi -->\n")
        self.assertIsNone(self.avaliar()["lacunas_pct"])

    def test_rodape_atrasado_nao_conta_id_acima(self) -> None:
        """IDs >= N não preenchem lacuna: o rodapé é sugestão (#244). Com
        rodapé 3 e IDs 1,2,50, os slots são {1,2} e estão cheios."""
        self.escrever_coerente([1, 2, 50], "\n<!-- proximo-id: 3 -->\n")
        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 0)

    def test_id_duplicado_conta_uma_vez(self) -> None:
        self.escrever_coerente([1, 1, 2], "\n<!-- proximo-id: 4 -->\n")
        # slots = 3, ocupados = {1,2} → 1 lacuna em 3
        self.assertEqual(self.avaliar()["lacunas_pct"], 33)

    def test_rodape_um_nao_tem_intervalo(self) -> None:
        self.escrever("# Índice\n\n<!-- proximo-id: 1 -->\n")
        self.assertIsNone(self.avaliar()["lacunas_pct"])


class VolumeTest(BaseTest):
    def test_uma_ficha_sem_entrada_reindexa(self) -> None:
        self.escrever(_tabela([1, 2]) + "\n<!-- proximo-id: 3 -->\n")
        self.fichas([1, 2, 3])
        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.REINDEXAR)
        self.assertEqual(r["sem_entrada"], ["Autor_Ficha-3_2026-01-01.md"])

    def test_lote_no_limiar_bloqueia(self) -> None:
        """`>= referencias_bulk_reindex_at`, não `>`."""
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas(range(1, 1 + BULK + 1))
        r = self.avaliar()
        self.assertEqual(len(r["sem_entrada"]), BULK)
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)

    def test_lote_abaixo_do_limiar_reindexa(self) -> None:
        """Negativa: crescimento normal não pode virar fricção."""
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas(range(1, 1 + BULK))
        r = self.avaliar()
        self.assertEqual(len(r["sem_entrada"]), BULK - 1)
        self.assertEqual(r["decisao"], indice_integridade.REINDEXAR)

    def test_fora_da_convencao_nao_aciona_mas_e_nomeado(self) -> None:
        """Operacionais e os 4 casos reais do incidente de 03/08 (#305) nunca
        acionam reindexação — mas ficam NOMEADOS em `fora_convencao` (Codex,
        314-r1: invisibilidade total deixaria truncamento de legado passar
        limpo). Ocultos e rascunhos não aparecem em conta nenhuma."""
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas([1])
        visiveis = [
            "CONTEXT-EFFICIENCY-AUDIT.md",
            "Frila-StripePartners-GHz-due-diligence-2026-07-04.md",
            "REUNIOES-INDEX.md",
            "WORKFLOWS-GRANOLA.md",
        ]
        infra_e_ocultos = ["WORKFLOWS.md", "EMAIL-CURADORIA.md", "_rascunho.md", ".oculto.md"]
        for nome in visiveis + infra_e_ocultos:
            (self.root / nome).write_text("x", encoding="utf-8")
        r = self.avaliar()
        self.assertEqual(r["sem_entrada"], [])
        self.assertEqual(r["fora_convencao"], sorted(visiveis))
        self.assertEqual(r["decisao"], indice_integridade.OK)

    def test_legado_truncado_nao_passa_limpo(self) -> None:
        """Cenário do Codex (314-r1): referência legada fora da convenção que
        perde a linha da tabela precisa aparecer nomeada no relato — e a marca
        `fichas-fora-conferidas` (mecanismo da #261) a despacha por nome."""
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas([1])
        (self.root / "research-notes.md").write_text("x", encoding="utf-8")
        r = self.avaliar()
        self.assertIn("research-notes.md", r["fora_convencao"])
        self.assertIn("research-notes.md", indice_integridade.render(r))
        self.escrever(
            _tabela([1])
            + "\n<!-- proximo-id: 2 -->\n"
            + "<!-- fichas-fora-conferidas: research-notes.md -->\n"
        )
        r2 = self.avaliar()
        self.assertEqual(r2["fora_convencao"], [])


class ArvoreUnicaTest(BaseTest):
    """E1 e E2 disparam no MESMO estado quando o índice é truncado. Como
    guards independentes dariam duas sirenes pro mesmo incêndio, a árvore é
    exclusiva e o volume entra como EVIDÊNCIA (Codex, 261-5)."""

    def test_truncamento_da_um_alerta_so(self) -> None:
        self.escrever_coerente([45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n")
        self.fichas(range(1, 49))

        r = self.avaliar()
        texto = indice_integridade.render(r)
        self.assertEqual(texto.count("Índice"), 1, f"duas sirenes: {texto}")
        self.assertIn("% dos IDs", texto)
        self.assertIn("ficha(s) em disco fora do índice", texto)
        self.assertNotIn("reindexar e nomear", texto)

    def test_bloqueio_por_volume_sem_pavio(self) -> None:
        """Sem rodapé o E1 é pulado, mas o E2 continua valendo."""
        self.escrever(_tabela([1]))
        self.fichas(range(1, 1 + BULK + 1))
        r = self.avaliar()
        self.assertIsNone(r["lacunas_pct"])
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)

    def test_reindexar_nomeia_os_arquivos(self) -> None:
        """Perda de UMA linha é indistinguível de ficha nova por diferença de
        conjuntos — mas trivial pro usuário, que é o único que sabe que aquilo
        é de fevereiro. Por isso nomear, não só contar."""
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas([1, 2])
        texto = indice_integridade.render(self.avaliar())
        self.assertIn("Autor_Ficha-2_2026-01-01.md", texto)

    def test_casa_em_ordem_e_silencio(self) -> None:
        self.escrever_coerente([1, 2], "\n<!-- proximo-id: 3 -->\n")
        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.OK)
        self.assertEqual(indice_integridade.render(r), "")

    def test_indice_ilegivel_bloqueia(self) -> None:
        self.indice().write_bytes(b"\xff\xfe nao sou utf-8")
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.BLOQUEAR)


class SementeTest(BaseTest):
    """O caminho PRODUTIVO: a decisão viaja na semente. Testar só o helper
    provaria um modelo paralelo (Codex, 261-7)."""

    def _panorama(self) -> dict:
        panorama, _ = build_local_panorama(
            pauta_path=self.root.parent / "PAUTA.md",
            inbox_path=self.root.parent / "INBOX.md",
            registro_path=self.root.parent / "REGISTRO.md",
            processed_path=self.root.parent / "_processed.json",
            preview={},
            today=date(2026, 7, 29),
            thresholds=faxina_thresholds.effective(self.root.parent),
            referencias_root=self.root,
            indice_path=self.indice(),
        )
        return panorama

    def test_semente_transporta_a_decisao(self) -> None:
        self.escrever_coerente([45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n")
        self.fichas(range(1, 49))

        bloco = self._panorama()["indice_referencias"]
        self.assertEqual(bloco["schema"], indice_integridade.SCHEMA)
        self.assertEqual(bloco["decisao"], indice_integridade.BLOQUEAR)
        self.assertEqual(bloco["lacunas_pct"], 92)

    def test_semente_transporta_fora_convencao_com_decisao_ok(self) -> None:
        """Rota produtiva do achado legado (Codex, 314-r2): a semente carrega
        `fora_convencao` MESMO com `decisao: ok` — é o que o consumo do
        `briefing-estado.md` nomeia pra higiene; sem isso, o briefing rico
        anuncia "nada pendente" e o legado truncado passa limpo na interface
        principal."""
        self.escrever_coerente([1], "\n<!-- proximo-id: 2 -->\n")
        (self.root / "research-notes.md").write_text("x", encoding="utf-8")

        bloco = self._panorama()["indice_referencias"]
        self.assertEqual(bloco["decisao"], indice_integridade.OK)
        self.assertEqual(bloco["fora_convencao"], ["research-notes.md"])

    def test_semente_declara_indisponivel_sem_os_caminhos(self) -> None:
        """Chamador antigo não quebra, mas também não finge saber."""
        panorama, _ = build_local_panorama(
            pauta_path=self.root.parent / "PAUTA.md",
            inbox_path=self.root.parent / "INBOX.md",
            registro_path=self.root.parent / "REGISTRO.md",
            processed_path=self.root.parent / "_processed.json",
            preview={},
            today=date(2026, 7, 29),
            thresholds=faxina_thresholds.effective(self.root.parent),
        )
        self.assertEqual(panorama["indice_referencias"]["decisao"], "indisponivel")

    def test_override_do_usuario_chega_na_decisao(self) -> None:
        """#258: o efetivo, não o default."""
        rules = self.root.parent / "Prumo" / "Custom" / "rules"
        rules.mkdir(parents=True)
        (rules / "faxina-thresholds.md").write_text(
            "- referencias_bulk_reindex_at: 2\n", encoding="utf-8"
        )
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas([1, 2, 3])  # 2 fichas fora: abaixo do default 5, no override 2

        bloco = self._panorama()["indice_referencias"]
        self.assertEqual(bloco["decisao"], indice_integridade.BLOQUEAR)



class ContratoDaFaxinaTest(unittest.TestCase):
    """A decisão vive em dois lugares por construção (runtime e texto, pro host
    sem runtime). Divergir é o bug da #195 em outra roupa — então o texto tem
    de citar os MESMOS thresholds e a MESMA ordem."""

    def setUp(self) -> None:
        raiz = Path(__file__).resolve().parents[2]
        self.faxina = (raiz / "skills" / "prumo" / "references" / "modules"
                       / "faxina.md").read_text(encoding="utf-8")
        self.higiene = (raiz / "skills" / "higiene" / "SKILL.md").read_text(encoding="utf-8")

    def test_texto_cita_os_dois_thresholds_do_codigo(self) -> None:
        for chave in ("referencias_id_gap_alert_pct", "referencias_bulk_reindex_at"):
            self.assertIn(chave, self.faxina, f"{chave} não aparece no contrato textual")

    def test_texto_declara_a_precedencia(self) -> None:
        """Ordem importa: E1 antes de E2, senão o truncamento vira dois alarmes."""
        pos_lacuna = self.faxina.index("referencias_id_gap_alert_pct")
        pos_volume = self.faxina.index("referencias_bulk_reindex_at")
        self.assertLess(pos_lacuna, pos_volume)
        trecho = self.faxina[pos_lacuna:pos_volume]
        self.assertIn("PULADO", trecho, "não declara que sem rodapé o passo 1 é pulado")

    def test_texto_manda_bloquear_e_nao_consertar(self) -> None:
        self.assertIn("não alterar o índice", self.faxina.lower())
        self.assertIn("Bloqueio é o conserto", self.faxina)

    def test_texto_manda_nomear(self) -> None:
        """Contar não basta: só o usuário sabe que aquela ficha é de fevereiro."""
        self.assertIn("Nomear, não só contar", self.faxina)

    def test_a_entrega_pra_higiene_tem_o_outro_lado(self) -> None:
        """Fronteira dos dois lados: a faxina entrega e a higiene RECEBE. Sem
        isto, o estado bloqueado não teria dono (Codex, 261-4)."""
        self.assertIn("leve pra higiene", self.faxina.lower())
        self.assertIn("Integridade do índice de referências", self.higiene)
        self.assertIn("a remoção foi deliberada", self.higiene)

    def test_higiene_nunca_reinsere_sozinha(self) -> None:
        self.assertIn("Nunca:** reinserir automaticamente", self.higiene)

    def test_higiene_usa_a_copia_da_262(self) -> None:
        """Restaurar do snapshot preserva IDs e descrições; recriar da ficha
        não. A higiene tem de oferecer a boa primeiro."""
        self.assertIn(".prumo/backups/curated/", self.higiene)


class ColunaArquivoTest(BaseTest):
    """Buscar o nome no texto inteiro fazia ficha citada numa descrição contar
    como indexada — a linha perdida ficava invisível no detector feito pra
    achá-la (Codex, 261D-3)."""

    def test_mencao_na_descricao_nao_conta_como_entrada(self) -> None:
        texto = (
            "# Índice\n\n| # | Título | Arquivo | Data | Descrição | Keywords |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | Outra | outra.md | 01/02/2026 | conversa com Autor_Ficha-2_2026-01-01.md | tag |\n"
            "\n<!-- proximo-id: 2 -->\n"
        )
        self.escrever(texto)
        (self.root / "outra.md").write_text("x", encoding="utf-8")
        (self.root / "Autor_Ficha-2_2026-01-01.md").write_text("x", encoding="utf-8")

        r = self.avaliar()
        self.assertEqual(r["sem_entrada"], ["Autor_Ficha-2_2026-01-01.md"], "menção na descrição virou entrada")

    def test_celula_com_link_markdown_conta(self) -> None:
        """Negativa: a coluna pode vir como link — isso É entrada."""
        texto = (
            "# Índice\n\n| # | Título | Arquivo | Data | Descrição | Keywords |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | Ficha | [Ficha](Autor_Ficha-1_2026-01-01.md) | 01/02/2026 | desc | tag |\n"
            "\n<!-- proximo-id: 2 -->\n"
        )
        self.escrever(texto)
        (self.root / "Autor_Ficha-1_2026-01-01.md").write_text("x", encoding="utf-8")
        self.assertEqual(self.avaliar()["sem_entrada"], [])


class FronteiraExataTest(BaseTest):
    """Arredondar antes de comparar movia a fronteira configurada: 49,5% em
    101 slots virava 50 e bloqueava no limiar 50 (Codex, 261D-4)."""

    def test_49_5_por_cento_nao_bloqueia_no_limiar_50(self) -> None:
        # 101 slots, 51 ocupados → 50 lacunas = 49,50%
        self.escrever_coerente(range(1, 52), "\n<!-- proximo-id: 102 -->\n")
        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 50, "a exibição arredonda, e tudo bem")
        self.assertEqual(r["decisao"], indice_integridade.OK, "arredondou para DECIDIR")


class FonteIndisponivelTest(BaseTest):
    """Raiz inacessível virava lista vazia e podia dar casa em ordem — o
    silêncio confiante que a #236 já nomeou (Codex, 261D-5)."""

    def test_raiz_ausente_bloqueia_em_vez_de_atestar_limpeza(self) -> None:
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        import shutil
        indice = self.indice().read_text(encoding="utf-8")
        shutil.rmtree(self.root)
        self.root.parent.mkdir(parents=True, exist_ok=True)
        # índice existe fora da raiz removida
        alt = self.root.parent / "INDICE.md"
        alt.write_text(indice, encoding="utf-8")

        r = indice_integridade.avaliar(
            self.root, alt, gap_alert_pct=GAP, bulk_reindex_at=BULK
        )
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)
        self.assertFalse(r["fonte_completa"])

    def test_falha_de_listagem_bloqueia(self) -> None:
        """`iterdir`, não `glob`: o glob engole erro POR ENTRADA, então uma
        falha real de listagem passaria como pasta vazia — e o mock em `glob`
        nem reproduzia o caso (Codex, r2)."""
        from unittest.mock import patch
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        with patch.object(Path, "iterdir", side_effect=PermissionError("sem permissão")):
            r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)
        self.assertFalse(r["fonte_completa"])

    def test_indice_ausente_com_fichas_bloqueia(self) -> None:
        """Índice sumido COM fichas em disco é a forma mais GRAVE do
        incidente. Reindexar aqui recriaria o catálogo com IDs novos e
        descrições derivadas — o reflexo que a #261 existe pra matar."""
        self.fichas([1, 2])
        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)
        self.assertFalse(r["fonte_completa"])
        self.assertIn("ausente", " ".join(r["razoes"]))

    def test_workspace_novo_sem_indice_e_sem_fichas_esta_ok(self) -> None:
        """Negativa: pasta vazia é começo, não perda."""
        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.OK)
        self.assertTrue(r["fonte_completa"])


class ConsumoNoBriefingTest(unittest.TestCase):
    """Transportar não basta: o contrato do briefing tem de LER a decisão.
    A família 3 mandava só comparar conjuntos, que deixa passar índice
    truncado sem ficha órfã (Codex, 261D-2)."""

    def setUp(self) -> None:
        raiz = Path(__file__).resolve().parents[2]
        self.estado = (raiz / "skills" / "prumo" / "references" / "modules"
                       / "briefing-estado.md").read_text(encoding="utf-8")

    def _familia3(self) -> str:
        ini = self.estado.index("3. **`Referencias/INDICE.md`**")
        return self.estado[ini:self.estado.index("4. **Processados", ini)]

    def test_gate_de_capacidade_exige_o_bloco(self) -> None:
        """Runtime anterior traz o MESMO schema_version sem o bloco novo —
        sem isto ele fingiria vigilância."""
        self.assertIn("indice_referencias.schema", self.estado)

    def test_frescor_cobre_indice_e_fichas(self) -> None:
        self.assertIn("`INDICE.md` + manifesto de `Referencias/`", self.estado)

    def test_familia_3_le_a_decisao(self) -> None:
        f3 = self._familia3()
        self.assertIn("indice_referencias.decisao", f3)
        for estado in ("bloquear", "reindexar", "ok"):
            self.assertIn(estado, f3, f"a família 3 não trata `{estado}`")

    def test_familia_3_proibe_reindexar_no_bloqueio(self) -> None:
        self.assertIn("proibido reindexar", self._familia3())

    def test_fallback_sem_bloco_nao_e_so_diferenca_de_conjuntos(self) -> None:
        """O ponto cego: índice truncado SEM ficha órfã. Sem a lacuna do
        rodapé no fallback, ele volta."""
        f3 = self._familia3()
        self.assertIn("coluna `Arquivo`", f3)
        self.assertIn("lacuna do rodapé", f3)


class FrescorDaSementeTest(unittest.TestCase):
    """Sem o índice e as fichas no retrato de frescor, truncar depois do
    `prumo seed` deixava a semente 'fresca' carregando `decisao: ok` — o
    incidente reencenado com JSON e gravata (Codex, 261D-1)."""

    def setUp(self) -> None:
        import tempfile as _tf
        from prumo_runtime.workspace_paths import workspace_paths
        self._tmp = _tf.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "Prumo" / "Referencias").mkdir(parents=True)
        (self.ws / ".prumo" / "state").mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)
        self.paths = workspace_paths(self.ws)

    def _captura(self) -> dict:
        from prumo_runtime.commands.seed import _capture_sources
        return _capture_sources(self.paths)

    def test_truncar_o_indice_muda_o_retrato(self) -> None:
        self.paths.referencias_index.write_text("a" * 2000, encoding="utf-8")
        antes = self._captura()
        self.paths.referencias_index.write_text("a" * 20, encoding="utf-8")
        self.assertNotEqual(antes, self._captura(), "truncamento passou como semente fresca")

    def test_remover_ficha_muda_o_retrato(self) -> None:
        ficha = self.paths.referencias_root / "artigo.md"
        ficha.write_text("x", encoding="utf-8")
        antes = self._captura()
        ficha.unlink()
        self.assertNotEqual(antes, self._captura())

    def test_adicionar_ficha_muda_o_retrato(self) -> None:
        antes = self._captura()
        (self.paths.referencias_root / "novo.md").write_text("x", encoding="utf-8")
        self.assertNotEqual(antes, self._captura())

    def test_editar_ficha_muda_o_retrato(self) -> None:
        """Só o mtime da PASTA não bastaria: editar não mexe no diretório."""
        ficha = self.paths.referencias_root / "artigo.md"
        ficha.write_text("x", encoding="utf-8")
        antes = self._captura()
        ficha.write_text("conteúdo bem maior", encoding="utf-8")
        self.assertNotEqual(antes, self._captura())

    def test_workspace_parado_nao_muda(self) -> None:
        """Negativa: sem edição, o retrato é estável — senão a semente nunca
        seria considerada fresca."""
        (self.paths.referencias_root / "artigo.md").write_text("x", encoding="utf-8")
        self.assertEqual(self._captura(), self._captura())


class ParidadeDoTextoTest(unittest.TestCase):
    """Sem runtime, o texto É o algoritmo. Comparar a contagem crua com um
    percentual bloquearia 60 lacunas em 200 slots (30% real) só porque
    `60 >= 50` — unidades diferentes na mesma comparação (Codex, r2)."""

    def setUp(self) -> None:
        raiz = Path(__file__).resolve().parents[2]
        self.faxina = (raiz / "skills" / "prumo" / "references" / "modules"
                       / "faxina.md").read_text(encoding="utf-8")

    def test_o_texto_compara_taxa_e_nao_contagem(self) -> None:
        self.assertIn("lacunas × 100 ≥ referencias_id_gap_alert_pct × slots", self.faxina)
        self.assertNotIn("lacunas ≥ referencias_id_gap_alert_pct", self.faxina)

    def test_o_texto_declara_a_definicao_de_slots(self) -> None:
        self.assertIn("slots = N-1", self.faxina)


class ConferenciaTest(BaseTest):
    """"A remoção foi deliberada" só vale se MUDAR o predicado. Sem marca, a
    confirmação do usuário não altera nada e o mesmo alarme volta na rodada
    seguinte — saída cenográfica (Codex, r3)."""

    def _indice_com_lacuna_grande(self) -> None:
        self.escrever_coerente([45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n")

    def test_sem_marca_bloqueia(self) -> None:
        self._indice_com_lacuna_grande()
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.BLOQUEAR)

    def test_marca_de_conferencia_silencia(self) -> None:
        self._indice_com_lacuna_grande()
        with self.indice().open("a", encoding="utf-8") as fh:
            fh.write("<!-- lacunas-conferidas: 44/48 -->\n")
        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.OK)
        self.assertEqual(r["lacunas_conferidas"], [44, 48])

    def test_fracao_exata_nao_arredonda_pra_bloquear_de_novo(self) -> None:
        """Mesmo estado, mesma fração: não pode voltar a bloquear."""
        self.escrever_coerente(
            range(1, 100), "\n<!-- proximo-id: 201 -->\n<!-- lacunas-conferidas: 101/200 -->\n"
        )
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.OK)

    def test_crescimento_dentro_do_mesmo_percentual_arredondado_alarma(self) -> None:
        """O caso que separa fração exata de percentual arredondado: 100/200
        (50%) aceito, estado atual 101/200 (50,5%). Cresceu — mas os dois
        arredondam pra 50, então comparar percentual ficaria calado
        (Codex, r4). Sem este caso, as duas implementações empatam."""
        self.escrever_coerente(
            range(1, 100), "\n<!-- proximo-id: 201 -->\n<!-- lacunas-conferidas: 100/200 -->\n"
        )
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.BLOQUEAR)

    def test_volume_conferido_por_nome_silencia(self) -> None:
        """A marca silenciava a lacuna e o volume bloqueava logo em seguida —
        a confirmação não encerrava o alarme (Codex, r4)."""
        self.escrever(
            _tabela([1]) + "\n<!-- proximo-id: 2 -->\n"
            "<!-- fichas-fora-conferidas: Autor_Ficha-2_2026-01-01.md, Autor_Ficha-3_2026-01-01.md, Autor_Ficha-4_2026-01-01.md, "
            "Autor_Ficha-5_2026-01-01.md, Autor_Ficha-6_2026-01-01.md -->\n"
        )
        self.fichas(range(1, 7))
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.OK)

    def test_ficha_nova_alem_da_conferida_ainda_reindexa(self) -> None:
        """Negativa: por NOME, não por contagem.

        A conferida é a ÚLTIMA na ordem alfabética de propósito — com a
        primeira, remover-por-nome e cortar-N-do-início dão o mesmo resultado
        e o teste não distinguiria as duas implementações (achado da bateria).
        """
        self.escrever(
            _tabela([1]) + "\n<!-- proximo-id: 2 -->\n"
            "<!-- fichas-fora-conferidas: Autor_Ficha-3_2026-01-01.md -->\n"
        )
        self.fichas([1, 2, 3])
        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.REINDEXAR)
        self.assertEqual(r["sem_entrada"], ["Autor_Ficha-2_2026-01-01.md"])

    def test_lacuna_que_cresce_alem_do_conferido_volta_a_alarmar(self) -> None:
        """Negativa central: conferir não é cheque em branco."""
        self.escrever_coerente(
            range(1, 26), "\n<!-- proximo-id: 49 -->\n<!-- lacunas-conferidas: 24/48 -->\n"
        )
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.OK)

        self.escrever_coerente(
            [45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n<!-- lacunas-conferidas: 24/48 -->\n"
        )
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.BLOQUEAR)

    def test_marca_malformada_nao_silencia(self) -> None:
        self._indice_com_lacuna_grande()
        with self.indice().open("a", encoding="utf-8") as fh:
            fh.write("<!-- lacunas-conferidas: sei/la -->\n")
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.BLOQUEAR)


class FichaInacessivelTest(BaseTest):
    """`is_file()` transforma erro de stat em False: a ficha inacessível
    sumiria da contagem e o resultado podia ser `ok` (Codex, r3)."""

    def test_stat_que_falha_bloqueia(self) -> None:
        from unittest.mock import patch
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas([1])
        real = Path.lstat
        alvo = (self.root / "Autor_Ficha-1_2026-01-01.md").resolve()

        def falha(self, *a, **kw):
            if self.resolve() == alvo:
                raise PermissionError("sem permissão")
            return real(self, *a, **kw)

        with patch.object(Path, "lstat", falha):
            r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)
        self.assertFalse(r["fonte_completa"])


class ParidadeHigieneTest(unittest.TestCase):
    """A higiene é quem RESOLVE o que a faxina bloqueou. Se ela recalcular com
    defaults enquanto a faxina usou override, o bombeiro chega e discorda do
    alarme (Codex, r3)."""

    def setUp(self) -> None:
        raiz = Path(__file__).resolve().parents[2]
        self.higiene = (raiz / "skills" / "higiene" / "SKILL.md").read_text(encoding="utf-8")
        self.faxina = (raiz / "skills" / "prumo" / "references" / "modules"
                       / "faxina.md").read_text(encoding="utf-8")

    def _check9(self) -> str:
        ini = self.higiene.index("### 9. Integridade do índice de referências")
        return self.higiene[ini:self.higiene.index("## Fluxo de execução", ini)]

    def test_higiene_usa_thresholds_efetivos(self) -> None:
        c9 = self._check9()
        self.assertIn("EFETIVOS", c9)
        self.assertIn("Custom/rules/", c9)

    def test_higiene_grava_as_DUAS_marcas(self) -> None:
        """Gravar só uma não fecha: a outra dimensão bloqueia em seguida
        (Codex, r4)."""
        c9 = self._check9()
        self.assertIn("lacunas-conferidas", c9)
        self.assertIn("fichas-fora-conferidas", c9)
        self.assertIn("fração exata", c9)
        self.assertIn("por NOME", c9)

    def test_faxina_le_as_duas_marcas(self) -> None:
        """Os dois lados: quem grava e quem respeita."""
        self.assertIn("lacunas-conferidas", self.faxina)
        self.assertIn("fichas-fora-conferidas", self.faxina)

    def test_faxina_bloqueia_indice_ausente_com_ficha(self) -> None:
        self.assertIn("Índice ausente com ficha em disco", self.faxina)
        self.assertIn("não criar o índice", self.faxina.lower())


class OrfasTest(BaseTest):
    """O outro sentido da integridade. Sem ele, `decisao: ok` declarava a
    família limpa e suprimia o contrato que a §3 preserva desde sempre —
    marcar "(arquivo não encontrado)" e deixar a higiene decidir
    (Codex, r5)."""

    def test_entrada_sem_arquivo_nao_deixa_a_familia_limpa(self) -> None:
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")  # sem criar a ficha
        r = self.avaliar()
        self.assertEqual(r["entradas_sem_arquivo"], ["Autor_Ficha-1_2026-01-01.md"])
        self.assertNotEqual(r["decisao"], indice_integridade.OK, "família limpa com órfã")

    def test_orfa_aparece_nomeada_no_relato(self) -> None:
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.assertIn("Autor_Ficha-1_2026-01-01.md", indice_integridade.render(self.avaliar()))
        self.assertIn("sem arquivo", indice_integridade.render(self.avaliar()))

    def test_indice_coerente_nao_tem_orfa(self) -> None:
        """Negativa: entrada com arquivo em disco não é órfã."""
        self.escrever_coerente([1, 2], "\n<!-- proximo-id: 3 -->\n")
        r = self.avaliar()
        self.assertEqual(r["entradas_sem_arquivo"], [])
        self.assertEqual(r["decisao"], indice_integridade.OK)


class SimetriaComASementeTest(BaseTest):
    """O manifesto da semente EXCLUI symlink. Seguir aqui criava assimetria: o
    produtor lia o alvo pra dizer `ok`, e mudanças nele não mexiam no
    manifesto — a semente seguiria 'fresca' depois de um truncamento, o bug
    original de bigode postiço (Codex, r5)."""

    def test_referencias_symlinkado_e_fonte_indisponivel(self) -> None:
        import shutil
        alvo = Path(self._tmp.name) / "outro-lugar"
        alvo.mkdir()
        (alvo / "INDICE.md").write_text(
            _tabela([1]) + "\n<!-- proximo-id: 2 -->\n", encoding="utf-8"
        )
        shutil.rmtree(self.root)
        self.root.symlink_to(alvo, target_is_directory=True)

        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)
        self.assertFalse(r["fonte_completa"])


class MarcaImpossivelTest(BaseTest):
    def test_fracao_impossivel_nao_silencia(self) -> None:
        """`999/1` fazia a multiplicação cruzada concluir eternamente que a
        lacuna não cresceu (Codex, r5)."""
        self.escrever_coerente(
            [45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n<!-- lacunas-conferidas: 999/1 -->\n"
        )
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.BLOQUEAR)

    def test_fracao_com_zero_slots_nao_silencia(self) -> None:
        self.escrever_coerente(
            [45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n<!-- lacunas-conferidas: 0/0 -->\n"
        )
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.BLOQUEAR)

    def test_fracao_valida_continua_silenciando(self) -> None:
        """Negativa: o guard não pode reprovar marca legítima."""
        self.escrever_coerente(
            [45, 46, 47, 48], "\n<!-- proximo-id: 49 -->\n<!-- lacunas-conferidas: 44/48 -->\n"
        )
        self.assertEqual(self.avaliar()["decisao"], indice_integridade.OK)


class RelatoProdutivoTest(BaseTest):
    """`render()` não tinha chamador produtivo: nomear a órfã só acontecia no
    teste (Codex, r6). Agora os dois comandos imprimem no modo texto."""

    def _rodar(self, comando, **extra):
        import io
        from contextlib import redirect_stdout
        from types import SimpleNamespace
        from unittest.mock import patch
        buf = io.StringIO()
        with patch.object(comando, "snapshot_curated", return_value={}), \
             redirect_stdout(buf):
            comando.run_briefing(SimpleNamespace(workspace=str(self.ws), format="text"))
        return buf.getvalue()

    def setUp(self) -> None:
        super().setUp()
        self.ws = self.root.parent
        (self.ws / ".prumo" / "state").mkdir(parents=True, exist_ok=True)

    def test_briefing_nomeia_a_orfa_no_texto(self) -> None:
        from unittest.mock import patch
        from prumo_runtime.commands import briefing as cmd
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        payload = {
            "message": "painel",
            "local_panorama": {"indice_referencias": self.avaliar()},
        }
        with patch.object(cmd, "build_briefing_payload", return_value=payload):
            saida = self._rodar(cmd)
        self.assertIn("Autor_Ficha-1_2026-01-01.md", saida)
        self.assertIn("[indice]", saida)

    def test_briefing_silencioso_com_indice_limpo(self) -> None:
        """Negativa: casa em ordem não imprime linha nenhuma."""
        from unittest.mock import patch
        from prumo_runtime.commands import briefing as cmd
        self.escrever_coerente([1], "\n<!-- proximo-id: 2 -->\n")
        payload = {
            "message": "painel",
            "local_panorama": {"indice_referencias": self.avaliar()},
        }
        with patch.object(cmd, "build_briefing_payload", return_value=payload):
            saida = self._rodar(cmd)
        self.assertNotIn("[indice]", saida)

    def test_bloqueio_nomeia_orfa_tambem(self) -> None:
        """No ramo `bloquear` o render omitia as órfãs (Codex, r6)."""
        self.escrever(_tabela([45, 46, 47, 48]) + "\n<!-- proximo-id: 49 -->\n")
        self.fichas(range(1, 40))
        texto = indice_integridade.render(self.avaliar())
        self.assertIn("Sem arquivo:", texto)


class IndiceSymlinkadoTest(BaseTest):
    def test_indice_symlinkado_e_fonte_indisponivel(self) -> None:
        """Corrigi a raiz na r5 e deixei o ARQUIVO passar (Codex, r6)."""
        alvo = Path(self._tmp.name) / "fora.md"
        alvo.write_text(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n", encoding="utf-8")
        self.indice().symlink_to(alvo)
        r = self.avaliar()
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)
        self.assertFalse(r["fonte_completa"])


class EspinhaEModuloTest(unittest.TestCase):
    """A espinha declarava o gate ANTIGO enquanto o módulo detalhado exigia o
    bloco novo — contradição que deixaria runtime velho passar (Codex, r6)."""

    def setUp(self) -> None:
        raiz = Path(__file__).resolve().parents[2] / "skills" / "prumo" / "references" / "modules"
        self.espinha = (raiz / "briefing-procedure.md").read_text(encoding="utf-8")
        self.estado = (raiz / "briefing-estado.md").read_text(encoding="utf-8")
        self.faxina = (raiz / "faxina.md").read_text(encoding="utf-8")

    def test_espinha_e_modulo_pedem_o_mesmo_gate(self) -> None:
        self.assertIn("indice_referencias.schema", self.espinha)
        self.assertIn("indice_referencias.schema", self.estado)

    def test_fallback_textual_valida_a_marca(self) -> None:
        """O Python rejeita `999/1`; o texto aceitava qualquer fração e
        silenciaria o pavio no caminho skills-first."""
        self.assertIn("0 < S", self.faxina)
        self.assertIn("0 ≤ L ≤ S", self.faxina)


class PipeEscapadoTest(BaseTest):
    """Título com `\\|` empurrava a coluna e a ficha ÍNTEGRA era acusada de
    ausente — virando reindexação com ID novo, o reparo no escuro que esta
    issue existe pra impedir (Codex, r7)."""

    def test_titulo_com_pipe_escapado_nao_desloca_a_coluna(self) -> None:
        texto = (
            "# Índice\n\n| # | Título | Arquivo | Data | Descrição | Keywords |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | A \\| B | Autor_Ficha-1_2026-01-01.md | 01/02/2026 | desc | tag |\n"
            "\n<!-- proximo-id: 2 -->\n"
        )
        self.escrever(texto)
        self.fichas([1])
        r = self.avaliar()
        self.assertEqual(r["sem_entrada"], [], "ficha íntegra acusada de ausente")
        self.assertEqual(r["entradas_sem_arquivo"], [])

    def test_linha_curta_nao_quebra(self) -> None:
        """Negativa: tabela sem a terceira coluna não pode estourar."""
        self.escrever("# Índice\n\n| 1 | só duas |\n\n<!-- proximo-id: 2 -->\n")
        self.assertIsInstance(self.avaliar(), dict)


class SinalDoTextoTest(unittest.TestCase):
    """Igualdade não é crescimento: com `≥`, uma conferência `44/48` voltava a
    bloquear no briefing seguinte pelo caminho skills-first (Codex, r7)."""

    def setUp(self) -> None:
        raiz = Path(__file__).resolve().parents[2]
        self.faxina = (raiz / "skills" / "prumo" / "references" / "modules"
                       / "faxina.md").read_text(encoding="utf-8")

    def test_texto_usa_estritamente_maior(self) -> None:
        self.assertIn("lacunas × S > L × slots", self.faxina)
        self.assertNotIn("lacunas × S ≥ L × slots", self.faxina)

    def test_texto_diz_que_igualdade_nao_conta(self) -> None:
        self.assertIn("igualdade NÃO é crescimento", self.faxina)


if __name__ == "__main__":
    unittest.main()
