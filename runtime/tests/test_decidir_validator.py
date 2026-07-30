"""O validador de cards do `decidir` (#287).

Um briefing real gastou 186 segundos — 28% do relógio — instalando Chromium
para conferir 29 cards. A instrução que provocou isso mandava contar
`<article class="card">` "renderizados", e essa string aparece UMA vez no
arquivo, dentro do template literal: um `grep` devolve 1 com 29 cards ou com
zero. Lida ao pé da letra, ela embutia execução de JS.

A troca: em vez de detectar o sintoma depois de pintar pixels, validar a
CAUSA. Tag crua num campo de markup é o que engole os cards seguintes —
barrada na origem, o engolimento não acontece.

Os testes de contrato (que a skill proíbe instalar dependência) rodam sempre.
Os do validador exigem `node` e pulam sem ele — mas o CI **instala** Node de
propósito: pular lá seria cobertura fantasma, verde significando "não
testamos o software novo". Ambiente de CI e briefing do usuário são coisas
diferentes; a proibição vale no segundo.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DECIDIR = REPO_ROOT / "skills" / "decidir"
VALIDADOR = DECIDIR / "validate-cards.mjs"
TEMPLATE = DECIDIR / "assets" / "template.html"
SKILL = DECIDIR / "SKILL.md"

NODE = shutil.which("node")

SECAO = "{id:'emails', num:1, title:'Emails'},"


def _gerar(sections: str, points: str) -> Path:
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__SECTIONS__*/", sections).replace("/*__POINTS__*/", points)
    destino = Path(tempfile.mkdtemp()) / "decidir.html"
    destino.write_text(html, encoding="utf-8")
    return destino


def _validar(path: Path) -> tuple[int, dict]:
    r = subprocess.run(
        [NODE, str(VALIDADOR), str(path), "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        return r.returncode, json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.returncode, {"stdout": r.stdout, "stderr": r.stderr}


class ContratoDaSkillTest(unittest.TestCase):
    """Roda sem node: é o texto que impede o desvio de 186 segundos."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = " ".join(SKILL.read_text(encoding="utf-8").split())

    def test_proibe_instalar_dependencia_para_validar(self) -> None:
        self.assertIn("NUNCA instalar browser, runtime ou dependência", self.skill)
        self.assertIn("npm i", self.skill)

    def test_desarma_o_se_houver_browser(self) -> None:
        # A frase antiga foi lida como licença para FAZER existir um browser.
        self.assertIn(
            'aproveitar um que já exista, nunca fabricá-lo',
            self.skill,
        )

    def test_avisa_que_grep_de_article_nao_conta_nada(self) -> None:
        # A armadilha original, nomeada para não voltar.
        self.assertIn("essa string existe uma única vez no arquivo", self.skill)

    def test_article_card_aparece_uma_vez_so_no_template(self) -> None:
        # A premissa do aviso acima. Se um dia o template ganhar `<article
        # class="card">` estático, a instrução volta a fazer sentido e este
        # teste avisa antes de a skill ficar mentindo.
        bruto = TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(bruto.count('<article class="card"'), 1)

    def test_skill_aponta_o_validador(self) -> None:
        self.assertIn("validate-cards.mjs", self.skill)

    def test_template_avisa_quando_a_contagem_diverge(self) -> None:
        tpl = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("querySelectorAll('article.card').length", tpl)
        self.assertIn("não renderizaram", tpl)

    def test_aviso_compara_contra_TODOS_os_points(self) -> None:
        # Achado do Codex: excluir os cards de seção órfã do "esperado" fazia
        # o card que some em silêncio se absolver sozinho — saidos ===
        # esperados — que é exatamente o defeito a denunciar.
        tpl = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("const esperados = POINTS.length;", tpl)
        self.assertNotIn(
            "const esperados = POINTS.filter(p => SECTIONS.some(s => s.id === p.sec)).length;",
            tpl,
            "o esperado voltou a excluir órfãos — o card sumido se absolve",
        )

    def test_comentario_do_template_bate_com_o_schema(self) -> None:
        # O comentário dizia que `title` aceita markup e omitia proposta e
        # sugestao: quem escreve o card lê ali, não no validador.
        tpl = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("`title` é TEXTO PURO", tpl)
        self.assertIn("validate-cards.mjs", tpl)

    def test_ci_roda_os_testes_do_validador(self) -> None:
        # `skipUnless(node)` é razoável na máquina de alguém, mas no CI vira
        # cobertura fantasma: verde significando "não testamos o software
        # novo" (Codex). O workflow precisa instalar node.
        ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("setup-node", ci)


