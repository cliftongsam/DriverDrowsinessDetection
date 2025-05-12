"""This Python script implements a real-time drowsiness detection system
using OpenCV, Dlib, and TensorFlow Lite (TFLite) to monitor a driver’s facial
features and detect signs of fatigue. It captures live video from a webcam, detects
the face using Dlib’s frontal face detector, and extracts facial landmarks to calculate
the Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR). If a driver’s eyes remain closed
for more than 3 seconds, the system classifies it as drowsiness and triggers an alert.
Similarly, if a driver yawns three times within 60 seconds, the system detects excessive
yawning and issues a warning. The detected frames are saved and analyzed using a TFLite model
to ensure accuracy before generating alerts. The system displays EAR, MAR values, and warnings
in real-time using OpenCV."""

import cv2
import dlib
import numpy as np
import time
import tflite_runtime.interpreter as tflite
import os
import sqlite3
from datetime import datetime # for timestamps
import database

# Initialize database
database.initialize_database()

# Constants
EYE_CLOSED_DURATION = 3.0  # Time in seconds before detecting drowsiness
YAWN_THRESHOLD = 3  # Number of yawns required for an alert
YAWN_TIME_WINDOW = 60  # Time window in seconds for counting yawns
EAR_THRESHOLD = 0.30 # Realistic value for eye closure detection

# Variables for tracking events
yawn_timestamps = []
yawn_alert_triggered = False
last_yawn_time = 0
yawn_timer_start = None
last_yawn_alert_time = None
frame_counter = 0  # For periodic logging 

# Create a directory to save frames
FRAME_SAVE_DIR = "saved_frames"
os.makedirs(FRAME_SAVE_DIR, exist_ok = True)

