import os
from openai import OpenAI
from supabase import create_client

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def embed_text(text: str) -> list[float]:
    res = openai_client.embeddings.create(model="text-embedding-3-small", input=text)
    return res.data[0].embedding


def store_chunks(video_id: str, chunks: list[dict]) -> None:
    """Embeds every chunk and inserts it into Supabase. Runs sequentially —
    fine for a single video; batch this properly once you're ingesting many
    videos concurrently."""
    for chunk in chunks:
        embedding = embed_text(chunk["content"])
        result = supabase.table("chunks").insert({
            "video_id": video_id,
            "content": chunk["content"],
            "start_time": chunk["start_time"],
            "embedding": embedding,
        }).execute()
        if not result.data:
            raise RuntimeError(f"Supabase insert failed for a chunk of video {video_id}")


def retrieve_relevant_chunks(video_id: str, question: str, match_count: int = 5) -> list[dict]:
    query_embedding = embed_text(question)
    result = supabase.rpc("match_chunks", {
        "query_embedding": query_embedding,
        "match_video_id": video_id,
        "match_count": match_count,
    }).execute()
    return result.data


def _format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def answer_question(video_id: str, question: str) -> str:
    relevant_chunks = retrieve_relevant_chunks(video_id, question)

    context = "\n\n".join(
        f"[{_format_timestamp(c['start_time'])}] {c['content']}" for c in relevant_chunks
    )

    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You answer questions about a YouTube video using only the transcript "
                    "excerpts provided. Each excerpt is tagged with its timestamp. Cite the "
                    "relevant timestamp(s) in your answer. If the excerpts don't contain the "
                    "answer, say so plainly instead of guessing."
                ),
            },
            {"role": "user", "content": f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}"},
        ],
    )

    return completion.choices[0].message.content