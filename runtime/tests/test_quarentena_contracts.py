"""Guards textuais do contrato de quarentena (#242).

Remover do inbox = MOVER (quarentena `_to_delete/` ou destino durável), nunca
deletar. Estes guards congelam o que carrega o contrato nos módulos — inclusive
a ORDEM da máquina de remoção — e varrem skills/ contra reintrodução de deleção
como via. Comparações rodam sobre texto com whitespace normalizado, pra reflow
de Markdown não quebrar guard legítimo ([D9] do review do Codex).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"
INBOX = SKILLS / "prumo" / "references" / "modules" / "inbox-processing.md"
CORE = SKILLS / "prumo" / "references" / "prumo-core.md"
PROTECTION = SKILLS / "prumo" / "references" / "file-protection-rules.md"
FAXINA = SKILLS / "prumo" / "references" / "modules" / "faxina.md"
HIGIENE = SKILLS / "higiene" / "SKILL.md"
ALLOWLIST = SKILLS / "decidir" / "references" / "acoes-allowlist.md"

# Afirmações de deleção do ORIGINAL de inbox são proibidas em qualquer skill —
# em qualquer formulação: verbo em PT ("deletar/apagar/excluir [o|um] [arquivo]
# original") ou operação literal (rm/unlink/os.remove) na MESMA ORAÇÃO que
# original/inbox, em qualquer ordem ([D9] r3). A negação absolve apenas quando
# está amarrada à PRÓPRIA operação destrutiva — janela imediata antes dela, sem
# cruzar oração ([D9] r4/r5: "não execute unlink" absolve; "não mova o arquivo
# e rode rm" NÃO absolve, a negação é do mover). O acervo (--permanent) tem
# contrato próprio e não usa esse fraseado.
_VERB_FORBIDDEN = re.compile(
    r"(?:deletar|apagar|excluir|remover\s+fisicamente)\s+(?:o\s+|um\s+)?(?:arquivo\s+)?origina(?:l|is)",
    re.IGNORECASE,
)
# Aceita a forma protegida (os_remove/shutil_rmtree) — o "." desses tokens
# cortaria a oração no _CLAUSE_SPLIT ([r6]); eles são escudados antes do split.
_OPS_RE = re.compile(r"\b(?:rm|rmdir|unlink|os[._]remove|shutil[._]rmtree)\b", re.IGNORECASE)
_OBJ_RE = re.compile(r"\b(?:original|origina(?:l|is)|inbox)\b", re.IGNORECASE)
_CLAUSE_SPLIT = re.compile(r"[.!?;:—]")
# Negação imediatamente antes da operação (mesma oração, janela curta, SEM
# atravessar vírgula — [r7]: "Se não mover, deletar o original" não está
# negado: a negação é do "mover", a vírgula abre outra ação).
_NEG_NEAR = re.compile(
    r"(?:nunca|não|nao|jamais|deixa\s+de|em\s+vez\s+de|falha)[^,\s]*\s+(?:[^,\s]+\s+){0,2}$",
    re.IGNORECASE,
)


def _deletion_offenses(flat: str) -> list[str]:
    """Trechos que AFIRMAM deleção do original — lógica única, testável."""
    # Escuda os tokens com ponto ANTES do split de orações ([r6]: sem isso,
    # "os.remove" vira "os" + "remove" e o matcher nunca vê a operação).
    flat = flat.replace("os.remove", "os_remove").replace("shutil.rmtree", "shutil_rmtree")
    out: list[str] = []
    for clause in _CLAUSE_SPLIT.split(flat):
        # Verbo PT: a negação é a que precede o próprio verbo, na oração.
        for m in _VERB_FORBIDDEN.finditer(clause):
            if _NEG_NEAR.search(clause[: m.start()]):
                continue
            out.append(clause[max(0, m.start() - 40): m.end() + 20].strip())
        # Operação literal: ofende quando divide a oração com original/inbox e
        # NÃO está ela mesma negada (a negação de outra ação não absolve).
        if _OBJ_RE.search(clause):
            for m in _OPS_RE.finditer(clause):
                if _NEG_NEAR.search(clause[: m.start()]):
                    continue
                out.append(clause[max(0, m.start() - 40): m.end() + 20].strip())
    return out


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    """Whitespace normalizado — imune a reflow de Markdown."""
    return re.sub(r"\s+", " ", text)


def _section(text: str, heading: str) -> str:
    """Do heading até o próximo heading de nível igual/superior."""
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i
            break
    if start is None:
        return ""
    for j in range(start + 1, len(lines)):
        stripped = lines[j].lstrip()
        if stripped.startswith("#") and len(stripped) - len(stripped.lstrip("#")) <= level:
            return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


class QuarentenaContractsTest(unittest.TestCase):
    def test_inbox_processing_nao_tem_delecao_como_via(self) -> None:
        flat = _flat(_read(INBOX))
        self.assertNotIn(
            "deletar o original do inbox com ação real de filesystem",
            flat,
            "deleção real voltou como operação válida (#242 revertida)",
        )
        self.assertNotIn(
            "solicitar a permissão do runtime",
            flat,
            "o degrau beco-sem-saída do fallback voltou (#242)",
        )

    def test_maquina_de_remocao_tem_os_passos_na_ordem(self) -> None:
        """Confirmar → registrar → mover → verificar → marcar — a ORDEM é o
        contrato (o REGISTRO vem ANTES do move; ASSERT do core)."""
        section = _flat(_section(_read(INBOX), "### Máquina de remoção (por item, nesta ordem)"))
        self.assertTrue(section, "seção da máquina de remoção sumiu do inbox-processing.md")
        steps = ["**Confirmar**", "**Registrar**", "**Mover**", "**Verificar**", "**Marcar**"]
        positions = [section.find(s) for s in steps]
        for step, pos in zip(steps, positions):
            self.assertNotEqual(pos, -1, f"máquina de remoção sem o passo {step}")
        self.assertEqual(positions, sorted(positions), "passos da máquina fora de ordem")
        self.assertIn("REMOCAO_FALHOU", section)

    def test_inbox_processing_tem_contrato_de_destino(self) -> None:
        flat = _flat(_read(INBOX))
        for marker in (
            "_to_delete/<AAAA-MM-DD>_<escopo>/",
            "mover, nunca deletar",
            "Retenção durável",
            "### Sequência de arquivamento (retenção)",
        ):
            self.assertIn(_flat(marker), flat, f"contrato de destino sem: {marker!r}")

    def test_core_assert_usa_remover_nao_deletar(self) -> None:
        text = _read(CORE)
        self.assertIn(
            "ASSERT: Antes de remover item de inbox, confirmar com o usuário o plano único de commit.",
            text,
        )
        self.assertNotIn("Antes de deletar item de inbox", text)

    def test_quarentena_e_do_usuario(self) -> None:
        """`_to_delete/` fora de listagem/índice/contagem — e o Prumo nunca esvazia."""
        protection = _flat(_read(PROTECTION))
        self.assertIn("`_to_delete/` (raiz do workspace)", protection)
        self.assertIn("Quarentena do USUÁRIO (#242)", protection)
        self.assertIn("nem esvazia", protection)
        inbox = _flat(_read(INBOX))
        self.assertIn("nunca lista, indexa, conta ou esvazia", inbox)

    def test_faxina_sinaliza_e_higiene_resolve(self) -> None:
        """#212 mantida: faxina só sinaliza; a oferta confirmável mora na higiene."""
        faxina = _flat(_read(FAXINA))
        self.assertIn("apenas sinalizar", faxina)
        self.assertIn("mora na `higiene` (#242)", faxina)
        higiene = _flat(_read(HIGIENE))
        self.assertIn("processados inconsistentes", higiene)
        self.assertIn("Movo pra quarentena `_to_delete/`", higiene)
        self.assertIn("não recebe backup duplicado", higiene)

    def test_allowlist_separa_quarentena_de_retencao(self) -> None:
        flat = _flat(_read(ALLOWLIST))
        self.assertIn("Remover nunca é deletar (#242)", flat)
        self.assertIn("movem o próprio arquivo pro destino durável", flat)

    def test_quarentena_e_termo_exclusivo_do_to_delete(self) -> None:
        """[D8]: 'quarentena' nas skills refere `_to_delete/` — o acervo/arquivo
        é retenção. Janela de contexto (não linha-a-linha, [D9] r2): chamar
        `Prumo/Arquivo/` de quarentena na mesma frase confunde pré-lixo com
        retenção, mesmo cruzando quebra de linha."""
        pattern = re.compile(
            r"quarenten\w*[^.!?]{0,80}Prumo/Arquivo|Prumo/Arquivo[^.!?]{0,80}quarenten\w*",
            re.IGNORECASE,
        )
        offenders = []
        for md in sorted(SKILLS.rglob("*.md")):
            flat = _flat(_read(md))
            for m in pattern.finditer(flat):
                offenders.append(f"{md.relative_to(REPO_ROOT)}: …{m.group(0)[:80]}…")
        self.assertEqual(offenders, [], f"'quarentena' aplicado a retenção: {offenders}")

    def test_nenhuma_skill_afirma_delecao_do_original(self) -> None:
        """Varredura com contexto ([D9]): afirmação de deleção do original — em
        qualquer formulação, inclusive rm/unlink, em qualquer ordem — é
        proibida; enunciado negativo ('nunca deletar…') é permitido."""
        offenders = []
        for md in sorted(SKILLS.rglob("*.md")):
            for snippet in _deletion_offenses(_flat(_read(md))):
                offenders.append(f"{md.relative_to(REPO_ROOT)}: …{snippet}…")
        self.assertEqual(offenders, [], f"afirmação de deleção do original: {offenders}")

    def test_padroes_do_guard_pegam_formulacoes_adversariais(self) -> None:
        """[D9] r3 — a lógica do guard, provada nos dois sentidos com os
        exemplos adversariais do review."""
        ofensas = (
            "deletar o original do inbox com ação real",
            "apagar o arquivo original depois de processar",
            "No original do inbox, execute unlink em seguida",
            "Nunca mover; deletar o original",  # negação de OUTRA oração não absolve
            "use rm no diretório do inbox",
            # [r5]: negação de OUTRA ação na mesma oração não absolve a destrutiva.
            "No inbox, não mova o arquivo e rode rm no original",
            # [r6]: tokens com ponto não podem ser cortados pelo split de orações.
            "use os.remove no original do inbox",
            "aplique shutil.rmtree no diretório do inbox",
            # [r7]: negação de outra ação ANTES da vírgula não absolve a condicional.
            "Se não mover, deletar o original do inbox",
        )
        for texto in ofensas:
            with self.subTest(texto=texto):
                self.assertTrue(_deletion_offenses(texto), f"deveria acusar: {texto!r}")
        permitidos = (
            "nunca deletar o original — mover é o contrato",
            "a deleção falha com Operation not permitted no host",
            "remover o original do inbox movendo-o pra quarentena",
            "rode rm -rf no diretório de build do seu projeto",
            # [D9] r4: negação ENTRE objeto e operação, mesma oração.
            "no original do inbox, não execute unlink",
            "no inbox, jamais rode rm",
            # [r6]: negação amarrada também vale pros tokens com ponto.
            "nunca chame os.remove no original do inbox",
            "jamais use shutil.rmtree no inbox",
        )
        for texto in permitidos:
            with self.subTest(texto=texto):
                self.assertEqual(_deletion_offenses(texto), [], f"falso positivo: {texto!r}")


if __name__ == "__main__":
    unittest.main()
