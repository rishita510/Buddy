# """Shared helpers for eval_retriever.py / eval_generator.py / eval_rag.py.

# Golden set (JSON list, see golden_set.example.json):
#   question, expected_output, golden_context (list of passages),
#   optional: video_id, answer_start / answer_end (seconds, enables hit@k + MRR)
# """
# import argparse
# import json
# import os

# os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
# from dotenv import load_dotenv

# load_dotenv()

# from deepeval.metrics import (
#     AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric,
#     ContextualRelevancyMetric, FaithfulnessMetric, GEval,
# )
# try:
#     from deepeval.test_case import SingleTurnParams as P
# except ImportError:  # older deepeval
#     from deepeval.test_case import LLMTestCaseParams as P

# JUDGE = os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini")  # LLM-as-judge model
# THRESHOLD = 0.7
# K = 5  # top-k chunks retrieved, same as the app


# def _m(cls, **kw):
#     return cls(model=JUDGE, threshold=THRESHOLD, async_mode=False, **kw)


# def retrieval_metrics():
#     return [_m(c, include_reason=True) for c in
#             (ContextualPrecisionMetric, ContextualRecallMetric, ContextualRelevancyMetric)]


# def generation_metrics():
#     return [
#         _m(FaithfulnessMetric, include_reason=True),
#         _m(AnswerRelevancyMetric, include_reason=True),
#         _m(GEval, name="Correctness",
#            criteria="Does the actual output convey the same facts as the expected output, "
#                     "without contradicting it or adding unsupported claims?",
#            evaluation_params=[P.ACTUAL_OUTPUT, P.EXPECTED_OUTPUT]),
#     ]


# def parse_args(desc):
#     p = argparse.ArgumentParser(description=desc)
#     p.add_argument("--golden", default="golden_set.json")
#     p.add_argument("--video", help="video_id for golden items that don't have their own")
#     p.add_argument("--limit", type=int, help="only the first N items (cheap dry run)")
#     p.add_argument("--tag", default="run", help="label for the results file, e.g. chunk150")
#     return p.parse_args()


# def load_golden(args):
#     with open(args.golden, encoding="utf-8") as f:
#         items = json.load(f)
#     for it in items:
#         it.setdefault("video_id", args.video)
#     return items[: args.limit] if args.limit else items


# def score(name, cases, metrics, tag, extra=None):
#     """Runs every metric on every case; prints mean / pass-rate; saves per-question detail."""
#     rows = []
#     for i, case in enumerate(cases, 1):
#         print(f"[{name}] {i}/{len(cases)}: {case.input[:60]}")
#         row = {"question": case.input, "answer": case.actual_output,
#                "context": case.retrieval_context}
#         for m in metrics:
#             try:
#                 m.measure(case)
#                 row[m.__name__] = {"score": m.score, "reason": getattr(m, "reason", None)}
#             except Exception as e:
#                 row[m.__name__] = {"score": None, "reason": f"error: {e}"}
#         rows.append(row)

#     summary = dict(extra or {})
#     for m in metrics:
#         vals = [r[m.__name__]["score"] for r in rows if r[m.__name__]["score"] is not None]
#         summary[m.__name__] = {
#             "mean": round(sum(vals) / len(vals), 3) if vals else None,
#             "pass_rate": round(sum(v >= THRESHOLD for v in vals) / len(vals), 3) if vals else None,
#             "n": len(vals),
#         }

#     os.makedirs("eval_results", exist_ok=True)
#     path = f"eval_results/{name}_{tag}.json"
#     with open(path, "w", encoding="utf-8") as f:
#         json.dump({"judge": JUDGE, "summary": summary, "rows": rows}, f, ensure_ascii=False, indent=2)
#     print(f"\n== {name} ({tag}) | judge={JUDGE} ==")
#     for k, v in summary.items():
#         print(f"{k:22} {v}")
#     print(f"details -> {path}")

