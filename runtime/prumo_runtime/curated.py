"""Snapshot de arquivo curado (#262 — P8+P9 do relatório de incidente de 29/07).

Por que existe: em 27/07 uma sessão reescreveu `Prumo/Referencias/INDICE.md`
com escrita INTEGRAL querendo acrescentar quatro linhas — 48 entradas viraram
5, e o dano ficou invisível por dois dias. Todo backup que o produto tinha era
disparado por comando do runtime (`setup`, `migrate`, `repair`, `sanitize`);
nenhum cobria o caminho de edição comum. O que o produto sabe recriar sozinho
tinha cópia; o que era insubstituível não tinha nenhuma.

Onde o snapshot mora: o Prumo NÃO tem gancho na ferramenta de escrita do agente
hospedeiro, então "antes de cada escrita" só existiria como regra que o agente
precisa lembrar — a proteção que falhou. A cópia pega carona nos rituais que o
runtime já é dono (`prumo seed` e `prumo briefing`), o que dá garantia mecânica
ao custo de a cópia ficar no máximo uma sessão atrasada.

Módulo folha: importa apenas `workspace_paths`, `projetos` (só as marcas de
pulso), `faxina_thresholds` e `backup` — todos folhas. Nunca `workspace.py`.
"""

from __future__ import annotations

import hashlib
import json
import stat as stat_module
from datetime import datetime, timezone
from pathlib import Path

from prumo_runtime import faxina_thresholds
from prumo_runtime.backup import iter_backup_roots
from prumo_runtime.projetos import PULSO_BEGIN, PULSO_END
from prumo_runtime.workspace_paths import (
    is_legacy_flat_workspace,
    is_prumo_workspace,
    workspace_paths,
)

SCOPE = "curated"
# Código de `skipped` do bloqueio por layout antigo (#268). É CÓDIGO, igual a
# `sem-mudanca` — a frase pro usuário nasce no `render_report`.
SKIPPED_LEGACY_FLAT = "layout-antigo"
# Não-nested que também não é workspace legado: pula igual, mas SEM oferecer
# migração — pasta comum não tem pra onde migrar.
SKIPPED_NOT_NESTED = "nao-nested"
MANIFEST_NAME = "_manifest.json"
MANIFEST_SCHEMA = "prumo_curated_snapshot.v1"

# Classes de VIGILÂNCIA. O snapshot cobre todas; o alerta de encolhimento só
# faz sentido onde encolher é anomalia (Codex, design r1: taxonomia binária
# fura em arquivo híbrido).
FLOW = "fluxo"                 # existe pra ser drenado — encolher é o contrato
HYBRID = "hibrido"             # parte gerada, parte autoral
ACCUMULATIVE = "acumulativo"   # catálogo: encolher brusco é suspeito

# Os conjuntos de cada classe vêm de `WorkspacePaths` (paths completos,
# cientes do layout nested/flat) — ver `curated_flow_paths`/`curated_hybrid_paths`.

# Teto por arquivo: acima disso a cópia diária deixa de ser barata. O que passa
# é REPORTADO, nunca descartado em silêncio.
MAX_FILE_BYTES = 512 * 1024
# Piso do alerta: em arquivo minúsculo qualquer edição é percentualmente
# enorme. Sem piso, o alarme viraria ruído no primeiro dia de workspace novo.
MIN_ALERT_BYTES = 200
# Sumiço completo é 100% de encolhimento — o caso mais grave, não o mais leve.
GONE = "ausente"
# Existe, mas ficou fora da medição (cresceu além do teto, ilegível, não-UTF-8).
# Sem este estado, crescer virava "SUMIU" — a sirene de perda tocando pra um
# arquivo que aumentou (Codex, 262I-1).
UNMEASURABLE = "nao-mensuravel"
# Sumiu daqui, mas há gêmeo byte a byte no acervo: indício, não prova.
ARCHIVED = "provavelmente-arquivado"


def watch_class(
    relative_path: str,
    flow_paths: frozenset[str] = frozenset(),
    hybrid_paths: frozenset[str] = frozenset(),
) -> str:
    """Classifica por PATH COMPLETO, nunca por basename.

    Uma ficha chamada `Referencias/PAUTA.md` é catálogo do usuário: com
    classificação por nome ela cairia em `fluxo` e sumiria sem alarme
    (Codex, 262F-5).
    """
    if relative_path in flow_paths:
        return FLOW
    if relative_path in hybrid_paths:
        return HYBRID
    return ACCUMULATIVE


