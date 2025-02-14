import uuid

from backend.database import get_db_connection
from supabase import create_client, Client
import os

# Set up Supabase
SUPABASE_URL = "https://ofaiofljgsxuamzaensq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mYWlvZmxqZ3N4dWFtemFlbnNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk1NDc5NTcsImV4cCI6MjA1NTEyMzk1N30.jvMpQavl14H-kBr8x576VXGTizZ3yBoi7P-oEEQckuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def mark_as_lacking_context(subject, question_id, user_id):
    """
    Mark a question as lacking context in Supabase.
    """
    subject = subject.lower()
    data = {
        "question_id": question_id,
        "user_id": user_id,
        "lacking_context": True,
        "updated_at": "now()"  # PostgreSQL function for the current timestamp
    }

    response = supabase.table(subject).upsert(data).execute()
    return response

def reset_progress(subject, user_id):
    """
    Delete all progress entries for a user in Supabase.
    """
    response = supabase.table(subject.lower()).delete().eq("user_id", user_id).execute()
    return response


def update_progress(subject, question_id, status, user_id):
    """
    Update user progress in Supabase.
    """
    subject = subject.lower()
    correct_val = 1 if status == "correct" else 0
    partial_val = 1 if status == "partially_correct" else 0
    incorrect_val = 1 if status == "incorrect" else 0

    data = {
        "question_id": question_id,
        "user_id": user_id,
        "correct_count": correct_val,
        "partially_correct_count": partial_val,
        "incorrect_count": incorrect_val,
        "updated_at": "now()"
    }

    response = supabase.table(subject).upsert(data).execute()
    return response

def get_progress(subject, user_id):
    """
    Get the total number of questions and the number of reviewed questions.
    """

    conn = get_db_connection(subject)
    cursor = conn.cursor()
    subject = subject.lower()
    # Fetch all questions and filter them in Python
    cursor.execute("SELECT id, reference_code, paper FROM questions")
    questions = cursor.fetchall()

    # Filter out invalid questions
    total_questions = len(questions)

    # Get user's progress from Supabase
    contextless_response = supabase.table(subject).select("question_id").eq("user_id", user_id).eq("lacking_context", True).execute()
    reviewed_response = supabase.table(subject).select("question_id").eq("user_id", user_id).eq("correct_count", 1).execute()

    contextless_count = len(contextless_response.data)
    reviewed_count = len(reviewed_response.data)

    total_questions -= contextless_count

    return reviewed_count, total_questions


def remove_question_from_history(question_id, subject, user_id):
    """
    Remove a specific question from the user's history in Supabase.
    """
    subject = subject.lower()
    response = supabase.table(subject).delete().eq("user_id", user_id).eq("question_id", question_id).execute()
    return response
