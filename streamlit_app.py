import streamlit as st
from bs4 import BeautifulSoup

from backend.database import get_db_connection, connect_game_db
from backend.question_handler import get_random_question, get_random_question_by_paper, get_questions_by_syllabus, \
    get_all_syllabus_links, fetch_question_by_id, get_all_questions_by_syllabus
from backend.progress import update_progress, get_progress, reset_progress, mark_as_lacking_context, \
    remove_question_from_history
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

    subjects = ["Chemistry", "Physics", "Mathematics"]
    # Safely figure out which index the current subject has in the list
    default_idx = subjects.index(st.session_state["subject"]) if st.session_state["subject"] in subjects else 0

    subject = st.sidebar.selectbox(
        "Select Subject",
        subjects,
        index=default_idx
    )
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
            if "math_syllabus_links" not in st.session_state:
                st.session_state.math_syllabus_links = get_all_syllabus_links("Mathematics")

            st.session_state.chem_syllabus_hierarchy = build_syllabus_hierarchy(st.session_state.chem_syllabus_links)
            st.session_state.phys_syllabus_hierarchy = build_syllabus_hierarchy(st.session_state.phys_syllabus_links)
            st.session_state.math_syllabus_hierarchy = build_syllabus_hierarchy(st.session_state.math_syllabus_links)
            _hierarchy = build_syllabus_hierarchy(st.session_state.math_syllabus_links)
            # Render the syllabus hierarchy and get the selected syllabus link
            st.markdown("### Syllabus Hierarchy")
            # Show the "Show All Questions" checkbox
            show_all = st.checkbox("Show All Questions for this Syllabus.")

            if subject == "Chemistry":
                selected_syllabus = render_syllabus_hierarchy(st.session_state.chem_syllabus_hierarchy)
            elif subject == "Physics":
                selected_syllabus = render_syllabus_hierarchy(st.session_state.phys_syllabus_hierarchy)
            elif subject == "Mathematics":
                selected_syllabus = render_syllabus_hierarchy(st.session_state.math_syllabus_hierarchy)
            else:
                selected_syllabus = None

            # Check if the selected syllabus has changed
            if selected_syllabus != st.session_state.selected_syllabus:
                st.session_state.selected_syllabus = selected_syllabus
                st.session_state.current_syllabus_question = None  # Reset the current question

            # Fetch and display a question for the selected syllabus link
            if st.session_state.selected_syllabus:
                if show_all:

                    st.session_state.current_syllabus_question = get_all_questions_by_syllabus(subject,
                                                                                               st.session_state.selected_syllabus)
                    if st.session_state.current_syllabus_question:
                        for question in st.session_state.current_syllabus_question:
                            display_question(subject, QuestionMode, question, user_id)

                else:
                    st.session_state.current_syllabus_question = get_questions_by_syllabus(subject,
                                                                                           st.session_state.selected_syllabus,
                                                                                           user_id)
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

