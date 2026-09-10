# from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


# def fetch_transcript(video_id: str) -> list[dict]:
#     """Returns a list of {"text": str, "offset": float} where offset is in SECONDS.

#     youtube-transcript-api gives 'start' in seconds already, unlike the JS
#     package which uses ms — one less conversion to think about here.
#     """
#     try:
#         raw = YouTubeTranscriptApi.get_transcript(video_id)
#     except (TranscriptsDisabled, NoTranscriptFound) as e:
#         raise RuntimeError(
#             "NO_TRANSCRIPT: this video has no captions available. "
#             "Phase 3 will add a Whisper fallback for this case."
#         ) from e

#     return [{"text": entry["text"], "offset": entry["start"]} for entry in raw]

# from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# # Try these languages in order. Add more codes here if you test videos in
# # other languages — e.g. "es" for Spanish, "fr" for French.
# PREFERRED_LANGUAGES = ["en", "hi"]

# for hindi and english trancript
# def fetch_transcript(video_id: str) -> list[dict]:
#     """Returns a list of {"text": str, "offset": float} where offset is in SECONDS.

#     Tries PREFERRED_LANGUAGES first (manually created or auto-generated).
#     If none of those exist, falls back to whatever transcript IS available
#     for the video, in any language, rather than failing outright.
#     """
#     try:
#         transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
#     except (TranscriptsDisabled, NoTranscriptFound) as e:
#         raise RuntimeError(
#             "NO_TRANSCRIPT: this video has no captions available at all. "
#             "Phase 3 will add a Whisper fallback for this case."
#         ) from e

#     try:
#         transcript = transcript_list.find_transcript(PREFERRED_LANGUAGES)
#     except NoTranscriptFound:
#         # None of our preferred languages exist — just grab the first
#         # available transcript, whatever language it happens to be in.
#         available = list(transcript_list)
#         if not available:
#             raise RuntimeError(
#                 "NO_TRANSCRIPT: this video has no captions available at all. "
#                 "Phase 3 will add a Whisper fallback for this case."
#             )
#         transcript = available[0]
#         print(f"Note: no {PREFERRED_LANGUAGES} transcript found, "
#               f"using '{transcript.language}' ({transcript.language_code}) instead.")

#     raw = transcript.fetch()
#     return [{"text": entry["text"], "offset": entry["start"]} for entry in raw]


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