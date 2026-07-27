from __future__ import annotations

import unittest
from pathlib import Path

from prumo_runtime import templates

try:
    from perimeter_invariants import PERIMETER_INVARIANTS
except ImportError:  # execução como runtime.tests.test_templates
    from runtime.tests.perimeter_invariants import PERIMETER_INVARIANTS

REPO_ROOT = Path(__file__).resolve().parents[2]


# As 9 regras do runtime-consumo.md, uma âncora DISTINTIVA por regra (#228
# C1, r1-r2 do Codex) — incluindo os DOIS predicados start-json
# (não-unificados por decisão do dono). Fonte única do guard.
RUNTIME_CONSUMO_ANCHORS = (
    "painel local estruturado (semente/backcompat)",
    "Se o host souber trabalhar com JSON",
    "Se o host conseguir renderizar ações próprias",
    "leia `adapter_hints` e respeite `kind`, `shell_command` e `host_prompt`",
    "`adapter_contract_version`, `workspace_resolution` e `adapter_hints` antes de bancar o esperto",
    "Antes de olhar `message`, leia `state_flags`, `degradation`, `next_move` e `selection_contract`",
    "Se `degradation.status` vier `error` ou `partial`",
    "Não fabrique JSON de `prumo start --format json`",
    "Se `next_move.id == kickoff`, não abra cardápio de aeroporto",
)


class TemplateAdapterTests(unittest.TestCase):
    def test_agents_wrapper_includes_short_invocation_contract(self) -> None:
        rendered = templates.render_agents_wrapper("Batata", "Prumo")
        # Wording unificado na #179 (fonte única): "chamar" venceu o par
        # disser/chamar — um texto por regra, ver wrapper_rules.RULES.
        self.assertIn('Se o usuário chamar "Prumo"', rendered)
        self.assertIn("skill `abrir`", rendered)
        self.assertIn("atalho equivalente", rendered)
        self.assertIn("prumo briefing --workspace . --format json", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva `_state/`", rendered)
        self.assertIn("Não rode comando extra só porque ficou curioso", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)
        # #228 C1: o contrato de consumo do JSON mudou de dono — as âncoras
        # vivem em runtime-consumo.md; a superfície aponta pra lá.
        self.assertIn("runtime-consumo.md", rendered)
        module = (
            Path(__file__).resolve().parents[2]
            / "skills" / "prumo" / "references" / "modules" / "runtime-consumo.md"
        ).read_text(encoding="utf-8")
        for anchor in RUNTIME_CONSUMO_ANCHORS:
            self.assertIn(anchor, module)

    def test_nested_wrapper_points_to_real_core_and_state_paths(self) -> None:
        # Perfil FULL: contrato completo segue derivando os paths reais.
        rendered = templates.render_claude_wrapper(
            "Batata",
            "Prumo",
            canonical_target="Prumo/AGENT.md",
            context_root="Prumo/Agente/",
            core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/",
            profile="full",
        )
        self.assertIn("Leia `Prumo/AGENT.md`", rendered)
        self.assertIn("Use `.prumo/system/PRUMO-CORE.md`", rendered)
        self.assertIn("Não escreva `.prumo/state/`", rendered)
        # #228 C1: kickoff é regra do runtime-consumo.md agora; o wrapper
        # full mantém o ponteiro.
        self.assertIn("runtime-consumo.md", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)

    def test_claude_wrapper_default_is_minimal_with_door_and_perimeter(self) -> None:
        # #180: default do CLAUDE.md é minimal — porta + perímetro presentes,
        # SEM o bloco dinâmico de dispatch (host com registry o dispensa).
        rendered = templates.render_claude_wrapper(
            "Batata",
            "Prumo",
            canonical_target="Prumo/AGENT.md",
            context_root="Prumo/Agente/",
            core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/",
            skills_dispatch="<!-- prumo:skills-dispatch -->\nbloco",
        )
        self.assertIn("Leia `Prumo/AGENT.md`", rendered)
        self.assertIn("Perímetro de leitura", rendered)
        self.assertNotIn("prumo:skills-dispatch", rendered)
        agents = templates.render_agents_wrapper(
            "Batata",
            "Prumo",
            skills_dispatch="<!-- prumo:skills-dispatch -->\nbloco",
        )
        self.assertIn("prumo:skills-dispatch", agents, "hosts sem registry mantêm o dispatch")

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
        self.assertIn("prumo briefing --workspace . --format json", rendered)
        self.assertIn("Não leia arquivo para simular", rendered)
        self.assertIn("Não escreva `_state/`", rendered)
        self.assertIn("Não rode comando extra só porque ficou curioso", rendered)
        self.assertIn("Execute primeiro e fale depois", rendered)
        # #228 C1: o contrato de consumo do JSON mudou de dono — as âncoras
        # vivem em runtime-consumo.md; a superfície aponta pra lá.
        self.assertIn("runtime-consumo.md", rendered)
        module = (
            Path(__file__).resolve().parents[2]
            / "skills" / "prumo" / "references" / "modules" / "runtime-consumo.md"
        ).read_text(encoding="utf-8")
        for anchor in RUNTIME_CONSUMO_ANCHORS:
            self.assertIn(anchor, module)

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
