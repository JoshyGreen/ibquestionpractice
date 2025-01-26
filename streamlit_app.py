import streamlit as st

from backend.database import get_db_connection, connect_game_db
from backend.question_handler import get_random_question, get_random_question_by_paper, get_questions_by_syllabus, get_all_syllabus_links
from backend.progress import update_progress, get_progress, reset_progress, mark_as_lacking_context, \
    remove_question_from_progress
from backend.auth import show_signup, show_login

def main():
    # If not logged in, show login or signup
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        # Show login/signup
        tabs = st.tabs(["Login", "Sign Up"])
        with tabs[0]:
            show_login()
        with tabs[1]:
            show_signup()
        return

    # Otherwise, show the main content
    st.sidebar.write(f"Logged in as: {st.session_state['username']}")
    user_id= st.session_state['user_id']
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
    subject = st.sidebar.selectbox("Select Subject", ["Chemistry", "Physics"],
                                   index=0 if st.session_state["subject"] == "Chemistry" else 1)

    st.session_state["subject"] = subject
    if subject == "Chemistry":
        st.title("Chemistry Question Practice Game")
    elif subject == "Physics":
        st.title("Physics Question Practice Game")

    st.sidebar.title("App Modes")
    mode = st.sidebar.selectbox("Mode", ["Practice","History","Analytics"])
    if mode == "Practice":
        st.sidebar.title("Practice Modes")
        # Select Mode
        QuestionMode = st.sidebar.selectbox("Mode", ["Random", "By Paper", "By Syllabus"])
        if QuestionMode == "Random":
            # Only fetch random question when needed
            if "random_question" not in st.session_state:
                st.session_state.random_question = get_random_question(st.session_state["subject"], user_id)
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
                    st.session_state.current_paper_question = get_random_question_by_paper(subject, paper, user_id)

                # Display the current question using the centralized function
                question = st.session_state.current_paper_question
                display_question(subject, QuestionMode, question, user_id)

        elif QuestionMode == "By Syllabus":
            # Fetch all syllabus links and build hierarchy
            if "chem_syllabus_links" not in st.session_state:
                st.session_state.chem_syllabus_links = get_all_syllabus_links("Chemistry")
            if "phys_syllabus_links" not in st.session_state:
                st.session_state.phys_syllabus_links = get_all_syllabus_links("Physics")

            st.session_state.chem_syllabus_hierarchy = build_syllabus_hierarchy(st.session_state.chem_syllabus_links)
            st.session_state.phys_syllabus_hierarchy = build_syllabus_hierarchy(st.session_state.phys_syllabus_links)

            # Render the syllabus hierarchy and get the selected syllabus link
            st.markdown("### Syllabus Hierarchy")
            if subject == "Chemistry":
                selected_syllabus = render_syllabus_hierarchy(st.session_state.chem_syllabus_hierarchy)
            elif subject == "Physics":
                selected_syllabus = render_syllabus_hierarchy(st.session_state.phys_syllabus_hierarchy)
            else:
                selected_syllabus = None

            # Check if the selected syllabus has changed
            if selected_syllabus != st.session_state.selected_syllabus:
                st.session_state.selected_syllabus = selected_syllabus
                st.session_state.current_syllabus_question = None  # Reset the current question

            # Fetch and display a question for the selected syllabus link
            if st.session_state.selected_syllabus:
                if st.session_state.selected_syllabus != st.session_state.previous_syllabus:
                    st.session_state.previous_syllabus = st.session_state.selected_syllabus
                    st.session_state.current_syllabus_question = get_questions_by_syllabus(subject,
                                                                                           st.session_state.selected_syllabus,
                                                                                           user_id)

                # Display the fetched question
                if st.session_state.current_syllabus_question:
                    display_question(subject, QuestionMode, st.session_state.current_syllabus_question, user_id)
                else:
                    st.write("No questions available for this syllabus link!")

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

def apply_css_to_html(html_content):
    """
    Combine the external CSS with the provided HTML content.
    """
    with open("application-a4c8c647abf5b5225a333b85c9518fa4c88c8b07cfba1dc4e8615725b03c4807.css", "r") as f:
        css1 = f.read()
    with open("print-53b80e997a3acfa1245d39590bda6f1f0b2720b92c225d009afd1743db97aaf1.css", "r") as f:
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
        options = list(current_level.keys())
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

