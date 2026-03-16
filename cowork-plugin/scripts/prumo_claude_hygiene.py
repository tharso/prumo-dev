#!/usr/bin/env python3
"""Higiene assistida do CLAUDE.md.

Fluxo conservador:
- diagnostica duplicacao, redundancia e conflitos potenciais;
- gera relatorio + patch proposto;
- so aplica com --apply;
- sempre cria backup antes de escrever;
- registra no REGISTRO.md quando houver mudanca real.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SECTION_TITLE_RE = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)
SPLIT_RE = re.compile(r"\n{2,}")
WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[`*_>#\-\u2013\u2014:;,.!?\[\]\(\)\"']")


@dataclass
class Block:
    index: int
    raw: str
    start_line: int
    end_line: int
    heading: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Higiene assistida do CLAUDE.md.")
    parser.add_argument("--workspace", default=".", help="Workspace raiz (default: .)")
    parser.add_argument("--apply", action="store_true", help="Aplica a proposta ao CLAUDE.md")
    parser.add_argument(
        "--report-dir",
        default="_state/claude-hygiene",
        help="Diretorio relativo para relatorios e patch",
    )
    parser.add_argument(
        "--near-duplicate-threshold",
        type=float,
        default=0.9,
        help="Threshold de similaridade para redundancia (default: 0.9)",
    )
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def normalize_text(text: str) -> str:
    lowered = text.casefold()
    lowered = PUNCT_RE.sub(" ", lowered)
    lowered = WHITESPACE_RE.sub(" ", lowered).strip()
    return lowered


def line_number_at(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def infer_heading(before: str) -> str:
    matches = list(SECTION_TITLE_RE.finditer(before))
    if not matches:
        return "(sem seção)"
    return matches[-1].group(1).strip()


def split_blocks(content: str) -> list[Block]:
    blocks: list[Block] = []
    for index, match in enumerate(SPLIT_RE.finditer(content)):
        pass

    parts: list[tuple[int, int]] = []
    last = 0
    for m in SPLIT_RE.finditer(content):
        parts.append((last, m.start()))
        last = m.end()
    parts.append((last, len(content)))

    block_index = 0
    for start, end in parts:
        raw = content[start:end].strip("\n")
        if not raw.strip():
            continue
        start_line = line_number_at(content, start)
        end_line = line_number_at(content, end)
        blocks.append(
            Block(
                index=block_index,
                raw=raw,
                start_line=start_line,
                end_line=end_line,
                heading=infer_heading(content[:start]),
            )
        )
        block_index += 1
    return blocks


def fingerprint(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def detect_duplicate_lines(content: str) -> list[dict[str, Any]]:
    lines = content.splitlines()
    slots: dict[str, list[int]] = defaultdict(list)
    raw_by_key: dict[str, str] = {}

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith(">"):
            continue
        normalized = normalize_text(stripped)
        if len(normalized) < 18:
            continue
        slots[normalized].append(idx)
        raw_by_key.setdefault(normalized, stripped)

    findings: list[dict[str, Any]] = []
    for key, positions in slots.items():
        if len(positions) < 2:
            continue
        findings.append(
            {
                "type": "duplicate_line",
                "label": "Duplicado",
                "snippet": raw_by_key[key],
                "lines": positions,
                "risk": "baixo",
                "suggestion": "Consolidar a frase em um único ponto do arquivo.",
            }
        )
    return findings


def detect_duplicate_blocks(blocks: list[Block]) -> tuple[list[dict[str, Any]], set[int]]:
    seen: dict[str, Block] = {}
    findings: list[dict[str, Any]] = []
    duplicate_indexes: set[int] = set()

    for block in blocks:
        if block.raw.lstrip().startswith("#"):
            continue
        normalized = normalize_text(block.raw)
        if len(normalized) < 12:
            continue
        if normalized not in seen:
            seen[normalized] = block
            continue
        first = seen[normalized]
        duplicate_indexes.add(block.index)
        findings.append(
            {
                "type": "duplicate_block",
                "label": "Duplicado",
                "snippet": block.raw.splitlines()[0][:180],
                "lines": [first.start_line, block.start_line],
                "risk": "baixo",
                "suggestion": "Manter o bloco mais bem posicionado e remover a repetição literal.",
            }
        )
    return findings, duplicate_indexes


def detect_near_duplicates(blocks: list[Block], threshold: float) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for i, left in enumerate(blocks):
        norm_left = normalize_text(left.raw)
        if len(norm_left) < 80:
            continue
        for right in blocks[i + 1 :]:
            norm_right = normalize_text(right.raw)
            if len(norm_right) < 80:
                continue
            if norm_left == norm_right:
                continue
            ratio = difflib.SequenceMatcher(a=norm_left, b=norm_right).ratio()
            if ratio < threshold:
                continue
            findings.append(
                {
                    "type": "near_duplicate_block",
                    "label": "Redundante",
                    "snippet": left.raw.splitlines()[0][:180],
                    "lines": [left.start_line, right.start_line],
                    "risk": "medio",
                    "suggestion": "Fundir os dois blocos em um texto único para evitar eco com roupa diferente.",
                    "similarity": round(ratio, 3),
                }
            )
    return findings


TOPIC_RULES = {
    "emoji": {
        "keywords": {"emoji", "emojis"},
        "positive": {"usar", "use", "pode usar", "permitido"},
        "negative": {"evite", "evitar", "sem", "nao use", "não use", "nao usar", "não usar"},
    },
    "travessao": {
        "keywords": {"travessao", "travessão", "travessões", "travessoes", "em dash"},
        "positive": {"usar", "use", "pode usar"},
        "negative": {"evite", "evitar", "prefira", "sem", "nao usar", "não usar"},
    },
    "bullet": {
        "keywords": {"bullet", "bullets", "listas"},
        "positive": {"usar", "use", "pode usar"},
        "negative": {"evite", "evitar", "sem", "nao usar", "não usar"},
    },
}


def classify_polarity(normalized: str, topic: str) -> str | None:
    rules = TOPIC_RULES[topic]
    if not any(keyword in normalized for keyword in rules["keywords"]):
        return None
    if any(marker in normalized for marker in rules["negative"]):
        return "negative"
    if any(marker in normalized for marker in rules["positive"]):
        return "positive"
    return None


def detect_conflicts(lines: list[str]) -> list[dict[str, Any]]:
    by_topic: dict[str, dict[str, list[tuple[int, str]]]] = {
        topic: {"positive": [], "negative": []} for topic in TOPIC_RULES
    }

    for idx, raw in enumerate(lines, start=1):
        normalized = normalize_text(raw)
        if len(normalized) < 12:
            continue
        for topic in TOPIC_RULES:
            polarity = classify_polarity(normalized, topic)
            if polarity:
                by_topic[topic][polarity].append((idx, raw.strip()))

    findings: list[dict[str, Any]] = []
    for topic, polarities in by_topic.items():
        if not polarities["positive"] or not polarities["negative"]:
            continue
        findings.append(
            {
                "type": "potential_conflict",
                "label": "Potencial conflito",
                "snippet": topic,
                "lines": [polarities["positive"][0][0], polarities["negative"][0][0]],
                "risk": "alto",
                "suggestion": "Revisar e decidir qual instrução vence. Aqui tem duas placas apontando para estradas opostas.",
            }
        )
    return findings


def build_proposed_content(content: str, duplicate_indexes: set[int]) -> str:
    blocks = split_blocks(content)
    kept_blocks = [block.raw.strip() for block in blocks if block.index not in duplicate_indexes]
    proposed = "\n\n".join(kept_blocks).strip() + "\n"
    proposed = re.sub(r"\n{3,}", "\n\n", proposed)
    return proposed


def render_report_md(payload: dict[str, Any]) -> str:
    lines = [
        "# CLAUDE Hygiene Report",
        "",
        f"Gerado em: {payload['generated_at']}",
        f"Arquivo analisado: `{payload['claude_path']}`",
        "",
        "## Resumo",
        "",
        f"- Duplicados: {payload['summary']['duplicate_count']}",
        f"- Redundâncias: {payload['summary']['redundant_count']}",
        f"- Conflitos potenciais: {payload['summary']['conflict_count']}",
        f"- Proposta altera arquivo: {'sim' if payload['summary']['proposal_changes'] else 'não'}",
        "",
        "## Achados",
    ]

    findings = payload.get("findings", [])
    if not findings:
        lines.extend(["", "- Nenhum achado relevante."])
    else:
        for item in findings:
            line_info = ", ".join(str(x) for x in item.get("lines", []))
            lines.extend(
                [
                    "",
                    f"### {item['label']}",
                    "",
                    f"- Linhas: {line_info or 'n/d'}",
                    f"- Risco: {item['risk']}",
                    f"- Trecho/tema: `{item['snippet']}`",
                    f"- Sugestão: {item['suggestion']}",
                ]
            )

    lines.extend(
        [
            "",
            "## Aplicação",
            "",
            "Este relatório não altera `CLAUDE.md` sozinho.",
            "Para aplicar a proposta, é preciso confirmação explícita do usuário e execução com `--apply`.",
            "",
        ]
    )
    return "\n".join(lines)


def build_report(content: str, claude_path: Path, threshold: float) -> tuple[dict[str, Any], str]:
    blocks = split_blocks(content)
    duplicate_line_findings = detect_duplicate_lines(content)
    duplicate_block_findings, duplicate_indexes = detect_duplicate_blocks(blocks)
    near_duplicate_findings = detect_near_duplicates(blocks, threshold)
    conflict_findings = detect_conflicts(content.splitlines())

    proposed = build_proposed_content(content, duplicate_indexes)
    summary = {
        "duplicate_count": len(duplicate_line_findings) + len(duplicate_block_findings),
        "redundant_count": len(near_duplicate_findings),
        "conflict_count": len(conflict_findings),
        "proposal_changes": proposed != content,
    }

    report = {
        "generated_at": now_iso(),
        "claude_path": str(claude_path),
        "summary": summary,
        "findings": duplicate_line_findings + duplicate_block_findings + near_duplicate_findings + conflict_findings,
        "proposal": {
            "changed": proposed != content,
            "fingerprint_before": fingerprint(content),
            "fingerprint_after": fingerprint(proposed),
        },
    }
    return report, proposed


def write_artifacts(
    report_dir: Path,
    report_payload: dict[str, Any],
    original_content: str,
    proposed_content: str,
    claude_path: Path,
) -> dict[str, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = report_dir / "claude-hygiene-report.json"
    report_md_path = report_dir / "claude-hygiene-report.md"
    patch_path = report_dir / "claude-hygiene.patch"
    proposed_path = report_dir / "CLAUDE.proposed.md"

    report_json_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(render_report_md(report_payload), encoding="utf-8")
    patch_text = "".join(
        difflib.unified_diff(
            original_content.splitlines(keepends=True),
            proposed_content.splitlines(keepends=True),
            fromfile=str(claude_path),
            tofile=f"{claude_path} (proposed)",
        )
    )
    patch_path.write_text(patch_text, encoding="utf-8")
    proposed_path.write_text(proposed_content, encoding="utf-8")

    return {
        "report_json": report_json_path,
        "report_md": report_md_path,
        "patch": patch_path,
        "proposed": proposed_path,
    }


def append_registro(workspace: Path, message: str, destination: str) -> None:
    registro_path = workspace / "REGISTRO.md"
    if not registro_path.exists():
        return
    stamp = dt.datetime.now().strftime("%d/%m")
    line = f"| {stamp} | Sistema | {message} | Atualizado | {destination} |\n"
    with registro_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    claude_path = workspace / "CLAUDE.md"
    if not claude_path.exists():
        print(f"error: {claude_path} nao encontrado")
        return 1

    original_content = claude_path.read_text(encoding="utf-8")
    report_payload, proposed_content = build_report(
        original_content,
        claude_path=claude_path,
        threshold=args.near_duplicate_threshold,
    )

    report_dir = (workspace / args.report_dir).resolve()
    artifact_paths = write_artifacts(
        report_dir=report_dir,
        report_payload=report_payload,
        original_content=original_content,
        proposed_content=proposed_content,
        claude_path=claude_path,
    )

    applied = False
    backup_path: Path | None = None
    if args.apply and proposed_content != original_content:
        backup_dir = workspace / "_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        backup_path = backup_dir / f"CLAUDE.md.{stamp}"
        backup_path.write_text(original_content, encoding="utf-8")
        claude_path.write_text(proposed_content, encoding="utf-8")
        append_registro(
            workspace,
            "Higiene assistida aplicada ao CLAUDE.md com backup e patch proposto",
            "CLAUDE.md",
        )
        applied = True

    print(f"claude: {claude_path}")
    print(f"report_json: {artifact_paths['report_json']}")
    print(f"report_md: {artifact_paths['report_md']}")
    print(f"patch: {artifact_paths['patch']}")
    print(f"proposed: {artifact_paths['proposed']}")
    print(f"duplicates: {report_payload['summary']['duplicate_count']}")
    print(f"redundancies: {report_payload['summary']['redundant_count']}")
    print(f"conflicts: {report_payload['summary']['conflict_count']}")
    print(f"proposal_changes: {report_payload['summary']['proposal_changes']}")
    print(f"apply_requested: {args.apply}")
    print(f"applied: {applied}")
    if backup_path:
        print(f"backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
