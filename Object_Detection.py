import cv2
import numpy as np
import time
from picamera.array import PiRGBArray
from picamera import PiCamera

# Initialize PiCamera
camera = PiCamera()
camera.rotation = 180
camera.resolution = (320, 240)  # Lower resolution for better performance
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(320, 240))

# Allow camera to warm up
time.sleep(2)

def detect_vertical_objects(frame):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Canny edge detection (Optimized thresholds)
    low_threshold = 20
    high_threshold = 120
    edges = cv2.Canny(blurred, low_threshold, high_threshold)
    
    # Apply morphological operations to enhance edges
    kernel = np.ones((3, 3), np.uint8)  # Kernel for dilation
    dilated_edges = cv2.dilate(edges, kernel, iterations=1)

    # Detect vertical lines using Hough Transform
    lines = cv2.HoughLinesP(dilated_edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=5)

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Check if the line is mostly vertical
            if abs(x1 - x2) < 20 and abs(y1 - y2) > 50:  
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Draw green line

    return frame, dilated_edges

# Start capturing frames
for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):
    image = frame.array  # Convert to numpy array
    
    # Detect vertical objects
    processed_frame, edge_output = detect_vertical_objects(image)

    # Save processed frames (since imshow doesn't work on Zumi)
    cv2.imwrite("/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_images/detected_objects.jpg", processed_frame)
    cv2.imwrite("/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_images/edges.jpg", edge_output)

    print("Images saved")

    # Clear the stream for the next frame
    raw_capture.truncate(0)

    # Add a delay to control processing speed
    time.sleep(1)  # Capture a frame every second
