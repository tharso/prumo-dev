"""Integridade do `Referencias/INDICE.md` (#261).

Por que existe: a faxina §3 já comparava as fichas em disco com a tabela do
índice, mas o reflexo era ADICIONAR o que faltava — sem teto e em silêncio.
Depois do truncamento de 27/07 (48 entradas viraram 5), qualquer briefing dos
dois dias seguintes teria reinserido 37 fichas com IDs NOVOS, trocado as
descrições autorais pelas derivadas, e reportado sucesso. O contrato, como
estava escrito, prescrevia a ação errada exatamente pro estado do incidente.

A assimetria estava no mesmo parágrafo: entrada sem arquivo tinha cautela
declarada ("não remover, marcar, deixar a higiene decidir"); arquivo sem
entrada agia na hora. A #212 já tinha estabelecido o padrão certo na seção
vizinha — estado inconsistente sinaliza e para.

Este módulo é o PRODUTOR da decisão. Ele existe pra que o caminho com runtime
tenha prova comportamental em vez de um cálculo paralelo que só os testes
chamam (Codex, 261-7). Sem runtime, o `faxina.md` replica o algoritmo em
texto — limitação nomeada, não maquiada.

Módulo folha: só stdlib e `faxina_thresholds`.
"""

from __future__ import annotations

import re
from pathlib import Path

SCHEMA = "prumo_indice_integridade.v1"

# Mesma lista de exclusão do acervo e da faxina: infraestrutura de
# `Referencias/`, não referência catalogável.
OPERACIONAIS = frozenset({"INDICE.md", "WORKFLOWS.md", "EMAIL-CURADORIA.md"})

_RODAPE = re.compile(r"<!--\s*proximo-id:\s*(\d+)\s*-->")
# Marcas de conferência (#261): a higiene grava aqui o que o usuário declarou
# DELIBERADO. Sem isto, "a remoção foi deliberada" não mudava nada e o mesmo
# estado bloqueava na rodada seguinte — saída cenográfica (Codex, r3). Moram no
# próprio índice: é arquivo curado, então entram no snapshot da #262 e viajam
# com ele.
#
# A lacuna é guardada como FRAÇÃO EXATA `L/S`, nunca como percentual
# arredondado: 101/200 vira 50% no arredondamento, e `101*100 > 50*200` faria o
# mesmo estado bloquear de novo sem ter crescido (Codex, r4). O volume é
# guardado POR NOME — contar não distingue "a ficha que o usuário aceitou
# deixar de fora" de "a ficha nova de amanhã", e a segunda deve ser indexada.
_CONFERIDA = re.compile(r"<!--\s*lacunas-conferidas:\s*(\d+)\s*/\s*(\d+)\s*-->")
_FORA_CONFERIDAS = re.compile(r"<!--\s*fichas-fora-conferidas:\s*([^>]*?)\s*-->")
# Linha de tabela cujo primeiro campo é o ID.
_LINHA_ID = re.compile(r"^\s*\|\s*(\d+)\s*\|", re.M)
# Linha de dados da tabela: começa com `| <id> |`. As células saem do split
# que respeita `\|` escapado — sem isso, um título com pipe escapado
# (`| 1 | A \| B | ficha.md |`) empurrava a coluna e a ficha ÍNTEGRA era
# acusada de ausente, virando reindexação com ID novo: o reparo no escuro que
# esta issue existe pra impedir (Codex, r7).
_LINHA_TABELA = re.compile(r"^\s*\|\s*\d+\s*\|.*$", re.M)

OK = "ok"
REINDEXAR = "reindexar"
BLOQUEAR = "bloquear"


def proximo_id(texto: str) -> int | None:
    """Última ocorrência do rodapé (#244). Ausente ou malformado → None, que
    NÃO é alarme por si: workspace legado simplesmente não tem o rodapé."""
    achados = _RODAPE.findall(texto)
    if not achados:
        return None
    try:
        return int(achados[-1])
    except ValueError:
        return None


