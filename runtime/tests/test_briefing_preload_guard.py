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
CANONICAL_PRELOAD_UNION = (
    "Prumo/Agente/PERFIL.md",
    "Prumo/Agente/ROTINA.md",
    "Prumo/Agente/PESSOAS.md",
    ".prumo/system/PRUMO-CORE.md",
    "skills/prumo/references/modules/load-policy.md",
    "skills/prumo/references/modules/version-update.md",
    "skills/prumo/references/modules/interaction-format.md",
    "skills/prumo/references/modules/runtime-paths.md",
    "skills/prumo/references/modules/cowork-runtime-bridge.md",
    "skills/prumo/references/modules/inbox-processing.md",
)

# Nomes de módulo que NÃO podem reaparecer como enumeração no SKILL.md.
FORBIDDEN_IN_SKILL_LOAD_SECTION = (
    "load-policy.md",
    "version-update.md",
    "interaction-format.md",
    "runtime-paths.md",
    "cowork-runtime-bridge.md",
    "inbox-processing.md",
    "PERFIL.md",
    "PESSOAS.md",
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

    def test_procedure_preload_contains_exact_union(self) -> None:
        section = _section(
            PROCEDURE.read_text(encoding="utf-8"), "Pré-carga obrigatória"
        )
        for item in CANONICAL_PRELOAD_UNION:
            with self.subTest(item=item):
                self.assertIn(item, section, f"lista canônica perdeu {item}")

    def test_procedure_declares_parallel_dag(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        self.assertIn("Ordem de execução (DAG", text)
        self.assertIn("começam juntos", text)
        self.assertIn("Escritas serializadas", text)
        self.assertIn("não cancela os demais", text)

    def test_body_read_predicates_present_with_defenses(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        self.assertIn("Leitura de corpo por predicados", text)
        self.assertIn("snippet é inconclusivo", text)
        self.assertIn("sempre-relevante", text)
        self.assertIn("heurística de aprofundamento", text)
        # As defesas de conteúdo de terceiro não podem ser enfraquecidas
        # pela leitura seletiva: rodam em todo corpo lido.
        self.assertIn("rodam em todo corpo lido", text)

    def test_version_cache_producer_cited_in_both_modules(self) -> None:
        procedure = PROCEDURE.read_text(encoding="utf-8")
        version_update = VERSION_UPDATE.read_text(encoding="utf-8")
        for text, where in ((procedure, "briefing-procedure"), (version_update, "version-update")):
            with self.subTest(module=where):
                self.assertIn("prumo version-check --ensure-fresh", text)
        self.assertIn("no máximo 1x/24h", version_update)


if __name__ == "__main__":
    unittest.main()
