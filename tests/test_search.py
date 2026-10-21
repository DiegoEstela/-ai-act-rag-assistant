import pytest

from src.embed import PROCESSED
from src.search import Index

pytestmark = pytest.mark.skipif(
    not (PROCESSED / "vectors_structural.npy").exists(),
    reason="run: python -m src.ingest && python -m src.embed build")


def test_search_returns_sorted_results_with_citation():
    res = Index("structural").search("¿Qué prácticas de IA están prohibidas?", k=3)
    assert len(res) == 3
    assert [r["score"] for r in res] == sorted((r["score"] for r in res), reverse=True)
    assert all(r["source"] for r in res)


def test_prohibited_practices_question_finds_article_5():
    res = Index("structural").search("¿Qué prácticas de IA están prohibidas?", k=3)
    assert "Artículo 5" in {r["source"] for r in res}
