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
import cv2  # for face‐box drawing & saving

# Initialize Zumi, Screen and Vision
zumi = Zumi()
screen = Screen()
vision = Vision()

# Zähler für entfernte Objekte
object_counter = 0
face_counter   = 0

# Logging-Datei vorbereiten
log_file = open("zumi_object_log.txt", "a")

### — QR-Command-Handler — 
def cmd_turn_right():
    zumi.forward(15, 0.3)

def cmd_turn_left():
    zumi.turn_left(90)

def cmd_left_circle():
    laps = object_counter - face_counter
    if laps > 0:
        left_roundabout(laps)

def cmd_right_circle():
    laps = object_counter - face_counter
    if laps > 0:
        left_roundabout(laps)

def cmd_happy_and_exit():
    screen.happy()
    zumi.stop()
    return "exit"

def cmd_angry_and_exit():
    if hasattr(screen, 'angry'):
        screen.angry()
    else:
        zumi.stop()
    return "exit"

def cmd_celebrate_and_exit():
    if hasattr(screen, 'celebrate'):
        screen.celebrate()
    else:
        screen.happy()
    return "exit"

def cmd_stop():
    zumi.stop()
    time.sleep(3)
    scan_qr()
    return "exit"


def cmd_unknown():
    print("Unbekannter QR-Befehl")
    return None

### — Dispatch-Dictionary für QR-Befehle —
qr_actions = {
    "turn right":               cmd_turn_right,
    "turn left":                cmd_turn_left,
    "left circle":              cmd_left_circle,
    "right circle":             cmd_right_circle,
    "zumi is happy today!":     cmd_happy_and_exit,
    "zumi is angry today!":     cmd_angry_and_exit,
    "zumi is celebrating today!": cmd_celebrate_and_exit,
    "stop":                     cmd_stop,
}


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
        threshold = 100
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


def scan_qr():
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
        return qr_result.strip().lower()
    else:
        return None

def scan_face_frame(rotation=180, resolution=(320,240)):
    """Grab one BGR frame from the front camera."""
    cam = PiCamera()
    cam.rotation   = rotation
    cam.resolution = resolution
    raw_capture    = PiRGBArray(cam, size=resolution)
    time.sleep(0.1)  # short warm-up
    cam.capture(raw_capture, format="bgr", use_video_port=True)
    frame = raw_capture.array
    cam.close()
    return frame

def detect_and_log_face():
    """Detect a face, draw box, save image, increment/log counter."""
    global face_counter
    frame = scan_face_frame()
    loc   = vision.find_face(frame, scale_factor=1.05,
                             min_neighbors=8, min_size=(40,40))
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if loc:
        x,y,w,h = loc
        cv2.rectangle(frame, (x,y), (x+w,y+h), (255,0,0), 2)
        fname = "face_{}.png".format(ts)
        cv2.imwrite(fname, frame)
        face_counter += 1
        msg = "{} – Face detected! Total faces: {}".format(ts, face_counter)
    else:
        msg = "{} – No face detected".format(ts)
    print(msg)
    log_file.write(msg + "\n")
    return True if loc else False

# --- Main Loop ---
while True:
    ir_readings = zumi.get_all_IR_data()
    bottom_right = ir_readings[1]
    bottom_left = ir_readings[3]
    front_right = ir_readings[0]
    front_left = ir_readings[5]
    threshold = 100

    # Wenn etwas im Weg ist (IR-Werte tief)
    if front_right < 30 or front_left < 30:
        print("IR vorne rechts:", front_right)
        print("IR vorne links :", front_left)
        print("Threshold-Wert:", threshold)
        zumi.stop()
        time.sleep(5)
        print("Objekt erkannt – versuche QR-Code zu lesen ...")

        qr_code = scan_qr()
        time.sleep(2)

        if qr_code:
            cmd = qr_code.strip().lower()
            handler = qr_actions.get(cmd, cmd_unknown)
            result = handler()
            if result == "exit":
                break
        else:
            # Kein QR → zuerst Gesichtserkennung oder Objekt zählen
            face_found = detect_and_log_face()
            if not face_found:
                print("Gesicht nicht erkannt. Zähle als Objekt.")
                object_counter = 1
                msg = "Objekt erkannt – Zähler: {}".format(object_counter)
                print(msg)
                log_file.write(msg + "\n")


        while True:
            ir_readings = zumi.get_all_IR_data()
            front_right = ir_readings[0]
            front_left = ir_readings[5]
            if front_right > 80 and front_left > 80:
                break
            if time.time() - start_wait > MAX_WAIT:
                print("⚠️ Timeout: Objekt bleibt zu lange!")
                break
            time.sleep(0.2)

        continue  # Nichts anderes machen in dieser Runde

    # --- Linienverfolgung ---
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

# --- Ende Logging ---
log_file.write("Total entfernte Objekte erkannt: {}\n".format(object_counter))
log_file.write("Total entfernte Objekte erkannt: {}\n".format(object_counter))
log_file.write("Total erkannte Gesichter: {}\n".format(face_counter))
log_file.close()