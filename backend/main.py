from fastapi import FastAPI
from pydantic import BaseModel, Field
from backend.db import get_connection
from backend.security import hash_password, verify_password, create_access_token, verify_access_token
from psycopg.errors import UniqueViolation
from fastapi import HTTPException
from typing import Literal
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
from psycopg.rows import dict_row
from datetime import datetime
security = HTTPBearer()
app = FastAPI()
def get_current_user(credentials:HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_access_token(credentials.credentials)
    return payload
def is_feedback_period_open(conn, academic_year:str, semester_number:int):
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SELECT start_date, end_date FROM feedback_periods WHERE academic_year = %s AND semester_number = %s", (academic_year, semester_number))
        period = cursor.fetchone()
        if period is None:
            return False
        now = datetime.now()
        return period["start_date"] <= now <= period["end_date"]
class AdminRegistration(BaseModel):
    name:str
    email:str
    password:str
@app.post("/admin")
def register_admin(admin:AdminRegistration):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(admin.password)
    cursor.execute("INSERT INTO admins (name, email, password_hash) VALUES (%s, %s, %s)", (admin.name, admin.email, hashed_password))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message":"Admins registered Successfully"}
class StudentRegistration(BaseModel):
    student_id:str
    name:str
    department_id:int
    password:str
@app.post("/students")
def register_student(student:StudentRegistration):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(student.password)
    cursor.execute("INSERT INTO students(student_id, name, department_id, password_hash) VALUES (%s, %s, %s, %s)",
    (student.student_id,
     student.name,
     student.department_id,
     hashed_password)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"message":"Student registered Successfully"}
class AdminLogin(BaseModel):
    email:str
    password:str
@app.post("/admins/login")
def admins_login(admin:AdminLogin):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id, email, password_hash FROM admins WHERE email= %s", (admin.email,))
    admins = cursor.fetchone()
    if admins is None:
        raise HTTPException(status_code = 401, detail= "Invalid Email_id or Password")
    password_correct = verify_password(admin.password, admins[2])
    if not password_correct:
        raise HTTPException(status_code= 401, detail="Inavalid email_id or Password")
    token_data = {
        "sub":str(admins[0]),
        "role":"admin"
    }
    
    access_token = create_access_token(token_data)
    cursor.close()
    conn.close()
    return {"access_token":access_token, "token_type":"bearer"}
class FacultyRegistration(BaseModel):
    name :str
    email:str
    password:str
    department_id :int
@app.post("/faculty")
def register_faculty(faculty:FacultyRegistration):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(faculty.password)
    cursor.execute("INSERT INTO faculty(name, email,password_hash, department_id, status) VALUES (%s, %s, %s, %s, %s)", 
    (faculty.name,
     faculty.email,
     hashed_password,
     faculty.department_id,
     "pending")
     )
    conn.commit()
    cursor.close()
    conn.close()
    return {"message":"Faculty registered successfully"}
class FacultyLogin(BaseModel):
    email:str
    password:str
@app.post("/faculty/login")
def faculty_login(login:FacultyLogin):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT faculty_id, email, password_hash, status FROM faculty WHERE email= %s", (login.email,))
    faculty = cursor.fetchone()
    if faculty is None: 
        raise HTTPException(status_code= 401, detail= "Invalid Email_id or Password")
    password_correct = verify_password(login.password, faculty[2])
    if not password_correct:
        raise HTTPException(status_code= 401, detail= "Invalid Email_id or Password")
    if faculty[3] != "approved":
        raise HTTPException(
            status_code= 403, detail= "Faculty account is not approved"
        )
    token_data = {
        "sub":str(faculty[0]),
        "role":"faculty"
    }
    access_token = create_access_token(token_data)
    cursor.close()
    conn.close()
    return {"access_token":access_token,
            "token_type":"bearer"}
class  FacultystatusUpdate(BaseModel):
    status:Literal["approved", "rejected"]
@app.patch("/faculty/{faculty_id}/status")
def upadate_faculty_status(faculty_id :int, update:FacultystatusUpdate, current_user:dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code = 403, detail= "Admin access required"
        )
    cursor.execute("UPDATE faculty SET status = %s WHERE faculty_id = %s", (update.status, faculty_id))
    
    if cursor.rowcount == 0:
        raise HTTPException (
            status_code = 404, detail= "Faculty_id doesn't exist"
        )
    conn.commit()
    cursor.close()
    conn.close()
    return {"message":"Faculty status updated successfully"}

class StudentLogin(BaseModel):
    student_id:str
    password:str
@app.post("/students/login")
def studuent_login(login:StudentLogin):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, password_hash FROM students WHERE student_id= %s", (login.student_id,)) 
    student = cursor.fetchone()
    if student is None:
        raise HTTPException(status_code= 401, detail= "Invalid student ID or password")
    password_correct=verify_password(login.password, student[2])
    if not password_correct:
        raise HTTPException(status_code= 401, detail = "Invaild student ID or password")
    cursor.close()
    conn.close()
    token_data = {
        "sub":str(student[0]),
        "role":"student"
    }
    access_token = create_access_token(token_data)
    return {"access_token":access_token,
            "token_type":"bearer"}
class FeedbackRating(BaseModel):
    question_id:int
    rating : int = Field(ge = 1, le = 5)
    
    

@app.get("/students/dashboard/{academic_year}/{semester_number}")
def student_dashboard(academic_year:str, semester_number:int, current_user:dict = Depends(get_current_user)):
    student_id = current_user["sub"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
    """
    SELECT
    co.offering_id,
    
    
    co.subject_code,
    s.subject_name,
    
    f.name AS faculty_name,
    CASE 
        WHEN fb.feedback_id IS NULL THEN 'Not Submitted'
        ELSE 'Submitted'
    END AS feedback_status

    FROM course_offerings co
    JOIN subjects s
    ON co.subject_code = s.subject_code
    JOIN faculty f
    ON co.faculty_id = f.faculty_id
    LEFT JOIN feedback fb
        ON co.offering_id = fb.offering_id
        AND fb.student_id = %s
    WHERE co.academic_year = %s
    AND co.semester_number = %s
    ORDER BY co.subject_code
    """, (student_id,academic_year, semester_number))
    dashboard = cursor.fetchall()
    cursor.close()
    conn.close()
    return dashboard
    
@app.get("/")
def home():
    return {"message":"Faculty Feedback System API is running"}
@app.get("/health/db")
def database_health():
    conn = get_connection()
    conn.close()
    return {"message":"PostgreSQL connected succesfully"}
@app.get("/departments")
def get_departments():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, code FROM departments ORDER BY name"
    )
    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    return departments
