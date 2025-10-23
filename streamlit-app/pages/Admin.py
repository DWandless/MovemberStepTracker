import streamlit as st
import os
import shutil
import zipfile
import io
import pandas as pd
import re
import unicodedata
import time
from db import supabase

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="🔐 Admin Dashboard", layout="wide")

# ------------------ DXC BRANDING & MOVEMBER CSS ------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    body {
        font-family: 'Roboto', sans-serif;
        background-color: #FFFFFF;
    }
    .header-container {
        display: flex;
        justify-content: flex-start;
        align-items: center;
        background: linear-gradient(90deg, #603494, #4a2678);
        color: white;
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .header-title {
        font-size: 42px;
        font-weight: bold;
    }
    .header-subtitle {
        font-size: 18px;
        margin-top: 5px;
    }
    .stButton>button {
        background-color: #603494;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #4a2678;
        transform: scale(1.05);
    }
    .footer-carousel {
        text-align: center;
        font-size: 18px;
        color: #603494;
        font-weight: bold;
        margin-top: 30px;
        padding: 10px;
        border-top: 2px solid #603494;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ HERO HEADER ------------------
header_html = """
<div class="header-container">
    <div>
        <div class="header-title">🔐 Admin Dashboard</div>
        <div class="header-subtitle">Manage submissions, verify evidence, and maintain the challenge securely.</div>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ------------------ LOGIN & ROLE CHECK ------------------
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

username = st.session_state.get("username", "")
user_resp = supabase.table("users").select("user_admin").eq("user_name", username).limit(1).execute()
if not user_resp.data or not user_resp.data[0].get("user_admin", False):
    st.error("Access denied: Admins only.")
    st.stop()

# ------------------ SECURITY FUNCTION ------------------
def secure_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filenames to prevent directory traversal or injection."""
    if not filename:
        return "file"
    filename = os.path.basename(filename)
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("utf-8", "ignore").decode("utf-8")
    filename = re.sub(r"[^A-Za-z0-9.\-_]", "_", filename)
    return filename[:max_length]

# ------------------ CONFIG & STATE ------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# replace old confirm state with a simpler pending_delete entry
if "pending_delete" not in st.session_state:
    st.session_state["pending_delete"] = None
if "confirm_clear" not in st.session_state:
    st.session_state["confirm_clear"] = False

# ------------------ FETCH DATA FROM SUPABASE ------------------
def fetch_all_submissions():
    forms = supabase.table("forms") \
        .select("*") \
        .eq("form_verified", False) \
        .gt("form_stepcount", 15000) \
        .execute().data
    users = supabase.table("users").select("user_id, user_name").execute().data
    if not forms:
        return pd.DataFrame()
    df_forms = pd.DataFrame(forms)
    df_users = pd.DataFrame(users)
    return pd.merge(df_forms, df_users, on="user_id")

df = fetch_all_submissions()

# ------------------ SIMPLE CONFIRM DELETE (CSS-RESISTANT) ------------------
# Show a minimal confirmation widget when a pending delete is set.
if st.session_state["pending_delete"]:
    pd = st.session_state["pending_delete"]
    st.warning(f"Are you sure you want to permanently delete the submission for **{pd['user_name']}** on **{pd['form_date']}**?")
    confirm_cb = st.checkbox("I understand this will permanently delete the submission.", key="confirm_delete_cb")
    colA, colB = st.columns(2)
    with colA:
        # Delete button is disabled until the checkbox is ticked
        if st.button("✅ Delete", disabled=not confirm_cb):
            try:
                supabase.table("forms").delete().eq("form_id", pd["form_id"]).execute()
                safe_name = secure_filename(os.path.basename(str(pd.get("file", ""))))
                file_path = os.path.join(UPLOAD_FOLDER, safe_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                st.success("Submission deleted successfully.")
            except Exception:
                st.error("Error deleting submission.")  # keep message generic
            st.session_state["pending_delete"] = None
            st.rerun()
    with colB:
        if st.button("❌ Cancel"):
            st.session_state["pending_delete"] = None
            st.rerun()

# ------------------ 1. HIGH-STEP SUBMISSIONS (>15,000) ------------------
st.subheader("📊 Unverified Submissions (Steps > 15,000)")

if not df.empty:
    for idx, row in df.iterrows():
        col1, col2, col3 = st.columns([1, 3, 2])
        safe_name = secure_filename(os.path.basename(str(row.get("form_filepath", ""))))
        file_path = os.path.join(UPLOAD_FOLDER, safe_name)

        with col1:
            if os.path.exists(file_path):
                st.image(file_path, width=100)
            else:
                st.warning("No preview available.")

        with col2:
            st.markdown(f"**Name:** {row['user_name']} | **Date:** {row['form_date']} | **Steps:** {row['form_stepcount']}")
            with st.expander("View Full Screenshot"):
                if os.path.exists(file_path):
                    st.image(file_path, caption=f"Screenshot for {row['user_name']}", width="stretch")
                else:
                    st.warning("Screenshot not found.")

        with col3:
            if st.button("✅ Verify", key=f"verify_{idx}"):
                try:
                    supabase.table("forms") \
                        .update({"form_verified": True}) \
                        .eq("form_id", row["form_id"]) \
                        .execute()
                    st.success(f"Verified submission for {row['user_name']}")
                except Exception as e:
                    st.error(f"Error verifying form: {e}")
                st.rerun()
            if st.button("❌ Delete", key=f"delete_{idx}"):
                # set a small pending_delete dict rather than relying on index
                st.session_state["pending_delete"] = {
                    "form_id": row["form_id"],
                    "user_name": row["user_name"],
                    "form_date": row["form_date"],
                    "file": row.get("form_filepath", "")
                }
                st.rerun()
        st.markdown("---")
else:
    st.info("No high-step unverified submissions found.")

# ------------------ 2. DOWNLOAD STEP DATA ------------------
st.subheader("📥 Download Step Data")
if not df.empty:
    csv_data = df.to_csv(index=False)
    st.download_button("Download Step Data CSV", csv_data, file_name="step_data.csv")
else:
    st.info("No step data available.")

# ------------------ 3. EVIDENCE FOLDER ------------------
st.subheader("📂 Evidence Folder")
folder_path = os.path.abspath(UPLOAD_FOLDER)
st.markdown(f"Path: `{folder_path}`")

if os.path.exists(UPLOAD_FOLDER) and os.listdir(UPLOAD_FOLDER):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for root, _, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)
    zip_buffer.seek(0)
    st.download_button("Download All Evidence as ZIP", zip_buffer, file_name="evidence.zip")
else:
    st.info("No evidence files found.")

# ------------------ 4. RESET CHALLENGE DATA ------------------
st.subheader("⚠️ Reset Challenge Data")
st.warning("This will permanently delete ALL submissions and screenshots. This action cannot be undone.")

if not st.session_state["confirm_clear"]:
    if st.button("Clear All Data"):
        st.session_state["confirm_clear"] = True
        st.rerun()
else:
    st.error("Are you sure you want to clear ALL data? This will remove all DB records and uploaded screenshots.")
    colA, colB = st.columns(2)
    with colA:
        if st.button("✅ Yes, Clear Everything"):
            try:
                supabase.table("forms").delete().neq("form_id", 0).execute()
                if os.path.exists(UPLOAD_FOLDER):
                    shutil.rmtree(UPLOAD_FOLDER)
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                st.success("✅ All data cleared successfully!")
            except Exception as e:
                st.error(f"Error clearing data: {e}")
            st.session_state["confirm_clear"] = False
            st.rerun()
    with colB:
        if st.button("❌ Cancel"):
            st.session_state["confirm_clear"] = False
            st.rerun()

# ------------------ 5. FOOTER CAROUSEL ------------------
carousel_messages = [
    "💡 Movember Tip: Walking meetings are a great way to add steps!",
    "🥸 Fun Fact: A mustache can grow up to 0.4mm per day!",
    "🚶 Challenge: Hit 10,000 steps today and celebrate with a Mo-selfie!",
    "💜 DXC supports Movember: Keep moving, keep growing!",
    "🔥 Did you know? Just 30 minutes of walking can boost your mood and health!",
    "🎯 Goal Reminder: Every step counts toward a healthier you and a great cause!",
    "📸 Share your Mo! Post your mustache progress and inspire others!",
    "🏆 Leaderboard Alert: Check who's leading the Mo-vement today!",
    "🌍 Together we can make a difference—one step at a time!",
    "💪 Pro Tip: Take the stairs instead of the elevator for an easy step boost!",
    "🎉 Fun Challenge: Invite a colleague for a lunchtime walk and double your steps!",
    "🥳 Celebrate small wins! Every 1,000 steps is a victory for your health!"
]

# non-blocking footer: pick one message based on the current time slice (no sleep loop)
placeholder = st.empty()
msg_index = (int(time.time()) // 3) % len(carousel_messages)
placeholder.markdown(f"<div class='footer-carousel'>{carousel_messages[msg_index]}</div>", unsafe_allow_html=True)