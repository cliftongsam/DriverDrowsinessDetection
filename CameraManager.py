import cv2
import time
import threading

# Configuration
FRAME_WIDTH = 480
FRAME_HEIGHT = 360
FPS = 10


class WebcamFeed:
    def __init__(self, cam_index, name):
        self.cam_index = cam_index
        self.name = name
        self.cap = None
        self.frame = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()  # Help prevent race condition from occurring with multiple uses of camera
        
        
    def start(self):
        #Initialize cameras
        self.cap = cv2.VideoCapture(self.cam_index)
        if not self.cap.isOpened():
            print(f"Error: Could not open {self.name} at index {self.cam_index}")
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, FPS)
        
        self.running = True
        self.thread = threading.Thread(target = self.update, daemon = True)
        self.thread.start()
        
        # Waiting until the first frame is captured
        start_time = time.time()
        while self.frame is None and time.time() - start_time < 5: # Timeout after 5 seconds
            time.sleep(0.1)
        if self.frame is None:
            print(f"Warning: No frame captured from camera {self.cam_index} after 5 seconds.")
        return self.frame is not None
        
        
    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(1 / FPS)
    
                
    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
        
            
    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join()
        if self.cap is not None:
            self.cap.release()
  
  
def find_camera(max_index = 10):
    #Scan for available camera indices
    camera_indices = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Found camera at index {i}")
            camera_indices.append(i)
            cap.release()
    return camera_indices
