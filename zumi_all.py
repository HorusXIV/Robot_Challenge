from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import datetime
import os
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
from zumi.util.vision import Vision  # Built-in Vision module
from utility import upload_submission, log_event

# Initialize Zumi, Screen and Vision
zumi = Zumi()
screen = Screen()
vision = Vision()


# Define directories and log file
#image_dir = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_images/"
#os.makedirs(image_dir, exist_ok=True)
#log_filename = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/submissions/Zumi3843_result.txt"


# --- IR-based Line Following Functions ---
def linefolower_ir(bottom_right, bottom_left, threshold):
    if bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(1, 10)
    elif bottom_right < threshold:
        zumi.control_motors(1, 0)  # Slight right turn
    elif bottom_left < threshold:
        zumi.control_motors(0, 1)  # Slight left turn

def right_roundabout(num_rounds):
    print("right circle")
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
            zumi.reverse(speed=15, duration=0.2)
            if turns_taken % 4 == 0:
                turns_taken = 0
                circled += 1
            else:
                zumi.turn_right(75)
                turns_taken += 1
        else:
            linefolower_ir(bottom_right, bottom_left, threshold)
        if (circled == num_rounds) and (bottom_right < threshold and bottom_left < threshold):
            #log_event("Rounds completed: " + str(circled))
            print("Rounds completed:", circled)
            zumi.turn_left(75)
            break

def left_roundabout(num_rounds):
    print("left circle")
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
        if circled == num_rounds:
            #log_event("Rounds completed: " + str(circled) + " Turns taken: " + str(turns_taken))
            break
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=15, duration=0.2)
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
                    linefolower_ir(bottom_right, bottom_left, threshold)
                zumi.turn_left(75)
                turns_taken += 1
                ir_readings = zumi.get_all_IR_data()
                bottom_right = ir_readings[1]
                bottom_left = ir_readings[3]
                if bottom_left < threshold:
                    zumi.forward(speed=10, duration=0.5)
            else:
                linefolower_ir(bottom_right, bottom_left, threshold)

# QR Code Scanning Function
def scan_qr():
    #log_event("Initiating QR scan")
    with PiCamera() as cam:
        cam.rotation = 180
        cam.resolution = (320, 240)
        cam.framerate = 30
        raw_capture_new = PiRGBArray(cam, size=(320, 240))
        cam.capture(raw_capture_new, format="bgr", use_video_port=True)
        image_new = raw_capture_new.array
    qr_code = vision.find_QR_code(image_new)
    qr_result = vision.get_QR_message(qr_code)
    if qr_result:
        #log_event("QR code detected: " + qr_result)
        return qr_result.strip().lower()
    else:
        #log_event("No QR code detected")
        return None

# Face Recognition Function
def face_rec():
    with 

# --- Initialization and Logging ---
#start_time = time.time()
#zumi.reset_gyro()
#with open(log_filename, mode='w', encoding='utf-8') as file:
#    file.write("Run started: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)) + "\n")

# --- Main Loop ---
while True:

    # Reset the camera buffer
    #raw_capture.truncate(0)
    
    # IR sensor based line following logic
    ir_readings = zumi.get_all_IR_data()
    bottom_right = ir_readings[1]
    bottom_left = ir_readings[3]
    front_right = ir_readings[0]
    front_left = ir_readings[5]
    
    threshold = 100  # IR threshold for line detection
    
    if bottom_right < threshold and bottom_left < threshold:
        zumi.reverse(speed=15, duration=0.2)
        zumi.turn_right(70)
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        if bottom_right < threshold or bottom_left < threshold:
            zumi.signal_left_on()
            zumi.turn_left(140)
            time.sleep(0.3)
            zumi.signal_left_off()
        else:
            zumi.signal_right_on()
            time.sleep(0.3)
            zumi.signal_right_off()
    elif bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(1, 10)
    elif bottom_right < threshold:
        zumi.control_motors(1, 0)
    elif bottom_left < threshold:
        zumi.control_motors(0, 1)
    
    # If front IR sensors detect a very close obstacle, perform a QR scan
    if front_right < 20 and front_left < 20:
        zumi.stop()
        time.sleep(5)
        #log_event("Front obstacle detected. Initiating QR scan.")
        qr_code = scan_qr()
        time.sleep(2)
        if qr_code:
            command = qr_code.lower()
            #log_event("QR command received: " + command)
            if command == "turn right":
                zumi.forward(15, .3)
                #log_event("Turn Right executed")
            elif command == "turn left":
                zumi.turn_left(90)
                #log_event("Turn Left executed")
            elif command == "left circle":
                rounds = 1
                #log_event("Left Circle roundabout executed with rounds: " + str(rounds))
                left_roundabout(rounds)
            elif command == "right circle":
                rounds = 1
                #log_event("Right Circle roundabout executed with rounds: " + str(rounds))
                right_roundabout(rounds)
            elif command == "zumi is happy today!":
                screen.happy()
                #log_event("Zumi happy expression displayed")
                zumi.stop()
                break
            elif command == "zumi is angry today!":
                if hasattr(screen, 'angry'):
                    screen.angry()
                else:
                    zumi.stop()
                #log_event("Zumi angry expression displayed")
                break
            elif command == "zumi is celebrating today!":
                if hasattr(screen, 'celebrate'):
                    screen.celebrate()
                else:
                    screen.happy()
                #log_event("Zumi celebrating expression displayed")
                break
            elif command == "stop":
                zumi.stop()
                #log_event("Stop command executed")
                time.sleep(3)
                qr_code = scan_qr()
                break
        elif face_rec:
            pass
        else:
            #log_event("No QR code found after IR obstacle detection. Resuming line following.")
            print("No QR code found after IR obstacle detection. Resuming line following.")
        
        


# --- Final Logging and Submission ---
#end_time = time.time()
#total_runtime = end_time - start_time

#with open(log_filename, mode='a', encoding='utf-8') as file:
#    file.write("Run ended: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)) + "\n")
#    file.write("Total runtime: " + str(total_runtime) + " seconds\n")
    
#print("Run completed. Total runtime: " + str(total_runtime) + " seconds")
#print("Log file saved to " + log_filename)

#upload_submission()