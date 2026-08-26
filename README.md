# FFXI Updates Combined

Combined, searchable archive of every official FINAL FANTASY XI update and news
page, 2002 to present. Existing update lists were built from wiki catalogs and
missed any page the wikis never recorded (for example
[news12126](https://www.playonline.com/ff11us/polnews/news12126.shtml), the
Nov. 28, 2007 client update). This project instead enumerates the primary
sources directly, so nothing depends on third-party cataloging:

| Source | Coverage | Method |
| --- | --- | --- |
| playonline.com/ff11us/polnews | 2003-present, all categories | brute-force sweep of every news id |
| playonline.com/pcd2/topics | 2007-2010 version update detail articles | brute-force sweep of every topics id |
| forum.square-enix.com/ffxi forums/84 | 2011-present version updates | crawl of the Version Updates subforum |
| playonline.com comnews/updateus/pcd | 2002-2007 update details | curated list plus pages linked from polnews |

The output is a single self-contained page, `docs/index.html`, with full-text
search, category/year/source filters, and links back to every original page.

## Pipeline

```
python scripts/sweep_polnews.py   # download every /ff11us/polnews/newsN.shtml that exists
python scripts/sweep_topics.py   # download every /pcd2/topics/ff11us/detail/N/ that exists
python scripts/fetch_forum.py    # download all Version Updates forum threads (printable view)
python scripts/fetch_legacy.py   # download legacy pages + pcd pages linked from polnews
python scripts/parse_polnews.py  # raw pages -> data/polnews.jsonl
python scripts/parse_forum.py    # raw threads -> data/forum.jsonl
python scripts/parse_legacy.py   # raw legacy -> data/legacy.jsonl
python scripts/build.py          # -> docs/index.html
```

Or run everything at once with `python scripts/update_all.py`.

Python 3 standard library only. Every step is incremental: sweep state lives in
`data/sweep_state.json` and `data/topics_state.json`, already-downloaded files
are skipped, so rerunning the whole pipeline just picks up new pages. The
polnews sweep reads the live index pages to find the current highest news id.

`data/*.jsonl` hold the full parsed content (including body HTML) and are the
archival record; `data/raw/` is the verbatim mirror and is not committed.

## Viewing

Open `docs/index.html` in a browser, or serve the `docs/` directory (GitHub
Pages works as-is).

## Credits

The seed list of 2002-2007 legacy page URLs in `data/legacy_links.txt` was
compiled from the link list in
[InoUno/ffxi-updates-combined](https://github.com/InoUno/ffxi-updates-combined).
Everything else (discovery, download, parsing, and the combined page) is
original to this project.
