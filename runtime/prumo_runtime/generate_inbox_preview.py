#!/usr/bin/env python3
"""Gera um preview visual local para itens do Inbox4Mobile.

Saida padrao: inbox-preview.html na raiz do workspace atual.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, quote, urlparse


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".svg",
    ".heic",
    ".heif",
}
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".tsv",
    ".log",
    ".url",
    ".webloc",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
    ".xml",
}
MAX_TEXT_PREVIEW_CHARS = 12000
URL_RE = re.compile(r"https?://[^\s<>\"]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera inbox-preview.html com preview visual de Inbox4Mobile."
    )
    parser.add_argument(
        "--inbox-dir",
        default="Inbox4Mobile",
        help="Pasta de entrada (default: Inbox4Mobile).",
    )
    parser.add_argument(
        "--output",
        default="inbox-preview.html",
        help="Arquivo HTML de saida (default: inbox-preview.html).",
    )
    parser.add_argument(
        "--index-output",
        default="_preview-index.json",
        help="Arquivo JSON com indice leve dos itens (default: _preview-index.json ao lado do HTML).",
    )
    return parser.parse_args()


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024.0
    return f"{size} B"


def format_dt(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def rel_url(base_dir: Path, target_path: Path) -> str:
    rel = os.path.relpath(target_path, base_dir)
    return "/".join(quote(part) for part in Path(rel).parts)


def extract_youtube_id(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.strip("/")

    if host == "youtu.be" and path:
        return path.split("/")[0]

    if host in {"youtube.com", "m.youtube.com"}:
        if path == "watch":
            vid = parse_qs(parsed.query).get("v", [None])[0]
            return vid
        if path.startswith("shorts/"):
            return path.split("/", 1)[1].split("/")[0]
        if path.startswith("embed/"):
            return path.split("/", 1)[1].split("/")[0]

    return None


def extract_first_url(text: str) -> str | None:
    match = URL_RE.search(text)
    return match.group(0).rstrip(".,);]") if match else None


def read_text_file(path: Path) -> str:
    try:
        data = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        data = path.read_text(encoding="latin-1", errors="replace")
    if len(data) > MAX_TEXT_PREVIEW_CHARS:
        data = data[:MAX_TEXT_PREVIEW_CHARS] + "\n\n[... preview truncado ...]"
    return data


def parse_url_file_contents(text: str) -> str | None:
    # .url format comum no Windows: [InternetShortcut]\nURL=https://...
    for line in text.splitlines():
        if line.upper().startswith("URL="):
            return line.split("=", 1)[1].strip()
    return extract_first_url(text)


def preview_image(path: Path, output_dir: Path) -> str:
    src = rel_url(output_dir, path)
    extra = "<p class='hint'>Imagem exibida por caminho local (sem inline base64).</p>"
    return (
        f"<div class='preview image'>"
        f"<img src='{escape(src)}' alt='{escape(path.name)}' loading='lazy'/>"
        f"{extra}</div>"
    )


def preview_pdf(path: Path, output_dir: Path) -> str:
    src = rel_url(output_dir, path)
    return (
        "<div class='preview pdf'>"
        f"<iframe title='{escape(path.name)}' src='{escape(src)}#view=FitH'></iframe>"
        f"<p><a href='{escape(src)}' target='_blank' rel='noopener noreferrer'>Abrir PDF em nova aba</a></p>"
        "</div>"
    )


def preview_text(path: Path) -> tuple[str, bool]:
    text = read_text_file(path)
    ext = path.suffix.lower()
    link_url = parse_url_file_contents(text) if ext in {".url", ".webloc"} else extract_first_url(text)
    youtube_id = extract_youtube_id(link_url) if link_url else None

    blocks: list[str] = ["<div class='preview text'>"]
    is_youtube = False

    if youtube_id:
        is_youtube = True
        embed = f"https://www.youtube.com/embed/{youtube_id}"
        thumb = f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg"
        watch = link_url or f"https://www.youtube.com/watch?v={youtube_id}"
        blocks.append(
            "<div class='youtube-preview' "
            f"data-embed='{escape(embed)}' "
            f"data-watch='{escape(watch)}' "
            f"data-thumb='{escape(thumb)}'>"
            "<div class='youtube-loading'>Preparando preview do YouTube...</div>"
            "</div>"
        )
        if link_url:
            safe = escape(link_url)
            blocks.append(
                f"<p><a href='{safe}' target='_blank' rel='noopener noreferrer'>{safe}</a></p>"
            )
    elif link_url:
        safe = escape(link_url)
        blocks.append(
            f"<p class='link-preview'><a href='{safe}' target='_blank' rel='noopener noreferrer'>{safe}</a></p>"
        )

    blocks.append(f"<pre>{escape(text)}</pre>")
    blocks.append("</div>")
    return "".join(blocks), is_youtube


def preview_generic(path: Path, output_dir: Path) -> str:
    src = rel_url(output_dir, path)
    return (
        "<div class='preview generic'>"
        "<p>Sem preview dedicado para este tipo de arquivo.</p>"
        f"<p><a href='{escape(src)}' target='_blank' rel='noopener noreferrer'>Abrir arquivo</a></p>"
        "</div>"
    )


def resolve_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"
    return "generic"


def item_card(index: int, path: Path, output_dir: Path) -> str:
    stat = path.stat()
    kind = resolve_kind(path)
    is_youtube = False
    if kind == "image":
        preview_html = preview_image(path, output_dir)
        type_label = "Imagem"
    elif kind == "pdf":
        preview_html = preview_pdf(path, output_dir)
        type_label = "PDF"
    elif kind == "text":
        preview_html, is_youtube = preview_text(path)
        type_label = "Texto/Link"
    else:
        preview_html = preview_generic(path, output_dir)
        type_label = "Arquivo"

    cmd_process = f"processar item {index}"
    cmd_move_ideas = f"mover item {index} para IDEIAS.md"
    cmd_discard = f"descartar item {index}"
    commands = [
        ("Copiar: processar", cmd_process),
        ("Copiar: mover para IDEIAS", cmd_move_ideas),
        ("Copiar: descartar", cmd_discard),
    ]
    if is_youtube:
        commands.insert(1, ("Copiar: youtube-extractor", f"processar item {index} com youtube-extractor"))

    buttons = "".join(
        (
            "<button type='button' class='copy-btn' "
            f"onclick='copyCmd({json.dumps(cmd)})'>{escape(label)}</button>"
        )
        for label, cmd in commands
    )

    return (
        "<article class='item-card'>"
        f"<h2>Item {index}</h2>"
        "<div class='meta'>"
        f"<p><strong>Nome:</strong> {escape(path.name)}</p>"
        f"<p><strong>Entrada:</strong> {escape(format_dt(stat.st_mtime))}</p>"
        f"<p><strong>Tipo:</strong> {escape(type_label)}</p>"
        f"<p><strong>Tamanho:</strong> {escape(format_bytes(stat.st_size))}</p>"
        "</div>"
        f"{preview_html}"
        f"<div class='actions'>{buttons}</div>"
        "</article>"
    )


def build_index_entry(path: Path) -> dict[str, str | int | None]:
    stat = path.stat()
    kind = resolve_kind(path)
    first_url: str | None = None
    if kind == "text":
        text = read_text_file(path)
        ext = path.suffix.lower()
        first_url = parse_url_file_contents(text) if ext in {".url", ".webloc"} else extract_first_url(text)

    return {
        "filename": path.name,
        "absolute_path": str(path.resolve()),
        "kind": kind,
        "size_bytes": stat.st_size,
        "mtime_iso": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "fingerprint": f"{stat.st_mtime_ns}:{stat.st_size}",
        "first_url": first_url,
    }


def iter_files(inbox_dir: Path, exclude_paths: set[Path]) -> Iterable[Path]:
    for path in sorted(
        inbox_dir.iterdir(),
        key=lambda p: (p.stat().st_mtime, p.name.lower()),
        reverse=True,
    ):
        if not path.is_file():
            continue
        if path.name == "_processed.json":
            continue
        if path.resolve() in exclude_paths:
            continue
        yield path


def build_html(cards: str, count: int) -> str:
    generated = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Inbox Preview</title>
  <style>
    :root {{
      --bg: #f4f6f8;
      --surface: #ffffff;
      --ink: #11212d;
      --muted: #4a6170;
      --accent: #006b75;
      --accent-2: #0b7285;
      --line: #d6e0e6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(160deg, #eef3f7 0%, #f8fbfd 100%);
      color: var(--ink);
    }}
    header {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 24px 12px;
    }}
    h1 {{ margin: 0; font-size: 1.8rem; }}
    .summary {{ color: var(--muted); margin-top: 8px; }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 16px 24px 32px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 16px;
    }}
    .item-card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      box-shadow: 0 2px 12px rgba(0, 25, 35, 0.05);
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 340px;
    }}
    .item-card h2 {{ margin: 0; font-size: 1.1rem; }}
    .meta p {{ margin: 4px 0; font-size: 0.92rem; color: var(--muted); }}
    .preview {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fbfdff;
      padding: 8px;
      min-height: 160px;
      overflow: hidden;
    }}
    .preview img {{
      width: 100%;
      max-height: 360px;
      object-fit: contain;
      border-radius: 8px;
      background: #eef2f5;
    }}
    .preview iframe {{
      width: 100%;
      height: 280px;
      border: 0;
      border-radius: 8px;
      background: #fff;
    }}
    .preview pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.85rem;
      line-height: 1.4;
      color: #19313f;
      max-height: 260px;
      overflow: auto;
    }}
    .link-preview {{
      margin: 0 0 8px;
      font-size: 0.9rem;
      word-break: break-all;
    }}
    .youtube-preview {{
      position: relative;
      width: 100%;
      margin-bottom: 8px;
      border-radius: 8px;
      overflow: hidden;
      background: #111;
      border: 1px solid #1f2a33;
    }}
    .youtube-preview iframe {{
      width: 100%;
      height: 280px;
      border: 0;
      border-radius: 8px;
      display: block;
      background: #111;
    }}
    .youtube-loading {{
      color: #c7d7e1;
      font-size: 0.86rem;
      padding: 14px;
    }}
    .yt-fallback-link {{
      display: block;
      color: #fff;
      text-decoration: none;
      background: #111;
    }}
    .yt-fallback-thumb {{
      width: 100%;
      display: block;
      aspect-ratio: 16 / 9;
      object-fit: cover;
      background: #111;
    }}
    .yt-fallback-caption {{
      padding: 10px 12px;
      font-size: 0.9rem;
      color: #d7e3ea;
      border-top: 1px solid rgba(255,255,255,0.12);
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: auto;
    }}
    .copy-btn {{
      border: 1px solid var(--accent);
      background: #f2fbfd;
      color: var(--accent-2);
      font-size: 0.83rem;
      padding: 7px 9px;
      border-radius: 8px;
      cursor: pointer;
    }}
    .copy-btn:hover {{ background: #def4f7; }}
    .hint {{ margin: 8px 0 0; color: var(--muted); font-size: 0.82rem; }}
    .empty {{
      background: var(--surface);
      border: 1px dashed var(--line);
      border-radius: 12px;
      padding: 24px;
      color: var(--muted);
    }}
    .toast {{
      position: fixed;
      right: 18px;
      bottom: 18px;
      background: #0c7d5a;
      color: #fff;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 0.86rem;
      opacity: 0;
      transition: opacity 180ms ease;
      pointer-events: none;
    }}
    .toast.show {{ opacity: 1; }}
  </style>
</head>
<body>
  <header>
    <h1>Inbox Preview</h1>
    <p class="summary">Itens: <strong>{count}</strong> · Gerado em: <strong>{generated}</strong></p>
  </header>
  <main>
    {cards if cards else "<section class='empty'>Inbox4Mobile sem itens para preview.</section>"}
  </main>
  <div id="toast" class="toast">Comando copiado.</div>
  <script>
    function renderYouTubeFallback(el) {{
      const watch = el.dataset.watch || '';
      const thumb = el.dataset.thumb || '';
      const safeWatch = watch.replace(/"/g, '&quot;');
      const safeThumb = thumb.replace(/"/g, '&quot;');
      el.innerHTML = `
        <a class="yt-fallback-link" href="${{safeWatch}}" target="_blank" rel="noopener noreferrer">
          <img class="yt-fallback-thumb" src="${{safeThumb}}" alt="Thumbnail do YouTube" loading="lazy" />
          <div class="yt-fallback-caption">Abrir video no YouTube</div>
        </a>
      `;
    }}

    function renderYouTubeEmbed(el) {{
      const embed = el.dataset.embed || '';
      if (!embed) {{
        renderYouTubeFallback(el);
        return;
      }}
      const iframe = document.createElement('iframe');
      iframe.title = 'YouTube preview';
      iframe.src = embed;
      iframe.allowFullscreen = true;
      iframe.loading = 'lazy';
      iframe.referrerPolicy = 'strict-origin-when-cross-origin';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      iframe.addEventListener('error', () => renderYouTubeFallback(el));
      el.innerHTML = '';
      el.appendChild(iframe);
    }}

    function hydrateYouTubePreviews() {{
      document.querySelectorAll('.youtube-preview').forEach((el) => {{
        if (window.location.protocol === 'file:') {{
          // YouTube costuma bloquear embeds sem referer em arquivo local (erro 153).
          renderYouTubeFallback(el);
          return;
        }}
        renderYouTubeEmbed(el);
      }});
    }}

    async function copyCmd(text) {{
      try {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          await navigator.clipboard.writeText(text);
        }} else {{
          const input = document.createElement('textarea');
          input.value = text;
          document.body.appendChild(input);
          input.select();
          document.execCommand('copy');
          document.body.removeChild(input);
        }}
        const toast = document.getElementById('toast');
        toast.textContent = 'Copiado: ' + text;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 1800);
      }} catch (err) {{
        alert('Falha ao copiar. Comando: ' + text);
      }}
    }}

    hydrateYouTubePreviews();
  </script>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    inbox_dir = (root / args.inbox_dir).resolve()
    output_path = (root / args.output).resolve()
    index_output_raw = Path(args.index_output)
    if index_output_raw.is_absolute():
        index_output_path = index_output_raw
    else:
        index_output_path = (root / index_output_raw).resolve()

    if not inbox_dir.exists() or not inbox_dir.is_dir():
        raise SystemExit(f"Inbox não encontrado: {inbox_dir}")

    output_dir = output_path.parent

    excluded = {output_path.resolve()}
    if index_output_path.exists():
        excluded.add(index_output_path.resolve())

    cards: list[str] = []
    index_entries: list[dict[str, str | int | None]] = []
    for idx, file_path in enumerate(iter_files(inbox_dir, excluded), start=1):
        cards.append(item_card(idx, file_path, output_dir))
        index_entries.append(build_index_entry(file_path))

    html_doc = build_html("\n".join(cards), len(cards))
    output_path.write_text(html_doc, encoding="utf-8")
    index_payload = {
        "generated_at": dt.datetime.now().isoformat(),
        "inbox_dir": str(inbox_dir),
        "items": index_entries,
    }
    index_output_path.write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"ok: {output_path}")
    print(f"index: {index_output_path}")
    print(f"items: {len(cards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