def lacunas_conferidas(texto: str) -> tuple[int, int] | None:
    """Fração `(lacunas, slots)` que o usuário declarou deliberada.

    A regex só casa dígitos, então marca malformada não casa e vira `None` —
    sem `try/except`, que aqui seria ramo inalcançável (achado da bateria).
    """
    achados = _CONFERIDA.findall(texto)
    if not achados:
        return None
    lacunas, slots = int(achados[-1][0]), int(achados[-1][1])
    # `999/1` fazia a multiplicação cruzada concluir eternamente que a lacuna
    # não cresceu — marca numericamente impossível não pode desligar a trava
    # (Codex, r5).
    return (lacunas, slots) if 0 < slots and 0 <= lacunas <= slots else None


def fichas_fora_conferidas(texto: str) -> set[str]:
    """Fichas que o usuário aceitou manter FORA do índice, por nome.

    Por nome e não por contagem: contagem não distingue a ficha aceita da
    ficha nova de amanhã, e a nova precisa ser indexada (Codex, r4).
    """
    achados = _FORA_CONFERIDAS.findall(texto)
    if not achados:
        return set()
    return {
        parte.strip().strip("`")
        for parte in achados[-1].split(",")
        if parte.strip().strip("`")
    }


def ids_da_tabela(texto: str) -> set[int]:
    return {int(m) for m in _LINHA_ID.findall(texto)}


def lacunas_fracao(texto: str) -> tuple[int, int] | None:
    """(lacunas, slots) — números INTEIROS, sem arredondar.

    Arredondar antes de comparar move a fronteira que o usuário configurou:
    49,5% em 101 slots virava 50 e bloqueava no limiar 50 (Codex, 261D-4).
    """
    n = proximo_id(texto)
    if n is None or n <= 1:
        return None
    slots = n - 1
    ocupados = len({i for i in ids_da_tabela(texto) if 1 <= i <= slots})
    return slots - ocupados, slots


def lacunas_pct(texto: str) -> int | None:
    """Percentual de IDs ausentes no intervalo que o rodapé declara já usado.

        slots     = N - 1            (o rodapé aponta o PRÓXIMO, não o último)
        ocupados  = IDs distintos em 1..slots
        lacunas   = 100 * (slots - ocupados) / slots

    ID **maior ou igual a N não preenche lacuna**: o rodapé é sugestão e pode
    estar atrasado (contrato da #244). Duplicata conta uma vez. `N <= 1` não
    tem intervalo — pavio inaplicável, devolve None.

    Buraco de ID é a REGRA, não a exceção: o índice reconstruído do dono tem
    11 ausentes em 48 (22,9%), e o truncamento real deu 91,7%. Há folga larga
    entre os dois, e é por isso que o limiar default fica no meio.
    """
    fracao = lacunas_fracao(texto)
    if fracao is None:
        return None
    lacunas, slots = fracao
    return round(100 * lacunas / slots)  # SÓ pra exibição


def _celulas(linha: str) -> list[str]:
    """Divide a linha em células respeitando `\|` escapado."""
    celulas: list[str] = []
    atual: list[str] = []
    i = 0
    while i < len(linha):
        c = linha[i]
        if c == "\\" and i + 1 < len(linha) and linha[i + 1] == "|":
            atual.append("|")
            i += 2
            continue
        if c == "|":
            celulas.append("".join(atual))
            atual = []
            i += 1
            continue
        atual.append(c)
        i += 1
    celulas.append("".join(atual))
    # A linha abre e fecha com `|`: as pontas viram strings vazias.
    return [c for c in celulas[1:-1]] if len(celulas) > 2 else []


def arquivos_indexados(texto: str) -> set[str]:
    """Nomes na COLUNA `Arquivo` (a terceira) das linhas de dados.

    Buscar o nome no texto inteiro fazia uma ficha citada numa descrição
    contar como indexada — a linha perdida ficava invisível justamente no
    detector feito pra achá-la (Codex, 261D-3).
    """
    nomes: set[str] = set()
    for linha in _LINHA_TABELA.findall(texto):
        celulas = _celulas(linha.rstrip())
        if len(celulas) < 3:
            continue
        alvo = celulas[2].strip().strip("`").strip()
        # A célula pode vir como link markdown `[texto](arquivo.md)`.
        link = re.search(r"\(([^)]+)\)\s*$", alvo)
        if link:
            alvo = link.group(1).strip()
        if alvo:
            nomes.add(alvo.rsplit("/", 1)[-1])
    return nomes


