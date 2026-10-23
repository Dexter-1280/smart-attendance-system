import os
from datetime import datetime

import pandas as pd

from database import ATTENDANCE_DIR, get_connection


def generate_attendance_report():
    with get_connection() as connection:
        students = pd.read_sql_query(
            """
            SELECT id AS Student_ID, name AS Name, roll_number AS Roll_Number
            FROM students
            ORDER BY id
            """,
            connection
        )

        sessions = pd.read_sql_query(
            """
            SELECT session_id AS Session_ID
            FROM sessions
            WHERE status = 'Completed'
            ORDER BY start_time
            """,
            connection
        )

        attendance = pd.read_sql_query(
            """
            SELECT student_id AS Student_ID, session_id AS Session_ID, status AS Status
            FROM attendance
            """,
            connection
        )

    if students.empty:
        report = pd.DataFrame(columns=[
            "Roll_Number", "Name", "Total_Classes", "Classes_Attended",
            "Classes_Missed", "Attendance_Percentage", "Attendance_Status"
        ])
    else:
        total_sessions = len(sessions)

        if total_sessions:
            completed_attendance = attendance[
                attendance["Session_ID"].isin(sessions["Session_ID"])
            ]
            present_counts = (
                completed_attendance[completed_attendance["Status"].str.lower() == "present"]
                .groupby("Student_ID")["Session_ID"]
                .nunique()
            )
        else:
            present_counts = pd.Series(dtype="int64")

        report = students[["Student_ID", "Name", "Roll_Number"]].copy()
        report["Total_Classes"] = total_sessions
        report["Classes_Attended"] = (
            report["Student_ID"].map(present_counts).fillna(0).astype(int)
        )
        report["Classes_Missed"] = (
            report["Total_Classes"] - report["Classes_Attended"]
        ).clip(lower=0)

        if total_sessions:
            report["Attendance_Percentage"] = (
                report["Classes_Attended"] / total_sessions * 100
            ).round(2)
        else:
            report["Attendance_Percentage"] = 0.0

        report["Attendance_Status"] = report["Attendance_Percentage"].apply(
            lambda value: "Eligible" if value >= 75 else "Low Attendance"
        )

        report = report[[
            "Roll_Number",
            "Name",
            "Total_Classes",
            "Classes_Attended",
            "Classes_Missed",
            "Attendance_Percentage",
            "Attendance_Status"
        ]]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(
        ATTENDANCE_DIR,
        f"attendance_summary_{timestamp}.csv"
    )
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)
    report.to_csv(filename, index=False, encoding="utf-8-sig")

    return filename, report
