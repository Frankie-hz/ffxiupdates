"""Parse raw polnews pages into data/polnews.jsonl (one JSON object per page:
id, lang, date, category, from, title, body html).

Covers the English site (data/raw/polnews, iso-8859-1) and the Japanese site
(data/raw/polnews_ja, Shift_JIS). Two layouts exist on each: the pre-2006
"headline" layout (font.news_title) and the 2006+ "info" layout
(tx_info1/tx_info2 spans with an infctl0N category banner). Unparseable files
are listed at the end so new layouts can be added.
"""

import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    {"dir": ROOT / "data" / "raw" / "polnews", "lang": "en"},
    {"dir": ROOT / "data" / "raw" / "polnews_ja", "lang": "ja"},
]
OUT_FILE = ROOT / "data" / "polnews.jsonl"

CHARSET_RE = re.compile(rb'charset=["\']?([-\w]+)', re.IGNORECASE)
CHARSET_ALIASES = {"x-sjis": "cp932", "shift_jis": "cp932", "shift-jis": "cp932"}

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
NEW_META_JA_RE = re.compile(
    r'class="tx_info2">\s*(\d{4})[./](\d{1,2})[./](\d{1,2})\s*[（(][^）)]*[）)]?\s*'
    r'(\d{1,2}:\d{2})\s*From:\s*([^<]+)</span>')
NEW_CTL_RE = re.compile(r'imgs/info/infctl(\d+)\.gif"[^>]*alt="([^"]*)"')
NEW_SPAN_RE = re.compile(r'<span class="tx_info1">(.*?)</span>\s*</td>', re.DOTALL)

OLD_META_RE = re.compile(
    r'From:\s*([^<]+?)<br>\s*([^<\[]+?)\s*\[(\w+)\]')
OLD_META_JA_RE = re.compile(
    r'From:\s*([^<]+?)<br>\s*(\d{4})[/.](\d{1,2})[/.](\d{1,2})'
    r'(?:\s*[（(][^）)]*[）)])?\s*(\d{1,2}:\d{2})')

# Earliest JA layout (~2002-2005): headline_txt banner, date above "From:",
# title in td.tx12bold, body in td.tx12g.
HEADLINE_JA_META_RE = re.compile(
    r'class="tx10"[^>]*>\s*(\d{4})[./](\d{1,2})[./](\d{1,2})\s*'
    r'(?:[（(][^）)]*[）)])?\s*(\d{1,2}:\d{2})<br>\s*From:\s*([^<]+)</td>')
HEADLINE_JA_CAT_RE = re.compile(r'imgs/news/headline_txt_?(\d+)[a-z]?(?:_(\d+))?[^"]*"[^>]*alt="([^"]*)"')
HEADLINE_JA_TITLE_RE = re.compile(r'class="tx12bold"[^>]*>(.*?)</td>', re.DOTALL)
HEADLINE_JA_BODY_RE = re.compile(r'class="tx12g">(.*?)</td>', re.DOTALL)

JA_ALT_CATEGORY = {
    "アップデート情報": "Updates",
    "重要なお知らせ": "Important Notices",
    "メンテナンス情報": "Maintenance",
    "サーバーメンテナンス情報": "Maintenance",
    "障害情報": "Status",
    "復旧情報": "Status",
    "イベント情報": "Events",
    "インフォメーション": "General",
    "その他のお知らせ": "General",
}
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


def new_layout_meta(text, lang):
    if lang == "ja":
        meta = NEW_META_JA_RE.search(text)
        if meta is None:
            return None
        date = (f"{meta.group(1)}-{int(meta.group(2)):02d}-{int(meta.group(3)):02d} "
                f"{int(meta.group(4).split(':')[0]):02d}:{meta.group(4).split(':')[1]}")
        return {"date": date, "tz": "JST", "from": meta.group(5).strip()}
    meta = NEW_META_RE.search(text)
    if meta is None:
        return None
    date = parse_date(meta.group(1))
    if date is None:
        return None
    return {"date": date, "tz": meta.group(2), "from": meta.group(3).strip()}


