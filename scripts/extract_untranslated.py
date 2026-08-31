"""List Japanese records that have neither an official counterpart nor a
machine translation, and dump their text to chunk files for translation work.

Usage: extract_untranslated.py [category] [chunk_size] [outdir]
Defaults: all categories, 40 per chunk, ./untranslated_chunks
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def strip_html(text):
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|td|tr|li|div|h\d|blockquote)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t　]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def main():
    category = sys.argv[1] if len(sys.argv) > 1 else None
    chunk_size = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    outdir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("untranslated_chunks")

    records = []
    for line in (ROOT / "data" / "all.jsonl").read_text(encoding="utf-8").split("\n"):
        if line == "":
            continue
        r = json.loads(line)
        if r["lang"] != "ja" or "counterpart" in r or "translation" in r:
            continue
        if category and r["category"] != category:
            continue
        records.append(r)
    records.sort(key=lambda r: r["date"])

    outdir.mkdir(parents=True, exist_ok=True)
    total_chars = 0
    for c in range(0, len(records), chunk_size):
        with (outdir / f"chunk_{c // chunk_size:02d}.txt").open("w", encoding="utf-8") as f:
            for r in records[c:c + chunk_size]:
                text = strip_html(r["body"])
                total_chars += len(text)
                f.write(f"===== {r['id']} | {r['date']} | {r['category']} | {r['title']}\n{text}\n\n")
    n_chunks = (len(records) + chunk_size - 1) // chunk_size
    print(f"{len(records)} untranslated ja records, {total_chars} chars, {n_chunks} chunks in {outdir}")


if __name__ == "__main__":
    main()
