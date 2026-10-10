# """Retriever only: are the right chunks retrieved, and ranked high?
# DeepEval: contextual precision / recall / relevancy.
# Plus free deterministic hit@k and MRR for items with answer_start/answer_end (seconds).

# Usage: python eval_retriever.py --video VIDEO_ID [--tag chunk150] [--limit 5]
# """
# from Eval_common import K, load_golden, parse_args, retrieval_metrics, score
# from Store import retrieve_relevant_chunks, supabase
# from deepeval.test_case import LLMTestCase

# OVERLAP_SLACK = 15  # s: a chunk runs slightly past the next chunk's start (overlap)
# _spans = {}


# def spans_for(video_id):
#     """chunk id -> (start, approx_end), derived from the stored chunks themselves."""
#     if video_id not in _spans:
#         rows = (supabase.table("chunks").select("id,start_time")
#                 .eq("video_id", video_id).order("start_time").execute().data)
#         _spans[video_id] = {
#             r["id"]: (r["start_time"],
#                       rows[i + 1]["start_time"] + OVERLAP_SLACK if i + 1 < len(rows) else float("inf"))
#             for i, r in enumerate(rows)
#         }
#     return _spans[video_id]


# args = parse_args("Evaluate the retriever only.")
# cases, ranks = [], []
# for it in load_golden(args):
#     chunks = retrieve_relevant_chunks(it["video_id"], it["question"], K)
#     cases.append(LLMTestCase(input=it["question"], expected_output=it["expected_output"],
#                              retrieval_context=[c["content_en"] for c in chunks]))
#     if it.get("answer_start") is not None and it.get("answer_end") is not None:
#         sp = spans_for(it["video_id"])
#         ranks.append(next((r for r, c in enumerate(chunks, 1)
#                            if sp[c["id"]][0] < it["answer_end"] and sp[c["id"]][1] > it["answer_start"]), None))

# extra = {}
# if ranks:
#     n = len(ranks)
#     extra = {f"hit@{k}": round(sum(r is not None and r <= k for r in ranks) / n, 3)
#              for k in (1, 3, 5) if k <= K}
#     extra["MRR"] = round(sum(1 / r for r in ranks if r) / n, 3)
#     extra["n_timestamped"] = n

# score("retriever", cases, retrieval_metrics(), args.tag, extra)


"""Retriever only: are the right chunks retrieved, and ranked high?
DeepEval: contextual precision / recall / relevancy.
Plus free deterministic hit@k and MRR for items with answer_ranges (seconds).

Usage: python eval_retriever.py --video VIDEO_ID [--tag chunk150] [--limit 5]
"""
from Eval_common import K, load_golden, parse_args, require_chunks, retrieval_metrics, score
from Store import retrieve_relevant_chunks, supabase
from deepeval.test_case import LLMTestCase

OVERLAP_SLACK = 15  # s: a chunk runs slightly past the next chunk's start (overlap)
_spans = {}


def spans_for(video_id):
    """chunk id -> (start, approx_end), derived from the stored chunks themselves."""
    if video_id not in _spans:
        rows = (supabase.table("chunks").select("id,start_time")
                .eq("video_id", video_id).order("start_time").execute().data)
        _spans[video_id] = {
            r["id"]: (r["start_time"],
                      rows[i + 1]["start_time"] + OVERLAP_SLACK if i + 1 < len(rows) else float("inf"))
            for i, r in enumerate(rows)
        }
    return _spans[video_id]


args = parse_args("Evaluate the retriever only.")
cases, ranks = [], []
for it in load_golden(args, need_video=True):
    chunks = retrieve_relevant_chunks(it["video_id"], it["question"], K)
    require_chunks(chunks, it)
    cases.append(LLMTestCase(input=it["question"], expected_output=it["expected_output"],
                             retrieval_context=[c["content_en"] for c in chunks]))
    rg = it.get("answer_ranges") or (
        [[it["answer_start"], it["answer_end"]]]
        if it.get("answer_start") is not None and it.get("answer_end") is not None else [])
    if rg:
        sp = spans_for(it["video_id"])
        ranks.append(next((r for r, c in enumerate(chunks, 1)
                           if any(sp[c["id"]][0] < e and sp[c["id"]][1] > s for s, e in rg)), None))

extra = {}
if ranks:
    n = len(ranks)
    extra = {f"hit@{k}": round(sum(r is not None and r <= k for r in ranks) / n, 3)
             for k in (1, 3, 5) if k <= K}
    extra["MRR"] = round(sum(1 / r for r in ranks if r) / n, 3)
    extra["n_timestamped"] = n

score("retriever", cases, retrieval_metrics(), args.tag, extra)