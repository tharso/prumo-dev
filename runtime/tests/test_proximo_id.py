"""Alocação de ID no INDICE.md (#244).

Em 27/07 um agente leu 32 linhas do índice, viu ID 24 e assumiu 25 — o índice
já ia a 34: dez fichas nasceram colidindo. Estes guards travam o mecanismo que
impede a repetição: rodapé como SUGESTÃO (nunca oráculo), sonda do candidato
em todo caminho, lock atômico e liberação sem deleção.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "runtime"))

from prumo_runtime import templates  # noqa: E402

SKILLS = REPO_ROOT / "skills"
FICHA = SKILLS / "prumo" / "references" / "ficha-de-fonte.md"
MULTIAGENT = SKILLS / "prumo" / "references" / "modules" / "multiagent.md"
FAXINA = SKILLS / "prumo" / "references" / "modules" / "faxina.md"
FILE_TEMPLATES = SKILLS / "prumo" / "references" / "file-templates.md"

_FOOTER = re.compile(r"<!-- proximo-id: (\d+) -->")


def _flat(value) -> str:
    text = value.read_text(encoding="utf-8") if isinstance(value, Path) else value
    return re.sub(r"\s+", " ", text)


def _section(text: str, heading: str) -> str:
    """Do heading até o próximo de nível igual/superior — guard por seção, não
    por varredura global do arquivo."""
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    start = next((i for i, ln in enumerate(lines) if ln.strip() == heading), None)
    if start is None:
        return ""
    for j in range(start + 1, len(lines)):
        stripped = lines[j].lstrip()
        if stripped.startswith("#") and len(stripped) - len(stripped.lstrip("#")) <= level:
            return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


class ProximoIdTest(unittest.TestCase):
    def test_renderer_nasce_com_rodape_um(self) -> None:
        rendered = templates.render_referencias_md("2026-07-27")
        ultima = rendered.rstrip().splitlines()[-1]
        # `fullmatch`: a última linha É o rodapé — não "termina com -->"
        # (qualquer comentário HTML passaria nesse teste frouxo).
        m = _FOOTER.fullmatch(ultima.strip())
        self.assertIsNotNone(m, f"última linha do INDICE não é o rodapé: {ultima!r}")
        self.assertEqual(m.group(1), "1")

    def test_paridade_template_manual_e_renderer(self) -> None:
        """O rodapé do caminho manual é IDÊNTICO ao do renderer — comparação
        direta entre os dois, não dois hard-codes separados."""
        text = FILE_TEMPLATES.read_text(encoding="utf-8")
        bloco = re.search(
            r"## Prumo/Referencias/INDICE\.md.*?--- INÍCIO ---\n(.*?)\n--- FIM ---",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(bloco, "seção do INDICE sumiu do file-templates.md")
        manual_ultima = bloco.group(1).rstrip().splitlines()[-1].strip()
        render_ultima = (
            templates.render_referencias_md("2026-07-27").rstrip().splitlines()[-1].strip()
        )
        self.assertIsNotNone(
            _FOOTER.fullmatch(manual_ultima),
            f"última linha do template manual não é o rodapé: {manual_ultima!r}",
        )
        self.assertEqual(
            manual_ultima, render_ultima, "rodapé do caminho manual ≠ do renderer"
        )

    def test_procedimento_na_secao_dona_e_na_ordem(self) -> None:
        """Os passos moram NA seção de alocação, na ordem do contrato — termo
        solto em outra seção não vale (Codex, diff r1: 'sacola de palavras')."""
        secao = _flat(_section(FICHA.read_text(encoding="utf-8"), "## Alocação de ID no `INDICE.md` (#244)"))
        self.assertTrue(secao, "seção de alocação ausente do ficha-de-fonte.md")
        marcos = [
            "Adquirir o lock",
            "última linha",
            "sugestão",
            "Sondar o candidato",
            "Escrever numa edição só",
            "Liberar o lock",
        ]
        pos = [secao.find(m) for m in marcos]
        for m, p_ in zip(marcos, pos):
            self.assertNotEqual(p_, -1, f"passo ausente da alocação: {m}")
        self.assertEqual(pos, sorted(pos), "passos da alocação fora de ordem")
        self.assertIn("Vale em TODO caminho", secao)

    def test_recuperacao_usa_semente_nao_maximo_global(self) -> None:
        secao = _flat(_section(FICHA.read_text(encoding="utf-8"), "## Alocação de ID no `INDICE.md` (#244)"))
        self.assertIn("como *semente*", secao)
        self.assertIn("nunca como máximo global", secao)
        self.assertIn("Repor o rodapé na mesma edição", secao)

    def test_lock_na_secao_dona_com_escopo_e_primitivas(self) -> None:
        secao = _flat(_section(MULTIAGENT.read_text(encoding="utf-8"), "## Escopo com aquisição ATÔMICA (#244)"))
        self.assertTrue(secao, "seção do lock atômico ausente do multiagent.md")
        for marco in (
            "`Prumo/Referencias/INDICE.md`",
            "mkdir -p .prumo/state/locks/released",
            "sem `-p`",
            "não existe hoje",
            "**não escrever**",
            "Liberação: mover, nunca deletar",
            "sufixo determinístico",
            "Sem retomada automática por idade",
        ):
            self.assertIn(marco, secao, f"contrato do lock sem: {marco!r}")

    def test_claude_md_registra_a_excecao_do_lock(self) -> None:
        """[P2 da r1]: a fonte de verdade dizia 'exclusivamente agent-lock.json'
        — a segunda primitiva precisa estar reconciliada, não contrabandeada."""
        flat = _flat((REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("Exceção nomeada (#244)", flat)
        self.assertIn("`Prumo/Referencias/INDICE.md` usa aquisição atômica", flat)

    def test_protocolo_de_lock_funciona_em_workspace_novo(self) -> None:
        """[P1 da r1]: o setup cria `.prumo/state/`, NÃO as subpastas do lock.
        Executa o protocolo documentado num workspace recém-criado."""
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".prumo" / "state").mkdir(parents=True)  # o que o setup entrega
            lock = ws / ".prumo" / "state" / "locks" / "referencias-indice.d"
            released = ws / ".prumo" / "state" / "locks" / "released"

            def sh(cmd: str) -> int:
                return subprocess.run(cmd, shell=True, cwd=ws, capture_output=True).returncode

            # passo 0 + 1 do contrato: pais idempotentes, folha atômica
            self.assertEqual(sh("mkdir -p .prumo/state/locks/released"), 0)
            self.assertEqual(sh("mkdir .prumo/state/locks/referencias-indice.d"), 0)
            self.assertTrue(lock.is_dir())
            # concorrência: o segundo mkdir FALHA (exclusão sem janela)
            self.assertNotEqual(sh("mkdir .prumo/state/locks/referencias-indice.d"), 0)
            # liberação: move, nunca deleta
            self.assertEqual(
                sh("mv .prumo/state/locks/referencias-indice.d .prumo/state/locks/released/2026-07-27T23-00-00"),
                0,
            )
            self.assertFalse(lock.exists(), "lock não foi liberado")
            self.assertTrue((released / "2026-07-27T23-00-00").is_dir())
            # e o path volta a ser adquirível
            self.assertEqual(sh("mkdir .prumo/state/locks/referencias-indice.d"), 0)

            # [254-2] COLISÃO na liberação: destino-base ocupado → sufixo
            # determinístico, sem aninhar dentro do que já existe.
            destino = ".prumo/state/locks/released/2026-07-27T23-00-00"
            self.assertTrue((ws / destino).is_dir(), "destino-base deveria estar ocupado")
            self.assertNotEqual(
                sh(f"test -e {destino}-2"), 0, "sufixo -2 não deveria existir ainda"
            )
            self.assertEqual(sh(f"mv .prumo/state/locks/referencias-indice.d {destino}-2"), 0)
            self.assertTrue((ws / f"{destino}-2").is_dir())
            self.assertFalse(
                (ws / destino / "referencias-indice.d").exists(),
                "liberação aninhou dentro do destino ocupado — lock preso",
            )
            self.assertFalse(lock.exists())
            self.assertEqual(sh("mkdir .prumo/state/locks/referencias-indice.d"), 0)

    def test_faxina_aponta_para_a_alocacao(self) -> None:
        flat = _flat(FAXINA)
        self.assertIn("alocação de ID do `ficha-de-fonte.md` (#244)", flat)


if __name__ == "__main__":
    unittest.main()
