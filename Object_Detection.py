import cv2
import numpy as np
import time
import os
from picamera.array import PiRGBArray
from picamera import PiCamera

# --- Setup Camera ---
camera = PiCamera()
camera.rotation = 180
camera.resolution = (320, 240)
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(320, 240))

# --- Timing & Logging ---
image_dir = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_images/"
os.makedirs(image_dir, exist_ok=True)

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


# --- Main Loop ---
while True:
    print("Capturing frame...")
    camera.capture(raw_capture, format="bgr", use_video_port=True)
    image = raw_capture.array

    detections, result_image = detect_playmobil(image, debug_dir="/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_debug")

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

    if detections["figure"]:
        print("Playmobil figure detected")
        path = os.path.join(image_dir, "playmobil_" + timestamp + ".jpg")
        cv2.imwrite(path, result_image)
        time.sleep(1)

    if detections["cone"]:
        print("Cone detected")
        path = os.path.join(image_dir, "cone_" + timestamp + ".jpg")
        cv2.imwrite(path, result_image)
        time.sleep(1)

    raw_capture.truncate(0)
    time.sleep(1)