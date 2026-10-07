

# """Streamlit frontend for the YouTube RAG chatbot.

# Run with: streamlit run app.py
# """
# import streamlit as st
# from dotenv import load_dotenv

# load_dotenv()

# from Auth import sign_up, sign_in
# from Utils import extract_video_id, fetch_video_title
# from Transcript import fetch_transcript
# from Chunk import chunk_transcript
# from Store import (
#     store_chunks,
#     video_already_ingested,
#     delete_existing_chunks,
#     upsert_video,
#     create_thread,
#     list_threads,
#     list_all_threads,
#     delete_thread,
#     get_messages,
#     answer_with_history,
#     save_message,
# )

# st.set_page_config(page_title="YouTube RAG Chat", layout="wide")

# if "user" not in st.session_state:
#     st.session_state.user = None
# if "video_id" not in st.session_state:
#     st.session_state.video_id = None
# if "thread_id" not in st.session_state:
#     st.session_state.thread_id = None
# if "messages" not in st.session_state:
#     st.session_state.messages = []


# def show_auth_screen():
#     st.title("YouTube RAG Chat")
#     tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

#     with tab_login:
#         email = st.text_input("Email", key="login_email")
#         password = st.text_input("Password", type="password", key="login_password")
#         if st.button("Log in"):
#             try:
#                 user = sign_in(email, password)
#                 st.session_state.user = user
#                 st.rerun()
#             except Exception as e:
#                 st.error(f"Login failed: {e}")

#     with tab_signup:
#         email = st.text_input("Email", key="signup_email")
#         password = st.text_input("Password", type="password", key="signup_password")
#         if st.button("Sign up"):
#             try:
#                 user = sign_up(email, password)
#                 st.session_state.user = user
#                 st.success("Account created — you're logged in.")
#                 st.rerun()
#             except Exception as e:
#                 st.error(f"Sign up failed: {e}")


# def ingest_video(url: str) -> str:
#     video_id = extract_video_id(url)

#     if not video_already_ingested(video_id):
#         with st.spinner("Fetching transcript..."):
#             transcript_lines = fetch_transcript(video_id)
#         with st.spinner("Chunking..."):
#             chunks = chunk_transcript(transcript_lines)
#         with st.spinner(f"Embedding + storing {len(chunks)} chunks..."):
#             store_chunks(video_id, chunks)
#         st.success("Video ready to chat about.")
#     else:
#         st.info("This video is already ingested — ready to chat.")

#     # always (re)save the title, cheap and keeps it fresh
#     title = fetch_video_title(video_id)
#     upsert_video(video_id, title)

#     return video_id


# def open_thread(video_id: str, thread_id: str):
#     st.session_state.video_id = video_id
#     st.session_state.thread_id = thread_id
#     st.session_state.messages = get_messages(thread_id)
#     st.rerun()


# def show_chat_app():
#     user = st.session_state.user

#     with st.sidebar:
#         st.write(f"Logged in as **{user['email']}**")
#         if st.button("Log out"):
#             st.session_state.user = None
#             st.session_state.video_id = None
#             st.session_state.thread_id = None
#             st.session_state.messages = []
#             st.rerun()

#         st.divider()
#         st.subheader("Load a video")
#         url = st.text_input("YouTube URL")
#         if st.button("Ingest video") and url:
#             video_id = ingest_video(url)
#             st.session_state.video_id = video_id
#             st.session_state.thread_id = None
#             st.session_state.messages = []
#             st.rerun()

#         # --- Threads for the CURRENTLY loaded video ---
#         if st.session_state.video_id:
#             st.divider()
#             st.subheader("This video's conversations")
#             threads = list_threads(st.session_state.video_id, user["id"])

#             for t in threads:
#                 label = t["title"] or "(untitled)"
#                 col1, col2 = st.columns([4, 1])
#                 with col1:
#                     if st.button(label, key=f"thread_{t['id']}"):
#                         open_thread(st.session_state.video_id, t["id"])
#                 with col2:
#                     if st.button("🗑️", key=f"delete_{t['id']}"):
#                         delete_thread(t["id"], user["id"])
#                         if st.session_state.thread_id == t["id"]:
#                             st.session_state.thread_id = None
#                             st.session_state.messages = []
#                         st.rerun()

#             new_title = st.text_input("New conversation name", key="new_thread_title")
#             if st.button("Start new conversation"):
#                 thread_id = create_thread(st.session_state.video_id, user["id"], new_title or None)
#                 open_thread(st.session_state.video_id, thread_id)

#         # --- ALL conversations across every video, ChatGPT-sidebar style ---
#         st.divider()
#         st.subheader("All your conversations")
#         all_threads = list_all_threads(user["id"])
#         if not all_threads:
#             st.caption("No conversations yet.")
#         for t in all_threads:
#             label = f"{t['video_title']}"
#             sublabel = t["title"] or "(untitled)"
#             if st.button(f"{label}\n{sublabel}", key=f"global_thread_{t['id']}"):
#                 open_thread(t["video_id"], t["id"])

#     # ---------- Main panel ----------
#     if not st.session_state.video_id:
#         st.title("YouTube RAG Chat")
#         st.write("Paste a YouTube link in the sidebar, or pick a past conversation.")
#         return

