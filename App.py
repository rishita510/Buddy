"""Streamlit frontend for the YouTube RAG chatbot.

Run with: streamlit run app.py
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from Auth import sign_up, sign_in
from Utils import extract_video_id
from Transcript import fetch_transcript
from Chunk import chunk_transcript
from Store import (
    store_chunks,
    video_already_ingested,
    delete_existing_chunks,
    create_thread,
    list_threads,
    get_messages,
    answer_with_history,
    save_message,
    delete_thread
)

st.set_page_config(page_title="YouTube RAG Chat", layout="wide")

# ---------- Session state defaults ----------
if "user" not in st.session_state:
    st.session_state.user = None          # {"id": ..., "email": ...}
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []        # list of {"role": ..., "content": ...}


# ---------- Auth screen ----------
def show_auth_screen():
    st.title("YouTube RAG Chat")
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in"):
            try:
                user = sign_in(email, password)
                st.session_state.user = user
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_signup:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Sign up"):
            try:
                user = sign_up(email, password)
                st.session_state.user = user
                st.success("Account created — you're logged in.")
                st.rerun()
            except Exception as e:
                st.error(f"Sign up failed: {e}")


# ---------- Ingest a video ----------
def ingest_video(url: str) -> str:
    video_id = extract_video_id(url)

    if video_already_ingested(video_id):
        st.info("This video is already ingested — ready to chat.")
        return video_id

    with st.spinner("Fetching transcript..."):
        transcript_lines = fetch_transcript(video_id)

    with st.spinner("Chunking..."):
        chunks = chunk_transcript(transcript_lines)

    with st.spinner(f"Embedding + storing {len(chunks)} chunks (this calls OpenAI per chunk, may take a bit)..."):
        store_chunks(video_id, chunks)

    st.success("Video ready to chat about.")
    return video_id


# ---------- Main chat app (only shown once logged in) ----------
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
            video_id = ingest_video(url)
            st.session_state.video_id = video_id
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()

        # if st.session_state.video_id:
        #     st.divider()
        #     st.subheader("Conversations")
        #     threads = list_threads(st.session_state.video_id, user["id"])

        #     for t in threads:
        #         label = t["title"] or "(untitled)"
        #         if st.button(label, key=f"thread_{t['id']}"):
        #             st.session_state.thread_id = t["id"]
        #             st.session_state.messages = get_messages(t["id"])
        #             st.rerun()

        #     new_title = st.text_input("New conversation name", key="new_thread_title")
        #     if st.button("Start new conversation"):
        #         thread_id = create_thread(st.session_state.video_id, user["id"], new_title or None)
        #         st.session_state.thread_id = thread_id
        #         st.session_state.messages = []
        #         st.rerun()
        if st.session_state.video_id:
            st.divider()
            st.subheader("Conversations")
            threads = list_threads(st.session_state.video_id, user["id"])

            for t in threads:
                label = t["title"] or "(untitled)"
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(label, key=f"thread_{t['id']}"):
                        st.session_state.thread_id = t["id"]
                        st.session_state.messages = get_messages(t["id"])
                        st.rerun()
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
                st.session_state.thread_id = thread_id
                st.session_state.messages = []
                st.rerun()

    # ---------- Main panel ----------
    if not st.session_state.video_id:
        st.title("YouTube RAG Chat")
        st.write("Paste a YouTube link in the sidebar to get started.")
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
        save_message(st.session_state.thread_id, "user", question)
        save_message(st.session_state.thread_id, "assistant", answer)


# ---------- Entry point ----------
if st.session_state.user is None:
    show_auth_screen()
else:
    show_chat_app()