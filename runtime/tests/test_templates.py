from __future__ import annotations

import unittest
from pathlib import Path

from prumo_runtime import templates

REPO_ROOT = Path(__file__).resolve().parents[2]

# Invariantes do perímetro de leitura (#194). A MESMA coleção vale para o
# template markdown (fonte canônica em skills/) e para o gerador Python —
# é o guard de paridade md ↔ py acordado na revisão do Codex (r1, achado 5).
PERIMETER_INVARIANTS = (
    "## Perímetro de leitura",
    "Perímetro automático",
    "enumeração recursiva",
    "node_modules",
    "Escopo autorizado pela tarefa",
    "caminhos permitidos",
)


class TemplateAdapterTests(unittest.TestCase):
    def test_agents_wrapper_includes_short_invocation_contract(self) -> None:
        rendered = templates.render_agents_wrapper("Batata", "Prumo")
        self.assertIn('Se o usuário disser "Prumo"', rendered)
        self.assertIn("skill `abrir`", rendered)
        self.assertIn("atalho equivalente", rendered)
        self.assertIn("prumo briefing --workspace .", rendered)
        self.assertIn("prumo start --format json", rendered)
        self.assertIn("prumo briefing --workspace . --format json", rendered)
        self.assertIn("adapter_hints", rendered)
        self.assertIn("state_flags", rendered)
        self.assertIn("degradation", rendered)
        self.assertIn("selection_contract", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva `_state/`", rendered)
        self.assertIn("Não rode comando extra sem necessidade", rendered)
        self.assertIn("next_move.id == kickoff", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)

    def test_nested_wrapper_points_to_real_core_and_state_paths(self) -> None:
        rendered = templates.render_claude_wrapper(
            "Batata",
            "Prumo",
            canonical_target="Prumo/AGENT.md",
            context_root="Prumo/Agente/",
            core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/",
        )
        self.assertIn("Leia `Prumo/AGENT.md`", rendered)
        self.assertIn("Use `.prumo/system/PRUMO-CORE.md`", rendered)
        self.assertIn("Não escreva `.prumo/state/`", rendered)
        self.assertIn("next_move.id == kickoff", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)

    def test_agent_md_mentions_host_invocation_rules(self) -> None:
        rendered = templates.render_agent_md(
            user_name="Batata",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
        )
        self.assertIn('Se o usuário chamar "Prumo"', rendered)
        self.assertIn("skill `abrir`", rendered)
        self.assertIn("atalho equivalente", rendered)
        self.assertIn("prumo briefing --workspace .", rendered)
        self.assertIn("prumo briefing --workspace . --format json", rendered)
        self.assertIn("adapter_hints", rendered)
        self.assertIn("state_flags", rendered)
        self.assertIn("degradation", rendered)
        self.assertIn("selection_contract", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva arquivos em `_state/`", rendered)
        self.assertIn("Não rode comando extra só porque ficou curioso", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)

    def test_workflows_template_exposes_structure_only_phase(self) -> None:
        rendered = templates.render_workflows_md("22/03/2026")
        self.assertIn("structure-only", rendered)
        self.assertIn("candidatos", rendered.lower())
        self.assertIn("22/03/2026", rendered)

    def test_agente_index_tombstone_points_to_agent_md(self) -> None:
        rendered = templates.render_agente_index_tombstone()
        self.assertIn("aposentado", rendered.lower())
        self.assertIn("Prumo/AGENT.md", rendered)
        # O tombstone não pode reanunciar o contrato de identidade legado.
        self.assertNotIn("- Nome preferido:", rendered)


class ReadingPerimeterTests(unittest.TestCase):
    """Perímetro de leitura (#194): dois escopos, proibição por efeito.

    O workspace real convive com repos de código (node_modules, .git) —
    listagem recursiva da raiz explode contexto. A regra precisa nascer nos
    templates (workspace novo) e a MESMA coleção de invariantes vale para o
    markdown canônico e o gerador Python (paridade sem drift).
    """

    def _assert_perimeter(self, rendered: str, where: str) -> None:
        for invariant in PERIMETER_INVARIANTS:
            self.assertIn(invariant, rendered, f"invariante do perímetro ausente em {where}: {invariant!r}")

    def test_agent_md_declares_reading_perimeter(self) -> None:
        rendered = templates.render_agent_md(
            user_name="Batata",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
            core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/",
            skills_path=".prumo/skills/",
        )
        self._assert_perimeter(rendered, "render_agent_md")

    def test_all_root_wrappers_declare_reading_perimeter(self) -> None:
        wrappers = {
            "render_agent_root_wrapper": templates.render_agent_root_wrapper(
                "Batata", "Prumo", canonical_target="Prumo/AGENT.md", system_root=".prumo/state/"
            ),
            "render_claude_wrapper": templates.render_claude_wrapper(
                "Batata", "Prumo", canonical_target="Prumo/AGENT.md", state_path=".prumo/state/"
            ),
            "render_agents_wrapper": templates.render_agents_wrapper(
                "Batata", "Prumo", canonical_target="Prumo/AGENT.md", state_path=".prumo/state/"
            ),
        }
        for where, rendered in wrappers.items():
            with self.subTest(wrapper=where):
                self._assert_perimeter(rendered, where)

    def test_markdown_template_has_parity_with_python_generator(self) -> None:
        template_md = (
            REPO_ROOT / "skills" / "prumo" / "references" / "agent-md-template.md"
        ).read_text(encoding="utf-8")
        self._assert_perimeter(template_md, "skills/prumo/references/agent-md-template.md")

    def test_perimeter_names_task_scope_escape_hatch(self) -> None:
        # O perímetro NÃO pode ser absoluto (Codex r1, achado 1): quando o
        # usuário cita um caminho, a expansão dirigida e rasa é legítima.
        rendered = templates.render_agent_md(
            user_name="Batata",
            agent_name="Prumo",
            timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
        )
        self.assertIn("dirigida e rasa", rendered)
        self.assertIn("perguntar", rendered)
