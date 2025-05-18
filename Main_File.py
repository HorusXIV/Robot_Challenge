from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import datetime
import os
import numpy as np
import matplotlib.pyplot as plt
from picamera.array import PiRGBArray
from picamera import PiCamera
from zumi.util.vision import Vision  # Built-in Vision module
from utility import upload_submission, log_event
import cv2  # for face‐box drawing & saving
import math

# Initialize Zumi, Screen and Vision
zumi = Zumi()
screen = Screen()
vision = Vision()

# Zähler für entfernte Objekte
object_counter = 0
face_counter   = 0

# Control Motors Variablen
speed_l = 10
speed_r = 8

last_qr_text = None

# Logging-Datei vorbereiten
csv_file = open("zumi_log.csv", "a", newline="")
csv_writer = csv.writer(csv_file)
# Falls die Datei neu ist, schreib Kopfzeile (optional):
if os.stat("zumi_log.csv").st_size == 0:
    csv_writer.writerow(["timestamp", "event", "count"])

# --- Mapping-Funktionalität ---
movement_log = []
current_direction = 'vertical'  # Startausrichtung
last_dir_change_time = time.time()

def record_segment(next_turn):
    """
    Speichert (Richtung, Dauer, Turn) in movement_log,
    wechselt current_direction und startet Timer neu.
    next_turn ist 'R' oder 'L' (bzw. None am Schluss).
    """
    global current_direction, last_dir_change_time, movement_log
    now = time.time()
    duration = now - last_dir_change_time
    movement_log.append((current_direction, duration, next_turn))
    # Toggle Achse
    current_direction = 'horizontal' if current_direction=='vertical' else 'vertical'
    last_dir_change_time = now

# Back on track Mission
def drive_straight_until_line():
    """
    Fahre geradeaus über eine weiße Fläche so lange,
    bis einer der unteren IR-Sensoren die Linie wieder erkennt.
    """
    zumi.control_motors(speed_l, speed_r)
    while True:
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        threshold = 100
        if bottom_right > threshold and bottom_left > threshold:
            zumi.stop()
            break
        time.sleep(0.02)

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
        right_roundabout(laps)
    global last_dir_change_time
    last_dir_change_time = time.time()

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
    """
    Wenn last_qr_text ein 'Nx 360° left|right, emotion: ...' enthält,
    dann hier spin + optional Emotion + Geradeaus bis Linie. Sonst nur print.
    """
    global last_dir_change_time

    text = last_qr_text or ""
    if "360" in text:
        # 1) Teile am Komma: ['1x 360° left', ' emotion: none']
        parts = [p.strip() for p in text.split(",", 1)]
        spin_part = parts[0]            # z.B. "2x 360° right"
        emotion_part = parts[1] if len(parts) > 1 else "emotion: none"

        # 2) Count und Richtung aus spin_part ziehen:
        #    spin_part ist z.B. "2x 360° right"
        count = int(spin_part.split("x",1)[0])
        direction = "left" if "left" in spin_part else "right"

        # 3) Spins ausführen
        for _ in range(count):
            if direction == "left":
                zumi.turn_left(360, 2)
            else:
                zumi.turn_right(360, 2)

        # 4) Emotion anzeigen, aber nicht stoppen:
        #    emotion_part ist z.B. "emotion: none" oder "emotion: zumi is happy today!"
        emo = emotion_part.split(":",1)[1].strip()
        if emo != "none":
            # vorhandenen Handler holen
            handler = qr_actions.get(emo, None)
            if handler:
                handler()

        # 5) Geradeaus über die weiße Fläche laufen lassen,
        #    bis die Linie wieder auftaucht
        zumi.forward(speed=10, duration=1)
        drive_straight_until_line()

        # 6) Timer-Reset, damit kein Geisterweg entsteht
        last_dir_change_time = time.time()

        return None

    # wenn kein Spin-Pattern, normaler Unknown-Log
    print("Unbekannter QR-Befehl:", text)
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
        zumi.control_motors(speed_l, speed_r)
    elif bottom_right < threshold:
        zumi.control_motors(1, 0)  # Slight right turn
    elif bottom_left < threshold:
        zumi.control_motors(0, 1)  # Slight left turn