def fichas_sem_entrada(referencias_root: Path, texto: str) -> list[str] | None:
    """Fichas em disco fora da coluna `Arquivo`. `None` = fonte indisponível.

    Distinguir "nenhuma ficha" de "não consegui olhar" é o que impede raiz
    inacessível de virar casa em ordem (Codex, 261D-5).
    """
    # O manifesto da semente EXCLUI symlink; seguir aqui criaria assimetria:
    # o produtor leria o alvo pra dizer `ok` e mudanças nele não mexeriam no
    # manifesto — a semente seguiria "fresca" depois de um truncamento, que é
    # o bug original de bigode postiço (Codex, r5).
    if referencias_root.is_symlink() or not referencias_root.is_dir():
        return None
    import stat as stat_module

    indexados = arquivos_indexados(texto)
    faltando: list[str] = []
    try:
        # `iterdir`, não `glob`: o glob engole erro por entrada e a falha de
        # listagem passaria como pasta vazia (Codex, r2).
        candidatos = sorted(
            p for p in referencias_root.iterdir() if p.suffix.lower() == ".md"
        )
    except OSError:
        return None
    for path in candidatos:
        nome = path.name
        if nome in OPERACIONAIS or nome.startswith((".", "_")):
            continue
        try:
            # `lstat` protegido, não `is_file()`: o helper transforma erro de
            # stat em False, e a ficha inacessível sumiria da contagem
            # (Codex, r3). Mesmo padrão do manifesto da semente.
            st = path.lstat()
        except OSError:
            return None
        if stat_module.S_ISLNK(st.st_mode) or not stat_module.S_ISREG(st.st_mode):
            continue
        if nome not in indexados:
            faltando.append(nome)
    return faltando


def entradas_sem_arquivo(referencias_root: Path, texto: str) -> list[str]:
    """Linhas do índice cujo arquivo não existe mais.

    O outro sentido da integridade. Sem isto, `decisao: ok` declarava a família
    limpa e suprimia o contrato que a §3 preserva desde sempre — marcar
    "(arquivo não encontrado)" e deixar a higiene decidir (Codex, r5).
    """
    if referencias_root.is_symlink() or not referencias_root.is_dir():
        return []
    faltando = []
    for nome in sorted(arquivos_indexados(texto)):
        alvo = referencias_root / nome
        try:
            if not alvo.exists() or alvo.is_symlink():
                faltando.append(nome)
        except OSError:
            faltando.append(nome)
    return faltando


