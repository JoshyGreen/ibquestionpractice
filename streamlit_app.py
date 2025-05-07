import streamlit as st
from backend.database import get_db_connection
from bs4 import BeautifulSoup
from backend.question_handler import get_random_question, get_random_question_by_paper, get_questions_by_syllabus, \
    get_all_syllabus_links, fetch_question_by_id, get_all_questions_by_syllabus
from backend.progress import update_progress, get_progress, reset_progress, mark_as_lacking_context
from backend.auth import initialize_session, show_signup, is_logged_in, logout, show_login
from supabase import create_client, Client
import pandas as pd

SUPABASE_URL = "https://ofaiofljgsxuamzaensq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mYWlvZmxqZ3N4dWFtemFlbnNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk1NDc5NTcsImV4cCI6MjA1NTEyMzk1N30.jvMpQavl14H-kBr8x576VXGTizZ3yBoi7P-oEEQckuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def main():
    initialize_session()  # Ensure session keys exist

    if not is_logged_in():
        # 🔹 Show Login & Sign-Up tabs before logging in
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            show_login()
        with tab2:
            show_signup()
        return  # Stop execution so the sidebar doesn't appear

    # 🔹 Sidebar only appears after login
    st.sidebar.write(f"Logged in as: {st.session_state['username']}")
    if st.sidebar.button("Logout"):
        logout()

    # 🔹 Main content after login
    user_id = st.session_state['user_id']
    # Initialize session state variables
    if "current_paper_type" not in st.session_state:
        st.session_state.current_paper_type = None

    if "selected_syllabus" not in st.session_state:
        st.session_state.selected_syllabus = None

    if "previous_syllabus" not in st.session_state:
        st.session_state.previous_syllabus = None

    if "current_syllabus_question" not in st.session_state:
        st.session_state.current_syllabus_question = None

    st.sidebar.title("Subject")
    if "subject" not in st.session_state:
        st.session_state["subject"] = "Chemistry"
    if "hl" not in st.session_state:
        st.session_state.hl = True


    subjects = ["Chemistry", "Physics", "MathAA", "MathAI", "CompSci" ]
    # Safely figure out which index the current subject has in the list
    default_idx = subjects.index(st.session_state["subject"]) if st.session_state["subject"] in subjects else 0

    subject = st.sidebar.selectbox(
        "Select Subject",
        subjects,
        index=default_idx
    )

    sl_only = st.sidebar.checkbox("Standard Level only", value=False)
    st.session_state["sl_only"] = sl_only

    if "previous_subject" not in st.session_state:
        st.session_state.previous_subject = st.session_state["subject"]

    # If the user just changed the subject, reset random_question, current_paper_question, etc.

    st.session_state["subject"] = subject

    st.title(f"{subject} Question Practice Game")

    st.sidebar.title("App Modes")
    mode = st.sidebar.selectbox("Mode", ["Practice", "History", "Analytics"])
    if mode == "Practice":
        st.sidebar.title("Practice Modes")
        # Select Mode
        QuestionMode = st.sidebar.selectbox("Mode", ["Random", "By Paper", "By Syllabus"])
        if st.session_state["subject"] != st.session_state.previous_subject:
            st.session_state.random_question = load_next_question(subject, QuestionMode, user_id)
            st.session_state.current_paper_question = load_next_question(subject, QuestionMode, user_id)
            st.session_state.current_syllabus_question = load_next_question(subject, QuestionMode, user_id)
            st.session_state.previous_subject = st.session_state["subject"]
        if QuestionMode == "Random":
            # Only fetch random question when needed
            if "random_question" not in st.session_state:
                st.session_state.random_question = get_random_question(st.session_state["subject"], user_id, hl=!(st.session_state["sl_only"]))
            display_question(subject, QuestionMode, st.session_state.random_question, user_id)
        elif QuestionMode == "By Paper":
            # Track the paper type in session state
            if "current_paper_type" not in st.session_state:
                st.session_state.current_paper_type = ""

            if "current_paper_question" not in st.session_state:
                st.session_state.current_paper_question = None

            # Input for selecting paper type
            paper = st.sidebar.text_input("Enter Paper Type:")

            # Reset question if paper type changes
            if paper != st.session_state.current_paper_type:
                st.session_state.current_paper_type = paper
                st.session_state.current_paper_question = None

            if paper:
                # Fetch a new random question if needed
                if st.session_state.current_paper_question is None:
                    st.session_state.current_paper_question = get_random_question_by_paper(subject, paper, user_id, hl=!(st.session_state["sl_only"]))

                # Display the current question using the centralized function
                question = st.session_state.current_paper_question
                display_question(subject, QuestionMode, question, user_id)

        elif QuestionMode == "By Syllabus":
            # Fetch all syllabus links and build hierarchy
            if f"{subject}_syllabus_links" not in st.session_state:
                st.session_state.syllabus_links = get_all_syllabus_links(subject)
        
            st.session_state.syllabus_hierarchy = build_syllabus_hierarchy(st.session_state.syllabus_links)
        
            # Render the syllabus hierarchy and get the selected syllabus link
            st.markdown("### Syllabus Hierarchy")
            show_all = st.checkbox("Show All Questions for this Syllabus.")
            selected_syllabus = render_syllabus_hierarchy(st.session_state.syllabus_hierarchy)
        
            # If the selected syllabus has changed, update the session and reset the current question
            if selected_syllabus != st.session_state.selected_syllabus:
                st.session_state.selected_syllabus = selected_syllabus
                st.session_state.current_syllabus_question = None  # Reset to force reloading a question
        
            # Only attempt to fetch and display questions if a syllabus has been selected
            if st.session_state.selected_syllabus:
                if show_all:
                    # Only load questions if not already fetched
                    if st.session_state.current_syllabus_question is None:
                        st.session_state.current_syllabus_question = get_all_questions_by_syllabus(
                            subject, st.session_state.selected_syllabus
                        )
                    if st.session_state.current_syllabus_question:
                        for question in st.session_state.current_syllabus_question:
                            display_question(subject, QuestionMode, question, user_id)
                else:
                    # Only fetch a single question if it's not already loaded
                    if st.session_state.current_syllabus_question is None:
                        st.session_state.current_syllabus_question = get_questions_by_syllabus(
                            subject, st.session_state.selected_syllabus, user_id
                        )
                    if st.session_state.current_syllabus_question:
                        display_question(subject, QuestionMode, st.session_state.current_syllabus_question, user_id)

            
           

        # Progress Bar
        reviewed, total = get_progress(subject, user_id)
        st.sidebar.write(f"Progress: {reviewed}/{total}")
        st.sidebar.progress(reviewed / total if total > 0 else 0)

        # Confirmation logic for Reset Progress
        if "confirm_reset" not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:
            # Initial Reset Progress button
            if st.sidebar.button("Reset Progress"):
                st.session_state.confirm_reset = True
        else:
            # Display confirmation buttons
            st.sidebar.warning("Are you sure you want to reset all progress? This action cannot be undone.")
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("Yes, Reset"):
                    reset_progress(subject, user_id)  # Call the reset function
                    st.session_state.random_question = get_random_question(subject,
                                                                           user_id)  # Fetch a new random question
                    st.session_state.confirm_reset = False  # Reset confirmation state
                    st.rerun()  # Reload the app
            with col2:
                if st.button("Cancel"):
                    st.session_state.confirm_reset = False  # Cancel confirmation
    elif mode == "History":
        show_history(subject, user_id)
    elif mode == "Analytics":
        show_analytics(subject, user_id)


