import json

import pytest

from evals.golden import load_golden, problems
from src.embed import PROCESSED

needs_chunks = pytest.mark.skipif(not (PROCESSED / "chunks_structural.json").exists(),
                                  reason="run: python -m src.ingest")


def test_golden_set_shape():
    g = load_golden()
    assert len(g) == 15
    assert sum(not q["answerable"] for q in g) == 3
    assert len({q["id"] for q in g}) == 15


@needs_chunks
def test_every_source_exists_in_the_corpus():
    chunks = json.loads((PROCESSED / "chunks_structural.json").read_text(encoding="utf-8"))
    assert problems(load_golden(), {c["source"] for c in chunks}) == []
