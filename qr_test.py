from zumi.zumi import Zumi
from zumi.util.screen import Screen
import time
import datetime
import cv2
import numpy as np
from zumi.util.vision import Vision    # Built-in Vision module
from picamera import PiCamera
from picamera.array import PiRGBArray
from utility import upload_submission

# Initialize Zumi, Screen and Vision
zumi = Zumi()
screen = Screen()
vision = Vision()

# -------------------------------
# IR-based Line Following Functions
def linefolower(bottom_right, bottom_left, threshold):
    if bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(1, 5)
    elif bottom_right < threshold:
        zumi.control_motors(5, 0)  # Slight right turn
    elif bottom_left < threshold:
        zumi.control_motors(0, 5)  # Slight left turn

def right_roundabout(obj_det):
    zumi.forward(speed=10, duration=0.2)
    zumi.turn_right(75)
    turns_taken = 1
    circled = 0
    while True:
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        threshold = 100  # Black vs. grey threshold
        
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=10, duration=0.2)
            if turns_taken % 4 == 0:
                turns_taken = 0
                circled += 1
            else:
                zumi.turn_right(75)
                turns_taken += 1
        else:
            linefolower(bottom_right, bottom_left, threshold)
        
        if (circled == obj_det) and (bottom_right < threshold and bottom_left < threshold):
            print("Rounds completed:", circled)
            break

def left_roundabout(obj_det):
    zumi.turn(180)
    turns_taken = 1
    circled = 0
    
    while True:
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        threshold = 100
        
        if turns_taken % 4 == 0:
            turns_taken = 0
            circled += 1
        
        if circled == obj_det:
            print("Rounds completed:", circled, "Turns taken:", turns_taken)
            break
        
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=10, duration=0.2)
            zumi.turn_left(75)
            turns_taken += 1
        else:
            if turns_taken % 2 == 0:
                start_time = datetime.datetime.now()
                duration = 1.5
                while (datetime.datetime.now() - start_time).total_seconds() < duration:
                    ir_readings = zumi.get_all_IR_data()
                    bottom_right = ir_readings[1]
                    bottom_left = ir_readings[3]
                    linefolower(bottom_right, bottom_left, threshold)
                zumi.turn_left(75)
                turns_taken += 1
                ir_readings = zumi.get_all_IR_data()
                bottom_right = ir_readings[1]
                bottom_left = ir_readings[3]
                if bottom_left < threshold:
                    zumi.forward(speed=10, duration=0.5)
            else:
                linefolower(bottom_right, bottom_left, threshold)

# -------------------------------
# QR Code Scanning and Command Handling using Built-in Vision
def scan_qr():
    print("Scanning for QR code using built-in Vision...")
    # Open a new PiCamera instance for QR scanning (using a with-statement to auto-close)
    with PiCamera() as cam:
        cam.rotation = 180
        cam.resolution = (320, 240)
        cam.framerate = 30
        raw_capture = PiRGBArray(cam, size=(320, 240))
        cam.capture(raw_capture, format="bgr", use_video_port=True)
        image = raw_capture.array
    qr_code = vision.find_QR_code(image)
    qr_result = vision.get_QR_message(qr_code)
    if qr_result:
        print("QR code detected:", qr_result)
        return qr_result.strip().lower()
    else:
        print("No QR code detected.")
        return None

def handle_qr(qr_data):
    command = qr_data.lower()
    if command == "turn right":
        print("Executing Turn Right: turning right 90 degrees.")
        zumi.turn_right(90)
    elif command == "turn left":
        print("Executing Turn Left: turning left 90 degrees.")
        zumi.turn_left(90)
    elif command == "left circle":
        print("Executing Left Circle roundabout.")
        left_roundabout(1)  # Default round count for testing
    elif command == "right circle":
        print("Executing Right Circle roundabout.")
        right_roundabout(1)
    elif command == "zumi is happy today!":
        print("Displaying happy expression.")
        screen.happy()
    elif command == "zumi is angry today!":
        print("Displaying angry expression.")
        if hasattr(screen, 'angry'):
            screen.angry()
        else:
            zumi.stop()
    elif command == "zumi is celebrating today!":
        print("Displaying celebration expression.")
        if hasattr(screen, 'celebrate'):
            screen.celebrate()
        else:
            screen.happy()
    elif command == "stop":
        print("Executing Stop command.")
        zumi.stop()
    else:
        print("Unknown QR code content:", qr_data)

# -------------------------------
# Main Loop
while True:
    # Get IR sensor readings for line following
    ir_readings = zumi.get_all_IR_data()
    bottom_right = ir_readings[1]
    bottom_left = ir_readings[3]
    front_right = ir_readings[0]
    front_left = ir_readings[5]
    
    threshold = 100  # IR threshold for line detection
    
    if bottom_right < threshold and bottom_left < threshold:
        zumi.reverse(speed=10, duration=0.2)
        zumi.turn_right(75)
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        if bottom_right < threshold or bottom_left < threshold:
            zumi.signal_left_on()
            zumi.turn_left(150)
            time.sleep(0.3)
            zumi.signal_left_off()
        else:
            zumi.signal_right_on()
            time.sleep(0.3)
            zumi.signal_right_off()
    elif bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(1, 5)
        if zumi.read_z_angle() > 40 or zumi.read_z_angle() < -40:
            pass  # Optionally update turn count
        zumi.reset_gyro()
    elif bottom_right < threshold:
        zumi.control_motors(5, 0)  # Slight right turn
    elif bottom_left < threshold:
        zumi.control_motors(0, 5)  # Slight left turn
    
    # If front IR sensors detect a very close obstacle, stop and scan for a QR code
    if front_right < 20 and front_left < 20:
        zumi.stop()
        time.sleep(5)
        print("Obstacle detected by front IR sensors. Scanning QR code...")
        qr_code = scan_qr()
        if qr_code:
            handle_qr(qr_code)
        else:
            print("No QR code found after IR obstacle detection. Resuming line following.")
    
    time.sleep(0.1)
