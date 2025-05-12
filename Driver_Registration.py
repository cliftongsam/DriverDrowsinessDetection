import dlib
import cv2
import numpy as np
import time
import sqlite3
import database


# Load Dlib's Models
frontal_detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat") # Landmark detection model
face_rec_model = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat") # Face embedding model

# Initialize database
database.initialize_database()

# Function to Generate Face Embedding
def generate_face_embedding(image, face):
    landmarks = predictor(image, face) # Extract facial landmarks
    embedding = np.array(face_rec_model.compute_face_descriptor(image, landmarks), dtype=np.float32)
    
    # Debug information for verification
    print(f"Generated embedding shape: {embedding.shape}, size: {embedding.size}, dtype: {embedding.dtype}, bytes: {embedding.nbytes}")
    
    
    
    # Validate the embedding landmarks
    if embedding.shape != (128,):
        raise ValueError(f"Unexpected embedding size: {embedding.shape}, Expected (128,).")
    return embedding


# Register a New Driver
def register_driver():  
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) # Lower resolution to help with bandwidth
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240) # Lower resolution
    cap.set(cv2.CAP_PROP_FPS, 15) # Lower framerate to help with bandwidth issues
    
    print("Press 'c' to capture the image for registration, or 'q' to quit.")

    frame_count = 0   # For frame skipping
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        frame_count += 1
        # Skip every other frame to reduce load
        if frame_count % 2 != 0:
            continue
            

        # Process the frame for display
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = frontal_detector(gray, 1)
        
        if len(faces) > 0: 
            # Draw rectangles around detected faces
            for face in faces:
                x, y, w, h = face.left(), face.top(), face.width(), face.height()
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.imshow("Driver Registration", frame)
        key = cv2.waitKey(10) & 0xFF
        
        if key == ord('c'):  # Capture the frame
            if len(faces) == 0:
                print("No faces detected. Try again.")
                continue

            embedding = generate_face_embedding(frame, faces[0])
            driver_id = input("Enter Driver ID: ").strip()
            driver_name = input("Enter Driver Name (First and Last): ").strip()
            first_name, *last_name_parts = driver_name.split(" ", 1)
            last_name = " ".join(last_name_parts) if last_name_parts else ""

            # Convert embedding to bytes for storage
            embedding_bytes = embedding.tobytes()
            # Verify byte size
            if len(embedding_bytes) != 512:
                print(f"Error: Embedding byte size is {len(embedding_bytes)}. Expected 512 bytes.")
                continue
        
            # Register the driver in the SQLite database
            user_id = database.get_or_create_driver(driver_id, first_name, last_name, "Driver", embedding_bytes)

            print(f"Driver {driver_name} registered successfully!")
            break
            
        elif key == ord('q'):  # Quit
            print("Registration canceled.")
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    database.close_connection()


# Run Driver Registration
if __name__ == "__main__":
    register_driver()
