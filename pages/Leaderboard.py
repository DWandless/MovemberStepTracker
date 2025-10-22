import streamlit as st
import pandas as pd
from db import supabase
import time

# ------------------ CONFIG ------------------
st.set_page_config(page_title="🏆 Leaderboard", layout="wide")

# ------------------ DXC BRANDING & MOVEMBER CSS ------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    body {
        font-family: 'Roboto', sans-serif;
        background-color: #FFFFFF;
    }
    /* Hero Header */
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
    /* Tabs & Buttons */
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
    /* Footer Carousel */
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
        <div class="header-title">🏆 Movember Step Leaderboard</div>
        <div class="header-subtitle">Track the leaders and keep moving for a cause!</div>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ------------------ LOGIN CHECK ------------------
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

username = st.session_state.get("username", "Guest")

# ------------------ FILTERS ------------------
st.subheader("Filter Leaderboard")
col1, col2 = st.columns(2)
with col1:
    selected_date = st.date_input("Select a date (leave empty for all-time)", value=None)
with col2:
    view_option = st.selectbox("Show:", ["All", "Top 10", "Bottom 10"])

# ------------------ FETCH DATA FROM SUPABASE ------------------
forms_query = supabase.table("forms").select("user_id, form_stepcount, form_date")
if selected_date:
    forms_query = forms_query.eq("form_date", str(selected_date))

forms = forms_query.execute().data

if not forms:
    st.info("No step data available for the selected date." if selected_date else "No step data available.")
    st.stop()

df = pd.DataFrame(forms)

# ------------------ AGGREGATE STEPS ------------------
step_summary = df.groupby("user_id")["form_stepcount"].sum().reset_index()
step_summary.rename(columns={"form_stepcount": "total_steps"}, inplace=True)

# ------------------ GET USERNAMES ------------------
users = supabase.table("users").select("user_id, user_name").execute().data
users_df = pd.DataFrame(users)

# Merge steps with usernames
leaderboard = pd.merge(step_summary, users_df, on="user_id")
leaderboard = leaderboard[["user_name", "total_steps"]]

# Apply sorting logic based on slicer
if view_option == "Top 10":
    leaderboard = leaderboard.sort_values("total_steps", ascending=False).head(10)
elif view_option == "Bottom 10":
    leaderboard = leaderboard.sort_values("total_steps", ascending=True).head(10)
else:  # All
    leaderboard = leaderboard.sort_values("total_steps", ascending=False)

leaderboard.reset_index(drop=True, inplace=True)
leaderboard.index += 1  # Start rank from 1

# ------------------ DISPLAY ------------------
st.subheader("Leaderboard")
if selected_date:
    st.caption(f"Showing results for **{selected_date}**")
else:
    st.caption("Showing **all-time** results")

st.dataframe(leaderboard, use_container_width=True)

# Highlight top user (only if showing all or top 10)
if not leaderboard.empty and view_option != "Bottom 10":
    top_user = leaderboard.iloc[0]
    st.success(f"🥇 {top_user['user_name']} is leading with {int(top_user['total_steps'])} steps!")

# ------------------ SIDEBAR USER INFO ------------------
if username:
    st.sidebar.markdown(f"**User:** {username}")

# ------------------ FOOTER CAROUSEL ------------------
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

placeholder = st.empty()
for i in range(2):  # Loop twice for effect
    for msg in carousel_messages:
        placeholder.markdown(f"<div class='footer-carousel'>{msg}</div>", unsafe_allow_html=True)
        time.sleep(3)