import psycopg
import os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg.connect(
    host = "localhost",
    port = 5432,
    dbname = "faculty_feedback",
    user = "postgres",
    password= os.getenv("DB_PASSWORD")
)
print("DataBase connected successfully")
conn.close()