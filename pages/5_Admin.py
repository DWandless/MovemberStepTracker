import streamlit as st
import os
import shutil
import zipfile
import io
import pandas as pd

# ------------------ LOGIN & ROLE CHECK ------------------
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("Access denied: Admins only.")
    st.stop()

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("🔐 Admin Dashboard")
st.write("Manage data and access evidence folder.")

DATA_FILE = "step_data.csv"
UPLOAD_FOLDER = "uploads"

# Initialize dismissed list and confirmation state
if "dismissed_rows" not in st.session_state:
    st.session_state["dismissed_rows"] = set()
if "confirm_delete" not in st.session_state:
    st.session_state["confirm_delete"] = None
if "confirm_clear" not in st.session_state:
    st.session_state["confirm_clear"] = False

# ------------------ SHOW CONFIRMATION FOR DELETE FIRST ------------------
if st.session_state["confirm_delete"] is not None and os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df_filtered = df[df["Steps"] > 15000].copy()
    confirm_idx = st.session_state["confirm_delete"]
    if confirm_idx in df_filtered.index:
        confirm_row = df_filtered.loc[confirm_idx]
        st.warning(f"Are you sure you want to delete submission for **{confirm_row['Name']}** on **{confirm_row['Date']}**?")
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Yes, Delete"):
                df.drop(confirm_idx, inplace=True)
                df.to_csv(DATA_FILE, index=False)
                if os.path.exists(confirm_row["Screenshot"]):
                    os.remove(confirm_row["Screenshot"])
                st.success(f"Deleted submission for {confirm_row['Name']} on {confirm_row['Date']}")
                st.session_state["confirm_delete"] = None
                st.rerun()
        with colB:
            if st.button("❌ Cancel"):
                st.session_state["confirm_delete"] = None
                st.rerun()

# ------------------ 1. ALL SUBMISSIONS > 15,000 ------------------
st.subheader("📊 All Submissions (Steps > 15,000)")
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df_filtered = df[df["Steps"] > 15000].copy()

    if not df_filtered.empty:
        st.write("### High-Step Submissions")
        for idx, row in df_filtered.iterrows():
            if idx in st.session_state["dismissed_rows"]:
                continue

            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                if os.path.exists(row["Screenshot"]):
                    st.image(row["Screenshot"], width=100)
            with col2:
                st.markdown(f"**Name:** {row['Name']} | **Date:** {row['Date']} | **Steps:** {row['Steps']}")
                with st.expander("View Full Screenshot"):
                    st.image(row["Screenshot"], caption=f"Screenshot for {row['Name']}", use_column_width=True)
            with col3:
                if st.button("Dismiss", key=f"dismiss_{idx}"):
                    st.session_state["dismissed_rows"].add(idx)
                    st.rerun()
                if st.button("Delete", key=f"delete_{idx}"):
                    st.session_state["confirm_delete"] = idx
                    st.rerun()
            st.markdown("---")
    else:
        st.info("No submissions with more than 15,000 steps yet.")
else:
    st.info("No submissions yet.")

# ------------------ 2. DOWNLOAD STEP DATA ------------------
st.subheader("📥 Download Step Data")
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as f:
        st.download_button("Download Step Data CSV", f, file_name="step_data.csv")
else:
    st.info("No step data file found.")

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
    st.error("Are you sure you want to clear ALL data? This will remove the CSV and all uploaded screenshots.")
    colA, colB = st.columns(2)
    with colA:
        if st.button("✅ Yes, Clear Everything"):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            if os.path.exists(UPLOAD_FOLDER):
                shutil.rmtree(UPLOAD_FOLDER)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            st.success("✅ All data cleared successfully!")
            st.session_state["confirm_clear"] = False
            st.rerun()
    with colB:
        if st.button("❌ Cancel"):
            st.session_state["confirm_clear"] = False
            st.rerun()