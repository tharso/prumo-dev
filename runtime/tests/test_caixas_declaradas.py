"""Caixas de entrada declaradas (#245).

30 itens apodreceram 5 meses numa rota morta e 10 nos Clippings desde junho
porque só o `Inbox4Mobile/` era contado. Estes guards travam: a gramática do
marcador (dona única), o bootstrap fásico que quebra o ciclo (a gramática
carrega ANTES do gate que depende dela), o escopo (inventário e cobrança, sem
processamento automático) e o detector da higiene.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"
LOAD_POLICY = SKILLS / "prumo" / "references" / "modules" / "load-policy.md"
CANAIS = SKILLS / "prumo" / "references" / "modules" / "briefing-canais.md"
MONTAGEM = SKILLS / "prumo" / "references" / "modules" / "briefing-montagem.md"
HIGIENE = SKILLS / "higiene" / "SKILL.md"
BRIEFING_SKILL = SKILLS / "briefing" / "SKILL.md"


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class CaixasDeclaradasTest(unittest.TestCase):
    def test_marcador_na_lista_fechada_com_excecao_delimitada(self) -> None:
        flat = _flat(LOAD_POLICY)
        self.assertIn("`(caixa de entrada)`", flat)
        self.assertIn("contagem da listagem plana + metadata rasa (nome e mtime)", flat)
        self.assertIn("**nunca conteúdo**", flat)
        self.assertIn("antiga caixa de entrada", flat, "falta o exemplo de match exato")

    def test_gramatica_carrega_antes_do_gate(self) -> None:
        """[P5-3]: bootstrap circular quebrado — a linha da gramática precede a
        do gate no MANIFESTO.

        Ordem verificada na SEQUÊNCIA devolvida pelo `parse_manifest` (Codex,
        diff r1: `EXPECTED_MAP` é frozenset — não trava ordem; e `str.find`
        global seria enganado por menção em prosa ou comentário).
        """
        from test_briefing_preload_guard import _audit  # parser já carregado
        parsed = _audit.parse_manifest(BRIEFING_SKILL.read_text(encoding="utf-8"))
        self.assertIsNotNone(parsed, "manifesto ausente do briefing/SKILL.md")
        rows, invalid = parsed
        self.assertEqual(invalid, [], f"linhas malformadas no manifesto: {invalid}")
        files = [(row["file"], row["trigger"]) for row in rows]
        gramatica = [
            i
            for i, (f, t) in enumerate(files)
            if f.endswith("load-policy.md") and "gramática dos marcadores" in t
        ]
        gate = [i for i, (f, _t) in enumerate(files) if f.endswith("briefing-canais.md")]
        self.assertTrue(gramatica, "linha da gramática ausente do manifesto")
        self.assertTrue(gate, "linha do gate (briefing-canais) ausente do manifesto")
        self.assertLess(
            min(gramatica),
            min(gate),
            "a gramática tem de vir ANTES do gate na sequência do manifesto",
        )
        self.assertIn(
            "caixa declarada",
            files[min(gate)][1],
            "o gatilho do gate não cobre caixa declarada",
        )

    def test_gramatica_declarada_uma_vez_so(self) -> None:
        """Dona única: nenhum outro módulo repete a lista de marcadores."""
        offenders = []
        for md in sorted(SKILLS.rglob("*.md")):
            if md == LOAD_POLICY:
                continue
            flat = re.sub(r"\s+", " ", md.read_text(encoding="utf-8"))
            if "(caixa de entrada)" in flat and "marcadores reservados" in flat:
                offenders.append(str(md.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [], f"gramática duplicada fora da dona: {offenders}")

    def test_canais_conta_itens_presentes_sem_processar(self) -> None:
        flat = _flat(CANAIS)
        self.assertIn("Caixas de entrada declaradas (#245)", flat)
        self.assertIn("contagem dos itens presentes", flat)
        self.assertIn("Nenhum processamento automático", flat)
        self.assertIn(
            "`_processed.json` é contrato exclusivo do `Inbox4Mobile/`",
            flat,
            "falta declarar que caixa genérica não tem ledger",
        )

    def test_montagem_apresenta_contagem(self) -> None:
        flat = _flat(MONTAGEM)
        self.assertIn("Caixas declaradas (#245)", flat)
        self.assertIn("sem despejar itens", flat)

    def test_higiene_sinaliza_caixa_envelhecida(self) -> None:
        flat = _flat(HIGIENE)
        self.assertIn("Caixa declarada envelhecida (#245)", flat)
        self.assertIn("`declared_inbox_stale_days`", flat)
        self.assertIn("sinalizar, nunca reorganizar", flat)

    def test_oferta_de_catalogacao_oferece_sem_agir(self) -> None:
        """#332: contagem > 0 gera OFERTA — e a oferta não compra nada sozinha:
        sem confirmação não há escrita nem leitura de conteúdo."""
        flat = _flat(CANAIS)
        self.assertIn("Oferta de catalogação (#332)", flat)
        self.assertIn("oferta, nunca ação", flat)
        self.assertIn(
            "sem confirmação explícita, nenhuma escrita e nenhuma leitura de conteúdo",
            flat,
            "a oferta precisa declarar que não lê nem escreve antes do sim",
        )

    def test_oferta_mora_na_secao_dona(self) -> None:
        """A oferta vale porque carrega junto do gate das caixas declaradas —
        fora da seção, a frase vira letra morta que nenhum fluxo lê."""
        text = CANAIS.read_text(encoding="utf-8")
        secao = text.index("## Caixas de entrada declaradas (#245)")
        oferta = text.index("Oferta de catalogação (#332)")
        proxima = text.index("## ", secao + 1)
        self.assertTrue(
            secao < oferta < proxima,
            "a oferta tem de viver DENTRO da seção 'Caixas de entrada declaradas'",
        )

    def test_oferta_reafirma_escopo_do_marcador(self) -> None:
        """A oferta não é licença: o escopo do #245 (sem processamento
        automático, sem ledger) é reafirmado DENTRO do texto da oferta."""
        flat = _flat(CANAIS)
        self.assertIn("Nenhum processamento automático", flat)
        self.assertIn("continua sem processamento automático e sem ledger", flat)

    def test_lote_degrada_no_escuro(self) -> None:
        """Item sem frontmatter legível não entra no lote cego: degrada pra
        proposta individual."""
        flat = _flat(CANAIS)
        self.assertIn("degrada pra proposta individual", flat)
        self.assertIn("o lote nunca age no escuro", flat)

    def test_lote_exige_motivo_item_a_item(self) -> None:
        """[Codex r1, P1]: confirmação genérica de lote não compra o
        `keep_with_reason` — sem motivo inferível ou dado, o item degrada."""
        flat = _flat(CANAIS)
        self.assertIn("`keep_with_reason` vale item a item", flat)
        self.assertIn("sem motivo, duplicado ou ambíguo", flat)

    def test_lote_renomeia_na_convencao_canonica(self) -> None:
        """[Codex r1, P2]: renomeação 'descritiva' fora da convenção deixa o
        arquivo fora da rota de recuperação do índice (#305)."""
        flat = _flat(CANAIS)
        self.assertIn("Autor_Assunto_AAAA-MM-DD", flat)
        self.assertIn("fora dela o arquivo sai da rota de recuperação do índice", flat)

    def test_montagem_apresenta_a_oferta(self) -> None:
        flat = _flat(MONTAGEM)
        self.assertIn("oferta de catalogação (#332)", flat)
        self.assertIn("nunca ação sem confirmação", flat)

    def test_threshold_do_override_existe_de_verdade(self) -> None:
        """[P5-2]: a promessa de override precisa de chave canônica declarada —
        vocabulário inventado não é sobrescrevível."""
        thresholds = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "faxina-thresholds.md"
        flat = _flat(thresholds)
        self.assertIn("declared_inbox_stale_days", flat)
        self.assertRegex(flat, r"declared_inbox_stale_days \| 14 \|")


if __name__ == "__main__":
    unittest.main()