def display_question(subject, QuestionMode, question, user_id, toggle_key=None):
    if not question:
        st.write("No more questions available!")
        return

    question_id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html = question

    # Apply CSS
    styled_html = apply_css_to_html(html, subject)
    styled_markscheme_html = apply_css_to_html(markscheme_html, subject)
    styled_examiner_notes = apply_css_to_html(examiner_report_html, subject)

    # Display question metadata
    st.markdown(f"**Paper:** {paper}")
    st.markdown(f"**Reference Code:** {reference_code}")
    st.markdown(f"**Syllabus Link:** {syllabus_link}")
    st.markdown(f"**Maximum Marks:** {maximum_marks}")
    st.markdown(f"**Level:** {level}")

    # Render the styled HTML question
    st.markdown(styled_html, unsafe_allow_html=True)

    # -----------------------------------------------------
    # 1) Special Case: Paper 1A for Chemistry or Physics
    # -----------------------------------------------------
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
            col5, col6= st.columns(2)
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
                   
                if QuestionMode == "Fetch" and toggle_key is not None:
                    st.session_state[toggle_key] = False

                
            

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

                # Decide how to move on
                if QuestionMode == "Fetch" and toggle_key is not None:
                    st.session_state[toggle_key] = False
                else:
                    load_next_question(subject, QuestionMode, user_id)

                st.rerun()

        return

    # -----------------------------------------------------
    # 2) Normal Flow (for everything not Paper 1A)
    # -----------------------------------------------------

    # Show/Hide Markscheme logic
    if f"show_markscheme_{question_id}" not in st.session_state:
        st.session_state[f"show_markscheme_{question_id}"] = False

    if st.button(
            "Show Markscheme" if not st.session_state[f"show_markscheme_{question_id}"] else "Hide Markscheme",
            key=f"markscheme_toggle_{question_id}",
    ):
        st.session_state[f"show_markscheme_{question_id}"] = not st.session_state[f"show_markscheme_{question_id}"]
        st.rerun()

    if st.session_state[f"show_markscheme_{question_id}"]:
        st.markdown("### Markscheme")
        st.markdown(styled_markscheme_html, unsafe_allow_html=True)

    # Show Examiner Notes (only if examiner_report_html is not empty)
    if examiner_report_html and examiner_report_html.strip():
        if f"show_examiner_notes_{question_id}" not in st.session_state:
            st.session_state[f"show_examiner_notes_{question_id}"] = False

        if st.button(
                "Show Examiner Notes" if not st.session_state[f"show_examiner_notes_{question_id}"] else "Hide Examiner Notes",
                key=f"examiner_notes_toggle_{question_id}",
        ):
            st.session_state[f"show_examiner_notes_{question_id}"] = not st.session_state[f"show_examiner_notes_{question_id}"]
            st.rerun()

        if st.session_state[f"show_examiner_notes_{question_id}"]:
            st.markdown("### Examiner Notes")
            st.markdown(examiner_report_html, unsafe_allow_html=True)

    # Progress tracking buttons (correct/partial/incorrect/lack context)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Correct", key=f"correct_{question_id}"):
            update_progress(subject, question_id, "correct", user_id)
            if QuestionMode == "Fetch" and toggle_key is not None:
                st.session_state[toggle_key] = False
            else:
                load_next_question(subject, QuestionMode, user_id)
            st.rerun()
    with col2:
        if st.button("Partially Correct", key=f"partially_correct_{question_id}"):
            update_progress(subject, question_id, "partially_correct", user_id)
            if QuestionMode == "Fetch" and toggle_key is not None:
                st.session_state[toggle_key] = False
            else:
                load_next_question(subject, QuestionMode, user_id)
            st.rerun()
    with col3:
        if st.button("Incorrect", key=f"incorrect_{question_id}"):
            update_progress(subject, question_id, "incorrect", user_id)
            if QuestionMode == "Fetch" and toggle_key is not None:
                st.session_state[toggle_key] = False
            else:
                load_next_question(subject, QuestionMode, user_id)
            st.rerun()
    with col4:
        if st.button("Lack Context", key=f"lacking_context_{question_id}"):
            mark_as_lacking_context(subject, question_id, user_id)
            if QuestionMode == "Fetch" and toggle_key is not None:
                st.session_state[toggle_key] = False
            else:
                load_next_question(subject, QuestionMode, user_id)
            st.rerun()


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
    query = f"""
                SELECT question_id, correct_count, partially_correct_count, incorrect_count, updated_at
                FROM {subject}
                WHERE reviewed = 1 AND user_id = ?
                ORDER BY updated_at DESC
                LIMIT 30
            """
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
        q_id = item['question_id']

        st.markdown(
            f"- **Question {q_id}** "
            f"(Paper: {item['paper']}, Ref: {item['reference_code']}) "
            f"| Correct: {item['correct']}, Partial: {item['partial']}, Incorrect: {item['incorrect']} "
            f"| Last answered on {item['updated_at']}"
        )

        col1, col2 = st.columns(2)

        # 1) Initialize the boolean in session_state if needed
        toggle_key = f"show_question_{q_id}"
        if toggle_key not in st.session_state:
            st.session_state[toggle_key] = False

        # 2) The Show/Hide Question button
        with col1:
            btn_label = "Show Question" if not st.session_state[toggle_key] else "Hide Question"
            if st.button(btn_label, key=f"question_toggle_{q_id}"):
                # Flip the boolean
                st.session_state[toggle_key] = not st.session_state[toggle_key]
                st.rerun()

        # 3) The Remove from History button
        with col2:
            if st.button("Remove from History", key=f"remove_{q_id}"):
                # remove_question_from_progress(q_id, user_id)
                st.success(f"Removed question {q_id} from your progress.")
                st.rerun()

        # 4) Conditionally display the question
        if st.session_state[toggle_key]:
            # fetch_question_by_id returns a tuple for display
            question_tuple = fetch_question_by_id(subject, q_id)
            display_question(subject, "Review", question_tuple, user_id, toggle_key)


def show_analytics(subject, user_id):
    conn = connect_game_db()
    cursor = conn.cursor()

    # 1) Count correct, partial, incorrect for the user
    query = f"""
                    SELECT SUM(correct_count), SUM(partially_correct_count), SUM(incorrect_count)
                    FROM {subject}
                    WHERE user_id = ?
                """
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
