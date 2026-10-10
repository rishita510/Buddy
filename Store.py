import os
from openai import OpenAI
from supabase import create_client
from datetime import datetime, timezone, timedelta
from postgrest.exceptions import APIError

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def embed_text(text: str) -> list[float]:
    res = openai_client.embeddings.create(model="text-embedding-3-small", input=text)
    return res.data[0].embedding


# def translate_to_english(text: str) -> str:
#     """Translates one transcript chunk to English using gpt-4o-mini.
 
#     A domain glossary is included because these videos are ML/RAG tutorials,
#     and generic translation can mishear phonetically-transcribed technical
#     jargon as an unrelated real word (e.g. the Hindi transliteration of
#     "augmentation" getting translated as "argumentation" — a real but
#     completely different word). Giving the model the expected vocabulary
#     up front makes it correct these instead of guessing phonetically.
#     """
#     completion = openai_client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {
#                 "role": "system",
#                 "content": (
#                     "Translate the following transcript excerpt to English. "
#                     "It may be in Hindi, Hinglish (English technical terms written "
#                     "phonetically in Devanagari), or another language.\n\n"
#                     "This is a tutorial about RAG (Retrieval-Augmented Generation) and "
#                     "LangChain. Common technical terms you should expect and translate "
#                     "accurately, even if the Devanagari transcription is phonetically "
#                     "imperfect: retrieval, augmentation, generation, embedding, embedding "
#                     "model, vector store, vector database, retriever, similarity search, "
#                     "chunk, chunking, chunk size, text splitter, recursive character text "
#                     "splitter, LLM, prompt, context, RAG architecture, RAG pipeline, "
#                     "LangChain, chain, parallel chain, transcript, API, OpenAI.\n\n"
#                     "If a word's phonetic transcription is ambiguous between a technical "
#                     "term from this list and an unrelated real word (e.g. 'augmentation' "
#                     "vs 'argumentation'), prefer the technical term given the ML/RAG context.\n\n"
#                     "Output ONLY the translation, no commentary."
#                 ),
#             },
#             {"role": "user", "content": text},
#         ],
#     )
#     return completion.choices[0].message.content
def translate_to_english(text: str) -> str:
    """Translates one transcript chunk to English using gpt-4o-mini.

    Explicitly handles the case where the chunk is ALREADY English — earlier
    versions of this prompt included a Hindi example for RAG vocabulary
    (e.g. 'टेक्स्ट स्प्लिटर' -> 'text splitter'), which could confuse the
    model into "translating" already-English text INTO Hindi on some chunks,
    since it had Devanagari text to pattern-match against. This version
    states the direction unambiguously and separates the glossary from
    any literal non-English example text.
    """
    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You translate transcript excerpts INTO English. The output must "
                    "ALWAYS be English, never any other language.\n\n"
                    "If the input is already entirely in English, output it completely "
                    "unchanged — do not alter, paraphrase, or translate it into any "
                    "other language under any circumstances.\n\n"
                    "If the input is in Hindi, or Hinglish (English technical terms "
                    "written phonetically in Devanagari script), translate it to natural "
                    "English.\n\n"
                    "This is a tutorial about RAG (Retrieval-Augmented Generation) and "
                    "LangChain. When translating, use these exact English technical terms "
                    "wherever the content refers to them, even if the source phonetics are "
                    "imperfect: retrieval, augmentation, generation, embedding, embedding "
                    "model, vector store, vector database, retriever, similarity search, "
                    "chunk, chunking, chunk size, text splitter, recursive character text "
                    "splitter, LLM, prompt, context, RAG architecture, RAG pipeline, "
                    "LangChain, chain, parallel chain, transcript, API, OpenAI.\n\n"
                    "Output ONLY the resulting English text, no commentary, no language "
                    "other than English under any circumstances."
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


# def answer_question(video_id: str, question: str) -> str:
#     relevant_chunks = retrieve_relevant_chunks(video_id, question)
 
#     # Use content_en (translated) for the LLM's context, not the raw
#     # transcript text — this is what retrieval was matched against, and
#     # it's far more reliable for the model to reason over than Hinglish text.
#     context = "\n\n".join(
#         f"[{_format_timestamp(c['start_time'])}] {c['content_en']}" for c in relevant_chunks
#     )
 
#     completion = openai_client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {
#                 "role": "system",
#                 "content": (
#                     "You answer questions about a YouTube video using only the transcript "
#                     "excerpts provided. Each excerpt is tagged with its timestamp. Cite the "
#                     "relevant timestamp(s) in your answer. If the excerpts don't contain the "
#                     "answer, say so plainly instead of guessing."
#                 ),
#             },
#             {
#                 "role": "user",
#                 "content": f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}",
#             },
#         ],
#     )
 
