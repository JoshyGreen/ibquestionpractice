import sqlite3
import os


CHEM_DB_PATH =  os.path.join(os.path.dirname(__file__), "../ChemQuestionsDataBase.db")  # Path to the external database
PHYS_DB_PATH = os.path.join(os.path.dirname(__file__), "../PhysicsQuestionsDataBase.db")
GAME_DB_PATH = os.path.join(os.path.dirname(__file__), "../questionsgame.db")  # Path to the game database in the project root


def connect_chem_db():
    """Connect to the ChemQuestionsDatabase."""
    return sqlite3.connect(CHEM_DB_PATH)

def connect_phys_db():
    """Connect to the PhysicsQuestionsDatabase."""
    return sqlite3.connect(PHYS_DB_PATH)

def connect_game_db():
    """Connect to the game's progress tracking database."""
    return sqlite3.connect(GAME_DB_PATH)

def get_db_connection(subject):
    if subject == "Chemistry":
        return connect_chem_db()
    else:
        return connect_phys_db()

def create_game_database():
    """Create the progress tracking table in the game's database."""
    conn = connect_game_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress_chemistry (
            question_id INTEGER PRIMARY KEY,
            correct_count INTEGER DEFAULT 0,
            partially_correct_count INTEGER DEFAULT 0,
            incorrect_count INTEGER DEFAULT 0,
            reviewed BOOLEAN DEFAULT 0,
            lacking_context BOOLEAN DEFAULT 0,
            user_id INTEGER,
            updated_at TIMESTAMP
        )
    """)

    cursor.execute("""
           CREATE TABLE IF NOT EXISTS user_progress_physics (
               question_id INTEGER PRIMARY KEY,
               correct_count INTEGER DEFAULT 0,
               partially_correct_count INTEGER DEFAULT 0,
               incorrect_count INTEGER DEFAULT 0,
               reviewed BOOLEAN DEFAULT 0,
               lacking_context BOOLEAN DEFAULT 0,
               user_id INTEGER,
               updated_at TIMESTAMP
           )
       """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()
    print(f"Game database created at: {GAME_DB_PATH}")



create_game_database()
