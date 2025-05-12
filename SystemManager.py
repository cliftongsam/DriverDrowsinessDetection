# main.py

from cameras import WebcamFeed, find_camera
from Voice_Intent import VoiceIntentHandler
from Driver_Identification import recognize_driver
from drowsiness_detection import start_monitoring 
import RPi.GPIO as GPIO 
import cv2
import time
from datetime import datetime
import database
import os


# Temp director to log events (change to SQLite)
EVENT_LOG_DIR = "event_logs"
os.makedirs(EVENT_LOG_DIR, exist_ok = True)


def log_event(event_type, video_path, user_id):
    # Log drowsiness event with timestamp and video path
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database.log_incident(user_id, timestamp, event_type, video_path)
        print(f"Logged event to database: UserID={user_id}, Timestamp={timestamp}, EventType={event_type}, VideoPath={video_path}")
    except Exception as e:
        print(f"Error logging event to database: {e}")
    
		
def main(camera_indices):
    if len(camera_indices) <2:
        print("Error: Need at least 2 cameras. Found: ", camera_indices)
        return
    
    # Initialize first camera for driver identification
    camera1 = WebcamFeed(camera_indices[0], "Driver Identification")
    camera1.start()
    time.sleep(2)  # Brief pause to ensure camera is ready
    
    # Driver identification
    print("Starting driver identification.")
    driver_login = recognize_driver(camera1)
    
    # Clean up driver identification
    camera1.stop()
    time.sleep(1)
    cv2.destroyWindow("Driver Identification")
    
    if driver_login is None: 
        print("Driver identification failed. Exiting program.")
        return
    
    driver_id = driver_login['id']  # Extract DriverID
    print(f"Driver {driver_login['name']} (ID: {driver_id}) recognized. Starting system.")
    
    # Initalize database
    database.initialize_database()
    
    # Initialize alarm
    GPIO.setmode(GPIO.BCM)
    BUZZER_PIN = 17   # GPIO pin 17, which is physical pin 11
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.LOW)  # Set alarm as off initially

    # Start drowsiness monitoring in a separate thread
    drowsiness_event = {'detected': False, 
                        'event_type': None, 
                        'video_path': None, 
                        'alarm_active': False,
                        'frame1': None,
                        'frame2': None
    }       

    
    # Lookup UserID from database
    try:
        cursor = database.conn.cursor()
        cursor.execute("SELECT UserID FROM User WHERE DriverID = ?", (driver_id,))
        result = cursor.fetchone()
        if not result:
            print(f"No driver found in database with DriverID: {driver_id}, Please register the driver first.")
            database.close_connection()
            return
        user_id = result[0]
        print(f"Retrieved UserID: {user_id} for DriverID: {driver_id}")
    except Exception as e:
        print(f"Error retrieving UserID: {e}")
        database.close_connection()
        return
        
    #Initialize both cameras for monitoring 
    camera1 = WebcamFeed(camera_indices[0], "Camera 1")
    camera2 = WebcamFeed(camera_indices[1], "Camera 2")
    if not camera1.start():
        print("Error: Camera 1 has failed to load.")   
        return
    if not camera2.start():
        print("Error: Camera 2 has failed to load.")
        camera1.stop()
        return
    time.sleep(3)

    # Flags to track camera status
    camera1_active = True
    camera2_active = True


    try:
        print(f"Driver {driver_login['name']} (ID: {driver_login['id']}) recognized. Starting system.")
        time.sleep(2)  #Short pause to ensure everything initializes
        monitoring = start_monitoring(camera1, camera2, driver_login['name'], drowsiness_event)
        # Initialize the voice intent handler
        voice_handler = VoiceIntentHandler(
            access_key = "JyVTLj0KwBXi330WkSmjJVqHRYkldIR3aDvYw2dGAhpXIGuebNfTjw==", 
            context_path = "/home/dckaramb/project/Drowsiness_Voice.rhn",
        )

        voice_handler_active = False
        alarm_start_time = None
        
        while True:
            try: 
                # Get next processed frames from monitoring
                frame1, frame2 = next(monitoring)
            except StopIteration:
                print("Monitoring stopped.")
                break
            
            if frame1 is None and camera1_active:
                print("Camera 1 feed lost. Disabling Camera 1.")
                camera1_active = False
                camera1.stop()
                cv2.destroyWindow("Camera 1 - Drowsiness Detection")
            if frame2 is None and camera2_active:    
                print("Camera 2 feed lost. Disabling Camera 1.")
                camera2_active = False
                camera2.stop()
                cv2.destroyWindow("Camera 2 - Drowsiness Detection")
                # Ensure window is fully closed
                cv2.waitKey(1)  # Brief delay to process window closure
            
            # If both cameras fail, exit the loop
            if not camera1_active and not camera2_active:
                print("Error: Both camera feeds lost. Exiting.")
                break
            
            if frame1 is not None:
                cv2.imshow("Camera 1 - Drowsiness Detection", frame1)
            if frame2 is not None:
                cv2.imshow("Camera 2 - Drowsiness Detection", frame2)
            
               
            if drowsiness_event['detected']:
                print(f"Drowsiness event: {drowsiness_event['event_type']}, video saved at {drowsiness_event['video_path']}")
                GPIO.output(BUZZER_PIN, GPIO.HIGH)  # Alarm ON
                log_event(drowsiness_event['event_type'], drowsiness_event['video_path'], user_id)  # log event to database
                drowsiness_event['detected'] = False
                drowsiness_event['alarm_active'] = True
                alarm_start_time = time.time()
                # Start voice handler when alarm is active
                if not voice_handler_active:
                    voice_handler.start()
                    voice_handler_active = True
                
            if drowsiness_event['alarm_active'] and alarm_start_time:
                try:
                    intent_data = voice_handler.get_intent()
                    if intent_data and intent_data.get("intent") == "stop":
                        print("Vocal STOP command received. Stopping alarm.")
                        GPIO.output(BUZZER_PIN, GPIO.LOW)  # Alarm OFF
                        drowsiness_event['alarm_active'] = False
                        alarm_start_time = None
                        drowsiness_event['reset_yawn'] = True   # Signal reset
                        for key in ['eyes_closed_start_Camera 1', 'eyes_closed_start_Camera 2', 'drowsiness_detected_Camera 1', 'drowsiness_detected_Camera 2']:
                            if key in drowsiness_event:
                                drowsiness_event[key] = None if "start" in key else False
                        # Stop voice handler when alarm turns off
                        if voice_handler_active:
                            voice_handler.stop()
                            voice_handler_active = False
                except Exception as e:
                    print(f"Voice intent error: {e}")
                    
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Exit by pressing 'Q' key")
                break
                
    finally:
        # Cleanup
        if camera1_active:
            camera1.stop()
        if camera2_active:    
            camera2.stop()
        if voice_handler_active:
            voice_handler.stop()
        GPIO.cleanup()
        cv2.destroyAllWindows()          
        database.close_connection()
        

if __name__ == "__main__":
    print("Scanning for available cameras")
    available_cameras = find_camera()
    
    if len(available_cameras) < 2:
        print(f"Error: Only found {len(available_cameras)} camera(s). Need 2.")
        print("Check USB connections and run 'ls /dev/video*' to verify devices/")
    else:
        device_index = 2  # This is the working device index
        print(f"Using cameras at indices: {available_cameras[0]} and {available_cameras[1]}")
        main(available_cameras)
