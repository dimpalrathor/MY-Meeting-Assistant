# streamlit_app.py
import streamlit as st
import requests

BACKEND_URL = "https://my-meeting-assistant.onrender.com"

st.set_page_config(page_title="Smart Meeting Assistant", layout="wide")

if "step" not in st.session_state:
    st.session_state.step = 1

st.title("🧠 Smart Meeting Assistant")
st.caption("Plan → Record → Summarize → Share")

# =========================
# STEP 1 – PLAN
# =========================
if st.session_state.step == 1:
    st.header("1️⃣ Plan the Meeting")

    with st.form("plan"):
        company = st.text_input("Company Name")
        title = st.text_input("Meeting Title")
        objective = st.text_area("Objective")
        duration = st.number_input("Duration (minutes)", 15, 180, 60)
        attendees = st.text_area("Attendees & Roles")

        if st.form_submit_button("Generate Meeting Plan"):
            r = requests.post(
                f"{BACKEND_URL}/plan",
                json={
                    "company_name": company,
                    "title": title,
                    "objective": objective,
                    "duration": duration,
                    "attendees": attendees,
                },
            )
            data = r.json()
            if "plan" in data:
                st.session_state.plan = data["plan"]
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Failed to generate plan")
                st.json(data)

# =========================
# STEP 2 – SHOW PLAN
# =========================
elif st.session_state.step == 2:
    st.header("📋 Meeting Plan")
    st.markdown(st.session_state.plan)

    if st.button("Proceed to Recording"):
        st.session_state.step = 3
        st.rerun()

# =========================
# STEP 3 – RECORD / UPLOAD
# =========================
elif st.session_state.step == 3:
    st.header("🎙️ Record or Upload Meeting")

    st.markdown("### Live Recording (Browser)")
    st.components.v1.html(
        """
        <script>
        let recorder, chunks=[];
        function start() {
          navigator.mediaDevices.getUserMedia({audio:true}).then(stream=>{
            recorder=new MediaRecorder(stream);
            recorder.start();
            recorder.ondataavailable=e=>chunks.push(e.data);
          });
        }
        function stop() {
          recorder.stop();
          recorder.onstop=()=>{
            const blob=new Blob(chunks,{type:'audio/webm'});
            const a=document.createElement('a');
            a.href=URL.createObjectURL(blob);
            a.download='recorded.webm';
            a.click();
            chunks=[];
          }
        }
        </script>
        <button onclick="start()">Start Recording</button>
        <button onclick="stop()">Stop & Download</button>
        <p>Upload the downloaded file below</p>
        """,
        height=180,
    )

    uploaded = st.file_uploader(
        "Upload meeting audio",
        type=["wav", "mp3", "m4a", "webm"]
    )

    if uploaded:
        st.session_state.audio = uploaded
        st.audio(uploaded)

    if "audio" in st.session_state and st.button("Summarize Meeting"):
        st.session_state.step = 4
        st.rerun()

# =========================
# STEP 4 – SUMMARY
# =========================
elif st.session_state.step == 4:
    st.header("🧾 Meeting Summary")

    with st.spinner("Analyzing..."):
        r = requests.post(
            f"{BACKEND_URL}/summarize",
            files={"audio": st.session_state.audio},
        )
        data = r.json()

    st.subheader("📌 Summary")
    st.write(data.get("summary"))

    st.subheader("✅ Action Points")
    for a in data.get("action_points", []):
        st.write("•", a)

    st.subheader("🧑‍💻 Tasks")
    for t in data.get("tasks", []):
        st.write(f"**{t.get('assignee')}** → {t.get('task')}")

    st.subheader("📧 Follow-up Email")
    st.text_area("", data.get("followup_email", ""), height=250)

    st.subheader("💬 WhatsApp Message")
    st.text_area("", data.get("whatsapp", ""), height=150)

    if st.button("New Meeting"):
        st.session_state.clear()
        st.rerun()
