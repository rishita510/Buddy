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




"""Usage: python ingest.py "https://www.youtube.com/watch?v=VIDEO_ID" """
import sys
from dotenv import load_dotenv

load_dotenv()

from Utils import extract_video_id
from Transcript import fetch_transcript
from Chunk import chunk_transcript
from Store import store_chunks, video_already_ingested, delete_existing_chunks


def main():
    if len(sys.argv) != 2:
        print('Usage: python ingest.py "<youtube-url>"')
        sys.exit(1)

    url = sys.argv[1]
    video_id = extract_video_id(url)
    print(f"Video ID: {video_id}")

    if video_already_ingested(video_id):
        answer = input(
            f"Video {video_id} is already ingested. Re-ingest and replace it? [y/N]: "
        ).strip().lower()
        if answer != "y":
            print("Skipping re-ingest. You can chat with it right away:")
            print(f'  python chat.py {video_id}')
            return
        print("Deleting old chunks before re-ingesting...")
        delete_existing_chunks(video_id)

    print("Fetching transcript...")
    transcript_lines = fetch_transcript(video_id)
    print(f"Got {len(transcript_lines)} transcript lines.")

    print("Chunking...")
    chunks = chunk_transcript(transcript_lines)
    print(f"Created {len(chunks)} chunks.")

    print("Embedding + storing in Supabase (this calls OpenAI once per chunk)...")
    store_chunks(video_id, chunks)

    print(f"\nDone. Video {video_id} is ready to query.")
    print(f'Run: python chat.py {video_id}')


if __name__ == "__main__":
    main()