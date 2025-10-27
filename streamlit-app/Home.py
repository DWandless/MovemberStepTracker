import streamlit as st
import os
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import zipfile
import io
from PIL import Image, UnidentifiedImageError
import re
import unicodedata
from db import supabase
import random

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Movember Step Tracker", layout="wide")
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# add max upload size
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

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
    /* Tabs */
    .stTabs [role="tablist"] {
        border-bottom: 3px solid #603494;
    }
    .stTabs [role="tab"] {
        color: #603494;
        font-weight: bold;
    }
    /* Buttons */
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
st.markdown("""
<div class="header-container">
    <div>
        <div class="header-title">🏃 Movember Step Tracker</div>
        <div class="header-subtitle">Track your steps, make every move count for men's health!</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------ SECURE FILENAME HELPER ------------------
def secure_filename(filename: str, max_length: int = 255) -> str:
    if not filename:
        return "file"
    filename = os.path.basename(filename)
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("utf-8", "ignore").decode("utf-8")
    filename = re.sub(r"[^A-Za-z0-9.\\-_]", "_", filename)
    return filename[:max_length]

# ------------------ HELPER FUNCTIONS ------------------
def get_user_id(username):
    try:
        response = supabase.table("users").select("user_id").eq("user_name", username).execute()
        if response.data and len(response.data) == 1:
            return response.data[0]["user_id"]
    except Exception as e:
        st.error(f"Error fetching user ID: {e}")
    return None

def fetch_user_forms(user_id):
    try:
        response = supabase.table("forms").select("*").eq("user_id", user_id).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching forms: {e}")
        return pd.DataFrame()

# ------------------ SECURITY: LOGIN CHECK ------------------
if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

username = st.session_state.get("username")
user_id = get_user_id(username)
if not user_id:
    st.error("User account not found.")
    st.stop()

# ------------------ SIDEBAR ------------------
st.sidebar.markdown(f"<h3 style='color:#603494;'>Welcome, {username}!</h3>", unsafe_allow_html=True)
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# ------------------ TABS ------------------

# ------------------ ADD NEW TAB TO EXISTING TABS ------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ Submit Steps",
    "📊 Daily Progress",
    "🏅 Badges & Achievements",
    "🗣️ Movember Shout-Out",
    "💜 About Movember"
])

# ------------------ TAB 1: SUBMIT STEPS (with 5-min cooldown) ------------------
with tab1:
    st.header("Submit Your Steps")
    
    col1, col2 = st.columns(2)
    with col1:
        step_date = st.date_input("Date")
    with col2:
        steps = st.number_input("Step Count", min_value=0, step=100)

    screenshot = st.file_uploader("Upload Screenshot (PNG/JPEG) - Please ensure both Date and Stepcount are visible", type=["png", "jpg", "jpeg"])
    if screenshot:
        st.image(screenshot, caption="Preview", width=300)

    # --- Initialize session state for last submission time ---
    if "last_submission_time" not in st.session_state:
        st.session_state.last_submission_time = None

    # --- Helper to fetch last submission timestamp from DB ---
    def get_last_submission_time(user_id):
        try:
            response = (
                supabase.table("forms")
                .select("form_created_at")
                .eq("user_id", user_id)
                .order("form_created_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) == 1:
                return datetime.fromisoformat(response.data[0]["form_created_at"])
        except Exception as e:
            st.error(f"Error fetching last submission time: {e}")
        return None

    if st.button("Submit"):
        now = datetime.now()
        last_submission = st.session_state.last_submission_time or get_last_submission_time(user_id)

        # --- Check 5-minute cooldown ---
        if last_submission and now - last_submission < timedelta(minutes=5):
            remaining = timedelta(minutes=5) - (now - last_submission)
            minutes, seconds = divmod(remaining.total_seconds(), 60)
            st.warning(f"⏳ You must wait {int(minutes)}m {int(seconds)}s before submitting again.")
        else:
            if not screenshot:
                st.error("Please upload a screenshot.")
            if steps <= 0:
                st.error("Please enter a valid step count greater than zero.")
            else:
                buf = bytes(screenshot.getbuffer())
                if len(buf) > MAX_UPLOAD_SIZE:
                    st.error("Uploaded file is too large (max 5 MB).")
                else:
                    try:
                        bio = io.BytesIO(buf)
                        img = Image.open(bio)
                        img.verify()  # Validate image
                        bio.seek(0)
                        img = Image.open(bio).convert("RGB")

                        # --- Save file ---
                        raw_name = f"{username}_{step_date}_{datetime.now().strftime('%H%M%S')}_{screenshot.name}"
                        filename = secure_filename(raw_name)
                        filename = os.path.splitext(filename)[0] + ".jpg"
                        file_path = os.path.join(UPLOAD_FOLDER, filename)

                        out_buf = io.BytesIO()
                        img.save(out_buf, format="JPEG", quality=85, optimize=True)
                        with open(file_path, "wb") as f:
                            f.write(out_buf.getvalue())
                        try:
                            os.chmod(file_path, 0o600)
                        except Exception:
                            pass

                        # --- Insert submission into Supabase ---
                        supabase.table("forms").insert({
                            "form_filepath": filename,
                            "form_stepcount": steps,
                            "form_date": str(step_date),
                            "user_id": user_id,
                            "form_verified": False
                        }).execute()

                        # --- Update session state cooldown ---
                        st.session_state.last_submission_time = now

                        st.success("✅ Step count submitted successfully!")
                        st.balloons()
                    except UnidentifiedImageError:
                        st.error("Uploaded file is not a valid image.")
                    except Exception as e:
                        st.error(f"Error processing uploaded image: {e}")

# ------------------ TAB 2: DAILY PROGRESS ------------------
with tab2:
    st.header("Daily Progress")
    df = fetch_user_forms(user_id)
    if not df.empty:
        daily_steps = df.groupby("form_date")["form_stepcount"].sum().reset_index()
        total_steps = int(df["form_stepcount"].sum())

        # --- Summary Metrics ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Your Total Steps", total_steps)
        with col2:
            today_steps = int(daily_steps[daily_steps["form_date"] == str(datetime.now().date())]["form_stepcount"].sum() or 0)
            st.metric("Your Steps Today", today_steps)
        with col3:
            st.metric("Days Participated", daily_steps["form_date"].nunique())

        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("Average Daily Steps", int(daily_steps["form_stepcount"].mean()))
        with col5:
            st.metric("Estimated Distance (km)", round(total_steps * 0.0008, 2))
        with col6:
            st.metric("Estimated Calories Burned (kcal)", int(total_steps * 0.04))

        # --- DAILY STREAK TRACKER (moved above plotly graph, no progress bar) ---
        daily_steps["form_date"] = pd.to_datetime(daily_steps["form_date"]).dt.date
        sorted_dates = sorted(daily_steps["form_date"].unique())

        streak = 0
        current_streak = 1 if sorted_dates else 0

        for i in range(len(sorted_dates) - 1, 0, -1):
            if (sorted_dates[i] - sorted_dates[i - 1]) == timedelta(days=1):
                current_streak += 1
            else:
                break

        # Reset streak if last submission wasn’t today
        if sorted_dates and sorted_dates[-1] != datetime.now().date():
            current_streak = 0

        streak = current_streak

        # --- Display streak message only ---
        if streak > 0:
            st.success(f"🔥 Current Streak: **{streak} day{'s' if streak > 1 else ''} in a row!**")
        else:
            st.info("No active streak. Submit today to start one!")

        # --- Plotly Graph (now appears after the streak tracker) ---
        fig = px.bar(
            daily_steps, x="form_date", y="form_stepcount",
            title=f"{username}'s Steps per Day",
            color_discrete_sequence=["#603494"],
            labels={"form_date": "Date", "form_stepcount": "Step Count"}
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No submissions yet. Submit your first steps to start tracking!")


# ------------------ TAB 4: ABOUT MOVEMBER ------------------
with tab5:
    st.header("About Movember")
    st.markdown(""" 
    **Movember** is a global movement committed to changing the face of men's health.
    Every November, participants grow mustaches and take on fitness challenges to raise
    awareness and funds for:

    - 🧠 **Mental Health & Suicide Prevention**  
    - 💪 **Prostate Cancer Research**  
    - 🩺 **Testicular Cancer Support**

    ### 🚶 Why Steps?
    Physical activity plays a major role in both physical and mental well-being.  
    By tracking your steps, you’re not only improving your health — you’re also supporting
    Movember’s mission for men everywhere.

    ---
    ### 📚 Learn More
    - [Movember Official Website](https://uk.movember.com)
    - [Men’s Health Resources](https://movember.com/mens-health)
    - [Get Involved / Donate](https://uk.movember.com/get-involved)
    - [DXC Official Website](https://dxc.com)
    """)

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
msg = random.choice(carousel_messages)
st.markdown(f"<div class='footer-carousel'>{msg}</div>", unsafe_allow_html=True)
st.markdown("<div class='footer-branding' style='color:#603494; text-align:center; font-weight:bold; margin-top:20px;'>DXC Technology | Movember 2025</div>", unsafe_allow_html=True)

# ------------------ NEW FEATURES SECTION ------------------
# ------------------ HELPER FUNCTIONS FOR BADGES TAB ------------------
def calculate_badges(total_steps, streak):
    badges = []
    if total_steps >= 10000: badges.append("10K Steps")
    if total_steps >= 50000: badges.append("50K Steps")
    if total_steps >= 100000: badges.append("100K Steps")
    if streak >= 7: badges.append("7-Day Streak")
    if streak >= 2: badges.append("Weekend Warrior")
    if total_steps >= 200000: badges.append("Mo’ Legend")
    return badges

def get_challenges(today_steps, weekly_steps):
    challenges = []
    if today_steps < 5000: challenges.append("Walk 5,000 steps today for a bonus badge.")
    if weekly_steps < 35000: challenges.append("Hit 35,000 steps this week to unlock ‘Mo’ Momentum’.")
    return challenges

def get_user_level(total_steps):
    if total_steps < 50000: return "Mo’ Rookie"
    elif total_steps < 150000: return "Mo’ Pro"
    else: return "Mo’ Champion"

def generate_shareable_image(username, total_steps, badges):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    d.text((10, 10), f"Movember Stats for {username}", fill=(0, 0, 0), font=font)
    d.text((10, 50), f"Total Steps: {total_steps}", fill=(0, 0, 0), font=font)
    d.text((10, 90), "Badges:", fill=(0, 0, 0), font=font)
    y = 120
    for badge in badges:
        d.text((10, y), f"- {badge}", fill=(0, 0, 0), font=font)
        y += 20
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ------------------ ADD NEW TAB TO EXISTING TABS ------------------

with tab3:
    st.header("🏅 Badges & Achievements")
    st.write("Welcome to the Mo’verse! Earn badges, conquer challenges, and climb the ranks!")

    # Storyline Overview with background
    st.markdown("""
    <div style="
        background-color:#f4f4f8;
        padding:20px;
        border-radius:10px;
        margin-bottom:20px;
        box-shadow:0 2px 8px rgba(0,0,0,0.1);
    ">
        <h3 style="color:#603494;">📖 Your Mo’ Journey</h3>
        <p>Every great adventure starts with a single step. In the Mo’verse, your journey unfolds like this:</p>
        <ul style="font-size:16px; line-height:1.6;">
            <li><b>🌱 Mo’ Rookie</b><br>You’re just starting out—full of energy and ready to learn the ropes.</li>
            <li><b>💪 Mo’ Pro</b><br>A seasoned stepper! You’re smashing goals and inspiring others along the way.</li>
            <li><b>🏆 Mo’ Champion</b><br>The ultimate Mo’ hero—leading the charge for men’s health and making a lasting impact.</li>
        </ul>
        <p>Each step brings you closer to legendary status. Complete challenges, earn badges, and show the world your Mo’ power!</p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch user data
    df = fetch_user_forms(user_id)
    if not df.empty:
        df['form_date'] = pd.to_datetime(df['form_date'], errors='coerce')
        total_steps = df['form_stepcount'].sum()
        today_steps = df[df['form_date'].dt.date == datetime.now().date()]['form_stepcount'].sum()
        week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
        weekly_steps = df[df['form_date'].dt.date >= week_start]['form_stepcount'].sum()
        streak = len(df['form_date'].dt.date.unique())

        badges = calculate_badges(total_steps, streak)
        level = get_user_level(total_steps)

        # Level thresholds
        level_thresholds = {
            "Mo’ Rookie": 0,
            "Mo’ Pro": 50000,
            "Mo’ Champion": 150000
        }

        # Next level logic
        if level == "Mo’ Rookie":
            next_level = "Mo’ Pro"
            steps_to_next = level_thresholds[next_level] - total_steps
        elif level == "Mo’ Pro":
            next_level = "Mo’ Champion"
            steps_to_next = level_thresholds[next_level] - total_steps
        else:
            next_level = None
            steps_to_next = 0

        # Display Current Rank
        st.subheader("🎮 Your Current Rank:")
        st.markdown(f"<h2 style='color:#603494;'>{level}</h2>", unsafe_allow_html=True)
        st.progress(min(total_steps / level_thresholds["Mo’ Champion"], 1.0))
        st.caption("🌱 Mo’ Rookie → 💪 Mo’ Pro → 🏆 Mo’ Champion")

        # Steps remaining
        if next_level:
            st.info(f"🚀 {steps_to_next:,} steps to reach **{next_level}**!")
        else:
            st.success("🎉 You’ve reached the top! Keep going to stay legendary!")

        # Badges
        st.subheader("🏅 Your Badges")
        if badges:
            for badge in badges:
                st.markdown(f"- ✅ {badge}")
        else:
            st.info("No badges yet. Keep moving!")

        # Challenges
        st.subheader("🔥 Challenges")
        challenges = []

        # Daily goal
        if today_steps < 10000:
            challenges.append(f"Hit 10,000 steps today! You’re at {today_steps:,} 🚶")
        else:
            challenges.append("Amazing! You smashed today’s goal! 🎉")

        # Weekly goal
        if weekly_steps < 50000:
            challenges.append(f"Reach 50,000 steps this week! Current: {weekly_steps:,} 🔥")
        else:
            challenges.append("Weekly goal crushed! Keep going! 💪")

        # Next level
        if next_level:
            challenges.append(f"Push for {next_level}! Only {steps_to_next:,} steps left 🚀")

        # Streak challenge
        if streak < 7:
            challenges.append(f"Build a 7-day streak! Current streak: {streak} days 📅")
        else:
            challenges.append(f"🔥 Incredible! {streak}-day streak going strong!")

        # Bonus challenges
        if total_steps < 100000:
            challenges.append("Break 100,000 total steps milestone! 🌟")
        else:
            challenges.append("Legendary! You’ve crossed 100,000 steps! 🏅")

        # Fun extra challenge
        if today_steps >= 15000:
            challenges.append("Double down! Can you hit 20,000 steps today? 💥")
        if weekly_steps >= 70000:
            challenges.append("Stretch goal: 100,000 steps this week! 🚀")

        # Show challenges
        for ch in challenges:
            st.write(f"- {ch}")

#---
import urllib.parse
import os
import streamlit as st

with tab4:
    st.subheader("📢 Share Your Movember Journey on LinkedIn or X")

    if not df.empty:
        # Messages for each asset
        messages = {
            "Move For Movember.png": (
                f"I’ve walked {total_steps:,} steps for Movember! Every step counts towards men’s health. "
                "Join the movement and make a difference! #Movember #MoveForMovember #MensHealth"
            ),
            "Movember Movement.png": (
                f"Currently at {level} level with {total_steps:,} steps! Proud to support Movember and raise awareness "
                "for men’s health. Let’s keep moving! #Movember #MensHealth"
            ),
            "Movember.png": (
                f"Walking for a cause! {total_steps:,} steps completed for Movember. Together, we can change the face of men’s health. "
                "#Movember #MensHealth #Fundraising"
            )
        }

        st.write("Select an image, copy the suggested message, and post it to your socials!")

        asset_dir = os.path.join(os.getcwd(), "assets")
        asset_files = list(messages.keys())

        selected_asset = st.selectbox("Choose an image:", asset_files)

        if selected_asset:
            asset_path = os.path.join(asset_dir, selected_asset)
            if os.path.exists(asset_path):
                st.image(asset_path, caption=selected_asset, width=300)

                message = messages[selected_asset]
                st.subheader("Suggested Message")
                st.text_area("Copy this message:", message, height=100)

                with open(asset_path, "rb") as f:
                    st.download_button(
                        label=f"Download {selected_asset}",
                        data=f,
                        file_name=selected_asset,
                        mime="image/png"
                    )

                encoded_message = urllib.parse.quote(message)

                # Share URLs
                linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url=https://uk.movember.com&summary={encoded_message}"
                twitter_url = f"https://twitter.com/intent/tweet?text={encoded_message}"

                # ✅ Proper HTML for clickable icons
                st.subheader("Quick Share Buttons")
                st.markdown(f"""
                    <style>
                        .share-icons {{
                            display: flex;
                            gap: 20px;
                            margin-top: 10px;
                        }}
                        .share-icons a img {{
                            width: 32px;
                            height: 32px;
                            cursor: pointer;
                            transition: transform 0.2s;
                        }}
                        .share-icons a img:hover {{
                            transform: scale(1.2);
                        }}
                    </style>
                    <div class="share-icons">
                        {linkedin_url}
                            https://cdn-icons-png.flaticon.com/512/174/174857.png
                        </a>
                        {twitter_url}
                            https://cdn-icons-png.flaticon.com/512/733/733579.png
                        </a>
                    </div>
                """, unsafe_allow_html=True)

                st.caption("✅ Click an icon to open the post composer. Attach the downloaded image manually.")
    else:
        st.info("No steps submitted yet. Start moving to unlock badges and share your progress!")