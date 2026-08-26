# FFXI Updates Combined

Combined, searchable archive of every official FINAL FANTASY XI update and news
page, 2002 to present. Existing update lists were built from wiki catalogs and
missed any page the wikis never recorded (for example
[news12126](https://www.playonline.com/ff11us/polnews/news12126.shtml), the
Nov. 28, 2007 client update). This project instead enumerates the primary
sources directly, so nothing depends on third-party cataloging:

| Source | Coverage | Method |
| --- | --- | --- |
| playonline.com/ff11us/polnews | 2003-present, all categories (EN) | brute-force sweep of every news id |
| playonline.com/ff11/polnews | 2002-present, all categories (JA) | brute-force sweep of every news id |
| playonline.com/pcd2/topics | 2007-2010 version update detail articles | brute-force sweep of every topics id |
| forum.square-enix.com/ffxi forums/84 | 2011-present version updates (EN) | crawl of the Version Updates subforum |
| forum.square-enix.com/ffxi forums/15 | 2011-present version updates (JA source text) | crawl of the JA Version Updates subforum |
| playonline.com comnews/updateus/pcd | 2002-2007 update details | curated list plus pages linked from polnews |

The output is a single self-contained page, `docs/index.html`, with full-text
search, category/year/source filters, and links back to every original page.

## Pipeline

```
python scripts/sweep_polnews.py   # download every /ff11us/polnews/newsN.shtml that exists
python scripts/sweep_polnews.py ja  # same for the Japanese site, /ff11/polnews/
python scripts/sweep_topics.py   # download every /pcd2/topics/ff11us/detail/N/ that exists
python scripts/fetch_forum.py    # download all Version Updates forum threads (printable view)
python scripts/fetch_legacy.py   # download legacy pages + pcd pages linked from polnews
python scripts/parse_polnews.py  # raw pages -> data/polnews.jsonl
python scripts/parse_forum.py    # raw threads -> data/forum.jsonl
python scripts/parse_legacy.py   # raw legacy -> data/legacy.jsonl
python scripts/combine.py        # normalize everything -> data/all.jsonl
python scripts/build.py          # data/all.jsonl -> docs/index.html
```

Or run everything at once with `python scripts/update_all.py`.

Python 3 standard library only. Every step is incremental: sweep state lives in
`data/sweep_state.json` and `data/topics_state.json`, already-downloaded files
are skipped, so rerunning the whole pipeline just picks up new pages. The
polnews sweep reads the live index pages to find the current highest news id.

`data/*.jsonl` hold the full parsed content (including body HTML) and are the
archival record; `data/raw/` is the verbatim mirror and is not committed.

## Data schema

`data/all.jsonl` is the normalized dataset intended for consumers - one JSON
record per line, one schema across every source. The per-source files
(`polnews.jsonl`, `forum.jsonl`, `legacy.jsonl`) are intermediate outputs and
may change shape; consume `all.jsonl`.

```
id           unique across sources, e.g. "forum-49064", "polnews-12126"
source       "polnews" | "forum" | "legacy" | "topics"
url          the original page (cite this)
date         ISO date, always present. Version-update forum threads are dated
             by the patch date in their title, not the posting date.
time         "HH:MM", optional
tz           timezone label, optional (polnews only)
lang         "en" | "ja"
from         announcement sender, optional (polnews only)
category     see below
title        plain text
body         HTML
translation  optional {title, body}: machine translation of ja legacy pages
```

Categories: polnews records carry PlayOnline's own categories (`Updates`,
`Maintenance`, `Status`, `General`, `Important Notices`, `Events`); forum
records are `Version Update` or `Forum Info`; legacy/topics records are
`Update Details`. To filter to the update stream only, keep categories in
{`Updates`, `Version Update`, `Update Details`}.

Pin a tagged release if you consume the data programmatically; the schema only
changes between tags.

The eleven 2002-2003 pages that only exist in Japanese (they predate the North
American release) carry machine translations in `data/translations/`, shown
above the original page with a clear machine-translation notice and included
in full-text search.

## Viewing

Open `docs/index.html` in a browser, or serve the `docs/` directory (GitHub
Pages works as-is).

## License

The code and tooling in this repository are released under the MIT License
(see `LICENSE`). The archived update notes, images, and other page content
remain the property of Square Enix and are preserved here for reference and
historical purposes; the license does not apply to them.

## Credits

The seed list of 2002-2007 legacy page URLs in `data/legacy_links.txt` was
compiled from the link list in
[InoUno/ffxi-updates-combined](https://github.com/InoUno/ffxi-updates-combined).
Everything else (discovery, download, parsing, and the combined page) is
original to this project.
