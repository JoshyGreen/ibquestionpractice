import streamlit as st
from supabase import create_client, Client
import bcrypt

SUPABASE_URL = "https://ofaiofljgsxuamzaensq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mYWlvZmxqZ3N4dWFtemFlbnNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk1NDc5NTcsImV4cCI6MjA1NTEyMzk1N30.jvMpQavl14H-kBr8x576VXGTizZ3yBoi7P-oEEQckuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def initialize_session():
    """Ensure session state variables are initialized."""
    if "session" not in st.session_state:
        st.session_state["session"] = None
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None


def save_session(session):
    """Save session information in Streamlit session state."""
    st.session_state["session"] = session
    st.session_state["logged_in"] = True
    st.session_state["user_id"] = session["user"]["id"]
    st.session_state["username"] = get_username(session["user"]["id"])
    st.session_state["access_token"] = session["access_token"]  # Save token for persistence
    st.rerun()


def get_username(user_id):
    """Fetch username from Supabase using the user_id."""
    response = supabase.table("users").select("username").eq("id", user_id).execute()
    if response.data:
        return response.data[0]["username"]
    return "Unknown"


def is_logged_in():
    """Check if the user is logged in based on stored session or re-authenticate."""
    if st.session_state["logged_in"]:
        return True

    # If user has an access token from a previous session, try to validate it
    if "access_token" in st.session_state and st.session_state["access_token"]:
        try:
            user = supabase.auth.get_user(st.session_state["access_token"])
            if user:
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user.id
                st.session_state["username"] = get_username(user.id)
                return True
        except Exception:
            pass

    return False


def logout():
    """Log the user out and clear session data."""
    supabase.auth.sign_out()
    for key in ["session", "logged_in", "user_id", "username", "access_token"]:
        st.session_state[key] = None
    st.rerun()


def login(username, password):
    """Authenticate user and store session."""
    response = supabase.table("users").select("id, password_hash").eq("username", username).execute()

    if response.data:
        user = response.data[0]
        stored_password_hash = user["password_hash"]

        # Verify password using bcrypt
        if bcrypt.checkpw(password.encode(), stored_password_hash.encode()):
            # Generate a Supabase session manually (optional)
            session = {"user": {"id": user["id"]}, "access_token": "dummy_token"}
            save_session(session)
            return True
    return False


def sign_up(username, password):
    """Register a new user in Supabase."""
    response = supabase.table("users").select("id").eq("username", username).execute()
    if response.data:
        return False, "Username already exists."

    # Hash password before storing
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    data = {"username": username, "password_hash": hashed_pw}
    insert_response = supabase.table("users").insert(data).execute()

    if insert_response.data:
        return True, "Sign-up successful! You can now log in."
    return False, "An error occurred."


def show_login():
    """Show login UI inside a tab."""
    st.subheader("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        success = login(username, password)
        if success:
            st.success("Login successful! Redirecting...")
            st.rerun()
        else:
            st.error("Invalid username or password")


def show_signup():
    """Show sign-up UI inside a tab."""
    st.subheader("Sign Up")
    username = st.text_input("Username", key="signup_username")
    password = st.text_input("Password", type="password", key="signup_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")

    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        success, message = sign_up(username, password)
        if success:
            st.success(message)
        else:
            st.error(message)