def right_roundabout(num_rounds):
    print("right circle")
    zumi.forward(speed=10, duration=0.2)
    record_segment('R')
    zumi.turn_right(75)
    turns_taken = 1
    circled = 0
    print("Rounds to do:", num_rounds)
    while True:
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        threshold = 100
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=10, duration=0.1)
            if turns_taken % 4 == 0 and turns_taken != 0:
                turns_taken = 0
                print("Turns taken:", turns_taken)
                circled += 1
                print("Circled:", circled)
            else:
                record_segment('R')
                zumi.turn_right(75)
                turns_taken += 1
                print("Turns taken:", turns_taken)
        else:
            linefolower_ir(bottom_right, bottom_left, threshold)
        if (circled == num_rounds) and (bottom_right < threshold and bottom_left < threshold):
            print("Rounds completed:", circled)
            record_segment('L')
            zumi.turn_left(75)
            break


def left_roundabout(num_rounds):
    print("left circle")
    zumi.forward(speed=10, duration=0.2)
    record_segment('L')
    zumi.turn_left(75)
    turns_taken = 1
    circled = 0
    print("Rounds to do:", num_rounds)
    while True:
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        threshold = 100
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=15, duration=0.2)
            if turns_taken % 4 == 0 and turns_taken != 0:
                turns_taken = 0
                print("Turns taken:", turns_taken)
                circled += 1
                print("Circled:", circled)
            else:
                record_segment('L')
                zumi.turn_left(75)
                turns_taken += 1
                print("Turns taken:", turns_taken)
        else:
            linefolower_ir(bottom_right, bottom_left, threshold)
        if (circled == num_rounds) and (bottom_right < threshold and bottom_left < threshold):
            print("Rounds completed:", circled)
            record_segment('R')
            zumi.turn_right(75)
            break


def scan_qr():
    global last_qr_text
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
        last_qr_text = qr_result.strip().lower()
        return last_qr_text
    else:
        last_qr_text = None
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
        msg = "{} – No QR or Face detected".format(ts)
    print(msg)
    # CSV-Eintrag: Timestamp, Event „face_detected“, Gesamt-Anzahl
    csv_writer.writerow([ts, "face_detected", face_counter])
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
    if front_right < 40 and front_left < 40:
        # Segment beenden – mit record_segment (kein Turn)
        record_segment(None)

        object_counter += 1
        # print("IR vorne rechts:", front_right)
        # print("IR vorne links :", front_left)
        # print("Threshold-Wert:", threshold)
        zumi.stop()
        time.sleep(5)
        print("Objekt erkannt – versuche QR-Code zu lesen ...")
        print("Objekt Zähler:", object_counter)
        # CSV-Eintrag: Timestamp, Event „object_detected“, Gesamt-Anzahl
        ts2 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_writer.writerow([ts2, "object_detected", object_counter])

        qr_code = scan_qr()
        time.sleep(2)

        if qr_code:
            last_dir_change_time = time.time()
            cmd = qr_code.strip().lower()
            handler = qr_actions.get(cmd, cmd_unknown)
            result = handler()
            if result == "exit":
                last_dir_change_time = time.time()
                break
        else:
            # Kein QR → zuerst Gesichtserkennung oder Objekt zählen
            face_found = detect_and_log_face()
            # if not face_found:
            #     print("Gesicht nicht erkannt. Ich fahre weiter.")  
                

        # begin timeout for object‐clearing
        start_wait = time.time()
        MAX_WAIT   = 10  # seconds


        while True:
            ir_readings = zumi.get_all_IR_data()
            front_right = ir_readings[0]
            front_left = ir_readings[5]
            if front_right > 60 and front_left > 60:
                break
            if time.time() - start_wait > MAX_WAIT:
                print("⚠️ Timeout: Objekt bleibt zu lange!")
                break
            time.sleep(0.2)

        last_dir_change_time = time.time()
        continue

    # --- Linienverfolgung ---
    if bottom_right < threshold and bottom_left < threshold:
        zumi.reverse(speed=15, duration=0.2)
        zumi.turn_right(70)
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]
        if bottom_right < threshold or bottom_left < threshold:
            zumi.signal_left_on()
            record_segment('L')
            zumi.turn_left(140)
            time.sleep(0.3)
            zumi.signal_left_off()
        else:
            zumi.signal_right_on()
            record_segment('R')
            time.sleep(0.3)
            zumi.signal_right_off()
    elif bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(speed_l, speed_r)
    elif bottom_right < threshold:
        zumi.control_motors(1, 0)
    elif bottom_left < threshold:
        zumi.control_motors(0, 1)

