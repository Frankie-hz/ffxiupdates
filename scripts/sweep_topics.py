"""Sweep the pcd2/topics FFXI detail pages by id (the 2007-2010 era feature and
version-update detail articles, e.g. "The Version Update Has Arrived!").

Like the polnews ids, topics ids are one sequence shared across PlayOnline;
404 means "not an FFXI-US topics page". Found pages land in the legacy mirror
tree (data/raw/legacy/pcd2/...) so parse_legacy picks them up. State lives in
data/topics_state.json.
"""

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fetch_legacy import download, fetch_assets

ROOT = Path(__file__).resolve().parent.parent
RAW_LEGACY = ROOT / "data" / "raw" / "legacy"
STATE_FILE = ROOT / "data" / "topics_state.json"

PATH_TEMPLATE = "/pcd2/topics/ff11us/detail/{}/detail.html"
BASE = "https://www.playonline.com" + PATH_TEMPLATE
ID_START = 1
ID_END = 9999
WORKERS = 8
TIMEOUT = 25
RETRIES = 3
USER_AGENT = "Mozilla/5.0 (ffxi-updates-archive; personal archival project)"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"found": [], "missing": [], "errors": []}


def save_state(state):
    state["found"] = sorted(set(state["found"]))
    state["missing"] = sorted(set(state["missing"]))
    state["errors"] = sorted(set(state["errors"]))
    STATE_FILE.write_text(json.dumps(state))


def probe(topic_id):
    req = urllib.request.Request(BASE.format(topic_id), headers={"User-Agent": USER_AGENT})
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


def main():
    state = load_state()
    done = set(state["found"]) | set(state["missing"])
    todo = sorted(set(i for i in range(ID_START, ID_END + 1) if i not in done)
                  | set(state["errors"]))
    state["errors"] = []
    print(f"{len(todo)} topic ids to check ({len(state['found'])} found so far)", flush=True)

    processed = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(probe, i): i for i in todo}
        for fut in as_completed(futures):
            topic_id = futures[fut]
            status, payload = fut.result()
            if status == "found":
                path = PATH_TEMPLATE.format(topic_id)
                dest = RAW_LEGACY / path.lstrip("/")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(payload)
                state["found"].append(topic_id)
                print(f"found topic {topic_id}", flush=True)
            elif status == "missing":
                state["missing"].append(topic_id)
            else:
                state["errors"].append(topic_id)
                print(f"error topic {topic_id}: {payload}", flush=True)
            processed += 1
            if processed % 500 == 0:
                save_state(state)
                print(f"{processed}/{len(todo)} checked", flush=True)
    save_state(state)

    asset_errors = []
    for topic_id in state["found"]:
        path = PATH_TEMPLATE.format(topic_id)
        body = (RAW_LEGACY / path.lstrip("/")).read_bytes()
        fetch_assets(path, body, asset_errors)
    print(f"done: {len(state['found'])} found, {len(state['errors'])} errors, "
          f"{len(asset_errors)} asset errors", flush=True)


if __name__ == "__main__":
    main()
