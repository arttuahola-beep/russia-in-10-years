#!/usr/bin/env python3
"""Build the static Russia in 10 years site from updates/*/update.md.

Python 3 standard library only. Run from anywhere:

    python3 scripts/build_site.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPDATES_DIR = ROOT / "updates"

SITE_TITLE = "Russia in 10 years"
TAGLINE = (
    "A rolling ten-year forecast of Russia, revised on weekdays by a chair and three philosophers."
)
VISION_WORDS_MIN = 600
VISION_WORDS_MAX = 1200
PHILOSOPHERS = ("Pufendorf", "Popper", "Socrates")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
HREF_RE = re.compile(r"""href=(['"])(.*?)\1""")


@dataclass
class Section:
    title: str
    body_md: str
    full_md: str

    @property
    def key(self) -> str:
        return self.title.strip().lower()


@dataclass
class Update:
    folder: Path
    published: date
    horizon: date
    headline: str
    summary: str
    body_md: str
    sections: list[Section] = field(default_factory=list)

    def section(self, *prefixes: str) -> Section | None:
        for section in self.sections:
            for prefix in prefixes:
                if section.key == prefix or section.key.startswith(prefix):
                    return section
        return None

    @property
    def slug_path(self) -> str:
        return f"updates/{self.published.isoformat()}/"


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def add_years(day: date, years: int) -> date:
    """Return day plus `years`, using 28 February when 29 February does not exist."""
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)


def long_date(day: date) -> str:
    return f"{day.strftime('%A')} {day.day} {day.strftime('%B %Y')}"


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def word_count(markdown: str) -> int:
    lines: list[str] = []
    for line in markdown.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^\s*[-*]\s+", "", line)
        line = re.sub(r"^\s*\d+\.\s+", "", line)
        line = line.replace("**", "")
        lines.append(line)
    return len(" ".join(lines).split())


def parse_front_matter(text: str, path: Path) -> tuple[dict[str, str], str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        fail([f"{path}: starts without YAML front matter"])
    meta: dict[str, str] = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            body = "\n".join(lines[index + 1 :]).strip()
            return meta, body + "\n"
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            fail([f"{path}: front matter line is not key: value ({line!r})"])
        meta[key.strip()] = value.strip().strip('"').strip("'")
    fail([f"{path}: front matter is not closed"])
    return {}, ""


def split_sections(body: str) -> list[Section]:
    chunks = re.split(r"(?m)^(?=## )", body.strip())
    sections: list[Section] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.startswith("## "):
            continue
        heading, _, rest = chunk.partition("\n")
        title = heading[3:].strip()
        sections.append(Section(title=title, body_md=rest.strip(), full_md=chunk))
    return sections


def parse_update(folder: Path) -> Update:
    path = folder / "update.md"
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path)
    errors: list[str] = []
    for key in ("date", "horizon", "headline", "summary"):
        if not meta.get(key):
            errors.append(f"{path}: missing front matter field {key}")
    if errors:
        fail(errors)

    published_text = meta["date"]
    horizon_text = meta["horizon"]
    if not DATE_RE.match(published_text):
        errors.append(f"{path}: date must be YYYY-MM-DD")
    if not DATE_RE.match(horizon_text):
        errors.append(f"{path}: horizon must be YYYY-MM-DD")
    if folder.name != published_text:
        errors.append(
            f"{path}: date {published_text} does not match folder {folder.name}"
        )
    if errors:
        fail(errors)

    published = date.fromisoformat(published_text)
    horizon = date.fromisoformat(horizon_text)
    expected = add_years(published, 10)
    if horizon != expected:
        fail(
            [
                f"{path}: horizon must be the publication date plus 10 years "
                f"({expected.isoformat()}, found {horizon.isoformat()})"
            ]
        )

    update = Update(
        folder=folder,
        published=published,
        horizon=horizon,
        headline=meta["headline"].strip(),
        summary=meta["summary"].strip(),
        body_md=body,
        sections=split_sections(body),
    )
    validate_update(update, path)
    return update


def validate_update(update: Update, path: Path) -> None:
    errors: list[str] = []
    changed = update.section("what changed today")
    vision = update.section("vision for")
    philosophers = update.section("philosophers")
    if changed is None:
        errors.append(f"{path}: missing section 'What changed today'")
    elif not changed.body_md.strip():
        errors.append(f"{path}: 'What changed today' is empty")
    if vision is None:
        errors.append(f"{path}: missing section 'Vision for …'")
    else:
        if str(update.horizon.year) not in vision.title:
            errors.append(
                f"{path}: vision heading {vision.title!r} should name the "
                f"horizon year {update.horizon.year}"
            )
        count = word_count(vision.full_md)
        if not VISION_WORDS_MIN <= count <= VISION_WORDS_MAX:
            errors.append(
                f"{path}: vision is {count} words; expected "
                f"{VISION_WORDS_MIN}–{VISION_WORDS_MAX}"
            )
    if philosophers is None:
        errors.append(f"{path}: missing section 'Philosophers'")
    else:
        for name in PHILOSOPHERS:
            if name not in philosophers.body_md:
                errors.append(f"{path}: philosophers section does not mention {name}")
    if changed is not None and not re.search(r"(?m)^[-*] ", changed.body_md):
        print(
            f"warning: {path}: 'What changed today' has no bullet list of deltas",
            file=sys.stderr,
        )

    order = [section.key for section in update.sections]
    required_prefixes = ("what changed today", "vision for", "philosophers")
    positions = []
    for prefix in required_prefixes:
        found = next((i for i, key in enumerate(order) if key.startswith(prefix)), None)
        if found is not None:
            positions.append(found)
    if positions != sorted(positions):
        errors.append(
            f"{path}: sections must run What changed today, Vision, Philosophers, "
            "then optional Falsifiers"
        )
    falsifiers_at = next((i for i, key in enumerate(order) if key.startswith("falsifiers")), None)
    philosophers_at = next(
        (i for i, key in enumerate(order) if key.startswith("philosophers")), None
    )
    if (
        falsifiers_at is not None
        and philosophers_at is not None
        and falsifiers_at < philosophers_at
    ):
        errors.append(f"{path}: Falsifiers should follow Philosophers")
    if errors:
        fail(errors)
    if update.published.weekday() >= 5:
        print(
            f"warning: {update.published.isoformat()} is a weekend; "
            "the series is revised on weekdays",
            file=sys.stderr,
        )


def load_updates() -> list[Update]:
    if not UPDATES_DIR.is_dir():
        fail([f"no updates directory at {UPDATES_DIR}"])
    folders = sorted(
        path for path in UPDATES_DIR.iterdir() if path.is_dir() and (path / "update.md").is_file()
    )
    if not folders:
        fail(["no updates/*/update.md files found"])
    updates = [parse_update(folder) for folder in folders]
    seen: set[str] = set()
    for update in updates:
        key = update.published.isoformat()
        if key in seen:
            fail([f"duplicate update date {key}"])
        seen.add(key)
    updates.sort(key=lambda item: item.published, reverse=True)
    return updates


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def inline(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in LINK_RE.finditer(text):
        parts.append(format_plain(text[cursor : match.start()]))
        label = format_plain(match.group(1))
        url = match.group(2).strip()
        if re.match(r"^(https?:|/|\.|#)", url):
            parts.append(f'<a href="{html.escape(url, quote=True)}">{label}</a>')
        else:
            parts.append(format_plain(match.group(0)))
        cursor = match.end()
    parts.append(format_plain(text[cursor:]))
    return "".join(parts)


def format_plain(text: str) -> str:
    escaped = html.escape(text, quote=False)
    return BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def is_heading(line: str) -> bool:
    return bool(re.match(r"^#{1,3} ", line))


def is_ul(line: str) -> bool:
    return bool(re.match(r"^[-*] ", line))


def is_ol(line: str) -> bool:
    return bool(re.match(r"^\d+\. ", line))


def is_quote(line: str) -> bool:
    return line.startswith(">")


def is_fence(line: str) -> bool:
    return line.startswith("```")


def md_to_html(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[str] = []
    used_ids: set[str] = set()
    index = 0

    def next_id(title: str) -> str:
        base = slugify(title)
        slug = base
        number = 2
        while slug in used_ids:
            slug = f"{base}-{number}"
            number += 1
        used_ids.add(slug)
        return slug

    def blank_then(predicate) -> bool:
        probe = index
        if probe >= len(lines) or lines[probe].strip():
            return False
        while probe < len(lines) and not lines[probe].strip():
            probe += 1
        return probe < len(lines) and predicate(lines[probe])

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if is_fence(line):
            index += 1
            code: list[str] = []
            while index < len(lines) and not is_fence(lines[index]):
                code.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            blocks.append(f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>")
            continue
        heading = re.match(r"^(#{1,3}) (.+)$", line)
        if heading:
            level = len(heading.group(1))
            # The page already has an h1. Markdown headings step down one level
            # past the third hash, which stays an h3.
            tag = {1: "h2", 2: "h2", 3: "h3"}[level]
            title = heading.group(2).strip()
            blocks.append(
                f'<{tag} id="{next_id(title)}">{inline(title)}</{tag}>'
            )
            index += 1
            continue
        if is_quote(line):
            quoted: list[str] = []
            while index < len(lines) and (is_quote(lines[index]) or not lines[index].strip()):
                if not lines[index].strip():
                    if not blank_then(is_quote):
                        break
                    quoted.append("")
                    index += 1
                    continue
                quoted.append(re.sub(r"^>\s?", "", lines[index]))
                index += 1
            paragraph = " ".join(part.strip() for part in quoted if part.strip())
            blocks.append(f"<blockquote><p>{inline(paragraph)}</p></blockquote>")
            continue
        if is_ul(line) or is_ol(line):
            ordered = is_ol(line)
            predicate = is_ol if ordered else is_ul
            items: list[str] = []
            while index < len(lines):
                current = lines[index]
                if predicate(current):
                    item = re.sub(r"^([-*]|\d+\.)\s+", "", current).strip()
                    items.append(f"<li>{inline(item)}</li>")
                    index += 1
                    continue
                if not current.strip() and blank_then(predicate):
                    index += 1
                    continue
                break
            tag = "ol" if ordered else "ul"
            blocks.append(f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>")
            continue
        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not block_start(lines[index]):
            paragraph_lines.append(lines[index].strip())
            index += 1
        blocks.append(f"<p>{inline(' '.join(paragraph_lines))}</p>")
    return "\n".join(blocks)


def block_start(line: str) -> bool:
    return (
        is_heading(line)
        or is_ul(line)
        or is_ol(line)
        or is_quote(line)
        or is_fence(line)
    )


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else "" for line in text.strip("\n").split("\n"))


def page(title: str, description: str, depth: int, main: str) -> str:
    prefix = "../" * depth
    home = f"{prefix}index.html"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title, quote=True)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="theme-color" content="#f6f5f2" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#12161b" media="(prefers-color-scheme: dark)">
  <link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap">
  <link rel="stylesheet" href="{prefix}styles.css">
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <div class="wrap">
    <header>
      <a class="site-title" href="{home}">{html.escape(SITE_TITLE)}</a>
      <p class="tagline">{html.escape(TAGLINE)}</p>
    </header>
    <main id="main">
{indent(main, 6)}
    </main>
    <footer>
      <p>A weekday record of how the ten-year forecast of Russia moves. The horizon is the publication date plus ten years.</p>
      <p>Pufendorf, Popper, and Socrates comment. A forecast, not a promise.</p>
    </footer>
  </div>
</body>
</html>
"""


def kicker(update: Update) -> str:
    return (
        '<p class="kicker">'
        f'<time datetime="{update.published.isoformat()}">{html.escape(long_date(update.published))}</time> '
        f'<span class="pill">Horizon {html.escape(long_date(update.horizon))}</span>'
        "</p>"
    )


def revision_heading(update: Update) -> str:
    """Lead with the one-line change. The revision name stays a label."""
    return (
        f"{kicker(update)}\n"
        f'  <p class="revision-name">{html.escape(update.headline)}</p>\n'
        f"  <h1>{inline(update.summary)}</h1>"
    )


def render_index(update: Update) -> str:
    changed = update.section("what changed today")
    vision = update.section("vision for")
    assert changed is not None and vision is not None
    href = update.slug_path
    main = f"""
<article>
  {revision_heading(update)}
  <section class="changed" aria-labelledby="changed-heading">
    <h2 id="changed-heading">What changed today</h2>
    <div class="body">
{indent(md_to_html(changed.body_md), 6)}
    </div>
  </section>
  <details class="vision-fold">
    <summary>Vision for {html.escape(long_date(update.horizon))}</summary>
    <div class="body">
      <h2 id="vision-heading">{html.escape(vision.title)}</h2>
{indent(md_to_html(vision.body_md), 6)}
    </div>
  </details>
  <p class="more"><a href="{href}#philosophers">Philosophers and falsifiers</a></p>
  <p class="more"><a href="archive/">Revision timeline</a></p>
</article>
"""
    description = f"{update.summary} Horizon {long_date(update.horizon)}."
    return page(SITE_TITLE, description, 0, main)


def render_update(update: Update, updates: list[Update]) -> str:
    position = next(i for i, item in enumerate(updates) if item.published == update.published)
    # updates are newest first, so the previous publication is later in the list.
    older = updates[position + 1] if position + 1 < len(updates) else None
    newer = updates[position - 1] if position > 0 else None
    pager_parts: list[str] = []
    if older is not None:
        pager_parts.append(
            f'<a href="../../{older.slug_path}">'
            '<span class="pager-dir">Previous</span>'
            f'<span class="pager-title">{html.escape(older.headline)}</span>'
            "</a>"
        )
    if newer is not None:
        pager_parts.append(
            f'<a href="../../{newer.slug_path}">'
            '<span class="pager-dir">Next</span>'
            f'<span class="pager-title">{html.escape(newer.headline)}</span>'
            "</a>"
        )
    pager_parts.append('<a class="pager-home" href="../../archive/">Revision timeline</a>')
    pager_parts.append('<a class="pager-home" href="../../index.html">Latest revision</a>')
    pager = "\n".join(pager_parts)
    changed = update.section("what changed today")
    vision = update.section("vision for")
    assert changed is not None and vision is not None
    later_sections = [
        section
        for section in update.sections
        if section is not changed and section is not vision
    ]
    later_html = []
    for section in later_sections:
        later_html.append(
            f'<section class="commentary">\n'
            f'  <h2 id="{slugify(section.title)}">{html.escape(section.title)}</h2>\n'
            f'  <div class="body">\n'
            f'{indent(md_to_html(section.body_md), 4)}\n'
            f'  </div>\n'
            f'</section>'
        )
    main = f"""
<article>
  {revision_heading(update)}
  <section class="changed" aria-labelledby="what-changed-today">
    <h2 id="what-changed-today">What changed today</h2>
    <div class="body">
{indent(md_to_html(changed.body_md), 6)}
    </div>
  </section>
  <details class="vision-fold">
    <summary>Show the full vision</summary>
    <div class="body">
      <h2 id="{slugify(vision.title)}">{html.escape(vision.title)}</h2>
{indent(md_to_html(vision.body_md), 6)}
    </div>
  </details>
{indent(chr(10).join(later_html), 2)}
  <p class="source"><a href="update.md">Markdown source</a></p>
</article>
<nav class="pager" aria-label="Other revisions">
{indent(pager, 2)}
</nav>
"""
    title = f"{update.summary} — {SITE_TITLE}"
    description = f"{update.summary} Horizon {long_date(update.horizon)}."
    return page(title, description, 2, main)


def render_archive(updates: list[Update]) -> str:
    items: list[str] = []
    for update in updates:
        items.append(
            "<li>\n"
            f'  <a href="../{update.slug_path}">\n'
            '    <span class="item-meta">'
            f'<time datetime="{update.published.isoformat()}">{html.escape(long_date(update.published))}</time> '
            f'<span class="pill">Horizon {update.horizon.year}</span>'
            "</span>\n"
            '    <span class="change-label">What changed</span>\n'
            f'    <span class="item-title">{html.escape(update.summary)}</span>\n'
            f'    <span class="item-name">{html.escape(update.headline)}</span>\n'
            "  </a>\n"
            "</li>"
        )
    main = f"""
<h1>Revisions</h1>
<p class="dek">A timeline of how the forecast moved, newest first. Each row is a change, not a separate essay. The horizon is ten years after that day's date.</p>
<ul class="takeaways">
{indent(chr(10).join(items), 2)}
</ul>
"""
    return page(
        f"Revisions — {SITE_TITLE}",
        "A timeline of how the ten-year forecast changed, newest first.",
        1,
        main,
    )


def render_404() -> str:
    main = """
<h1>Page not found</h1>
<p class="dek">That page is not part of the forecast.</p>
<p class="more"><a href="index.html">Latest revision</a></p>
"""
    return page(f"Page not found — {SITE_TITLE}", TAGLINE, 0, main)


def write_current(update: Update) -> None:
    vision = update.section("vision for")
    assert vision is not None
    text = (
        "---\n"
        f"date: {update.published.isoformat()}\n"
        f"horizon: {update.horizon.isoformat()}\n"
        f"headline: {yaml_quote(update.headline)}\n"
        f"summary: {yaml_quote(update.summary)}\n"
        f"source: {update.slug_path}update.md\n"
        "---\n\n"
        f"{vision.full_md.strip()}\n"
    )
    path = ROOT / "vision" / "current.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(updates: list[Update]) -> None:
    payload = {
        "title": SITE_TITLE,
        "tagline": TAGLINE,
        "updates": [
            {
                "date": update.published.isoformat(),
                "horizon": update.horizon.isoformat(),
                "headline": update.headline,
                "summary": update.summary,
                "path": update.slug_path,
            }
            for update in updates
        ],
    }
    path = UPDATES_DIR / "updates.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_stale_pages(updates: list[Update]) -> None:
    live = {update.folder.resolve() for update in updates}
    for page_path in UPDATES_DIR.glob("*/index.html"):
        if page_path.parent.resolve() not in live:
            page_path.unlink()
            print(f"removed stale {page_path.relative_to(ROOT)}")


STYLES = """/* Generated by scripts/build_site.py. Edit that file and rebuild. */
:root {
  color-scheme: light;
  --bg: #f6f5f2;
  --text: #1a1d21;
  --muted: #4e555d;
  --accent: #1f5c99;
  --pill-bg: #e5eef6;
  --pill-text: #1a4e80;
  --line: #e2e0da;
  --selection: #d5e4f5;
  --code-bg: #e5eef6;
}

@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --bg: #12161b;
    --text: #eceae4;
    --muted: #b0b6bd;
    --accent: #9ec4ee;
    --pill-bg: #1c2c3d;
    --pill-text: #c5ddf6;
    --line: #2c333c;
    --selection: #1f5c99;
    --code-bg: #1c2c3d;
  }
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  -webkit-text-size-adjust: 100%;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 1.0625rem;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}

body::before {
  content: "";
  display: block;
  height: 4px;
  background: var(--accent);
}

::selection {
  background: var(--selection);
  color: var(--text);
}

.skip {
  position: absolute;
  left: 0.75rem;
  top: 0.75rem;
  padding: 0.35rem 0.7rem;
  background: var(--bg);
  color: var(--accent);
  font-weight: 600;
  text-decoration: none;
  transform: translateY(-160%);
}

.skip:focus {
  transform: none;
}

.wrap {
  width: min(100%, calc(680px + 2.5rem));
  margin: 0 auto;
  padding: 2.25rem 1.25rem 3.5rem;
}

header {
  margin-bottom: 2.75rem;
}

.site-title {
  color: var(--accent);
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.015em;
  text-decoration: none;
}

.site-title:hover {
  text-decoration: underline;
  text-underline-offset: 0.18em;
}

.tagline {
  margin: 0.4rem 0 0;
  color: var(--muted);
  font-size: 0.98rem;
  line-height: 1.5;
}

.revision-name {
  margin: 0.9rem 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  line-height: 1.4;
  text-transform: uppercase;
}

h1 {
  margin: 0.35rem 0 1.5rem;
  font-size: clamp(1.7rem, 4.6vw, 2.3rem);
  font-weight: 700;
  letter-spacing: -0.028em;
  line-height: 1.18;
  text-wrap: balance;
}

h2 {
  margin: 0 0 0.35rem;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  line-height: 1.4;
  text-transform: uppercase;
}

p {
  overflow-wrap: break-word;
}

.kicker {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem 0.7rem;
  margin: 0;
}

time {
  color: var(--muted);
  font-size: 0.95rem;
}

.pill {
  display: inline-block;
  padding: 0.18rem 0.62rem;
  border-radius: 999px;
  background: var(--pill-bg);
  color: var(--pill-text);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.4;
}

.dek {
  margin: 0.2rem 0 2rem;
  color: var(--muted);
  font-size: 1.125rem;
  line-height: 1.5;
}

.changed,
.forecast,
.commentary {
  margin: 0 0 2.5rem;
}

.changed {
  padding-left: 1rem;
  border-left: 3px solid var(--accent);
}

.changed .body,
.forecast .body,
.commentary .body {
  margin-top: 0.85rem;
}

.forecast-note {
  margin: 0.35rem 0 0.9rem;
  color: var(--muted);
  font-size: 0.98rem;
  line-height: 1.5;
}

.vision-fold {
  margin: 0.35rem 0 1.5rem;
}

.vision-fold summary {
  display: inline-block;
  padding: 0.15rem 0;
  color: var(--accent);
  font-weight: 600;
  line-height: 1.4;
  cursor: pointer;
}

.vision-fold summary:hover {
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.vision-fold .body {
  margin-top: 1.15rem;
}

.body {
  font-size: 1.125rem;
  line-height: 1.7;
}

.body p,
.body ul,
.body ol,
.body blockquote,
.body pre {
  margin: 0 0 1.15rem;
}

.body p:last-child,
.body ul:last-child,
.body ol:last-child,
.body blockquote:last-child,
.body pre:last-child {
  margin-bottom: 0;
}

.body h2 {
  margin: 2.75rem 0 0.9rem;
}

.body h2:first-child {
  margin-top: 0;
}

.body h3 {
  margin: 1.9rem 0 0.6rem;
  color: var(--text);
  font-size: 1.2rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.3;
  text-transform: none;
}

.body a {
  color: var(--accent);
  text-underline-offset: 0.16em;
}

.body ul,
.body ol {
  padding-left: 1.25rem;
}

.body li {
  margin: 0.4rem 0;
}

.body li::marker {
  color: var(--accent);
}

.body blockquote {
  padding-left: 1rem;
  border-left: 3px solid var(--line);
}

.body pre {
  padding: 0.9rem 1rem;
  overflow: auto;
  background: var(--code-bg);
  border-radius: 6px;
  font-size: 0.92rem;
  line-height: 1.5;
}

.body code {
  font-family: ui-monospace, "Cascadia Code", "Segoe UI Mono", Menlo, Consolas, monospace;
}

strong {
  font-weight: 600;
}

.source {
  margin: 1.6rem 0 0;
  color: var(--muted);
  font-size: 0.95rem;
  line-height: 1.55;
}

.source a {
  color: var(--accent);
}

.takeaways {
  margin: 0;
  padding: 0;
  list-style: none;
}

.takeaways a {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4rem;
  padding: 1rem 0;
  border-top: 1px solid var(--line);
  color: inherit;
  text-decoration: none;
}

.takeaways li:last-child a {
  border-bottom: 1px solid var(--line);
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.6rem;
}

.change-label {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  line-height: 1.3;
  text-transform: uppercase;
}

.item-title {
  font-size: 1.08rem;
  font-weight: 600;
  letter-spacing: -0.015em;
  line-height: 1.35;
}

.item-name {
  color: var(--muted);
  font-size: 0.95rem;
  line-height: 1.4;
}

.takeaways a:hover .item-title,
.takeaways a:focus-visible .item-title {
  color: var(--accent);
}

.more {
  margin: 1.2rem 0 0;
}

.more a,
.pager a {
  color: var(--accent);
  font-weight: 600;
  text-decoration: none;
}

.more a:hover,
.pager a:hover {
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.pager {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1rem;
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--line);
}

.pager-dir {
  display: block;
  margin-bottom: 0.15rem;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  line-height: 1.3;
  text-transform: uppercase;
}

.pager-title {
  display: block;
  color: var(--text);
  font-weight: 600;
  line-height: 1.35;
}

.pager a:hover .pager-title,
.pager a:focus-visible .pager-title {
  color: var(--accent);
}

.pager-home {
  font-weight: 600;
}

footer {
  margin-top: 3.75rem;
  padding-top: 1.15rem;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.55;
}

footer p {
  margin: 0.3rem 0;
}

a:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: 2px;
}

@media (min-width: 720px) {
  .wrap {
    padding-top: 4.5rem;
    padding-bottom: 5rem;
  }

  header {
    margin-bottom: 3.25rem;
  }
}

@media (max-width: 380px) {
  .wrap {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .body {
    font-size: 1.0625rem;
  }
}
"""

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="Russia in 10 years">
  <rect width="32" height="32" rx="7" fill="#1f5c99"/>
  <circle cx="16" cy="11" r="2.1" fill="#f6f5f2"/>
  <path d="M6.5 22.5h19" stroke="#f6f5f2" stroke-width="1.8" stroke-linecap="round"/>
</svg>
"""

README = """# Russia in 10 years

A weekday record of how a ten-year forecast of Russia changes. The horizon is the publication date plus ten years. It is never a fixed year. The site is in English.

The thing to read is the history of the revisions. Each edition leads with what moved that day. The full vision is the living text those notes revise. It is kept, and it is not the front page.

A chair gathers Russia-related news. Three philosopher personas comment. Samuel von Pufendorf speaks to sovereignty, natural law, and the duties of states. Karl Popper speaks to the open society, piecemeal reform, and the refusal to treat history as a script. Socrates asks the questions that unsettle a confident forecast.

The site is static. Relative links are used throughout, so the same files work on GitHub Pages at `/russia-in-10-years/` and at a domain root.

## Read

- `index.html` — what changed today, then a short preview of the vision, then the revision timeline
- `archive/index.html` — every revision, newest first, listed by the change
- `updates/YYYY-MM-DD/index.html` — that day's change, with the full vision folded underneath
- `updates/updates.json` — the same list, for anything that wants data rather than HTML
- `vision/current.md` — the latest full vision, regenerated from the newest update

## Add a weekday update

Create `updates/YYYY-MM-DD/update.md`. The folder name and the `date` field must match. `horizon` must be that date plus ten years. When the day is 29 February and the horizon year is not a leap year, use 28 February.

```yaml
---
date: 2026-09-30
horizon: 2036-09-30
headline: Short title of the revision
summary: One line on what changed.
---
```

`summary` is the change in one line. It is the title of the day and the line the timeline shows. `headline` is the short name of the revision, shown as a label, not as the thing the reader meets first.

The body uses these sections, in order:

1. `## What changed today` — the primary note. Open with a changelog of bullets (what was revised, strengthened, weakened, or newly uncertain), then a short narrative. Compare with the previous vision.
2. `## Vision for YYYY` — the full living forecast after today's revisions, about 600 to 1200 words, naming the horizon year
3. `## Philosophers` — brief attributed notes from Pufendorf, Popper, and Socrates
4. `## Falsifiers` — optional; what evidence would force this vision to be revised

Rebuild from the repository root, or from anywhere:

```bash
python3 scripts/build_site.py
```

The script uses only the Python 3 standard library. It rewrites the HTML, `vision/current.md`, `updates/updates.json`, `styles.css`, `favicon.svg`, `404.html`, `.nojekyll`, and this README. Edit the Markdown under `updates/`, and edit `scripts/build_site.py` for the design. Do not hand-edit the generated pages.

## Publish

Serve the `main` branch root with GitHub Pages. No build workflow is required: the HTML in the repository is the site. `.nojekyll` tells Pages to serve the files as they are.

The project URL is `https://arttuahola-beep.github.io/russia-in-10-years/`.
"""


def write_static() -> None:
    (ROOT / "styles.css").write_text(STYLES, encoding="utf-8")
    (ROOT / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    (ROOT / "404.html").write_text(render_404(), encoding="utf-8")
    (ROOT / ".nojekyll").write_bytes(b"")
    (ROOT / "README.md").write_text(README, encoding="utf-8")


def check_calendar() -> None:
    if add_years(date(2026, 9, 29), 10) != date(2036, 9, 29):
        fail(["horizon arithmetic failed for 2026-09-29"])
    if add_years(date(2024, 2, 29), 10) != date(2034, 2, 28):
        fail(["horizon arithmetic failed for 29 February"])


def local_target(html_path: Path, href: str) -> Path | None:
    if href.startswith(("http://", "https://", "mailto:")):
        return None
    bare = href.split("#", 1)[0].split("?", 1)[0]
    if not bare:
        return None
    resolved = (html_path.parent / bare).resolve()
    if bare.endswith("/"):
        return resolved / "index.html"
    return resolved


def smoke(updates: list[Update]) -> None:
    errors: list[str] = []
    html_files = [
        ROOT / "index.html",
        ROOT / "archive" / "index.html",
        ROOT / "404.html",
    ]
    html_files.extend(update.folder / "index.html" for update in updates)
    required = html_files + [
        ROOT / "styles.css",
        ROOT / "favicon.svg",
        ROOT / ".nojekyll",
        ROOT / "README.md",
        ROOT / "vision" / "current.md",
        UPDATES_DIR / "updates.json",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")

    for html_path in html_files:
        if not html_path.is_file():
            continue
        text = html_path.read_text(encoding="utf-8")
        for _, href in HREF_RE.findall(text):
            target = local_target(html_path, href)
            if target is None:
                continue
            if not target.is_file():
                errors.append(
                    f"{html_path.relative_to(ROOT)} links to {href}, which is not a file"
                )

    index = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").is_file() else ""
    archive = (
        (ROOT / "archive" / "index.html").read_text(encoding="utf-8")
        if (ROOT / "archive" / "index.html").is_file()
        else ""
    )
    if updates:
        latest = updates[0]
        update_html_path = latest.folder / "index.html"
        update_html = update_html_path.read_text(encoding="utf-8") if update_html_path.is_file() else ""
        if f'href="{latest.slug_path}#philosophers"' not in index:
            errors.append("index does not link to the latest update")
        if 'href="archive/"' not in index:
            errors.append("index does not link to the archive")
        if "What changed today" not in index or "Vision for" not in index:
            errors.append("index is missing the vision or today's note")
        if f"<h1>{html.escape(latest.summary)}</h1>" not in index:
            errors.append("index title should be the change summary, not the vision name")
        if index.find("What changed today") > index.find("Vision for"):
            errors.append("index should lead with what changed, before the vision")
        if "<details" not in index:
            errors.append("index should fold the rest of the vision")
        if "Sovereignty is a duty before it is a licence." in index:
            errors.append("index should not repeat the philosopher excerpts")
        if f'href="../{latest.slug_path}"' not in archive:
            errors.append("archive does not link to the latest update")
        if f'<span class="item-title">{html.escape(latest.summary)}</span>' not in archive:
            errors.append("archive should lead each row with the change summary")
        if 'href="../../index.html"' not in update_html:
            errors.append("update page does not link home")
        if 'href="../../archive/"' not in update_html:
            errors.append("update page does not link to the archive")
        if "Sovereignty is a duty before it is a licence." not in update_html:
            errors.append("update page is missing the Pufendorf note")
        vision_text = (ROOT / "vision" / "current.md").read_text(encoding="utf-8")
        if "This is a baseline, not a prophecy." not in vision_text:
            errors.append("vision/current.md does not hold the latest vision")
        if "This is a baseline, not a prophecy." not in index:
            errors.append("index does not show the latest vision")
        data = json.loads((UPDATES_DIR / "updates.json").read_text(encoding="utf-8"))
        if data["updates"][0]["date"] != latest.published.isoformat():
            errors.append("updates.json is not ordered newest first")
        if data["updates"][0]["path"] != latest.slug_path:
            errors.append("updates.json path does not match the latest update")

    if errors:
        fail(errors)


def main() -> None:
    check_calendar()
    updates = load_updates()
    clean_stale_pages(updates)
    latest = updates[0]
    (ROOT / "index.html").write_text(render_index(latest), encoding="utf-8")
    archive_dir = ROOT / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(render_archive(updates), encoding="utf-8")
    for update in updates:
        (update.folder / "index.html").write_text(
            render_update(update, updates), encoding="utf-8"
        )
    write_json(updates)
    write_current(latest)
    write_static()
    smoke(updates)
    vision = latest.section("vision for")
    assert vision is not None
    print(f"Built {len(updates)} update{'s' if len(updates) != 1 else ''}.")
    print(
        f"Latest {latest.published.isoformat()} → {latest.horizon.isoformat()} "
        f"({word_count(vision.full_md)} vision words): {latest.headline}"
    )


if __name__ == "__main__":
    main()
