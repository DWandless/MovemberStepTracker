import streamlit as st
import pandas as pd
import os

# Require login
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

st.title("About & Leaderboard")
st.write("Welcome to the Movember Step Tracker! Below is the leaderboard for the challenge.")

DATA_FILE = "step_data.csv"

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    leaderboard = df.groupby("Name", as_index=False)["Steps"].sum()
    leaderboard = leaderboard.sort_values(by="Steps", ascending=False)

    st.subheader("🏆 Leaderboard")
    st.dataframe(leaderboard)

    if not leaderboard.empty:
        top_user = leaderboard.iloc[0]
        st.success(f"🥇 {top_user['Name']} is leading with {top_user['Steps']} steps!")
else:
    st.info("No step data available yet.")