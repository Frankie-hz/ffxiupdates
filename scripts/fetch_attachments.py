"""Download every forum attachment referenced by the raw thread pages in
data/raw/forum/ into docs/attachments/ so images render inline instead of
linking back to the forum.

Writes data/attachments.json manifest {attachment_id: filename}. Extension is
sniffed from magic bytes. Already-downloaded ids are skipped on rerun.
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_FORUM_DIR = ROOT / "data" / "raw" / "forum"
OUT_DIR = ROOT / "docs" / "attachments"
MANIFEST = ROOT / "data" / "attachments.json"

URL = "https://forum.square-enix.com/ffxi/attachment.php?attachmentid={}"
USER_AGENT = "Mozilla/5.0 (ffxi-updates-archive; personal archival project)"
ATTACH_RE = re.compile(r"attachment\.php\?attachmentid=(\d+)")

MAGIC = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG", "png"),
    (b"GIF8", "gif"),
    (b"RIFF", "webp"),
    (b"%PDF", "pdf"),
]


def sniff_ext(data):
    for magic, ext in MAGIC:
        if data.startswith(magic):
            return ext
    return None


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ids = set()
    for page in RAW_FORUM_DIR.glob("thread*.html"):
        text = page.read_text(encoding="utf-8", errors="replace")
        ids.update(int(m) for m in ATTACH_RE.findall(text))
    manifest = {}
    if MANIFEST.exists():
        manifest = {int(k): v for k, v in json.loads(MANIFEST.read_text()).items()}
    todo = sorted(i for i in ids if i not in manifest)
    print(f"{len(ids)} attachments referenced, {len(todo)} to download", flush=True)

    errors = 0
    for n, att_id in enumerate(todo):
        req = urllib.request.Request(URL.format(att_id), headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            ext = sniff_ext(data)
            if ext is None:
                print(f"skip {att_id}: unrecognized content ({data[:12]!r})", flush=True)
                errors += 1
                continue
            name = f"{att_id}.{ext}"
            (OUT_DIR / name).write_bytes(data)
            manifest[att_id] = name
        except Exception as e:
            print(f"error {att_id}: {e}", flush=True)
            errors += 1
        if (n + 1) % 100 == 0:
            MANIFEST.write_text(json.dumps({str(k): v for k, v in sorted(manifest.items())}))
            print(f"{n + 1}/{len(todo)} done", flush=True)
        time.sleep(0.35)

    MANIFEST.write_text(json.dumps({str(k): v for k, v in sorted(manifest.items())}))
    print(f"done: {len(manifest)} in manifest, {errors} errors", flush=True)
    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
