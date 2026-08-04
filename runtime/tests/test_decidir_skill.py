"""Guards estruturais da skill `decidir` (Fase 1, issue #102).

Travam o que é fácil quebrar sem perceber: a garantia de que o template é
offline (nenhuma URL de rede), o registro da skill nos manifestos que listam
skills individualmente, e a presença dos arquivos canônicos.
"""

import base64
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "decidir"


class DecidirSkillStructureTests(unittest.TestCase):
    def test_canonical_files_exist(self):
        for rel in (
            "SKILL.md",
            "assets/template.html",
            "assets/Boliand.otf",
            "references/acoes-allowlist.md",
            "references/exemplos-de-cards.md",
        ):
            self.assertTrue((SKILL_DIR / rel).exists(), f"falta {rel}")

    def test_skill_md_declares_name_decidir(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^name:\s*decidir\s*$", "frontmatter name deve ser 'decidir'")

    def test_registered_in_individual_manifests(self):
        for manifest in ("plugin.json", ".claude-plugin/plugin.json"):
            data = json.loads((REPO_ROOT / manifest).read_text(encoding="utf-8"))
            self.assertIn(
                "./skills/decidir",
                data.get("skills", []),
                f"`./skills/decidir` não registrado em {manifest}",
            )


class DecidirTemplateOfflineTests(unittest.TestCase):
    def test_template_has_no_network_urls(self):
        """O usuário abre o HTML offline (file://). Nenhuma URL de rede é permitida."""
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        hits = re.findall(r"https?://", html)
        self.assertEqual(hits, [], "template.html não pode conter URL de rede (offline)")

    def test_template_references_local_font(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        self.assertIn("url('Boliand.otf')", html, "fonte deve ser referenciada localmente")

    def test_report_schema_is_versioned(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        self.assertIn("prumo_decidir_report.v1", html, "relatório precisa do schema JSON versionado")


class DecidirContentAwareGuards(unittest.TestCase):
    """#109: ações por conteúdo, links ativos, sem 'virar referência' passivo, sem API externa."""

    def test_allowlist_is_content_aware(self):
        text = (SKILL_DIR / "references" / "acoes-allowlist.md").read_text(encoding="utf-8")
        self.assertIn("extract_transcript", text)  # gancho de vídeo (soft-hook)
        self.assertIn("Vídeo", text)  # subtipo por conteúdo, não só "item de inbox"
        # "virar referência" passivo morreu (era effect save_reference).
        self.assertNotIn("save_reference", text)

    def test_skill_offline_is_mechanics_only_and_no_external_api(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ATIVOS", skill)  # links de conteúdo do usuário vêm ativos
        self.assertIn("sem API key", skill)  # extract_transcript não exige API do Google

    def test_template_offline_rule_scoped_to_mechanics(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        # A regra offline é da MECÂNICA; links de conteúdo podem ser externos.
        # (Sem isso, o template contradiz a SKILL.md e o agente amputa o link.)
        self.assertIn("MECÂNICA", html)
        self.assertIn("CONTEÚDO do usuário", html)

    def test_template_report_carries_source_url(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        # extract_transcript/summarize/open_link precisam da URL no JSON.
        self.assertIn("source_url", html)

    def test_template_sanitizes_content_link(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        self.assertIn("function safeUrl", html)
        self.assertIn("safeUrl(p.link.href)", html)  # aplicado no render do link

    def test_inbox_preview_has_no_heavy_extractor_action(self):
        text = (REPO_ROOT / "runtime" / "prumo_runtime" / "generate_inbox_preview.py").read_text(
            encoding="utf-8"
        )
        # #110: o botão não anuncia a skill pesada; usa ação neutra/degradável.
        self.assertNotIn("Copiar: youtube-extractor", text)
        self.assertIn("extrair/transcrever", text)


class DecidirTriagemNoEscuroGuards(unittest.TestCase):
    """#191: o card mostra o item ou leva a ele em um clique; labels sem ambiguidade; ⚑ com legenda."""

    def test_allowlist_label_marcar_visto_sem_ver(self):
        text = (SKILL_DIR / "references" / "acoes-allowlist.md").read_text(encoding="utf-8")
        # O effect é um só (dar baixa); "Ver/" prometia a ação oposta.
        self.assertNotIn("Ver/Marcar visto", text)
        self.assertIn("| Marcar visto |", text)

    def test_allowlist_distingue_mark_seen_de_no_action(self):
        text = (SKILL_DIR / "references" / "acoes-allowlist.md").read_text(encoding="utf-8")
        self.assertIn("`mark_seen` ≠ `no_action`", text)

    def test_allowlist_regra_mostrar_nao_analisar(self):
        text = (SKILL_DIR / "references" / "acoes-allowlist.md").read_text(encoding="utf-8")
        # Nota curta: texto integral no campo `conteudo` (o template escapa).
        # Não-elementar: link de visualização. Análise pesada só pós-despacho.
        self.assertIn("Mostrar ≠ analisar", text)
        self.assertIn("pós-despacho", text)
        self.assertIn("`conteudo_b64`", text)

    def test_template_tem_legenda_fixa_do_requires(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        # A nota dinâmica só aparece DEPOIS do clique; a legenda estática explica antes.
        self.assertIn("pede um detalhe no comentário", html)

    def test_skill_checklist_pre_entrega_ancorado(self):
        # Ancorado NA SEÇÃO do checklist (round 1 do Codex: substring solta
        # passava mesmo com o checklist removido, porque a regra geral repete a frase).
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"Verifique antes de entregar.*?## Como apresentar", skill, re.S)
        self.assertIsNotNone(m, "seção 'Verifique antes de entregar' sumiu do SKILL.md")
        checklist = m.group(0)
        self.assertIn("sem conteúdo nem link", checklist)
        self.assertIn("delegado plausível", checklist)
        # A regra vale pra todo card baseado em fonte — email incluso (não só inbox).
        self.assertIn("remetente", checklist)

    def test_limiar_de_nota_padronizado_nos_dois_arquivos(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        allow = (SKILL_DIR / "references" / "acoes-allowlist.md").read_text(encoding="utf-8")
        for text, name in ((skill, "SKILL.md"), (allow, "acoes-allowlist.md")):
            self.assertIn("~400", text, f"limiar da nota curta ausente em {name}")
            self.assertIn("fronteira de palavra", text, f"regra de corte ausente em {name}")

    def test_exemplos_tem_card_de_nota_bom_e_ruim(self):
        text = (SKILL_DIR / "references" / "exemplos-de-cards.md").read_text(encoding="utf-8")
        self.assertIn("Texto integral", text)
        self.assertIn("triagem no escuro", text)
        # O card BOM usa o transporte base64, não o contexto. Âncora na forma
        # JSON estrito — o formato de autoria desde a #321 (builder).
        self.assertIn('"conteudo_b64":', text)


class DecidirConteudoEscapadoGuards(unittest.TestCase):
    """#191 round 1 (Codex): conteúdo de usuário entra escapado; safeUrl sem absoluto."""

    # Espelho 1:1 da política do safeUrl no template. Se mudar lá, mude aqui —
    # o teste de presença abaixo quebra junto e aponta a dessincronia.
    _JS_LOCAL_PREDICATE = r"/^#/.test(u) || /^\.\.?\//.test(u) || /^[\w][\w./?=&%+~-]*$/.test(u)"

    @staticmethod
    def _mirror_safeurl(url):
        u = url.strip()
        if re.match(r"^(https?:|mailto:)", u, re.I):
            return u
        if re.match(r"^#", u) or re.match(r"^\.\.?/", u) or re.match(r"^[\w][\w./?=&%+~-]*$", u):
            return u
        return "#"

    def test_template_carrega_a_politica_espelhada(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        self.assertIn(self._JS_LOCAL_PREDICATE, html, "predicado do safeUrl divergiu do espelho do teste")

    def test_safeurl_aceita_externo_e_relativo(self):
        for ok in ("https://ex.com/a", "HTTP://EX.COM/x", "mailto:a@b.c", "#card-3",
                   "./inbox/nota.md", "../inbox/img.jpg", "inbox/nota.md", "nota.md"):
            self.assertEqual(self._mirror_safeurl(ok), ok, f"deveria aceitar: {ok}")

    def test_safeurl_rejeita_absoluto_e_esquemas(self):
        for bad in ("/etc/passwd", "//server/share", "file:///Users/x/nota.md",
                    "javascript:alert(1)", "data:text/html,x", "  /abs-apos-trim"):
            self.assertEqual(self._mirror_safeurl(bad), "#", f"deveria rejeitar: {bad}")

    def test_render_decodifica_e_escapa_o_conteudo(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        # Pipeline completo: base64 → fromB64 (TextDecoder UTF-8) → escapeHtml.
        self.assertIn("fromB64(p.conteudo_b64)", html)
        self.assertIn("new TextDecoder()", html)
        # O caminho antigo (texto cru interpolado) não pode voltar.
        self.assertNotIn("escapeHtml(p.conteudo)", html)
        self.assertNotIn("${p.conteudo_b64}", html)

    def test_transporte_base64_e_inerte_por_construcao(self):
        # Round 2 do Codex: apóstrofo/newline/backslash/</script> quebravam o
        # literal JS ANTES do escapeHtml. Base64 fecha por construção: o
        # alfabeto não contém nenhum caractere capaz de quebrar string ou tag.
        hostil = "O'Brien disse \"oi\" </script> '; alert(1) // barra\\invertida\nsegunda linha — travessão"
        b64 = base64.b64encode(hostil.encode("utf-8")).decode("ascii")
        self.assertRegex(b64, r"^[A-Za-z0-9+/=]+$")
        for perigoso in ("'", '"', "\\", "<", ">", "\n", "`", "$"):
            self.assertNotIn(perigoso, b64)
        # Round-trip fiel (UTF-8, travessão incluso) — o que o fromB64 do
        # template reproduz com atob + TextDecoder.
        self.assertEqual(base64.b64decode(b64).decode("utf-8"), hostil)

    def test_doc_do_template_instrui_escapar_fechamento_de_script(self):
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        # `</script>` dentro de string JS de POINTS encerraria o script do
        # documento (vale pros campos de markup do gerador; conteudo_b64 é imune).
        self.assertIn(r"vira `<\/`", html)

    def test_sink_do_conteudo_encadeia_decode_e_escape(self):
        # Round 3 do Codex: o guard anterior não travava o SINK — trocar
        # `escapeHtml(raw)` por `${raw}` reabriria XSS com o teste verde.
        html = (SKILL_DIR / "assets" / "template.html").read_text(encoding="utf-8")
        self.assertIn("escapeHtml(raw)", html)
        self.assertNotIn("${raw}", html)  # raw nunca vai cru pra interpolação

    def test_produtor_documentado_e_linha_unica_em_todos_os_contratos(self):
        # Round 3 do Codex: `printf | base64` sozinho emite newline final e,
        # no GNU, quebra em 76 colunas — SyntaxError no literal JS antes do
        # fromB64. O produtor contratado é linha única em TODOS os documentos.
        # O pipeline COMPLETO, não só a cauda: sem o `printf '%s'` um gerador
        # poderia usar `echo` (que injeta newline no próprio conteúdo).
        full_producer = r"""printf '%s' "$texto" | base64 | tr -d '\r\n'"""
        for doc in (
            SKILL_DIR / "SKILL.md",
            SKILL_DIR / "references" / "acoes-allowlist.md",
            SKILL_DIR / "references" / "exemplos-de-cards.md",
            SKILL_DIR / "assets" / "template.html",
        ):
            with self.subTest(doc=doc.name):
                self.assertIn(full_producer, doc.read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("bash"), "produtor de shell exige bash")
    def test_produtor_de_shell_roda_com_conteudo_hostil_longo(self):
        # Executa o comando CONTRATADO com texto hostil e longo o bastante
        # pra forçar o wrapping de 76 colunas do GNU base64 (>100 chars).
        hostil = (
            "O'Brien disse \"oi\" </script> '; alert(1) // barra\\invertida\n"
            "segunda linha — travessão, e texto comprido o suficiente para "
            "ultrapassar as setenta e seis colunas do GNU base64 com folga."
        )
        result = subprocess.run(
            ["bash", "-c", "printf '%s' \"$1\" | base64 | tr -d '\\r\\n'", "_", hostil],
            capture_output=True,
            text=True,
            check=True,
        )
        b64 = result.stdout
        self.assertNotIn("\n", b64)
        self.assertNotIn("\r", b64)
        self.assertRegex(b64, r"^[A-Za-z0-9+/=]+$")
        self.assertEqual(base64.b64decode(b64).decode("utf-8"), hostil)


if __name__ == "__main__":
    unittest.main()
