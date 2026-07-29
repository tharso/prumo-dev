"""Contrato de escrita em arquivo curado (#261, E3).

Uma política de carregamento condicional só dispara se algo JÁ CARREGADO
souber quando carregá-la: pra identificar "vou substituir integralmente um
arquivo curado", o agente precisaria conhecer a regra antes de lê-la — catraca
com o segurança trancado no almoxarifado (Codex, design r1).

Por isso a regra 6 do core (rota sempre-carregada) ganhou o ponteiro, com o
custo aprovado pelo dono: catraca 6.642 → 6.652. Este guard existe pra que o
ponteiro não seja removido junto com o doc numa dieta futura — foi o cenário
que o Codex nomeou como "promessa que o incidente já demonstrou que agentes
esquecem".

Guard de CONTRATO, não de comportamento: nenhum texto impede uma escrita. O
que é mecânico está na #262 (cópia) e no `indice_integridade` (detecção).
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md"
POLITICA = REPO_ROOT / "skills" / "prumo" / "references" / "escrita-curada.md"
FICHA = REPO_ROOT / "skills" / "prumo" / "references" / "ficha-de-fonte.md"


class GatilhoNaRotaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.core = CORE.read_text(encoding="utf-8")

    def test_a_rota_aponta_a_politica(self) -> None:
        self.assertIn("escrita-curada.md", self.core, "o gatilho sumiu da rota")

    def test_o_gatilho_nomeia_a_condicao(self) -> None:
        """Ponteiro sem condição não é gatilho: o agente precisa saber QUANDO
        carregar, senão carrega sempre (custo) ou nunca (inútil)."""
        linha = next(l for l in self.core.splitlines() if "escrita-curada.md" in l)
        self.assertIn("substituir integralmente", linha)

    def test_o_alvo_do_ponteiro_existe(self) -> None:
        """Ponteiro pra arquivo inexistente é pior que ponteiro nenhum:
        custa palavra na rota e não entrega nada."""
        self.assertTrue(POLITICA.is_file(), f"{POLITICA} não existe")


class PoliticaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.texto = POLITICA.read_text(encoding="utf-8")

    def test_declara_append_como_operacao_sancionada(self) -> None:
        self.assertIn("Acrescentar é a operação sancionada", self.texto)

    def test_preserva_a_244_em_vez_de_revogar(self) -> None:
        """O relatório pediu 'proibido escrever índice sem ler inteiro', que
        colide de frente com a #244 ('ler a última linha, nunca o arquivo
        inteiro'). A formulação que sobra governa a REESCRITA TOTAL e deixa o
        append como a #244 o definiu — as duas continuam válidas."""
        self.assertIn("#244", self.texto)
        self.assertIn("continua valendo", self.texto)
        self.assertIn("última linha", self.texto)

    def test_reescrita_do_indice_acontece_sob_lock(self) -> None:
        """Ler e escrever em momentos diferentes sem lock reabre a corrida que
        a #244 fechou (Codex, 261-8)."""
        self.assertIn("lock", self.texto)
        self.assertIn("janela inteira", self.texto)

    def test_nao_promete_trava_mecanica(self) -> None:
        """Honestidade arquitetural: o Prumo não tem gancho na ferramenta de
        escrita do host. Prometer bloqueio seria promessa que não se cumpre."""
        self.assertIn("Não é trava mecânica", self.texto)

    def test_a_244_nao_foi_enfraquecida(self) -> None:
        """Do outro lado: o dono do append continua mandando ler só a última
        linha. Se alguém 'harmonizasse' os dois docs pra ler tudo sempre, a
        #244 morria em silêncio."""
        ficha = FICHA.read_text(encoding="utf-8")
        self.assertIn("nunca o arquivo inteiro", ficha)


if __name__ == "__main__":
    unittest.main()