# --- Ende Logging ---
csv_file.close()

# --- Ende Mapping-Log und Berechnung Manhattan-Distanz ---
# letztes Segment ohne folgende Kurve speichern
record_segment(None)

# Manhattan-Distanz berechnen (Fährt ca. 10 cm/s)
speed_cm_per_s = 10
h_dur = sum(duration for direction, duration, _ in movement_log
            if direction == 'horizontal')
v_dur = sum(duration for direction, duration, _ in movement_log
            if direction == 'vertical')
h_dist = h_dur * speed_cm_per_s
v_dist = v_dur * speed_cm_per_s
manhattan_dist = h_dist + v_dist

print(
    "Geschätzte Manhattan-Distanz: {:.2f} cm "
    "(horizontal: {:.2f} cm, vertikal: {:.2f} cm)"
    .format(manhattan_dist, h_dist, v_dist)
)

# Abschliessendes Log in CSV
with open("manhattan_distance.csv", "a", newline="") as md_file:
    md_writer = csv.writer(md_file)
    md_writer.writerow([datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                        round(manhattan_dist, 2)])

# --- Map-Plot aus movement_log erzeugen ---



# # --- Map-Plot aus movement_log (mit Turn-Odometry) ---
# x, y      = 0.0, 0.0
# heading   = 0.0        # 0° = +Y
# positions = [(x, y)]

# for direction, duration, turn in movement_log:
#     dist = duration * speed_cm_per_s
#     # Δx/Δy vom aktuellen Heading
#     dx = dist * math.sin(math.radians(heading))
#     dy = dist * math.cos(math.radians(heading))
#     x += dx; y += dy
#     positions.append((x, y))
#     # Heading um 90° drehen, wenn Kurve folgt
#     if turn == 'R':
#         heading = (heading + 90) % 360
#     elif turn == 'L':
#         heading = (heading - 90) % 360

# # Plot zeichen und speichern
# xs, ys = zip(*positions)
# plt.figure()
# plt.plot(xs, ys, '-o')
# plt.axis('equal')
# plt.title("Zumi Path Map")
# plt.xlabel("X [cm]"); plt.ylabel("Y [cm]")
# plt.grid(True)
# plt.savefig("zumi_map.png", dpi=150)
# print("Karte gespeichert als 'zumi_map.png'")

# --- Map-Plot aus movement_log (mit Turn-Odometry) ---
x, y      = 0.0, 0.0
heading   = 0.0        # 0° = +Y
positions = [(x, y)]

for direction, duration, turn in movement_log:
    dist = duration * speed_cm_per_s
    dx = dist * math.sin(math.radians(heading))
    dy = dist * math.cos(math.radians(heading))
    x += dx; y += dy
    positions.append((x, y))
    if turn == 'R':
        heading = (heading + 90) % 360
    elif turn == 'L':
        heading = (heading - 90) % 360

# Extrahiere und verschiebe so, dass min=0
xs = np.array([p[0] for p in positions])
ys = np.array([p[1] for p in positions])
xs -= xs.min()
ys -= ys.min()

# Plot zeichnen und speichern
plt.figure()
plt.plot(xs, ys, '-o')
plt.axis('equal')

# Achsenbegrenzung ab 0
plt.xlim(left=0)
plt.ylim(bottom=0)

plt.title("Zumi Pfad (nur positive Werte ab Start)")
plt.xlabel("X-Verschiebung vom Start [cm]")
plt.ylabel("Y-Verschiebung vom Start [cm]")
plt.grid(True)
plt.savefig("zumi_map.png", dpi=150)
print("Karte gespeichert als 'zumi_map.png'")
