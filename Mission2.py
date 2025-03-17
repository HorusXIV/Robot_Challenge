from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import os
import cv2
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera

# Initialize Zumi and Screen
zumi = Zumi()
screen = Screen()

# Initialize PiCamera
camera = PiCamera()
camera.rotation = 180
camera.resolution = (320, 240)
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(320, 240))

# Define image save directory
image_dir = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_images/"
os.makedirs(image_dir, exist_ok=True)

# Define CSV file for logging events
csv_filename = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_runtime.csv"

# Function to detect Lego figures
def detect_lego(frame):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny edge detection
    edges = cv2.Canny(blurred, 20, 120)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        # Check if object is within the expected Lego figure size range
        if 30 < w < 100 and 50 < h < 200:
            cv2.rectangle(edges, (x, y), (x + w, y + h), (255, 255, 255), 2)
            return True, edges  # Return edges with bounding box

    return False, edges  # No Lego figure detected

# Start time
start_time = time.time()
zumi.reset_gyro()
turns = 0

# Open CSV file to log events
with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    while True:
        # Capture a frame from the camera
        camera.capture(raw_capture, format="bgr", use_video_port=True)
        image = raw_capture.array

        # Check for Lego figure
        lego_detected, edge_output = detect_lego(image)

        if lego_detected:
            zumi.stop()
            print("Lego figure detected! Stopping for 5 seconds.")
            screen.happy()
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

            # Save image with bounding box
            edge_path = os.path.join(image_dir, "lego_edges_{}.jpg".format(timestamp))
            cv2.imwrite(edge_path, edge_output)
          
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

        # message = "    IR readings        "
        # message = message + str(bottom_left) + ", " + str(bottom_right)
        # screen.draw_text(message)

        # Threshold for detecting black (190-200) vs grey (100-120)
        threshold = 150  

        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=10, duration=0.2)
            zumi.turn_right(45)
            ir_readings = zumi.get_all_IR_data()
            bottom_right = ir_readings[1]
            bottom_left = ir_readings[3]
            if bottom_right < threshold or bottom_left < threshold:
                zumi.signal_left_on()
                zumi.turn_left(90)
                time.sleep(0.3)
                zumi.signal_left_off()
            else:
                zumi.signal_right_on()
                zumi.signal_right_off()

        elif bottom_right > threshold and bottom_left > threshold:
            zumi.control_motors(5, 10)
            #zumi.forward(15,0.2)
            if zumi.read_z_angle() > 40 or zumi.read_z_angle() < -40:
                turns += 1
            zumi.reset_gyro()

        elif bottom_right < threshold:
            zumi.control_motors(10, 0)  # Slight right turn

        elif bottom_left < threshold:
            zumi.control_motors(0, 10)  # Slight left turn
        
        if front_right < 50 and front_left < 50:
            zumi.stop()
            break

# Record end time
end_time = time.time()

# Log final runtime in CSV
with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow([start_time, end_time, turns])