# Load face detector and landmark predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# Load TFLite model
interpreter = tflite.Interpreter(model_path="d2.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()


def eye_aspect_ratio(eye):
    """Calculate the eye aspect ratio (EAR) to detect eye closure"""
    A = np.linalg.norm(np.array(eye[1]) - np.array(eye[5]))
    B = np.linalg.norm(np.array(eye[2]) - np.array(eye[4]))
    C = np.linalg.norm(np.array(eye[0]) - np.array(eye[3]))
    ear = (A + B) / (2.0 * C)
    return ear


def mouth_aspect_ratio(mouth):
    """Calculate the mouth aspect ratio (MAR) to detect yawning"""
    A = np.linalg.norm(np.array(mouth[2]) - np.array(mouth[10]))
    B = np.linalg.norm(np.array(mouth[4]) - np.array(mouth[8]))
    C = np.linalg.norm(np.array(mouth[0]) - np.array(mouth[6]))
    return (A + B) / (2.0 * C)


def detect_and_crop_face(img):
    """Detect the face in the frame and return a cropped version"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    if len(faces) > 0:
        x, y, w, h = (faces[0].left(), faces[0].top(), faces[0].width(), faces[0].height())
 
        # Ensuring coordinates are within image bounds and non-negative
        h_img, w_img = img.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img -y)
        if w <= 0 or h <= 0:
            print("Invalid crop dimensions: w = {}, h = {}".format(w, h))
            return None
 
 
        face_img = img[y:y + h, x:x + w]  # Crop the detected face

        # Check of the cropped image is empty
        if face_img.size == 0:
            print("Cropped face is empty")
            return None

        face_img = cv2.resize(face_img, (224, 224))  # Resize to match model input
        return face_img
    else:
        return None  # Return None if no face is detected


def record_video(webcam_feed, video_path, duration = 5):
    # Records short video clip when drowsiness is detected
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(video_path, fourcc, 20.0, (480, 360)) # Match webcam feed from cameras.py
    start_time = time.time()
    while (time.time() - start_time) < duration:
        frame = webcam_feed.read()
        if frame is not None:
            out.write(frame)
    out.release()


def process_camera(frame, webcam_feed, camera_label, drowsiness_event):
    # Process a single camera feed for drowsiness detection
    # Repeat for each camera
    global yawn_timestamps, yawn_timer_start, yawn_alert_triggered, last_yawn_time, last_yawn_alert_time, frame_counter
    
    if frame is None:
        print(f"{camera_label}: Frame is None in processing_camera")
        return frame
    
    # Increment frame counter for periodic logging
    frame_counter += 1
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, f"{camera_label}, {timestamp}", (10, 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                     
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)
    cropped_face = detect_and_crop_face(frame)

    # Initialize variables if not yet defined
    frame_sent = drowsiness_event.get(f'frame_sent_{camera_label}', False)
    eyes_closed_start = drowsiness_event.get(f'eyes_closed_start_{camera_label}', None)
    drowsiness_detected = drowsiness_event.get(f'drowsiness_detected_{camera_label}', False)

    # Check for yawn reset from main.py
    if drowsiness_event.get('reset_yawn', False):
        yawn_timestamps = []
        yawn_alert_triggered = False
        last_yawn_time = 0
        last_yawn_alert_time = None
        drowsiness_event['reset_yawn'] = False
        print(f"{camera_label}: Yawn state reset by STOP voice command received.")

    for face in faces:
        landmarks = predictor(gray, face)

        # Get eye and mouth landmarks
        left_eye = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)]
        right_eye = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)]
        mouth = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(48, 68)]
        
        avg_EAR = (eye_aspect_ratio(left_eye) or 0.0) + (eye_aspect_ratio(right_eye) or 0.0) / 2.0
        MAR = mouth_aspect_ratio(mouth)
        
        # Log avg_EAR periodically (every 30 frames)
        if frame_counter % 30 == 0:
            print(f"{camera_label}: avg_EAR: {avg_EAR:.4f}")
        
        # Display EAR and MAR values on screen
        cv2.putText(frame, f"EAR: {avg_EAR:.2f}", (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"MAR: {MAR:.2f}", (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Detect Drowsiness (Eye Closure for 3 Seconds)
        if avg_EAR < EAR_THRESHOLD:                            
            if eyes_closed_start is None:
                eyes_closed_start = time.time()
                frame_sent = False  # Reset frame flag when eyes first close

            elif time.time() - eyes_closed_start >= EYE_CLOSED_DURATION and not frame_sent and not drowsiness_detected:
                if cropped_face is not None:
                    print(f"{camera_label}: Sending frame to model for eye closure inference...")

                    # Save the frame before inference
                    unique_time = int(time.time())
                    frame_filename = f"{FRAME_SAVE_DIR}/eye_closure_{camera_label.lower().replace(' ', '_')}_{unique_time}.jpg"
                    cv2.imwrite(frame_filename, cropped_face)

                    # Run inference
                    input_tensor = np.expand_dims(cropped_face / 255.0, axis=0).astype(np.float32)
                    interpreter.set_tensor(input_details[0]['index'], input_tensor)
                    interpreter.invoke()
                    prediction = interpreter.get_tensor(output_details[0]['index'])
                    
                    print(f"{camera_label}: Model prediction for eye closure: {prediction[0][1]:.4f}")

                    if prediction[0][0] > 0.5:  # Drowsy detected
                        video_path = f"{FRAME_SAVE_DIR}/event_{camera_label.lower().replace(' ', '_')}_{unique_time}.avi"
                        record_video(webcam_feed, video_path)
                        print(f"{camera_label} ALERT: Drowsiness detected (Eye Closure)")
                        drowsiness_event['detected'] = True
                        drowsiness_event['event_type'] = f"Eye Closure"
                        drowsiness_event['video_path'] = video_path
                        drowsiness_detected = True
                        frame_sent = True
                        cv2.putText(frame, "Drowsy - Pull to side of road and rest!", (50, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            # Reset when eyes open again
            eyes_closed_start = None
            frame_sent = False
            drowsiness_detected = False

        # Store udpated variables in drowsiness_event for persistence
        drowsiness_event[f'eyes_closed_start_{camera_label}'] = eyes_closed_start
        drowsiness_event[f'frame_sent_"{camera_label}'] = frame_sent
        drowsiness_event[f'drowsiness_detected_{camera_label}'] = drowsiness_detected


        # Detect Excessive Yawning
        current_time = time.time()
        if MAR > 0.75 and (current_time - last_yawn_time) > 2:
            yawn_timestamps.append(current_time)
            last_yawn_time = current_time
            print(f"{camera_label}: Yawn detected! Total yawns in last 60 sec: {len(yawn_timestamps)}")

        # Remove old yawns beyond 60 sec
        yawn_timestamps = [t for t in yawn_timestamps if current_time - t <= YAWN_TIME_WINDOW]
        if len(yawn_timestamps) >= YAWN_THRESHOLD and not yawn_alert_triggered:
            if cropped_face is not None:
                print(f"{camera_label}: Sending frame to model for yawn inference...")
                unique_time = int(time.time())
                frame_filename = f"{FRAME_SAVE_DIR}/yawn_{camera_label.lower().replace(' ', '_')}_{unique_time}.jpg"
                cv2.imwrite(frame_filename, cropped_face)
                print(f"Frame saved: {frame_filename}")
                input_tensor = np.expand_dims(cropped_face / 255.0, axis=0).astype(np.float32)
                interpreter.set_tensor(input_details[0]['index'], input_tensor)
                interpreter.invoke()
                prediction = interpreter.get_tensor(output_details[0]['index'])

                print("Model Prediction:", prediction)

                if prediction[0][0] > 0.5:  # Drowsy detected
                    video_path = f"{FRAME_SAVE_DIR}/event_{camera_label.lower().replace(' ', '_')}_{unique_time}.avi"
                    record_video(webcam_feed, video_path)
                    print(f"{camera_label}: ALERT: Excessive yawning detected.")
                    drowsiness_event['detected'] = True
                    drowsiness_event['event_type'] = f"Excessive Yawning"
                    drowsiness_event['video_path'] = video_path
                    yawn_timestamps.clear()
                    yawn_alert_triggered = True
                    last_yawn_alert_time = current_time                
                    cv2.putText(frame, "Drowsy - Pull to side of road and rest!", (50, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # Reset `yawn_alert_triggered` after 60 seconds
        if yawn_alert_triggered and last_yawn_alert_time is not None and (time.time() - last_yawn_alert_time > YAWN_TIME_WINDOW):
            yawn_alert_triggered = False
            print(f"{camera_label}: Yawn alert reset after cooldown.")
   
   
    if drowsiness_event['alarm_active']:
        cv2.putText(frame, "Alarm: Drowsiness Detected!", (50, 180), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
    return frame


def start_monitoring(webcam_feed1, webcam_feed2, user_id, drowsiness_event):
    # Variable to track if a frame has already been sent for inference
    global yawn_timestamps, yawn_timer_start, yawn_alert_triggered, last_yawn_time, last_yawn_alert_time, frame_counter
    
    # Store the user_id directly in drowsiness_event
    drowsiness_event['user_id'] = user_id
    print(f"Monitoring driver with UserID: {user_id} using two cameras")
    
    print("Waiting for camera feeds to initialize.")
    max_attempts = 50
    for attempt in range(max_attempts):
        frame1 = webcam_feed1.read()
        frame2 = webcam_feed2.read()
        if frame1 is not None and frame2 is not None:
            try:
                if frame1.shape[0] > 0 and frame1.shape[1] > 0 and frame2.shape[0] > 0 and frame2.shape[1] >0:
                    print(f"Camera feeds initialized successfully. Frame1 size: {frame1.shape}, Frame2 size: {frame2.shape}")
                    break
            except AttributeError:
                pass
            print(f"Attempt {attempt+1}/{max_attempts}: Waiting for vaild frames...")
            time.sleep(0.1) # 100ms delay between attempts
        else:
            print("Error: Failed to get valid frames from cameras after multiple attempts.")
            print(f"Frame1: {frame1}, Frame2: {frame2}")
            return # Exit function if camera fails to initialize
        
    while True:
        frame1 = webcam_feed1.read()
        frame2 = webcam_feed2.read()
        
        if frame1 is None or frame2 is None: 
            print("Error: One or both camera feeds unavailable")
            break
           
        frame1 = process_camera(frame1, webcam_feed1, "Camera 1", drowsiness_event)
        frame2 = process_camera(frame2, webcam_feed2, "Camera 2", drowsiness_event)
        
        # Yield processed frames
        yield (frame1, frame2) 
    
    # Close database connection when done
    database.close_connection()
    print("Drowsiness detection thread completed.")
