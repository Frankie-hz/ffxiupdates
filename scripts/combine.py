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
  translation  optional {title, body} machine translation for ja pages with no
               official English version
  counterpart  optional record id of the same content in the other language
               (official localization; forum records only)

Version-update forum threads are dated by the date in their title (the actual
patch day) rather than the posting date. Counterparts are paired by date
(exact, then +-1 day) for version updates, by episode number for Freshly
Picked Vana'diel digests, and by the curated map in data/thread_pairs.json
for topic stickies.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "all.jsonl"

JP_CHAR_RE = re.compile(r"[぀-ヿ一-鿿]")
EN_TITLE_DATE_RE = re.compile(r"(\w+)\.?\s+(\d{1,2}),?\s+(\d{4})")
JA_TITLE_DATE_RE = re.compile(r"(\d{4})[年.](\d{1,2})[月.](\d{1,2})")
JA_DIGEST_NUM_RE = re.compile(r"第\s*(\d+)\s*回")
EN_DIGEST_NUM_RE = re.compile(r"Freshly Picked Vana.diel\s*(\d*)\s*.?\s*Digest")


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
        lang = e.get("lang", "en")
        if lang == "ja":
            record_id = f"polnews-ja-{e['id']}"
            site = "ff11"
        else:
            record_id = f"polnews-{e['id']}"
            site = "ff11us"
        yield {
            "id": record_id,
            "source": "polnews",
            "url": f"https://www.playonline.com/{site}/polnews/news{e['id']}.shtml",
            "date": e["date"][:10],
            "time": e["date"][11:],
            "tz": e.get("tz", ""),
            "lang": lang,
            "from": e.get("from", ""),
            "category": category_map.get(e["category"], e["category"]) or "General",
            "title": e["title"],
            "body": e["body"],
        }


def digest_number(record):
    if record["lang"] == "ja":
        if "もぎたて" in record["title"] or "ヴァナ・ディール」まとめ" in record["title"]:
            m = JA_DIGEST_NUM_RE.search(record["title"])
            if m:
                return int(m.group(1))
            if record["title"] == "「もぎたて ヴァナ・ディール」まとめ":
                return 1
        return None
    m = EN_DIGEST_NUM_RE.search(record["title"])
    if m:
        return int(m.group(1) or 1)
    return None


def pair_counterparts(records):
    manual = json.loads((DATA / "thread_pairs.json").read_text(encoding="utf-8"))["pairs"]
    en_vu = {}
    en_digest = {}
    for r in records:
        if r["lang"] != "en":
            continue
        if r["category"] == "Version Update":
            en_vu.setdefault(r["date"], r)
        n = digest_number(r)
        if n is not None:
            en_digest[n] = r
    for r in records:
        if r["lang"] != "ja":
            continue
        tid = r["id"].removeprefix("forum-")
        partner = None
        if tid in manual:
            partner_id = f"forum-{manual[tid]}"
            partner = next((x for x in records if x["id"] == partner_id), None)
        if partner is None:
            n = digest_number(r)
            if n is not None:
                partner = en_digest.get(n)
        if partner is None and r["category"] == "Version Update":
            partner = en_vu.get(r["date"])
            if partner is None:
                base = date.fromisoformat(r["date"])
                near = [v for k, v in en_vu.items()
                        if abs((date.fromisoformat(k) - base).days) <= 1]
                if len(near) == 1:
                    partner = near[0]
        if partner is not None:
            r["counterpart"] = partner["id"]
            partner.setdefault("counterpart", r["id"])


def load_forum_translations():
    index_path = DATA / "translations" / "forum_index.json"
    if index_path.exists() is False:
        return {}
    translations = {}
    for t in json.loads(index_path.read_text(encoding="utf-8")):
        body = (DATA / "translations" / t["file"]).read_text(encoding="utf-8")
        translations[t["thread"]] = {"title": t["title"], "body": body}
    return translations


def forum_records():
    translations = load_forum_translations()
    records = []
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
        tr = translations.get(e["id"])
        if tr:
            record["translation"] = tr
        records.append(record)
    pair_counterparts(records)
    return records


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
