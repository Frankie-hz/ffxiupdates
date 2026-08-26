"""Fetch all threads from the SE forum's FFXI Version Updates subforum (forums/84).

Listing pages are crawled until they stop yielding new threads. Each thread is
saved via vBulletin's printthread view (clean, single page, all posts) into
data/raw/forum/. The thread index (id, title) goes to data/forum_threads.json.
Already-downloaded threads are skipped, so reruns only pick up new ones.
"""

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

FORUM_LIST = "https://forum.square-enix.com/ffxi/forums/84-Version-Updates/page{}"
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


def crawl_listing():
    threads = {}
    for page in range(1, MAX_LIST_PAGES + 1):
        body = get(FORUM_LIST.format(page)).decode("utf-8", errors="replace")
        found = THREAD_RE.findall(body)
        new = [t for t in found if int(t[0]) not in threads]
        for tid, title in found:
            threads[int(tid)] = html.unescape(title).strip()
        print(f"listing page {page}: {len(found)} threads, {len(new)} new", flush=True)
        if len(new) == 0:
            break
        time.sleep(0.5)
    return threads


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    threads = crawl_listing()
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(
        [{"id": tid, "title": title} for tid, title in sorted(threads.items())],
        indent=1))
    print(f"{len(threads)} threads indexed", flush=True)

    errors = []
    for tid in sorted(threads):
        out = RAW_DIR / f"thread{tid}.html"
        if out.exists():
            continue
        try:
            out.write_bytes(get(PRINT_THREAD.format(tid)))
            print(f"downloaded thread{tid}: {threads[tid]}", flush=True)
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
