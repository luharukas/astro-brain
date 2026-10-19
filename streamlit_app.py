import os
import uuid
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")


def api_get(path):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("Backend not running. Start with: uvicorn app.main:app --port 8000")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path, data):
    try:
        resp = requests.post(f"{API_BASE}{path}", json=data, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("Backend not running. Start with: uvicorn app.main:app --port 8000")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.text}")
        return None


st.set_page_config(page_title="MyNaksh Astrology Chat", page_icon="", layout="wide")

if "current_user_id" not in st.session_state:
    st.session_state.current_user_id = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("MyNaksh")
    st.markdown("---")

    st.subheader("👤 User")

    tab_existing, tab_new = st.tabs(["Existing User", "New User"])

    with tab_existing:
        users = api_get("/users")
        if users:
            user_options = {f"{u['name']} ({u['user_id']})": u["user_id"] for u in users}
            if user_options:
                selected = st.selectbox("Select user", list(user_options.keys()), key="user_select")
                if st.button("Load User", use_container_width=True):
                    st.session_state.current_user_id = user_options[selected]
                    st.session_state.current_session_id = None
                    st.session_state.messages = []
                    st.rerun()
            else:
                st.info("No users yet. Create one →")

    with tab_new:
        with st.form("create_user_form"):
            name = st.text_input("Name*", placeholder="Shubham")
            dob = st.date_input("Date of Birth", value=None, min_value=None)
            tob = st.text_input("Time of Birth", placeholder="14:30 (optional)")
            birth_place = st.text_input("Birth Place", placeholder="Delhi")
            language = st.selectbox("Preferred Language", ["English", "Hindi", "Tamil", "Telugu", "Bengali"])
            submitted = st.form_submit_button("Create User", use_container_width=True)

            if submitted and name:
                user_id = f"user-{uuid.uuid4().hex[:8]}"
                payload = {
                    "user_id": user_id,
                    "name": name,
                    "preferred_language": language,
                }
                if dob:
                    payload["date_of_birth"] = dob.strftime("%Y-%m-%d")
                if tob:
                    payload["time_of_birth"] = tob
                if birth_place:
                    payload["birth_place"] = birth_place

                result = api_post("/users", payload)
                if result:
                    st.session_state.current_user_id = user_id
                    st.session_state.current_session_id = None
                    st.session_state.messages = []
                    st.success(f"Created {name}:{result.get('zodiac_sign', '?')}")
                    st.rerun()

    if st.session_state.current_user_id:
        st.markdown("---")
        profile = api_get(f"/users/{st.session_state.current_user_id}")
        if profile:
            st.markdown(f"**Active:** {profile['name']}")
            if profile.get("zodiac_sign"):
                st.markdown(f"**Zodiac:** {profile['zodiac_sign']}")
            if profile.get("date_of_birth"):
                st.markdown(f"**DOB:** {profile['date_of_birth']}")
            if profile.get("birth_place"):
                st.markdown(f"**Place:** {profile['birth_place']}")

        st.markdown("---")
        st.subheader("💬 Sessions")

        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.current_session_id = f"session-{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.rerun()

        sessions = api_get(f"/users/{st.session_state.current_user_id}/sessions")
        if sessions:
            for s in sessions:
                sid = s["session_id"]
                preview = s.get("preview", "")[:40]
                count = s.get("message_count", 0)
                label = f"{preview}... ({count} msgs)" if preview else f"{sid[:16]}..."
                if st.button(label, key=f"sess_{sid}", use_container_width=True):
                    st.session_state.current_session_id = sid
                    history = api_get(f"/sessions/{sid}/history")
                    if history:
                        st.session_state.messages = [
                            {"role": m["role"], "content": m["content"]}
                            for m in history
                        ]
                    else:
                        st.session_state.messages = []
                    st.rerun()

        st.markdown("---")
        with st.expander("🧠 Shared Brain"):
            brain = api_get(f"/users/{st.session_state.current_user_id}/brain")
            if brain:
                memories = brain.get("memories", [])
                if memories:
                    for m in memories:
                        props = m.get("properties", {})
                        cat = props.get("category", m.get("category", ""))
                        content = props.get("content", m.get("content", ""))
                        st.markdown(f"• **[{cat}]** {content}")
                else:
                    st.markdown("_No memories yet_")

if not st.session_state.current_user_id:
    st.markdown("## Welcome to MyNaksh Astrology Chat")
    st.markdown("Select or create a user from the sidebar to start chatting.")
    st.stop()

if not st.session_state.current_session_id:
    st.markdown("## 💬 Start a conversation")
    st.markdown("Click **New Chat** in the sidebar to begin.")
    st.stop()

st.markdown(f"### 💬 Chat:`{st.session_state.current_session_id[:20]}...`")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("context_used"):
            st.caption(f"Context: {', '.join(msg['context_used'])}")

if prompt := st.chat_input("Ask about your stars, career, life..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting the stars..."):
            result = api_post("/chat", {
                "user_id": st.session_state.current_user_id,
                "session_id": st.session_state.current_session_id,
                "message": prompt,
            })

        if result:
            response = result["response"]
            context_used = result.get("context_used", [])
            st.markdown(response)
            if context_used:
                st.caption(f"Context: {', '.join(context_used)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "context_used": context_used,
            })
        else:
            st.error("Failed to get response")
