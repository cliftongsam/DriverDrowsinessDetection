import sqlite3
import mysql.connector
import time
from datetime import datetime

# Connect to local SQLite 
def connect_local_db():
	return sqlite3.connect('drowsiness_events_local.db')
	
# Connect to main MySQL database
# Include retry logic
def connect_main_db(max_retries = 3, retry_delay = 5):
	for attempt in range(max_retries):
		try:
			conn = mysql.connector.connect(
				#host = "10.0.0.183",
				host = "172.20.10.2",   # mobile connection
				user = "drowsiness_user",
				password = "DrowsinessPass4969!",
				database = "drowsiness_main_db"
			)
			return conn
		except mysql.connector.Error as e:
			print(f"Failed to connect to MySQL (attempt {attempt +1}/{max_retries}):{e}")
			if attempt < max_retries - 1:
				time.sleep(retry_delay)
	raise Exception("Failed to connect to MySQL after maximum retries")
	
# Sync User table
def sync_users(local_conn, main_conn):
	local_cursor = local_conn.cursor()
	main_cursor = main_conn.cursor()
	
	local_cursor.execute("SELECT UserId, DriverID, FirstName, LastName, Role, embedding FROM User WHERE synced = 0")
	users = local_cursor.fetchall()
	
	for user in users:
		user_id, driver_id, first_name, last_name, role, embedding = user
		try:
			main_cursor.execute(
				"""
				INSERT INTO User (UserID, DriverID, FirstName, LastName, Role, embedding, synced)
				VALUES (%s, %s, %s, %s, %s, %s, %s)
				ON DUPLICATE KEY UPDATE
					FirstName = VALUES(FirstName),
					LastName = VALUES(LastName),
					Role = VALUES(Role), 
					embedding = VALUES(embedding),
					synced = VALUES(synced)
				""",
				(user_id, driver_id, first_name, last_name, role, embedding, 1)
			)
			local_cursor.execute("UPDATE User SET synced = 1 WHERE UserID = ?", (user_id,))
			local_conn.commit()
			main_conn.commit()
			print(f"Synced UserID {user_id} to main database")
		except Exception as e:
			print(f"Error syncing UserID {user_id}: {e}")
			main_conn.rollback()
			
# Sync Incident table
def sync_incidents(local_conn, main_conn):
	local_cursor = local_conn.cursor()
	main_cursor = main_conn.cursor()
	
	local_cursor.execute("SELECT IncidentID, UserID, Timestamp, EventType, VideoPath FROM Incident WHERE synced = 0")
	incidents = local_cursor.fetchall()
	
	for incident in incidents:
		incident_id, user_id, timestamp, event_type, video_path = incident
		print(f"Syncing IncidentID {incident_id}: {user_id}, {timestamp}, {event_type}, {video_path}")  #DEBUGGGGGGG
		try:
			main_cursor.execute(
				"""
				INSERT INTO Incident (IncidentID, UserId, Timestamp, EventType, VideoPath, synced)
				VALUES (%s, %s, %s, %s, %s, %s)
				ON DUPLICATE KEY UPDATE
					UserID = VALUES(UserID),
					Timestamp = VALUES(Timestamp),
					EventType = VALUES(EventType),
					VideoPath = VALUES(VideoPath),
					synced = VALUES(synced)
				""",
				(incident_id, user_id, timestamp, event_type, video_path, 1)
			)
			local_cursor.execute("UPDATE Incident SET synced = 1 WHERE IncidentID = ?", (incident_id,))
			local_conn.commit()
			main_conn.commit()
			print(f"Synced IncidentID {incident_id} to main database")
		except Exception as e:
			print(f"Error syncing IncidentID {incident_id}: {e}")
			main_conn.rollback()	


def has_unsynced_records(local_conn):
	# Function to check to see if there are unsynced records
	local_cursor = local_conn.cursor()
	
	# Count unsynced User records
	local_cursor.execute("SELECT COUNT(*) FROM User WHERE synced = 0")
	unsynced_users = local_cursor.fetchone()[0]
	
	# Count unsynced Incident records
	local_cursor.execute("SELECT COUNT(*) FROM Incident WHERE synced = 0")
	unsynced_incidents = local_cursor.fetchone()[0]
	
	total_unsynced = unsynced_users + unsynced_incidents
	print(f"Unsynced records: {unsynced_users} Users, {unsynced_incidents} Incidents")
	return total_unsynced > 0
						
				
def main():
	while True:
		try:
			local_conn = connect_local_db()
			main_conn = connect_main_db()
			sync_users(local_conn, main_conn)
			sync_incidents(local_conn, main_conn)
			print(f"Sync completed at {datetime.now()}")
		except Exception as e:
			print(f"Sync failed: {e}")
		finally:
			local_conn.close()
			main_conn.close()
		time.sleep(300)  #Sync every 5 mins
		
if __name__ == "__main__":
	main()	
