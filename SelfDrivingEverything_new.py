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
from zumi.util.camera import Camera # Neu
from zumi.util.vision import Vision # Neu

from utility import upload_submission

# Initialize Zumi and Screen
zumi = Zumi()
screen = Screen()

# Initialize Zumi Camera
zumicam = Camera()
vision = Vision()

# Initialize PiCamera
camera = PiCamera()
camera.rotation = 180
camera.resolution = (320, 240)
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(320, 240))

# Define image save directory
image_dir = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_images/"
os.makedirs(image_dir, exist_ok=True)

# Define text file for logging events (will be rewritten each time)
log_filename = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/submissions/DaLuYaZe_result.txt"

# --- Detection Function ---
def detect_playmobil(frame, debug_dir=None):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    result_image = frame.copy()
    result = {"figure": False, "cone": False}

    # === FIGURE DETECTION ===
    color_ranges_figure = [
        (np.array([20, 100, 100]), np.array([30, 255, 255])),     # Yellow
        (np.array([0, 100, 100]), np.array([10, 255, 255])),      # Red range 1
        (np.array([160, 100, 100]), np.array([180, 255, 255])),   # Red range 2
        (np.array([100, 100, 100]), np.array([130, 255, 255])),   # Blue
        (np.array([40, 100, 100]), np.array([80, 255, 255]))      # Green
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

    # === CONE DETECTION: LAB COLOR SPACE ===
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    L, A, B = cv2.split(lab)

    # Red pops in A channel: white/gray has ~128, red > 145
    red_mask = cv2.inRange(A, 145, 255)

    small_kernel = np.ones((3, 3), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, small_kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, small_kernel)

    # Save red mask debug image
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

    # Save result image with bounding boxes
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "detection_result.jpg"), result_image)

    return result, result_image

def linefolower(bottom_right, bottom_left, threshold):
        if bottom_right > threshold and bottom_left > threshold:
            zumi.control_motors(1, 15)
        
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
        # print(turns_taken)
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]

        # Threshold for detecting black (190-200) vs grey (100-120)
        threshold = 100
        
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=10, duration=0.2)
            if turns_taken % 4 == 0:
                turns_taken = 0
                circled +=1
            else:
                zumi.turn_right(75)
                turns_taken += 1
        else:
            linefolower(bottom_right,bottom_left, threshold)

        if (circled == obj_det) and ((bottom_right < threshold )and (bottom_left < threshold)):
            print(circled)
            break
    


def left_roundabout(obj_det):
    zumi.turn(180)
    turns_taken = 1
    circled = 0
    left_roundabout_bool = False
    
    while True:
        # print(turns_taken)
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]

        # Threshold for detecting black (190-200) vs grey (100-120)
        threshold = 100

        if turns_taken % 4 == 0:
                turns_taken = 0
                circled += 1

        if circled == obj_det:
            print(circled)
            print(turns_taken)
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


# Start time
start_time = time.time()
zumi.reset_gyro()
turns = 0
playmobil_detections = 0
cone_detections = 0

# Write to text log file (overwrite instead of append)
with open(log_filename, mode='w', encoding='utf-8') as file:
    file.write("Run started: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)) + "\n")

# Main loop
while True:
    # Capture a frame from the camera
    camera.capture(raw_capture, format="bgr", use_video_port=True)
    image = raw_capture.array
    
    # Check for Playmobil figure
    detections, result_image = detect_playmobil(image, debug_dir="/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_debug")
    
    if detections["figure"]:
        zumi.stop()
        playmobil_detections += 1
        print("Playmobil figure detected! (" + str(playmobil_detections) + ") Stopping for 5 seconds.")
        screen.happy()
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

        with open(log_filename, mode='a', encoding='utf-8') as file:
            file.write(timestamp + "Playmobil detected\n")

        # Save image with bounding box
        image_path = os.path.join(image_dir, "playmobil_detection_" + timestamp + ".jpg")
        cv2.imwrite(image_path, result_image)
        
        time.sleep(5)  # Stop for 5 seconds
        print("Resuming line following.")

    if detections["cone"]:
        zumi.stop()
        cone_detections += 1
        print("Cone detected! (" + str(cone_detections) + ") Stopping for 5 seconds.")
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

        with open(log_filename, mode='a', encoding='utf-8') as file:
            file.write(timestamp + "Cone detected\n")

        # Save image with bounding box
        image_path = os.path.join(image_dir, "cone_detection_" + timestamp + ".jpg")
        cv2.imwrite(image_path, result_image)
        
        time.sleep(5)  # Stop for 5 seconds
        print("Resuming line following.")
    
    # Reset the camera buffer
    raw_capture.truncate(0)
    
    # Zumi's IR line-following logic
    ir_readings = zumi.get_all_IR_data()
    bottom_right = ir_readings[1]
    bottom_left = ir_readings[3]
    front_right = ir_readings[0]
    front_left = ir_readings[5]
    
    # Threshold for detecting black (190-200) vs grey (100-120)
    threshold = 100
    
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
            turns += 1
        zumi.reset_gyro()
    
    elif bottom_right < threshold:
        zumi.control_motors(5, 0)  # Slight right turn
    
    elif bottom_left < threshold:
        zumi.control_motors(0, 5)  # Slight left turn
    
    if front_right < 15 and front_left < 15:
        zumi.stop()
        time.sleep(5)  # Warten bis Hindernis entfernt

        # Scan QR-Code
        print("Scanne QR-Code...")
        zumicam.start_camera()
        frame = zumicam.capture()
        zumicam.close()
        qr_code = vision.find_QR_code(frame)
        qr_result = vision.get_QR_message(qr_code)

        # number of rounds in circle
        rounds = playmobil_detections + cone_detections

        if "Left Circle" in qr_result:
            left_roundabout(rounds)
        elif "Right Circle" in qr_result:
            right_roundabout(rounds)
        else:
            print("Kein gültiger QR-Code gefunden.")

        break


# Record end time
end_time = time.time()
total_runtime = end_time - start_time

# Write to text log file (overwrite instead of append)
with open(log_filename, mode='a', encoding='utf-8') as file:
    file.write("Run ended: "+ time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)) + "\n")
    file.write("Total runtime:" + str(total_runtime) +" seconds\n")
    file.write("Total turns:" + str(turns) + "\n")
    file.write("Playmobil figures detected:" + str(playmobil_detections) + "\n")

print("Run completed. Total runtime: " + str(total_runtime) + " seconds")
print("Log file saved to " + log_filename)

upload_submission()