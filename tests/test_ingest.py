import pytest
from bs4 import BeautifulSoup

from src.ingest import RAW, fixed_chunks, parse_units, split_long, structural_chunks

needs_raw = pytest.mark.skipif(not RAW.exists(), reason="download the EUR-Lex HTML into data/raw first")


def test_split_long_overlaps_and_respects_limit():
    paras = [f"parrafo {i} " + "x" * 80 for i in range(10)]
    parts = split_long(paras, max_chars=300, overlap=100)
    assert len(parts) > 1
    assert all(len(p) <= 300 for p in parts)
    assert paras[2] in parts[0] and paras[2] in parts[1]  # overlap: last paragraph is repeated


@needs_raw
def test_units_match_the_regulation():
    units = parse_units(BeautifulSoup(RAW.read_text(encoding="utf-8"), "lxml"))
    kinds = [u["kind"] for u in units]
    assert (kinds.count("articulo"), kinds.count("considerando"), kinds.count("anexo")) == (113, 180, 13)
    sources = {u["source"] for u in units}
    assert {"Artículo 5", "Anexo III", "Considerando 1"} <= sources


@needs_raw
def test_every_chunk_keeps_its_citation():
    units = parse_units(BeautifulSoup(RAW.read_text(encoding="utf-8"), "lxml"))
    assert all(c["source"] and c["text"] for c in structural_chunks(units))
    assert all(c["sources"] for c in fixed_chunks(units))
