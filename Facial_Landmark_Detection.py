import dlib
import cv2

# Load Dlib's Frontal Face Detector and Shape Predictor
frontal_detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# Function to Draw Bounding Box and Facial Landmarks
def draw_landmarks_and_box(image, gray, faces):
    for face in faces:
        # Draw the bounding box around the face
        x, y, w, h = face.left(), face.top(), face.width(), face.height()
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Detect facial landmarks
        landmarks = predictor(gray, face)
        for n in range(68):
            x = landmarks.part(n).x
            y = landmarks.part(n).y
            cv2.circle(image, (x, y), 2, (0, 0, 255), -1)

# Real-Time Webcam Processing
def process_webcam_landmarks():
    cap = cv2.VideoCapture(0)  # 0 is the default webcam
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = frontal_detector(gray, 1)  # Upsample once for better accuracy

        draw_landmarks_and_box(frame, gray, faces)
        cv2.imshow("Facial Landmarks", frame)

        # Exit on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Run Real-Time Facial Landmarks Detection
process_webcam_landmarks()
