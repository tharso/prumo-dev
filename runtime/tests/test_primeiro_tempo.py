"""Integridade do contrato do primeiro tempo (#284).

A #196 prometeu "tempo até a primeira resposta" e não deixou como cobrar. No
briefing real de 30/07 o agente compôs os dois tempos e entregou tudo junto
aos 11 minutos; o auto-relatório certificou conformidade auditando a
numeração contínua — verdadeira e irrelevante, porque ela prova que os
números não reiniciaram, não que houve DUAS entregas.

O ASSERT do core (`test_core_asserts.py`) congela o texto. Este módulo
congela as PEÇAS de que ele depende, espalhadas por três arquivos: se
qualquer uma sair de baixo dele, o ASSERT vira letra morta apontando pro
vazio. Um teste estático não prova que um modelo vai entregar texto antes de
uma ferramenta — isso é do guard de transcript, no medidor. Aqui só se
garante que o contrato continua dizendo o que o ASSERT afirma que ele diz.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULES = REPO_ROOT / "skills" / "prumo" / "references" / "modules"
CORE = REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"
MONTAGEM = MODULES / "briefing-montagem.md"
CANAIS = MODULES / "briefing-canais.md"

# A frase-sentinela é MARCADOR DE PROTOCOLO, não copy (#284). É a fronteira
# observável que o ASSERT usa e que o medidor procura no transcript. Mudá-la
# exige atualizar, no mesmo diff: o core, o montagem, este guard e o parser.
SENTINELA = "Curadoria de email e agenda chegando na sequência."


def _read(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class SentinelaTest(unittest.TestCase):
    """A frase existe, é única no dono, e o ASSERT cita a mesma string."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.core = _read(CORE)
        cls.montagem = _read(MONTAGEM)

    def test_sentinela_existe_no_montagem(self) -> None:
        self.assertIn(
            SENTINELA,
            self.montagem,
            "a frase-sentinela sumiu do briefing-montagem.md — o ASSERT do "
            "core e o medidor ficam apontando pro vazio",
        )

    def test_assert_do_core_usa_a_mesma_string(self) -> None:
        # Duas grafias divergentes fariam o guard passar e a execução falhar:
        # o agente encerra com uma frase e o detector procura outra.
        self.assertIn(
            SENTINELA,
            self.core,
            "o ASSERT do core não cita a frase-sentinela textualmente — "
            "fronteira observável tem de ser a MESMA string dos dois lados",
        )

    def test_sentinela_mora_na_secao_do_PRIMEIRO_tempo(self) -> None:
        # A mutação que os testes de string sozinhos deixariam passar: mover a
        # linha para a seção do segundo tempo. Todas as palavras continuariam
        # presentes no arquivo e o contrato estaria invertido — o "fim do
        # primeiro tempo" passaria a marcar o fim do briefing inteiro.
        bruto = MONTAGEM.read_text(encoding="utf-8")
        inicio = bruto.index("### Primeiro tempo")
        fim = bruto.index("### Segundo tempo")
        primeiro, segundo = bruto[inicio:fim], bruto[fim:]

        self.assertIn(
            SENTINELA,
            " ".join(primeiro.split()),
            "a frase-sentinela saiu da seção do PRIMEIRO tempo",
        )
        self.assertNotIn(
            SENTINELA,
            " ".join(segundo.split()),
            "a frase-sentinela aparece também depois do primeiro tempo — "
            "fronteira ambígua faz o detector marcar o momento errado",
        )

    def test_montagem_declara_que_e_marcador_de_protocolo(self) -> None:
        self.assertIn(
            "marcador de protocolo",
            self.montagem,
            "sem essa declaração a linha volta a ser lida como copy e alguém "
            "a reescreve por gosto, quebrando o detector em silêncio",
        )


class AssertReferenciaAsPecasTest(unittest.TestCase):
    """O ASSERT tem de nomear a fronteira e a natureza da falha."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.core = _read(CORE)

    def test_assert_nomeia_a_fronteira_observavel(self) -> None:
        self.assertIn(
            "nenhuma chamada Gmail/Calendar pode começar antes",
            self.core,
            "a fronteira do ASSERT tem de ser a primeira chamada "
            "Gmail/Calendar — é o único evento observável no transcript",
        )

    def test_assert_fecha_a_brecha_de_compor(self) -> None:
        # Sem isto o agente se convence de que "emitiu" porque pôs o primeiro
        # bloco antes do segundo dentro da MESMA resposta final.
        self.assertIn("Compor não é entregar", self.core)
        self.assertIn("emitido junto do segundo tempo não conta", self.core)

    def test_preflight_fica_fora_por_construcao(self) -> None:
        # O WebFetch de versão pertence ao primeiro tempo e não pode ser
        # bloqueado. A proibição cita canal, não rede — o carve-out é
        # estrutural, não uma exceção escrita que alguém possa ampliar.
        assert_line = next(
            linha
            for linha in CORE.read_text(encoding="utf-8").splitlines()
            if linha.startswith("`ASSERT: Em host de dois tempos")
        )
        for termo in ("WebFetch", "preflight", "rede"):
            self.assertNotIn(
                termo,
                assert_line,
                f"o ASSERT menciona '{termo}' — a fronteira tem de ser "
                "Gmail/Calendar e só; citar rede convida a ampliar a proibição",
            )


class PecasNosOutrosModulosTest(unittest.TestCase):
    """As duas premissas que moram fora do core."""

    def test_canais_ainda_exige_primeiro_tempo_antes_dos_externos(self) -> None:
        canais = _read(CANAIS)
        self.assertIn(
            "antes de qualquer resultado de email/calendário",
            canais,
            "briefing-canais.md deixou de exigir o primeiro tempo antes dos "
            "canais externos — o ASSERT do core passa a contradizer a fase",
        )

    def test_cowork_continua_classificado_como_dois_tempos(self) -> None:
        # O ASSERT nomeia o Cowork diretamente. Se a matriz reclassificar o
        # host, o ASSERT passa a impor dois tempos onde o produto já desistiu
        # deles — e o briefing quebra por conformidade, não por defeito.
        montagem = _read(MONTAGEM)
        self.assertIn(
            "| Cowork | **dois tempos completo**",
            montagem,
            "a matriz por host mudou a classificação do Cowork; o ASSERT do "
            "core o nomeia explicitamente e precisa ser revisto junto",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