#     if not st.session_state.thread_id:
#         st.title("YouTube RAG Chat")
#         st.write("Pick an existing conversation or start a new one from the sidebar.")
#         return

#     st.title("Chat")

#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.write(msg["content"])

#     question = st.chat_input("Ask a question about the video...")
#     if question:
#         st.session_state.messages.append({"role": "user", "content": question})
#         with st.chat_message("user"):
#             st.write(question)

#         with st.chat_message("assistant"):
#             with st.spinner("Thinking..."):
#                 answer = answer_with_history(
#                     st.session_state.video_id, question, st.session_state.messages[:-1]
#                 )
#             st.write(answer)

#         st.session_state.messages.append({"role": "assistant", "content": answer})
#         save_message(st.session_state.thread_id, "user", question)
#         save_message(st.session_state.thread_id, "assistant", answer)


# if st.session_state.user is None:
#     show_auth_screen()
# else:
#     show_chat_app()



"""Streamlit frontend for the YouTube RAG chatbot.

Run with: streamlit run app.py
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from Auth import sign_up, sign_in
from Utils import extract_video_id
from Pipeline import ingest_video
from Store import (
    create_thread,
    list_threads,
    list_all_threads,
    delete_thread,
    get_messages,
    answer_with_history,
    save_message,
)
# NOTE: delete_existing_chunks is intentionally NOT imported here. Chunks are
# shared by every user, so no user action may delete them (see ingest.py --force).

st.set_page_config(page_title="YouTube RAG Chat", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def show_auth_screen():
    st.title("YouTube RAG Chat")
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in"):
            try:
                st.session_state.user = sign_in(email, password)
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_signup:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Sign up"):
            try:
                user = sign_up(email, password)
                if user is None:
                    st.info(
                        "Account created. Check your email for a confirmation link, "
                        "then log in."
                    )
                    return
                st.session_state.user = user
                st.success("Account created — you're logged in.")
                st.rerun()
            except Exception as e:
                st.error(f"Sign up failed: {e}")


def handle_ingest(url: str):
    """Runs ingestion with live progress. Returns the video_id if the video is
    ready to chat about, otherwise None (with a message already shown)."""
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        st.error(str(e))
        return None

    with st.status("Preparing video...", expanded=True) as status:
        try:
            result = ingest_video(video_id, progress=status.write)
        except Exception as e:
            status.update(label="Ingestion failed", state="error")
            st.error(f"Ingestion failed: {e}")
            return None

        if result == "busy":
            status.update(label="Already being processed", state="complete")
            st.warning("Someone is processing this video right now. Try again in a minute.")
            return None

        status.update(label="Video ready", state="complete")
    return video_id


def open_thread(video_id: str, thread_id: str):
    st.session_state.video_id = video_id
    st.session_state.thread_id = thread_id
    st.session_state.messages = get_messages(thread_id, st.session_state.user["id"])
    st.rerun()


def show_chat_app():
    user = st.session_state.user

    with st.sidebar:
        st.write(f"Logged in as **{user['email']}**")
        if st.button("Log out"):
            st.session_state.user = None
            st.session_state.video_id = None
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.subheader("Load a video")
        url = st.text_input("YouTube URL")
        if st.button("Ingest video") and url:
            video_id = handle_ingest(url)
            if video_id:
                st.session_state.video_id = video_id
                st.session_state.thread_id = None
                st.session_state.messages = []
                st.rerun()

        if st.session_state.video_id:
            st.divider()
            st.subheader("This video's conversations")
            threads = list_threads(st.session_state.video_id, user["id"])

            for t in threads:
                label = t["title"] or "(untitled)"
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(label, key=f"thread_{t['id']}"):
                        open_thread(st.session_state.video_id, t["id"])
                with col2:
                    if st.button("🗑️", key=f"delete_{t['id']}"):
                        delete_thread(t["id"], user["id"])
                        if st.session_state.thread_id == t["id"]:
                            st.session_state.thread_id = None
                            st.session_state.messages = []
                        st.rerun()

            new_title = st.text_input("New conversation name", key="new_thread_title")
            if st.button("Start new conversation"):
                thread_id = create_thread(st.session_state.video_id, user["id"], new_title or None)
                open_thread(st.session_state.video_id, thread_id)

        st.divider()
        st.subheader("All your conversations")
        all_threads = list_all_threads(user["id"])
        if not all_threads:
            st.caption("No conversations yet.")
        for t in all_threads:
            sublabel = t["title"] or "(untitled)"
            if st.button(f"{t['video_title']}\n{sublabel}", key=f"global_thread_{t['id']}"):
                open_thread(t["video_id"], t["id"])

    if not st.session_state.video_id:
        st.title("YouTube RAG Chat")
        st.write("Paste a YouTube link in the sidebar, or pick a past conversation.")
        return

    if not st.session_state.thread_id:
        st.title("YouTube RAG Chat")
        st.write("Pick an existing conversation or start a new one from the sidebar.")
        return

    st.title("Chat")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("Ask a question about the video...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = answer_with_history(
                    st.session_state.video_id, question, st.session_state.messages[:-1]
                )
            st.write(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        save_message(st.session_state.thread_id, user["id"], "user", question)
        save_message(st.session_state.thread_id, user["id"], "assistant", answer)


if st.session_state.user is None:
    show_auth_screen()
else:
    show_chat_app()