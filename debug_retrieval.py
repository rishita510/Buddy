"""Debug helper: shows exactly which chunks get retrieved for a question,
and their similarity scores — so you can see if the right chunk is being
found but ranked low, or not found at all.

Usage: python debug_retrieval.py VIDEO_ID "your question"
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from Store import embed_text, supabase


def main():
    if len(sys.argv) != 3:
        print('Usage: python debug_retrieval.py VIDEO_ID "your question"')
        sys.exit(1)

    video_id, question = sys.argv[1], sys.argv[2]

    query_embedding = embed_text(question)
    result = supabase.rpc("match_chunks", {
        "query_embedding": query_embedding,
        "match_video_id": video_id,
        "match_count": 10,  # grab more than the usual 5, to see further down the ranking
    }).execute()

    print(f"Question: {question}\n")
    print(f"Top {len(result.data)} chunks by similarity:\n")
    for i, c in enumerate(result.data, 1):
        mins, secs = divmod(int(c["start_time"]), 60)
        preview = c["content"][:150].replace("\n", " ")
        print(f"{i}. similarity={c['similarity']:.4f}  [{mins}:{secs:02d}]")
        print(f"   {preview}...\n")


if __name__ == "__main__":
    main()