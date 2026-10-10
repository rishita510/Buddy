"""Generator only: given the GOLDEN context (perfect retrieval), is the answer
faithful, relevant and correct? Retrieval can't affect these scores.
DeepEval: faithfulness, answer relevancy, correctness (GEval).

Tip: prefix golden passages with "[12:22] " to mimic the production prompt.
Usage: python eval_generator.py [--tag prompt_v2] [--limit 5]
"""
from Eval_common import generation_metrics, load_golden, parse_args, score
from Store import generate_answer
from deepeval.test_case import LLMTestCase

args = parse_args("Evaluate the generator only, using golden context.")
cases = []
for it in load_golden(args):
    ctx = it["golden_context"]
    cases.append(LLMTestCase(input=it["question"],
                             actual_output=generate_answer(it["question"], "\n\n".join(ctx)),
                             expected_output=it["expected_output"], retrieval_context=ctx))

score("generator", cases, generation_metrics(), args.tag)