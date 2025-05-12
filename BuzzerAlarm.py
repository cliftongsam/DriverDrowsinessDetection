import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

BUZZER_PIN = 17

GPIO.setup(BUZZER_PIN, GPIO.OUT)

try:
	print("Testing the buzzer. Press Ctrl+C to stop.")
	while True:
		# Turn buzzer on
		GPIO.output(BUZZER_PIN, GPIO.HIGH)
		print("Buzzer ON")
		time.sleep(1)
		
		GPIO.output(BUZZER_PIN, GPIO.LOW)
		print("Buzzer OFF")
		time.sleep(1)
		
except KeyboardInterrupt:
	print("\nTest stopped by user")

finally:
	GPIO.cleanup()
	print("GPIO cleaned up.")	
	
	
