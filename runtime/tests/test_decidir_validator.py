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
Os do validador exigem `node`; sem ele, pulam — instalar Node para testar o
script que existe para não instalar nada seria piada de mau gosto.
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

    def test_validador_nao_toca_a_rede_nem_o_disco_do_usuario(self) -> None:
        # O sandbox `vm` roda sem `process` e sem `require`: um literal
        # malicioso no artefato não vira execução.
        path = _gerar(
            SECAO,
            """{ id:'7', sec:'emails', type:'despacho', title:'x',
                 contexto: (typeof process === 'undefined' ? 'sem process' : 'TEM PROCESS'),
                 actions:[{key:'r',label:'R',tone:'green',effect:'archive'}] },""",
        )
        code, r = _validar(path)
        self.assertEqual(code, 0, r)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
