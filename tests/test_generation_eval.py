from evals.generation import abstained, cites, summarize
from src.generate import NOT_FOUND


def test_cites_does_not_confuse_article_5_with_article_50():
    assert cites("Según el Artículo 5.1.a, está prohibido", ["Artículo 5"])
    assert not cites("Véase el Artículo 50", ["Artículo 5"])
    assert cites("(Anexo III)", ["Artículo 6", "Anexo III"])  # any expected source counts


def test_abstained_detects_the_fixed_phrase_even_with_extra_text():
    assert abstained(NOT_FOUND)
    assert abstained(NOT_FOUND + " Los fragmentos tratan de otra cosa.")
    assert not abstained("Hasta 35 000 000 EUR (Artículo 99).")


def test_summarize_separates_answerable_from_out_of_scope():
    rows = [
        {"answerable": True, "faithfulness": 5, "correctness": 4, "cites_expected": True, "abstained": False},
        {"answerable": True, "faithfulness": 3, "correctness": 2, "cites_expected": False, "abstained": True},
        {"answerable": False, "faithfulness": 5, "correctness": 5, "cites_expected": None, "abstained": True},
    ]
    s = summarize(rows)
    assert s["correctness_mean"] == 3.0
    assert s["citation_rate"] == 0.5
    assert s["false_abstention_rate"] == 0.5
    assert s["abstention_rate_out_of_scope"] == 1.0
