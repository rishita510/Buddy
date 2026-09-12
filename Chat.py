"""Interactive chat: run once, ask as many questions as you want about one video.

Usage: python chat.py VIDEO_ID
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from Store import answer_with_history


def main():
    if len(sys.argv) != 2:
        print("Usage: python chat.py VIDEO_ID")
        sys.exit(1)

    video_id = sys.argv[1]
    print(f"Chatting about video {video_id}. Type 'exit' or 'quit' to stop.\n")

    # Conversation history: list of {"role": "user"/"assistant", "content": str}
    # This is what makes follow-up questions work — each new question is sent
    # to the model along with everything asked/answered before it in this session.
    history = []

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            print("Bye!")
            break

        answer = answer_with_history(video_id, question, history)
        print(f"\nBot: {answer}\n")

        # Remember this exchange for the next question in this session
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()