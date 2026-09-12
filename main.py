from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from fastapi import Header
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class CreateTask(BaseModel):
    title: Optional[str] = None

app=FastAPI()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL
        )
    """)
    cur.execute("SELECT COUNT(*) FROM tasks")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute("INSERT INTO tasks (title, done) VALUES (%s, %s)", ("Buy groceries", False))
        cur.execute("INSERT INTO tasks (title, done) VALUES (%s, %s)", ("Clean the Room", False))
        cur.execute("INSERT INTO tasks (title, done) VALUES (%s, %s)", ("Complete assignment", True))
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.get("/", summary="API info")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health", summary="Health check")
def health():
    return { "status": "ok" }

@app.get("/tasks", summary="List all tasks")
def get_tasks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, done FROM tasks")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = [{"id": row[0], "title": row[1], "done": bool(row[2])} for row in rows]
    return result

@app.get("/tasks/{task_id}", summary="Get a single task")
def get_one_task(task_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )
    return {"id": row[0], "title": row[1], "done": bool(row[2])}

@app.post("/tasks", summary="Create a new task")
def create_task(new_task: CreateTask):
    if not new_task.title or not new_task.title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"}
        )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
        (new_task.title, False)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    task = {"id": new_id, "title": new_task.title, "done": False}
    return JSONResponse(status_code=201, content=task)

class UpdateTask(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, updates: UpdateTask):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )
    new_title = updates.title if updates.title is not None else row[1]
    new_done = updates.done if updates.done is not None else bool(row[2])
    cur.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s",
        (new_title, new_done, task_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"id": task_id, "title": new_title, "done": new_done}

@app.delete("/tasks/{task_id}", summary="Delete a task")
def delete_task(task_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cur.close()
    conn.close()
    return JSONResponse(status_code=204, content=None)

class SignupRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

@app.post("/auth/signup", summary="Create a new user account")
def signup(credentials: SignupRequest):
    if not credentials.email or not credentials.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )
    try:
        result = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })
        return JSONResponse(status_code=201, content={"user": result.user.model_dump(mode="json")})
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
class LoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

@app.post("/auth/login", summary="Authenticate user and return JWT")
def login(credentials: LoginRequest):
    if not credentials.email or not credentials.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )
    try:
        result = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        return JSONResponse(
            status_code=200,
            content={
                "access_token": result.session.access_token,
                "refresh_token": result.session.refresh_token
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"}
        )

@app.get("/public/info", summary="Public info, no auth required")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile", summary="Get private profile data")
def protected_profile(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"error": "Access token required"}
        )
    token = authorization.split(" ")[1]
    return {"message": "Token received (not yet verified)", "token_preview": token[:10] + "..."}    