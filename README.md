# Smart Attendance System 

#  Project Overview

The Smart Attendance System is a Python-based desktop application that automates student attendance using facial recognition. Instead of manually calling student names or signing an attendance sheet, the system captures faces through a webcam, identifies registered students, and records their attendance in a database.

The project aims to make attendance management faster, more convenient, and less prone to manual errors.

# Main Features
Student Registration: Register students using their name, roll number, and photograph.
Face Recognition: Use a webcam to identify registered students.
Automatic Attendance: Record attendance when a registered student's face is recognized.
Student Management: View and manage registered student records.
Attendance Sessions: Start and finish attendance sessions.
Attendance Reports: View previously recorded attendance.
Database Management: Store student information and attendance records using SQLite.
Report Export: Export attendance records for further use.
Graphical User Interface: Interact with the application through a desktop interface built using Tkinter.

| Technology          | Purpose                                        |
| ------------------- | ---------------------------------------------- |
| Python 3.11         | Main programming language                      |
| Tkinter             | Desktop graphical user interface               |
| OpenCV              | Webcam access and image processing             |
| Face Recognition    | Identifying registered students by their faces |
| Pillow              | Loading and displaying images                  |
| SQLite              | Storing student and attendance records         |
| CSV                 | Exporting attendance data                      |
| Virtual Environment | Managing project dependencies                  |
