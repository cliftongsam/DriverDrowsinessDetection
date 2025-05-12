import numpy as np
import pyaudio
import queue
import threading
import time
import pvrhino

DEVICE_INDEX = 2 # USB Audio device index

class VoiceIntentHandler:
	def __init__(self, access_key, context_path, device_index = 2):
		self.intent_queue = queue.Queue()
		self.device_index = device_index
		try:
			self.rhino = pvrhino.create(
				access_key = access_key, 
				context_path = context_path,
				sensitivity = 0.5
			)
			print("Rhino initialized successfully.")
		except Exception as e:
			print(f"Error initializing Rhino: {e}")
			self.rhino = None
			raise
		self.running = False
		self.audio = pyaudio.PyAudio()
		self.sample_rate = self.rhino.sample_rate    # Should be 16000 Hz
		self.frame_length = self.rhino.frame_length
		self.stream = None
		
		
	def process_audio(self):
		if self.rhino is None:
			print("Rhino not initialized. Cannot process audio.")
			return
			
		try:
			print(f"Opening audio stream on device index {self.device_index}")
			self.stream = self.audio.open(
				format = pyaudio.paInt16, 
				channels = 1,    # Mono, has been confirmed to work on raspberry pi
				rate = self.sample_rate,   # 16000 Hz
				input = True,
				frames_per_buffer = self.frame_length,
				input_device_index = self.device_index, 
				output = False,   # No output, only input
				stream_callback = None    # Avoiding JACK, which is causing errors
			)
			print("Listening for 'stop' command.")
		except Exception as e:
			print(f"Error opening audio stream: {e}")
			self.running = False
			return

		
		while self.running:
			try:
				pcm = self.stream.read(self.frame_length, exception_on_overflow = False)
				audio_data = np.frombuffer(pcm, dtype = np.int16)
				is_finalized = self.rhino.process(audio_data)
				if is_finalized:
					inference = self.rhino.get_inference()
					if inference.is_understood and inference.intent == "stop":
						self.intent_queue.put({"intent": inference.intent, "slots": inference.slots})
						print (f"Detected intent: {inference.intent}, slots: {inference.slots}")
			except Exception as e:
				print(f"Error processing audio: {e}")
				break		
				
		if self.stream:
			self.stream.stop_stream()
			self.stream.close()
		self.audio.terminate()
		
		
	def start(self):
		if not self.running and self.rhino is not None:
			self.running = True
			self.thread = threading.Thread(target = self.process_audio, daemon = True)
			self.thread.start()
			
	def stop(self):
		self.running = False
		if hasattr(self, 'thread'):
			self.thread.join(timeout = 2)
		print("Stopped listening.")
		if self.rhino:
			self.rhino.delete()  # Clean up Rhino resources
		
	def get_intent(self):
		try: 
			return self.intent_queue.get(timeout = 0.1)
		except queue.Empty:
			return None
			
			
			
if __name__ == "__main__":
	handler = VoiceIntentHandler(
		access_key = "JyVTLj0KwBXi330WkSmjJVqHRYkldIR3aDvYw2dGAhpXIGuebNfTjw==", 
		context_path = "/home/dckaramb/project/Drowsiness_Voice.rhn",
	)
	handler.start()
	try:
		while True:
			intent_data = handler.get_intent()
			if intent_data and intent_data["intent"] == "stop":
				print("Stop command received.")
				break
			time.sleep(0.1)
	except KeyboardInterrupt:
		handler.stop()
