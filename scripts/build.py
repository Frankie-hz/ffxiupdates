"""Build docs/index.html: a single self-contained page rendering every record
from data/all.jsonl (produced by combine.py).

Records are embedded as JSON and rendered client-side: filterable list on the
left, full entry on the right. polnews/forum bodies render inline; legacy and
topics pages render as full documents in a sandboxed iframe.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "index.html"

SOURCE_LABEL = {"polnews": "", "forum": "SE Forum", "legacy": "PlayOnline", "topics": "PlayOnline"}


def load_entries():
    entries = []
    for line in (DATA / "all.jsonl").read_text(encoding="utf-8").split("\n"):
        if line == "":
            continue
        r = json.loads(line)
        entry = {
            "s": r["source"],
            "aid": r["id"],
            "url": r["url"],
            "d": r["date"] + " " + (r.get("time") or "00:00"),
            "c": r["category"],
            "f": r.get("from") or SOURCE_LABEL[r["source"]],
            "l": r["lang"],
            "t": r["title"],
            "b": r["body"],
        }
        if r["source"] in ("legacy", "topics"):
            entry["k"] = "doc"
        else:
            entry["k"] = "inline"
        if "translation" in r:
            entry["tr"] = r["translation"]["body"]
            entry["trt"] = r["translation"]["title"]
        if "counterpart" in r:
            entry["cp"] = r["counterpart"]
        entries.append(entry)
    return entries


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FFXI Updates Combined</title>
<style>
:root {
  --bg: #14161f; --panel: #1c1f2b; --panel2: #232736; --line: #343a4f;
  --text: #d8dbe6; --dim: #8b91a7; --accent: #e8c268; --accent2: #7aa2d6;
  --badge-upd: #3d6b45; --badge-vu: #6b5a2e; --badge-maint: #444b63;
  --badge-imp: #7a3d3d; --badge-other: #3a3f55;
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.5 "Segoe UI", system-ui, sans-serif; }
#app { display: flex; flex-direction: column; height: 100vh; }
header { padding: 10px 16px; border-bottom: 2px solid var(--accent);
  background: var(--panel); display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
header h1 { margin: 0; font-size: 18px; color: var(--accent); letter-spacing: 1px; }
header .sub { color: var(--dim); font-size: 12px; }
#controls { padding: 8px 16px; background: var(--panel2); border-bottom: 1px solid var(--line);
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
#controls input[type=search] { background: var(--bg); color: var(--text);
  border: 1px solid var(--line); border-radius: 4px; padding: 6px 10px; width: 300px; }
#controls select { background: var(--bg); color: var(--text);
  border: 1px solid var(--line); border-radius: 4px; padding: 5px 8px; }
#catdrop { position: relative; }
#catbtn { background: var(--bg); color: var(--text); border: 1px solid var(--line);
  border-radius: 4px; padding: 5px 10px; cursor: pointer; }
#catbtn.filtered { border-color: var(--accent); color: var(--accent); }
#catpanel { display: none; position: absolute; top: calc(100% + 4px); left: 0; z-index: 30;
  background: var(--panel); border: 1px solid var(--line); border-radius: 6px;
  padding: 8px 12px; min-width: 190px; box-shadow: 0 6px 18px rgba(0,0,0,0.5); }
#catpanel.open { display: block; }
#catpanel label { display: flex; align-items: center; gap: 7px; padding: 3px 0;
  cursor: pointer; white-space: nowrap; }
#catpanel .quick { display: flex; gap: 10px; border-bottom: 1px solid var(--line);
  padding-bottom: 6px; margin-bottom: 6px; }
#catpanel .quick a { color: var(--accent2); cursor: pointer; font-size: 12px; }
#controls label.chip { display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px; border: 1px solid var(--line); border-radius: 12px;
  cursor: pointer; user-select: none; font-size: 12px; color: var(--dim); }
#controls label.chip:has(input:checked) { color: var(--text); border-color: var(--accent); }
#controls .count { margin-left: auto; color: var(--dim); font-size: 12px; }
#matchnav { display: none; align-items: center; gap: 5px; color: var(--dim); font-size: 12px; }
#matchnav button { background: var(--bg); color: var(--text); border: 1px solid var(--line);
  border-radius: 4px; cursor: pointer; padding: 1px 7px; font-size: 11px; line-height: 1.4; }
#matchnav button:hover { border-color: var(--accent); color: var(--accent); }
#main { display: flex; flex: 1; min-height: 0; }
#list { width: 460px; min-width: 300px; overflow-y: auto; border-right: 1px solid var(--line);
  background: var(--panel); }
#list .row { padding: 7px 12px; border-bottom: 1px solid #262a3a; cursor: pointer; }
#list .row:hover { background: var(--panel2); }
#list .row.active { background: #2b3046; border-left: 3px solid var(--accent); padding-left: 9px; }
#list .row .date { color: var(--dim); font-size: 11px; margin-right: 8px; white-space: nowrap; }
#list .row .badge { font-size: 10px; padding: 1px 6px; border-radius: 8px; margin-left: 6px;
  vertical-align: 1px; white-space: nowrap; }
#list .row .t { display: block; margin-top: 1px; }
#list .more { padding: 10px; text-align: center; color: var(--accent2); cursor: pointer; }
.badge { background: var(--badge-other); color: #cfd4e4; }
.badge.upd { background: var(--badge-upd); }
.badge.vu { background: var(--badge-vu); }
.badge.maint { background: var(--badge-maint); }
.badge.imp { background: var(--badge-imp); }
.badge.ja { background: #5a3a5e; }
.badge.dev { background: #2f5a3e; }
#view { flex: 1; overflow-y: auto; padding: 0; min-width: 0; }
#view .inner { max-width: 860px; margin: 0 auto; padding: 22px 28px 60px; }
#view h2 { color: var(--accent); margin: 0 0 4px; font-size: 20px; }
#view .meta { color: var(--dim); font-size: 12px; margin-bottom: 16px;
  border-bottom: 1px solid var(--line); padding-bottom: 10px; }
#view .meta a { color: var(--accent2); }
#view .body { word-wrap: break-word; }
#view .body a { color: var(--accent2); }
#view .body h3 { color: var(--accent); border-bottom: 1px solid var(--line);
  padding-bottom: 4px; margin-top: 26px; }
#view .body table { border-collapse: collapse; }
#view .body td, #view .body th { border: 1px solid var(--line); padding: 4px 8px; }
#view .body td[bgcolor], #view .body th[bgcolor],
#view .body tr[bgcolor] td, #view .body tr[bgcolor] th,
#view .body table[bgcolor] td, #view .body table[bgcolor] th,
#view .body td[style*="background"], #view .body th[style*="background"],
#view .body tr[style*="background"] td, #view .body tr[style*="background"] th { color: #2a2c38; }
#view .body td[bgcolor] a, #view .body tr[bgcolor] td a,
#view .body td[style*="background"] a, #view .body th[style*="background"] a { color: #1d4ed8; }
#view .body blockquote { border-left: 3px solid var(--line); margin: 8px 0 8px 4px;
  padding: 2px 12px; color: #c2c7d8; }
#view .body font[color="red" i], #view .body font[color="#ff0000" i] { color: #ff7a70; }
#view .body font[color="darkred" i], #view .body font[color="#601f1f" i] { color: #e08585; }
#view .body font[color="#556b2f" i], #view .body font[color="olive" i],
#view .body font[color="green" i], #view .body font[color="darkgreen" i],
#view .body font[color="seagreen" i] { color: #9dc487; }
#view .body font[color="blue" i], #view .body font[color="navy" i],
#view .body font[color="royalblue" i], #view .body font[color="#4040ff" i],
#view .body font[color="#4169e1" i], #view .body font[color="#284176" i],
#view .body font[color="#336699" i], #view .body font[color="darkslateblue" i],
#view .body font[color="#483d8b" i] { color: #8ab4f8; }
#view .body font[color="indigo" i], #view .body font[color="#4b0082" i],
#view .body font[color="purple" i], #view .body font[color="#9932cc" i],
#view .body font[color="darkorchid" i] { color: #c79be0; }
#view .body font[color="black" i], #view .body font[color="#000000" i],
#view .body font[color="#333333" i] { color: inherit; }
#view .body font[color="gray" i], #view .body font[color="dimgray" i],
#view .body font[color="rightgray" i] { color: var(--dim); }
#view .body font[color="sienna" i], #view .body font[color="#a0522d" i],
#view .body font[color="#654924" i] { color: #d2a679; }
#view .body .bbcode_container { border: 1px solid var(--line); background: var(--panel2);
  border-radius: 4px; padding: 6px 12px; margin: 8px 0; }
#view .body .bbcode_description { color: var(--dim); font-size: 11px;
  text-transform: uppercase; letter-spacing: 1px; }
#view .body .bbcode_quote hr { border: 0; border-top: 1px solid var(--line); }
#view .body .bbcode_hiddenblock { border: 1px dashed var(--line); border-radius: 4px;
  padding: 6px 12px; margin: 8px 0; }
#view .body .bbcode_hiddenblock_header { display: none; }
#view .body img.inlineimg { display: none; }
#view .body img { max-width: 100%; }
#view .body img.att { display: block; margin: 8px 0; border: 1px solid var(--line);
  border-radius: 4px; }
#view iframe.doc { width: 100%; height: calc(100vh - 210px); border: 1px solid var(--line);
  background: #fff; border-radius: 4px; }
#view .mtbanner { background: #4a3d1e; border: 1px solid #8a6d2e; color: #e8d9a8;
  border-radius: 4px; padding: 8px 12px; margin-bottom: 14px; font-size: 12.5px; }
#view h3.origlabel { color: var(--dim); border-bottom: 1px solid var(--line);
  padding-bottom: 4px; margin-top: 30px; font-size: 14px; }
#view .empty { color: var(--dim); text-align: center; margin-top: 15vh; }
mark { background: var(--accent); color: #14161f; padding: 0 1px; }
mark.cur { background: #ff9d3c; outline: 2px solid #ff9d3c; }
@media (max-width: 800px) {
  #main { flex-direction: column; }
  #list { width: 100%; max-height: 45vh; }
}
</style>
</head>
<body>
<div id="app">
<header>
  <h1>FFXI UPDATES COMBINED</h1>
  <span class="sub">__SUBTITLE__</span>
</header>
<div id="controls">
  <input id="q" type="search" placeholder="Search titles &amp; full text...">
  <div id="catdrop">
    <button id="catbtn" type="button">Categories</button>
    <div id="catpanel"></div>
  </div>
  <select id="year"><option value="">All years</option></select>
  <label class="chip"><input type="checkbox" id="src-polnews" checked>POL News</label>
  <label class="chip"><input type="checkbox" id="src-forum" checked>SE Forum</label>
  <label class="chip"><input type="checkbox" id="src-legacy" checked>Legacy</label>
  <label class="chip"><input type="checkbox" id="lang-en" checked>EN</label>
  <label class="chip"><input type="checkbox" id="lang-ja" checked>JA</label>
  <label class="chip"><input type="checkbox" id="updonly">Updates only</label>
  <span class="count" id="count"></span>
  <span id="matchnav"><button id="mprev" title="Previous match (Shift+Enter)">&#9650;</button><span id="mcount"></span><button id="mnext" title="Next match (Enter)">&#9660;</button></span>
</div>
<div id="main">
  <div id="list"></div>
  <div id="view"><div class="inner"><div class="empty">Select an entry</div></div></div>
</div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const entries = JSON.parse(document.getElementById("data").textContent);
entries.forEach((e, i) => { e.i = i; });
entries.sort((a, b) => b.d.localeCompare(a.d) || b.i - a.i);
const byIdx = new Map(entries.map(e => [e.i, e]));
const byAid = new Map(entries.map(e => [e.aid, e]));

const UPDATE_CATS = new Set(["Updates", "Version Update", "Update Details"]);
const BADGE_CLASS = { "Updates": "upd", "Version Update": "vu", "Update Details": "vu",
  "Maintenance": "maint", "Important Notices": "imp", "Dev Tracker": "dev" };
const PAGE = 400;

const $ = id => document.getElementById(id);
const list = $("list"), view = $("view");
let filtered = entries;
let shown = PAGE;
let activeIdx = -1;
let searchText = null;

function textOf(e) {
  if (e.x === undefined) {
    e.x = (e.t + " " + (e.trt || "") + " " + (e.tr || "") + " " + e.b)
      .replace(/<[^>]+>/g, " ").toLowerCase();
  }
  return e.x;
}

const allCats = [...new Set(entries.map(e => e.c))].sort();
let catOn = new Set(allCats);
try {
  const saved = JSON.parse(localStorage.getItem("ffxiupd-cats"));
  if (Array.isArray(saved) && saved.length > 0) {
    catOn = new Set(saved.filter(c => allCats.includes(c)));
  }
} catch (err) {}

function saveCats() {
  try {
    localStorage.setItem("ffxiupd-cats", JSON.stringify([...catOn]));
  } catch (err) {}
}

function updateCatButton() {
  const btn = $("catbtn");
  btn.textContent = "Categories " + catOn.size + "/" + allCats.length + " ▾";
  if (catOn.size === allCats.length) {
    btn.classList.remove("filtered");
  } else {
    btn.classList.add("filtered");
  }
}

function applyFilters() {
  const q = $("q").value.trim().toLowerCase();
  const year = $("year").value;
  const srcOn = { polnews: $("src-polnews").checked, forum: $("src-forum").checked,
    legacy: $("src-legacy").checked, topics: $("src-legacy").checked };
  const langOn = { en: $("lang-en").checked, ja: $("lang-ja").checked };
  const updOnly = $("updonly").checked;
  searchText = q.length >= 2 ? q : null;
  filtered = entries.filter(e => {
    if (srcOn[e.s] === false) return false;
    if (langOn[e.l] === false) return false;
    if (catOn.has(e.c) === false) return false;
    if (year !== "" && e.d.slice(0, 4) !== year) return false;
    if (updOnly && UPDATE_CATS.has(e.c) === false) return false;
    if (searchText !== null && textOf(e).indexOf(searchText) === -1) return false;
    return true;
  });
  shown = PAGE;
  clearMarks();
  renderList();
}

function renderList() {
  const frag = document.createDocumentFragment();
  filtered.slice(0, shown).forEach(e => {
    const row = document.createElement("div");
    row.className = "row" + (e.i === activeIdx ? " active" : "");
    row.dataset.i = e.i;
    const badge = BADGE_CLASS[e.c] || "";
    let langBadge = "";
    if (e.l === "ja") langBadge = '<span class="badge ja">JA</span>';
    row.innerHTML = '<span class="date">' + e.d.slice(0, 10) + '</span>' +
      '<span class="badge ' + badge + '">' + esc(e.c) + '</span>' + langBadge +
      '<span class="t">' + esc(e.trt || e.t) + '</span>';
    frag.appendChild(row);
  });
  if (filtered.length > shown) {
    const more = document.createElement("div");
    more.className = "more";
    more.textContent = "Show " + Math.min(PAGE, filtered.length - shown) + " more (" +
      (filtered.length - shown) + " remaining)";
    more.onclick = () => { shown += PAGE; renderList(); };
    frag.appendChild(more);
  }
  list.replaceChildren(frag);
  $("count").textContent = filtered.length + " / " + entries.length + " entries";
}

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlight(container, q, doc) {
  doc = doc || document;
  const walker = doc.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const targets = [];
  while (walker.nextNode()) {
    if (walker.currentNode.nodeValue.toLowerCase().includes(q)) targets.push(walker.currentNode);
  }
  targets.forEach(node => {
    const parts = node.nodeValue.split(new RegExp("(" + q.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&") + ")", "ig"));
    if (parts.length < 2) return;
    const frag = doc.createDocumentFragment();
    parts.forEach((p, idx) => {
      if (idx % 2 === 1) {
        const m = doc.createElement("mark");
        m.textContent = p;
        frag.appendChild(m);
      } else if (p !== "") {
        frag.appendChild(doc.createTextNode(p));
      }
    });
    node.parentNode.replaceChild(frag, node);
  });
}

let marks = [];
let markIdx = -1;

function updateMatchNav() {
  const nav = $("matchnav");
  if (marks.length === 0) {
    nav.style.display = "none";
    return;
  }
  nav.style.display = "inline-flex";
  $("mcount").textContent = (markIdx + 1) + " / " + marks.length;
}

function clearMarks() {
  marks = [];
  markIdx = -1;
  updateMatchNav();
}

function gotoMatch(i) {
  if (marks.length === 0) return;
  if (markIdx >= 0 && marks[markIdx]) marks[markIdx].classList.remove("cur");
  markIdx = ((i % marks.length) + marks.length) % marks.length;
  const m = marks[markIdx];
  m.classList.add("cur");
  m.scrollIntoView({block: "center"});
  updateMatchNav();
}

function setMarks(list) {
  marks = list;
  markIdx = -1;
  if (marks.length > 0) gotoMatch(0);
  updateMatchNav();
}

function show(i) {
  const e = byIdx.get(i);
  activeIdx = i;
  const inner = document.createElement("div");
  inner.className = "inner";
  let cpLine = "";
  const partner = e.cp !== undefined ? byAid.get(e.cp) : undefined;
  if (partner !== undefined) {
    const label = (() => {
      if (e.l === "ja") return "Official English version";
      return "Japanese version (日本語版)";
    })();
    cpLine = ' &middot; ' + label + ': <a href="#" data-goto="' + partner.i + '">' +
      esc(partner.t) + '</a>';
  }
  const meta = '<div class="meta">' + esc(e.d) + (e.f ? " &middot; From: " + esc(e.f) : "") +
    ' &middot; ' + esc(e.c) + ' &middot; <a href="' + e.url +
    '" target="_blank" rel="noopener">original page</a>' + cpLine + '</div>';
  if (e.k === "doc") {
    inner.innerHTML = "<h2>" + esc(e.t) + "</h2>" + meta;
    if (e.tr !== undefined) {
      const trWrap = document.createElement("div");
      trWrap.className = "body";
      trWrap.innerHTML = '<div class="mtbanner">&#9888; Machine translation. This page was ' +
        "only published in Japanese (it predates the North American release); the text below " +
        "is an automatic translation provided for readability and search. The original " +
        "Japanese page is shown underneath.</div>" + e.tr;
      if (searchText !== null) highlight(trWrap, searchText);
      inner.appendChild(trWrap);
      inner.insertAdjacentHTML("beforeend",
        '<h3 class="origlabel">Original page (Japanese)</h3>');
    }
    const frame = document.createElement("iframe");
    frame.className = "doc";
    frame.sandbox = "allow-same-origin";
    frame.srcdoc = e.b;
    if (searchText !== null) {
      const q = searchText;
      frame.addEventListener("load", () => {
        try {
          const doc = frame.contentDocument;
          const style = doc.createElement("style");
          style.textContent = "mark{background:#e8c268;color:#14161f;padding:0 1px}" +
            "mark.cur{background:#ff9d3c;outline:2px solid #ff9d3c}";
          doc.head.appendChild(style);
          highlight(doc.body, q, doc);
          const frameMarks = [...doc.querySelectorAll("mark")];
          if (marks.length === 0) {
            setMarks(frameMarks);
          } else {
            marks = marks.concat(frameMarks);
            updateMatchNav();
          }
        } catch (err) {}
      });
    }
    inner.appendChild(frame);
  } else if (e.tr !== undefined) {
    inner.innerHTML = "<h2>" + esc(e.trt || e.t) + "</h2>" + meta +
      '<div class="body"><div class="mtbanner">&#9888; Machine translation. No official ' +
      "English version of this post exists; the text below is an automatic translation " +
      "provided for readability and search. The original Japanese post follows underneath." +
      "</div>" + e.tr + '<h3 class="origlabel">Original post (Japanese)</h3>' + e.b + "</div>";
    if (searchText !== null) highlight(inner.querySelector(".body"), searchText);
  } else {
    inner.innerHTML = "<h2>" + esc(e.t) + "</h2>" + meta + '<div class="body">' + e.b + "</div>";
    if (searchText !== null) highlight(inner.querySelector(".body"), searchText);
  }
  view.replaceChildren(inner);
  clearMarks();
  const found = [...inner.querySelectorAll("mark")];
  if (found.length > 0) {
    setMarks(found);
  } else {
    view.scrollTop = 0;
  }
  list.querySelectorAll(".row.active").forEach(r => r.classList.remove("active"));
  const row = list.querySelector('.row[data-i="' + i + '"]');
  if (row !== null) row.classList.add("active");
  history.replaceState(null, "", "#" + e.s + "-" + e.url.split("/").pop());
}

list.addEventListener("click", ev => {
  const row = ev.target.closest(".row");
  if (row !== null) show(parseInt(row.dataset.i, 10));
});

view.addEventListener("click", ev => {
  const link = ev.target.closest("a[data-goto]");
  if (link !== null) {
    ev.preventDefault();
    show(parseInt(link.dataset.goto, 10));
  }
});

let timer = null;
$("q").addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(applyFilters, 200);
});
$("q").addEventListener("keydown", ev => {
  if (ev.key === "Enter") {
    ev.preventDefault();
    gotoMatch(markIdx + (ev.shiftKey ? -1 : 1));
  }
});
$("mprev").addEventListener("click", () => gotoMatch(markIdx - 1));
$("mnext").addEventListener("click", () => gotoMatch(markIdx + 1));
["year", "src-polnews", "src-forum", "src-legacy", "lang-en", "lang-ja", "updonly"].forEach(id => {
  $(id).addEventListener("change", applyFilters);
});

function buildCatPanel() {
  const panel = $("catpanel");
  panel.innerHTML = '<div class="quick"><a id="cat-all">All</a><a id="cat-none">None</a></div>';
  allCats.forEach(c => {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = catOn.has(c);
    box.addEventListener("change", () => {
      if (box.checked) {
        catOn.add(c);
      } else {
        catOn.delete(c);
      }
      saveCats();
      updateCatButton();
      applyFilters();
    });
    label.appendChild(box);
    label.appendChild(document.createTextNode(c));
    panel.appendChild(label);
  });
  panel.querySelector("#cat-all").addEventListener("click", () => {
    catOn = new Set(allCats);
    saveCats();
    buildCatPanel();
    updateCatButton();
    applyFilters();
  });
  panel.querySelector("#cat-none").addEventListener("click", () => {
    catOn = new Set();
    saveCats();
    buildCatPanel();
    updateCatButton();
    applyFilters();
  });
}

$("catbtn").addEventListener("click", () => {
  $("catpanel").classList.toggle("open");
});
document.addEventListener("click", ev => {
  if (ev.target.closest("#catdrop") === null) {
    $("catpanel").classList.remove("open");
  }
});
buildCatPanel();
updateCatButton();

const years = [...new Set(entries.map(e => e.d.slice(0, 4)))].sort().reverse();
years.forEach(y => $("year").insertAdjacentHTML("beforeend",
  '<option value="' + y + '">' + y + "</option>"));

applyFilters();

if (location.hash.length > 1) {
  const ref = decodeURIComponent(location.hash.slice(1));
  const target = entries.find(e => e.s + "-" + e.url.split("/").pop() === ref);
  if (target !== undefined) show(target.i);
}
</script>
</body>
</html>
"""


def main():
    entries = load_entries()
    counts = {}
    for e in entries:
        counts[e["s"]] = counts.get(e["s"], 0) + 1
    print(" ".join(f"{s}={n}" for s, n in sorted(counts.items())))
    dates = sorted(e["d"] for e in entries)
    subtitle = (f"{len(entries)} entries &middot; {dates[0][:10]} to {dates[-1][:10]} &middot; "
                "PlayOnline news, SE forum &amp; legacy update archives")
    payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    html = TEMPLATE.replace("__SUBTITLE__", subtitle).replace("__DATA__", payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
