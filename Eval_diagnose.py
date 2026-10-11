

"""Attribute end-to-end failures to retrieval or generation.

  retrieval miss          wrong answer AND the retrieved context lacked the answer
  generation problem      wrong answer even though the context had it
  unfaithful but correct  right answer, but it contains claims the context doesn't support
  ok                      none of the above

Usage: python eval_diagnose.py eval_results/rag_baseline.json [--threshold 0.7]
       python eval_diagnose.py eval_results/rag_baseline.json --show [--group "generation problem"]
--show prints the reference answer, the app's answer and the judge's reason for one group.
"""
import json
import sys

path = sys.argv[1]
def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


thr = float(opt("--threshold", 0.7))
CORRECT, RECALL, FAITH = "Correctness [GEval]", "Contextual Recall", "Faithfulness"

rows = json.load(open(path, encoding="utf-8"))["rows"]
groups = {"retrieval miss": [], "generation problem": [], "unfaithful but correct": [], "ok": []}
for r in rows:
    c, rc, f = (r[k]["score"] for k in (CORRECT, RECALL, FAITH))
    if None in (c, rc, f):
        continue
    if c < thr and rc < thr:
        groups["retrieval miss"].append((r, c, rc, f))
    elif c < thr:
        groups["generation problem"].append((r, c, rc, f))
    elif f < thr:
        groups["unfaithful but correct"].append((r, c, rc, f))
    else:
        groups["ok"].append((r, c, rc, f))

print(f"{sum(len(v) for v in groups.values())} questions, threshold {thr}\n")
for name, items in groups.items():
    print(f"{name}: {len(items)}")
    if name != "ok":
        for r, c, rc, f in sorted(items, key=lambda x: x[1]):
            print(f"   correct={c:.2f} recall={rc:.2f} faithful={f:.2f}  {r['question']}")
        print()

if "--show" in sys.argv:
    group = opt("--group", "generation problem")
    try:
        expected = {g["question"]: g["expected_output"]
                    for g in json.load(open(opt("--golden", "golden_set.json"), encoding="utf-8"))}
    except OSError:
        expected = {}
    print("=" * 70, f"\n{group.upper()}: reference vs app answer\n", "=" * 70, sep="")
    for r, c, rc, f in sorted(groups[group], key=lambda x: x[1]):
        print(f"\nQ: {r['question']}   (correct={c:.2f} recall={rc:.2f} faithful={f:.2f})")
        print(f"EXPECTED: {expected.get(r['question'], '(golden_set.json not found)')}")
        print(f"ANSWER:   {r['answer']}")
        print(f"JUDGE:    {r[CORRECT]['reason']}")