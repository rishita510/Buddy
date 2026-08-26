from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


def fetch_transcript(video_id: str) -> list[dict]:
    """Returns a list of {"text": str, "offset": float} where offset is in SECONDS.

    youtube-transcript-api gives 'start' in seconds already, unlike the JS
    package which uses ms — one less conversion to think about here.
    """
    try:
        raw = YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise RuntimeError(
            "NO_TRANSCRIPT: this video has no captions available. "
            "Phase 3 will add a Whisper fallback for this case."
        ) from e

    return [{"text": entry["text"], "offset": entry["start"]} for entry in raw]