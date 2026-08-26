"""Groups raw transcript lines into ~WORDS_PER_CHUNK-word chunks, each tagged
with the timestamp (in seconds) of its FIRST word — that's what lets you
later show "this answer comes from 4:32 in the video."

Word count is a rough stand-in for token count (~0.75 tokens/word), which
is plenty accurate for chunking purposes. Don't reach for a tokenizer here.
"""

WORDS_PER_CHUNK = 500
OVERLAP_WORDS = 50  # small overlap so we don't split a thought exactly at a chunk boundary


def chunk_transcript(transcript_lines: list[dict]) -> list[dict]:
    # Flatten to one (word, offset) pair per word so every word remembers
    # exactly when it was spoken — this is what keeps start_time accurate
    # across the overlap-slicing below, instead of freezing on the first chunk's time.
    words = []
    for line in transcript_lines:
        for word in line["text"].split():
            words.append((word, line["offset"]))

    chunks = []
    current: list[tuple[str, float]] = []

    for word, offset in words:
        current.append((word, offset))
        if len(current) >= WORDS_PER_CHUNK:
            chunks.append({
                "content": " ".join(w for w, _ in current),
                "start_time": current[0][1],
            })
            current = current[-OVERLAP_WORDS:]

    if current:
        chunks.append({
            "content": " ".join(w for w, _ in current),
            "start_time": current[0][1],
        })

    return chunks