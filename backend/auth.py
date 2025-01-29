import streamlit as st
import bcrypt
from backend.database import connect_game_db

# -------------------------
# Password hashing helpers
# -------------------------
def hash_password(password: str) -> str:
    # bcrypt.gensalt() automatically handles generating the salt
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

# -------------------------
# Sign-up logic
# -------------------------
def sign_up(username: str, password: str) -> (bool, str):
    """
    Creates a new user in the 'users' table with the given username and hashed password.
    Returns (success, message).
    """
    conn = connect_game_db()
    cursor = conn.cursor()

    # Check if username already exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return False, "Username is already taken."

    # Insert new user
    hashed_pw = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hashed_pw)
    )
    conn.commit()
    conn.close()

    return True, "Sign-up successful! You can now log in."

def show_signup():
    """
    Streamlit UI to handle new user sign-up.
    You can place this in app.py if you prefer, but it's often nice to keep it here.
    """
    st.subheader("Sign Up")
    username = st.text_input("Username", key="024123")
    password = st.text_input("Password", key="124053",  type="password")
    confirm_password = st.text_input("Confirm Password", key="1230492", type="password")

    if st.button("Create Account"):
        if not username or not password:
            st.error("Username and Password cannot be empty.")
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        success, msg = sign_up(username, password)
        if success:
            st.success(msg)
        else:
            st.error(msg)

def show_login():
    st.write("## Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        success, user_id = login(username, password)
        if success:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["user_id"] = user_id
            st.rerun()
        else:
            st.error("Invalid username or password")

def login(username, password):
    conn = connect_game_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        user_id, password_hash = row
        if check_password(password, password_hash):
            return True, user_id
    return False, None