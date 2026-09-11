from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="To-Do List API",
    version="1.0.0",
    description="A simple to-do list API built with FastAPI"
)

# ---------------------------
# Stage 2: In-memory task storage
# ---------------------------
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a to-do API", "done": False},
    {"id": 3, "title": "Test the endpoints", "done": False},
]

# ---------------------------
# List of all 7 endpoints, used in the "/" response
# ---------------------------
ALL_ENDPOINTS = [
    "GET /",
    "GET /health",
    "GET /tasks",
    "GET /tasks/{task_id}",
    "POST /tasks",
    "PUT /tasks/{task_id}",
    "DELETE /tasks/{task_id}",
]


# ---------------------------
# Pydantic models
# ---------------------------
class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


# ---------------------------
# Stage 0 + Stage 1: Root and health check
# ---------------------------
@app.get("/", summary="API info", description="Returns the API name, version, and a list of all available endpoints.")
def read_root():
    return {
        "name": "To-Do List API",
        "version": "1.0.0",
        "endpoints": ALL_ENDPOINTS
    }


@app.get("/health", summary="Health check", description="Returns the current status of the API.")
def health_check():
    return {"status": "ok"}


# ---------------------------
# Stage 2: Get all tasks and get a task by id
# ---------------------------
@app.get("/tasks", summary="Get all tasks", description="Returns the full list of tasks currently stored.")
def get_tasks():
    return tasks


@app.get("/tasks/{task_id}", summary="Get a single task", description="Returns one task by its id. Returns 404 if no task has that id.")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return JSONResponse(
        status_code=404,
        content={"error": f"Task with id {task_id} not found"}
    )


# ---------------------------
# Stage 3: Create a task
# ---------------------------
@app.post(
    "/tasks",
    status_code=201,
    summary="Create a task",
    description="Creates a new task. The title is required and cannot be empty or just whitespace. The new task starts with done set to false, and its id is assigned automatically."
)
def create_task(task: TaskCreate):
    if task.title is None or task.title.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"}
        )

    new_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {"id": new_id, "title": task.title.strip(), "done": False}
    tasks.append(new_task)
    return new_task


# ---------------------------
# Stage 4: Update and delete a task
# ---------------------------
@app.put(
    "/tasks/{task_id}",
    summary="Update a task",
    description="Updates the title and/or done status of an existing task by id. Returns 404 if no task has that id."
)
def update_task(task_id: int, task_update: TaskUpdate):
    for task in tasks:
        if task["id"] == task_id:
            if task_update.title is not None:
                task["title"] = task_update.title
            if task_update.done is not None:
                task["done"] = task_update.done
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task with id {task_id} not found"}
    )


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task",
    description="Deletes a task by id. Returns 404 if no task has that id, or 204 with no content if the deletion succeeds."
)
def delete_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return

    return JSONResponse(
        status_code=404,
        content={"error": f"Task with id {task_id} not found"}
    )


# ---------------------------
# Stage 5: Swagger UI
# FastAPI generates this automatically at /docs and /redoc
# No extra code needed. Run the server and visit:
# http://localhost:8000/docs
# ---------------------------