#     return completion.choices[0].message.content
 
 
# def answer_with_history(video_id: str, question: str, history: list[dict]) -> str:
#     relevant_chunks = retrieve_relevant_chunks(video_id, question)
 
#     context = "\n\n".join(
#         f"[{_format_timestamp(c['start_time'])}] {c['content_en']}" for c in relevant_chunks
#     )
 
#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You answer questions about a YouTube video using only the transcript "
#                 "excerpts provided. Each excerpt is tagged with its timestamp. Cite the "
#                 "relevant timestamp(s) in your answer. If the excerpts don't contain the "
#                 "answer, say so plainly instead of guessing. Use the earlier conversation "
#                 "to understand follow-up questions and pronouns like 'that' or 'it'."
#             ),
#         },
#     ]
#     messages.extend(history)
#     messages.append({
#         "role": "user",
#         "content": f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}",
#     })
 
#     completion = openai_client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=messages,
#     )
 
#     return completion.choices[0].message.content


# REPLACE answer_question and answer_with_history in Store.py with this block.
# Behaviour is unchanged; generation is split out so it can be evaluated alone,
# and rag_answer returns the retrieved chunks so the end-to-end eval can score them.

def _build_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{_format_timestamp(c['start_time'])}] {c['content_en']}" for c in chunks
    )


def generate_answer(question: str, context: str, history: list[dict] = None) -> str:
    """Generation only: answer from the given context."""
    messages = [{
        "role": "system",
        "content": (
            "You answer questions about a YouTube video using only the transcript "
            "excerpts provided. Each excerpt is tagged with its timestamp. Cite the "
            "relevant timestamp(s) in your answer. If the excerpts don't contain the "
            "answer, say so plainly instead of guessing. Use the earlier conversation "
            "to understand follow-up questions and pronouns like 'that' or 'it'."
        ),
    }]
    messages.extend(history or [])
    messages.append({
        "role": "user",
        "content": f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}",
    })
    completion = openai_client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    return completion.choices[0].message.content


def rag_answer(video_id: str, question: str, history: list[dict] = None, k: int = 5):
    """Retrieve + generate. Returns (answer, retrieved_chunks)."""
    chunks = retrieve_relevant_chunks(video_id, question, k)
    return generate_answer(question, _build_context(chunks), history), chunks


def answer_question(video_id: str, question: str) -> str:
    return rag_answer(video_id, question)[0]


def answer_with_history(video_id: str, question: str, history: list[dict]) -> str:
    return rag_answer(video_id, question, history)[0]






# def video_already_ingested(video_id: str) -> bool:
#     """Checks if this video already has chunks stored, so we don't re-embed
#     and duplicate rows on a second ingest run."""
#     result = supabase.table("chunks").select("id").eq("video_id", video_id).limit(1).execute()
#     return len(result.data) > 0


# def delete_existing_chunks(video_id: str) -> None:
#     """Wipes previously stored chunks for a video — call this before
#     re-ingesting if you want a clean re-embed (e.g. after changing chunk size)."""
#     supabase.table("chunks").delete().eq("video_id", video_id).execute()


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


# def get_messages(thread_id: str) -> list[dict]:
#     result = (
#         supabase.table("messages")
#         .select("role, content")
#         .eq("thread_id", thread_id)
#         .order("created_at")
#         .execute()
#     )
#     return result.data


# def save_message(thread_id: str, role: str, content: str) -> None:
#     supabase.table("messages").insert({
#         "thread_id": thread_id,
#         "role": role,
#         "content": content,
#     }).execute()
#     supabase.table("threads").update({
#         "updated_at": datetime.now(timezone.utc).isoformat()
#     }).eq("id", thread_id).execute()

STALE_AFTER_MINUTES = 10  # a 'processing' video untouched this long is assumed crashed
 
 
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
 
 
# ---------- Fix 1: ownership checks on messages ----------
 
def get_messages(thread_id: str, user_id: str) -> list[dict]:
    """Returns a thread's messages, but only if the thread belongs to user_id."""
    owned = (
        supabase.table("threads").select("id")
        .eq("id", thread_id).eq("user_id", user_id).limit(1).execute()
    )
    if not owned.data:
        raise PermissionError("Thread not found or not owned by this user.")
 
    result = (
        supabase.table("messages").select("role, content")
        .eq("thread_id", thread_id).order("created_at").execute()
    )
    return result.data
 
 
def save_message(thread_id: str, user_id: str, role: str, content: str) -> None:
    """Saves a message, but only into a thread owned by user_id.
 
    The update on `threads` (bumping updated_at) doubles as the ownership
    check: it only matches a row if BOTH the id and the owner match."""
    touched = (
        supabase.table("threads").update({"updated_at": _now_iso()})
        .eq("id", thread_id).eq("user_id", user_id).execute()
    )
    if not touched.data:
        raise PermissionError("Thread not found or not owned by this user.")
 
    supabase.table("messages").insert({
        "thread_id": thread_id,
        "role": role,
        "content": content,
    }).execute()
 
 
