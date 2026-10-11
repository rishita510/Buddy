


#for all language transcript

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# v1.x of this library changed to an instance-based API (YouTubeTranscriptApi().fetch(...)
# instead of the old static YouTubeTranscriptApi.get_transcript(...)). Older versions
# (pre-1.1.0) also had a bug that threw "no element found: line 1, column 0" on many
# videos — if you hit that error, `pip install --upgrade youtube-transcript-api` first.
_ytt_api = YouTubeTranscriptApi()


def fetch_transcript(video_id: str) -> list[dict]:
    """Returns a list of {"text": str, "offset": float} where offset is in SECONDS.

    Works for ANY language — no preference list. Just grabs whichever
    transcript YouTube has for this video (manually created preferred
    over auto-generated, if both exist), and uses it as-is.
    """
    try:
        transcript_list = _ytt_api.list(video_id)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise RuntimeError(
            "NO_TRANSCRIPT: this video has no captions available at all. "
            "Phase 3 will add a Whisper fallback for this case."
        ) from e

    available = list(transcript_list)
    if not available:
        raise RuntimeError(
            "NO_TRANSCRIPT: this video has no captions available at all. "
            "Phase 3 will add a Whisper fallback for this case."
        )

    # Prefer a manually created transcript (more accurate) over an
    # auto-generated one, if the video happens to have both. Otherwise
    # just take the first one available, whatever language it's in.
    manual = [t for t in available if not t.is_generated]
    transcript = manual[0] if manual else available[0]

    print(f"Using transcript: '{transcript.language}' ({transcript.language_code}), "
          f"{'auto-generated' if transcript.is_generated else 'manually created'}")

    fetched = transcript.fetch()  # returns a FetchedTranscript object
    return [{"text": s.text, "offset": s.start} for s in fetched]