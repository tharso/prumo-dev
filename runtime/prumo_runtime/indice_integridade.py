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
# Linha de tabela cujo primeiro campo é o ID.
_LINHA_ID = re.compile(r"^\s*\|\s*(\d+)\s*\|", re.M)
# Linha de dados da tabela: `| # | Título | Arquivo | ...`. A COLUNA importa —
# nome citado numa descrição não é entrada de índice (Codex, 261D-3).
_LINHA_DADOS = re.compile(r"^\s*\|\s*\d+\s*\|([^|]*)\|([^|]*)\|", re.M)

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


def arquivos_indexados(texto: str) -> set[str]:
    """Nomes na COLUNA `Arquivo` das linhas de dados.

    Buscar o nome no texto inteiro fazia uma ficha citada numa descrição
    contar como indexada — a linha perdida ficava invisível justamente no
    detector feito pra achá-la (Codex, 261D-3).
    """
    nomes: set[str] = set()
    for _, coluna_arquivo in _LINHA_DADOS.findall(texto):
        alvo = coluna_arquivo.strip().strip("`").strip()
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
    if not referencias_root.is_dir():
        return None
    indexados = arquivos_indexados(texto)
    faltando: list[str] = []
    try:
        candidatos = sorted(referencias_root.glob("*.md"))
    except OSError:
        return None
    for path in candidatos:
        nome = path.name
        if nome in OPERACIONAIS or nome.startswith((".", "_")):
            continue
        if not path.is_file() or path.is_symlink():
            continue
        if nome not in indexados:
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
        "fonte_completa": True,
        "decisao": OK,
        "razoes": [],
    }
    try:
        texto = indice_path.read_text(encoding="utf-8") if indice_path.is_file() else ""
    except (OSError, UnicodeDecodeError) as exc:
        resultado["fonte_completa"] = False
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = [f"índice ilegível ({exc})"]
        return resultado

    resultado["proximo_id"] = proximo_id(texto)
    resultado["ids_distintos"] = len(ids_da_tabela(texto))
    resultado["lacunas_pct"] = lacunas_pct(texto)

    sem_entrada = fichas_sem_entrada(referencias_root, texto)
    if sem_entrada is None:
        # Não é "nenhuma ficha fora": é "não consegui olhar". Chamar isso de
        # casa em ordem seria o silêncio confiante que a #236 já nomeou.
        resultado["fonte_completa"] = False
        resultado["decisao"] = BLOQUEAR
        resultado["razoes"] = ["não consegui listar `Referencias/` — inventário indisponível"]
        return resultado
    resultado["sem_entrada"] = sem_entrada

    fracao = lacunas_fracao(texto)
    # Comparação EXATA em inteiros: `lacunas/slots >= pct/100`.
    if fracao is not None and fracao[0] * 100 >= gap_alert_pct * fracao[1]:
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
    elif sem_entrada:
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
        return linha
    if decisao == REINDEXAR:
        return "Índice: " + ", ".join(f"`{n}`" for n in nomes) + " sem entrada — reindexar e nomear."
    return ""
