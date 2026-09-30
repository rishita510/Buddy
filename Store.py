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







def answer_with_history(video_id: str, question: str, history: list[dict]) -> str:
    """Like answer_question(), but includes prior conversation turns so the
    model can resolve follow-ups like 'explain that more' or 'what about X instead'.

    Note: retrieval still runs fresh on just the CURRENT question's text — the
    RAG lookup itself doesn't "remember" past questions, only the final answer
    generation step does. This is fine for most follow-ups, but if a follow-up
    depends heavily on a totally different part of the video than the original
    question, retrieval may miss it. (A more advanced version would first ask
    the model to rewrite the follow-up into a standalone question before
    retrieving — worth doing later if you notice this happening.)
    """
    relevant_chunks = retrieve_relevant_chunks(video_id, question)

    context = "\n\n".join(
        f"[{_format_timestamp(c['start_time'])}] {c['content']}" for c in relevant_chunks
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You answer questions about a YouTube video using only the transcript "
                "excerpts provided. Each excerpt is tagged with its timestamp. Cite the "
                "relevant timestamp(s) in your answer. If the excerpts don't contain the "
                "answer, say so plainly instead of guessing. Use the earlier conversation "
                "to understand follow-up questions and pronouns like 'that' or 'it'."
            ),
        },
    ]

    # replay prior turns so the model has conversational context
    messages.extend(history)

    messages.append({
        "role": "user",
        "content": f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}",
    })

    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    return completion.choices[0].message.content



def video_already_ingested(video_id: str) -> bool:
    """Checks if this video already has chunks stored, so we don't re-embed
    and duplicate rows on a second ingest run."""
    result = supabase.table("chunks").select("id").eq("video_id", video_id).limit(1).execute()
    return len(result.data) > 0


def delete_existing_chunks(video_id: str) -> None:
    """Wipes previously stored chunks for a video — call this before
    re-ingesting if you want a clean re-embed (e.g. after changing chunk size)."""
    supabase.table("chunks").delete().eq("video_id", video_id).execute()


# --- Thread + message persistence ---
# These let a conversation survive across script restarts. A "thread" is one
# saved conversation about one video; "messages" are the individual turns in it.
from datetime import datetime, timezone


def create_thread(video_id: str, title: str = None) -> str:
    """Creates a new thread and returns its id."""
    result = supabase.table("threads").insert({
        "video_id": video_id,
        "title": title,
    }).execute()
    return result.data[0]["id"]


def list_threads(video_id: str) -> list[dict]:
    """Lists all saved threads for a video, most recently updated first."""
    result = (
        supabase.table("threads")
        .select("id, title, created_at, updated_at")
        .eq("video_id", video_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


def get_messages(thread_id: str) -> list[dict]:
    """Fetches a thread's message history in the {role, content} shape
    answer_with_history() expects."""
    result = (
        supabase.table("messages")
        .select("role, content")
        .eq("thread_id", thread_id)
        .order("created_at")
        .execute()
    )
    return result.data


def save_message(thread_id: str, role: str, content: str) -> None:
    """Saves one turn (either the user's question or the assistant's answer)."""
    supabase.table("messages").insert({
        "thread_id": thread_id,
        "role": role,
        "content": content,
    }).execute()
    # bump updated_at so list_threads() sorts recently-active threads first
    supabase.table("threads").update({
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", thread_id).execute()