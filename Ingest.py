


"""ADMIN CLI for ingesting videos.

Usage:
  python ingest.py "<youtube-url>"           ingest if not already ingested
  python ingest.py "<youtube-url>" --force   rebuild a video from scratch

--force is the ONLY way to wipe and rebuild a video that's already 'ready'.
It is deliberately not available in the app: chunks are shared by all users,
so one user rebuilding a video would break everyone else's chats on it.
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from Utils import extract_video_id
from Pipeline import ingest_video
from Store import mark_video_failed


def main():
    force = "--force" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 1:
        print('Usage: python ingest.py "<youtube-url>" [--force]')
        sys.exit(1)

    video_id = extract_video_id(args[0])
    print(f"Video ID: {video_id}")

    if force:
        print("--force: marking video for rebuild (existing chunks will be wiped)...")
        mark_video_failed(video_id)  # makes the pipeline re-claim it and rebuild

    result = ingest_video(video_id)

    if result == "already_ready":
        print("Already ingested. Use --force to rebuild it from scratch.")
    elif result == "busy":
        print("Another ingestion of this video is in progress. Try again shortly.")
    else:
        print(f"\nDone. Video {video_id} is ready.")


if __name__ == "__main__":
    main()