def display_question(subject, QuestionMode, question, user_id):
    if question:
        question_id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html = question

        # Apply CSS to the question HTML
        styled_html = apply_css_to_html(html)
        styled_markscheme_html = apply_css_to_html(markscheme_html)
        styled_examiner_notes = apply_css_to_html(examiner_report_html)

        # Display question metadata
        st.markdown(f"**Paper:** {paper}")
        st.markdown(f"**Reference Code:** {reference_code}")
        st.markdown(f"**Syllabus Link:** {syllabus_link}")
        st.markdown(f"**Maximum Marks:** {maximum_marks}")
        st.markdown(f"**Level:** {level}")

        # Render the styled HTML ar
        st.markdown(styled_html, unsafe_allow_html=True)

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
                "Show Examiner Notes" if not st.session_state[f"show_examiner_notes_{question_id}"] else "Hide Examiner Notes",
                key=f"examiner_notes_toggle_{question_id}",
            ):
                st.session_state[f"show_examiner_notes_{question_id}"] = not st.session_state[f"show_examiner_notes_{question_id}"]
                st.rerun()  # Immediately refresh the app

            if st.session_state[f"show_examiner_notes_{question_id}"]:
                st.markdown("### Examiner Notes")
                st.markdown(examiner_report_html, unsafe_allow_html=True)

        # Add buttons for progress tracking
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Correct", key=f"correct_{question_id}"):
                update_progress(subject, question_id, "correct", user_id)
                load_next_question(subject, QuestionMode, user_id)
                st.rerun()
        with col2:
            if st.button("Partially Correct", key=f"partially_correct_{question_id}"):
                update_progress(subject, question_id, "partially_correct", user_id)
                load_next_question(subject, QuestionMode, user_id)
                st.rerun()
        with col3:
            if st.button("Incorrect", key=f"incorrect_{question_id}"):
                update_progress(subject, question_id, "incorrect", user_id)
                load_next_question(subject, QuestionMode, user_id)
                st.rerun()
        with col4:
            if st.button("Lack Context", key=f"lacking_context_{question_id}"):
                mark_as_lacking_context(subject, question_id, user_id)
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
    Displays the 30 most recently answered questions for the given user,
    fetching user_progress rows from questions_game.db,
    then fetching question details from ChemQuestionsDatabase.db.
    """

    # -------------------------------
    # 1) Fetch user_progress from questions_game.db
    # -------------------------------
    game_conn = connect_game_db()
    game_cursor = game_conn.cursor()

    # Suppose we store the last updated time in 'updated_at'
    # and we only want to show questions where reviewed=1
    if subject=="Chemistry":
        query = """
                    SELECT question_id,
                           correct_count,
                           partially_correct_count,
                           incorrect_count,
                           updated_at
                    FROM user_progress_chemistry
                    WHERE user_id = ? AND reviewed = 1
                    ORDER BY updated_at DESC
                    LIMIT 30
                """
    elif subject=="Physics":
        query = """
                    SELECT question_id,
                           correct_count,
                           partially_correct_count,
                           incorrect_count,
                           updated_at
                    FROM user_progress_physics
                    WHERE user_id = ? AND reviewed = 1
                    ORDER BY updated_at DESC
                    LIMIT 30
                """
    else:
        query = None
    game_cursor.execute(query, (user_id,))
    progress_rows = game_cursor.fetchall()

    game_conn.close()

    if not progress_rows:
        st.write("No recently answered questions to show.")
        return

    # -------------------------------
    # 2) For each question_id, look up question info in ChemQuestionsDatabase.db
    # -------------------------------
    conn = get_db_connection(subject)
    cursor = conn.cursor()

    final_results = []
    for (q_id, correct, partial, incorrect, updated_at) in progress_rows:
        # Retrieve the question data from the chem DB
        cursor.execute("""
            SELECT reference_code, paper
            FROM questions
            WHERE id = ?
        """, (q_id,))
        question_row = cursor.fetchone()
        col1, col2 = st.columns(2)
        # "Show Question" button
        with col1:
            if st.button("Show Question", key=f"show_{q_id}"):
                st.session_state["show_history_question_id"] = q_id
                st.rerun()

        # "Remove from Progress" button
        with col2:
            if st.button("Remove from History", key=f"remove_{q_id}"):
                remove_question_from_progress(q_id, user_id)
                st.success(f"Removed question {q_id} from your progress.")
                st.rerun()
        if question_row:
            reference_code, paper = question_row
            final_results.append({
                "question_id": q_id,
                "reference_code": reference_code,
                "paper": paper,
                "correct": correct,
                "partial": partial,
                "incorrect": incorrect,
                "updated_at": updated_at
            })


    conn.close()

    # -------------------------------
    # 3) Display the combined data
    # -------------------------------
    st.write("### Recently Answered Questions")
    for item in final_results:
        st.markdown(
            f"- **Question {item['question_id']}** "
            f"(Paper: {item['paper']}, Ref: {item['reference_code']}) "
            f"| Correct: {item['correct']}, Partial: {item['partial']}, Incorrect: {item['incorrect']} "
            f"| Last answered on {item['updated_at']}"
        )

def show_analytics(subject, user_id):
    conn = connect_game_db()
    cursor = conn.cursor()

    # 1) Count correct, partial, incorrect for the user
    if subject == "Chemistry":
        query = """
                    SELECT SUM(correct_count), SUM(partially_correct_count), SUM(incorrect_count)
                    FROM user_progress_chemistry
                    WHERE user_id = ?
                """
    elif subject == "Physics":
        query = """
                    SELECT SUM(correct_count), SUM(partially_correct_count), SUM(incorrect_count)
                    FROM user_progress_physics
                    WHERE user_id = ?
                """
    else:
        query = None
    cursor.execute(query, (user_id,))
    correct_total, partial_total, incorrect_total = cursor.fetchone()
    correct_total = correct_total or 0
    partial_total = partial_total or 0
    incorrect_total = incorrect_total or 0

    st.write("### Overall Performance")
    st.write(f"**Correct:** {correct_total}")
    st.write(f"**Partially Correct:** {partial_total}")
    st.write(f"**Incorrect:** {incorrect_total}")

    # 2) Possibly a bar chart
    import pandas as pd
    data = {
        "Status": ["Correct", "Partially Correct", "Incorrect"],
        "Count": [correct_total, partial_total, incorrect_total]
    }
    df = pd.DataFrame(data)
    st.bar_chart(data=df, x="Status", y="Count")

    conn.close()

if __name__ == "__main__":
    main()
