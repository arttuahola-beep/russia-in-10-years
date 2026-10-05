# Russia in 10 years

The public name is Russia in 10 years. The subject of the forecast is the Russian Federation. The site is in English.

Publish an edition every weekday, even when the ten-year vision does not change. The horizon is the publication date plus ten years. It is never a fixed year.

Each edition leads with the news. Take a few key stories. For each one, say whether it strengthens, weakens, leaves uncertain, or does not move the living vision. The vision text stays stable. Copy it forward word for word, except a light roll of the pictured calendar date to the new horizon, unless a material change requires a real rewrite.

`vision_revised` is the date the vision text was last rewritten. It is separate from the edition date. When the two dates match, that day revised the vision. When `vision_revised` is earlier, the vision was carried forward. On a later revision day, the page leads with a loud VISION REVISED banner. On a carry-forward day, it does not. The first edition sets the vision down, so it does not use that banner.

A chair gathers Russian Federation–related news. Three philosopher personas comment. bot Pufendorf speaks to sovereignty, natural law, and the duties of states. bot Popper speaks to the open society, piecemeal reform, and the refusal to treat history as a script. bot Socrates asks the questions that unsettle a confident forecast.

The site is static. Relative links are used throughout, so the same files work on GitHub Pages at `/russia-in-10-years/` and at a domain root.

## Read

- `index.html` — today's news, the vision-revised date, the vision folded, Society in ten points in full, then the timeline
- `archive/index.html` — every weekday edition, newest first, with the vision-revised date
- `updates/YYYY-MM-DD/index.html` — that day's news, with the full vision folded underneath and Society in ten points last
- `updates/updates.json` — the same list, for anything that wants data rather than HTML
- `vision/current.md` — the latest full vision, regenerated from the newest update, including `vision_revised`

## Add a weekday update

Create `updates/YYYY-MM-DD/update.md`. The folder name and the `date` field must match. `horizon` must be that date plus ten years. When the day is 29 February and the horizon year is not a leap year, use 28 February. `vision_revised` is the date the vision text was last materially rewritten (`YYYY-MM-DD`). It cannot be later than the edition date. On a carry-forward day, keep the previous value. On a revision day, set it to today's date.

```yaml
---
date: 2026-10-05
horizon: 2036-10-05
vision_revised: 2026-09-30
headline: Short title of the day's news
summary: One line on what the news did to the living vision.
---
```

`summary` is the day in one line. It is the title of the edition and the line the timeline shows. `headline` is a short label. On a day that rewrites the vision, lead the headline or summary with VISION REVISED so the change is obvious. The builder also prints a loud banner when `vision_revised` equals `date` after the first edition.

The body uses these sections, in order:

1. `## What changed today` — the primary note. Open with a changelog of bullets (strengthened, weakened, newly uncertain, or not moved), then a short narrative. On a carry-forward day, say that the vision text is unchanged and name the vision-revised date. On a revision day, say what was rewritten.
2. `## Vision for YYYY` — the full living forecast, about 600 to 1250 words, naming the horizon year. Copy the previous text forward, and roll the pictured calendar date to the new horizon, unless the news forces a material rewrite.
3. `## Philosophers` — brief attributed notes from bot Pufendorf, bot Popper, and bot Socrates
4. `## Falsifiers` — optional; what evidence would force this vision to be revised
5. `## Society in ten points` — required last section, after Philosophers and after Falsifiers when that section is present. The ten labels stay fixed. Carry the same lines forward; rewrite a line only when the vision itself has a material social change, not when the day's news only deepens an already-named path.

Rebuild from the repository root, or from anywhere:

```bash
python3 scripts/build_site.py
```

The script uses only the Python 3 standard library. It rewrites the HTML, `vision/current.md`, `updates/updates.json`, `styles.css`, `favicon.svg`, `404.html`, `.nojekyll`, and this README. Edit the Markdown under `updates/`, and edit `scripts/build_site.py` for the design. Do not hand-edit the generated pages.

## Publish

Serve the `main` branch root with GitHub Pages. No build workflow is required: the HTML in the repository is the site. `.nojekyll` tells Pages to serve the files as they are.

The project URL is `https://arttuahola-beep.github.io/russia-in-10-years/`.