# ---------- Fix 2: ingestion status ----------
 
def claim_video_for_ingestion(video_id: str) -> str:
    """Decides, atomically, who gets to ingest a video.
 
    Returns:
      'ready'   - already fully ingested, nothing to do
      'busy'    - another ingestion is in progress right now
      'claimed' - this caller now owns ingestion and must finish it with
                  mark_video_ready() or mark_video_failed()
 
    Atomicity: the videos primary key means only one INSERT can succeed, and
    the takeover UPDATEs below only match rows in the exact state we expect,
    so two simultaneous callers can never both get 'claimed'.
    """
    try:
        supabase.table("videos").insert({
            "id": video_id,
            "status": "processing",
            "status_updated_at": _now_iso(),
        }).execute()
    except APIError as e:
        if e.code != "23505":  # 23505 = duplicate key: someone already has a row
            raise
    else:
        delete_existing_chunks(video_id)  # clear any leftovers from before status existed
        return "claimed"
 
    row = supabase.table("videos").select("status").eq("id", video_id).limit(1).execute().data[0]
    if row["status"] == "ready":
        return "ready"
 
    # Previous attempt failed -> take over.
    taken = (
        supabase.table("videos")
        .update({"status": "processing", "status_updated_at": _now_iso()})
        .eq("id", video_id).eq("status", "failed").execute()
    )
    # Previous attempt is 'processing' but silent for too long (crashed, tab closed) -> take over.
    if not taken.data:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=STALE_AFTER_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
        taken = (
            supabase.table("videos")
            .update({"status": "processing", "status_updated_at": _now_iso()})
            .eq("id", video_id).eq("status", "processing").lt("status_updated_at", cutoff).execute()
        )
 
    if taken.data:
        delete_existing_chunks(video_id)  # safe: nobody can chat on a video that isn't 'ready'
        return "claimed"
    return "busy"
 
 
def heartbeat_video(video_id: str) -> None:
    """Tells everyone 'I'm still working on this' so a long ingestion isn't
    mistaken for a crashed one."""
    supabase.table("videos").update({"status_updated_at": _now_iso()}).eq("id", video_id).execute()
 
 
def mark_video_ready(video_id: str, title: str = None) -> None:
    values = {"status": "ready", "status_updated_at": _now_iso()}
    if title:
        values["title"] = title
    supabase.table("videos").update(values).eq("id", video_id).execute()
 
 
def mark_video_failed(video_id: str) -> None:
    supabase.table("videos").update(
        {"status": "failed", "status_updated_at": _now_iso()}
    ).eq("id", video_id).execute()
 
 
# ---------- Fix 3: deletion is internal/admin only ----------
 
def delete_existing_chunks(video_id: str) -> None:
    """INTERNAL / ADMIN ONLY. Never call this from a user action.
 
    Chunks for a video are shared by every user, so deleting them breaks
    everyone's chats on that video. It is only safe when the video is NOT
    'ready' (called by claim_video_for_ingestion after it wins the claim)."""
    supabase.table("chunks").delete().eq("video_id", video_id).execute()
 



def delete_thread(thread_id: str, user_id: str) -> None:
    """Deletes a thread (and all its messages, via cascade delete) — but only
    if it actually belongs to this user, so you can't delete someone else's
    thread by guessing an id."""
    supabase.table("threads").delete().eq("id", thread_id).eq("user_id", user_id).execute()



def upsert_video(video_id: str, title: str = None) -> None:
    """Saves/updates a video's title. Safe to call every time a video is
    ingested, even if it already exists."""
    supabase.table("videos").upsert({"id": video_id, "title": title}).execute()


def get_video_title(video_id: str) -> str:
    """Returns the stored title for a video, or the raw id if unknown."""
    result = supabase.table("videos").select("title").eq("id", video_id).limit(1).execute()
    if result.data and result.data[0]["title"]:
        return result.data[0]["title"]
    return video_id


def list_all_threads(user_id: str) -> list[dict]:
    """Lists ALL of a user's threads across every video, most recently
    active first — this is what powers a ChatGPT-style sidebar where you
    can jump into any past conversation without re-loading its video first."""
    threads_result = (
        supabase.table("threads")
        .select("id, video_id, title, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    threads = threads_result.data
    if not threads:
        return []

    # fetch titles for every video these threads belong to, in one query
    video_ids = list({t["video_id"] for t in threads})
    videos_result = (
        supabase.table("videos").select("id, title").in_("id", video_ids).execute()
    )
    titles_by_id = {v["id"]: v["title"] for v in videos_result.data}

    for t in threads:
        t["video_title"] = titles_by_id.get(t["video_id"]) or t["video_id"]

    return threads