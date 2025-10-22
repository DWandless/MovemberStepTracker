import streamlit as st
import os
import pandas as pd
from datetime import datetime
import plotly.express as px
import zipfile
import io

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Movember Step Tracker", layout="wide")
UPLOAD_FOLDER = "uploads"
DATA_FILE = "step_data.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ LOGIN CHECK ------------------
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

username = st.session_state.get("username", "Guest")

# ------------------ HEADER ------------------
st.title("🏃 Movember Step Tracker")
st.sidebar.success(f"Welcome, {username}!")
st.sidebar.button("Logout")

# ------------------ TABS ------------------
tab1, tab2, tab3 = st.tabs(["➕ Submit Steps", "📊 Daily Progress", "📂 All Submissions"])

# ------------------ TAB 1: SUBMIT STEPS ------------------
with tab1:
    st.header("Submit Your Steps")
    col1, col2 = st.columns(2)
    with col1:
        step_date = st.date_input("Date")
    with col2:
        steps = st.number_input("Step Count", min_value=0, step=100)

    screenshot = st.file_uploader("Upload Screenshot (PNG/JPEG)", type=["png", "jpg", "jpeg"])
    if screenshot:
        st.image(screenshot, caption="Preview", width=300)  # Smaller preview

    if st.button("Submit"):
        if not screenshot:
            st.error("Please upload a screenshot.")
        else:
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
            st.success("✅ Step count submitted successfully!")
            st.balloons()

# ------------------ TAB 2: DAILY PROGRESS ------------------
with tab2:
    st.header("Daily Progress")
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)

        # Filter for logged-in user only
        user_df = df[df["Name"] == username]
        if not user_df.empty:
            daily_steps = user_df.groupby("Date")["Steps"].sum().reset_index()
            st.metric("Your Total Steps", int(user_df["Steps"].sum()))
            fig = px.bar(daily_steps, x="Date", y="Steps", title=f"{username}'s Steps per Day")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("You have no submissions yet.")
    else:
        st.info("No submissions yet.")

# ------------------ TAB 3: ALL SUBMISSIONS ------------------
with tab3:
    st.header("Your Submissions")
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        user_df = df[df["Name"] == username]

        if not user_df.empty:
            st.dataframe(user_df, use_container_width=True)

            # Download only user's CSV
            st.download_button("Download My Data (CSV)", user_df.to_csv(index=False), f"{username}_steps.csv")

            # User-specific ZIP download
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for file_path in user_df["Screenshot"]:
                    if os.path.exists(file_path):
                        zip_file.write(file_path, arcname=os.path.basename(file_path))
            zip_buffer.seek(0)
            st.download_button("Download My Screenshots (ZIP)", zip_buffer, f"{username}_screenshots.zip")
        else:
            st.info("You have no submissions yet.")
    else:
        st.info("No submissions yet.")