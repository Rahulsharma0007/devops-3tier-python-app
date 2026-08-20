import os
import time
from typing import Any

import pymysql
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "tasksdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "apppassword")


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
    )


def init_db(retries: int = 30, delay: int = 2) -> None:
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            connection = get_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            title VARCHAR(255) NOT NULL,
                            completed BOOLEAN NOT NULL DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
            finally:
                connection.close()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"Could not initialize MySQL: {last_error}")


def validate_title(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be JSON")
    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title is required")
    return title.strip()


@app.get("/api/health")
def health():
    try:
        connection = get_connection()
        connection.close()
        return jsonify({"status": "ok", "database": "ok"})
    except Exception as exc:
        return jsonify({"status": "error", "database": str(exc)}), 503


@app.get("/api/tasks")
def list_tasks():
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, completed, created_at FROM tasks ORDER BY id DESC"
            )
            return jsonify(cursor.fetchall())
    finally:
        connection.close()


@app.post("/api/tasks")
def create_task():
    try:
        title = validate_title(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO tasks (title) VALUES (%s)", (title,))
            task_id = cursor.lastrowid
            cursor.execute(
                "SELECT id, title, completed, created_at FROM tasks WHERE id = %s",
                (task_id,),
            )
            return jsonify(cursor.fetchone()), 201
    finally:
        connection.close()


@app.put("/api/tasks/<int:task_id>")
def update_task(task_id: int):
    payload = request.get_json(silent=True)
    completed = payload.get("completed") if isinstance(payload, dict) else None

    if not isinstance(completed, bool):
        return jsonify({"error": "completed must be boolean"}), 400

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET completed = %s WHERE id = %s",
                (completed, task_id),
            )
            if cursor.rowcount == 0:
                return jsonify({"error": "task not found"}), 404
            cursor.execute(
                "SELECT id, title, completed, created_at FROM tasks WHERE id = %s",
                (task_id,),
            )
            return jsonify(cursor.fetchone())
    finally:
        connection.close()


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "task not found"}), 404
            return jsonify({"message": "task deleted"})
    finally:
        connection.close()


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
