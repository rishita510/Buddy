# """Usage: python src/ask.py VIDEO_ID "what does the speaker say about X?" """
import sys
from dotenv import load_dotenv

load_dotenv()

from Store import answer_question


def main():
    if len(sys.argv) != 3:
        print('Usage: python src/ask.py VIDEO_ID "your question"')
        sys.exit(1)

    video_id, question = sys.argv[1], sys.argv[2]
    print(f'Asking about video {video_id}: "{question}"\n')
    print(answer_question(video_id, question))


if __name__ == "__main__":
    main()