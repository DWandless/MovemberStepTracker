import streamlit as st
import os
import pandas as pd
from datetime import datetime

# Require login
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

st.set_page_config(page_title="Movember Step Tracker", layout="wide")
st.title("Movember Step Tracker - Home")

UPLOAD_FOLDER = "uploads"
DATA_FILE = "step_data.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.header("Submit Your Steps")
with st.form("step_form"):
    step_date = st.date_input("Date")
    steps = st.number_input("Step Count", min_value=0, step=100)
    screenshot = st.file_uploader("Upload Screenshot (PNG/JPEG)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("Submit")

    if submitted:
        if not screenshot:
            st.error("Please upload a screenshot.")
        else:
            username = st.session_state.get("username")  # Use logged-in username
            filename = f"{username}_{step_date}_{datetime.now().strftime('%H%M%S')}.png"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(file_path, "wb") as f:
                f.write(screenshot.getbuffer())

            new_entry = pd.DataFrame([{
                "Name": username,
                "Date": step_date,
                "Steps": steps,
                "Screenshot": file_path
            }])

            if os.path.exists(DATA_FILE):
                df = pd.read_csv(DATA_FILE)
                df = pd.concat([df, new_entry], ignore_index=True)
            else:
                df = new_entry

            df.to_csv(DATA_FILE, index=False)
            st.success("Step count submitted successfully!")

# Show submissions (optional for all logged-in users)
if st.checkbox("Show all submissions"):
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        st.dataframe(df)
    else:
        st.info("No submissions yet.")