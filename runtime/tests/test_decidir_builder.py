"""O builder de cards do `decidir` (#321).

O relatório de campo de 03/08 mediu o custo de não existir um "preencher
template" barato: o agente escreveu um gerador Python de 22 KB do zero —
o maior bloco único de tempo do briefing (2min04s) e a maior fatia dos
114k tokens de output. O template já tinha marcadores de injeção; faltava
o executor fixo.

O contrato: o agente autora um `cards.json` (JSON ESTRITO — a alternativa
que a #287 adiou como decisão de produto) e `build-cards.mjs` injeta nos
marcadores, valida com o MESMO `validar()` do validate-cards.mjs (fonte
única de verdade — o builder não duplica regra) e se recusa a escrever
quando reprova. Artefato inválido não ganha arquivo.

Como no validador: os testes de contrato textual rodam sempre; os do
builder exigem `node` e pulam sem ele — mas o CI instala Node de
propósito (cobertura fantasma é verde significando "não testamos").
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DECIDIR = REPO_ROOT / "skills" / "decidir"
BUILDER = DECIDIR / "build-cards.mjs"
VALIDADOR = DECIDIR / "validate-cards.mjs"
TEMPLATE = DECIDIR / "assets" / "template.html"
SKILL = DECIDIR / "SKILL.md"
EXEMPLOS = DECIDIR / "references" / "exemplos-de-cards.md"
MONTAGEM = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-montagem.md"

NODE = shutil.which("node")

SCHEMA = "prumo_decidir_cards.v1"

# Os 11 placeholders do template + os 2 marcadores de dados. Se o template
# ganhar um placeholder novo, este teste quebra ANTES de o builder entregar
# HTML com `__X__` cru pro usuário.
PLACEHOLDERS = [
    "__DOC_TITLE__",
    "__KICKER__",
    "__HEADLINE__",
    "__META__",
    "__INTRO__",
    "__HOWTO__",
    "__FINALE_TITLE__",
    "__FINALE_TEXT__",
    "__FINALE_HINT__",
    "__STORAGE_KEY__",
    "__REPORT_TITLE__",
]
MARCADORES = ["/*__SECTIONS__*/", "/*__POINTS__*/"]


def _doc() -> dict:
    return {
        "title": "Decidir — teste",
        "kicker": "PRUMO / DECIDIR",
        "headline": "Despacho de teste",
        "meta": "03/08/2026 · rodada de teste",
        "intro": "Contexto do documento de teste.",
        "howto": "Despache item a item e copie as respostas.",
        "finale_title": "Fim",
        "finale_text": "Copie as respostas e cole na conversa.",
        "finale_hint": "O bloco JSON volta pro Prumo executar.",
        "storage_key": "prumo-decidir-2026-08-03-1200-t3st",
        "report_title": "Respostas do teste",
    }


def _cards(**overrides) -> dict:
    base = {
        "schema": SCHEMA,
        "doc": _doc(),
        "sections": [{"id": "emails", "num": 1, "title": "Emails"}],
        "points": [
            {
                "id": "1",
                "sec": "emails",
                "type": "despacho",
                "title": "Email de teste",
                "contexto": "Contexto com <strong>markup</strong> permitido.",
                "actions": [
                    {"key": "archive", "label": "Arquivar", "tone": "slate", "effect": "archive"}
                ],
            },
            {
                "id": "2",
                "sec": "emails",
                "type": "escolha",
                "title": "Escolha de teste",
                "contexto": "Duas opções no card.",
                "options": [
                    {"key": "a", "label": "A", "desc": "opção A", "rec": True},
                    {"key": "b", "label": "B", "desc": "opção B"},
                ],
            },
        ],
    }
    base.update(overrides)
    return base


def _build(conteudo, *flags: str) -> tuple[subprocess.CompletedProcess, Path]:
    """Escreve `conteudo` (dict → JSON, str → cru) e roda o builder."""
    pasta = Path(tempfile.mkdtemp())
    origem = pasta / "cards.json"
    if isinstance(conteudo, dict):
        origem.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    else:
        origem.write_text(conteudo, encoding="utf-8")
    destino = pasta / "decidir.html"
    r = subprocess.run(
        [NODE, str(BUILDER), str(origem), str(destino), *flags],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return r, destino


def _validar_saida(path: Path) -> dict:
    r = subprocess.run(
        [NODE, str(VALIDADOR), str(path), "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(r.stdout)


class ContratoDoBuilderTest(unittest.TestCase):
    """Roda sem node: o texto que ancora o contrato de autoria em JSON."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = " ".join(SKILL.read_text(encoding="utf-8").split())

    def test_builder_existe(self) -> None:
        self.assertTrue(BUILDER.exists(), "skills/decidir/build-cards.mjs não existe")

    def test_skill_aponta_o_builder_e_o_schema(self) -> None:
        # Quem gera lê a skill. Sem o ponteiro, o agente volta a escrever o
        # gerador de 22 KB — o custo que a #321 existe pra matar.
        self.assertIn("build-cards.mjs", self.skill)
        self.assertIn("cards.json", self.skill)
        self.assertIn(SCHEMA, self.skill)

    def test_template_aponta_o_builder(self) -> None:
        # O outro lugar onde quem preenche lê: o comentário do template.
        tpl = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("build-cards.mjs", tpl)

    def test_montagem_aponta_o_caminho_novo(self) -> None:
        # A rota do briefing (F3) é quem dispara a geração — se ela seguir
        # mandando "preencher template.html" sem o builder, nada muda.
        montagem = MONTAGEM.read_text(encoding="utf-8")
        self.assertIn("cards.json", montagem)
        self.assertIn("build-cards.mjs", montagem)

    def test_exemplos_sao_json_estrito(self) -> None:
        # A #287 previu: mudar o contrato de autoria muda a documentação.
        # Exemplo em JS-literal ensinaria o formato que o builder recusa.
        texto = EXEMPLOS.read_text(encoding="utf-8")
        # "```js" é prefixo de "```json" — a fence precisa fechar com \n.
        self.assertNotIn("```js\n", texto, "exemplo em JS-literal — o builder fala JSON estrito")
        blocos = re.findall(r"```json\n(.*?)```", texto, re.DOTALL)
        self.assertTrue(blocos, "exemplos-de-cards.md sem nenhum bloco ```json")
        for i, bloco in enumerate(blocos):
            try:
                json.loads(bloco)
            except json.JSONDecodeError as e:
                self.fail(f"bloco json #{i + 1} de exemplos-de-cards.md não parseia: {e}")

    def test_placeholders_do_teste_batem_com_o_template(self) -> None:
        # A lista PLACEHOLDERS deste arquivo é a premissa dos testes de
        # resíduo. Se o template ganhar/perder placeholder, quebrar AQUI.
        tpl = TEMPLATE.read_text(encoding="utf-8")
        for token in PLACEHOLDERS + MARCADORES:
            self.assertIn(token, tpl, f"template sem {token}")
        # `__ASSIM__` é o exemplo ilustrativo do comentário do template;
        # `__SECTIONS__`/`__POINTS__` são o miolo dos marcadores de dados.
        conhecidos = set(PLACEHOLDERS) | {"__ASSIM__", "__SECTIONS__", "__POINTS__"}
        extras = set(re.findall(r"__[A-Z][A-Z_]*__", tpl)) - conhecidos
        self.assertFalse(extras, f"placeholders fora da lista do teste: {extras}")


