
import sqlite3
import os
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FACES_DIR = os.path.join(BASE_DIR, "faces")
ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")
DB_PATH = os.path.join(DATA_DIR, "attendance.db")

MAX_STUDENTS = 3

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE,
                face_encoding TEXT NOT NULL,
                photo_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Present',
                FOREIGN KEY(student_id) REFERENCES students(id),
                UNIQUE(student_id, attendance_date)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL DEFAULT 'Active'
            )
        """)


def register_student(name, roll_number, face_encoding, photo_path):
    name = name.strip()
    roll_number = roll_number.strip()

    if not name or not roll_number:
        raise ValueError("Name and roll number are required.")

    encoding_string = ",".join(
        str(float(value)) for value in face_encoding
    )

    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM students WHERE roll_number = ?",
            (roll_number,)
        ).fetchone()

        if existing:
            raise ValueError("This roll number is already registered.")

        count = connection.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        if count >= MAX_STUDENTS:
            raise ValueError("Only 3 students can be registered.")

        connection.execute("""
            INSERT INTO students
            (name, roll_number, face_encoding, photo_path, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            roll_number,
            encoding_string,
            photo_path,
            created_at
        ))


def get_students():
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, name, roll_number, face_encoding, photo_path
            FROM students
            ORDER BY id
        """).fetchall()


def start_session():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    start_time = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO sessions
            (session_id, start_time, status)
            VALUES (?, ?, 'Active')
        """, (session_id, start_time))

    return session_id


def finish_session(session_id):
    end_time = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        connection.execute("""
            UPDATE sessions
            SET end_time = ?, status = 'Completed'
            WHERE session_id = ?
        """, (end_time, session_id))


def mark_attendance(student_id, session_id):
    now = datetime.now()
    attendance_date = now.strftime("%Y-%m-%d")
    entry_time = now.strftime("%H:%M:%S")

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT OR IGNORE INTO attendance
            (student_id, session_id, attendance_date, entry_time, status)
            VALUES (?, ?, ?, ?, 'Present')
        """, (
            student_id,
            session_id,
            attendance_date,
            entry_time
        ))

        return cursor.rowcount == 1


def get_attendance_records(session_id=None):
    with get_connection() as connection:
        query = """
            SELECT
                s.name,
                s.roll_number,
                a.attendance_date,
                a.entry_time,
                a.status,
                a.session_id
            FROM attendance a
            JOIN students s ON s.id = a.student_id
        """

        if session_id:
            query += " WHERE a.session_id = ?"
            query += " ORDER BY a.entry_time"
            return connection.execute(query, (session_id,)).fetchall()

        query += " ORDER BY a.attendance_date DESC, a.entry_time DESC"
        return connection.execute(query).fetchall()


def export_attendance(session_id=None):
    records = get_attendance_records(session_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(
        ATTENDANCE_DIR,
        f"attendance_{timestamp}.csv"
    )

    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        writer.writerow([
            "Name",
            "Roll Number",
            "Date",
            "Entry Time",
            "Status",
            "Session ID"
        ])

        for record in records:
            writer.writerow([
                record["name"],
                record["roll_number"],
                record["attendance_date"],
                record["entry_time"],
                record["status"],
                record["session_id"]
            ])

    return filename
