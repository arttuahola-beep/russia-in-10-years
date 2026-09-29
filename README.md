# Russia in 10 years

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