def _flat_name(relative_path: str) -> str:
    """Convenção `__` do runtime-migrate: `a/b/c.md` → `a__b__c.md`.

    NÃO é bijetiva (`a/b.md` e `a__b.md` colidem), e por isso o caminho de
    volta é o manifesto — nunca o nome do arquivo (mesma lição da sanitize).
    """
    return relative_path.replace("/", "__")


def _pulso_partition(text: str) -> tuple[str, str | None]:
    """Devolve (texto fora dos blocos de pulso, erro de integridade).

    Estrutura inválida — `BEGIN` aninhado, `END` órfão, `BEGIN` sem fechar —
    é FALHA CONSERVADORA: devolve o texto inteiro e nomeia o erro. Excluir o
    sufixo de um marcador órfão faria conteúdo autoral sumir da conta sem
    alarme nenhum, que é o oposto do propósito deste módulo (Codex, 262D-2).
    """
    kept: list[str] = []
    inside = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == PULSO_BEGIN:
            if inside:
                return text, "bloco de pulso aninhado"
            inside = True
            continue
        if stripped == PULSO_END:
            if not inside:
                return text, "fim de bloco de pulso sem começo"
            inside = False
            continue
        if not inside:
            kept.append(line)
    if inside:
        return text, "bloco de pulso aberto sem fechar"
    return "".join(kept), None