"""Shared helpers for eval_retriever.py / eval_generator.py / eval_rag.py.

Golden set (JSON list, see golden_set.example.json):
  question, expected_output, golden_context (list of passages),
  optional: video_id, answer_ranges [[start_s, end_s], ...] (enables hit@k + MRR)
"""
import argparse
import json
import os

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
from dotenv import load_dotenv

load_dotenv()

from deepeval.metrics import (
    AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric,
    ContextualRelevancyMetric, FaithfulnessMetric, GEval,
)
try:
    from deepeval.test_case import SingleTurnParams as P
except ImportError:  # older deepeval
    from deepeval.test_case import LLMTestCaseParams as P

JUDGE = os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini")  # LLM-as-judge model
THRESHOLD = 0.7
K = 5  # top-k chunks retrieved, same as the app


def _m(cls, **kw):
    return cls(model=JUDGE, threshold=THRESHOLD, async_mode=False, **kw)


def retrieval_metrics():
    return [_m(c, include_reason=True) for c in
            (ContextualPrecisionMetric, ContextualRecallMetric, ContextualRelevancyMetric)]


def generation_metrics():
    return [
        _m(FaithfulnessMetric, include_reason=True),
        _m(AnswerRelevancyMetric, include_reason=True),
        _m(GEval, name="Correctness",
           criteria="Does the actual output convey the same facts as the expected output, "
                    "without contradicting it or adding unsupported claims?",
           evaluation_params=[P.ACTUAL_OUTPUT, P.EXPECTED_OUTPUT]),
    ]


def parse_args(desc):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("--golden", default="golden_set.json")
    p.add_argument("--video", help="video_id for golden items that don't have their own")
    p.add_argument("--limit", type=int, help="only the first N items (cheap dry run)")
    p.add_argument("--tag", default="run", help="label for the results file, e.g. chunk150")
    return p.parse_args()


def load_golden(args, need_video=False):
    with open(args.golden, encoding="utf-8") as f:
        items = json.load(f)
    for it in items:
        if not it.get("video_id"):
            it["video_id"] = args.video
    if need_video and any(not it["video_id"] for it in items):
        raise SystemExit("No video_id. Pass --video <bare 11-char YouTube id> "
                         "(or add video_id to the golden items).")
    return items[: args.limit] if args.limit else items


def require_chunks(chunks, it):
    """Retrieval always returns top-k for an ingested video, so empty means misconfig."""
    if not chunks:
        raise SystemExit(
            f"Retriever returned 0 chunks for video_id={it['video_id']!r}. Check that --video is the "
            "bare 11-char ID (no URL / &t=...) and that the video is ingested. "
            "Stopped before any judge calls.")


def score(name, cases, metrics, tag, extra=None):
    """Runs every metric on every case; prints mean / pass-rate; saves per-question detail."""
    rows = []
    for i, case in enumerate(cases, 1):
        print(f"[{name}] {i}/{len(cases)}: {case.input[:60]}")
        row = {"question": case.input, "answer": case.actual_output,
               "context": case.retrieval_context}
        for m in metrics:
            try:
                m.measure(case)
                row[m.__name__] = {"score": m.score, "reason": getattr(m, "reason", None)}
            except Exception as e:
                row[m.__name__] = {"score": None, "reason": f"error: {e}"}
        rows.append(row)

    summary = dict(extra or {})
    for m in metrics:
        vals = [r[m.__name__]["score"] for r in rows if r[m.__name__]["score"] is not None]
        summary[m.__name__] = {
            "mean": round(sum(vals) / len(vals), 3) if vals else None,
            "pass_rate": round(sum(v >= THRESHOLD for v in vals) / len(vals), 3) if vals else None,
            "n": len(vals),
        }

    os.makedirs("eval_results", exist_ok=True)
    path = f"eval_results/{name}_{tag}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"judge": JUDGE, "summary": summary, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"\n== {name} ({tag}) | judge={JUDGE} ==")
    for k, v in summary.items():
        print(f"{k:22} {v}")
    print(f"details -> {path}")