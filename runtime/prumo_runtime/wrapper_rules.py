"""Fonte única das regras de porta ("Porta curta" / "Regras rápidas") (#179).

Antes desta lista existiam DOIS rule-sets paralelos em `templates.py` — 17
regras nos wrappers da raiz e 20 no `Prumo/AGENT.md`, com ~13 pares dizendo
a mesma coisa em wording diferente. Agora cada regra tem UM texto e declara
em quais superfícies aparece:

- `wrapper`  → CLAUDE.md / AGENT.md / AGENTS.md da raiz do workspace
- `workspace` → Prumo/AGENT.md (a porta canônica)

O perfil `minimal` (subconjunto, só superfície wrapper) existe pro
enxugamento da rota do briefing (M3 do #177): wrappers da raiz com o
essencial + ponteiro, conjunto completo só na porta canônica.

Módulo folha: não importa nada de `prumo_runtime`.
"""

from __future__ import annotations

from dataclasses import dataclass

SURFACES = ("wrapper", "workspace")
PROFILES = ("full", "minimal")

_BOTH = frozenset(SURFACES)
_WRAPPER = frozenset({"wrapper"})
_WORKSPACE = frozenset({"workspace"})
_ALL_PROFILES = frozenset(PROFILES)
_FULL_ONLY = frozenset({"full"})


@dataclass(frozen=True)
class WrapperRule:
    id: str
    text: str  # placeholder {state_path} quando precisar
    surfaces: frozenset[str]
    profiles: frozenset[str] = _FULL_ONLY


