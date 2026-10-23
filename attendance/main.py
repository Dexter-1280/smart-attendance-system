
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import os
import time
import shutil
from database import (
    initialize_database,
    register_student,
    get_students,
    start_session,
    finish_session,
    mark_attendance,
    get_attendance_records,
    export_attendance
)

from face_engine import FaceEngine
from attendance_report import generate_attendance_report


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, "faces")
os.makedirs(FACES_DIR, exist_ok=True)


class SmartAttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Attendance System")
        self.root.geometry("1150x760")
        self.root.minsize(950, 650)

        initialize_database()
        self.face_engine = FaceEngine()
        self.mode = "idle"
        self.camera_running = False
        self.selected_photo = None
        self.session_id = None
        self.last_recognition_time = 0
        self.recognition_interval = 0.8
        self.marked_this_session = set()
        self.last_results = []

        self.name_var = tk.StringVar()
        self.roll_var = tk.StringVar()
        self.photo_var = tk.StringVar(value="No photo selected")
        self.status_var = tk.StringVar(value="Ready")

        self.create_widgets()
        self.refresh_students()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        container = ttk.Frame(self.root, padding=15)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="SMART ATTENDANCE SYSTEM",
            font=("Arial", 22, "bold")
        ).pack(pady=(0, 15))

        body = ttk.Frame(container)
        body.pack(fill="both", expand=True)

        camera_frame = ttk.LabelFrame(
            body,
            text="Live Camera",
            padding=10
        )
        camera_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 12)
        )

        self.camera_label = ttk.Label(
            camera_frame,
            text="Camera is stopped",
            anchor="center"
        )
        self.camera_label.pack(fill="both", expand=True)

        control_frame = ttk.LabelFrame(
            body,
            text="Student Registration and Controls",
            padding=12
        )
        control_frame.pack(side="right", fill="y")

        ttk.Label(control_frame, text="Student Name").pack(
            anchor="w",
            pady=(4, 3)
        )

        ttk.Entry(
            control_frame,
            textvariable=self.name_var,
            width=30
        ).pack(fill="x", pady=(0, 8))

        ttk.Label(control_frame, text="Roll Number").pack(
            anchor="w",
            pady=(4, 3)
        )

        ttk.Entry(
            control_frame,
            textvariable=self.roll_var,
            width=30
        ).pack(fill="x", pady=(0, 8))

        ttk.Button(
            control_frame,
            text="Upload Student Photo",
            command=self.select_photo
        ).pack(fill="x", pady=5)

        ttk.Label(
            control_frame,
            textvariable=self.photo_var,
            wraplength=230
        ).pack(fill="x", pady=5)

        ttk.Button(
            control_frame,
            text="Register Student",
            command=self.register
        ).pack(fill="x", pady=5)

        ttk.Separator(control_frame).pack(fill="x", pady=10)

        ttk.Button(
            control_frame,
            text="Start Attendance",
            command=self.start_attendance
        ).pack(fill="x", pady=5)

        ttk.Button(
            control_frame,
            text="Stop Attendance",
            command=self.stop_attendance
        ).pack(fill="x", pady=5)

        ttk.Button(
            control_frame,
            text="View Attendance",
            command=self.view_attendance
        ).pack(fill="x", pady=5)

        ttk.Button(
            control_frame,
            text="Export Attendance CSV",
            command=self.export_records
        ).pack(fill="x", pady=5)

        ttk.Button(
            control_frame,
            text="Generate Attendance Report",
            command=self.generate_report
        ).pack(fill="x", pady=5)

        ttk.Button(
            control_frame,
            text="Refresh Students",
            command=self.refresh_students
        ).pack(fill="x", pady=5)

        ttk.Separator(control_frame).pack(fill="x", pady=10)

        ttk.Label(
            control_frame,
            text="Registered Students",
            font=("Arial", 11, "bold")
        ).pack(anchor="w")

        self.student_count_var = tk.StringVar()

        ttk.Label(
            control_frame,
            textvariable=self.student_count_var
        ).pack(anchor="w", pady=5)

        status_frame = ttk.LabelFrame(
            container,
            text="System Status",
            padding=10
        )
        status_frame.pack(fill="x", pady=(12, 0))

        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            wraplength=1000
        ).pack(anchor="w")

    def select_photo(self):
        filename = filedialog.askopenfilename(
            title="Select Student Photo",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png"),
                ("All Files", "*.*")
            ]
        )

        if filename:
            self.selected_photo = filename
            self.photo_var.set(os.path.basename(filename))

    def register(self):
        if self.mode != "idle":
            messagebox.showwarning(
                "Camera Active",
                "Stop the current attendance session before registering."
            )
            return

        name = self.name_var.get().strip()
        roll_number = self.roll_var.get().strip()

        if not name or not roll_number or not self.selected_photo:
            messagebox.showwarning(
                "Missing Information",
                "Enter the student's name and roll number, then upload a photo."
            )
            return

        students = get_students()

        if len(students) >= 3:
            messagebox.showerror(
                "Registration Limit",
                "Exactly 3 students can be registered in this project."
            )
            return

        if any(
            student["roll_number"].casefold() == roll_number.casefold()
            for student in students
        ):
            messagebox.showerror(
                "Duplicate Roll Number",
                "This roll number is already registered."
            )
            return

        try:
            encoding = self.face_engine.encode_photo(
                self.selected_photo
            )

            extension = os.path.splitext(
                self.selected_photo
            )[1].lower()

            if extension not in (".jpg", ".jpeg", ".png"):
                raise ValueError("Choose a JPG, JPEG, or PNG image.")

            destination = os.path.join(
                FACES_DIR,
                f"{roll_number}{extension}"
            )

            if os.path.exists(destination):
                raise ValueError(
                    "A photo with this roll number already exists."
                )

            shutil.copy2(
                self.selected_photo,
                destination
            )

            try:
                register_student(
                    name,
                    roll_number,
                    encoding,
                    destination
                )
            except Exception:
                if os.path.exists(destination):
                    os.remove(destination)
                raise

            self.name_var.set("")
            self.roll_var.set("")
            self.selected_photo = None
            self.photo_var.set("No photo selected")

            self.refresh_students()

            messagebox.showinfo(
                "Registration Successful",
                f"{name} has been registered successfully."
            )

        except Exception as error:
            messagebox.showerror(
                "Registration Failed",
                str(error)
            )

    def start_attendance(self):
        if self.mode != "idle":
            messagebox.showwarning(
                "Session Active",
                "An attendance session is already running."
            )
            return

        students = get_students()

        if len(students) != 3:
            messagebox.showwarning(
                "Registration Required",
                "Register all 3 students before starting attendance."
            )
            return

        if not self.face_engine.open_camera():
            messagebox.showerror(
                "Camera Error",
                "Unable to open the webcam. Check camera permissions."
            )
            return

        try:
            self.session_id = start_session()
        except Exception as error:
            self.face_engine.close_camera()

            messagebox.showerror(
                "Session Error",
                str(error)
            )
            return

        self.mode = "attendance"
        self.camera_running = True
        self.marked_this_session.clear()
        self.last_results = []
        self.last_recognition_time = 0

        self.status_var.set(
            "Attendance session started. Waiting for recognized students."
        )

        self.update_camera()

    def stop_attendance(self):
        if self.mode != "attendance":
            self.face_engine.close_camera()
            self.camera_running = False
            self.mode = "idle"

            self.camera_label.configure(
                image="",
                text="Camera is stopped"
            )
            self.camera_label.image = None

            self.status_var.set("Camera stopped.")
            return

        completed_session = self.session_id

        self.camera_running = False
        self.mode = "idle"
        self.session_id = None

        self.face_engine.close_camera()

        if completed_session:
            finish_session(completed_session)

        self.camera_label.configure(
            image="",
            text="Camera is stopped"
        )
        self.camera_label.image = None

        self.show_session_summary(completed_session)

    def update_camera(self):
        if not self.camera_running:
            return

        frame = self.face_engine.read_frame()

        if frame is None:
            self.stop_attendance()

            messagebox.showerror(
                "Camera Error",
                "Could not read a frame from the webcam."
            )
            return

        current_time = time.monotonic()

        if current_time - self.last_recognition_time >= self.recognition_interval:
            self.last_recognition_time = current_time

            self.last_results = self.face_engine.recognize_faces(
                frame,
                get_students()
            )

            for result in self.last_results:
                student = result["student"]

                if student is None:
                    continue

                student_id = student["id"]

                if student_id in self.marked_this_session:
                    continue

                try:
                    inserted = mark_attendance(
                        student_id,
                        self.session_id
                    )

                    self.marked_this_session.add(student_id)

                    if inserted:
                        self.status_var.set(
                            f"Attendance marked: {student['name']} "
                            f"({student['roll_number']})"
                        )
                    else:
                        self.status_var.set(
                            f"{student['name']} already has attendance "
                            "recorded in this session."
                        )

                except Exception as error:
                    self.status_var.set(
                        f"Attendance error: {error}"
                    )

        display_frame = frame.copy()

        for result in self.last_results:
            top, right, bottom, left = result["location"]

            if result["student"] is None:
                color = (0, 0, 255)
            else:
                color = (0, 180, 0)

            cv2_label = result["name"]

            import cv2

            cv2.rectangle(
                display_frame,
                (left, top),
                (right, bottom),
                color,
                2
            )

            cv2.rectangle(
                display_frame,
                (left, max(0, bottom - 30)),
                (right, bottom),
                color,
                -1
            )

            cv2.putText(
                display_frame,
                cv2_label,
                (left + 5, bottom - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2
            )

        import cv2

        display_frame = cv2.cvtColor(
            display_frame,
            cv2.COLOR_BGR2RGB
        )

        image = Image.fromarray(display_frame)

        width = max(400, self.camera_label.winfo_width())
        height = max(300, self.camera_label.winfo_height())

        image.thumbnail((width, height))

        photo = ImageTk.PhotoImage(image=image)

        self.camera_label.configure(
            image=photo,
            text=""
        )
        self.camera_label.image = photo

        self.root.after(30, self.update_camera)

    def show_session_summary(self, session_id):
        if not session_id:
            return

        records = get_attendance_records(session_id)
        present_roll_numbers = {
            record["roll_number"] for record in records
        }

        students = get_students()

        present = [
            student for student in students
            if student["roll_number"] in present_roll_numbers
        ]

        not_detected = [
            student for student in students
            if student["roll_number"] not in present_roll_numbers
        ]

        lines = [
            f"Attendance session completed.",
            f"Present: {len(present)} of {len(students)}",
            "",
            "Present students:"
        ]

        if present:
            lines.extend(
                f"{student['name']} ({student['roll_number']})"
                for student in present
            )
        else:
            lines.append("None")

        lines.extend(["", "Not detected during this session:"])

        if not_detected:
            lines.extend(
                f"{student['name']} ({student['roll_number']})"
                for student in not_detected
            )
        else:
            lines.append("None")

        lines.extend([
            "",
            "Review the not-detected list before finalizing absences."
        ])

        self.status_var.set(
            f"Session completed. {len(present)} students marked present."
        )

        messagebox.showinfo(
            "Attendance Summary",
            "\n".join(lines)
        )

    def refresh_students(self):
        students = get_students()

        self.student_count_var.set(
            f"{len(students)} / 3 students registered"
        )

    def view_attendance(self):
        records = get_attendance_records()

        window = tk.Toplevel(self.root)
        window.title("Attendance Records")
        window.geometry("900x450")

        columns = (
            "name",
            "roll",
            "date",
            "time",
            "status",
            "session"
        )

        tree = ttk.Treeview(
            window,
            columns=columns,
            show="headings"
        )

        headings = {
            "name": "Student Name",
            "roll": "Roll Number",
            "date": "Date",
            "time": "Entry Time",
            "status": "Status",
            "session": "Session ID"
        }

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=140, anchor="center")

        scrollbar = ttk.Scrollbar(
            window,
            orient="vertical",
            command=tree.yview
        )

        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(10, 0),
            pady=10
        )

        scrollbar.pack(
            side="right",
            fill="y",
            padx=(0, 10),
            pady=10
        )

        for record in records:
            tree.insert(
                "",
                "end",
                values=(
                    record["name"],
                    record["roll_number"],
                    record["attendance_date"],
                    record["entry_time"],
                    record["status"],
                    record["session_id"]
                )
            )

    def export_records(self):
        try:
            filename = export_attendance()

            messagebox.showinfo(
                "Export Successful",
                f"Attendance report saved to:\n{filename}"
            )

        except Exception as error:
            messagebox.showerror(
                "Export Failed",
                str(error)
            )

    def generate_report(self):
        try:
            filename, report = generate_attendance_report()
            if report.empty:
                messagebox.showinfo(
                    "Attendance Report",
                    f"No registered students or completed sessions were found.\n\nSaved to:\n{filename}"
                )
                return

            messagebox.showinfo(
                "Attendance Report Generated",
                f"Attendance report saved to:\n{filename}\n\n"
                f"Students included: {len(report)}"
            )
        except Exception as error:
            messagebox.showerror(
                "Report Generation Failed",
                str(error)
            )

    def on_close(self):
        if self.mode == "attendance" and self.session_id:
            try:
                finish_session(self.session_id)
            except Exception:
                pass

        self.camera_running = False
        self.face_engine.close_camera()
        self.root.destroy()


if __name__ == "__main__":
    import cv2

    root = tk.Tk()
    app = SmartAttendanceApp(root)
    root.mainloop()
