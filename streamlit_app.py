# streamlit_app.py
import streamlit as st
import requests

# ==================================================
# LOCALHOST BACKEND
# ==================================================
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Smart Meeting Assistant",
    layout="wide"
)

# ==================================================
# SESSION STATE
# ==================================================
if "step" not in st.session_state:
    st.session_state.step = 1

# ==================================================
# HEADER
# ==================================================
st.title("🧠 Smart Meeting Assistant")
st.caption("Plan → Record → Summarize → Share")

# ==================================================
# STEP 1: PLAN MEETING
# ==================================================
if st.session_state.step == 1:
    st.header("1️⃣ Plan the Meeting")

    with st.form("plan_form"):
        company = st.text_input("Company Name")
        title = st.text_input("Meeting Title")
        objective = st.text_area("Meeting Objective")
        duration = st.number_input("Duration (minutes)", 15, 180, 60)
        attendees = st.text_area("Attendees & Roles (e.g. Rahul – Backend, Priya – PM)")

        if st.form_submit_button("Generate Meeting Plan"):
            resp = requests.post(
                f"{BACKEND_URL}/plan",
                json={
                    "company_name": company,
                    "title": title,
                    "objective": objective,
                    "duration": duration,
                    "attendees": attendees,
                },
            )
            data = resp.json()

            if resp.status_code == 200 and data.get("plan"):
                st.session_state.plan = data["plan"]
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("❌ Failed to generate meeting plan.")
                st.json(data)


# ==================================================
# STEP 2: SHOW PLAN
# ==================================================
elif st.session_state.step == 2:
    st.header("📋 AI-Generated Meeting Plan")
    st.markdown(st.session_state.plan)

    if st.button("Proceed to Recording"):
        st.session_state.step = 3
        st.rerun()

# ==================================================
# STEP 3: RECORD / UPLOAD AUDIO
# ==================================================
elif st.session_state.step == 3:
    st.header("🎙️ Record or Upload Meeting")

    uploaded = st.file_uploader(
        "Upload meeting audio",
        type=["wav", "mp3", "m4a", "webm"]
    )
    recorded = st.audio_input("Or record live")

    if uploaded:
        st.session_state.audio = uploaded
    if recorded:
        st.session_state.audio = recorded

    if "audio" in st.session_state and st.button("Summarize Meeting"):
        st.session_state.step = 4
        st.rerun()

# ==================================================
# STEP 4: SUMMARY & SHARING
# ==================================================
elif st.session_state.step == 4:
    st.header("🧾 AI Meeting Summary")

    with st.spinner("Analyzing meeting..."):
        resp = requests.post(
            f"{BACKEND_URL}/summarize",
            files={"audio": st.session_state.audio}
        )
        data = resp.json()

    st.subheader("📌 Summary")
    st.write(data["summary"])

    st.subheader("✅ Action Points")
    for a in data.get("action_points", []):
        st.write("•", a)

    st.subheader("🧑‍💻 Tasks Assigned")
    for t in data.get("tasks", []):
        st.write(f"**{t['assignee']}** → {t['task']} ({t['deadline']})")

    st.subheader("📧 Follow-up Email")
    st.text_area("", data["followup_email"], height=250)

    st.subheader("💬 WhatsApp Message")
    st.text_area("", data["whatsapp"], height=150)

    if st.button("New Meeting"):
        st.session_state.clear()
        st.rerun()