@unittest.skipUnless(NODE, "node ausente — builder é opcional por desenho")
class BuilderTest(unittest.TestCase):
    def test_caminho_feliz_gera_valida_e_escreve(self) -> None:
        r, destino = _build(_cards())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(destino.exists(), "builder aprovou mas não escreveu")
        self.assertIn("ok — 2 cards", r.stdout)

        html = destino.read_text(encoding="utf-8")
        self.assertIn("Email de teste", html)
        for token in PLACEHOLDERS + MARCADORES:
            self.assertNotIn(token, html, f"{token} sobrou no artefato final")

        # O artefato final passa no validador oficial — mesma régua da #287.
        veredito = _validar_saida(destino)
        self.assertTrue(veredito["ok"], veredito)
        self.assertEqual(veredito["total"], 2)
        self.assertEqual(veredito["renderizaveis"], 2)

    def test_reprovado_nao_ganha_arquivo(self) -> None:
        cards = _cards()
        cards["points"][0]["contexto"] = "tag <b>fora</b> da gramática"
        r, destino = _build(cards)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertFalse(destino.exists(), "reprovado mas o arquivo foi escrito")
        self.assertIn("<b>", r.stdout + r.stderr)

    def test_sec_orfa_reprova_via_validador(self) -> None:
        # Prova a delegação: a regra vive no validate-cards.mjs, o builder
        # só a executa. Card de seção órfã some EM SILÊNCIO no render.
        cards = _cards()
        cards["points"][0]["sec"] = "nao-existe"
        r, destino = _build(cards)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(destino.exists())
        self.assertIn("não existe em SECTIONS", r.stdout + r.stderr)

    def test_json_quebrado_e_exit_2(self) -> None:
        r, destino = _build("{oops")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertFalse(destino.exists())

    def test_js_literal_nao_e_json(self) -> None:
        # O formato antigo dos exemplos ({id: 'x'}) é JS válido e JSON
        # inválido. A recusa é o contrato: JSON estrito, sem exceção.
        r, destino = _build("{schema: 'prumo_decidir_cards.v1'}")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(destino.exists())
        self.assertIn("JSON", r.stdout + r.stderr)

    def test_schema_desconhecido_e_exit_2(self) -> None:
        r, destino = _build(_cards(schema="prumo_decidir_cards.v0"))
        self.assertEqual(r.returncode, 2)
        self.assertFalse(destino.exists())
        self.assertIn(SCHEMA, r.stdout + r.stderr)

    def test_doc_incompleto_nomeia_o_campo(self) -> None:
        cards = _cards()
        del cards["doc"]["storage_key"]
        r, destino = _build(cards)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(destino.exists())
        self.assertIn("storage_key", r.stdout + r.stderr)

    def test_doc_com_tipo_errado_reprova(self) -> None:
        cards = _cards()
        cards["doc"]["meta"] = 42
        r, destino = _build(cards)
        self.assertEqual(r.returncode, 1)
        self.assertIn("meta", r.stdout + r.stderr)

    def test_storage_key_com_aspas_nao_quebra_o_script(self) -> None:
        # `storageKey: '__STORAGE_KEY__'` vive DENTRO de string JS. Aspas no
        # valor quebravam o documento inteiro no preenchimento manual; via
        # JSON.stringify o valor entra escapado, com as próprias aspas.
        cards = _cards()
        cards["doc"]["storage_key"] = "prumo-'decidir'-\"x\""
        r, destino = _build(cards)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        html = destino.read_text(encoding="utf-8")
        self.assertIn(json.dumps(cards["doc"]["storage_key"]), html)
        self.assertTrue(_validar_saida(destino)["ok"])

    def test_points_vazio_nao_sai(self) -> None:
        # Documento sem card não decide nada — e o validador aprovaria o
        # vazio (0 erros em 0 cards). A guarda é do builder.
        r, destino = _build(_cards(points=[]))
        self.assertEqual(r.returncode, 1)
        self.assertFalse(destino.exists())

    def test_saida_json_para_automacao(self) -> None:
        r, _ = _build(_cards(), "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        maquina = json.loads(r.stdout)
        self.assertTrue(maquina["ok"])
        self.assertEqual(maquina["total"], 2)
        self.assertEqual(maquina["renderizaveis"], 2)


if __name__ == "__main__":
    unittest.main()
