# streamlit_app.py
import streamlit as st
import requests

# ==================================================
# BACKEND URL (Render)
# ==================================================
BACKEND_URL = "https://my-meeting-assistant.onrender.com"

st.set_page_config(
    page_title="Smart Meeting Assistant",
    layout="wide"
)

# ==================================================
# SESSION STATE INITIALIZATION
# ==================================================
if "step" not in st.session_state:
    st.session_state.step = 1

if "meeting_plan" not in st.session_state:
    st.session_state.meeting_plan = ""

if "audio_file" not in st.session_state:
    st.session_state.audio_file = None

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

        submitted = st.form_submit_button("Generate Meeting Plan")

    # ✅ ALL backend logic stays INSIDE submitted block
    if submitted:
        try:
            resp = requests.post(
                f"{BACKEND_URL}/plan",
                json={
                    "company_name": company,
                    "title": title,
                    "objective": objective,
                    "duration": duration,
                    "attendees": attendees,
                },
                timeout=100,
            )

            data = resp.json()

            if resp.status_code == 200 and data.get("plan"):
                st.session_state.meeting_plan = data["plan"]
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("❌ Failed to generate meeting plan")
                st.json(data)

        except Exception as e:
            st.error("❌ Backend connection failed")
            st.write(str(e))

# ==================================================
# STEP 2: SHOW PLAN
# ==================================================
elif st.session_state.step == 2:
    st.header("📋 AI-Generated Meeting Plan")
    st.markdown(st.session_state.meeting_plan)

    if st.button("Proceed to Recording"):
        st.session_state.step = 3
        st.rerun()

# ==================================================
# STEP 3: RECORD / UPLOAD AUDIO
# ==================================================
elif st.session_state.step == 3:
    st.header("🎙️ Record or Upload Meeting Audio")

    st.markdown("### 🔴 Live Recording (Browser)")
    st.components.v1.html(
        """
        <script>
        let recorder, chunks=[];
        function startRecording() {
          navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
            recorder = new MediaRecorder(stream);
            recorder.start();
            recorder.ondataavailable = e => chunks.push(e.data);
          });
        }
        function stopRecording() {
          recorder.stop();
          recorder.onstop = () => {
            const blob = new Blob(chunks, { type: 'audio/webm' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'meeting_recording.webm';
            a.click();
            chunks = [];
          };
        }
        </script>
        <button onclick="startRecording()">Start Recording</button>
        <button onclick="stopRecording()">Stop & Download</button>
        <p>⬇️ Upload the downloaded file below</p>
        """,
        height=200,
    )

    uploaded = st.file_uploader(
        "Upload meeting audio",
        type=["wav", "mp3", "m4a", "webm"]
    )

    if uploaded:
        st.session_state.audio_file = uploaded
        st.audio(uploaded)

    if st.session_state.audio_file and st.button("Summarize Meeting"):
        st.session_state.step = 4
        st.rerun()

# ==================================================
# STEP 4: SUMMARY & SHARING
# ==================================================
elif st.session_state.step == 4:
    st.header("🧾 AI Meeting Summary")

    with st.spinner("Analyzing meeting audio..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/summarize",
                files={"audio": st.session_state.audio_file},
                timeout=300,
            )
            data = resp.json()
        except Exception as e:
            st.error("❌ Failed to summarize meeting")
            st.write(str(e))
            st.stop()

    # -------- SUMMARY --------
    st.subheader("📌 Summary")
    st.write(data.get("summary", "No summary available."))

    # -------- ACTION POINTS --------
    st.subheader("✅ Action Points")
    for a in data.get("action_points", []):
        st.write("•", a)

    # -------- TASKS --------
    st.subheader("🧑‍💻 Tasks Assigned")
    for t in data.get("tasks", []):
        assignee = t.get("assignee", "Unknown")
        task = t.get("task", "")
        deadline = t.get("deadline", "No deadline")
        st.write(f"**{assignee}** → {task} _(Deadline: {deadline})_")

    # -------- FOLLOW-UP EMAIL --------
    st.subheader("📧 Follow-up Email")
    st.text_area(
        "",
        data.get("followup_email", "No email generated."),
        height=250
    )

    # -------- WHATSAPP --------
    st.subheader("💬 WhatsApp Message")
    st.text_area(
        "",
        data.get("whatsapp", "No WhatsApp summary generated."),
        height=150
    )

    # -------- RESET --------
    if st.button("🔁 Start New Meeting"):
        st.session_state.clear()
        st.rerun()