# Cache progress data to prevent repetitive queries
@st.cache_data
def load_progress(subject, user_id):
    return get_progress(subject, user_id)


def apply_css_to_html(html_content, subject):
    """
    Combine the external CSS with the provided HTML content.
    """
    if subject == "Chemistry" or subject == "Physics":
        with open("application-a4c8c647abf5b5225a333b85c9518fa4c88c8b07cfba1dc4e8615725b03c4807.css", "r") as f:
            css1 = f.read()
        with open("print-53b80e997a3acfa1245d39590bda6f1f0b2720b92c225d009afd1743db97aaf1.css", "r") as f:
            css2 = f.read()
    else:
        with open("application-02ef852527079acf252dc4c9b2922c93db8fde2b6bff7c3c7f657634ae024ff1.css", "r") as f:
            css1 = f.read()
        with open("print-6da094505524acaa25ea39a4dd5d6130a436fc43336c0bb89199951b860e98e9.css", "r") as f:
            css2 = f.read()

    # Inline the CSS with the HTML
    inline_css = f"<style>{css1}\n{css2}</style>"
    return f"{inline_css}\n{html_content}"


def build_syllabus_hierarchy(links):
    """
    Build a hierarchical structure from syllabus links.
    Handles multiple syllabus links and nested levels.
    """
    hierarchy = {}
    for link in links:
        # Handle multiple syllabus links for a single question
        individual_links = [l.strip() for l in link.split("||") if l.strip()]
        for individual_link in individual_links:
            # Create a hierarchy for the current link
            parts = [part.strip() for part in individual_link.split("»") if part.strip()]
            current_level = hierarchy
            for part in parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
    return hierarchy


