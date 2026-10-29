import os
import psycopg
from dotenv import load_dotenv
load_dotenv()
def get_connection():
    return psycopg.connect(
        host= "localhost",
        user="postgres",
        dbname="faculty_feedback",
        port=5432,
        password=os.getenv("DB_PASSWORD")

    )