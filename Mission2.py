from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import os
import cv2
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera

from utility import upload_submission

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

# Define text file for logging events (will be rewritten each time)
log_filename = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/submissions/DaLuYaZe_result.txt"

# Function to detect Playmobil figures with improved background filtering
def detect_playmobil(frame):
    # Convert to HSV for better color segmentation
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Define color ranges for common Playmobil colors (bright plastic colors)
    # Yellow, red, blue, green, etc.
    color_ranges = [
        # Yellow
        (np.array([20, 100, 100]), np.array([30, 255, 255])),
        # Red (two ranges because red wraps around in HSV)
        (np.array([0, 100, 100]), np.array([10, 255, 255])),
        (np.array([160, 100, 100]), np.array([180, 255, 255])),
        # Blue
        (np.array([100, 100, 100]), np.array([130, 255, 255])),
        # Green
        (np.array([40, 100, 100]), np.array([80, 255, 255])),
    ]
    
    # Create a mask for all defined color ranges
    color_mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
    for lower, upper in color_ranges:
        mask = cv2.inRange(hsv, lower, upper)
        color_mask = cv2.bitwise_or(color_mask, mask)
    
    # Apply morphological operations to clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours in the mask
    contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Create a copy of the original frame for visualization
    result_image = frame.copy()
    
    for contour in contours:
        # Calculate contour area to filter out small noise
        area = cv2.contourArea(contour)
        if area < 500:  # Filter small areas
            continue
            
        x, y, w, h = cv2.boundingRect(contour)
        
        # Calculate aspect ratio to help identify figures (Playmobil figures are typically taller than wide)
        aspect_ratio = h / float(w)
        
        # Playmobil figures typically have aspect ratio > 1.5 (taller than wide)
        # and are not too thin or too wide
        if 1.5 < aspect_ratio < 4 and 20 < w < 80 and 40 < h < 150:
            # Draw bounding box
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            return True, result_image
    
    return False, result_image

# Start time
start_time = time.time()
zumi.reset_gyro()
turns = 0
playmobil_detections = 0

# Write to text log file (overwrite instead of append)
with open(log_filename, mode='w', encoding='utf-8') as file:
    file.write("Run started: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)) + "\n")

# Main loop
while True:
    # Capture a frame from the camera
    camera.capture(raw_capture, format="bgr", use_video_port=True)
    image = raw_capture.array
    
    # Check for Playmobil figure
    playmobil_detected, result_image = detect_playmobil(image)
    
    if playmobil_detected:
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
        zumi.control_motors(5, 20)
        if zumi.read_z_angle() > 40 or zumi.read_z_angle() < -40:
            turns += 1
        zumi.reset_gyro()
    
    elif bottom_right < threshold:
        zumi.control_motors(5, 0)  # Slight right turn
    
    elif bottom_left < threshold:
        zumi.control_motors(0, 5)  # Slight left turn
    
    if front_right < 50 and front_left < 50:
        zumi.stop()
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