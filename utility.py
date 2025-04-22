import git
import os
from datetime import datetime
import time
from picamera.array import PiRGBArray
from picamera import PiCamera
from zumi.util.vision import Vision
import cv2
import numpy as np

REPO_PATH = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter"
SUBMISSION_FOLDER = os.path.join(REPO_PATH, "submissions")
TEAM_NAME = "Zumi3843.txt"
FILE_NAME = "result.txt"
COMMIT_MESSAGE = "Submission by " + TEAM_NAME + " - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def upload_submission():
    try:
        repo = git.Repo(REPO_PATH)

        os.makedirs(SUBMISSION_FOLDER, exist_ok=True)

        team_file_path = os.path.join(SUBMISSION_FOLDER, "{}_{}".format(TEAM_NAME, FILE_NAME))
        # Add and commit the file
        repo.index.add([team_file_path])
        repo.index.commit(COMMIT_MESSAGE)
        # Push changes to GitHub
        origin = repo.remote(name='origin')
        origin.push()
        print("✅ {} successfully uploaded submission!".format(TEAM_NAME))
    except Exception as e:
        print("❌ Error: {}".format(e))

# --- Logging Function ---
def log_event(log_filename, message):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    print(timestamp + " " + message + "\n")
    with open(log_filename, mode='a', encoding='utf-8') as file:
        file.write(timestamp + " " + message + "\n")


# line_follwoer(...)
    # while(True)

    # alle mögliche IR-events 

    

# --- IR-based Line Following Functions ---
def linefolower_ir(zumi, bottom_right, bottom_left, threshold):
    # if beide sensoren weiss
        # special case 1 
        # special case 2 
    if bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(1, 16)
    elif bottom_right < threshold:
        zumi.control_motors(1, 0)  # Slight right turn
    elif bottom_left < threshold:
        zumi.control_motors(0, 1)  # Slight left turn


def scan_qr(vision):
    log_event("Initiating QR scan")
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
        log_event("QR code detected: " + qr_result)
        return qr_result.strip().lower()
    else:
        log_event("No QR code detected")
        return None
    
def right_roundabout(zumi, obj_det):
    zumi.forward(speed=10, duration=0.5)
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
            linefolower_ir(zumi,bottom_right, bottom_left, threshold)
        if (circled == obj_det) and (bottom_right < threshold and bottom_left < threshold):
            log_event("Rounds completed: " + str(circled))
            print("Rounds completed:", circled)
            break

def left_roundabout(zumi, obj_det):
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
            log_event("Rounds completed: " + str(circled) + " Turns taken: " + str(turns_taken))
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
                    linefolower_ir(zumi, bottom_right, bottom_left, threshold)
                zumi.turn_left(75)
                turns_taken += 1
                ir_readings = zumi.get_all_IR_data()
                bottom_right = ir_readings[1]
                bottom_left = ir_readings[3]
                if bottom_left < threshold:
                    zumi.forward(speed=10, duration=0.5)
            else:
                linefolower_ir(zumi, bottom_right, bottom_left, threshold)

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