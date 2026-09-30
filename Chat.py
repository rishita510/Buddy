"""Interactive chat with PERSISTENT memory: your conversation is saved to
Supabase and will still be there next time you run this script.

Usage: python chat.py VIDEO_ID
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from Store import (
    answer_with_history,
    create_thread,
    list_threads,
    get_messages,
    save_message,
)


def pick_thread(video_id: str) -> str:
    """Shows existing threads for this video and lets you resume one,
    or start a new one."""
    threads = list_threads(video_id)

    if threads:
        print(f"\nExisting conversations about this video:")
        for i, t in enumerate(threads, 1):
            label = t["title"] or "(untitled)"
            print(f"  {i}. {label}  (last active: {t['updated_at']})")
        print(f"  {len(threads) + 1}. Start a new conversation")

        choice = input("\nPick a number: ").strip()
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(threads):
                return threads[choice_num - 1]["id"]
        except ValueError:
            pass
        # anything else (including the "new" number or invalid input) -> new thread

    title = input("Name this conversation (optional, press enter to skip): ").strip() or None
    return create_thread(video_id, title)


def main():
    if len(sys.argv) != 2:
        print("Usage: python chat.py VIDEO_ID")
        sys.exit(1)

    video_id = sys.argv[1]
    thread_id = pick_thread(video_id)

    # Load prior messages for this thread (empty list if it's brand new)
    history = get_messages(thread_id)

    print(f"\nChatting about video {video_id}. Type 'exit' or 'quit' to stop.\n")
    if history:
        print(f"(Resumed thread with {len(history)} previous messages.)\n")

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            print("Bye!")
            break

        answer = answer_with_history(video_id, question, history)
        print(f"\nBot: {answer}\n")

        # Update in-memory history for this session's follow-ups...
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

        # ...and persist both turns to Supabase so they survive a restart.
        save_message(thread_id, "user", question)
        save_message(thread_id, "assistant", answer)


if __name__ == "__main__":
    main()