"""Normalize polnews.jsonl, forum.jsonl, and legacy.jsonl into data/all.jsonl,
one schema across every source (documented in the README):

  id        unique across sources, e.g. "forum-49064"
  source    "polnews" | "forum" | "legacy" | "topics"
  url       original page
  date      ISO date, always present
  time      "HH:MM", optional
  tz        optional (polnews only)
  lang      "en" | "ja"
  from      optional (polnews only)
  category  "Updates" | "Version Update" | "Update Details" | ... (see README)
  title     plain text
  body      HTML
  translation  optional {title, body} machine translation for ja legacy pages

Version-update forum threads are dated by the date in their title (the actual
patch day) rather than the posting date.
"""

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "all.jsonl"

JP_CHAR_RE = re.compile(r"[぀-ヿ一-鿿]")
EN_TITLE_DATE_RE = re.compile(r"(\w+)\.?\s+(\d{1,2}),?\s+(\d{4})")
JA_TITLE_DATE_RE = re.compile(r"(\d{4})[年.](\d{1,2})[月.](\d{1,2})")


def load_jsonl(name):
    path = DATA / name
    if path.exists() is False:
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]


def load_translations():
    index_path = DATA / "translations" / "index.json"
    if index_path.exists() is False:
        return {}
    translations = {}
    for t in json.loads(index_path.read_text(encoding="utf-8")):
        body = (DATA / "translations" / t["file"]).read_text(encoding="utf-8")
        translations[t["path"]] = {"title": t["title"], "body": body}
    return translations


def title_date(title):
    m = JA_TITLE_DATE_RE.search(title)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = EN_TITLE_DATE_RE.search(title)
    if m:
        month = m.group(1)[:3].title()
        try:
            parsed = datetime.strptime(f"{month} {m.group(2)} {m.group(3)}", "%b %d %Y")
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%d")
    return None


def is_version_update_title(title):
    return "version update" in title.lower() or "バージョンアップ" in title


def polnews_records():
    category_map = {"Server Maintenance": "Maintenance", "Important": "Important Notices"}
    for e in load_jsonl("polnews.jsonl"):
        yield {
            "id": f"polnews-{e['id']}",
            "source": "polnews",
            "url": f"https://www.playonline.com/ff11us/polnews/news{e['id']}.shtml",
            "date": e["date"][:10],
            "time": e["date"][11:],
            "tz": e.get("tz", ""),
            "lang": "en",
            "from": e.get("from", ""),
            "category": category_map.get(e["category"], e["category"]) or "General",
            "title": e["title"],
            "body": e["body"],
        }


def forum_records():
    for e in load_jsonl("forum.jsonl"):
        record = {
            "id": f"forum-{e['id']}",
            "source": "forum",
            "url": f"https://forum.square-enix.com/ffxi/threads/{e['id']}",
            "date": e["date"][:10],
            "time": e["date"][11:],
            "lang": e.get("lang", "en"),
            "category": "Forum Info",
            "title": e["title"],
            "body": e["body"],
        }
        if is_version_update_title(e["title"]):
            record["category"] = "Version Update"
            record["date"] = title_date(e["title"]) or record["date"]
        yield record


def legacy_records():
    translations = load_translations()
    for e in load_jsonl("legacy.jsonl"):
        if "/pcd2/topics/" in e["path"]:
            source = "topics"
        else:
            source = "legacy"
        slug = re.sub(r"[^A-Za-z0-9]+", "-", e["path"].removesuffix(".html")).strip("-")
        body = e["doc"]
        jp_chars = len(JP_CHAR_RE.findall(body))
        if jp_chars > 0 and jp_chars / max(len(body), 1) > 0.02:
            lang = "ja"
        else:
            lang = "en"
        record = {
            "id": f"{source}-{slug}",
            "source": source,
            "url": e["url"],
            "date": e["date"],
            "lang": lang,
            "category": "Update Details",
            "title": e["title"],
            "body": body,
        }
        tr = translations.get(e["path"])
        if tr:
            record["title"] = tr["title"]
            record["translation"] = tr
        yield record


def main():
    records = list(polnews_records()) + list(forum_records()) + list(legacy_records())
    records.sort(key=lambda r: (r["date"], r["id"]))
    seen = set()
    for r in records:
        if r["id"] in seen:
            raise SystemExit(f"duplicate id: {r['id']}")
        seen.add(r["id"])
    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts = {}
    for r in records:
        key = (r["source"], r["lang"])
        counts[key] = counts.get(key, 0) + 1
    print(f"wrote {len(records)} records to {OUT}")
    for (source, lang), n in sorted(counts.items()):
        print(f"  {source}/{lang}: {n}")


if __name__ == "__main__":
    main()
