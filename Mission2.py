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

def detect_playmobil(frame):
    # Convert to HSV for better color segmentation
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Define color ranges for common Playmobil colors (bright plastic colors)
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
    
    # Define red color range for cones specifically
    red_lower1 = np.array([0, 100, 100])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 100, 100])
    red_upper2 = np.array([180, 255, 255])
    
    # Create red masks and combine them
    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    # Apply morphological operations to clean up the masks
    kernel = np.ones((5, 5), np.uint8)
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
    
    # Initialize result dictionary
    result = {
        "figure": False,
        "cone": False
    }
    
    # Create a copy of the original frame for visualization
    result_image = frame.copy()
    
    # Find contours in the color mask
    contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        # Calculate contour area to filter out small noise
        area = cv2.contourArea(contour)
        if area < 200:  # Filter small areas
            continue
            
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = h / float(w)
        
        # Create a mask of just this contour to check color composition
        contour_mask = np.zeros_like(color_mask)
        cv2.drawContours(contour_mask, [contour], 0, 255, -1)
        
        # Check if this could be a cone (smaller size than figures)
        if 1.2 < aspect_ratio < 2.5 and 10 < w < 40 and 20 < h < 80:
            # Check if there's significant red content in this contour
            contour_red_pixels = cv2.countNonZero(cv2.bitwise_and(red_mask, contour_mask))
            contour_total_pixels = cv2.countNonZero(contour_mask)
            
            red_percentage = contour_red_pixels / contour_total_pixels if contour_total_pixels > 0 else 0
            
            # If at least 30% of the object is red, classify as a cone
            if red_percentage > 0.30:
                cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(result_image, "Cone", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                result["cone"] = True
                continue  # Skip figure detection for this contour
        
        # Playmobil figures typically have aspect ratio > 1.5 and are larger than cones
        if 1.5 < aspect_ratio < 4 and 20 < w < 80 and 40 < h < 150:
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(result_image, "Figure", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            result["figure"] = True
    
    return result, result_image

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
    detections, result_image = detect_playmobil(image)
    
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
        zumi.control_motors(1, 15)
        if zumi.read_z_angle() > 40 or zumi.read_z_angle() < -40:
            turns += 1
        zumi.reset_gyro()
    
    elif bottom_right < threshold:
        zumi.control_motors(5, 0)  # Slight right turn
    
    elif bottom_left < threshold:
        zumi.control_motors(0, 5)  # Slight left turn
    
    if front_right < 15 and front_left < 15:
        print("Threshold reached, stopping programm.")
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