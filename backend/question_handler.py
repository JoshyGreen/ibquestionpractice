from backend.database import get_db_connection
from supabase import create_client, Client
import sqlite3
import os
# Sanitize the subject to prevent SQL injection

SUPABASE_URL = "https://ofaiofljgsxuamzaensq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mYWlvZmxqZ3N4dWFtemFlbnNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk1NDc5NTcsImV4cCI6MjA1NTEyMzk1N30.jvMpQavl14H-kBr8x576VXGTizZ3yBoi7P-oEEQckuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_question_by_id(subject, question_id):
    """
    Fetches question details from the SQLite `questions` table.
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
    return row

def get_reviewed_question_ids(subject, user_id):
    """
    Fetches reviewed question IDs from Supabase `{subject}` table.
    """
    response = (
        supabase.table(subject.lower())
        .select("question_id")
        .eq("user_id", user_id)
        .or_("correct_count.eq.true,lacking_context.eq.true")
        .execute()
    )
    return [row["question_id"] for row in response.data] if response.data else []

def get_random_question(subject, user_id, hl=True):
    """
    Fetches a random question from the SQLite `questions` table,
    excluding reviewed questions from Supabase.
    """
    print("Subject: "+ subject)
    conn = get_db_connection(subject)
    cursor = conn.cursor()

    reviewed_ids = get_reviewed_question_ids(subject, user_id)

    if hl:
        level = ["HL", "Additional Higher Level"]
    else:
        level = ["SL", "Standard Level"]

    if reviewed_ids:
        placeholders = ",".join("?" for _ in reviewed_ids)
        placeholders2 = ",".join("?" for _ in level)
        query = f"""
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            WHERE id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor.execute(query, reviewed_ids)
    else:
        query = """
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor.execute(query)

    question = cursor.fetchone()
    conn.close()
    return question

def get_random_question_by_paper(subject, paper, user_id, hl=True):
    """
    Fetches a random question by paper, excluding reviewed questions.
    """
    conn = get_db_connection(subject)
    cursor = conn.cursor()
    if hl:
        level = ["HL", "Additional Higher Level"]
    else:
        level = ["SL", "Standard Level"]
    
    reviewed_ids = get_reviewed_question_ids(subject, user_id)
    if reviewed_ids:
        placeholders = ",".join("?" for _ in reviewed_ids)
        placeholders2 = ",".join("?" for _ in level)
        query = f"""
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            WHERE paper = ? AND id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor.execute(query, [paper, *reviewed_ids])
    else:
        query = """
            SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
            FROM questions
            WHERE paper = ?
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor.execute(query, [paper])

    question = cursor.fetchone()
    conn.close()
    return question

def get_all_questions_by_syllabus(subject, selected_syllabus):
    """
    Retrieves all questions from SQLite `questions` table for a given syllabus.
    """
    conn = get_db_connection(subject)
    cursor = conn.cursor()

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
    Retrieves all unique syllabus links from SQLite `questions` table.
    """
    print("Subject:" + subject)
    conn = get_db_connection(subject)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT syllabus_link FROM questions WHERE syllabus_link IS NOT NULL")
    raw_links = {row[0].strip() for row in cursor.fetchall()}  # Use a set to remove duplicates

    conn.close()
    return sorted(raw_links)  # Sort the links alphabetically for consistency

def get_questions_by_syllabus(subject, selected_syllabus, user_id):
    """
    Fetches a single random question filtered by syllabus link.
    Excludes reviewed questions from Supabase.
    """
    conn = get_db_connection(subject)
    cursor = conn.cursor()

    reviewed_ids = get_reviewed_question_ids(subject, user_id)

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
        cursor.execute(query, params)
    else:
        query = """
               SELECT id, html, paper, reference_code, syllabus_link, maximum_marks, level, markscheme_html, examiner_report_html
               FROM questions
               WHERE syllabus_link LIKE ? OR syllabus_link LIKE ?
               ORDER BY RANDOM()
               LIMIT 1
           """
        cursor.execute(query, [f"%{selected_syllabus}%", f"%||{selected_syllabus}%"])

    question = cursor.fetchone()

    conn.close()
    return question



