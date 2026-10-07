import re
import requests

_PATTERNS = [
    r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtu\.be/)([a-zA-Z0-9_-]{11})",
]

def extract_video_id(url: str) -> str:
    """Pulls the 11-character video ID out of any common YouTube URL shape."""
    for pattern in _PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract a video ID from: {url}")





def fetch_video_title(video_id: str) -> str | None:
    """Fetches a video's title via YouTube's public oEmbed endpoint — no API
    key required. Returns None if it fails (e.g. video is private/deleted),
    in which case the caller should fall back to showing the raw video_id."""
    try:
        resp = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("title")
    except Exception:
        return None