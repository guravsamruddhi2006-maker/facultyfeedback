from backend.db import get_connection 
from backend.main import is_feedback_period_open
conn = get_connection()
try:
    result = is_feedback_period_open(
        conn, "2026-27", 5
    )
    print("Feedback period open:", result)
finally:
    conn.close()
    