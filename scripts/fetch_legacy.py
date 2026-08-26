"""Fetch legacy playonline.com update pages plus any pcd/update or pcd/topics
detail pages that the polnews sweep pages link to.

Pages are mirrored under data/raw/legacy/<url path>. Same-directory assets
(images) referenced by each page are mirrored next to it, and site-absolute
assets (stylesheets, shared images) are mirrored at their site paths.
Existing files are skipped so reruns are incremental.
"""

import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_POLNEWS = ROOT / "data" / "raw" / "polnews"
RAW_LEGACY = ROOT / "data" / "raw" / "legacy"
LINKS_FILE = ROOT / "data" / "legacy_links.txt"

USER_AGENT = "Mozilla/5.0 (ffxi-updates-archive; personal archival project)"
HOST = "https://www.playonline.com"

PCD_LINK_RE = re.compile(r'https?://www\.playonline\.com(/pcd/(?:update|topics)/[^"\'<>\s]+?\.html)')
ASSET_RE = re.compile(r'(?:src|href)="([^"]+?\.(?:jpg|jpeg|gif|png|css))"', re.IGNORECASE)


def local_path(url_path):
    return RAW_LEGACY / url_path.lstrip("/")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def download(url_path, errors):
    dest = local_path(url_path)
    if dest.exists():
        return dest.read_bytes()
    try:
        body = get(HOST + url_path)
    except Exception as e:
        errors.append(url_path)
        print(f"error {url_path}: {e}", flush=True)
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    print(f"downloaded {url_path}", flush=True)
    time.sleep(0.3)
    return body


def collect_page_paths():
    paths = []
    for line in LINKS_FILE.read_text().splitlines():
        line = line.strip()
        if line and (line.startswith("#") is False):
            paths.append(urllib.parse.urlparse(line).path)
    linked = set()
    for page in sorted(RAW_POLNEWS.glob("news*.html")):
        text = page.read_text(encoding="iso-8859-1", errors="replace")
        for target in PCD_LINK_RE.findall(text):
            linked.add(target.replace("/pcd/topics/", "/pcd2/topics/"))
    print(f"{len(paths)} curated pages, {len(linked)} pcd pages linked from polnews", flush=True)
    return sorted(set(paths) | linked)


def fetch_assets(page_path, body, errors):
    page_dir = str(Path(page_path).parent).replace("\\", "/")
    text = body.decode("utf-8", errors="replace")
    for ref in set(ASSET_RE.findall(text)):
        if ref.startswith(("http:", "https:", "//")):
            continue
        if ref.startswith("/"):
            asset_path = ref
        else:
            asset_path = urllib.parse.urljoin(page_dir + "/", ref)
        download(asset_path, errors)


def main():
    RAW_LEGACY.mkdir(parents=True, exist_ok=True)
    errors = []
    for page_path in collect_page_paths():
        body = download(page_path, errors)
        if body is not None:
            fetch_assets(page_path, body, errors)
    print(f"done, {len(errors)} errors", flush=True)


if __name__ == "__main__":
    main()
