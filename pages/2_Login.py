import streamlit as st
import json
import hashlib
import os

CREDENTIALS_FILE = "credentials.json"

# Load credentials
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    return {}

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    credentials = load_credentials()
    if username in credentials and credentials[username]["password"] == hash_password(password):
        return credentials[username]["role"]
    return None

st.title("Log In")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""

if st.session_state.logged_in:
    st.info(f"Already logged in as **{st.session_state.username}** ({st.session_state.role}).")
else:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")

    if submitted:
        role = authenticate(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.success(f"Login successful! Role: {role}")
        else:
            st.error("Invalid username or password.")

# Sidebar info
if st.session_state.get("username"):
    st.sidebar.markdown(f"**User:** {st.session_state.username} ({st.session_state.role})")

# Logout button
if st.button("Logout"):
    st.session_state.clear()

# Link to Sign-Up page
st.markdown("---")
st.markdown("Don't have an account? Signup")