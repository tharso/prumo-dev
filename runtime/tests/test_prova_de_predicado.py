"""Prova de predicado de busca (#236) — o zero silencioso vira estado declarado.

`from:me newer_than:4d` devolveu `{}` no briefing real de 27/07 enquanto existia
mensagem com `SENT` em `labelIds` DENTRO da janela: o conector não resolvia o
alias `me`, e o vazio foi lido como "não tem nada". A regra que existia pra
prevenir o furo da Cora estava silenciosamente morta desde que foi escrita — o
buraco só não apareceu porque uma busca por palavra-chave o cobriu por sorte.

ESCOPO DESTES GUARDS: travam o CONTRATO TEXTUAL — protocolo, estados fechados,
orçamento, dono da completude, schema do registro. NÃO provam comportamento de
conector: não existe função de produção que execute query e classifique
veredito, e simular conector dentro do teste seria teatro com crachá. O que
eles impedem é o contrato perder uma perna numa edição futura.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"
CANAIS = SKILLS / "prumo" / "references" / "modules" / "briefing-canais.md"
MONTAGEM = SKILLS / "prumo" / "references" / "modules" / "briefing-montagem.md"
FILE_TEMPLATES = SKILLS / "prumo" / "references" / "file-templates.md"

TITULO = "### Prova de predicado de busca (#236)"
# Os 3 primeiros são estados da ASSINATURA; o 4º é da resposta deste briefing e
# se alcança sem assinatura — sem ele, varredura exaustiva sem correspondência
# ficava simultaneamente `INCONCLUSIVO` e "zero confiável" (gate r1, achado 1).
ESTADOS = ("VALIDADA", "FALHA", "INCONCLUSIVO", "VAZIO CONFIRMADO")


def _flat(text: str) -> str:
    """Achata pra comparar frase. Tira o `>` de continuação de citação: numa
    frase quebrada em duas linhas de blockquote o marcador vira lixo no meio
    do texto ("evidência > contrária") e o assert falha por diagramação."""
    sem_citacao = re.sub(r"(?m)^\s*>\s?", "", text)
    return re.sub(r"\s+", " ", sem_citacao)


def _secao_do_protocolo() -> str:
    """O corpo da seção dona, do título até o próximo `### `."""
    texto = CANAIS.read_text(encoding="utf-8")
    inicio = texto.find(TITULO)
    assert inicio != -1, f"seção dona sumiu de {CANAIS.name}"
    fim = texto.find("\n### ", inicio + len(TITULO))
    return texto[inicio : fim if fim != -1 else len(texto)]


# Marcas do protocolo, na ordem em que aparecem no dono. Uma CÓPIA tem todas
# nesta sequência; um ponteiro legítimo ("o protocolo mora em X") não tem.
_MARCAS = ("VALIDADA", "FALHA", "INCONCLUSIVO", "testemunha", "osmose")


def _copia_do_protocolo(flat: str) -> bool:
    pos = -1
    for marca in _MARCAS:
        found = flat.find(marca, pos + 1)
        if found == -1:
            return False
        pos = found
    return True


class EstadosETransicoesTest(unittest.TestCase):
    """O bug do plano r2: o protocolo sabia concluir FALHA e INCONCLUSIVO, mas
    VALIDADA nascia por geração espontânea — osmose de bigode falso."""

    def test_os_tres_estados_existem_e_sao_fechados(self) -> None:
        """O conjunto é lido da PRIMEIRA COLUNA da tabela de estados — não do
        texto solto, senão `SENT` (evidência de label) entra como estado."""
        linhas = [
            linha
            for linha in _secao_do_protocolo().splitlines()
            if linha.startswith("| `")
        ]
        achados = [linha.split("|")[1].strip().strip("`") for linha in linhas]
        self.assertEqual(
            achados,
            list(ESTADOS),
            f"conjunto de estados deixou de ser fechado ou mudou de ordem: {achados}",
        )

    def test_cada_estado_tem_porta_de_entrada(self) -> None:
        """Estado sem condição de entrada é estado inalcançável — ou pior,
        alcançável por vontade própria do agente."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("prova o predicado por conta própria** | zero passa a ser confiável", flat)
        self.assertIn("controle expôs **testemunha** que a query filtrada não devolveu", flat)
        self.assertIn("todo o resto", flat)

    def test_protocolo_tem_os_quatro_passos_na_ordem(self) -> None:
        flat = _flat(_secao_do_protocolo())
        passos = (
            "rodar `B` sem `P`",
            "procurar **testemunha**",
            "testemunha existe e `B + P` não a devolveu → `FALHA`",
            "sem testemunha, ou controle também vazio → `INCONCLUSIVO`",
        )
        pos = [flat.find(p) for p in passos]
        for p, i in zip(passos, pos):
            self.assertNotEqual(i, -1, f"passo do protocolo ausente: {p}")
        self.assertEqual(pos, sorted(pos), "passos do protocolo fora de ordem")

    def test_controle_vazio_nao_aprova_por_osmose(self) -> None:
        flat = _flat(_secao_do_protocolo())
        self.assertIn("controle também vazio → `INCONCLUSIVO`", flat)
        self.assertIn("Nada é aprovado por osmose", flat)

    def test_resultado_nao_vazio_sem_prova_segue_inconclusivo(self) -> None:
        """Voltar mensagem não valida a assinatura: tem de vir prova."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("resultado não vazio sem prova independente", flat)


class EscopoDaAssinaturaTest(unittest.TestCase):
    def test_assinatura_nao_atravessa_host_nem_conta(self) -> None:
        flat = _flat(_secao_do_protocolo())
        self.assertIn("host/conector + conta ou caixa", flat)
        self.assertIn("**não** atravessa host nem conta", flat)

    def test_classe_do_argumento_separa_alias_de_endereco(self) -> None:
        """`from:me` reprovado não reprova `from:<endereço>` — foi o risco de
        canonizar o resultado em vez do protocolo."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("**classe** do argumento", flat)
        self.assertIn("trocar `from:me` por `from:<endereço>` cria", flat)

    def test_trocar_a_data_nao_cria_assinatura_nova(self) -> None:
        flat = _flat(_secao_do_protocolo())
        self.assertIn("Trocar a data não cria assinatura nova", flat)


