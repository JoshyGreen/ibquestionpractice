from backend.database import connect_game_db, get_db_connection
from backend.progress import should_exclude_question
# Sanitize the subject to prevent SQL injection


def fetch_question_by_id(subject, question_id):
    """
    Returns (html, markscheme_html, examiner_report_html) for a single question ID,
    or None if not found.
    """
    conn = get_db_connection(subject)
    c = conn.cursor()
    c.execute("""
        SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
        FROM questions
        WHERE id = ?
    """, (question_id,))
    row = c.fetchone()
    conn.close()
    return row  # e.g., (html, markscheme, examiner_report)

def get_random_question(subject, user_id):
    print(f"Getting questions from {subject}")
    chem_conn = get_db_connection(subject)
    game_conn = connect_game_db()
    chem_cursor = chem_conn.cursor()
    game_cursor = game_conn.cursor()

    # Fetch reviewed IDs for *this subject*

    query = f"""
        SELECT question_id FROM {subject}
        WHERE reviewed = 1 AND user_id = ?
    """
    game_cursor.execute(query, (user_id,))

    reviewed_ids = [row[0] for row in game_cursor.fetchall()]

    if reviewed_ids:
        placeholders = ",".join("?" for _ in reviewed_ids)
        query = f"""
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            WHERE id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT 1
        """
        chem_cursor.execute(query, reviewed_ids)
    else:
        query = """
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            ORDER BY RANDOM()
            LIMIT 1
        """
        chem_cursor.execute(query)

    question = chem_cursor.fetchone()

    chem_conn.close()
    game_conn.close()
    return question

def get_random_question_by_paper(subject, paper, user_id):
    conn = get_db_connection(subject)
    game_conn = connect_game_db()
    c = conn.cursor()
    g = game_conn.cursor()

    query = f"""
               SELECT question_id FROM {subject}
               WHERE reviewed = 1 AND user_id = ?
           """
    g.execute(query, (user_id,))
    reviewed_ids = [row[0] for row in g.fetchall()]

    if reviewed_ids:
        placeholders = ",".join("?" for _ in reviewed_ids)
        query = f"""
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            WHERE paper = ?
              AND id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT 1
        """
        c.execute(query, [paper, *reviewed_ids])
    else:
        query = """
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            WHERE paper = ?
            ORDER BY RANDOM()
            LIMIT 1
        """
        c.execute(query, [paper])

    question = c.fetchone()
    conn.close()
    game_conn.close()
    return question

def get_all_questions_by_syllabus(subject, selected_syllabus):
    """
    Retrieve all questions (not just one) for the given syllabus link.
    Returns a list of question rows, or an empty list if none found.
    """
    conn = get_db_connection(subject)
    cursor = conn.cursor()

    # Return *all* matching rows
    query = """
        SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
        FROM questions
        WHERE syllabus_link LIKE ? OR syllabus_link LIKE ?
        ORDER BY reference_code 
    """
    cursor.execute(query, [f"%{selected_syllabus}%", f"%||{selected_syllabus}%"])
    rows = cursor.fetchall()

    conn.close()
    return rows

def get_all_syllabus_links(subject):
    """
    Retrieve all unique syllabus links from the database.
    """
    conn = get_db_connection(subject)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT syllabus_link FROM questions WHERE syllabus_link IS NOT NULL")
    raw_links = {row[0].strip() for row in cursor.fetchall()}  # Use a set to remove duplicates

    conn.close()
    return sorted(raw_links)  # Sort the links alphabetically for consistency

def get_questions_by_syllabus(subject, selected_syllabus, user_id):
    """
    Retrieve a single random question filtered by the selected syllabus link.
    """
    game_conn = connect_game_db()
    g = game_conn.cursor()
    conn = get_db_connection(subject)
    c = conn.cursor()

    query = f"""
                   SELECT question_id FROM {subject}
                   WHERE reviewed = 1 AND user_id = ?
               """
    g.execute(query, (user_id,))
    reviewed_ids = [row[0] for row in g.fetchall()]

    # Normalize the selected syllabus
    selected_syllabus = selected_syllabus.strip()

    if reviewed_ids:
        placeholders = ",".join("?" for _ in reviewed_ids)
        query = f"""
               SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
               FROM questions
               WHERE (syllabus_link LIKE ? OR syllabus_link LIKE ?)
                 AND id NOT IN ({placeholders})
               ORDER BY RANDOM()
               LIMIT 1
           """
        params = [f"%{selected_syllabus}%", f"%||{selected_syllabus}%"] + reviewed_ids
        c.execute(query, params)
    else:
        query = """
               SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
               FROM questions
               WHERE syllabus_link LIKE ? OR syllabus_link LIKE ?
               ORDER BY RANDOM()
               LIMIT 1
           """
        c.execute(query, [f"%{selected_syllabus}%", f"%||{selected_syllabus}%"])

    question = c.fetchone()

    conn.close()
    game_conn.close()
    return question


