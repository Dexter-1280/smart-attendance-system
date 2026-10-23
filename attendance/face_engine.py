
import cv2
import face_recognition
import numpy as np


class FaceEngine:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.camera = None

    def encode_photo(self, image_path):
        image = face_recognition.load_image_file(image_path)

        if image.ndim == 3 and image.shape[2] == 4:
            image = image[:, :, :3]

        locations = face_recognition.face_locations(
            image,
            model="hog"
        )

        if len(locations) != 1:
            raise ValueError(
                "The uploaded photo must contain exactly one detectable face."
            )

        encodings = face_recognition.face_encodings(
            image,
            locations
        )

        if len(encodings) != 1:
            raise ValueError(
                "Unable to extract a face encoding from this photo."
            )

        return encodings[0]

    def open_camera(self):
        if self.camera is not None and self.camera.isOpened():
            return True

        self.camera = cv2.VideoCapture(self.camera_index)

        if not self.camera.isOpened():
            self.camera.release()
            self.camera = None
            return False

        return True

    def close_camera(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def read_frame(self):
        if self.camera is None or not self.camera.isOpened():
            return None

        success, frame = self.camera.read()

        if not success:
            return None

        return frame

    def recognize_faces(self, frame, students, tolerance=0.48):
        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        small_frame = cv2.resize(
            rgb_frame,
            (0, 0),
            fx=0.5,
            fy=0.5
        )

        locations = face_recognition.face_locations(
            small_frame,
            model="hog"
        )

        encodings = face_recognition.face_encodings(
            small_frame,
            locations
        )

        known_encodings = []
        known_students = []

        for student in students:
            encoding = np.fromstring(
                student["face_encoding"],
                sep=","
            )

            if encoding.size != 128:
                continue

            known_encodings.append(encoding)
            known_students.append(student)

        results = []

        for location, encoding in zip(locations, encodings):
            top, right, bottom, left = location

            top *= 2
            right *= 2
            bottom *= 2
            left *= 2

            matched_student = None

            if known_encodings:
                distances = face_recognition.face_distance(
                    known_encodings,
                    encoding
                )

                best_index = int(np.argmin(distances))

                if distances[best_index] <= tolerance:
                    matched_student = known_students[best_index]

            results.append({
                "location": (top, right, bottom, left),
                "student": matched_student,
                "name": (
                    matched_student["name"]
                    if matched_student is not None
                    else "Unknown"
                )
            })

        return results

