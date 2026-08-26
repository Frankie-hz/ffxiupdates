"""Fetch all threads from the SE forum's FFXI Version Updates subforums:
forums/84 (English) and forums/15 (Japanese source text).

Listing pages are crawled until they stop yielding new threads. Each thread is
saved via vBulletin's printthread view (clean, single page, all posts) into
data/raw/forum/. The thread index (id, title, lang) goes to
data/forum_threads.json. Already-downloaded threads are skipped, so reruns
only pick up new ones.
"""

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

FORUMS = [
    {"id": 84, "lang": "en"},
    {"id": 15, "lang": "ja"},
]
FORUM_LIST = "https://forum.square-enix.com/ffxi/forums/{}/page{}"
PRINT_THREAD = "https://forum.square-enix.com/ffxi/printthread.php?t={}&pp=100"
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "forum"
INDEX_FILE = ROOT / "data" / "forum_threads.json"

MAX_LIST_PAGES = 40
USER_AGENT = "Mozilla/5.0 (ffxi-updates-archive; personal archival project)"
THREAD_RE = re.compile(r'class="title" href="threads/(\d+)-[^"?]*[^"]*" id="thread_title_\d+">([^<]+)')


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def crawl_listing(forum_id, lang):
    threads = {}
    for page in range(1, MAX_LIST_PAGES + 1):
        body = get(FORUM_LIST.format(forum_id, page)).decode("utf-8", errors="replace")
        found = THREAD_RE.findall(body)
        new = [t for t in found if int(t[0]) not in threads]
        for tid, title in found:
            threads[int(tid)] = {"title": html.unescape(title).strip(), "lang": lang}
        print(f"forum {forum_id} page {page}: {len(found)} threads, {len(new)} new", flush=True)
        if len(new) == 0:
            break
        time.sleep(0.5)
    return threads


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    threads = {}
    for forum in FORUMS:
        threads.update(crawl_listing(forum["id"], forum["lang"]))
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(
        [{"id": tid, "title": t["title"], "lang": t["lang"]}
         for tid, t in sorted(threads.items())],
        indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(threads)} threads indexed", flush=True)

    errors = []
    for tid in sorted(threads):
        out = RAW_DIR / f"thread{tid}.html"
        if out.exists():
            continue
        try:
            out.write_bytes(get(PRINT_THREAD.format(tid)))
            print(f"downloaded thread{tid}: {threads[tid]['title']}", flush=True)
            time.sleep(0.5)
        except Exception as e:
            errors.append(tid)
            print(f"error thread{tid}: {e}", flush=True)

    if errors:
        print(f"{len(errors)} errors, rerun to retry", flush=True)
        sys.exit(1)
    print("done", flush=True)


if __name__ == "__main__":
    main()