def avaliar(
    referencias_root: Path,
    indice_path: Path,
    *,
    gap_alert_pct: int,
    bulk_reindex_at: int,
) -> dict:
    """Uma leitura, uma decisão, um alerta.

    E1 (lacunas) e E2 (volume) disparam no MESMO estado quando o índice é
    truncado. Escritos como guards independentes, dariam duas sirenes pro
    mesmo incêndio (Codex, 261-5) — então a árvore é exclusiva e o volume
    entra como evidência do bloqueio por lacuna, não como segundo alarme.
    """
    resultado: dict = {
        "schema": SCHEMA,
        "proximo_id": None,
        "ids_distintos": 0,
        "lacunas_pct": None,
        "sem_entrada": [],
        "entradas_sem_arquivo": [],
        "lacunas_conferidas": None,
        "fichas_fora_conferidas": [],
        "fonte_completa": True,
        "decisao": OK,
        "razoes": [],
    }
    if indice_path.is_symlink():
        # Mesma assimetria da raiz: o manifesto da semente exclui symlink, e
        # seguir aqui deixaria a decisão velha valendo depois de o alvo mudar
        # (Codex, r6).
        resultado["fonte_completa"] = False
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = ["`INDICE.md` é symlink — fonte fora do território"]
        return resultado
    indice_existe = indice_path.is_file()
    try:
        texto = indice_path.read_text(encoding="utf-8") if indice_existe else ""
    except (OSError, UnicodeDecodeError) as exc:
        resultado["fonte_completa"] = False
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = [f"índice ilegível ({exc})"]
        return resultado

    resultado["proximo_id"] = proximo_id(texto)
    resultado["ids_distintos"] = len(ids_da_tabela(texto))
    resultado["lacunas_pct"] = lacunas_pct(texto)

    sem_entrada_bruto = fichas_sem_entrada(referencias_root, texto)
    conferidas_fora = fichas_fora_conferidas(texto)
    sem_entrada = (
        None if sem_entrada_bruto is None
        else [n for n in sem_entrada_bruto if n not in conferidas_fora]
    )
    if sem_entrada is None:
        # Não é "nenhuma ficha fora": é "não consegui olhar". Chamar isso de
        # casa em ordem seria o silêncio confiante que a #236 já nomeou.
        resultado["fonte_completa"] = False
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = ["não consegui listar `Referencias/` — inventário indisponível"]
        return resultado
    resultado["sem_entrada"] = sem_entrada
    orfas = entradas_sem_arquivo(referencias_root, texto)
    resultado["entradas_sem_arquivo"] = orfas

    if not indice_existe and sem_entrada:
        # Índice sumido COM fichas em disco é a forma mais grave do incidente,
        # não um workspace novo. Reindexar aqui recriaria o catálogo com IDs
        # novos e descrições derivadas — o reflexo que a #261 existe pra matar.
        resultado["fonte_completa"] = False
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = [
            f"`INDICE.md` ausente com {len(sem_entrada)} ficha(s) em disco"
        ]
        return resultado

    fracao = lacunas_fracao(texto)
    conferido = lacunas_conferidas(texto)
    resultado["lacunas_conferidas"] = list(conferido) if conferido else None
    resultado["fichas_fora_conferidas"] = sorted(conferidas_fora)
    # Comparação EXATA em inteiros: `lacunas/slots >= pct/100`. E só alarma o
    # que CRESCEU além do que o usuário já aceitou — senão a confirmação dele
    # não muda o predicado e o alarme volta amanhã.
    # `lacunas/slots > L/S` por multiplicação cruzada — comparar a fração
    # EXATA que foi aceita, nunca o percentual exibido.
    cresceu = conferido is None or fracao is not None and (
        fracao[0] * conferido[1] > conferido[0] * fracao[1]
    )
    if (
        fracao is not None
        and fracao[0] * 100 >= gap_alert_pct * fracao[1]
        and cresceu
    ):
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = [
            f"{resultado['lacunas_pct']}% dos IDs até {resultado['proximo_id']} "
            "estão ausentes da tabela",
            f"{len(sem_entrada)} ficha(s) em disco fora do índice",
        ]
    elif len(sem_entrada) >= bulk_reindex_at:
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = [
            f"{len(sem_entrada)} ficha(s) em disco fora do índice de uma vez"
        ]
    elif sem_entrada or orfas:
        # Órfã não é dano silencioso, é manutenção declarada: a §3 marca
        # "(arquivo não encontrado)" e a higiene decide. Mas a família NÃO
        # pode ser declarada limpa com ela pendente.
        resultado["decisao"] = REINDEXAR
    return resultado


def render(resultado: dict) -> str:
    """Linha única e nominal. Estado SUSPEITO, nunca "dano confirmado":
    nenhuma porcentagem lê intenção, e apagar uma seção de propósito produz o
    mesmo observável de um truncamento (Codex, 261-2)."""
    decisao = resultado.get("decisao", OK)
    nomes = resultado.get("sem_entrada", [])
    if decisao == BLOQUEAR:
        razoes = "; ".join(resultado.get("razoes", []))
        linha = f"Índice de referências inconsistente — {razoes}. Não alterei o índice; leve pra higiene."
        if nomes:
            linha += " Fora da tabela: " + ", ".join(f"`{n}`" for n in nomes[:10])
            if len(nomes) > 10:
                linha += f" (+{len(nomes) - 10})"
        orfas = resultado.get("entradas_sem_arquivo", [])
        if orfas:
            linha += " Sem arquivo: " + ", ".join(f"`{n}`" for n in orfas[:10])
            if len(orfas) > 10:
                linha += f" (+{len(orfas) - 10})"
        return linha
    if decisao == REINDEXAR:
        partes = []
        if nomes:
            partes.append(", ".join(f"`{n}`" for n in nomes) + " sem entrada")
        orfas = resultado.get("entradas_sem_arquivo", [])
        if orfas:
            partes.append(", ".join(f"`{n}`" for n in orfas) + " sem arquivo")
        return "Índice: " + "; ".join(partes) + " — reindexar e nomear."
    return ""
