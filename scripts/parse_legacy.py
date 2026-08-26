"""Parse mirrored legacy pages into data/legacy.jsonl.

Legacy pages span several site layouts (comnews 2002-2003, comnewsus/updateus
2003-2005, pcd/update 2005-2007), so instead of extracting article bodies they
are kept as full documents to be shown in an iframe; src/href attributes are
rewritten to absolute playonline.com URLs so styling and images resolve.
Dates are inferred from the URL naming schemes.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "legacy"
POLNEWS_FILE = ROOT / "data" / "polnews.jsonl"
OUT_FILE = ROOT / "data" / "legacy.jsonl"
HOST = "https://www.playonline.com"

PCD_LINK_RE = re.compile(r'https?://www\.playonline\.com(/pcd/(?:update|topics)/[^"\'<>\s]+?\.html)')

CHARSET_RE = re.compile(rb'charset=["\']?([-\w]+)', re.IGNORECASE)
CHARSET_ALIASES = {"x-sjis": "cp932", "shift_jis": "cp932", "shift-jis": "cp932", "euc-jp": "euc_jp"}
META_CHARSET_SUB = re.compile(r'(charset=["\']?)([-\w]+)', re.IGNORECASE)

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
TOPICS_TITLE_RE = re.compile(
    r'<div id="title">(.*?)(?:&nbsp;|\s)*\((\d{1,2})/(\d{1,2})/(\d{4})\)\s*</div>', re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
ATTR_RE = re.compile(r'((?:src|href|background)=")([^"]+)(")', re.IGNORECASE)

DATE_PATTERNS = [
    re.compile(r"/(20\d{6})"),          # 20060418..., 200404226037 (first 8 digits)
    re.compile(r"verup(20\d{6})"),
    re.compile(r"/(\d{6})[a-z]"),       # 050421er1gb1, 040629fg5rh3, 020912detail
    re.compile(r"/(\d{6})detail"),
]


def infer_date(url_path):
    for pat in DATE_PATTERNS:
        m = pat.search(url_path)
        if m is None:
            continue
        digits = m.group(1)
        if len(digits) >= 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return f"20{digits[:2]}-{digits[2:4]}-{digits[4:6]}"
    return None


def decode_page(raw):
    m = CHARSET_RE.search(raw)
    if m:
        declared = m.group(1).decode("ascii", errors="replace").lower()
        enc = CHARSET_ALIASES.get(declared, declared)
        try:
            return raw.decode(enc, errors="replace")
        except LookupError:
            pass
    for enc in ("utf-8", "cp932", "iso-8859-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def absolutize(html_text, page_dir):
    def fix(m):
        url = m.group(2)
        if url.startswith(("http:", "https:", "mailto:", "javascript:", "#")):
            return m.group(0)
        if url.startswith("/"):
            return m.group(1) + HOST + url + m.group(3)
        return m.group(1) + HOST + page_dir + "/" + url + m.group(3)
    return ATTR_RE.sub(fix, html_text)


def polnews_link_map():
    linked = {}
    if POLNEWS_FILE.exists() is False:
        return linked
    for line in POLNEWS_FILE.read_text(encoding="utf-8").split("\n"):
        if line == "":
            continue
        e = json.loads(line)
        for target in PCD_LINK_RE.findall(e["body"]):
            linked.setdefault(target, (e["date"][:10], e["title"]))
    return linked


def main():
    link_map = polnews_link_map()
    entries = []
    seen = set()
    for path in sorted(RAW_DIR.rglob("*.html")):
        url_path = "/" + path.relative_to(RAW_DIR).as_posix()
        canonical = url_path.replace("/pcd/topics/", "/pcd2/topics/")
        if canonical in seen:
            continue
        seen.add(canonical)
        text = decode_page(path.read_bytes())
        text = META_CHARSET_SUB.sub(r"\1utf-8", text)

        date = infer_date(url_path)
        title = ""
        topics = TOPICS_TITLE_RE.search(text)
        if topics:
            title = html.unescape(re.sub(r"\s+", " ", TAG_RE.sub("", topics.group(1))).strip())
            month = int(topics.group(2))
            day = int(topics.group(3))
            date = date or f"{topics.group(4)}-{month:02d}-{day:02d}"
        linked_title = None
        if date is None and canonical in link_map:
            date, linked_title = link_map[canonical]
        if date is None:
            print(f"skip (no date): {url_path}")
            continue
        if title == "":
            m = TITLE_RE.search(text)
            if m:
                title = html.unescape(re.sub(r"\s+", " ", TAG_RE.sub("", m.group(1))).strip())
        if title in ("", "FINAL FANTASY XI", "PlayOnline.com",
                     "FINAL FANTASY XI Official Web Site"):
            title = linked_title or f"Update details ({date})"
        entries.append({
            "path": url_path,
            "url": HOST + url_path,
            "date": date,
            "title": title,
            "doc": absolutize(text, str(Path(url_path).parent).replace("\\", "/")),
        })

    with OUT_FILE.open("w", encoding="utf-8") as f:
        for e in sorted(entries, key=lambda e: e["date"]):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"parsed {len(entries)} legacy pages")


if __name__ == "__main__":
    main()