def render_syllabus_hierarchy(hierarchy):
    """
    Render the syllabus hierarchy interactively and return the selected syllabus link.
    """
    current_level = hierarchy
    selected_parts = []

    # Iterate through the hierarchy levels
    for depth in range(10):  # Assume a max depth of 10 levels
        if not current_level:
            break

        # Create a unique key for each level of the hierarchy
        options = sorted(list(current_level.keys()))
        if not options:
            break

        selected_key = f"selected_level_{depth}"
        default_value = st.session_state.get(selected_key, options[0])

        # Render a dropdown for the current level
        selected = st.selectbox(
            f"Level {depth + 1}",
            options,
            index=options.index(default_value) if default_value in options else 0,
            key=selected_key,
        )

        # Save the selected part
        selected_parts.append(selected)
        current_level = current_level[selected]

    # Combine selected parts into a full path
    return " » ".join(selected_parts)

def extract_cardbody(html):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find('div', class_='card-body').get_text()

def display_question(subject, QuestionMode, question, user_id, toggle_key=None, hl=True):
    if question:
        question_id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html = question

        # Apply CSS to the question HTML
        styled_html = apply_css_to_html(html, subject)
        styled_markscheme_html = apply_css_to_html(markscheme_html, subject)
        styled_examiner_notes = apply_css_to_html(examiner_report_html, subject)

        # Display question metadata
        st.markdown(f"**Paper:** {paper}")
        st.markdown(f"**Reference Code:** {reference_code}")
        st.markdown(f"**Syllabus Link:** {syllabus_link}")
        st.markdown(f"**Maximum Marks:** {maximum_marks}")
        st.markdown(f"**Level:** {level}")

        # Render the styled HTML ar
        st.markdown(styled_html, unsafe_allow_html=True)
        if (subject in ["Chemistry", "Physics"]) and paper == "1A":
            # Extract the correct MCQ letter, e.g., "C" or "A"
            correct_option = extract_cardbody(markscheme_html).strip()  # You already have this function

            # We'll store the user's MCQ choice in a radio button,
            # and also track whether they've submitted.
            mc_key = f"mc_choice_{question_id}"
            submitted_key = f"mc_submitted_{question_id}"
            feedback_key = f"mc_feedback_{question_id}"

            # 1) Initialize session state if needed
            if mc_key not in st.session_state:
                st.session_state[mc_key] = "A"  # Default to "A"
            if submitted_key not in st.session_state:
                st.session_state[submitted_key] = False
            if feedback_key not in st.session_state:
                st.session_state[feedback_key] = ""

            # 2) If the user has *not* submitted yet, show the radio and "Submit Answer" button
            if not st.session_state[submitted_key]:
                mc_key = f"mc_choice_{question_id}"
                submitted_key = f"mc_submitted_{question_id}"

                # Initialize defaults if needed:
                if mc_key not in st.session_state:
                    st.session_state[mc_key] = "A"
                if submitted_key not in st.session_state:
                    st.session_state[submitted_key] = False

                # Just call st.radio(...) and store its return value
                user_choice = st.radio(
                    "Select your answer:",
                    options=["A", "B", "C", "D"],
                    index=["A", "B", "C", "D"].index(st.session_state[mc_key]),
                    key=mc_key
                )
                col5, col6 = st.columns(2)
                with col5:
                    if st.button("Submit Answer", key=f"submit_{question_id}"):
                        user_choice = st.session_state[mc_key]
                        # Compare user choice to correct option
                        if user_choice == correct_option:
                            st.session_state[feedback_key] = f"✅ Correct! The answer is **{correct_option}**."
                            update_progress(subject, question_id, "correct", user_id)
                        else:
                            st.session_state[feedback_key] = (
                                f"❌ Incorrect. You chose **{user_choice}**, "
                                f"but the correct answer is **{correct_option}**."
                            )
                            update_progress(subject, question_id, "incorrect", user_id)

                        # Mark "submitted" so we can show feedback + Next
                        st.session_state[submitted_key] = True
                        # We *don't* rerun now. We want to show feedback immediately in the same run.
                with col6:
                    if st.button("Lack Context", key=f"lacking_context_{question_id}"):
                        mark_as_lacking_context(subject, question_id, user_id)
                        st.session_state[submitted_key] = True


            # 3) If the user *has* submitted, show the feedback and "Next" button
            if st.session_state[submitted_key]:
                # Show the feedback message
                st.write(st.session_state[feedback_key])

                # Optionally show examiner notes
                if examiner_report_html and examiner_report_html.strip():
                    st.markdown("### Examiner Notes")
                    st.markdown(styled_examiner_notes, unsafe_allow_html=True)

                # "Next" button
                if st.button("Next", key=f"next_{question_id}"):
                    # Reset submission for next time
                    st.session_state[submitted_key] = False
                    st.session_state[feedback_key] = ""

                    # Optionally clear the MCQ choice if you want to reset
                    st.session_state[mc_key] = "A"
                    load_next_question(subject, QuestionMode, user_id)
                    st.rerun()
            return

        # Show/Hide Markscheme Logic
        if f"show_markscheme_{question_id}" not in st.session_state:
            st.session_state[f"show_markscheme_{question_id}"] = False

        if st.button(
                "Show Markscheme" if not st.session_state[f"show_markscheme_{question_id}"] else "Hide Markscheme",
                key=f"markscheme_toggle_{question_id}",
        ):
            st.session_state[f"show_markscheme_{question_id}"] = not st.session_state[f"show_markscheme_{question_id}"]
            st.rerun()  # Immediately refresh the app

        if st.session_state[f"show_markscheme_{question_id}"]:
            st.markdown("### Markscheme")
            st.markdown(styled_markscheme_html, unsafe_allow_html=True)

        # Show Examiner Notes Logic (only if examiner_report_html is not empty)
        if examiner_report_html and examiner_report_html.strip():
            if f"show_examiner_notes_{question_id}" not in st.session_state:
                st.session_state[f"show_examiner_notes_{question_id}"] = False

            if st.button(
                    "Show Examiner Notes" if not st.session_state[
                        f"show_examiner_notes_{question_id}"] else "Hide Examiner Notes",
                    key=f"examiner_notes_toggle_{question_id}",
            ):
                st.session_state[f"show_examiner_notes_{question_id}"] = not st.session_state[
                    f"show_examiner_notes_{question_id}"]
                st.rerun()  # Immediately refresh the app

            if st.session_state[f"show_examiner_notes_{question_id}"]:
                st.markdown("### Examiner Notes")
                st.markdown(examiner_report_html, unsafe_allow_html=True)

        # Add buttons for progress tracking
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Correct", key=f"correct_{question_id}"):
                update_progress(subject, question_id, "correct", user_id)
                if QuestionMode == "Fetch":
                    st.session_state[toggle_key] = False
                else:
                    load_next_question(subject, QuestionMode, user_id)
                st.rerun()
        with col2:
            if st.button("Partially Correct", key=f"partially_correct_{question_id}"):
                update_progress(subject, question_id, "partially_correct", user_id)
                if QuestionMode == "Fetch":
                    st.session_state[toggle_key] = False
                else:
                    load_next_question(subject, QuestionMode, user_id)
                st.rerun()
        with col3:
            if st.button("Incorrect", key=f"incorrect_{question_id}"):
                update_progress(subject, question_id, "incorrect", user_id)
                if QuestionMode == "Fetch":
                    st.session_state[toggle_key] = False
                else:
                    load_next_question(subject, QuestionMode, user_id)
                st.rerun()
        with col4:
            if st.button("Lack Context", key=f"lacking_context_{question_id}"):
                mark_as_lacking_context(subject, question_id, user_id)
                if QuestionMode == "Fetch":
                    st.session_state[toggle_key] = False
                else:
                    load_next_question(subject, QuestionMode, user_id)
                st.rerun()
    else:
        st.write("No more questions available!")