@app.get("/semesters")
def get_semesters():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT semester_number FROM  semesters ORDER BY semester_number")
    semesters = cursor.fetchall() 
    cursor.close()

    conn.close()
    return semesters
@app.get("/subjects/{semester_number}")
def get_subjects(semester_number:int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subject_code, subject_name FROM subjects WHERE semester_number = %s ORDER BY subject_code", (semester_number,))
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()
    return subjects
@app.get("/feedback/questions")
def get_feedback_question():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_id, question_text FROM feedback_questions WHERE is_active = TRUE ORDER BY question_id")
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return questions
@app.get("/academic_years")
def get_academic_years():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT academic_year FROM academic_years ORDER BY academic_year")
    academic_years = cursor.fetchall()
    cursor.close()
    conn.close()
    return academic_years
@app.get("/course_offerings")
def get_course_offerings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT co.offering_id, co.academic_year, co.semester_number, co.subject_code, s.subject_name, co.faculty_id, f.name AS faculty_name FROM course_offerings co JOIN subjects s ON co.subject_code = s.subject_code JOIN faculty f ON co.faculty_id = f.faculty_id ORDER BY co.academic_year, co.semester_number, co.subject_code")
    offerings = cursor.fetchall()
    cursor.close()
    conn.close()
    return offerings
@app.get("/course_offering/{academic_year}/{semester_number}")
def get_course_offerings(academic_year: str, semester_number: int):
    conn = get_connection()
    cursor = conn.cursor(row_factory = dict_row)
    cursor.execute("SELECT co.offering_id, co.subject_code, s.subject_name, co.faculty_id, f.name AS faculty_name FROM course_offerings co JOIN subjects s ON co.subject_code = s.subject_code JOIN faculty f ON co.faculty_id = f.faculty_id WHERE co.academic_year = %s AND co.semester_number = %s ORDER BY co.subject_code", (academic_year, semester_number))
    offerings = cursor.fetchall()
    cursor.close()
    conn.close()
    return offerings
@app.get("/faculty")
def get_faculty():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT faculty_id, name, email, department_id, status FROM faculty ORDER BY faculty_id")
    faculty = cursor.fetchall()
    cursor.close()
    conn.close()
    return faculty
@app.get("/students")
def get_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, department_id FROM students ORDER BY student_id")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return students
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_access_token(credentials.credentials)
    return payload
class CourseOfferingCreate(BaseModel):
    academic_year:str
    semester_number:int
    subject_code:str
@app.post("/course-offerings")
def create_course_offering(
    offering:CourseOfferingCreate, current_user:dict=Depends(get_current_user)
):
    if current_user["role"] != "faculty":
        raise HTTPException(
            status_code = 403,
            detail = "Faculty access required"

        )
    conn = get_connection()
    cursor = conn.cursor()
    faculty_id = int(current_user["sub"])
    try:
        cursor.execute("INSERT INTO course_offerings (academic_year, semester_number, subject_code, faculty_id) VALUES (%s, %s, %s, %s)", (offering.academic_year, offering.semester_number, offering.subject_code, faculty_id))
    except UniqueViolation:
        conn.rollback()
        raise HTTPException(
            status_code = 400, detail = "Course offering already exists for this academic year and semester."
        )
    conn.commit()
    cursor.close()
    conn.close()
    return {"message":"Course offering created successfully"}
class FeedbackRating(BaseModel):
    question_id:int
    rating : int = Field(ge = 1, le = 5)
class FeedbackSubmission(BaseModel):
    offering_id:int
    ratings:list[FeedbackRating]
    comment:str|None = None
@app.post("/feedback/submit")
def submit_feedback(
    submission:FeedbackSubmission, current_user:dict = Depends(get_current_user)):
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code = 403, detail = "Student access required"
        )
    student_id = current_user.get("sub")
    if submission.comment is None:
        raise HTTPException(status_code = 400, detail = "A written comment is required")
    comment = submission.comment.strip()
    if len(comment) < 10 or len(comment)>1000:
        raise HTTPException(status_code = 400, detail  = "Comment must contains 10 to 1000 characters")
    question_ids = [item.question_id for item in submission.ratings]
    if len(question_ids) != len(set(question_ids)):
        raise HTTPException(status_code = 400, detail = "Each question can be rated only once")
    conn = get_connection()
    try:
        with conn.cursor(row_factory = dict_row) as cursor:
            cursor.execute(
                "SELECT academic_year, semester_number FROM course_offerings WHERE offering_id = %s", (submission.offering_id,)
            )
            offering = cursor.fetchone()
            if offering is None:
                raise HTTPException(status_code = 404, detail = "Course offering not found")
            if not is_feedback_period_open(
                conn, offering["academic_year"],  offering["semester_number"]
            ):
                raise HTTPException(
                    status_code = 403, detail = "Feedback period is closed or not configured"
                )
            cursor.execute(
                "SELECT question_id FROM feedback_questions WHERE is_active = TRUE"
            )
            active_question = {
                row["question_id"] for row in cursor.fetchall()
            }
            if not active_question:
                raise HTTPException(status_code = 400, detail = "No active feedback questions are configured")
            submitted_questions = set(question_ids)
            if submitted_questions != active_question:
                raise HTTPException(status_code = 400, detail = ("Submit exactly one rating for every active" "feedback question"))
            cursor.execute("SELECT feedback_id FROM feedback WHERE student_id = %s AND offering_id = %s FOR UPDATE", (student_id, submission.offering_id))
            existing_feedback = cursor.fetchone()
            if existing_feedback:
                feedback_id = existing_feedback["feedback_id"]
                cursor.execute(
                    "UPDATE feedback SET comment = %s, submitted_at = CURRENT_TIMESTAMP WHERE feedback_id = %s", (comment, feedback_id,)
                )
                cursor.execute("DELETE FROM feedback_answer WHERE feedback_id = %s", (feedback_id,))
                message = "Feedabck updated successfully"
            else:
                cursor.execute("INSERT INTO feedback (student_id, offering_id, submitted_at, comment) VALUES(%s, %s, CURRENT_TIMESTAMP, %s) RETURNING feedback_id", (student_id, submission.offering_id, comment))
                feedback_id = cursor.fetchone()["feedback_id"]
                message = "Feedback submitted successfully"
            for item in submission.ratings:
                cursor.execute("INSERT INTO feedback_answer (feedback_id, question_id, rating) VALUES (%s, %s,%s)", (feedback_id, item.question_id, item.rating))

            conn.commit()
            return {
                "message":message, 
                "feedback_id":feedback_id

            }
    except HTTPException:
        conn.rollback()
        raise
    except HTTPException:
        conn.rollback()
    finally:
        conn.close

