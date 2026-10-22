import pytest

from evals.retrieval import first_rank, summarize


def test_first_rank_is_one_based_and_takes_best_of_several_sources():
    ranking = ["Artículo 5", "Considerando 31", "Artículo 111", "Artículo 113"]
    assert first_rank(ranking, ["Artículo 5"]) == 1
    assert first_rank(ranking, ["Artículo 113", "Artículo 111"]) == 3  # any source counts: earliest wins
    assert first_rank(ranking, ["Artículo 99"]) is None


def test_hit_at_k_and_mrr_match_the_worked_example():
    # positions 1st, 3rd, 2nd and not found, as explained in the docs
    m = summarize([1, 3, 2, None], ks=(1, 3))
    assert m["hit@1"] == 0.25
    assert m["hit@3"] == 0.75
    assert m["mrr"] == pytest.approx((1 + 1 / 3 + 1 / 2 + 0) / 4)
