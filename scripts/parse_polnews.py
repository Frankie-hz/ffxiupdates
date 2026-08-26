"""Parse raw polnews pages into data/polnews.jsonl (one JSON object per page:
id, date, category, from, title, body html).

Two layouts exist: the pre-2006 "headline" layout (font.news_title) and the
2006+ "info" layout (tx_info1/tx_info2 spans with an infctl0N category banner).
Unparseable files are listed at the end so new layouts can be added.
"""

import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "polnews"
OUT_FILE = ROOT / "data" / "polnews.jsonl"

# The infctl banner number is authoritative; its alt text is often a stale
# template value (e.g. infctl03 pages carry alt="Updates").
CATEGORY_BY_NUM = {
    "01": "Important Notices",
    "02": "Maintenance",
    "021": "Status",
    "022": "Maintenance",
    "03": "General",
    "04": "Events",
    "05": "Updates",
}

NEW_META_RE = re.compile(
    r'class="tx_info2">([^<]+?)\s*\[(\w+)\]\s*From:\s*([^<]+)</span>')
NEW_CTL_RE = re.compile(r'imgs/info/infctl(\d+)\.gif"[^>]*alt="([^"]*)"')
NEW_SPAN_RE = re.compile(r'<span class="tx_info1">(.*?)</span>\s*</td>', re.DOTALL)

OLD_META_RE = re.compile(
    r'From:\s*([^<]+?)<br>\s*([^<\[]+?)\s*\[(\w+)\]')
OLD_CAT_RE = re.compile(r'imgs/news/headline_txt[^"]*"[^>]*alt="([^"]+)"')
OLD_TITLE_RE = re.compile(r'<font class="news_title">(.*?)</font>', re.DOTALL)
OLD_BODY_RE = re.compile(
    r'<font class="news_title">.*?</font><br>\s*(?:<br>\s*)?(.*?)\s*</td>', re.DOTALL)

TAG_RE = re.compile(r"<[^>]+>")


def parse_date(text):
    text = text.strip().rstrip(",")
    for fmt in ("%b. %d, %Y %H:%M", "%b %d, %Y %H:%M", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    text = text.replace("May.", "May").replace("Sept.", "Sep.")
    for fmt in ("%b. %d, %Y %H:%M", "%b %d, %Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    return None


def clean_title(raw):
    return html.unescape(TAG_RE.sub("", raw)).strip()


def parse_new_layout(text):
    meta = NEW_META_RE.search(text)
    if meta is None:
        return None
    spans = NEW_SPAN_RE.findall(text)
    if len(spans) < 2:
        return None
    category = ""
    ctl = NEW_CTL_RE.search(text)
    if ctl:
        category = CATEGORY_BY_NUM.get(ctl.group(1)) or ctl.group(2).strip()
    date = parse_date(meta.group(1))
    if date is None:
        return None
    return {
        "date": date,
        "tz": meta.group(2),
        "from": meta.group(3).strip(),
        "category": category,
        "title": clean_title(spans[0]),
        "body": spans[1].strip(),
    }


def parse_old_layout(text):
    meta = OLD_META_RE.search(text)
    title = OLD_TITLE_RE.search(text)
    body = OLD_BODY_RE.search(text)
    if meta is None or title is None or body is None:
        return None
    date = parse_date(meta.group(2))
    if date is None:
        return None
    category = ""
    cat = OLD_CAT_RE.search(text)
    if cat:
        category = cat.group(1).strip()
    return {
        "date": date,
        "tz": meta.group(3),
        "from": meta.group(1).strip(),
        "category": category,
        "title": clean_title(title.group(1)),
        "body": body.group(1).strip(),
    }


def main():
    entries = []
    failed = []
    for path in sorted(RAW_DIR.glob("news*.html"), key=lambda p: int(p.stem[4:])):
        news_id = int(path.stem[4:])
        text = path.read_text(encoding="iso-8859-1", errors="replace")
        parsed = parse_new_layout(text)
        if parsed is None:
            parsed = parse_old_layout(text)
        if parsed is None:
            failed.append(news_id)
            continue
        parsed["id"] = news_id
        entries.append(parsed)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"parsed {len(entries)} pages, {len(failed)} failed")
    if failed:
        print("failed ids:", failed[:50], "..." if len(failed) > 50 else "")


if __name__ == "__main__":
    main()