@unittest.skipUnless(NODE, "node ausente — o validador é opcional por desenho")
class ValidadorTest(unittest.TestCase):
    def test_card_canonico_da_documentacao_aprova(self) -> None:
        # `exemplos-de-cards.md` usa <span class="ref"> e <span class="q">.
        # Um scanner que barrasse todo `<` reprovaria o exemplo do próprio
        # produto — por isso a allowlist, não o banimento.
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'Acme pede retorno',
                 contexto: 'Thread ontem. <span class="ref">de: ana@acme.com</span> <span class="q">"mantem o dia 30?"</span>',
                 actions:[{key:'reply',label:'Responder',tone:'green',effect:'draft_reply'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 0, r)
        self.assertTrue(r["ok"])
        self.assertEqual(r["renderizaveis"], 1)

    def test_tag_crua_reprova(self) -> None:
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 contexto: 'o assunto era <title> e sumiu',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("<title>", " ".join(r["erros"]))

    def test_menor_que_solto_tambem_reprova(self) -> None:
        # "a < b" não parece tag, mas o parser do browser engole igual.
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 contexto: 'prazo < 3 dias',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("não escapado", " ".join(r["erros"]))

    def test_secao_orfa_reprova(self) -> None:
        # O silêncio mais caro: `if (!pts.length) return;` faz o card sumir
        # sem erro e sem console.
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'nao_existe', type:'despacho', title:'x', contexto:'y',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("SILÊNCIO", " ".join(r["erros"]))

    def test_id_duplicado_reprova(self) -> None:
        # Dois cards com o mesmo id: o segundo sobrescreve o estado do
        # primeiro no localStorage e o despacho vira loteria.
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'a', contexto:'y', actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },
               { id:'7', sec:'emails', type:'despacho', title:'b', contexto:'y', actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("id duplicado", " ".join(r["erros"]))

    def test_base64_com_quebra_reprova(self) -> None:
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y',
                 conteudo_b64: 'YWJj\\nZGVm',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("76 colunas", " ".join(r["erros"]))

    def test_chave_de_acao_repetida_reprova(self) -> None:
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y',
                 actions:[{key:'r',label:'A',tone:'green',effect:'archive'},
                          {key:'r',label:'B',tone:'amber',effect:'snooze'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("repetida", " ".join(r["erros"]))

    def test_tipo_invalido_reprova(self) -> None:
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despachoo', title:'x', contexto:'y' },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)

    def test_arquivo_ilegivel_sai_dois_nao_um(self) -> None:
        # Não conseguir validar ≠ reprovar. Confundir os dois faria o agente
        # descartar um HTML bom por causa de um erro de leitura.
        vazio = Path(tempfile.mkdtemp()) / "x.html"
        vazio.write_text("<html>sem literais</html>", encoding="utf-8")
        code, _ = _validar(vazio)
        self.assertEqual(code, 2)

    def test_injecao_por_atributo_reprova(self) -> None:
        # `id` vai para dentro de `data-pt="${p.id}"`. Proibir só `<`/`>`
        # não impedia fechar a aspas e abrir um handler (Codex).
        path = _gerar(
            SECAO,
            """{ id:'7" onclick="alert(1)', sec:'emails', type:'despacho', title:'x', contexto:'y',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("ATRIBUTO", " ".join(r["erros"]))

    def test_handler_dentro_de_tag_permitida_reprova(self) -> None:
        # A allowlist antiga olhava o nome da tag e a classe, e deixava
        # passar qualquer outro atributo.
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 contexto: 'oi <span class="ref" onclick="alert(1)">x</span>',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("onclick", " ".join(r["erros"]))

    def test_atributo_sem_aspas_reprova(self) -> None:
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 contexto: 'oi <span class=ref>x</span>',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        self.assertEqual(_validar(path)[0], 1)

    def test_tag_nao_fechada_reprova(self) -> None:
        for contexto in ("oi <strong x", "oi <strong>x", "oi </em>x"):
            path = _gerar(
                SECAO,
                f"""{{ id:'7', sec:'emails', type:'despacho', title:'x',
                     contexto: '{contexto}',
                     actions:[{{key:'r',label:'R',tone:'green',effect:'archive'}}] }},""",
            )
            self.assertEqual(_validar(path)[0], 1, contexto)

    def test_tone_fora_do_enum_reprova(self) -> None:
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y',
                 badges:[{label:'P1', tone:'neon'}],
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 1)
        self.assertIn("enum", " ".join(r["erros"]))

    def test_getter_hostil_nao_trava_o_validador(self) -> None:
        # O timeout do `vm` termina quando `runInContext` retorna; um getter
        # rodaria DEPOIS, sem timeout, na hora de ler o campo. Por isso o
        # JSON.stringify acontece DENTRO do contexto (Codex).
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 get contexto() { for(;;){} },
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, _ = _validar(path)
        self.assertIn(code, (1, 2), "o validador não pode congelar num getter")

    def test_roda_em_path_com_espaco(self) -> None:
        # O entry point comparava URL percent-encoded com path cru: em pasta
        # com espaço o processo saía 0 SEM VALIDAR NADA (Codex). O bug é do
        # caminho DO VALIDADOR, então é ELE que precisa mudar de pasta —
        # mover só o HTML deixaria o teste verde com a comparação defeituosa.
        base = Path(tempfile.mkdtemp()) / "pasta com espaço e #"
        base.mkdir()
        copia = base / "validate-cards.mjs"
        copia.write_text(VALIDADOR.read_text(encoding="utf-8"), encoding="utf-8")

        alvo = _gerar(
            SECAO,
            """{ id:'7', sec:'nao_existe', type:'despacho', title:'x', contexto:'y',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        r = subprocess.run(
            [NODE, str(copia), str(alvo), "--json"], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(
            r.returncode, 1, f"saiu {r.returncode} sem validar — entry point morto: {r.stdout}"
        )

    def test_contexto_do_vm_nao_expoe_process(self) -> None:
        # Prova o que prova: `process` não está no contexto. NÃO prova sandbox
        # — `node:vm` não é fronteira de segurança, e o cabeçalho do script
        # diz isso. O artefato é do agente, não de terceiro.
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 contexto: (typeof process === 'undefined' ? 'sem process' : 'TEM PROCESS'),
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 0, r)


class TiposTest(unittest.TestCase):
    """O validador certificava artefato que não abre (Codex, r10 e r11)."""

    def _reprova(self, points: str, trecho: str = "", sections: str = SECAO) -> None:
        code, r = _validar(_gerar(sections, points))
        self.assertEqual(code, 1, f"passou: {r}")
        if trecho:
            self.assertIn(trecho, " ".join(r["erros"]))

    def test_badges_string_reprova(self) -> None:
        # `.map()` numa string mata o render ANTES de desenhar qualquer card
        # e antes do aviso visual: sem card e sem alarme.
        self._reprova(
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y', badges:'abc',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
            "não é lista",
        )

    def test_contexto_objeto_reprova(self) -> None:
        self._reprova(
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:{a:1},
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
            "[object Object]",
        )

    def test_campos_irmaos_com_tipo_errado_reprovam(self) -> None:
        # Corrigir só `title`/`contexto` deixava os irmãos passando (Codex).
        casos = {
            "evidencia": """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y', evidencia:{a:1},
                             actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
            "badge.label": """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y',
                               badges:[{label:{a:1}, tone:'red'}],
                               actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
            "option.desc": """{ id:'7', sec:'emails', type:'escolha', title:'x', contexto:'y',
                               options:[{key:'a', label:'A', desc:{a:1}}] },""",
            "badges lista de lista": """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y',
                                        badges:[[]],
                                        actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        }
        for nome, pts in casos.items():
            with self.subTest(campo=nome):
                self._reprova(pts)

    def test_section_title_com_tipo_errado_reprova(self) -> None:
        self._reprova(
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
            sections="{id:'emails', num:1, title:{a:1}},",
        )

    def test_acao_sem_label_reprova(self) -> None:
        self._reprova(
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y',
                 actions:[{key:'r',tone:'green',effect:'archive'}] },""",
            "obrigatório",
        )

    def test_campo_obrigatorio_ausente_reprova(self) -> None:
        for pts in (
            """{ id:'7', sec:'emails', type:'despacho', contexto:'y',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        ):
            self._reprova(pts, "obrigatório")

    def test_colecao_obrigatoria_vazia_reprova(self) -> None:
        # Card sem ação nenhuma existe na tela e não decide nada.
        self._reprova(
            """{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y', actions:[] },""",
            "não oferece decisão",
        )
        self._reprova(
            """{ id:'7', sec:'emails', type:'escolha', title:'x', contexto:'y', options:[] },""",
            "não oferece decisão",
        )

    def test_despacho_sem_actions_reprova(self) -> None:
        self._reprova("""{ id:'7', sec:'emails', type:'despacho', title:'x', contexto:'y' },""")

    def test_escolha_sem_options_reprova(self) -> None:
        self._reprova("""{ id:'7', sec:'emails', type:'escolha', title:'x', contexto:'y' },""")


class GramaticaFechadaTest(unittest.TestCase):
    """Os mutantes que o Codex executou e que passavam."""

    def _reprova(self, contexto: str) -> None:
        code, r = _validar(
            _gerar(
                SECAO,
                f"""{{ id:'7', sec:'emails', type:'despacho', title:'x',
                     contexto: '{contexto}',
                     actions:[{{key:'r',label:'R',tone:'green',effect:'archive'}}] }},""",
            )
        )
        self.assertEqual(code, 1, f"'{contexto}' passou: {r}")

    def test_span_sem_class_reprova(self) -> None:
        self._reprova("oi <span>x</span>")

    def test_atributo_repetido_reprova(self) -> None:
        self._reprova('oi <span class=\"ref\" class=\"q\">x</span>')

    def test_atributo_em_fechamento_reprova(self) -> None:
        self._reprova('oi <span class=\"ref\">x</span onclick=\"alert(1)\">')

    def test_espaco_depois_do_menor_reprova(self) -> None:
        self._reprova("oi < strong>x")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
