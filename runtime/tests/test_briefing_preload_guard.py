"""#195: guards textuais da dieta do briefing, fase 1.

1. Anti-drift da pré-carga: a lista canônica mora SÓ em
   `briefing-procedure.md`; a seção "Carregamento obrigatório" do SKILL.md
   aponta pra lá sem manter segunda enumeração (duas listas divergindo em
   silêncio foi o bug de origem).
2. União exata preservada: a lista canônica contém tudo que as duas listas
   antigas somavam — zero corte nesta fase (acordo com o Codex, r2).
3. DAG de paralelismo, predicados de leitura de corpo e produtor do cache
   de versão presentes nos módulos certos.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "briefing" / "SKILL.md"
PROCEDURE = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "briefing-procedure.md"
VERSION_UPDATE = REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "version-update.md"

# União exata das duas listas pré-#195 (SKILL.md ∪ procedure) + PESSOAS.md
# (entrou no acordo r2 do Codex para alimentar o predicado de remetente).
# Comparada como CONJUNTO EXATO contra os paths `.md` da seção — item a mais
# ou a menos quebra o guard (Codex, diff r1 achado 5).
CANONICAL_PRELOAD_UNION = frozenset(
    {
        "Prumo/Agente/PERFIL.md",
        "Prumo/Agente/ROTINA.md",
        "Prumo/Agente/PESSOAS.md",
        ".prumo/system/PRUMO-CORE.md",
        "briefing-procedure.md",
        "skills/prumo/references/modules/load-policy.md",
        "skills/prumo/references/modules/version-update.md",
        "skills/prumo/references/modules/interaction-format.md",
        "skills/prumo/references/modules/runtime-paths.md",
        "skills/prumo/references/modules/cowork-runtime-bridge.md",
        "skills/prumo/references/modules/inbox-processing.md",
    }
)

# Nomes de arquivo que NÃO podem reaparecer como enumeração no SKILL.md.
FORBIDDEN_IN_SKILL_LOAD_SECTION = (
    "load-policy.md",
    "version-update.md",
    "interaction-format.md",
    "runtime-paths.md",
    "cowork-runtime-bridge.md",
    "inbox-processing.md",
    "PERFIL.md",
    "ROTINA.md",
    "PESSOAS.md",
    "PRUMO-CORE.md",
)

# Rótulo → invariante de cada predicado de leitura de corpo. Verificados
# DENTRO do bloco do Estágio 2, na linha do próprio rótulo — busca no
# documento inteiro deixaria a remoção de um predicado passar batida
# (Codex, diff r2 achado 2).
BODY_READ_PREDICATE_LABELS = {
    "(a)": "canal prioritário",
    "(b)": "remetente é **pessoa**",
    "(c)": "thread tem participação do usuário",
    "(d)": "prazo, pergunta direta ou pedido de ação",
    "(e)": "snippet é inconclusivo",
    "(f)": "sempre-relevante",
    "(g)": "heurística de aprofundamento",
}

# Frases únicas fora do bloco: precedência do Estágio 1 e defesas intactas.
BODY_READ_GLOBAL_INVARIANTS = (
    "prevalecem sobre o sinal de automatização",
    "rodam em todo corpo lido",
)

# Invariantes do DAG do Passo 4 — desde a #196 a execução é ADAPTATIVA
# (o "começam juntos" físico caiu na medição do #205), mas as dependências
# lógicas seguem invioláveis (classificação exige contexto local).
DAG_INVARIANTS = (
    "Ordem de execução (DAG lógico, execução ADAPTATIVA",
    "Primeiro o local, sem esperar o externo",
    "Paralelismo por subagente: DESLIGADO por default",
    "Classificação só depois do contexto local",
    "Escritas serializadas",
    "não cancela os demais",
)

# Contratos centrais do briefing em dois tempos (#196): emissão local antes
# de qualquer espera externa, numeração congelada e contínua, escape
# best-effort que nunca marca o dia, e conclusão definida POR VARIANTE.
TWO_TEMPOS_INVARIANTS = (
    "antes de aguardar qualquer resultado de email/calendário",
    "nunca renumerar",
    "sem reiniciar entre seções **nem entre os dois tempos (#196)**",
    '"segue tudo"/"continua" é o CONTRÁRIO de escape',
    "Quando cada variante está COMPLETA",
    "Escape do usuário (qualquer variante) | nunca",
    "seguir sem esperar resposta",
    "Estágio LOCAL, integral, ANTES da emissão do primeiro tempo",
)


def _section(text: str, header: str) -> str:
    match = re.search(rf"^## {re.escape(header)}.*?(?=^## )", text, re.MULTILINE | re.DOTALL)
    assert match, f"seção '## {header}' não encontrada"
    return match.group(0)


class PreloadSingleEnumerationTests(unittest.TestCase):
    def test_skill_points_to_procedure_without_second_list(self) -> None:
        section = _section(SKILL.read_text(encoding="utf-8"), "Carregamento obrigatório")
        self.assertIn("briefing-procedure.md", section)
        self.assertIn("lista canônica", section)
        for module in FORBIDDEN_IN_SKILL_LOAD_SECTION:
            with self.subTest(forbidden=module):
                self.assertNotIn(
                    module,
                    section,
                    f"SKILL.md recriou enumeração de pré-carga com {module} — "
                    "a lista canônica mora só no briefing-procedure.md (#195)",
                )

    def test_procedure_preload_is_the_exact_union(self) -> None:
        section = _section(
            PROCEDURE.read_text(encoding="utf-8"), "Pré-carga obrigatória"
        )
        # Só as linhas numeradas são a lista; a prosa em volta pode citar
        # outros arquivos (ex.: "o SKILL.md aponta pra cá") sem quebrar.
        numbered = "\n".join(
            line for line in section.splitlines() if re.match(r"^\d+\.", line)
        )
        listed = frozenset(re.findall(r"`([^`\s]+\.md)`", numbered))
        self.assertEqual(
            listed,
            CANONICAL_PRELOAD_UNION,
            "lista canônica divergiu da união acordada: "
            f"faltando={sorted(CANONICAL_PRELOAD_UNION - listed)}, "
            f"sobrando={sorted(listed - CANONICAL_PRELOAD_UNION)}",
        )

    def test_procedure_declares_adaptive_dag(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        for invariant in DAG_INVARIANTS:
            with self.subTest(invariant=invariant):
                self.assertIn(invariant, text)

    def test_two_tempos_contracts_present(self) -> None:
        # #196: os contratos do briefing em dois tempos são invariantes —
        # emissão local sem espera, numeração congelada, escape que nunca
        # marca, conclusão POR VARIANTE.
        text = PROCEDURE.read_text(encoding="utf-8")
        for invariant in TWO_TEMPOS_INVARIANTS:
            with self.subTest(invariant=invariant):
                self.assertIn(invariant, text)

    def test_body_read_predicates_present_with_defenses(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        self.assertIn("Leitura de corpo por predicados", text)
        block_match = re.search(
            r"Ler o corpo via `gmail_read_message` quando:(.*?)Fica \*\*sem corpo lido\*\*",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(block_match, "bloco de predicados do Estágio 2 não encontrado")
        block_lines = block_match.group(1).splitlines()
        for label, invariant in BODY_READ_PREDICATE_LABELS.items():
            with self.subTest(predicate=label):
                line = next(
                    (l for l in block_lines if l.lstrip().startswith(f"- {label}")),
                    None,
                )
                self.assertIsNotNone(line, f"predicado {label} sumiu do bloco")
                self.assertIn(invariant, line, f"{label} perdeu a invariante: {invariant!r}")
        for invariant in BODY_READ_GLOBAL_INVARIANTS:
            with self.subTest(invariant=invariant):
                self.assertIn(invariant, text)

    def test_version_cache_producer_cited_in_both_modules(self) -> None:
        procedure = PROCEDURE.read_text(encoding="utf-8")
        version_update = VERSION_UPDATE.read_text(encoding="utf-8")
        for text, where in ((procedure, "briefing-procedure"), (version_update, "version-update")):
            with self.subTest(module=where):
                self.assertIn("prumo version-check --ensure-fresh", text)
        self.assertIn("no máximo 1x/24h", version_update)


if __name__ == "__main__":
    unittest.main()
