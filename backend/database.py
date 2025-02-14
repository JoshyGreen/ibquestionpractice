import sqlite3
import os


CHEM_DB_PATH = "ChemistryQuestionsDataBase.db"  # Path to the external database
PHYS_DB_PATH = "PhysicsQuestionsDataBase.db"
MATH_DB_PATH = "MathematicsQuestionDataBase.db"


def connect_comp_db():
    """Connect to the ChemQuestionsDatabase."""
    return sqlite3.connect("CompSciQuestionDataBase.db")

def connect_chem_db():
    """Connect to the ChemQuestionsDatabase."""
    return sqlite3.connect(CHEM_DB_PATH)

def connect_phys_db():
    """Connect to the PhysicsQuestionsDatabase."""
    return sqlite3.connect(PHYS_DB_PATH)

def connect_math_db():
    return sqlite3.connect(MATH_DB_PATH)

def connect_wierd_math_db():
    return sqlite3.connect("WierdMathQuestionDataBase.db")

def get_db_connection(subject):
    if subject == "Chemistry":
        return connect_chem_db()
    elif subject == "Physics":
        return connect_phys_db()
    elif subject == "MathAA":
        return connect_math_db()
    elif subject == "MathAI":
        raise ValueError("MathAi Questions not imported yet (sorry franny)")
    elif subject == "CompSci":
        return connect_comp_db()
