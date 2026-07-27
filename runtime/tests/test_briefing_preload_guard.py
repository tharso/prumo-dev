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

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
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
VALID_PHASES = {"F0", "F1", "F2", "F3"}

# União canônica da era #195 — TODO arquivo daquela lista precisa seguir
# presente no mapa (o fatiamento move, nunca corta), mais os módulos novos
# da #180. Comparação por NOME de arquivo (o mapa usa paths de workspace).
CANONICAL_FILES_IN_MAP = frozenset(
    {
        "PERFIL.md",
        "ROTINA.md",
        "PESSOAS.md",
        "PRUMO-CORE.md",
        "briefing-procedure.md",
        "load-policy.md",
        "version-update.md",
        "interaction-format.md",
        "runtime-paths.md",
        "cowork-runtime-bridge.md",
        "inbox-processing.md",
        # Novos donos da rota fásica (#180):
        "SKILL.md",
        "CLAUDE.md",
        "AGENT.md",
        "briefing-estado.md",
        "briefing-canais.md",
        "briefing-montagem.md",
        "version-preflight.md",
    }
)

# ── Registro origem→destino (#180) ─────────────────────────────────────────
# Invariante textual → arquivo DONO pós-fatiamento. Era tudo em
# briefing-procedure.md; mover uma frase sem atualizar aqui quebra o guard —
# é o teste `test_moved_guardrails_registry` pedido na issue.

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
    "PAUTA→REGISTRO de concluídos, `Referencias/INDICE.md` e rotação do `Diario/`": ESTADO,
    "Briefing sem a linha de faxina é briefing **fora de conformidade**": MONTAGEM,
    "GERAR o HTML interativo da skill `decidir` e entregá-lo linkado — automaticamente, sem pedir autorização prévia (#218)": MONTAGEM,
    "Sinal de divergência agenda × email (#211)": MONTAGEM,
    "comparar cada compromisso com a agenda da SUA data": MONTAGEM,
    "consulta pontual à agenda de amanhã antes de declarar": MONTAGEM,
    "só com confirmação do usuário; nunca criar sozinho": MONTAGEM,
    # Preflight de versão (#174/#195/#215) → mini-módulo novo
    "prumo version-check --ensure-fresh": PREFLIGHT,
    "Nunca dizer \"versão em dia\" sem ter comparado": PREFLIGHT,
}

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
    lines = skill_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == MANIFEST_HEADING:
            start = i + 1
            break
    assert start is not None, f"heading '{MANIFEST_HEADING}' não encontrado no SKILL"
    rows: list[dict] = []
    started = False
    backtick = re.compile(r"`([^`]+)`")
    for line in lines[start:]:
        s = line.strip()
        if s.startswith("#"):
            break
        if not s.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and (set(cells[0]) <= set("-: ") and cells[0] != "" or cells[0].lower() == "fase"):
            continue
        assert len(cells) == 5 and all(cells), f"linha de mapa malformada: {s}"
        m = backtick.search(cells[2])
        rows.append(
            {
                "phase": cells[0],
                "trigger": cells[1],
                "file": m.group(1).strip() if m else cells[2],
                "section": cells[3],
            }
        )
    return rows


class PhaseMapTests(unittest.TestCase):
    """O mapa do SKILL é a lista única (#195 emendada) e é semanticamente válido."""

    def setUp(self) -> None:
        self.skill_text = SKILL.read_text(encoding="utf-8")
        self.rows = _parse_map_rows(self.skill_text)

    def test_map_semantics(self) -> None:
        seen: set[tuple[str, str]] = set()
        for row in self.rows:
            with self.subTest(file=row["file"], section=row["section"]):
                self.assertIn(row["phase"], VALID_PHASES, f"fase inválida: {row['phase']}")
                self.assertTrue(row["trigger"], "gatilho vazio")
                key = (row["file"], row["section"])
                self.assertNotIn(key, seen, f"duplicata no mapa: {key}")
                seen.add(key)

    def test_map_covers_canonical_union(self) -> None:
        names = {Path(row["file"]).name for row in self.rows}
        missing = CANONICAL_FILES_IN_MAP - names
        self.assertFalse(
            missing,
            f"arquivos da união canônica sumiram do mapa (mover ≠ cortar): {sorted(missing)}",
        )

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
        for invariant, owner in GUARDRAIL_OWNERS.items():
            with self.subTest(invariant=invariant[:60], owner=owner.name):
                text = cache.setdefault(owner, owner.read_text(encoding="utf-8"))
                self.assertIn(
                    invariant,
                    text,
                    f"invariante sumiu do dono {owner.name}: {invariant!r}",
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

    def test_version_update_treats_smaller_remote_as_suspect(self) -> None:
        # #215: o canônico completo segue dono do protocolo de suspeita; o
        # preflight referencia (âncora própria no registro acima).
        text = VERSION_UPDATE.read_text(encoding="utf-8")
        for anchor in (
            "resposta SUSPEITA — nunca \"em dia\" (#215)",
            "cache-busting",
            "declarar status **desconhecido**",
            "**Nunca** ler \"remoto menor\" como \"estou em dia\"",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)
        self.assertIn("resposta SUSPEITA (#215)", PREFLIGHT.read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
