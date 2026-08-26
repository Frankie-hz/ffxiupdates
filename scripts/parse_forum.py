"""Parse downloaded forum printthread pages into data/forum.jsonl
(one JSON object per thread: id, title, date, body html).

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


def parse_datetime(text):
    text = text.strip()
    try:
        return datetime.strptime(text, "%m-%d-%Y, %I:%M %p").strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


def clean(body):
    body = SESSION_RE.sub(r"\1", body)
    return body.replace("?#", "#").strip()


def main():
    threads = {t["id"]: t["title"] for t in json.loads(INDEX_FILE.read_text())}
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
        sections = []
        for _, post_title, content in posts:
            post_title = html.unescape(post_title).strip()
            if post_title and post_title != threads.get(tid, ""):
                sections.append(f"<h3>{post_title}</h3>")
            sections.append(clean(content))
        entries.append({
            "id": tid,
            "date": date,
            "title": threads.get(tid, f"Thread {tid}"),
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
