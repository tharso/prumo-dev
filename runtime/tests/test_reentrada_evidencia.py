"""Reentrada por evidência (#325): a soneca que qualquer batida cancela.

O caso-mãe (rodada 18h de 03/08): ganho de capital e processo Santa Maria
suprimidos por `cobrar: 06/08` — e a guia de custas do processo chegou por
email NO MESMO DIA, virando item avulso sem conexão com a pendência
escondida. As quatro regras vieram de grill com o dono (03/08): qualquer
evidência reabre; a evidência queima a supressão; os três braços cruzam;
na dúvida, reabre como "vínculo possível".

Pergunta de mutação que estes guards respondem: que edição errada
preservaria as palavras? (a) tirar a exceção do filtro de F1 (a regra
ficaria bonita no canais e o filtro seguiria suprimindo) — assert de
POSIÇÃO; (b) inverter a validade do evento (valer até baixa explícita
recriaria o ledger que o desenho evitou) — âncora da regra de staleness;
(c) apresentar o reaberto sem o vínculo (a conexão perdida que motivou
tudo) — âncora DENTRO do bullet das pendências.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULES = REPO_ROOT / "skills" / "prumo" / "references" / "modules"
CANAIS = (MODULES / "briefing-canais.md").read_text(encoding="utf-8")
ESTADO = (MODULES / "briefing-estado.md").read_text(encoding="utf-8")
MONTAGEM = (MODULES / "briefing-montagem.md").read_text(encoding="utf-8")


class RegrasDoGrillTest(unittest.TestCase):
    """As quatro decisões do dono, ancoradas no dono do cruzamento (canais)."""

    def test_reentrada_universal_sem_juizo_de_relevancia(self) -> None:
        self.assertIn("Reentrada por evidência (#325", CANAIS)
        self.assertIn("sem juízo de relevância", CANAIS)
        self.assertIn("qualquer evidência reabre", CANAIS)

    def test_evidencia_queima_a_supressao(self) -> None:
        self.assertIn("queima a supressão", CANAIS)
        self.assertIn("permanece até despacho", CANAIS)
        self.assertIn("soneca, não cofre", CANAIS)

    def test_os_tres_bracos_cruzam(self) -> None:
        self.assertIn("TRÊS braços", CANAIS)
        secao = CANAIS[CANAIS.index("Reentrada por evidência (#325"):]
        trecho = secao[:1200]
        for braco in ("email", "calendário", "Inbox4Mobile"):
            self.assertIn(braco, trecho, f"braço {braco} fora do cruzamento")

    def test_na_duvida_reabre_como_vinculo_possivel(self) -> None:
        self.assertIn("Na dúvida, reabre", CANAIS)
        self.assertIn('"vínculo possível"', CANAIS)
        self.assertIn("nunca é descartado em silêncio", CANAIS)

    def test_vinculo_e_julgamento_do_agente(self) -> None:
        self.assertIn("julgamento do agente", CANAIS)


class PersistenciaTest(unittest.TestCase):
    def test_evento_no_registro_com_data_original(self) -> None:
        # Padrão #238: fonte durável é evento no REGISTRO, não marker novo.
        self.assertIn("data original do cobrar", CANAIS)
        self.assertIn("Reabertura: <item>", CANAIS)

    def test_staleness_e_pela_data_do_cobrar_nao_por_baixa(self) -> None:
        # A mutação barata: "vale até baixa explícita" recriaria um ledger
        # de reaberturas — o desenho faz o evento envelhecer sozinho.
        self.assertIn("enquanto o cobrar da linha for o MESMO registrado", CANAIS)
        self.assertIn("o evento envelhece sozinho, sem baixa", CANAIS)
        self.assertIn("UM passo", CANAIS)

    def test_briefing_nunca_mexe_no_cobrar(self) -> None:
        # #242: a PAUTA só muda via despacho.
        self.assertIn("**nunca** mexe no `cobrar` por conta própria", CANAIS)

    def test_busca_alem_da_cauda(self) -> None:
        # Codex 325-r1 (P1): a cauda da semente tem ~10 linhas — evento fora
        # dela suprimiria de volta em silêncio, quebrando o "vivo até
        # despacho". Suprimido sem evento na cauda exige busca dirigida.
        self.assertIn("Busca além da cauda", CANAIS)
        self.assertIn("recorte dirigido", CANAIS)
        self.assertIn("NÃO pode suprimir o item de volta em silêncio", CANAIS)

    def test_evidencia_consumida_nao_requeima(self) -> None:
        # Codex 325-r1 (P2): o email ainda na janela de 24h re-queimaria a
        # data nova no briefing seguinte — re-suprimir de UM passo viraria
        # zero. Evidência já registrada em reabertura anterior está consumida.
        self.assertIn("CONSUMIDA", CANAIS)
        self.assertIn("só evidência nova reabre", CANAIS)
        self.assertIn("viraria zero passos", CANAIS)


class FiltroDeF1Test(unittest.TestCase):
    def test_excecao_vive_DENTRO_do_filtro_de_cobranca(self) -> None:
        # Posição, não só presença: a exceção fora do filtro deixaria a
        # regra bonita no canais enquanto F1 segue suprimindo o item.
        inicio = ESTADO.index("## Filtro de cobrança")
        fim = ESTADO.find("\n## ", inicio + 1)
        filtro = ESTADO[inicio : fim if fim != -1 else len(ESTADO)]
        self.assertIn("Exceção (#325)", filtro)
        self.assertIn("reabertura VÁLIDA no REGISTRO", filtro)
        self.assertIn("volta VIVO", filtro)
        # A busca não é só a cauda (Codex 325-r1): o gatilho de F1 aponta o
        # recorte dirigido cuja regra completa mora nos canais.
        self.assertIn("busca além da cauda (recorte dirigido)", filtro)

    def test_excecao_aplica_depois_da_regra_base(self) -> None:
        # A semente calcula a regra base; a exceção é do agente, DEPOIS —
        # senão a paridade do runtime viraria mentira.
        self.assertIn("aplica-se DEPOIS", ESTADO)


class ApresentacaoTest(unittest.TestCase):
    def test_reaberto_entra_no_bullet_das_pendencias_com_vinculo(self) -> None:
        # O vínculo visível é o remédio do caso-mãe (item 26 sem conexão).
        bullet = next(
            linha
            for linha in MONTAGEM.splitlines()
            if "Pendências vivas da PAUTA" in linha
        )
        self.assertIn("REABERTO por evidência (#325)", bullet)
        self.assertIn("vínculo visível", bullet)
        self.assertIn("cobrar 06/08 queimado", bullet)
        self.assertIn("vínculo possível", bullet)

    def test_descoberta_por_email_agenda_apresenta_no_segundo_tempo(self) -> None:
        # Codex 325-r1 (P1): no fluxo de dois tempos, Gmail/Calendar só
        # abrem DEPOIS da primeira entrega — a reabertura descoberta por
        # eles precisa de caminho de apresentação no SEGUNDO tempo, senão
        # ela só apareceria amanhã (a conexão perdida de novo).
        self.assertIn("Reabertura descoberta na curadoria (#325", MONTAGEM)
        self.assertIn("entra no **SEGUNDO tempo** como item numerado", MONTAGEM)
        self.assertIn("só abrem DEPOIS da primeira entrega", MONTAGEM)



class IdentidadeDaEvidenciaTest(unittest.TestCase):
    """Codex 325-r2: consumo por prosa não consome nada — o mesmo email
    resumido com outras palavras parecia evidência nova."""

    def test_evento_exige_identidade_estavel(self) -> None:
        self.assertIn("[id: <identidade estável>]", CANAIS)
        self.assertIn("identidade estável é obrigatória", CANAIS)
        self.assertIn("é por ELA que o consumo reconhece", CANAIS)

    def test_consumo_compara_pelo_id_nunca_pelo_resumo(self) -> None:
        self.assertIn("a comparação é pelo id, nunca pelo resumo", CANAIS)

    def test_busca_leva_o_item_nao_so_o_prefixo(self) -> None:
        # O prefixo sozinho num REGISTRO cheio devolve as reaberturas de
        # todos os itens — recorte sem direção não é recorte.
        self.assertIn("junto do identificador do item suprimido", CANAIS)
        self.assertIn("nunca o prefixo sozinho", CANAIS)

    def test_gatilho_do_mapa_cobre_variante_zero_canais(self) -> None:
        # Sem esta perna, F2 nunca abre no host sem email/agenda/inbox e a
        # reabertura fora da cauda fica suprimida com briefing "completo".
        # "Válido" importa (325-r3): evento STALE na cauda não dispensa a
        # busca — um consumido fora dela pareceria evidência nova.
        skill = (
            REPO_ROOT / "skills" / "briefing" / "SKILL.md"
        ).read_text(encoding="utf-8")
        linha_canais = next(
            ln for ln in skill.splitlines()
            if "briefing-canais.md" in ln and "| F2 |" in ln
        )
        self.assertIn("OU suprimido sem evento válido na cauda", linha_canais)

    def test_evento_stale_na_cauda_nao_dispensa_a_busca(self) -> None:
        # Codex 325-r3 (P1): E2 stale na cauda bloqueava a busca por E1
        # consumida fora dela — E1 parecia nova e re-queimava.
        self.assertIn("sem evento VÁLIDO na cauda", CANAIS)
        self.assertIn("evento stale na cauda NÃO dispensa a busca", CANAIS)

    def test_identidade_do_item_exclui_os_markers(self) -> None:
        # Codex 325-r3 (P1): com a linha inteira como chave, mudar o cobrar
        # mudaria exatamente a chave usada pra achar o histórico.
        self.assertIn("Identidade do item (Codex, 325-r3/r4)", CANAIS)
        self.assertIn("sem os markers `| chave: valor` e sem numeração", CANAIS)
        self.assertIn("NUNCA inclui o marker que a re-supressão altera", CANAIS)

    def test_busca_tem_teto_declarado(self) -> None:
        # Codex 325-r3 (P2): recorte sem teto pode devolver uma parcela
        # arbitrária do REGISTRO num item recorrente.
        self.assertIn("teto explícito: as 20 linhas mais recentes do item", CANAIS)
        self.assertIn("declarar o corte", CANAIS)
        self.assertIn('"histórico truncado"', CANAIS)



class HistoricoTruncadoEColisoesTest(unittest.TestCase):
    """Codex 325-r4: o teto não pode tornar falsa a promessa do consumo, e
    a identidade normalizada não pode colidir em silêncio."""

    def test_truncamento_reabre_como_vinculo_possivel(self) -> None:
        # Com 21+ eventos, id consumido além do teto pareceria novo. Na
        # dúvida do histórico vale a régua do dono: mostrar custa um clique;
        # esconder custa o incidente-mãe.
        self.assertIn("o consumo é INCOMPLETO por construção", CANAIS)
        self.assertIn('"vínculo possível — histórico truncado"', CANAIS)
        self.assertIn("nunca fica suprimida", CANAIS)

    def test_identidade_leva_a_secao_como_discriminador(self) -> None:
        self.assertIn("a seção da PAUTA + a linha sem os markers", CANAIS)
        self.assertIn("A seção é o discriminador", CANAIS)

    def test_colisao_na_mesma_secao_trata_pro_lado_de_mostrar(self) -> None:
        self.assertIn("colisão trata pro lado de mostrar", CANAIS)
        self.assertIn("a reabertura vale pra ambas", CANAIS)


if __name__ == "__main__":
    unittest.main()
