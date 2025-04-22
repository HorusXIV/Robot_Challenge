from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import datetime
import os
import cv2
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
from zumi.util.vision import Vision  # Built-in Vision module
from utility import upload_submission

# Initialize Zumi, Screen and Vision
zumi = Zumi()
screen = Screen()
vision = Vision()

# Initialize PiCamera for object detection only
camera = PiCamera()
camera.rotation = 180
camera.resolution = (320, 240)
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(320, 240))

# Define directories and log file
image_dir = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_images/"
os.makedirs(image_dir, exist_ok=True)
log_filename = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/submissions/DaLuYaZe_result.txt"

# --- Object Detection Function ---
def detect_playmobil(frame, debug_dir=None):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    result_image = frame.copy()
    result = {"figure": False, "cone": False}

    # FIGURE DETECTION: use multiple color ranges
    color_ranges_figure = [
        (np.array([20, 100, 100]), np.array([30, 255, 255])),     # Yellow
        (np.array([0, 100, 100]), np.array([10, 255, 255])),        # Red range 1
        (np.array([160, 100, 100]), np.array([180, 255, 255])),     # Red range 2
        (np.array([100, 100, 100]), np.array([130, 255, 255])),     # Blue
        (np.array([40, 100, 100]), np.array([80, 255, 255]))        # Green
    ]
    figure_mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
    for lower, upper in color_ranges_figure:
        mask = cv2.inRange(hsv, lower, upper)
        figure_mask = cv2.bitwise_or(figure_mask, mask)
    kernel = np.ones((5, 5), np.uint8)
    figure_mask = cv2.morphologyEx(figure_mask, cv2.MORPH_OPEN, kernel)
    figure_mask = cv2.morphologyEx(figure_mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(figure_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 500:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = h / float(w)
        if 1.5 < aspect_ratio < 4 and 20 < w < 80 and 40 < h < 150:
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            result["figure"] = True

    # CONE DETECTION using LAB color space
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    L, A, B = cv2.split(lab)
    red_mask = cv2.inRange(A, 145, 255)
    small_kernel = np.ones((3, 3), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, small_kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, small_kernel)
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(debug_dir, "lab_red_mask.jpg"), red_mask)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 30 or area > 1000:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = h / float(w)
        if 0.4 < aspect_ratio < 2.5 and 10 < w < 100 and 10 < h < 100:
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
            result["cone"] = True
            break
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "detection_result.jpg"), result_image)
    return result, result_image

# --- IR-based Line Following Functions ---
def linefolower_ir(bottom_right, bottom_left, threshold):
    if bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(1, 18)
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
            linefolower_ir(bottom_right, bottom_left, threshold)
        
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

# --- New QR Code Scanning Function ---
# This function uses a temporary PiCamera instance (opened with a with‑statement)
# to capture a frame for QR scanning using the built-in Vision module.
def scan_qr():
    print("Scanning for QR code using built-in Vision...")
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
        left_roundabout(1)
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

# --- Initialization and Logging ---
start_time = time.time()
zumi.reset_gyro()
turns = 0
playmobil_detections = 0
cone_detections = 0


with open(log_filename, mode='w', encoding='utf-8') as file:
    file.write("Run started: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)) + "\n")

# --- Main Loop ---
while True:
    # Capture a frame from the object detection camera
    camera.capture(raw_capture, format="bgr", use_video_port=True)
    image = raw_capture.array
    
    # Check for Playmobil figure (or similar object) detection
    detections, result_image = detect_playmobil(image, debug_dir="/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_debug")
    
    if detections["figure"]:
        zumi.stop()
        playmobil_detections += 1
        print("Playmobil figure detected! (" + str(playmobil_detections) + ") Stopping for 5 seconds.")
        screen.happy()
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        with open(log_filename, mode='a', encoding='utf-8') as file:
            file.write(timestamp + " Playmobil detected\n")
        image_path = os.path.join(image_dir, "playmobil_detection_" + timestamp + ".jpg")
        cv2.imwrite(image_path, result_image)
        time.sleep(5)
        print("Resuming line following.")
    
    if detections["cone"]:
        zumi.stop()
        cone_detections += 1
        print("Cone detected! (" + str(cone_detections) + ") Stopping for 5 seconds.")
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        with open(log_filename, mode='a', encoding='utf-8') as file:
            file.write(timestamp + " Cone detected\n")
        image_path = os.path.join(image_dir, "cone_detection_" + timestamp + ".jpg")
        cv2.imwrite(image_path, result_image)
        time.sleep(5)
        print("Resuming line following.")
    
    # Reset the camera buffer
    raw_capture.truncate(0)
    
    # IR sensor based line following logic
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
        zumi.control_motors(1, 18)
        if zumi.read_z_angle() > 40 or zumi.read_z_angle() < -40:
            turns += 1
        zumi.reset_gyro()
    elif bottom_right < threshold:
        zumi.control_motors(5, 0)
    elif bottom_left < threshold:
        zumi.control_motors(0, 5)
    
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

# --- Final Logging and Submission ---
end_time = time.time()
total_runtime = end_time - start_time

with open(log_filename, mode='a', encoding='utf-8') as file:
    file.write("Run ended: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)) + "\n")
    file.write("Total runtime:" + str(total_runtime) + " seconds\n")
    file.write("Total turns:" + str(turns) + "\n")
    file.write("Playmobil figures detected:" + str(playmobil_detections) + "\n")

print("Run completed. Total runtime: " + str(total_runtime) + " seconds")
print("Log file saved to " + log_filename)

upload_submission()
