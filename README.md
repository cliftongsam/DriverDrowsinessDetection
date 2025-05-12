# DriverDrowsinessDetection
Driver Drowsiness Detection System for High-Risk Transportation Services and Medical Service Transportation

OVERVIEW:
This project focuses on developing a real-time driver drowsiness detection system aimed at reducing fatigue-related accidents in sectors like charter buses, taxi services, company vehicles, and emergency medical transport (e.g., ambulances). The system uses a camera-based approach to monitor facial cues such as eye closure, yawning, and head tilting, indicating fatigue. A Raspberry Pi 4 serves as the core hardware platform, and the model is trained using the Driver Drowsiness Dataset (DDD) from Kaggle.

Key Features:
1. Dual Webcam Setup: One camera monitors eye activity; the other tracks mouth movements (yawning).
2. Multi-Output Model: Simultaneous detection of eye closure and yawning using a single model.
3. Voice Command Feature: Drivers can stop fatigue alerts using speech recognition (via Picovoice).
4. Driver Profiles: Personalized data tracking for individual drivers.
5. UI Separation: Two distinct interfaces — one for drivers (including access to their footage) and another for company administrators (receiving only drowsiness event logs).
6. Privacy Safeguards: Only drowsiness logs are shared with companies, while full video access is restricted to the driver.

This system is particularly vital in industries with long shifts and high-stress roles, where fatigue poses serious safety risks. For example, ambulance drivers benefit greatly due to the life-critical nature of their job.
