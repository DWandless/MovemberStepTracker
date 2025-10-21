import streamlit as st
import os
import shutil
import zipfile

# Require login and admin role
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("Access denied: Admins only.")
    st.stop()

st.title("Admin Dashboard")
st.write("Manage data and access evidence folder.")

DATA_FILE = "step_data.csv"
UPLOAD_FOLDER = "uploads"

# --- Download CSV ---
st.subheader("Download Step Data")
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as f:
        st.download_button("Download Step Data CSV", f, file_name="step_data.csv")
else:
    st.info("No step data file found.")

# --- Evidence Folder ---
st.subheader("Evidence Folder")
folder_path = os.path.abspath(UPLOAD_FOLDER)
st.markdown(f"Path: `{folder_path}`")

# --- Zip and Download Screenshots ---
if os.path.exists(UPLOAD_FOLDER) and os.listdir(UPLOAD_FOLDER):
    zip_path = "evidence.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for root, _, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)
    with open(zip_path, "rb") as f:
        st.download_button("Download All Evidence as ZIP", f, file_name="evidence.zip")
else:
    st.info("No evidence files found.")

# --- Clear All Data ---
st.subheader("Reset Challenge Data")
if st.button("Clear All Data"):
    # Remove CSV
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    # Remove uploads
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    st.success("All data cleared successfully!")