from backend.database import connect_game_db, get_db_connection

def mark_as_lacking_context(subject, question_id, user_id):
    """
    Mark a question as lacking context and remove it from the pool of available questions.
    """
    conn = connect_game_db()
    cursor = conn.cursor()


    if subject =="Chemistry":
        cursor.execute("""
            INSERT INTO user_progress_chemistry (
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
                user_id = excluded.user_id,
                lacking_context = 1,
                reviewed = 1,
                updated_at = CURRENT_TIMESTAMP
        """, (question_id, user_id))
    else:
        cursor.execute("""
            INSERT INTO user_progress_physics (
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
                user_id = excluded.user_id,
                lacking_context = 1,
                reviewed = 1,
                updated_at = CURRENT_TIMESTAMP
        """, (question_id, user_id))

    conn.commit()
    conn.close()

def reset_progress(subject, user_id):
    """
    Reset progress by clearing all entries in the user_progress_chemistry table.
    """
    conn = connect_game_db()
    cursor = conn.cursor()

    # Delete all rows from the user_progress_chemistry table
    if subject == "Chemistry":
        cursor.execute("DELETE FROM user_progress_chemistry WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("DELETE FROM user_progress_physics WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

def update_progress(subject, question_id, status, user_id):
    """
    Update the progress for a question based on the status.
    Status can be "correct", "partially_correct", or "incorrect".
    """
    print(f"[DEBUG] update_progress called with " + f"question_id={question_id}, subject={subject}, status={status}, user_id={user_id}")
    conn = connect_game_db()
    cursor = conn.cursor()
    print("updating question" + str(question_id))
    
    if status == "correct":
         print("[DEBUG] Marking question as correct in user_progress...")
        if subject == "Chemistry":
            cursor.execute("""
                INSERT INTO user_progress_chemistry (
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
                    user_id = excluded.user_id,
                    lacking_context = 1,
                    reviewed = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (question_id, user_id))
        else:
            cursor.execute("""
                            INSERT INTO user_progress_physics (
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
                                user_id = excluded.user_id,
                                lacking_context = 1,
                                reviewed = 1,
                                updated_at = CURRENT_TIMESTAMP
                        """, (question_id, user_id))
    elif status == "partially_correct":
        print("[DEBUG] Marking question as partially correct...")
        if subject == "Chemistry":
            cursor.execute("""
                INSERT INTO user_progress_chemistry (
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
                    user_id = excluded.user_id,
                    lacking_context = 1,
                    reviewed = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (question_id, user_id))
        else:
            cursor.execute("""
                            INSERT INTO user_progress_physics (
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
                                user_id = excluded.user_id,
                                lacking_context = 1,
                                reviewed = 1,
                                updated_at = CURRENT_TIMESTAMP
                        """, (question_id, user_id))
    elif status == "incorrect":
        print("[DEBUG] Marking question as incorrect...")
        if subject == "Chemistry":
            cursor.execute("""
                INSERT INTO user_progress_chemistry (
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
                    user_id = excluded.user_id,
                    lacking_context = 1,
                    reviewed = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (question_id, user_id))
        else:
            cursor.execute("""
                INSERT INTO user_progress_physics (
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
                    user_id = excluded.user_id,
                    lacking_context = 1,
                    reviewed = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (question_id, user_id))

    conn.commit()
    conn.close()
    print("[DEBUG] update_progress completed.")

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
        q for q in questions if not should_exclude_question(q[1], q[2])
    ]
    total_questions = len(valid_questions)

    # Reviewed questions from the game's database
    if subject == "Chemistry":
        game_cursor.execute("SELECT COUNT(*) FROM user_progress_chemistry WHERE reviewed = 1 AND lacking_context = 0 AND user_id = ?", (user_id,))
    else:
        game_cursor.execute("SELECT COUNT(*) FROM user_progress_physics WHERE reviewed = 1 AND lacking_context = 0 AND user_id = ?", (user_id,))
    reviewed_questions = game_cursor.fetchone()[0]

    conn.close()
    game_conn.close()

    return reviewed_questions, total_questions

def should_exclude_question(reference_code, paper):
    """
    Determine if a question should be excluded based on its reference_code and paper type.

    - Exclude questions if the part after the last full stop in the reference_code is not numeric.
    - Do not exclude Paper 1B questions.
    """
    if paper == "1B":  # Always include Paper 1B questions
        return False

    # Extract the part after the last full stop
    last_part = reference_code.split(".")[-1]

    # Exclude if the last part is not numeric
    return not last_part.isdigit()

def remove_question_from_progress(question_id, user_id):
    """
    Permanently remove this question's progress for the given user,
    so it can appear again in other modes, etc.
    """
    conn = connect_game_db()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM user_progress_chemistry
        WHERE question_id = ?
          AND user_id = ?
    """, (question_id, user_id))
    conn.commit()
    conn.close()
