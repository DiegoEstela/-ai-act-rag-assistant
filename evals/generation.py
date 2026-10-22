"""Generation evals: run the full RAG on the golden set and score the answers.

Deterministic checks (code): did it cite the expected article? did it abstain?
Judgement calls (LLM-as-judge): is every claim supported by the fragments (faithfulness) and does
the answer match the expected one in substance (correctness)?
"""
import argparse
import json
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from evals.golden import load_golden
from src.generate import NOT_FOUND, answer
from src.search import DEFAULT_EXCLUDE, Index

load_dotenv()

JUDGE_MODEL = "claude-sonnet-5-5"  # stronger and different from the generator, to limit self-preference bias
RESULTS = Path("evals/results")

JUDGE_SYSTEM = """Sos un evaluador estricto de un sistema de preguntas y respuestas sobre el Reglamento (UE) 2024/1689.
Recibís la pregunta, la respuesta esperada (escrita por una persona), los fragmentos de contexto que se le dieron al sistema y la respuesta del sistema.

Puntuá de 1 a 5:
- fidelidad: ¿todo lo que afirma la respuesta está respaldado por los fragmentos de contexto? 5 = todo respaldado; 3 = algún dato no respaldado; 1 = inventa o contradice el contexto. Si la respuesta solo dice que el reglamento no lo indica, es fiel (5).
- correctitud: ¿coincide en lo esencial con la respuesta esperada? 5 = cubre todo lo esencial sin errores; 3 = parcial o incompleta; 1 = incorrecta o no responde. Si la respuesta esperada es que el reglamento no lo indica, 5 = se abstiene y 1 = da una respuesta de fondo.

No premies la longitud ni el estilo. Respondé SOLO con un JSON: {"fidelidad": <1-5>, "correctitud": <1-5>, "justificacion": "<una frase>"}"""


def cites(answer_text: str, sources: list[str]) -> bool:
    """True if the answer mentions any expected source ('Artículo 5' must not match 'Artículo 50')."""
    return any(re.search(re.escape(s) + r"(?!\d)", answer_text) for s in sources)


def abstained(answer_text: str) -> bool:
    return NOT_FOUND.lower().rstrip(".") in answer_text.lower()


def judge(q: dict, result: dict) -> dict:
    context = "\n\n".join(f'[{c["source"]}]\n{c["text"]}' for c in result["chunks"])
    user = (f"<pregunta>{q['question']}</pregunta>\n<respuesta_esperada>{q['expected_answer']}</respuesta_esperada>\n"
            f"<contexto>\n{context}\n</contexto>\n<respuesta_del_sistema>{result['answer']}</respuesta_del_sistema>")
    resp = anthropic.Anthropic().messages.create(
        model=JUDGE_MODEL, max_tokens=4000, system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in resp.content if b.type == "text")
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))


def run(strategy: str, k: int, reuse: bool, exclude_kinds: tuple[str, ...] = DEFAULT_EXCLUDE) -> list[dict]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    suffix = "" if "considerando" in exclude_kinds else "_withrecitals"
    path = RESULTS / f"generation_{strategy}_k{k}{suffix}.json"
    if reuse and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    index, rows = Index(strategy, exclude_kinds), []
    for q in load_golden():
        r = answer(q["question"], index, k)
        j = judge(q, r)
        rows.append({
            "id": q["id"], "question": q["question"], "answerable": q["answerable"],
            "expected_answer": q["expected_answer"], "answer": r["answer"],
            "context": [c["id"] for c in r["chunks"]],
            "cites_expected": cites(r["answer"], q["sources"]) if q["answerable"] else None,
            "abstained": abstained(r["answer"]),
            "faithfulness": j["fidelidad"], "correctness": j["correctitud"], "judge_note": j["justificacion"],
        })
        print(f"  {q['id']} fid={j['fidelidad']} cor={j['correctitud']}", flush=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["answerable"]]
    out = [r for r in rows if not r["answerable"]]
    return {
        "faithfulness_mean": sum(r["faithfulness"] for r in rows) / len(rows),
        "correctness_mean": sum(r["correctness"] for r in ans) / len(ans),
        "citation_rate": sum(r["cites_expected"] for r in ans) / len(ans),
        "false_abstention_rate": sum(r["abstained"] for r in ans) / len(ans),
        "abstention_rate_out_of_scope": sum(r["abstained"] for r in out) / len(out),
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Generation evals (LLM-as-judge)")
    ap.add_argument("--strategy", choices=["structural", "fixed"], default="structural")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--reuse", action="store_true", help="reuse saved answers and judgements, no API calls")
    ap.add_argument("--with-recitals", action="store_true", help="also search the recitals (considerandos)")
    args = ap.parse_args()
    rows = run(args.strategy, args.k, args.reuse, () if args.with_recitals else DEFAULT_EXCLUDE)
    print()
    for r in rows:
        cite = {True: "cita", False: "NO cita", None: "-"}[r["cites_expected"]]
        print(f"{r['id']}  fid={r['faithfulness']} cor={r['correctness']}  {cite:<8} abstuvo={r['abstained']!s:<5} {r['judge_note'][:90]}")
    print()
    for name, value in summarize(rows).items():
        print(f"{name:>30}: {value:.3f}")


if __name__ == "__main__":
    main()