@app.get("/faculty/feedback-results/{academic_year}/{semester_number}")
def get_faculty_feedback_results(
    academic_year: str,
    semester_number: int,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can view these results"
        )

    faculty_id = int(current_user["sub"])

    conn = get_connection()

    try:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    s.subject_code,
                    s.subject_name,
                    fq.question_text,
                    AVG(fa.rating)::float AS average_rating,
                    COUNT(DISTINCT fb.feedback_id) AS response_count
                FROM course_offerings co
                JOIN subjects s
                    ON s.subject_code = co.subject_code
                JOIN feedback fb
                    ON fb.offering_id = co.offering_id
                JOIN feedback_answer fa
                    ON fa.feedback_id = fb.feedback_id
                JOIN feedback_questions fq
                    ON fq.question_id = fa.question_id
                WHERE co.faculty_id = %s
                  AND co.academic_year = %s
                  AND co.semester_number = %s
                GROUP BY
                    s.subject_code,
                    s.subject_name,
                    fq.question_id,
                    fq.question_text
                ORDER BY s.subject_code, fq.question_id
                """,
                (faculty_id, academic_year, semester_number)
            )

            results = cursor.fetchall()
            cursor.execute(
            """
            SELECT
                s.subject_code,
                s.subject_name,
                AVG(fa.rating)::float AS overall_average_rating,
                COUNT(DISTINCT fb.feedback_id) AS response_count
            FROM course_offerings co
            JOIN subjects s
                ON s.subject_code = co.subject_code
            JOIN feedback fb
                ON fb.offering_id = co.offering_id
            JOIN feedback_answer fa
                ON fa.feedback_id = fb.feedback_id
            WHERE co.faculty_id = %s
            AND co.academic_year = %s
            AND co.semester_number = %s
            GROUP BY s.subject_code, s.subject_name
            ORDER BY s.subject_code
            """,
            (faculty_id, academic_year, semester_number))

            subject_summary = cursor.fetchall()
            cursor.execute(
                """
                SELECT
                    s.subject_code,
                    s.subject_name,
                    fb.comment,
                    fb.submitted_at
                FROM course_offerings co
                JOIN subjects s
                    ON s.subject_code = co.subject_code
                JOIN feedback fb
                    ON fb.offering_id = co.offering_id
                WHERE co.faculty_id = %s
                AND co.academic_year = %s
                AND co.semester_number = %s
                AND fb.comment IS NOT NULL
                AND TRIM(fb.comment) <> ''
                ORDER BY fb.submitted_at DESC
                """,
                (faculty_id, academic_year, semester_number)
            )

            comments = cursor.fetchall()
            strengths = [
                item for item in results
                if item["average_rating"] >= 4.0
                and item["response_count"] >= 3
            ]

            improvement_areas = [
                item for item in results
                if item["average_rating"] < 3.0
                and item["response_count"] >= 3
            ]

            return {
                "academic_year": academic_year,
                "semester_number": semester_number,
                "subject_summary":subject_summary,
                "question_results": results,
                "comments":comments,
                "strengths":strengths,
                "improvement_areas":improvement_areas
            }

    finally:
        conn.close()
@app.get("/faculty/performance-comparison/{subject_code}")
def compare_faculty_performance(
    subject_code: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can compare performance"
        )

    faculty_id = int(current_user["sub"])
    conn = get_connection()

    try:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    co.academic_year,
                    s.subject_code,
                    s.subject_name,
                    AVG(fa.rating)::float AS overall_average_rating,
                    COUNT(DISTINCT fb.feedback_id) AS response_count
                FROM course_offerings co
                JOIN subjects s
                    ON s.subject_code = co.subject_code
                JOIN feedback fb
                    ON fb.offering_id = co.offering_id
                JOIN feedback_answer fa
                    ON fa.feedback_id = fb.feedback_id
                WHERE co.faculty_id = %s
                  AND co.subject_code = %s
                GROUP BY
                    co.academic_year,
                    s.subject_code,
                    s.subject_name
                ORDER BY co.academic_year
                """,
                (faculty_id, subject_code)
            )

            results = cursor.fetchall()

        return {
            "subject_code": subject_code,
            "comparison": results
        }

    finally:
        conn.close()