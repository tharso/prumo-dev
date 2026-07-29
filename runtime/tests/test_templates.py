from __future__ import annotations

import unittest
from pathlib import Path

from prumo_runtime import templates

try:
    from perimeter_invariants import NESTED_DISCOVERY_INVARIANTS, PERIMETER_INVARIANTS
except ImportError:  # execução como runtime.tests.test_templates
    from runtime.tests.perimeter_invariants import NESTED_DISCOVERY_INVARIANTS, PERIMETER_INVARIANTS

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


# #228 fase 2 — os QUATRO contratos INTEGRAIS que mudaram de dono. Fragmento
# ("disco riscado") aceitaria paráfrase: o texto tem de chegar inteiro no dono
# novo (Codex, diff r1).
RULES_MOVED_TO_RUNTIME_CONSUMO = (
    "Não leia arquivo para simular `prumo`, `briefing` ou `start`. Primeiro execute o comando real.",
    "Não escreva `{state_path}` fingindo ser o runtime.",
    "Não rode comando extra só porque ficou curioso. Execute o que foi pedido ou o que o runtime sugeriu.",
    "Se um comando falhar por uso ou argumento inválido, não repita a mesma linha como disco riscado.",
)


class TemplateAdapterTests(unittest.TestCase):
    def test_agents_wrapper_includes_short_invocation_contract(self) -> None:
        rendered = templates.render_agents_wrapper("Batata", "Prumo")
        # Wording unificado na #179 (fonte única): "chamar" venceu o par
        # disser/chamar — um texto por regra, ver wrapper_rules.RULES.
        self.assertIn('Se o usuário chamar "Prumo"', rendered)
        self.assertIn("skill `abrir`", rendered)
        self.assertIn("atalho equivalente", rendered)
        self.assertIn("QUALQUER comando `prumo`", rendered)  # #228 fase 2: gatilho amplo
        # #228 fase 2: as 4 regras de INVOCAÇÃO saíram da porta (pagas na
        # abertura de toda sessão) e passaram a morar no runtime-consumo.md,
        # carregado antes de rodar comando do runtime. Mover ≠ deletar: o
        # registro origem→destino é o teste `test_regras_de_invocacao_mudaram_de_dono`.
        self.assertNotIn("Não leia arquivo para simular", rendered)
        self.assertNotIn("Não rode comando extra só porque ficou curioso", rendered)
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
        self.assertIn("QUALQUER comando `prumo`", rendered)  # #228 fase 2: gatilho amplo
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

    def test_agent_md_se_declara_gerado_e_aponta_a_saida(self) -> None:
        """#279: o `repair` MOVE este arquivo pra backup e regenera do zero a
        cada bump, enquanto os wrappers da raiz — declaradamente descartáveis —
        ganham mescla que preserva bloco custom. O arquivo com mais chance de
        alguém editar era o único sem aviso.

        Anti-regressão do contrato que subiu a catraca pra 6.699: avisar sem
        dizer PARA ONDE levar o que é do usuário faz a pessoa parar sem saída
        e editar mesmo assim — por isso o ponteiro pro mapa autoral é parte do
        contrato, não enfeite.
        """
        nested = templates.render_agent_md(
            user_name="Batata", agent_name="Prumo", timezone_name="America/Sao_Paulo",
            briefing_time="09:00", core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/", skills_path=".prumo/skills/",
        )
        self.assertIn("Arquivo gerado", nested)
        self.assertIn("prumo repair", nested)
        self.assertIn("Prumo/Agente/MAPA-AUTORAL.md", nested)

        flat = templates.render_agent_md(
            user_name="Batata", agent_name="Prumo", timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
        )
        self.assertIn("Arquivo gerado", flat)
        self.assertIn("`Agente/MAPA-AUTORAL.md`", flat)
        self.assertNotIn("`Prumo/Agente/MAPA-AUTORAL.md`", flat)

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

    def test_discovery_clause_nested_only(self) -> None:
        # B4: nested tem as 3 âncoras da descoberta; flat as OMITE (arquivos
        # moram na raiz) preservando a base do perímetro.
        nested = templates.render_agent_md(
            user_name="B", agent_name="P", timezone_name="America/Sao_Paulo",
            briefing_time="09:00", core_path=".prumo/system/PRUMO-CORE.md",
            state_path=".prumo/state/", skills_path=".prumo/skills/",
        )
        flat = templates.render_agent_md(
            user_name="B", agent_name="P", timezone_name="America/Sao_Paulo",
            briefing_time="09:00",
        )
        for invariant in NESTED_DISCOVERY_INVARIANTS:
            with self.subTest(invariant=invariant, layout="nested"):
                self.assertIn(invariant, nested)
            with self.subTest(invariant=invariant, layout="flat"):
                self.assertNotIn(invariant, flat)
        self._assert_perimeter(flat, "AGENT.md flat (base preservada)")

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