def measured_size(data: bytes, klass: str) -> int:
    """Bytes que o alerta vigia.

    No híbrido, o miolo dos blocos de pulso sai da conta: ele encolhe por
    contrato a cada `projetos --sync`, e contá-lo produziria falso alarme
    justamente no comando que o produto oferece.
    """
    if klass != HYBRID:
        return len(data)
    kept, _ = _pulso_partition(data.decode("utf-8"))
    return len(kept.encode("utf-8"))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _under_backup_root(workspace: Path, source: Path) -> bool:
    """Origem que cai dentro de qualquer raiz de backup não é conteúdo de
    trabalho — copiá-la aninharia backup em backup (#178). Compara os
    caminhos RESOLVIDOS, porque o vetor real é `Referencias/` ser symlink
    pra dentro de `.prumo/backups/` (Codex, 262D-7)."""
    try:
        resolved = source.resolve()
    except OSError:
        return True
    for root in iter_backup_roots(workspace):
        try:
            resolved.relative_to(root.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


def _has_symlink_ancestor(workspace: Path, relative: str) -> bool:
    """Cerca da leitura, no molde do `_require_clean_target` da semente
    (#189): nenhum componente entre o workspace e a origem pode ser link."""
    probe = workspace
    for part in Path(relative).parts:
        probe = probe / part
        try:
            if probe.is_symlink():
                return True
        except OSError:
            return True
    return False


def _check_roots(paths, errors: list[str]) -> None:
    """Raiz que existe mas NÃO é diretório fura o inventário em silêncio:
    `Referencias/` virado arquivo faz o glob devolver nada e todo `is_file()`
    dos filhos dar `False`, então nada entrava em `coleta` e nascia uma
    baseline "completa" sem referência nenhuma (Codex, 262F-2)."""
    for root in paths.curated_roots():
        try:
            if root.exists() and not root.is_dir():
                errors.append(
                    f"{paths.relative(root)}: existe mas não é diretório — inventário furado"
                )
        except OSError as exc:
            errors.append(f"{paths.relative(root)}: {exc}")


def _read_current(paths, errors: list[str]) -> tuple[dict[str, bytes], list[str], set[str]]:
    """Lê os curados existentes. Devolve (bytes por path, oversized, presentes
    sem medida).

    Ausência LEGÍTIMA (arquivo que nunca existiu) é silêncio; qualquer outra
    falha de `stat` vira erro de coleta — distinguir as duas é o que impede o
    retrato furado de se declarar completo.
    """
    _check_roots(paths, errors)
    current: dict[str, bytes] = {}
    oversized: list[str] = []
    # Presente em disco, porém fora de `current`: NÃO é sumiço.
    presentes_sem_medida: set[str] = set()
    for rel in paths.curated_relative_paths():
        source = paths.root / rel
        try:
            if _has_symlink_ancestor(paths.root, rel) or _under_backup_root(paths.root, source):
                errors.append(f"{rel}: caminho atravessa link ou cai dentro do backup")
                # Recusado, mas EXISTE: não pode ser lido como sumiço.
                presentes_sem_medida.add(rel)
                continue
            try:
                st = source.stat()
            except FileNotFoundError:
                continue  # nunca existiu: ausência legítima
            except NotADirectoryError as exc:
                errors.append(f"{rel}: {exc}")
                continue
            if not stat_module.S_ISREG(st.st_mode):
                errors.append(f"{rel}: existe mas não é arquivo regular")
                presentes_sem_medida.add(rel)
                continue
            if st.st_size > MAX_FILE_BYTES:
                oversized.append(rel)
                presentes_sem_medida.add(rel)
                continue
            # BYTES, nunca `read_text`: o modo texto normaliza CRLF na leitura
            # e retraduz na escrita, então a "cópia" poderia diferir do
            # original e o digest autenticaria o texto, não o arquivo
            # (Codex, 262G-1). Backup que não devolve os bytes não é backup.
            data = source.read_bytes()
            data.decode("utf-8")  # curado é texto; binário aqui é erro
            current[rel] = data
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: {exc}")
            presentes_sem_medida.add(rel)
    return current, oversized, presentes_sem_medida


def _manifest_of(stamp_dir: Path) -> dict | None:
    try:
        raw = json.loads((stamp_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or raw.get("schema") != MANIFEST_SCHEMA:
        return None
    files, digests = raw.get("files"), raw.get("digests")
    if not isinstance(files, dict) or not isinstance(digests, dict):
        return None
    # Estrutura frouxa aqui explodia lá na frente: `digests: []` chegava em
    # `_validate_candidate`, estourava `AttributeError` no boundary global e
    # o snapshot abortava PRA SEMPRE — despertador tocando enquanto a casa
    # queima (Codex, 262G-2).
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
        return None
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in digests.items()):
        return None
    if set(files) != set(digests) or len(set(files.values())) != len(files):
        return None
    if any("/" in k or "\\" in k or k in {"", ".", ".."} for k in files):
        return None
    if not isinstance(raw.get("complete"), bool):
        return None
    oversized = raw.get("oversized", [])
    if not isinstance(oversized, list) or not all(isinstance(v, str) for v in oversized):
        # `oversized: [{}]` passava aqui e estourava `TypeError` no `set()` lá
        # na frente — e, como o boundary só registra, o MESMO manifesto
        # repetia a pane em todo ritual (Codex, 262H-1).
        return None
    if len(set(oversized)) != len(oversized) or set(oversized) & set(files.values()):
        return None
    if _parse_instant(raw.get("captured_at_utc")) is None:
        return None
    return raw


def _parse_instant(value) -> datetime | None:
    """`captured_at_utc` tem de ser INSTANTE, não string qualquer: ordenar
    lexicalmente um campo malformado poderia eleger a régua errada
    (Codex, 262G-5)."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _validate_candidate(stamp_dir: Path, manifest: dict) -> tuple[dict[str, bytes], str | None]:
    """Lê e CONFERE cada cópia declarada contra o digest do manifesto.

    Manifesto que diz `complete: true` não prova que as cópias existem: se a
    do índice sumisse e o original também, os dois lados ficariam sem ela,
    `equivalente` daria verdadeiro e o sumiço passaria calado. Régua que não
    se verifica é papel timbrado (Codex, 262F-1).
    """
    conteudo: dict[str, bytes] = {}
    digests = manifest["digests"]
    for flat, rel in manifest["files"].items():
        # O mapeamento tem que bater com a função que o gerou (#265). Sem
        # isto, adulteração COERENTE — `files` e `digests` consistentes entre
        # si, com o nome achatado trocado — passava, e `previous_copy`
        # apontava pra arquivo inexistente. A promessa "a cópia está aqui"
        # precisa ser verificável, não só plausível.
        if str(flat) != _flat_name(str(rel)):
            return {}, f"cópia `{flat}` não corresponde a `{rel}` no mapeamento do manifesto"
        copy = stamp_dir / str(flat)
        try:
            if copy.parent != stamp_dir or copy.is_symlink() or not copy.is_file():
                return {}, f"cópia `{flat}` ausente ou fora do carimbo"
            data = copy.read_bytes()
        except OSError as exc:
            return {}, f"cópia `{flat}` ilegível ({exc})"
        if _digest(data) != digests.get(flat):
            return {}, f"cópia `{flat}` diverge do digest do manifesto"
        try:
            # Digest confere bytes, não prova que continuam sendo texto. Sem
            # isto, uma cópia com bytes inválidos e digest coerente virava
            # régua e o `errors="replace"` fabricava uma medição falsa
            # (Codex, 262H-3).
            data.decode("utf-8")
        except UnicodeDecodeError:
            return {}, f"cópia `{flat}` não é UTF-8 válido"
        conteudo[str(rel)] = data
    return conteudo, None


def _collect_baseline(
    scope_root: Path, degradacoes: list[str]
) -> tuple[dict[str, tuple[bytes, Path]], Path | None, dict | None]:
    """Régua POR ARQUIVO: para cada path, a cópia mensurável mais recente.

    Dois buracos que isto fecha. Um carimbo só como régua não bastava: arquivo
    que passa do teto sai do inventário daquele carimbo, e o carimbo continua
    COMPLETO (oversized é estado conhecido, não falha) — no dia seguinte, com o
    arquivo mutilado de volta abaixo do teto, ele parecia não ter história
    (Codex, 262J-1). E limitar a busca aos N carimbos mais recentes só adiava o
    mesmo esquecimento: com o arquivo grande por N rituais seguidos, a cópia
    boa continuava retida em disco e fora do alcance (Codex, rodada 8).

    A caminhada percorre TODO o histórico retido, mas só paga leitura no
    carimbo que contribui com algum path ainda pendente — no caso comum, o
    primeiro. Manifesto é barato; cópia é que custa.

    Devolve também o carimbo VÁLIDO mais novo e seu manifesto: é ele que
    responde "mudou alguma coisa?" pro dedupe, porque dedupe compara com um
    instante, não com o retrato composto.
    """
    try:
        if not scope_root.is_dir():
            return {}, None, None
        candidates = sorted(
            p for p in scope_root.iterdir() if p.is_dir() and not p.is_symlink()
        )
    except OSError as exc:
        degradacoes.append(f"backups/{SCOPE}: {exc}")
        return {}, None, None

    # Manifestos primeiro: são baratos e dizem QUEM tem o quê.
    completos: list[tuple[datetime, Path, dict]] = []
    for stamp_dir in candidates:
        manifest = _manifest_of(stamp_dir)
        if manifest is None:
            degradacoes.append(
                f"snapshot `{stamp_dir.name}` sem manifesto válido — ignorado como referência"
            )
            continue
        if manifest["complete"]:
            completos.append((_parse_instant(manifest["captured_at_utc"]), stamp_dir, manifest))
    completos.sort(key=lambda c: c[0], reverse=True)

    pendentes: set[str] = set()
    for _, _, manifest in completos:
        pendentes |= {str(v) for v in manifest["files"].values()}

    baseline: dict[str, tuple[bytes, Path]] = {}
    topo_stamp: Path | None = None
    topo_manifest: dict | None = None
    for _, stamp_dir, manifest in completos:
        declara = {str(v) for v in manifest["files"].values()}
        precisa_ler = topo_stamp is None or bool(declara & pendentes)
        if not precisa_ler:
            continue
        conteudo, problema = _validate_candidate(stamp_dir, manifest)
        if problema is not None:
            degradacoes.append(f"snapshot `{stamp_dir.name}`: {problema} — não serve de régua")
            continue
        if topo_stamp is None:
            topo_stamp, topo_manifest = stamp_dir, {**manifest, "_conteudo": conteudo}
        for rel, data in conteudo.items():
            baseline.setdefault(rel, (data, stamp_dir))
        pendentes -= set(baseline)

    if candidates and topo_stamp is None:
        degradacoes.append(
            "nenhum snapshot completo no histórico — detecção de encolhimento indisponível"
        )
    return baseline, topo_stamp, topo_manifest


def _read_capped(path: Path) -> bytes | None:
    """Lê no máximo `MAX_FILE_BYTES`; acima disso devolve None.

    O teto é por CONSTRUÇÃO, não por medição prévia: `stat().st_size` antes de
    `read_bytes()` é fotografia, e o arquivo pode engordar entre a medida e a
    leitura — o custo que o teto existe pra evitar seria pago mesmo assim
    (Codex, r1). Pedindo `MAX+1`, o excedente prova o estouro sem materializar
    o arquivo inteiro.
    """
    with path.open("rb") as fh:
        data = fh.read(MAX_FILE_BYTES + 1)
    return None if len(data) > MAX_FILE_BYTES else data


def _acervo_index(paths) -> dict[str, str]:
    """Índice `digest → path` de `Arquivo/Acervo/`, construído UMA vez.

    Restrito ao destino real do acervo (`acervo_apply._quarantine_dir`), e por
    CONTEÚDO em vez de nome: o acervo renomeia em colisão, então casar por
    basename perderia arquivamento legítimo — e casaria com homônimo que não
    tem nada a ver (Codex, 262F-3). Um `rglob` por ausente também transformava
    o briefing em arqueólogo pago por hora.
    """
    raiz = paths.arquivo_root / "Acervo"
    indice: dict[str, str] = {}
    try:
        # Cerca de ancestral também aqui: `Acervo/` symlinkado pra fora leria
        # conteúdo externo e rebaixaria uma deleção REAL a "arquivado"
        # (Codex, 262G-3).
        if _has_symlink_ancestor(paths.root, paths.relative(raiz)):
            return indice
        if not raiz.is_dir():
            return indice
        for candidate in sorted(raiz.rglob("*.md")):
            try:
                if (
                    candidate.is_file()
                    and not candidate.is_symlink()
                    and not _has_symlink_ancestor(paths.root, paths.relative(candidate))
                ):
                    # Mesmo teto por arquivo da coleta (#265): sem ele, um
                    # acervo com arquivos grandes fazia o ritual pagar leitura
                    # integral deles só pra decidir se um sumiço foi
                    # arquivamento. Acima do teto não entra no índice — e por
                    # isso NÃO rebaixa alerta: sem digest comparável não há
                    # evidência de arquivamento, e rebaixar transformaria
                    # ignorância em álibi.
                    dados = _read_capped(candidate)
                    if dados is None:
                        continue
                    indice.setdefault(_digest(dados), paths.relative(candidate))
            except (OSError, ValueError):
                continue
    except OSError:
        return indice
    return indice


def _build_alerts(
    paths,
    current: dict[str, bytes],
    baseline: dict[str, tuple[bytes, Path]],
    shrink_pct: int,
    presentes_sem_medida: set[str] = frozenset(),
) -> list[dict]:
    flow, hybrid = paths.curated_flow_paths(), paths.curated_hybrid_paths()
    ausentes = [
        rel for rel in baseline
        if rel not in current
        and rel not in presentes_sem_medida
        and watch_class(rel, flow, hybrid) != FLOW
    ]
    # Índice do acervo só quando há ausente — quem nunca perdeu arquivo não
    # paga varredura nenhuma.
    acervo = _acervo_index(paths) if ausentes else {}

    alerts: list[dict] = []
    for rel in sorted(set(current) | set(baseline)):
        klass = watch_class(rel, flow, hybrid)
        if klass == FLOW or rel not in baseline:
            # Sem cópia anterior não há delta — só ausência de história.
            continue
        anterior, stamp_do_rel = baseline[rel]
        before = measured_size(anterior, klass)
        # O piso existe contra ruído PROPORCIONAL (arquivo minúsculo em que
        # qualquer edição é % enorme). Sumiço não é proporção: um curado que
        # deixou de existir é perda, tenha 20 bytes ou 20 mil.
        if before < MIN_ALERT_BYTES and rel in current:
            continue
        base = {
            "path": rel,
            "watch_class": klass,
            "before_bytes": before,
            # Caminho EXATO do arquivo restaurável, não só o diretório: a
            # mensagem promete "a cópia está aqui" e tem de cumprir.
            "previous_copy": str(stamp_do_rel / _flat_name(rel)),
        }
        if rel in presentes_sem_medida:
            # Está lá; só não coube na régua. Anunciar sumiço aqui seria a
            # sirene de perda tocando pra um arquivo que CRESCEU.
            alerts.append({**base, "after_bytes": 0, "shrink_pct": 0,
                           "state": UNMEASURABLE, "twin": ""})
            continue
        if rel not in current:
            # Gêmeo byte a byte em `Arquivo/Acervo/` é indício FORTE de
            # arquivamento, não prova: o produto não tem proveniência da
            # operação. Então rebaixa o tom em vez de silenciar — chamar de
            # arquivamento sem rastro seria o detector inventando história
            # (Codex, 262F-3).
            gemeo = acervo.get(_digest(anterior))
            alerts.append(
                {
                    **base,
                    "after_bytes": 0,
                    "shrink_pct": 100,
                    "state": ARCHIVED if gemeo else GONE,
                    "twin": gemeo or "",
                }
            )
            continue
        after = measured_size(current[rel], klass)
        if after >= before:
            continue
        shrink = (before - after) * 100 // before
        if shrink < shrink_pct:
            continue
        alerts.append(
            {**base, "after_bytes": after, "shrink_pct": shrink, "state": "encolheu", "twin": ""}
        )
    return alerts


def _integrity_errors(paths, current: dict[str, bytes]) -> list[str]:
    hybrid = paths.curated_hybrid_paths()
    problemas = []
    for rel, data in sorted(current.items()):
        if rel not in hybrid:
            continue
        _, erro = _pulso_partition(data.decode("utf-8"))
        if erro:
            problemas.append(f"{rel}: {erro} — alerta medido sobre o arquivo inteiro")
    return problemas


def _reserve_stamp_dir(scope_root: Path, stamp: str) -> Path:
    """Reserva o diretório ATOMICAMENTE: `mkdir` sem `exist_ok` é a própria
    trava. Checar `exists()` antes e criar depois é corrida — dois `prumo seed`
    simultâneos escolheriam o mesmo nome e um perderia o snapshot inteiro no
    boundary (Codex, 262E-5)."""
    scope_root.mkdir(parents=True, exist_ok=True)
    for suffix in range(0, 100):
        candidate = scope_root / (stamp if suffix == 0 else f"{stamp}-{suffix + 1}")
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise OSError(f"cem carimbos colididos em {scope_root}")


def _require_clean_destination(workspace: Path, target: Path) -> None:
    """Cerca da ESCRITA (#189, molde do `_require_clean_target` da semente):
    nenhum componente até o destino pode ser symlink. A `prune_expired_backups`
    já recusa raiz symlinkada; o writer novo precisa da mesma disciplina, senão
    `.prumo/backups` apontando pra fora grava o snapshot fora do território
    (Codex, 262E-6)."""
    probe = workspace
    for part in target.relative_to(workspace).parts:
        probe = probe / part
        if probe.is_symlink():
            raise OSError(f"`{probe.relative_to(workspace)}` é symlink — escrita recusada")


def _write_manifest(target_root: Path, payload: dict) -> None:
    """Escrita atômica: manifesto truncado por crash seria ignorado depois e a
    história sumiria em silêncio."""
    tmp = target_root / f"{MANIFEST_NAME}.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target_root / MANIFEST_NAME)


def snapshot_curated(
    workspace: Path, *, stamp: str | None = None, shrink_pct: int | None = None
) -> dict:
    """Copia os curados pra `.prumo/backups/<SCOPE>/<stamp>/` e mede encolhimento.

    O carimbo nasce AQUI, em UTC, e não do fuso configurado: ele é só rótulo
    de diretório — a ordem cronológica vem do `captured_at_utc` do manifesto.
    Assim o snapshot não depende de `build_config_from_existing`.

    Só copia em workspace NESTED (#268). Workspace no layout antigo devolve
    `skipped=SKIPPED_LEGACY_FLAT` — gravar criaria um `.prumo/` dentro do flat
    — e pasta sem identidade de workspace devolve `SKIPPED_NOT_NESTED`, sem
    convite pra migrar. A tolerância antiga ("sem identidade canônica ganha
    cópia") acabou aqui: `nested_layout` detectado não prova identidade, e uma
    pasta alheia com subpasta `Prumo/` incidental receberia backup dentro dela.

    NUNCA levanta: qualquer falha entra em `errors` e o ritual segue. Backup
    que derruba o briefing é pior que o problema que ele resolve.
    """
    if stamp is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if "/" in stamp or "\\" in stamp or stamp in {"", ".", ".."}:
        # Carimbo é NOME de diretório, não caminho: absoluto ou `../` reservaria
        # e gravaria fora do scope, furando a cerca (Codex, 262G-4).
        stamp = "carimbo-invalido"
    errors: list[str] = []
    report: dict = {
        "scope": SCOPE,
        "stamp": stamp,
        "copied": [],
        "oversized": [],
        "alerts": [],
        "errors": errors,
        "skipped": None,
    }
    try:
        workspace = Path(workspace).expanduser().resolve()
        paths = workspace_paths(workspace)
        # Duas recusas, códigos diferentes, mesma trava (#268). Ela mora AQUI e
        # não nos dois chamadores (`seed` e `briefing`) pra que qualquer ritual
        # futuro que peça snapshot já nasça protegido. `skipped` carrega CÓDIGO,
        # nunca frase — `sem-mudanca`, o dedupe normal, mora no mesmo campo, e
        # confundir os dois fazia todo briefing sem alteração alarmar (Codex, r4).
        if is_legacy_flat_workspace(workspace):
            # Workspace legítimo no layout antigo: o destino é `.prumo/backups/`
            # literal, então gravar criaria um `.prumo/` DENTRO do flat e
            # misturaria os dois arranjos. Este ganha o convite pra migrar.
            report["skipped"] = SKIPPED_LEGACY_FLAT
            return report
        if not is_prumo_workspace(workspace):
            # `nested_layout` sozinho NÃO é identidade: pasta alheia com uma
            # subpasta `Prumo/` incidental é detectada como nested, e o snapshot
            # gravaria `.prumo/backups/curated/` dentro do projeto de outra
            # pessoa — e o briefing chama isto antes de montar o painel
            # (Codex, r6). Sem convite pra migrar: não há de onde.
            report["skipped"] = SKIPPED_NOT_NESTED
            return report
        scope_root = workspace / ".prumo" / "backups" / SCOPE

        # Três origens de mensagem, com pesos DIFERENTES. Só a primeira decide
        # se este retrato serve de régua: falha de leitura/cópia é buraco no
        # inventário. Pulso malformado é aviso de medição (o arquivo foi
        # copiado inteiro), e manifesto velho corrompido é história perdida lá
        # atrás — nenhum dos dois pode desligar o dedupe pra sempre.
        coleta: list[str] = []
        # A cerca vem ANTES de ler histórico: com `.prumo/backups` symlinkado
        # pra fora, uma baseline externa "equivalente" devolvia `sem-mudanca`
        # e o atalho passava por baixo da cerca (Codex, 262H-2).
        _require_clean_destination(workspace, scope_root)
        current, oversized, sem_medida = _read_current(paths, coleta)
        report["oversized"] = oversized
        errors.extend(coleta)
        errors.extend(_integrity_errors(paths, current))

        # O conteúdo do baseline já vem VERIFICADO contra os digests do
        # manifesto (`_validate_candidate`) — reler aqui reabriria a janela.
        baseline, previous_stamp, previous_manifest = _collect_baseline(scope_root, errors)

        if shrink_pct is None:
            shrink_pct = faxina_thresholds.effective(workspace)["values"][
                "curated_shrink_alert_pct"
            ]
        report["alerts"] = _build_alerts(
            paths, current, baseline, shrink_pct, sem_medida
        )

        # DOIS conceitos, antes espremidos num `complete` só (Codex, 262E-4):
        # integridade (serve de régua pro alerta) e equivalência (justifica
        # pular). Arquivo grande demais NÃO fura a integridade — ele é
        # conhecido e declarado no manifesto; furar faria um único .md de
        # 512 KiB desligar o dedupe pra sempre e copiar tudo em todo ritual.
        integro = not coleta
        # Dedupe compara com o carimbo mais novo válido — "mudou algo desde a
        # última foto?" —, não com a régua por arquivo (que é retrato composto
        # de vários carimbos).
        topo = dict(previous_manifest.get("_conteudo", {})) if previous_manifest else {}
        previous_oversized = set(previous_manifest.get("oversized", [])) if previous_manifest else set()
        equivalente = (
            set(current) == set(topo)
            and set(oversized) == previous_oversized
            and all(_digest(current[r]) == _digest(topo.get(r, b"")) for r in current)
        )
        if previous_stamp is not None and integro and equivalente:
            report["skipped"] = "sem-mudanca"
            return report

        target_root = _reserve_stamp_dir(scope_root, stamp)
        gravados: dict[str, str] = {}
        digests: dict[str, str] = {}
        for rel in sorted(current):
            # Grava os BYTES QUE FORAM MEDIDOS, em vez de reabrir a origem.
            # Reler abria janela entre medir e copiar: o alerta sairia sobre um
            # conteúdo e a cópia guardaria outro, com o manifesto declarando
            # completo o que ninguém conferiu (Codex, 262F-4).
            flat = _flat_name(rel)
            try:
                (target_root / flat).write_bytes(current[rel])
                report["copied"].append(rel)
                gravados[flat] = rel
                digests[flat] = _digest(current[rel])
            except (OSError, ValueError) as exc:
                errors.append(f"{rel}: {exc}")
        report["stamp"] = target_root.name
        _write_manifest(
            target_root,
            {
                "schema": MANIFEST_SCHEMA,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "complete": not coleta and len(gravados) == len(current),
                "files": gravados,
                "digests": digests,
                "oversized": sorted(oversized),
            },
        )
    except Exception as exc:  # noqa: BLE001 — boundary: o ritual nunca cai por causa do backup
        errors.append(f"{type(exc).__name__}: {exc}")
    return report


def render_report(report: dict) -> str:
    """Linhas pro usuário: encolhimento, o que não coube e o que falhou.

    Nomear é o ponto — só o usuário sabe que aquele índice era de fevereiro —
    e `errors`/`oversized` também aparecem: são exatamente os arquivos que
    NÃO ganharam cópia, o pior momento pra ficar calado (Codex, 262D-5).
    """
    linhas: list[str] = []
    # Só o bloqueio por layout vira linha: quem não ganhou cópia de segurança
    # tem que saber (Codex, r3). `sem-mudanca` NÃO entra — é o dedupe normal,
    # e alarmá-lo transformaria uma otimização saudável em aviso recorrente
    # em todo briefing sem alteração (Codex, r4).
    if report.get("skipped") == SKIPPED_LEGACY_FLAT:
        linhas.append(
            "[curado] snapshot não rodou — workspace no layout antigo (flat): a cópia "
            "gravaria em `.prumo/backups/` e criaria um `.prumo/` dentro dele. Rode "
            "`prumo migrate` pra ganhar a cópia de segurança dos arquivos curados."
        )
    graves = [
        a for a in report.get("alerts", [])
        if a.get("state") not in {ARCHIVED, UNMEASURABLE}
    ]
    if graves:
        linhas.append(
            "[curado] mudança suspeita desde a última cópia — confira antes de seguir:"
        )
    for a in graves:
        if a.get("state") == GONE:
            linhas.append(
                f"  - `{a['path']}`: SUMIU (tinha {a['before_bytes']} bytes). "
                f"Cópia em `{a['previous_copy']}`."
            )
        else:
            linhas.append(
                f"  - `{a['path']}`: {a['before_bytes']} → {a['after_bytes']} bytes "
                f"(−{a['shrink_pct']}%). Cópia anterior em `{a['previous_copy']}`."
            )
    # Tom mais baixo, mas nunca silêncio: o produto não tem proveniência da
    # operação do acervo, então relata o indício em vez de afirmar o fato.
    arquivados = [a for a in report.get("alerts", []) if a.get("state") == ARCHIVED]
    if arquivados:
        linhas.append("[curado] saiu de lugar, com cópia idêntica no acervo:")
        linhas.extend(f"  - `{a['path']}` → `{a['twin']}`" for a in arquivados)
    # Estado próprio no texto também: dizer "antes → 0 bytes (−0%)" pra um
    # arquivo que CRESCEU seria trocar uma ficção contábil por outra
    # (Codex, 262J-2).
    sem_medida = [a for a in report.get("alerts", []) if a.get("state") == UNMEASURABLE]
    if sem_medida:
        linhas.append("[curado] existe, mas ficou fora da medição desta vez:")
        linhas.extend(
            f"  - `{a['path']}` (tinha {a['before_bytes']} bytes na última cópia)"
            for a in sem_medida
        )
    naocopiados = list(report.get("oversized", []))
    if naocopiados:
        linhas.append("[curado] acima do teto de tamanho, SEM cópia:")
        linhas.extend(f"  - `{rel}`" for rel in naocopiados)
    if report.get("errors"):
        linhas.append("[curado] falhas no snapshot (o ritual seguiu):")
        linhas.extend(f"  - {erro}" for erro in report["errors"])
    return "\n".join(linhas)
