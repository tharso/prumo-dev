"""#195 (emendada pela #180): guards textuais da rota fásica do briefing.

1. Lista única: o mapa de fases do `briefing/SKILL.md` é a ÚNICA enumeração
   de carregamento (a Pré-carga do procedure foi emendada pra lá na #180);
   a espinha não mantém segunda lista.
2. Registro origem→destino (#180): cada invariante da era pré-fásica tem um
   DONO nomeado pós-fatiamento — remoção ou mudança de dono quebra aqui.
3. Validação semântica do mapa (emenda A1 do design): vocabulário de fases,
   gatilhos não-vazios, sem duplicata, cobertura da união canônica.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Parser ÚNICO do manifesto (review Codex r2 do #180): o guard reusa o
# parse_manifest do audit — dois parsers do mesmo formato divergiriam.
_spec = importlib.util.spec_from_file_location(
    "briefing_route_audit", REPO_ROOT / "scripts" / "briefing_route_audit.py"
)
_audit = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("briefing_route_audit", _audit)
_spec.loader.exec_module(_audit)
MODULES = REPO_ROOT / "skills" / "prumo" / "references" / "modules"
SKILL = REPO_ROOT / "skills" / "briefing" / "SKILL.md"
ESPINHA = MODULES / "briefing-procedure.md"
ESTADO = MODULES / "briefing-estado.md"
CANAIS = MODULES / "briefing-canais.md"
MONTAGEM = MODULES / "briefing-montagem.md"
PREFLIGHT = MODULES / "version-preflight.md"
VERSION_UPDATE = MODULES / "version-update.md"
FAXINA = MODULES / "faxina.md"

MANIFEST_HEADING = "## Mapa de carregamento por fase"
# F4 existe como fase do contrato (#177): fechamento — não carrega material
# novo (a seção mora em briefing-montagem.md, já em contexto desde F3).
VALID_PHASES = {"F0", "F1", "F2", "F3", "F4"}

# O MAPA ESPERADO, EXATO (rounds 2-3 do Codex no #180): tuplas
# (fase, gatilho, arquivo, seção, tipo) — igualdade de CONJUNTO com o
# manifesto, TODAS as células. Mudança em qualquer uma só entra atualizando
# aqui conscientemente.
_M = ".prumo/skills/prumo/references/modules"
EXPECTED_MAP = frozenset(
    {
        ("F0", "sempre", "CLAUDE.md", "(integral)", "wrapper da raiz"),
        ("F0", "sempre", "Prumo/AGENT.md", "(integral)", "porta canônica"),
        ("F0", "sempre", ".prumo/system/PRUMO-CORE.md", "até: # Parte 2 — Playbooks operacionais", "core P1"),
        # #248: dispatch.md é leitura obrigatória de abertura (opening_reads
        # do AGENT.md) — entrou no cesto na recalibração do termômetro.
        # #228 fase 2: a porta carrega o dispatch ATÉ a tabela de intenções; a
        # tabela é consultada DEPOIS que o usuário fala — por construção, fora
        # do "antes do primeiro dado".
        ("F0", "sempre", ".prumo/skills/prumo/references/modules/dispatch.md", "até: ## Roteamento por intenção", "abertura (#248)"),
        ("F1", "ao resolver a intenção do usuário (nunca na abertura)", ".prumo/skills/prumo/references/modules/dispatch.md", "## Roteamento por intenção", "roteamento (#228)"),
        # #241: mapa autoral lido na abertura quando existir — conta no cesto
        # quando presente; ausência tolerada (gatilho `sempre (autoral)`).
        ("F0", "sempre (autoral)", "Prumo/Agente/MAPA-AUTORAL.md", "(integral)", "caminhos autorais (#241)"),
        ("F1", "sempre", ".prumo/skills/briefing/SKILL.md", "(integral)", "esta skill"),
        ("F1", "sempre", f"{_M}/briefing-procedure.md", "(integral)", "espinha"),
        ("F1", "sempre", ".prumo/system/PRUMO-CORE.md", "## Guardrails", "core (seção)"),
        ("F1", "sempre", "Prumo/Agente/PERFIL.md", "(integral)", "config"),
        ("F1", "sempre", "Prumo/Agente/ROTINA.md", "(integral)", "config"),
        ("F1", "sempre", "Prumo/Agente/PESSOAS.md", "(integral)", "remetentes"),
        ("F1", "sempre", f"{_M}/briefing-estado.md", "(integral)", "estado"),
        ("F1", "sempre", f"{_M}/version-preflight.md", "(integral)", "preflight"),
        ("F1", "sem semente, `faxina.schema` ≠ `prumo_faxina_thresholds.v1` OU override divergente", f"{_M}/faxina-thresholds.md", "(integral)", "números da faxina (#258)"),
        ("F1", "override do usuário existir", "Prumo/Custom/rules/faxina-thresholds.md", "(integral)", "overrides"),
        ("F1", "oferta/execução de update (warning/alert)", f"{_M}/version-update.md", "(integral)", "canônico do update"),
        ("F1", "scripts via shell", f"{_M}/runtime-paths.md", "(integral)", "scripts"),
        ("F1", "shell com runtime alcançável", f"{_M}/cowork-runtime-bridge.md", "(integral)", "ponte do runtime"),
        ("F1", "antes de QUALQUER comando do runtime (formato e invocação)", f"{_M}/runtime-consumo.md", "(integral)", "consumo"),
        (
            "F1",
            "família de faxina pendente (execução — a checagem mínima mora no estado)",
            f"{_M}/faxina.md",
            "(integral)",
            "executor",
        ),
        # #245: a gramática dos marcadores (dona: load-policy) carrega ANTES do
        # gate de "caixa declarada" — senão o reconhecimento seria circular.
        (
            "F2",
            "`MAPA-AUTORAL.md` com nota (gramática dos marcadores)",
            f"{_M}/load-policy.md",
            "## Listagem de diretórios (perímetro de leitura, #194)",
            "marcadores (#245)",
        ),
        (
            "F2",
            "antes da triagem local do Inbox4Mobile, de caixa declarada OU de abrir email/agenda",
            f"{_M}/briefing-canais.md",
            "(integral)",
            "canais",
        ),
        ("F2", "Inbox4Mobile com itens novos", f"{_M}/inbox-processing.md", "(integral)", "inbox"),
        ("F2", "antes de filtrar email (se existir)", "Prumo/Referencias/EMAIL-CURADORIA.md", "(integral)", "curadoria"),
        (
            "F2",
            "canal de email disponível E EMAIL-CURADORIA.md ausente (criação)",
            ".prumo/skills/prumo/references/file-templates.md",
            "## Prumo/Referencias/EMAIL-CURADORIA.md",
            "template",
        ),
        ("F2", "aprofundamento (predicado g / fallback por fonte)", f"{_M}/load-policy.md", "(integral)", "leitura"),
        ("F3", "ao montar o panorama", f"{_M}/briefing-montagem.md", "(integral)", "dois tempos"),
        ("F3", "ao montar o panorama", f"{_M}/interaction-format.md", "(integral)", "numeração"),
        ("F3", "6+ itens acionáveis (#218)", ".prumo/skills/decidir/SKILL.md", "(integral)", "despacho"),
    }
)

# ── Registro origem→destino (#180) ─────────────────────────────────────────
# Invariante textual → arquivo DONO pós-fatiamento. Era tudo em
# briefing-procedure.md; mover uma frase sem atualizar aqui quebra o guard —
# é o teste `test_moved_guardrails_registry` pedido na issue.

# #258: duas invariantes SAÍRAM daqui por OBSOLESCÊNCIA, não por mudança de
# dono — "threshold efetivo ≠ declarado" e "recalcular direto da fonte" eram
# remendo para a semente declarar sempre o default. Com o runtime aplicando o
# override, a semente parou de mentir e a obrigação deixou de existir. Ver
# test_faxina_thresholds.py (que prova o novo comportamento) e DECISIONS.
GUARDRAIL_OWNERS: dict[str, Path] = {
    # DAG do ex-Passo 4 (#195/#196/#205) → canais
    "Ordem de execução (DAG lógico, execução ADAPTATIVA": CANAIS,
    "Primeiro o local, sem esperar o externo": CANAIS,
    "Paralelismo por subagente: DESLIGADO por default": CANAIS,
    "Classificação só depois do contexto local": CANAIS,
    "Escritas serializadas": CANAIS,
    "não cancela os demais": CANAIS,
    # Camada 1 (#210) → canais
    "label:Prumo after:{ontem}": CANAIS,
    "(subject:PRUMO OR subject:INBOX) after:{ontem}": CANAIS,
    "NENHUM remetente é excluído na query": CANAIS,
    "Pós-filtro EXATO obrigatório (#210)": CANAIS,
    "(?<!\\w)(?:PRUMO|INBOX):": CANAIS,
    "`ÉPRUMO: oferta` → NÃO casa": CANAIS,
    "`Run failed: tharso/prumo-dev CI` → NÃO casa": CANAIS,
    "`SUPERPRUMO: promoção` → NÃO casa": CANAIS,
    "segue pra Camada 2 como email comum": CANAIS,
    # Estágio 1/2 e defesas (#156/#195) → canais
    "prevalecem sobre o sinal de automatização": CANAIS,
    "rodam em todo corpo lido": CANAIS,
    # Inbox4Mobile local A/B (#196) → canais
    "Estágio LOCAL, ANTES da emissão do primeiro tempo — SEM abrir bruto": CANAIS,
    "Abrir arquivo bruto do Inbox4Mobile (Estágio B — aprofundamento) só DEPOIS da primeira entrega": CANAIS,
    # Dois tempos (#196) → montagem (emissão/escape/variantes) e espinha (numeração)
    "antes de aguardar qualquer resultado de email/calendário": MONTAGEM,
    "nunca renumerar": MONTAGEM,
    'sem reiniciar entre seções **nem entre os dois tempos (#196)**': ESPINHA,
    '"segue tudo"/"continua" é o CONTRÁRIO de escape': MONTAGEM,
    "Quando cada variante está COMPLETA": MONTAGEM,
    "Escape do usuário (qualquer variante) | nunca": MONTAGEM,
    "seguir sem esperar resposta": MONTAGEM,
    # Transportes da semente (#197/#206/#216) → estado
    "arquivo-semente `.prumo/state/local-panorama.json` (#216": ESTADO,
    "gate TRIPLO": ESTADO,
    "`local_panorama.generated_for` == a data de HOJE no fuso do workspace": ESTADO,
    "Frescor POR FONTE**: o arquivo carrega `source_mtimes`": ESTADO,
    "`inbox4mobile_manifest`": ESTADO,
    "O agente **NUNCA escreve** esse arquivo": ESTADO,
    "Gate por CAPACIDADE, não por presença de binário (#206)": ESTADO,
    # Conformidade (#214/#217/#218/#211) → montagem/estado
    "proibido de escrever `last-briefing.json`": MONTAGEM,
    "seguem permitidos** — a proibição é sobre fingir ser o runtime": MONTAGEM,
    "Sem runtime aqui, o dia não fica marcado": MONTAGEM,
    "A checagem de faxina declara o resultado SEMPRE (#217": ESTADO,
    "só depois de olhar as CINCO famílias do `faxina.md`": ESTADO,
    # As 5 checagens baratas moram no estado (round 2: sem circularidade —
    # checar não exige abrir o executor).
    "**PAUTA→REGISTRO de concluídos**": ESTADO,
    "**`Referencias/INDICE.md`**": ESTADO,
    "**Rotação do `Diario/`**": ESTADO,
    "carregar `faxina.md` e executar": ESTADO,
    # Override × semente (round 4): threshold efetivo ≠ declarado pela
    # semente → recalcular da fonte, nunca usar o pré-calculado.
    "Briefing sem a linha de faxina é briefing **fora de conformidade**": MONTAGEM,
    "GERAR o HTML interativo da skill `decidir` e entregá-lo linkado — automaticamente, sem pedir autorização prévia (#218)": MONTAGEM,
    # #211 (review Codex r1 do #180): DETECÇÃO nos canais (comparação +
    # consulta pontual); APRESENTAÇÃO/oferta na montagem.
    "Detecção de divergência agenda × email (#211": CANAIS,
    "comparar cada compromisso com a agenda da SUA data": CANAIS,
    "consulta pontual à agenda de amanhã antes de declarar": CANAIS,
    "Sinal de divergência agenda × email (#211)": MONTAGEM,
    "só com confirmação do usuário; nunca criar sozinho": MONTAGEM,
    # Relatório de 27/07 (B1/B2/B3 — decisões do dono nas perguntas didáticas):
    # A regra de formato foi corrigida na #304 (03/08): a escalada por
    # "texto puro" pedia um degrau que o conector não tem — as âncoras
    # novas travam a regra executável e o predicado de anexo.
    "FORMATO da leitura de corpo (corrigido em 03/08, #304": CANAIS,
    "extraindo apenas `plaintextBody` — e sem repropagar `htmlBody` adiante": CANAIS,
    "Política de cobertura (FIXA — decisão do dono em 27/07": CANAIS,
    "Respostas ao que o usuário enviou** desde o último briefing": CANAIS,
    "Anexo é substância (#304)": CANAIS,
    "nas threads** selecionar as mensagens EXTERNAS recebidas": CANAIS,
    "Declarar a cobertura em uma linha": CANAIS,
    # #236 — o protocolo mora nos CANAIS (é lá que a query roda); a completude
    # do briefing segue dona da MONTAGEM. Dois donos semânticos de
    # `--mark-done` foi o risco que o review do plano pegou.
    "Prova de predicado de busca (#236)": CANAIS,
    "query nunca é testemunha de si mesma": CANAIS,
    "Nada é aprovado por osmose": CANAIS,
    "três validações novas por briefing": CANAIS,
    "Braço `INCONCLUSIVO` (#236) — este módulo é o dono da completude": MONTAGEM,
    "em Cowork/host containerizado, **WebFetch PRIMEIRO**": PREFLIGHT,
    '"não consegui checar" só depois de esgotar os dois': PREFLIGHT,
    # Preflight de versão (#174/#195/#215) → mini-módulo novo. O protocolo
    # MÍNIMO do #215 mora aqui (review Codex r1 do #180: remoto-menor pode
    # nunca acionar a oferta — o dono grande pode nunca carregar).
    "prumo version-check --ensure-fresh": PREFLIGHT,
    "Nunca dizer \"versão em dia\" sem ter comparado": PREFLIGHT,
    "re-tentar UMA vez com **cache-busting**": PREFLIGHT,
    "**declarar status desconhecido** em uma linha": PREFLIGHT,
}

# Âncoras com RESUMO legítimo em outro arquivo (a espinha resume os gates;
# exclusividade estrita quebraria resumos declarados como tal).
EXCLUSIVITY_EXEMPT = frozenset(
    {
        "gate TRIPLO",
        "prumo version-check --ensure-fresh",
        "`inbox4mobile_manifest`",  # resumo do gate 2 na espinha é declarado
    }
)

_PHASE_FILES = (ESPINHA, ESTADO, CANAIS, MONTAGEM, PREFLIGHT)

# Predicados de leitura de corpo — verificados DENTRO do bloco do Estágio 2
# (busca global deixaria remoção passar batida; Codex, diff r2 da #195).
BODY_READ_PREDICATE_LABELS = {
    "(a)": "canal prioritário",
    "(b)": "remetente é **pessoa**",
    "(c)": "thread tem participação do usuário",
    "(d)": "prazo, pergunta direta ou pedido de ação",
    "(e)": "snippet é inconclusivo",
    "(f)": "sempre-relevante",
    "(g)": "heurística de aprofundamento",
}

# O resumo da SKILL não pode regredir pra ambiguidade que a #218 matou.
CONFORMIDADE_SKILL_INVARIANTS = (
    "**gerar automaticamente o despacho visual da skill `decidir`",
    "sem perguntar antes (#218)",
)

# #212: a poda do _processed.json é por idade COM salvaguarda.
FAXINA_INVARIANTS = (
    "Salvaguarda (#212): nunca remover entrada cujo arquivo ainda existe",
    "Arquivo ainda presente → não mover, não podar; apenas sinalizar",
)


def _parse_map_rows(skill_text: str) -> list[dict]:
    parsed = _audit.parse_manifest(skill_text)
    assert parsed is not None, f"heading '{MANIFEST_HEADING}' não encontrado no SKILL"
    rows, invalid = parsed
    assert not invalid, f"linhas de mapa malformadas: {invalid}"
    return rows


class PhaseMapTests(unittest.TestCase):
    """O mapa do SKILL é a lista única (#195 emendada) e é semanticamente válido."""

    def setUp(self) -> None:
        self.skill_text = SKILL.read_text(encoding="utf-8")
        self.rows = _parse_map_rows(self.skill_text)

    def test_map_is_exactly_the_expected_set(self) -> None:
        # Igualdade de CONJUNTO em TODAS as células (Codex r2-r3): fase,
        # gatilho, arquivo, seção e tipo — qualquer troca quebra aqui.
        actual = {
            (row["phase"], row["trigger"], row["file"], row["section"], row["type"])
            for row in self.rows
        }
        self.assertEqual(len(actual), len(self.rows), "linha duplicada no mapa")
        missing = EXPECTED_MAP - actual
        extra = actual - EXPECTED_MAP
        self.assertFalse(
            missing or extra,
            f"mapa divergiu do esperado — faltando={sorted(missing)} sobrando={sorted(extra)}",
        )
        for row in actual:
            self.assertIn(row[0], VALID_PHASES)

    def test_f4_declared_as_phase_without_new_material(self) -> None:
        # F4 é fase do contrato (#177): fechamento sem carregamento novo —
        # declarada em prosa, nunca linha fantasma na tabela.
        self.assertIn("F4", self.skill_text)
        self.assertIn("não carrega material novo", self.skill_text)
        self.assertIn("## Escrita e fechamento", self.skill_text)

    def test_map_declared_repo_files_exist(self) -> None:
        # Arquivos de skill/módulo declarados no mapa têm que existir no repo
        # (os de workspace — Prumo/, CLAUDE.md, core — nascem no install).
        for row in self.rows:
            marker = ".prumo/skills/"
            if row["file"].startswith(marker):
                repo_path = REPO_ROOT / "skills" / row["file"][len(marker):]
                with self.subTest(file=row["file"]):
                    self.assertTrue(repo_path.exists(), f"declarado no mapa, ausente no repo: {repo_path}")

    def test_espinha_does_not_keep_second_preload_list(self) -> None:
        espinha = ESPINHA.read_text(encoding="utf-8")
        self.assertNotIn("## Pré-carga obrigatória", espinha)
        self.assertIn("Mapa de carregamento por\n> fase", espinha.replace("`", ""))

    def test_skill_conformidade_summary_kept(self) -> None:
        for invariant in CONFORMIDADE_SKILL_INVARIANTS:
            with self.subTest(invariant=invariant):
                self.assertIn(invariant, self.skill_text)


class MovedGuardrailsRegistryTests(unittest.TestCase):
    """Registro origem→destino (#180): cada invariante no seu dono."""

    def test_moved_guardrails_registry(self) -> None:
        cache: dict[Path, str] = {}

        def _text(path: Path) -> str:
            return cache.setdefault(path, path.read_text(encoding="utf-8"))

        for invariant, owner in GUARDRAIL_OWNERS.items():
            with self.subTest(invariant=invariant[:60], owner=owner.name):
                self.assertIn(
                    invariant,
                    _text(owner),
                    f"invariante sumiu do dono {owner.name}: {invariant!r}",
                )
                if invariant in EXCLUSIVITY_EXEMPT:
                    continue
                # Exclusividade (review Codex r1 do #180): dono ÚNICO — a
                # mesma âncora reaparecendo noutro módulo de fase é a cópia
                # divergente que a regra "um dono por regra" mata.
                for other in _PHASE_FILES:
                    if other == owner:
                        continue
                    self.assertNotIn(
                        invariant,
                        _text(other),
                        f"invariante duplicada fora do dono: {invariant!r} em {other.name}",
                    )

    def test_body_read_predicates_present_in_canais(self) -> None:
        text = CANAIS.read_text(encoding="utf-8")
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

    def test_camada1_post_filter_reference_oracle(self) -> None:
        # Oráculo executável da regra ESCRITA (a MESMA regex de referência do
        # módulo): token com fronteira — substring pura aceitaria SUPERPRUMO:.
        post_filter = re.compile(r"(?<!\w)(?:PRUMO|INBOX):").search
        cases = {
            "PRUMO: pagar o boleto amanhã": True,
            "Re: INBOX: link pra ler depois": True,
            "Run failed: tharso/prumo-dev CI": False,
            "prumo update disponível": False,
            "[tharso/prumo-dev] Run failed: Specs canônicas": False,
            "Fwd: PRUMO: comprovante": True,
            "SUPERPRUMO: promoção imperdível": False,
            "MYINBOX: novidades da semana": False,
            "ÉPRUMO: oferta relâmpago": False,
        }
        for subject, expected in cases.items():
            with self.subTest(subject=subject):
                self.assertEqual(bool(post_filter(subject)), expected)

    def test_preflight_owns_smaller_remote_protocol(self) -> None:
        # #215 (round 2 do #180): dono ÚNICO do protocolo é o preflight —
        # que roda SEMPRE; o canônico do update apenas aponta pra ele.
        preflight = PREFLIGHT.read_text(encoding="utf-8")
        for anchor in (
            "resposta SUSPEITA (#215)",
            "re-tentar UMA vez com **cache-busting**",
            "**declarar status desconhecido** em uma linha",
            "**nunca** ler \"remoto menor\" como \"estou em dia\"",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, preflight)
        update = VERSION_UPDATE.read_text(encoding="utf-8")
        self.assertIn("dono do protocolo é o `version-preflight.md`", update)
        self.assertIn("**Nunca** ler \"remoto menor\" como \"estou em dia\"", update)

    def test_version_cache_producer_cited_in_both_modules(self) -> None:
        for path in (PREFLIGHT, VERSION_UPDATE):
            with self.subTest(module=path.name):
                self.assertIn("prumo version-check --ensure-fresh", path.read_text(encoding="utf-8"))
        self.assertIn("no máximo 1x/24h", VERSION_UPDATE.read_text(encoding="utf-8"))

    def test_faxina_prune_safeguard_present(self) -> None:
        faxina = FAXINA.read_text(encoding="utf-8")
        for invariant in FAXINA_INVARIANTS:
            with self.subTest(invariant=invariant):
                self.assertIn(invariant, faxina)

    def test_override_contract_is_executable(self) -> None:
        # #258 (substitui o contrato da r5 do #180): antes o runtime DECLARAVA
        # sempre o default e o agente é que recalculava quando o efetivo
        # divergisse — remendo que dependia de o doc estar em contexto. Agora o
        # runtime APLICA o override e a semente transporta o efetivo; o contrato
        # segue executável de ponta a ponta, com outra mecânica.
        sys.path.insert(0, str(REPO_ROOT / "runtime"))
        from prumo_runtime import faxina_thresholds

        # 1. o runtime conhece TODOS os números do doc (paridade travada em
        #    test_faxina_thresholds.py) e sabe onde mora o override do usuário
        self.assertEqual(faxina_thresholds.DEFAULTS["processed_expiry_days"], 14)
        self.assertIn("Custom", str(faxina_thresholds.override_path(REPO_ROOT)))
        # 2. o dono dos números exemplifica um override diferente do default
        thresholds = (MODULES / "faxina-thresholds.md").read_text(encoding="utf-8")
        self.assertIn("- processed_expiry_days: 7", thresholds)
        # 3. o consumidor lê da semente, com fallback declarado pra quem não tem
        estado = ESTADO.read_text(encoding="utf-8")
        self.assertIn("`faxina.thresholds` da semente", estado)
        self.assertIn("Sem semente", estado)
        self.assertNotIn(
            "threshold efetivo ≠ declarado pela semente",
            estado,
            "remendo obsoleto voltou: a semente não declara mais um número e conta por outro",
        )
        # 4. E o executor não guarda literal nenhum dos números.
        faxina = FAXINA.read_text(encoding="utf-8")
        for param in (
            "max_items",
            "archive_age_days",
            "processed_expiry_days",
            "diario_expiry_days",
            "referencias_subcategorize_at",
        ):
            with self.subTest(param=param):
                self.assertIn(param, faxina)


if __name__ == "__main__":
    unittest.main()
