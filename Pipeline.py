"""One ingestion flow, used by BOTH the Streamlit app and the admin CLI,
so the status/claim rules can never differ between them."""
from Utils import fetch_video_title
from Transcript import fetch_transcript
from Chunk import chunk_transcript
from Store import (
    store_chunks,
    claim_video_for_ingestion,
    heartbeat_video,
    mark_video_ready,
    mark_video_failed,
)

BATCH_SIZE = 10  # chunks per batch; a heartbeat is sent after each batch


def ingest_video(video_id: str, progress=print) -> str:
    """Returns:
      'already_ready' - video was already fully ingested, nothing done
      'ingested'      - this call ingested it successfully
      'busy'          - someone else is ingesting it right now
    Raises on failure, after marking the video 'failed' so it can be retried.
    """
    state = claim_video_for_ingestion(video_id)
    if state == "ready":
        return "already_ready"
    if state == "busy":
        return "busy"

    try:
        progress("Fetching transcript...")
        lines = fetch_transcript(video_id)

        progress("Chunking...")
        chunks = chunk_transcript(lines)

        total = len(chunks)
        for i in range(0, total, BATCH_SIZE):
            store_chunks(video_id, chunks[i:i + BATCH_SIZE])
            heartbeat_video(video_id)
            progress(f"Embedded {min(i + BATCH_SIZE, total)} / {total} chunks")
    except Exception:
        mark_video_failed(video_id)
        raise

    mark_video_ready(video_id, fetch_video_title(video_id))
    return "ingested"