import sqlite3
from datetime import datetime
import numpy as np

# Database path for "mini" database on Raspberry Pi
LOCAL_DB_PATH = "drowsiness_events_local.db"

# Global connection and cursor
conn = None
cursor = None

def initialize_database():
	# Initialize the SQLite database with User and Indicenttables
	global conn, cursor
	try:
		conn = sqlite3.connect(LOCAL_DB_PATH)
		cursor = conn.cursor()
		
		# Create User table
		# DriverID is entered during registration
		# embedding stores facial embedding as binary data
		cursor.execute('''
			CREATE TABLE IF NOT EXISTS User (
				UserID INTEGER PRIMARY KEY AUTOINCREMENT,
				DriverID VARCHAR(50) UNIQUE,
				FirstName VARCHAR(30) NOT NULL, 
				LastName VARCHAR(30) NOT NULL,
				Role VARCHAR(30) NOT NULL, 
				embedding BLOB, 
				synced INTEGER DEFAULT 0
			)
		''')
		
		# Create Incident table
		cursor.execute('''
			CREATE TABLE IF NOT EXISTS Incident (
				IncidentID INTEGER PRIMARY KEY AUTOINCREMENT, 
				UserID INTEGER NOT NULL,
				Timestamp TEXT NOT NULL,
				EventType VARCHAR(50) NOT NULL, 
				VideoPath TEXT NOT NULL,
				synced INTEGER DEFAULT 0,
				FOREIGN KEY (UserID) REFERENCES User(UserID)
			)
		''')
		conn.commit()
		
		print("Mini database initialized successfully at", LOCAL_DB_PATH)
	except sqlite3.Error as e:
		print(f"Error initializing database: {e}")
		raise

def get_or_create_driver(driver_id, first_name, last_name, role = "Driver", embedding = None):
	# Get or create a driver in the database, return the UserID
	if not cursor:
		raise Exception("Database not initialized. Call initialize_database() first.")
	try:
		# Check to see if driver already exists by DriverID
		cursor.execute("SELECT UserID FROM User WHERE DriverID = ?", (driver_id,))
		result = cursor.fetchone()
		if result:
			return result[0]			
			
		# If not found, create a new driver with optional embedding
		cursor.execute("INSERT INTO User (DriverID, FirstName, LastName, Role, embedding, synced) VALUES (?, ?, ?, ?, ?, 0)",
						(driver_id, first_name, last_name, role, sqlite3.Binary(embedding) if embedding is not None else None))
		conn.commit()
		
		# Retrieve the new UserID
		cursor.execute("SELECT UserID FROM User WHERE FirstName = ? AND Lastname = ? AND Role = ?",
						(first_name, last_name, role))
		user_id = cursor.fetchone()[0]
		print(f"Created new driver: {first_name} {last_name}, Role = {role}, UserID = {user_id}")
		return user_id
	except sqlite3.Error as e:
		print(f"Error in get_or_create_driver: {e}")
		raise
		
def log_incident(user_id, timestamp, event_type, video_path):
	# Log a drowsiness event to the Incident table
	if not cursor:
		raise Exception("Database not initialized. Call initialize_database() first.")
	try:
		cursor.execute('''
			INSERT INTO Incident (UserID, Timestamp, EventType, VideoPath, synced)
			VALUES (?, ?, ?, ?, ?)
		''', (user_id, timestamp, event_type, video_path, 0))
		conn.commit()
		print(f"Logged incident: UsserID = {user_id}, EventType = {event_type}, VideoPath = {video_path}, Timestamp = {timestamp}")
	except sqlite3.Error as e:
		print(f"Error logging incident: {e}")
		raise

def close_connection():
	# close database connection
	global conn, cursor
	try:
		if conn:
			conn.close()
			conn = None
			cursor = None
			print("Mini database connection closed.")
	except sqlite3.Error as e:
		print(f"Error closing dtabase connection: {e}")
		raise
		
if __name__ == "__main__":
	# Test module standalone
	try:
		# Initialize database
		initialize_database()
		
		# Test creating a driver with a test embedding
		test_embedding = np.zeros(128, dtype = np.float32).tobytes()
		user_id = get_or_create_driver("JD0001", "John", "Doe", "Driver", test_embedding)
		user_id2 = get_or_create_driver("SG002", "Jane", "Smith", "Driver")
		
		# Test logging an incident
		log_incident(user_id, "Eye Closure (Camera 1)", "/saved_frames/test_event_123.avi")
		
		# Verify the data in the database
		conn_test = sqlite3.connect(LOCAL_DB_PATH)
		cursor_test = conn_test.cursor()
		print("User table contents:")
		for row in cursor_test.execute("SELECT * FROM User").fetchall():
			print(row)
		conn_test.close()
		
	except Exception as e:
		print(f"Test failed: {e}")
	finally:
		# Closes connection always, even if error occurs
		close_connection()
