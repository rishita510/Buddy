"""Show which questions scored below the threshold, and per-category means.

Usage: python eval_failures.py eval_results/retriever_baseline.json "Contextual Recall"
       [--golden golden_set.json] [--threshold 0.7]
"""
import json
import sys
from collections import defaultdict

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = {sys.argv[i]: sys.argv[i + 1] for i in range(1, len(sys.argv) - 1) if sys.argv[i].startswith("--")}
path, metric = args[0], args[1]
thr = float(opt.get("--threshold", 0.7))

rows = json.load(open(path, encoding="utf-8"))["rows"]
try:
    cat = {g["question"]: g.get("category", "?") for g in json.load(open(opt.get("--golden", "golden_set.json"), encoding="utf-8"))}
except OSError:
    cat = {}

by_cat = defaultdict(list)
fails = []
for r in rows:
    s = r[metric]["score"]
    if s is None:
        continue
    by_cat[cat.get(r["question"], "all")].append(s)
    if s < thr:
        fails.append((s, r))

print(f"{metric}: {len(fails)}/{len(rows)} below {thr}\n")
for s, r in sorted(fails, key=lambda x: x[0]):
    print(f"{s:.2f}  {r['question']}\n      {r[metric]['reason']}\n")
if len(by_cat) > 1:
    print("Mean by category (lowest first):")
    for c, v in sorted(by_cat.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        print(f"  {sum(v) / len(v):.2f}  {c}  (n={len(v)})")