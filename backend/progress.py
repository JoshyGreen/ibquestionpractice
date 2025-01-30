from backend.database import connect_game_db, get_db_connection

def mark_as_lacking_context(subject, question_id, user_id):
    """
    Mark a question as lacking context and remove it from the pool of available questions.
    """
    conn = connect_game_db()
    cursor = conn.cursor()
    query = f"""
                INSERT INTO {subject} (
                question_id,
                user_id,
                lacking_context,
                reviewed,
                updated_at
                )
                VALUES (?, ?, 1, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(question_id)
                DO UPDATE
                SET
                    lacking_context = 1,
                    reviewed = 1,
                    updated_at = CURRENT_TIMESTAMP
            """
    cursor.execute(query,(question_id, user_id))

    conn.commit()
    conn.close()

def reset_progress(subject, user_id):
    """
    Reset progress by clearing all entries in the user_progress_chemistry table.
    """
    conn = connect_game_db()
    cursor = conn.cursor()

    # Delete all rows from the user_progress_chemistry table
    query=  f"DELETE FROM {subject} WHERE user_id = ?"
    cursor.execute(query,(user_id,))

    conn.commit()
    conn.close()


def update_progress(subject, question_id, status, user_id):
    """
    Update the progress for a question based on the status.
    Status can be "correct", "partially_correct", or "incorrect".
    """
    print(
        f"[DEBUG] update_progress called with " + f"question_id={question_id}, subject={subject}, status={status}, user_id={user_id}")
    conn = connect_game_db()
    cursor = conn.cursor()
    correct_val = 1 if status == "correct" else 0
    partial_val = 1 if status == "partially_correct" else 0
    incorrect_val = 1 if status == "incorrect" else 0

    # 2) Insert or update all three columns
    #    Note we use 'excluded' so the new row overwrites old values on conflict
    query = f"""
            INSERT INTO {subject} (
                question_id, user_id,
                correct_count, partially_correct_count, incorrect_count,
                reviewed,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(question_id)
            DO UPDATE
            SET
                correct_count = excluded.correct_count,
                partially_correct_count = excluded.partially_correct_count,
                incorrect_count = excluded.incorrect_count,
                reviewed = excluded.reviewed,
                updated_at = excluded.updated_at
        """

    cursor.execute(query, (question_id, user_id, correct_val, partial_val, incorrect_val))
    conn.commit()
    conn.close()

def get_progress(subject, user_id):
    """
    Get the total number of questions and the number of reviewed questions.
    Exclude questions marked as 'lacking context' or invalid multipart questions.
    """
    conn = get_db_connection(subject) # Connect to ChemQuestionsDatabase
    game_conn = connect_game_db()  # Connect to Game Database
    cursor = conn.cursor()
    game_cursor = game_conn.cursor()

    # Fetch all questions and filter them in Python
    cursor.execute("SELECT id, reference_code, paper FROM questions")
    questions = cursor.fetchall()
    # Filter out questions to exclude
    valid_questions = [
        q for q in questions if not should_exclude_question(q[0], subject, q[1], q[2], user_id)
    ]

    total_questions = len(valid_questions)

    # Reviewed questions from the game's database
    query1 = f"""SELECT COUNT(*) FROM {subject} WHERE lacking_context =1 AND user_id = ?"""
    query2 = f"""SELECT COUNT(*) FROM {subject} WHERE correct_count = 1 AND user_id = ?"""
    contextless = game_cursor.execute(query1, (user_id,)).fetchone()[0]
    total_questions = total_questions - contextless
    reviewed_questions = game_cursor.execute(query2,(user_id,)).fetchone()[0]

    conn.close()
    game_conn.close()

    return reviewed_questions, total_questions

def should_exclude_question(id, subject, reference_code, paper, user_id):
    """
    Determine if a question should be excluded based on its reference_code and paper type.

    - Exclude questions if the part after the last full stop in the reference_code is not numeric.
    - Do not exclude Paper 1B questions.
    """
    game = connect_game_db()
    g = game.cursor()

    if paper == "1B":  # Always include Paper 1B questions
        return False

    # Extract the part after the last full stop
    last_part = reference_code.split(".")[-1]

    # Exclude if the last part is not numeric
    if subject == "Mathematics":
        return False
    else:
        return not last_part.isdigit()

def remove_question_from_history(question_id, subject, user_id):
    conn = connect_game_db()
    cursor = conn.cursor()

    query = f"DELETE FROM {subject} WHERE user_id = {user_id} AND question_id = {question_id}"
    cursor.execute(query)