def load_next_question(subject, mode, user_id):
    if mode == "Random":
        st.session_state.random_question = get_random_question(subject, user_id)
    elif mode == "By Paper":
        paper = st.session_state.current_paper_type
        st.session_state.current_paper_question = get_random_question_by_paper(subject, paper, user_id)
    elif mode == "By Syllabus":
        syllabus = st.session_state.selected_syllabus
        st.session_state.current_syllabus_question = get_questions_by_syllabus(subject, syllabus, user_id)


def debug_syllabus_hierarchy(hierarchy, level=0):
    """
    Recursively display the syllabus hierarchy with proper indentation.
    Handles multi-level and multi-link hierarchies.
    """
    for key, sub_hierarchy in hierarchy.items():
        # Add indentation for each level of the hierarchy
        indent = "&nbsp;" * (level * 4)  # 4 spaces per level
        st.markdown(f"{indent}- **{key}**", unsafe_allow_html=True)

        # Recursively call for sub-hierarchies
        if isinstance(sub_hierarchy, dict):
            debug_syllabus_hierarchy(sub_hierarchy, level + 1)


def show_history(subject, user_id):
    """
    Displays the 30 most recently answered questions for the given user.
    - Retrieves progress from Supabase
    - Retrieves question details from SQLite
    """

    # -------------------------------
    # 1) Fetch user progress from Supabase
    # -------------------------------
    response = (
        supabase.table(subject.lower())
        .select("question_id, correct_count, partially_correct_count, incorrect_count, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(30)
        .execute()
    )

    progress_rows = response.data if response.data else []

    if not progress_rows:
        st.write("No recently answered questions to show.")
        return

    # -------------------------------
    # 2) Fetch question details from SQLite
    # -------------------------------
    conn = get_db_connection(subject)
    cursor = conn.cursor()

    final_results = []
    for row in progress_rows:
        q_id = row["question_id"]
        cursor.execute(
            """
            SELECT reference_code, paper
            FROM questions
            WHERE id = ?
            """,
            (q_id,),
        )
        question_row = cursor.fetchone()

        if question_row:
            reference_code, paper = question_row
            final_results.append({
                "question_id": q_id,
                "reference_code": reference_code,
                "paper": paper,
                "correct": row["correct_count"],
                "partial": row["partially_correct_count"],
                "incorrect": row["incorrect_count"],
                "updated_at": row["updated_at"]
            })

    conn.close()

    # -------------------------------
    # 3) Display Data
    # -------------------------------
    st.write("### Recently Answered Questions")
    for item in final_results:
        q_id = item['question_id']

        st.markdown(
            f"- **Question {q_id}** "
            f"(Paper: {item['paper']}, Ref: {item['reference_code']}) "
            f"| ✅ Correct: {item['correct']} | ⚠️ Partial: {item['partial']} | ❌ Incorrect: {item['incorrect']} "
            f"| 🕒 Last answered on {item['updated_at']}"
        )

        col1, col2 = st.columns(2)

        # Show/Hide Question Toggle
        toggle_key = f"show_question_{q_id}"
        if toggle_key not in st.session_state:
            st.session_state[toggle_key] = False

        with col1:
            btn_label = "Show Question" if not st.session_state[toggle_key] else "Hide Question"
            if st.button(btn_label, key=f"question_toggle_{q_id}"):
                st.session_state[toggle_key] = not st.session_state[toggle_key]
                st.rerun()

        # Remove from History
        with col2:
            if st.button("Remove from History", key=f"remove_{q_id}"):
                supabase.table(subject.lower()).delete().eq("user_id", user_id).eq("question_id", q_id).execute()
                st.success(f"Removed question {q_id} from your history.")
                st.rerun()

        # Conditionally Display Question
        if st.session_state[toggle_key]:
            question_tuple = fetch_question_by_id(subject, q_id)
            display_question(subject, "Review", question_tuple, user_id, toggle_key)


def show_analytics(subject, user_id):
    """
    Displays user analytics, including overall performance, accuracy,
    total attempts, and a leaderboard of all users in the subject.
    """

    # -------------------------------
    # 1) Fetch User Performance from Supabase
    # -------------------------------
    response = (
        supabase.table(subject.lower())
        .select("correct_count, partially_correct_count, incorrect_count")
        .eq("user_id", user_id)
        .execute()
    )

    records = response.data if response.data else []

    # Compute totals
    correct_total = sum(1 for row in records if row["correct_count"])
    partial_total = sum(1 for row in records if row["partially_correct_count"])
    incorrect_total = sum(1 for row in records if row["incorrect_count"])
    total_attempts = correct_total + partial_total + incorrect_total
    accuracy = (correct_total / total_attempts * 100) if total_attempts > 0 else 0

    st.write("### 📊 Overall Performance")
    st.write(f"**✅ Correct:** {correct_total}")
    st.write(f"**⚠️ Partially Correct:** {partial_total}")
    st.write(f"**❌ Incorrect:** {incorrect_total}")
    st.write(f"**Total Questions Attempted:** {total_attempts}")
    st.write(f"**🎯 Accuracy:** {accuracy:.2f}%")

    # -------------------------------
    # 2) Generate Performance Bar Chart
    # -------------------------------
    df = pd.DataFrame({
        "Status": ["Correct", "Partially Correct", "Incorrect"],
        "Count": [correct_total, partial_total, incorrect_total]
    })
    st.bar_chart(df, x="Status", y="Count")

    # -------------------------------
    # 3) Fetch Leaderboard with Usernames from Supabase
    # -------------------------------
    leaderboard_response = (
        supabase.rpc("get_leaderboard", {"subject": subject.lower()})
        .execute()
    )

    leaderboard_data = leaderboard_response.data if leaderboard_response.data else []

    if leaderboard_data:
        leaderboard_df = pd.DataFrame(leaderboard_data)
        leaderboard_df["Rank"] = leaderboard_df["total_correct"].rank(ascending=False, method="min").astype(int)
        leaderboard_df = leaderboard_df.sort_values(by="Rank")

        st.write("### 🏆 Leaderboard (Most Correct Answers)")
        st.dataframe(leaderboard_df, hide_index=True)

    # -------------------------------
    # 4) Performance Over Time
    # -------------------------------
    response = (
        supabase.table(subject.lower())
        .select("updated_at, correct_count")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)  # ✅ Corrected sorting
        .execute()
    )

    trend_data = response.data if response.data else []

    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        trend_df["updated_at"] = pd.to_datetime(trend_df["updated_at"])
        trend_df.set_index("updated_at", inplace=True)

        st.write("### 📈 Performance Over Time")
        st.line_chart(trend_df["correct_count"])

    st.write("🎯 Keep practicing and track your progress!")


if __name__ == "__main__":
    main()
