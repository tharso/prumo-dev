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


def _tabela(ids, arquivo=lambda n: f"ficha-{n}.md") -> str:
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

    def fichas(self, ids) -> None:
        for n in ids:
            (self.root / f"ficha-{n}.md").write_text(f"# Ficha {n}\n", encoding="utf-8")

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
        self.escrever(_tabela([45, 46, 47, 48]) + "\n<!-- proximo-id: 49 -->\n")
        self.fichas(range(1, 49))

        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 92)
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)

    def test_fronteira_abaixo_do_limiar(self) -> None:
        """49,x% não dispara — o limiar é `>=`."""
        self.escrever(_tabela(range(1, 51)) + "\n<!-- proximo-id: 100 -->\n")
        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 49)
        self.assertEqual(r["decisao"], indice_integridade.OK)

    def test_fronteira_no_limiar(self) -> None:
        self.escrever(_tabela(range(1, 50)) + "\n<!-- proximo-id: 99 -->\n")
        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 50)
        self.assertEqual(r["decisao"], indice_integridade.BLOQUEAR)

    def test_sem_rodape_pavio_indisponivel(self) -> None:
        """Negativa: workspace legado não tem rodapé, e ausência NUNCA é
        alarme por si."""
        self.escrever(_tabela([1, 2, 3]))
        r = self.avaliar()
        self.assertIsNone(r["lacunas_pct"])
        self.assertEqual(r["decisao"], indice_integridade.OK)

    def test_rodape_malformado_nao_alarma(self) -> None:
        self.escrever(_tabela([1, 2, 3]) + "\n<!-- proximo-id: abacaxi -->\n")
        self.assertIsNone(self.avaliar()["lacunas_pct"])

    def test_rodape_atrasado_nao_conta_id_acima(self) -> None:
        """IDs >= N não preenchem lacuna: o rodapé é sugestão (#244). Com
        rodapé 3 e IDs 1,2,50, os slots são {1,2} e estão cheios."""
        self.escrever(_tabela([1, 2, 50]) + "\n<!-- proximo-id: 3 -->\n")
        r = self.avaliar()
        self.assertEqual(r["lacunas_pct"], 0)

    def test_id_duplicado_conta_uma_vez(self) -> None:
        self.escrever(_tabela([1, 1, 2]) + "\n<!-- proximo-id: 4 -->\n")
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
        self.assertEqual(r["sem_entrada"], ["ficha-3.md"])

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

    def test_operacionais_nunca_contam(self) -> None:
        self.escrever(_tabela([1]) + "\n<!-- proximo-id: 2 -->\n")
        self.fichas([1])
        for nome in ("WORKFLOWS.md", "EMAIL-CURADORIA.md", "_rascunho.md"):
            (self.root / nome).write_text("x", encoding="utf-8")
        self.assertEqual(self.avaliar()["sem_entrada"], [])


class ArvoreUnicaTest(BaseTest):
    """E1 e E2 disparam no MESMO estado quando o índice é truncado. Como
    guards independentes dariam duas sirenes pro mesmo incêndio, a árvore é
    exclusiva e o volume entra como EVIDÊNCIA (Codex, 261-5)."""

    def test_truncamento_da_um_alerta_so(self) -> None:
        self.escrever(_tabela([45, 46, 47, 48]) + "\n<!-- proximo-id: 49 -->\n")
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
        self.assertIn("ficha-2.md", texto)

    def test_casa_em_ordem_e_silencio(self) -> None:
        self.escrever(_tabela([1, 2]) + "\n<!-- proximo-id: 3 -->\n")
        self.fichas([1, 2])
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
        self.escrever(_tabela([45, 46, 47, 48]) + "\n<!-- proximo-id: 49 -->\n")
        self.fichas(range(1, 49))

        bloco = self._panorama()["indice_referencias"]
        self.assertEqual(bloco["schema"], indice_integridade.SCHEMA)
        self.assertEqual(bloco["decisao"], indice_integridade.BLOQUEAR)
        self.assertEqual(bloco["lacunas_pct"], 92)

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


if __name__ == "__main__":
    unittest.main()


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