def parse_new_layout(text, lang):
    meta = new_layout_meta(text, lang)
    if meta is None:
        return None
    spans = NEW_SPAN_RE.findall(text)
    if len(spans) < 2:
        return None
    category = ""
    ctl = NEW_CTL_RE.search(text)
    if ctl:
        category = CATEGORY_BY_NUM.get(ctl.group(1)) or ctl.group(2).strip()
    meta.update({
        "category": category,
        "title": clean_title(spans[0]),
        "body": spans[1].strip(),
    })
    return meta


def old_layout_meta(text, lang):
    if lang == "ja":
        meta = OLD_META_JA_RE.search(text)
        if meta is None:
            return None
        date = (f"{meta.group(2)}-{int(meta.group(3)):02d}-{int(meta.group(4)):02d} "
                f"{int(meta.group(5).split(':')[0]):02d}:{meta.group(5).split(':')[1]}")
        return {"date": date, "tz": "JST", "from": meta.group(1).strip()}
    meta = OLD_META_RE.search(text)
    if meta is None:
        return None
    date = parse_date(meta.group(2))
    if date is None:
        return None
    return {"date": date, "tz": meta.group(3), "from": meta.group(1).strip()}


def parse_old_layout(text, lang):
    meta = old_layout_meta(text, lang)
    title = OLD_TITLE_RE.search(text)
    body = OLD_BODY_RE.search(text)
    if meta is None or title is None or body is None:
        return None
    category = ""
    cat = OLD_CAT_RE.search(text)
    if cat:
        category = cat.group(1).strip()
    meta.update({
        "category": category,
        "title": clean_title(title.group(1)),
        "body": body.group(1).strip(),
    })
    return meta


def parse_headline_ja_layout(text):
    meta = HEADLINE_JA_META_RE.search(text)
    title = HEADLINE_JA_TITLE_RE.search(text)
    body = HEADLINE_JA_BODY_RE.search(text)
    if meta is None or title is None or body is None:
        return None
    date = (f"{meta.group(1)}-{int(meta.group(2)):02d}-{int(meta.group(3)):02d} "
            f"{int(meta.group(4).split(':')[0]):02d}:{meta.group(4).split(':')[1]}")
    category = ""
    cat = HEADLINE_JA_CAT_RE.search(text)
    if cat:
        alt = cat.group(3).strip()
        number = cat.group(1) + (cat.group(2) or "")
        category = JA_ALT_CATEGORY.get(alt) or CATEGORY_BY_NUM.get(number) \
            or CATEGORY_BY_NUM.get(cat.group(1)) or alt
    return {
        "date": date,
        "tz": "JST",
        "from": meta.group(5).strip(),
        "category": category,
        "title": clean_title(title.group(1)),
        "body": body.group(1).strip(),
    }


def decode_page(raw, lang):
    if lang == "en":
        return raw.decode("iso-8859-1", errors="replace")
    m = CHARSET_RE.search(raw)
    if m:
        declared = m.group(1).decode("ascii", errors="replace").lower()
        enc = CHARSET_ALIASES.get(declared, declared)
        try:
            return raw.decode(enc, errors="replace")
        except LookupError:
            pass
    for enc in ("cp932", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp932", errors="replace")


def main():
    entries = []
    for source in SOURCES:
        if source["dir"].exists() is False:
            continue
        lang = source["lang"]
        failed = []
        count = 0
        for path in sorted(source["dir"].glob("news*.html"), key=lambda p: int(p.stem[4:])):
            news_id = int(path.stem[4:])
            text = decode_page(path.read_bytes(), lang)
            parsed = parse_new_layout(text, lang)
            if parsed is None:
                parsed = parse_old_layout(text, lang)
            if parsed is None and lang == "ja":
                parsed = parse_headline_ja_layout(text)
            if parsed is None:
                failed.append(news_id)
                continue
            parsed["id"] = news_id
            parsed["lang"] = lang
            entries.append(parsed)
            count += 1
        print(f"{lang}: parsed {count} pages, {len(failed)} failed")
        if failed:
            print(f"{lang} failed ids:", failed[:50], "..." if len(failed) > 50 else "")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
