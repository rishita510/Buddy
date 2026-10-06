import os
from openai import OpenAI
from supabase import create_client

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def embed_text(text: str) -> list[float]:
    res = openai_client.embeddings.create(model="text-embedding-3-small", input=text)
    return res.data[0].embedding


def translate_to_english(text: str) -> str:
    """Translates one transcript chunk to English using gpt-4o-mini.
 
    A domain glossary is included because these videos are ML/RAG tutorials,
    and generic translation can mishear phonetically-transcribed technical
    jargon as an unrelated real word (e.g. the Hindi transliteration of
    "augmentation" getting translated as "argumentation" — a real but
    completely different word). Giving the model the expected vocabulary
    up front makes it correct these instead of guessing phonetically.
    """
    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Translate the following transcript excerpt to English. "
                    "It may be in Hindi, Hinglish (English technical terms written "
                    "phonetically in Devanagari), or another language.\n\n"
                    "This is a tutorial about RAG (Retrieval-Augmented Generation) and "
                    "LangChain. Common technical terms you should expect and translate "
                    "accurately, even if the Devanagari transcription is phonetically "
                    "imperfect: retrieval, augmentation, generation, embedding, embedding "
                    "model, vector store, vector database, retriever, similarity search, "
                    "chunk, chunking, chunk size, text splitter, recursive character text "
                    "splitter, LLM, prompt, context, RAG architecture, RAG pipeline, "
                    "LangChain, chain, parallel chain, transcript, API, OpenAI.\n\n"
                    "If a word's phonetic transcription is ambiguous between a technical "
                    "term from this list and an unrelated real word (e.g. 'augmentation' "
                    "vs 'argumentation'), prefer the technical term given the ML/RAG context.\n\n"
                    "Output ONLY the translation, no commentary."
                ),
            },
            {"role": "user", "content": text},
        ],
    )
    return completion.choices[0].message.content


def store_chunks(video_id: str, chunks: list[dict]) -> None:
    """Translates each chunk to English, embeds the TRANSLATED version (so
    similarity search works reliably against English questions), and stores
    both the original text (for showing what was actually said) and the
    translation (used for retrieval and as LLM context)."""
    for chunk in chunks:
        content_en = translate_to_english(chunk["content"])
        embedding = embed_text(content_en)  # embed the translation, not the original
        result = supabase.table("chunks").insert({
            "video_id": video_id,
            "content": chunk["content"],       # original, for reference/display
            "content_en": content_en,          # translated, used for retrieval + context
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
 
    # Use content_en (translated) for the LLM's context, not the raw
    # transcript text — this is what retrieval was matched against, and
    # it's far more reliable for the model to reason over than Hinglish text.
    context = "\n\n".join(
        f"[{_format_timestamp(c['start_time'])}] {c['content_en']}" for c in relevant_chunks
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
            {
                "role": "user",
                "content": f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}",
            },
        ],
    )
 
    return completion.choices[0].message.content
 
 
def answer_with_history(video_id: str, question: str, history: list[dict]) -> str:
    relevant_chunks = retrieve_relevant_chunks(video_id, question)
 
    context = "\n\n".join(
        f"[{_format_timestamp(c['start_time'])}] {c['content_en']}" for c in relevant_chunks
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


# def create_thread(video_id: str, title: str = None) -> str:
#     """Creates a new thread and returns its id."""
#     result = supabase.table("threads").insert({
#         "video_id": video_id,
#         "title": title,
#     }).execute()
#     return result.data[0]["id"]


# def list_threads(video_id: str) -> list[dict]:
#     """Lists all saved threads for a video, most recently updated first."""
#     result = (
#         supabase.table("threads")
#         .select("id, title, created_at, updated_at")
#         .eq("video_id", video_id)
#         .order("updated_at", desc=True)
#         .execute()
#     )
#     return result.data


# def get_messages(thread_id: str) -> list[dict]:
#     """Fetches a thread's message history in the {role, content} shape
#     answer_with_history() expects."""
#     result = (
#         supabase.table("messages")
#         .select("role, content")
#         .eq("thread_id", thread_id)
#         .order("created_at")
#         .execute()
#     )
#     return result.data


# def save_message(thread_id: str, role: str, content: str) -> None:
#     """Saves one turn (either the user's question or the assistant's answer)."""
#     supabase.table("messages").insert({
#         "thread_id": thread_id,
#         "role": role,
#         "content": content,
#     }).execute()
#     # bump updated_at so list_threads() sorts recently-active threads first
#     supabase.table("threads").update({
#         "updated_at": datetime.now(timezone.utc).isoformat()
#     }).eq("id", thread_id).execute()
# --- Thread + message persistence (now scoped to a user) ---

def create_thread(video_id: str, user_id: str, title: str = None) -> str:
    """Creates a new thread owned by a specific user, returns its id."""
    result = supabase.table("threads").insert({
        "video_id": video_id,
        "user_id": user_id,
        "title": title,
    }).execute()
    return result.data[0]["id"]


def list_threads(video_id: str, user_id: str) -> list[dict]:
    """Lists a user's own saved threads for a video, most recently updated first.
    Filtering by user_id means User A never sees User B's conversations."""
    result = (
        supabase.table("threads")
        .select("id, title, created_at, updated_at")
        .eq("video_id", video_id)
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


def get_messages(thread_id: str) -> list[dict]:
    result = (
        supabase.table("messages")
        .select("role, content")
        .eq("thread_id", thread_id)
        .order("created_at")
        .execute()
    )
    return result.data


def save_message(thread_id: str, role: str, content: str) -> None:
    supabase.table("messages").insert({
        "thread_id": thread_id,
        "role": role,
        "content": content,
    }).execute()
    supabase.table("threads").update({
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", thread_id).execute()



def delete_thread(thread_id: str, user_id: str) -> None:
    """Deletes a thread (and all its messages, via cascade delete) — but only
    if it actually belongs to this user, so you can't delete someone else's
    thread by guessing an id."""
    supabase.table("threads").delete().eq("id", thread_id).eq("user_id", user_id).execute()