"""Sweep the PlayOnline FFXI news archive by ID and download every page that exists.

POL news IDs are one shared sequence across all PlayOnline sites; only a subset
resolve under /ff11us/. A 404 means "not an FFXI-US news page". Pages are kept
verbatim (bytes) in data/raw/polnews/. State is tracked in data/sweep_state.json
so reruns only check unseen IDs and previous errors.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = "https://www.playonline.com/ff11us/polnews/news{}.shtml"
INDEX_PAGES = [
    "https://www.playonline.com/ff11us/polnews/news.shtml",
    "https://www.playonline.com/ff11us/info/list_imp.shtml",
    "https://www.playonline.com/ff11us/info/list_mnt.shtml",
    "https://www.playonline.com/ff11us/info/list_gen.shtml",
    "https://www.playonline.com/ff11us/info/list_upd.shtml",
]
NEWS_ID_RE = re.compile(r"/polnews/news(\d+)\.shtml")
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "polnews"
STATE_FILE = ROOT / "data" / "sweep_state.json"

ID_START = 1
ID_END_FLOOR = 27800
ID_MARGIN = 50
WORKERS = 8
TIMEOUT = 25
RETRIES = 3
USER_AGENT = "Mozilla/5.0 (ffxi-updates-archive; personal archival project)"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"found": [], "missing": [], "errors": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["found"] = sorted(set(state["found"]))
    state["missing"] = sorted(set(state["missing"]))
    state["errors"] = sorted(set(state["errors"]))
    STATE_FILE.write_text(json.dumps(state))


def fetch(news_id):
    req = urllib.request.Request(BASE.format(news_id), headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return ("found", resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ("missing", None)
            last_err = e
        except Exception as e:
            last_err = e
        time.sleep(2 * (attempt + 1))
    return ("error", last_err)


def current_id_end():
    seen = [ID_END_FLOOR]
    for url in INDEX_PAGES:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("iso-8859-1", errors="replace")
        except Exception as e:
            print(f"index fetch failed ({url}): {e}", flush=True)
            continue
        seen += [int(m) for m in NEWS_ID_RE.findall(body)]
    return max(seen) + ID_MARGIN


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    id_end = current_id_end()
    print(f"sweeping ids {ID_START}..{id_end}", flush=True)
    done = set(state["found"]) | set(state["missing"])
    todo = [i for i in range(ID_START, id_end + 1) if i not in done]
    todo += [i for i in state["errors"] if i not in done]
    state["errors"] = []
    todo = sorted(set(todo))
    print(f"{len(todo)} ids to check ({len(state['found'])} found so far)", flush=True)

    processed = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch, i): i for i in todo}
        for fut in as_completed(futures):
            news_id = futures[fut]
            status, payload = fut.result()
            if status == "found":
                (RAW_DIR / f"news{news_id}.html").write_bytes(payload)
                state["found"].append(news_id)
            elif status == "missing":
                state["missing"].append(news_id)
            else:
                state["errors"].append(news_id)
                print(f"error news{news_id}: {payload}", flush=True)
            processed += 1
            if processed % 500 == 0:
                save_state(state)
                print(f"{processed}/{len(todo)} checked, {len(state['found'])} found", flush=True)

    save_state(state)
    print(f"done: {len(state['found'])} found, {len(state['missing'])} missing, {len(state['errors'])} errors", flush=True)
    if state["errors"]:
        print("rerun to retry errored ids", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
