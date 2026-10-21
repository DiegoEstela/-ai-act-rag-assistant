"""Parse the EUR-Lex HTML of Reglamento (UE) 2024/1689 and split it into chunks.

Two strategies are produced so we can compare them later:
  - structural: one chunk per article / recital / annex, long ones split with overlap
  - fixed: the whole text cut every N characters, ignoring the structure
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

RAW = Path("data/raw/ai_act_es.html")
OUT = Path("data/processed")
MAX_CHARS = 1200
OVERLAP = 200


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def blocks(el) -> list[str]:
    """Return the text paragraphs of an element, keeping table rows ("a)" + text) together."""
    out = []
    for child in el.children:
        if not getattr(child, "name", None):
            continue
        if child.name == "p":
            out.append(clean(child.get_text(" ")))
        elif child.name == "table":
            for tr in child.select(":scope > tbody > tr, :scope > tr"):
                out.append(clean(tr.get_text(" ")))
        elif child.name == "div":
            out.extend(blocks(child))
    return [b for b in out if b]


def split_long(paragraphs: list[str], max_chars=MAX_CHARS, overlap=OVERLAP) -> list[str]:
    """Group paragraphs into parts of up to max_chars; each part repeats the tail of the previous one."""
    pieces = []
    for p in paragraphs:  # a single huge paragraph is cut by sentences
        if len(p) <= max_chars:
            pieces.append(p)
        else:
            pieces.extend(re.findall(r".{1,%d}(?:[.;:]\s|$)" % max_chars, p) or [p[:max_chars]])
    parts, cur = [], []
    for p in pieces:
        if cur and len(" ".join(cur + [p])) > max_chars:
            parts.append(" ".join(cur))
            tail = []
            while cur and len(" ".join([cur[-1]] + tail)) <= overlap:
                tail.insert(0, cur.pop())
            cur = tail
        cur.append(p)
    if cur:
        parts.append(" ".join(cur))
    return parts


def parse_units(soup) -> list[dict]:
    """Return the document as ordered units: recitals, articles, annexes."""
    units = []
    for d in soup.find_all("div", id=re.compile(r"^rct_\d+$")):
        text = clean(d.get_text(" "))
        n = d["id"].split("_")[1]
        units.append({"kind": "considerando", "source": f"Considerando {n}", "title": "",
                      "chapter": "", "paragraphs": [text]})
    for d in soup.find_all("div", id=re.compile(r"^art_\d+$")):
        label = clean(d.find("p", class_="oj-ti-art").get_text(" "))
        title = clean(d.find("p", class_="oj-sti-art").get_text(" "))
        body = [b for b in blocks(d) if b not in (label, title)]
        cpt = d.find_parent("div", id=re.compile(r"^cpt_[IVX]+$"))
        chapter = ""
        if cpt:
            chapter = clean(cpt.find("p").get_text(" ")).title() + " - " + \
                clean(cpt.find("div", class_="eli-title").get_text(" "))
        units.append({"kind": "articulo", "source": label, "title": title,
                      "chapter": chapter, "paragraphs": body})
    for d in soup.find_all("div", id=re.compile(r"^anx_[IVX]+$")):
        b = blocks(d)
        label = "Anexo " + b[0].split()[1]  # "ANEXO III" -> "Anexo III"
        title = b[1] if len(b) > 1 else ""
        units.append({"kind": "anexo", "source": label, "title": title,
                      "chapter": "", "paragraphs": b[2:]})
    return units


def structural_chunks(units: list[dict]) -> list[dict]:
    chunks = []
    for u in units:
        header = u["source"] + (f" - {u['title']}" if u["title"] else "")
        parts = split_long(u["paragraphs"])
        for i, part in enumerate(parts):
            suffix = f" (parte {i + 1}/{len(parts)})" if len(parts) > 1 else ""
            chunks.append({
                "id": f"{u['source']}#{i + 1}",
                "kind": u["kind"],
                "source": u["source"],
                "chapter": u["chapter"],
                "text": f"{header}{suffix}\n{part}",
            })
    return chunks


def fixed_chunks(units: list[dict], size=1000, overlap=OVERLAP) -> list[dict]:
    """Cut the full text every `size` chars. `sources` lists the units each cut touches (for evals only)."""
    full, spans, pos = "", [], 0
    for u in units:
        t = u["source"] + "\n" + " ".join(u["paragraphs"]) + "\n"
        spans.append((pos, pos + len(t), u["source"]))
        full += t
        pos += len(t)
    chunks, start = [], 0
    while start < len(full):
        end = min(start + size, len(full))
        srcs = [s for a, b, s in spans if a < end and b > start]
        chunks.append({"id": f"fixed#{len(chunks)}", "kind": "fixed", "source": srcs[0],
                       "sources": srcs, "chapter": "", "text": full[start:end]})
        if end == len(full):
            break
        start = end - overlap
    return chunks


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    soup = BeautifulSoup(RAW.read_text(encoding="utf-8"), "lxml")
    units = parse_units(soup)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, chunks in (("structural", structural_chunks(units)), ("fixed", fixed_chunks(units))):
        (OUT / f"chunks_{name}.json").write_text(
            json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
        lens = [len(c["text"]) for c in chunks]
        print(f"{name}: {len(chunks)} chunks, chars min/avg/max = "
              f"{min(lens)}/{sum(lens) // len(lens)}/{max(lens)}")
    kinds = {}
    for u in units:
        kinds[u["kind"]] = kinds.get(u["kind"], 0) + 1
    print("units:", kinds)


if __name__ == "__main__":
    main()
