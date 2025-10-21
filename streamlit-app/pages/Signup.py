import streamlit as st
import json
import os
import hashlib

CREDENTIALS_FILE = "credentials.json"

# Load existing credentials
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save credentials
def save_credentials(credentials):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f)

# Hash password for security
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

st.title("Sign Up")

credentials = load_credentials()

with st.form("signup_form"):
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    submitted = st.form_submit_button("Sign Up")

if submitted:
    if username in credentials:
        st.error("Username already exists. Please choose another.")
    elif not username or not password:
        st.error("Please enter both username and password.")
    else:
        credentials[username] = {"password": hash_password(password), "role": role}
        save_credentials(credentials)
        st.success(f"Account created successfully! You can now log in as {username}.")