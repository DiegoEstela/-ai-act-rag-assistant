"""Quality gates: these tests fail if the system gets worse than the committed thresholds."""
import json
from pathlib import Path

import pytest

from evals import generation
from evals.retrieval import evaluate
from src.embed import PROCESSED
from src.generate import DEFAULT_K

THRESHOLDS = json.loads(Path("evals/thresholds.json").read_text(encoding="utf-8"))

needs_index = pytest.mark.skipif(
    not (PROCESSED / "vectors_structural.npy").exists(),
    reason="build the index first: python -m src.ingest && python -m src.embed build")


def check(metrics: dict, rules: dict):
    """Collect every violated threshold so a failure lists all of them, not just the first."""
    failures = []
    for name, rule in rules.items():
        value = metrics[name]
        if "min" in rule and value < rule["min"]:
            failures.append(f"{name} = {value:.3f} < min {rule['min']}")
        if "max" in rule and value > rule["max"]:
            failures.append(f"{name} = {value:.3f} > max {rule['max']}")
    assert not failures, "quality gate failed:\n  " + "\n  ".join(failures)


@needs_index
def test_retrieval_meets_thresholds():
    check(evaluate("structural")["metrics"], THRESHOLDS["retrieval"])


@needs_index
@pytest.mark.skipif(not (PROCESSED / "vectors_fixed.npy").exists(), reason="fixed index not built")
def test_structural_chunking_is_not_worse_than_fixed_size():
    structural = evaluate("structural")["metrics"]["mrr"]
    fixed = evaluate("fixed")["metrics"]["mrr"]
    assert structural >= fixed, f"structural MRR {structural:.3f} < fixed MRR {fixed:.3f}"


@pytest.mark.llm
@needs_index
def test_generation_meets_thresholds(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "RESULTS", tmp_path)  # do not overwrite the committed baseline
    rows = generation.run("structural", k=DEFAULT_K, reuse=False)
    check(generation.summarize(rows), THRESHOLDS["generation"])
