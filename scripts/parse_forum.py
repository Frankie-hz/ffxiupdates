"""Parse downloaded forum printthread pages into data/forum.jsonl
(one JSON object per thread: id, title, date, lang, body html).

Multi-post threads (the monthly version updates) are flattened into one body
with each post's title as a section heading. Session ids are stripped from
forum links so archived pages don't carry stale state.
"""

import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "forum"
INDEX_FILE = ROOT / "data" / "forum_threads.json"
OUT_FILE = ROOT / "data" / "forum.jsonl"

POST_RE = re.compile(
    r'<li class="postbit blockbody" id="post_\d+">\s*<div class="header">\s*'
    r'<div class="datetime">([^<]+)</div>.*?'
    r'(?:<div class="title">(.*?)</div>\s*)?'
    r'<div class="content">\s*<blockquote class="restore">(.*?)</blockquote>\s*</div>\s*</li>',
    re.DOTALL)
SESSION_RE = re.compile(r'([?&])s=[0-9a-f]{32}(?:&amp;|&)?')

# SE posts raw HTML (tables etc.) that the printthread view escapes; unescape
# spans that are clearly escaped tags so they render. iframe/script stay inert.
ESCAPED_TAG_RE = re.compile(
    r'&lt;(/?)(table|tbody|thead|tr|td|th|caption|br|hr|a|font|div|span|p'
    r'|strong|b|i|u|em|center|ul|ol|li|img|h[1-6])'
    r'((?:(?!&[lg]t;).)*?)&gt;',
    re.IGNORECASE | re.DOTALL)


def parse_datetime(text):
    text = text.strip()
    for fmt in ("%m-%d-%Y, %I:%M %p", "%Y-%m-%d, %H:%M", "%m-%d-%Y, %H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})\D+(\d{1,2}):(\d{2})", text)
    if m:
        return (f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} "
                f"{int(m.group(4)):02d}:{m.group(5)}")
    return None


ATTACH_LINK_RE = re.compile(
    r'<a\s[^>]*attachment\.php\?(?:[^"\'>]*?)?attachmentid=(\d+)[^>]*>.*?</a>',
    re.DOTALL | re.IGNORECASE)


def load_attachment_manifest():
    manifest_path = ROOT / "data" / "attachments.json"
    if manifest_path.exists() is False:
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


ATTACHMENTS = load_attachment_manifest()


def inline_attachment(m):
    name = ATTACHMENTS.get(m.group(1))
    if name is None:
        return m.group(0)
    return f'<img class="att" src="attachments/{name}" loading="lazy" alt="Attachment {m.group(1)}">'


def clean(body):
    body = SESSION_RE.sub(r"\1", body)
    body = ESCAPED_TAG_RE.sub(lambda m: html.unescape(m.group(0)), body)
    body = ATTACH_LINK_RE.sub(inline_attachment, body)
    return body.replace("?#", "#").strip()


def main():
    threads = {}
    for t in json.loads(INDEX_FILE.read_text(encoding="utf-8")):
        threads[t["id"]] = {"title": t["title"], "lang": t.get("lang", "en")}
    entries = []
    failed = []
    for path in sorted(RAW_DIR.glob("thread*.html"), key=lambda p: int(p.stem[6:])):
        tid = int(path.stem[6:])
        text = path.read_text(encoding="utf-8", errors="replace")
        posts = POST_RE.findall(text)
        if len(posts) == 0:
            failed.append(tid)
            continue
        date = parse_datetime(posts[0][0])
        if date is None:
            failed.append(tid)
            continue
        info = threads.get(tid, {"title": f"Thread {tid}", "lang": "en"})
        sections = []
        for _, post_title, content in posts:
            post_title = html.unescape(post_title).strip()
            if post_title and post_title != info["title"]:
                sections.append(f"<h3>{post_title}</h3>")
            sections.append(clean(content))
        entries.append({
            "id": tid,
            "date": date,
            "lang": info["lang"],
            "title": info["title"],
            "body": "\n".join(sections),
        })

    with OUT_FILE.open("w", encoding="utf-8") as f:
        for e in sorted(entries, key=lambda e: e["date"]):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"parsed {len(entries)} threads, {len(failed)} failed")
    if failed:
        print("failed ids:", failed)


if __name__ == "__main__":
    main()