class ProvaTest(unittest.TestCase):
    def test_query_nunca_e_testemunha_de_si_mesma(self) -> None:
        flat = _flat(_secao_do_protocolo())
        self.assertIn("query nunca é testemunha de si mesma", flat)

    def test_prova_na_granularidade_da_mensagem(self) -> None:
        flat = _flat(_secao_do_protocolo())
        self.assertIn("granularidade da **mensagem**", flat)
        self.assertIn("Agregado de thread não prova mensagem", flat)
        self.assertIn("ID de label opaco não vira nome", flat)

    def test_prova_declarada_por_operador(self) -> None:
        """`SENT` cobre `in:sent` e mais nada — cada predicado tem sua prova.
        A perna da COMPOSIÇÃO morria calada antes do gate r1."""
        flat = _flat(_secao_do_protocolo())
        for par in (
            "`in:sent` ← `SENT` em `labelIds`",
            "`from:<endereço>` ← header `From`",
            "predicado temporal ← timestamp da mensagem",
            "composição ← prova de cada componente aplicável",
        ):
            self.assertIn(par, flat, f"prova não declarada para: {par}")

    def test_varredura_exaustiva_tem_definicao(self) -> None:
        """"Li bastante" não é "li tudo": sem fim declarado pelo conector, o
        zero continua inconclusivo."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("paginar até o conector declarar fim", flat)
        self.assertIn("nem exaustiva foi, então segue `INCONCLUSIVO`", flat)

    def test_varredura_exige_aplicar_o_predicado_localmente(self) -> None:
        """Metade que morria calada (gate r1): varrer sem aplicar o predicado
        não responde pergunta nenhuma."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("aplicar o predicado localmente", flat)
        self.assertIn("As duas metades são obrigatórias", flat)

    def test_zero_so_e_confiavel_pelos_dois_caminhos(self) -> None:
        flat = _flat(_secao_do_protocolo())
        self.assertIn("**Zero só é confiável** com assinatura `VALIDADA`, ou por `VAZIO CONFIRMADO`", flat)

    def test_vazio_confirmado_nao_valida_a_assinatura(self) -> None:
        """Varrer localmente responde ESTE briefing; não prova nada sobre o
        conector. Confundir os dois reabriria a porta pelo outro lado."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("**Não valida a assinatura** — varrer não prova nada sobre o conector", flat)


class OrcamentoTest(unittest.TestCase):
    def test_teto_por_assinatura_e_teto_global(self) -> None:
        """Só "uma por assinatura" ainda permite 4 contas × 4 assinaturas num
        canal que mede 22–28s por chamada."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("**uma** validação por assinatura **por briefing**", flat)
        self.assertIn("**três validações novas por briefing**", flat)

    def test_inconclusivo_volta_a_fila_e_validada_nao(self) -> None:
        """Sem isso o limbo é permanente — e não estava dito se dava pra
        tentar de novo (gate r1, achado 3)."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("`VALIDADA` e `FALHA` não voltam à fila até invalidar", flat)
        self.assertIn("`INCONCLUSIVO` **volta**", flat)

    def test_fila_tem_criterio_deterministico(self) -> None:
        """"Rotação" sem critério deixa o agente literal repetir as mesmas três
        pra sempre — hamster com SLA."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("Fila determinística: **primeiro a nunca tentada**", flat)
        self.assertIn("empate, a de registro mais antigo", flat)

    def test_tentativa_inconclusiva_tambem_e_registrada(self) -> None:
        """O registro É o estado persistido; tentativa não registrada se repete
        amanhã e a rotação não sai do lugar."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("**Registrar também o `INCONCLUSIVO`**", flat)

    def test_prioridade_do_teto_declara_a_relacao(self) -> None:
        """Nem presença nem posição bastam: "cobertura DEPOIS DE dirigida"
        preserva as duas posições textuais e passaria (gate r2 mutou isto).
        O que se ancora é o CONECTIVO entre os dois termos."""
        flat = _flat(_secao_do_protocolo())
        i_cobertura = flat.find("braço da política de cobertura")
        i_dirigida = flat.find("busca dirigida")
        self.assertNotEqual(i_cobertura, -1, "prioridade do teto sumiu")
        self.assertNotEqual(i_dirigida, -1, "prioridade do teto sumiu")
        self.assertLess(i_cobertura, i_dirigida, "termos da prioridade fora de ordem")
        entre = flat[i_cobertura + len("braço da política de cobertura") : i_dirigida].strip()
        self.assertEqual(
            entre,
            "antes de",
            f"a relação entre os termos da prioridade não é 'antes de': {entre!r}",
        )


class DegradacaoVisivelTest(unittest.TestCase):
    def test_braco_inconclusivo_e_nomeado_na_linha_de_cobertura(self) -> None:
        flat = _flat(CANAIS.read_text(encoding="utf-8"))
        self.assertIn("Braço em `INCONCLUSIVO` é nomeado na mesma linha", flat)
        self.assertIn("nunca o que só foi tentado", flat)

    def test_completude_e_dona_da_montagem_nao_dos_canais(self) -> None:
        """Dois donos semânticos de `--mark-done` seria contrato novo em
        silêncio — os canais declaram, a montagem decide."""
        self.assertIn(
            "Completude do briefing é decidida por `briefing-montagem.md`, nunca aqui",
            _flat(_secao_do_protocolo()),
        )
        flat_montagem = _flat(MONTAGEM.read_text(encoding="utf-8"))
        self.assertIn("este módulo é o dono da completude", flat_montagem)
        self.assertIn("desde que a degradação tenha sido nomeada", flat_montagem)

    def test_braco_inconclusivo_nao_impede_o_dia(self) -> None:
        flat = _flat(MONTAGEM.read_text(encoding="utf-8"))
        self.assertIn("mesma regra da indisponibilidade declarada", flat)


class RegistroTest(unittest.TestCase):
    SCHEMA = (
        "validado_em | host/conector | conta ou caixa | assinatura normalizada "
        "| predicado exato testado | veredito | evidência"
    )

    def test_schema_identico_nos_dois_lados(self) -> None:
        """Dono e template divergindo em silêncio já foi bug aqui (#195)."""
        for nome, path in (("template", FILE_TEMPLATES), ("canais", CANAIS)):
            self.assertIn(self.SCHEMA, _flat(path.read_text(encoding="utf-8")), f"schema ausente em {nome}")
        self.assertIn("## Compatibilidade da busca", _flat(FILE_TEMPLATES.read_text(encoding="utf-8")))

    def test_assinatura_normalizada_e_o_que_casa(self) -> None:
        """Sem ela `after:27/07` e `after:28/07` viram assinaturas diferentes e
        a validação nunca se reaproveita (gate r1, achado 2)."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("é o que casa entre briefings", flat)
        self.assertIn("operador + classe do argumento + sozinho/composto", flat)

    def test_registro_e_log_append_only_com_ultima_linha_valendo(self) -> None:
        """`INCONCLUSIVO` volta à fila e é registrado — logo a mesma assinatura
        ganha linhas repetidas, e sem regra de precedência não se sabe qual
        veredito vale nem qual data ordena a fila (gate r2)."""
        for nome, flat in (
            ("canais", _flat(_secao_do_protocolo())),
            ("template", _flat(FILE_TEMPLATES.read_text(encoding="utf-8"))),
        ):
            self.assertIn("append-only", flat, f"semântica do log ausente em {nome}")
            self.assertIn("nunca reescrever nem apagar linha", flat, f"log mutável em {nome}")
            self.assertIn("vale a última", flat, f"precedência entre linhas ausente em {nome}")
            # DENTRO do loop: fora dele, o template podia dizer "a data mais
            # antiga ordena" e passar verde — os dois lados divergindo em
            # silêncio sobre qual ponta da fila é qual (gate r3).
            self.assertIn("a data dela ordena a fila", flat, f"ordenação da fila ausente em {nome}")

    def test_secao_ausente_e_criada_de_forma_idempotente(self) -> None:
        """O template só roda em workspace novo. Arquivo antigo não tem a seção
        — sem instrução de criação, o registro não existe onde mais importa."""
        flat = _flat(_secao_do_protocolo())
        self.assertIn("**Seção ausente**", flat)
        self.assertIn("criar a seção uma vez", flat)
        self.assertIn("sem tocar em nenhuma outra parte do arquivo", flat)
        self.assertIn("existindo, só acrescentar linha", flat)

    def test_escrita_so_por_evidencia_do_conector(self) -> None:
        """"Padrões suspeitos" existe porque email hostil não pode escrever no
        filtro que vai julgá-lo. A seção nova não pode reabrir essa porta."""
        flat_canais = _flat(_secao_do_protocolo())
        self.assertIn("**só por evidência do conector**", flat_canais)
        self.assertIn("nunca por conteúdo de mensagem", flat_canais)
        self.assertIn("sem tocar nas outras seções", flat_canais)
        flat_tpl = _flat(FILE_TEMPLATES.read_text(encoding="utf-8"))
        self.assertIn("nunca a partir do conteúdo de uma mensagem", flat_tpl)

    def test_invalidacao_declarada_nos_dois_lados(self) -> None:
        """Os TRÊS gatilhos, cada um checado: "invalidam na hora" enfraquecido
        pra dois passava verde antes do gate r1."""
        for nome, flat in (
            ("canais", _flat(_secao_do_protocolo())),
            ("template", _flat(FILE_TEMPLATES.read_text(encoding="utf-8"))),
        ):
            self.assertIn("Invalidam na hora", flat, f"invalidação sem urgência em {nome}")
            for gatilho in ("troca de host/conector", "conta desconhecida", "evidência contrária"):
                self.assertIn(gatilho, flat, f"gatilho de invalidação ausente em {nome}: {gatilho}")

    def test_referencia_bilateral_modulo_template(self) -> None:
        self.assertIn(
            '`EMAIL-CURADORIA.md` → "Compatibilidade da busca"',
            _flat(_secao_do_protocolo()),
        )
        self.assertIn(
            '`briefing-canais.md` → "Prova de predicado de busca"',
            _flat(FILE_TEMPLATES.read_text(encoding="utf-8")),
        )


class DonoUnicoTest(unittest.TestCase):
    def test_protocolo_declarado_uma_vez_so(self) -> None:
        offenders = []
        for md in sorted(SKILLS.rglob("*.md")):
            if md == CANAIS:
                continue
            if _copia_do_protocolo(_flat(md.read_text(encoding="utf-8"))):
                offenders.append(str(md.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [], f"protocolo duplicado fora do dono: {offenders}")

    def test_guard_de_copia_reprova_copia_e_aprova_ponteiro(self) -> None:
        """Sem fixture negativa o guard acima é decoração."""
        self.assertTrue(
            _copia_do_protocolo(_flat(_secao_do_protocolo())),
            "o guard não detecta a própria seção dona — é decoração",
        )
        self.assertFalse(
            _copia_do_protocolo(
                _flat(
                    "Predicado sem assinatura VALIDADA segue o protocolo de "
                    '"Prova de predicado de busca" em `briefing-canais.md`.'
                )
            ),
            "ponteiro legítimo confundido com cópia",
        )

    def test_regra_antiga_do_alias_nao_sobreviveu(self) -> None:
        """A frase pontual do caveat virou ponteiro pro protocolo; sobrevivente
        em outro arquivo seria a mesma regra com dois donos."""
        morta = "nunca confiar em alias sem um teste positivo"
        offenders = [
            str(md.relative_to(REPO_ROOT))
            for md in sorted(SKILLS.rglob("*.md"))
            if morta in md.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [], f"regra antiga sobreviveu em: {offenders}")


# Endereços ilustrativos legítimos (placeholder, exemplo de doc, pattern de
# ruído). Qualquer OUTRO endereço concreto em skills/ é identidade de uma
# pessoa real vazando pro produto que vai pra todo mundo.
_ENDERECOS_ILUSTRATIVOS = frozenset(
    {
        "SEUEMAIL@gmail.com",
        "ana@acme.com",
        "email-de-feedback@dominio-do-produto.com",
        "fulano@contador.com",
        "marketing@servico.com",
        "noreply@github.com",
    }
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _enderecos_pessoais(texto: str) -> set[str]:
    return {e for e in _EMAIL_RE.findall(texto) if e not in _ENDERECOS_ILUSTRATIVOS}


class SemEnderecoPessoalTest(unittest.TestCase):
    """Critério 3 da #236. A linha 89 do canais listava as 4 contas do dono —
    todo usuário do Prumo lia os emails do Tharso no próprio módulo."""

    def test_nenhum_endereco_pessoal_em_skills(self) -> None:
        """Varre TODO arquivo de texto de `skills/`, não só `*.md`: o guard
        prometia `skills/` e percorria markdown — e existe HTML lá (gate r1)."""
        offenders: dict[str, set[str]] = {}
        lidos: set[Path] = set()
        for path in sorted(SKILLS.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            try:
                texto = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, ValueError):
                continue  # binário (fontes .otf) não carrega endereço legível
            lidos.add(path)
            achados = _enderecos_pessoais(texto)
            if achados:
                offenders[str(path.relative_to(REPO_ROOT))] = achados
        self.assertEqual(offenders, {}, f"endereço pessoal em módulo canônico: {offenders}")

        # Contagem não prova cobertura: 49 markdown ≥ 2 HTML deixava a mutação
        # `rglob("*.md")` passar verde (gate r2). O que se afirma é que ESTES
        # paths foram lidos.
        htmls = set(SKILLS.rglob("*.html"))
        self.assertTrue(htmls, "fixture do próprio guard: sumiram os HTML de skills/")
        self.assertEqual(
            htmls - lidos,
            set(),
            "o guard deixou de ler arquivos não-markdown de skills/",
        )

    def test_guard_pega_o_endereco_que_estava_la(self) -> None:
        """Fixture negativa com a linha REAL que existia antes da correção."""
        antes = (
            "A inbox agrega 4 contas (tharso@gmail.com, tharso@brise.cloud, "
            "tharso@brise.science, tharso@tharso.com). Uma query cobre todas."
        )
        self.assertEqual(len(_enderecos_pessoais(antes)), 4, "o guard não pega a linha original")
        self.assertEqual(
            _enderecos_pessoais("escreve pra fulano@contador.com quando houver item fiscal"),
            set(),
            "endereço ilustrativo não pode ser acusado",
        )

    def test_contas_monitoradas_viraram_a_fonte(self) -> None:
        flat = _flat(CANAIS.read_text(encoding="utf-8"))
        self.assertIn('`EMAIL-CURADORIA.md` → "Contas monitoradas"', flat)
        self.assertIn("não some em silêncio", flat)


class RegistroArquiteturalTest(unittest.TestCase):
    """O contrato mudou no módulo e a projeção dele ficou pra trás — dito de
    outro jeito, o registro descrevendo produto que não existe mais. Aconteceu
    aqui (DECISIONS e CHANGELOG anunciavam "três estados fechados" depois de o
    quarto entrar) e na #258 (índice do DECISIONS com entrada fantasma)."""

    def test_os_quatro_resultados_chegam_aos_registros(self) -> None:
        for nome, path, marco in (
            ("DECISIONS.md", REPO_ROOT / "DECISIONS.md", "#236 prova de predicado"),
            ("CHANGELOG.md", REPO_ROOT / "CHANGELOG.md", "Prova de predicado de busca"),
        ):
            flat = _flat(path.read_text(encoding="utf-8"))
            self.assertIn(marco, flat, f"entrada da #236 sumiu de {nome}")
            for estado in ESTADOS:
                self.assertIn(
                    f"`{estado}`",
                    flat,
                    f"{nome} não registra o resultado {estado} — projeção defasada do contrato",
                )

    def test_registros_declaram_os_dois_eixos(self) -> None:
        """Listar os 4 lado a lado seria pior que o texto antigo: sugeriria que
        `VAZIO CONFIRMADO` é estado de assinatura, que é justo o que ele não é."""
        for nome, path in (
            ("DECISIONS.md", REPO_ROOT / "DECISIONS.md"),
            ("CHANGELOG.md", REPO_ROOT / "CHANGELOG.md"),
        ):
            # Sem os `*`: a ênfase cai em lugar diferente nos dois arquivos e
            # o assert não pode depender de diagramação.
            flat = _flat(path.read_text(encoding="utf-8")).replace("*", "")
            self.assertIn("dois eixos", flat, f"{nome} não separa assinatura de resposta")
            self.assertIn("não valida a assinatura", flat, f"{nome} omite a ressalva do 4º")


if __name__ == "__main__":
    unittest.main()