# A ordem AQUI define a numeração renderizada em cada superfície (filtro +
# enumerate). Preserva a sequência histórica dos dois sets originais.
RULES: tuple[WrapperRule, ...] = (
    WrapperRule(
        "usuario-legivel-sem-prumo",
        "Tudo que é do usuário continua legível sem o Prumo.",
        _WORKSPACE,
    ),
    WrapperRule(
        "wrappers-nao-sao-fonte",
        "`CLAUDE.md` e `AGENTS.md` são wrappers de compatibilidade, não a fonte de verdade.",
        _WORKSPACE,
    ),
    WrapperRule(
        "repair-antes-de-inventar",
        "Se um arquivo modular faltar, usar `prumo repair` antes de inventar realidade.",
        _WORKSPACE,
    ),
    WrapperRule(
        "invocacao-curta-abrir",
        'Se o usuário chamar "Prumo" cru, "ei prumo" ou equivalente curto, consulte a '
        "tabela de skills disponíveis e leia o SKILL.md da skill `abrir`. Quando shell e "
        "runtime estiverem disponíveis, rodar `prumo` no diretório do workspace é atalho "
        "equivalente.",
        _BOTH,
        _ALL_PROFILES,
    ),
    WrapperRule(
        "runtime-fora-do-path",
        "Se `prumo` não estiver no PATH do host, tente o caminho absoluto de instalação "
        "do runtime neste sistema antes de concluir que ele sumiu.",
        _BOTH,
        _ALL_PROFILES,
    ),
    WrapperRule(
        "briefing-e-curadoria-rica",
        "Se o pedido for briefing explícito, conduza a curadoria rica (skill `briefing` / "
        "`briefing-procedure.md`): email/agenda + panorama numerado único → `decidir`. "
        "O cartão do runtime é a prévia, não o briefing — não encerre nele.",
        _BOTH,
        _ALL_PROFILES,
    ),
    WrapperRule(
        "painel-local-semente",
        "Para o painel local estruturado (semente/backcompat), "
        "`prumo briefing --workspace . --format json`.",
        _BOTH,
    ),
    # Par 8/5 NÃO unificado de propósito: os predicados diferem em substância
    # ("renderizar ações próprias" ⊂ "saber trabalhar com JSON") — unificar
    # mudaria comportamento silenciosamente. Decisão de texto é do dono.
    WrapperRule(
        "start-json-preferido",
        "Se o host souber trabalhar com JSON, prefira `prumo start --format json`.",
        _WRAPPER,
    ),
    WrapperRule(
        "start-json-renderizador",
        "Se o host conseguir renderizar ações próprias, preferir `prumo start --format json` "
        "em vez de reinventar onboarding na unha.",
        _WORKSPACE,
    ),
    WrapperRule(
        "adapter-hints-do-json",
        "Se usar JSON, leia `adapter_hints` e respeite `kind`, `shell_command` e `host_prompt`.",
        _WRAPPER,
    ),
    WrapperRule(
        "contrato-antes-do-esperto",
        "Ao consumir JSON estruturado, o host deve ler `adapter_contract_version`, "
        "`workspace_resolution` e `adapter_hints` antes de bancar o esperto.",
        _WORKSPACE,
    ),
    WrapperRule(
        "flags-antes-da-prosa",
        "Antes de olhar `message`, leia `state_flags`, `degradation`, `next_move` e "
        "`selection_contract`. A prosa vem depois.",
        _BOTH,
    ),
    WrapperRule(
        "degradacao-preserva-e-recupera",
        "Se `degradation.status` vier `error` ou `partial`, preserve o que ainda presta, "
        "mostre o tropeço em uma linha curta e, se houver `action_id` útil, priorize essa "
        "recuperação antes de inventar novo ritual.",
        _BOTH,
    ),
    WrapperRule(
        "nao-reinvente-runtime",
        "Não reinvente `setup`, `migrate`, `repair` ou `auth`. Deixe o runtime tomar a "
        "primeira decisão.",
        _WRAPPER,
    ),
    WrapperRule(
        "nao-simule-comando",
        "Não leia arquivo para simular `prumo`, `briefing` ou `start`. Primeiro execute o "
        "comando real.",
        _BOTH,
        _ALL_PROFILES,
    ),
    WrapperRule(
        "nao-escreva-state",
        "Não escreva `{state_path}` fingindo ser o runtime.",
        _BOTH,
        _ALL_PROFILES,
    ),
    WrapperRule(
        "nao-fabrique-json",
        "Não fabrique JSON de `prumo start --format json` ou "
        "`prumo briefing --workspace . --format json`. Ou retorna a saída real, ou assume "
        "que falhou.",
        _WORKSPACE,
    ),
    WrapperRule(
        "sem-comando-por-curiosidade",
        "Não rode comando extra só porque ficou curioso. Execute o que foi pedido ou o que "
        "o runtime sugeriu.",
        _BOTH,
    ),
    WrapperRule(
        "sem-disco-riscado",
        "Se um comando falhar por uso ou argumento inválido, não repita a mesma linha como "
        "disco riscado.",
        _BOTH,
    ),
    WrapperRule(
        "falha-parcial-preserva",
        "Em falha parcial, preserve o que ainda presta e explique o tropeço em uma linha "
        "curta, sem vazar stack trace nem jargão técnico.",
        _BOTH,
    ),
    WrapperRule(
        "kickoff-sem-cardapio",
        "Se `next_move.id == kickoff`, não abra cardápio de aeroporto. Faça uma segue curta "
        "e convide ao despejo inicial.",
        _BOTH,
    ),
    WrapperRule(
        "sem-backstage",
        "Na invocação curta, não anuncie que vai rodar comando, ler JSON ou abrir arquivo. "
        "Execute primeiro e fale depois.",
        _BOTH,
    ),
    WrapperRule(
        "uma-pergunta-por-vez",
        "Quando houver escolha, prefira uma pergunta por vez e opções curtas. Produto não é "
        "formulário com perfume.",
        _BOTH,
    ),
)


def _validate(surface: str, profile: str) -> None:
    if surface not in SURFACES:
        raise ValueError(f"superfície desconhecida: {surface!r} (válidas: {SURFACES})")
    if profile not in PROFILES:
        raise ValueError(f"perfil desconhecido: {profile!r} (válidos: {PROFILES})")


def rules_for(surface: str, *, profile: str = "full") -> list[str]:
    """Textos (crus, sem numeração) da superfície/perfil, na ordem canônica."""
    _validate(surface, profile)
    return [
        rule.text
        for rule in RULES
        if surface in rule.surfaces and (profile == "full" or profile in rule.profiles)
    ]


def render_rules(surface: str, *, state_path: str = "_state/", profile: str = "full") -> str:
    """Bloco numerado pronto pro template, com `{state_path}` resolvido."""
    texts = rules_for(surface, profile=profile)
    return "\n".join(
        f"{i}. {text.format(state_path=state_path)}" for i, text in enumerate(texts, start=1)
    )
