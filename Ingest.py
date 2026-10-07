# """Usage: python src/ingest.py "https://www.youtube.com/watch?v=VIDEO_ID" """
# import sys
# from dotenv import load_dotenv

# load_dotenv()

# from Utils import extract_video_id
# from Transcript import fetch_transcript
# from Chunk import chunk_transcript
# from Store import store_chunks


# def main():
#     if len(sys.argv) != 2:
#         print('Usage: python src/ingest.py "<youtube-url>"')
#         sys.exit(1)

#     url = sys.argv[1]
#     video_id = extract_video_id(url)
#     print(f"Video ID: {video_id}")

#     print("Fetching transcript...")
#     transcript_lines = fetch_transcript(video_id)
#     print(f"Got {len(transcript_lines)} transcript lines.")

#     print("Chunking...")
#     chunks = chunk_transcript(transcript_lines)
#     print(f"Created {len(chunks)} chunks.")

#     print("Embedding + storing in Supabase (this calls OpenAI once per chunk)...")
#     store_chunks(video_id, chunks)

#     print(f"\nDone. Video {video_id} is ready to query.")
#     print(f'Run: python src/ask.py {video_id} "your question here"')


# if __name__ == "__main__":
#     main()




# """Usage: python ingest.py "https://www.youtube.com/watch?v=VIDEO_ID" """
# import sys
# from dotenv import load_dotenv

# load_dotenv()

# from Utils import extract_video_id
# from Transcript import fetch_transcript
# from Chunk import chunk_transcript
# from Store import store_chunks, video_already_ingested, delete_existing_chunks


# def main():
#     if len(sys.argv) != 2:
#         print('Usage: python ingest.py "<youtube-url>"')
#         sys.exit(1)

#     url = sys.argv[1]
#     video_id = extract_video_id(url)
#     print(f"Video ID: {video_id}")

#     if video_already_ingested(video_id):
#         answer = input(
#             f"Video {video_id} is already ingested. Re-ingest and replace it? [y/N]: "
#         ).strip().lower()
#         if answer != "y":
#             print("Skipping re-ingest. You can chat with it right away:")
#             print(f'  python chat.py {video_id}')
#             return
#         print("Deleting old chunks before re-ingesting...")
#         delete_existing_chunks(video_id)

#     print("Fetching transcript...")
#     transcript_lines = fetch_transcript(video_id)
#     print(f"Got {len(transcript_lines)} transcript lines.")

#     print("Chunking...")
#     chunks = chunk_transcript(transcript_lines)
#     print(f"Created {len(chunks)} chunks.")

#     print("Embedding + storing in Supabase (this calls OpenAI once per chunk)...")
#     store_chunks(video_id, chunks)

#     print(f"\nDone. Video {video_id} is ready to query.")
#     print(f'Run: python chat.py {video_id}')


# if __name__ == "__main__":
#     main()


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