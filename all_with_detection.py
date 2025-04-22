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

# Zähler für entfernte Objekte
object_counter = 0

# Logging-Datei vorbereiten
log_file = open("zumi_object_log.txt", "a")


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
            command = qr_code.lower()
            print("✅ QR-Code erkannt:", command)
            if command == "turn right":
                zumi.forward(15, .3)
            elif command == "turn left":
                zumi.turn_left(90)
            elif command == "left circle":
                left_roundabout(1)
            elif command == "right circle":
                right_roundabout(1)
            elif command == "zumi is happy today!":
                screen.happy()
                zumi.stop()
                break
            elif command == "zumi is angry today!":
                if hasattr(screen, 'angry'):
                    screen.angry()
                else:
                    zumi.stop()
                break
            elif command == "zumi is celebrating today!":
                if hasattr(screen, 'celebrate'):
                    screen.celebrate()
                else:
                    screen.happy()
                break
            elif command == "stop":
                zumi.stop()
                time.sleep(3)
                scan_qr()
                break
        else:
            # Kein QR → Zähle als Objekt
            print("Kein QR-Code. Zähle als Objekt.")
            object_counter += 1
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
log_file.close()