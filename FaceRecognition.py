# This code identifies a driver by comparing live webcam facial embeddings 
# with those stored in database. 
# Key features:
# - Uses Dlib for facial detection and feature extraction
# - Matches the extracted embedding against a list of registered drivers
# - Integrates with a shared webcam feed
# - Returns identified driver's information if match is found
import dlib
import cv2
import numpy as np
from cameras import WebcamFeed
import sqlite3
import time

# Load pre-trained Dlib models
detector = dlib.get_frontal_face_detector()
sp = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat") # Facial landmark predictor
facerec = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat") # Face embedding model

# Path to local SQLite database
DATABASE_PATH = "drowsiness_events_local.db"


# Function to generate 128D face embedding for a detected face
def generate_embedding(image, face):
    shape = sp(image, face) # Get facial landmarks
    embedding = np.array(facerec.compute_face_descriptor(image, shape)) 
    return embedding


# Function to load all registered drivers and their embeddings from database
def load_database():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DriverID, FirstName, LastName, embedding FROM User")
        drivers = []
        for row in cursor.fetchall():
            driver_id, first_name, last_name, embedding = row
            if embedding is not None:
                embedding_array = np.frombuffer(embedding, dtype=np.float32)
                drivers.append({
                    "id": driver_id,
                    "name": f"{first_name} {last_name}",
                    "embedding": embedding_array
                })
            else:
                print(f"Warning: Driver {first_name} {last_name} (ID: {driver_id} missing facial embedding.")
        conn.close()
        return{"drivers": drivers}
    except sqlite3.Error as e:
        print(f"Error loading database: {e}")
        return {"drivers": []}
        

# Function to recognize the driver by capturing live webcam feed and matching embeddings
def recognize_driver(webcam_feed, name="Driver Identification"):
    database = load_database()
    if len(database["drivers"]) == 0:
        print("No drivers registered in the database.")
        return None

    print("Starting driver identification. Attempting to capture face for identification.")
    #cap = cv2.VideoCapture(0)  # 0 is the default webcam
    #print("Press 'c' to capture the image for identification, or 'q' to quit.")
    
    # Create blank window to avoid "non-registered window" error
    blank_frame = np.zeros((240, 320, 3), dtype = np.uint8)  # Match resolution in cameras
    cv2.putText(blank_frame, "Waiting for camera.", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imshow(name, blank_frame)

    max_attempts = 3  # Number of attempts to capture facial information
    attempt_timeout = 5  # 5 second duration to wait for each attempt
    attempt = 0   # attempt counter
    
    # Try up to max_attempts to detect and recognize a face
    while attempt < max_attempts:
        attempt += 1
        print(f"Attempt {attempt}/{max_attempts} to capture face...")
        start_time = time.time()
        
        while time.time() - start_time < attempt_timeout:
            frame = webcam_feed.read() # Get frame from webcam
            if frame is None:
                print(f"No frame available from {name}.")
                time.sleep(0.1)
                continue


            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector(gray, 1) # Detect faces in the grayscale frame

            # Draw bounding boxes for any detected faces
            for face in faces:
                x, y, w, h = face.left(), face.top(), face.width(), face.height()
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cv2.imshow(name, frame)

            if len(faces) > 0:
                print("Face detected, cpaturing for identification.")
                embedding = generate_embedding(frame, faces[0]) # Generate embedding from first detected face
                recognized_driver = None
                min_distance = float("inf")
                threshold = 0.6 # Distance threshold for recognition

                # Compare embeddings with all stored embeddings
                for driver in database["drivers"]:
                    stored_embedding = driver["embedding"]
                    distance = np.linalg.norm(embedding - stored_embedding)
                    if distance < threshold and distance < min_distance:
                        min_distance = distance
                        recognized_driver = driver

                if recognized_driver:
                    print(f"Driver recognized: {recognized_driver['name']} (ID: {recognized_driver['id']})")
                    return recognized_driver
                else:
                    print("Driver not recognized in this attempt.")
                    break # Exit inner loop to start next attempt
                
            time.sleep(0.1)        
                
        print(f"Attempt {attempt} failed: No face detected within {attempt_timeout} seconds.")
    
    print("Identification failed after 3 attempts. Exiting.")            
    cv2.destroyWindow(name)
    return None