class RegrasMovidasTest(unittest.TestCase):
    """#228 fase 2 — mover ≠ deletar: as 4 regras de invocação saíram da porta
    (custavam a abertura de TODA sessão) e têm dono novo."""

    def test_dono_novo_declara_gatilho_amplo(self) -> None:
        """#228 fase 2 (Codex, r6): o cabeçalho do módulo não pode contradizer a
        regra ampla — as 10–13 valem pra qualquer invocação, não só start/briefing."""
        modulo = (
            Path(__file__).resolve().parents[2]
            / "skills" / "prumo" / "references" / "modules" / "runtime-consumo.md"
        ).read_text(encoding="utf-8")
        cabecalho = modulo.split("## As regras")[0]
        self.assertIn("antes de QUALQUER comando `prumo`", cabecalho)
        self.assertNotIn(
            "antes de invocar\n> `prumo start`/`prumo briefing`",
            cabecalho,
            "formulação restritiva antiga voltou ao cabeçalho",
        )
        self.assertNotRegex(
            cabecalho.replace("\n", " "),
            r"Carregar \*\*antes de invocar\*\*? `prumo start`",
            "cabeçalho voltou a restringir o gatilho a start/briefing",
        )

    def test_regras_de_invocacao_mudaram_de_dono(self) -> None:
        modulo = (
            Path(__file__).resolve().parents[2]
            / "skills" / "prumo" / "references" / "modules" / "runtime-consumo.md"
        ).read_text(encoding="utf-8")
        # TODAS as superfícies de porta, nos dois layouts — ausência numa só
        # renderização não prova mudança de dono (Codex, diff r1).
        superficies = {
            "AGENT.md (nested)": templates.render_agent_md(
                user_name="Batata", agent_name="Prumo",
                timezone_name="America/Sao_Paulo", briefing_time="09:00",
                core_path=".prumo/system/PRUMO-CORE.md", state_path=".prumo/state/",
                skills_path=".prumo/skills/",
            ),
            "AGENT.md (flat)": templates.render_agent_md(
                user_name="Batata", agent_name="Prumo",
                timezone_name="America/Sao_Paulo", briefing_time="09:00",
            ),
            "CLAUDE.md": templates.render_claude_wrapper("Batata", "Prumo"),
            "AGENTS.md": templates.render_agents_wrapper("Batata", "Prumo"),
            "AGENT.md raiz": templates.render_agent_root_wrapper("Batata", "Prumo"),
        }
        for bruta in RULES_MOVED_TO_RUNTIME_CONSUMO:
            # o texto de origem trazia `{state_path}` — normalizar por layout é
            # a ÚNICA licença; o resto tem de ser byte-equivalente à main.
            regra = bruta.replace("{state_path}", ".prumo/state/")
            with self.subTest(regra=regra[:40]):
                # `assertIn` aceitaria duplicata (Codex, r3): exigir UMA
                # ocorrência prova byte-equivalência de verdade.
                self.assertEqual(
                    modulo.count(regra),
                    1,
                    "texto ausente, parafraseado ou DUPLICADO no dono novo — isso não é mover",
                )
                for nome, texto in superficies.items():
                    for variante in (regra, bruta.replace("{state_path}", "_state/")):
                        self.assertNotIn(
                            variante, texto, f"regra ainda na porta {nome} — não foi movida"
                        )
