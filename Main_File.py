from zumi.zumi import Zumi
from zumi.util.screen import Screen
from zumi.protocol import Note
import csv
import time
from datetime import datetime
import os
import numpy as np
import matplotlib.pyplot as plt
from picamera.array import PiRGBArray
from picamera import PiCamera
from zumi.util.vision import Vision  # Built-in Vision module
from utility import upload_submission, log_event
import cv2  # for face‐box drawing & saving
import math
# from zumi.personality import Personality

# Initialize Zumi, Screen and Vision
zumi = Zumi()
screen = Screen()
vision = Vision()
# personality = Personality(zumi, screen)

zumi.reset_gyro()

# Zähler für entfernte Objekte
object_counter = 0
face_counter   = 0

# Control Motors Variablen
speed_l = 1
speed_r = 15

last_qr_text = None

# Text file logging preparation
log_file_path = "submissions/Zumi3843_result.txt"
# Create directories if they don't exist
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

# Initialize log file and write start time
with open(log_file_path, "w") as log_file:
    log_file.write("=== ZUMI ROBOT MISSION LOG ===\n")
    start_time = datetime.now()
    log_file.write("Mission Start: "+ start_time.strftime('%Y-%m-%d %H:%M:%S') + "\n\n")

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
    # Log the turn
    if next_turn:
        log_event(log_file_path,"TURN", "Direction: " + str(next_turn) + ", Duration in " + str(current_direction) + ": " + "{:.2f}".format(duration) + "s")
    # Toggle Achse
    current_direction = 'horizontal' if current_direction=='vertical' else 'vertical'
    last_dir_change_time = now

# Back on track Mission
def drive_straight_until_line():
    """
    Fahre geradeaus über eine weisse Fläche so lange,
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

# — QR-Command-Handler — 
def cmd_turn_right():
    print("QR ACTION:", " turn right")
    log_event(log_file_path,"QR ACTION", "turn right")
    zumi.forward(15, 0.3)

def cmd_turn_left():
    print("QR ACTION:", " turn left")
    log_event(log_file_path,"QR ACTION", "turn left")
    zumi.turn_left(90)

def cmd_left_circle():
    laps = object_counter - face_counter
    print("QR ACTION:", " left circle with " + str(laps) + " lap(s)")
    log_event(log_file_path,"QR ACTION", "left circle with " + str(laps) + " lap(s)")
    if laps > 0:
        left_roundabout(laps)

def cmd_right_circle():
    laps = object_counter - face_counter
    print("QR ACTION: right circle with " + str(laps) + " lap(s)")
    log_event(log_file_path,"QR ACTION", "right circle with " + str(laps) + " lap(s)")
    
    if laps > 0:
        right_roundabout(laps)
    global last_dir_change_time
    last_dir_change_time = time.time()

def cmd_happy_and_exit(log_it=True):
    print("QR ACTION: happy emotion and exit")
    if log_it:
        log_event(log_file_path,"QR ACTION", "happy emotion and exit")
    screen.happy()
    zumi.stop()
    return "exit"

def cmd_angry_and_exit(log_it=True):
    print("QR ACTION: angry emotion and exit")
    if log_it:
        log_event(log_file_path,"QR ACTION", "angry emotion and exit")
    screen.angry()
    zumi.stop()
    return "exit"

def cmd_celebrate_and_exit(log_it=True):
    print("QR ACTION: celebrate emotion and exit")
    if log_it:
        log_event(log_file_path,"QR ACTION", "celebrate emotion and exit")
    # personality.celebrate() # Uncomment if using Personality
    if hasattr(screen, 'celebrate'):
        screen.celebrate()
    else:
        screen.happy()
    return "exit"

def cmd_stop():
    print("QR ACTION: stop command")
    log_event(log_file_path,"QR ACTION", "stop command")
    zumi.stop()
    time.sleep(3)
    scan_qr()
    return "exit"


def cmd_unknown():
    global last_dir_change_time

    text = last_qr_text or ""
    print("QR ACTION", "Processing complex command: " + text + "")
    """
    Wenn last_qr_text ein 'Nx 360° left|right, emotion: ...' enthält,
    dann hier spin + optional Emotion + Geradeaus bis Linie. Sonst nur print.
    """
    
    if "360" in text:
        log_event(log_file_path,"QR ACTION", "Processing complex command: " + text + "")
        # Split am Komma: ['1x 360° left', ' emotion: none']
        parts = [p.strip() for p in text.split(",", 1)]
        spin_part = parts[0]            # z.B. "2x 360° right"
        emotion_part = parts[1] if len(parts) > 1 else "emotion: none"

        # Count und Richtung aus spin_part ziehen
        count = int(spin_part.split("x",1)[0])
        direction = "left" if "left" in spin_part else "right"

        log_event(log_file_path,"SPINNING TRICK", "Starting Spinning Trick")

        zumi.forward(speed=10, duration=0.4)

        # Spins ausführen
        for _ in range(count):
            if direction == "left":
                zumi.turn_left(360, 2)
            else:
                zumi.turn_right(360, 2)
        
        log_event(log_file_path,"SPINNING TRICK", "Number of Spins: " + str(count))

        # Emotion anzeigen, aber nicht stoppen
        emo = emotion_part.split(":",1)[1].strip()
        if emo != "none":
            # vorhandenen Handler holen
            handler = qr_actions.get(emo, None)
            if handler:
                handler(log_it=False)

        log_event(log_file_path,"SPINNING TRICK", "Emotion to Display: " + str(emo))

        # Geradeaus über die weisse Fläche laufen lassen, bis die Linie wieder auftaucht
        zumi.forward(speed=10, duration=1)
        drive_straight_until_line()
        
        log_event(log_file_path,"SPINNING TRICK", "Ending Spinning Trick")
        # Timer-Reset, damit kein Geisterweg auf Plot entsteht
        last_dir_change_time = time.time()

        return None

    # wenn kein Spin-Pattern, normaler Unknown-Log
    log_event(log_file_path,"QR ACTION", "Unknown QR command: " + text + "")
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
    log_event(log_file_path,"ROUNDABOUT", "Entering right roundabout with " + str(num_rounds) + " round(s)")
    log_event(log_file_path,"ROUNDABOUT", "z-angle: " + str(zumi.read_z_angle()))
    zumi.forward(speed=10, duration=0.4)
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
                circled += 1
                log_event(log_file_path,"ROUNDABOUT", "Completed " + str(circled) + " of " + str(num_rounds) + " circles")
            else:
                log_event(log_file_path,"ROUNDABOUT", "z-angle: " + str(zumi.read_z_angle()))
                record_segment('R')
                zumi.turn_right(75)
                
                turns_taken += 1
        else:
            linefolower_ir(bottom_right, bottom_left, threshold)
        if (circled == num_rounds) and (bottom_right < threshold and bottom_left < threshold):
            print("Rounds completed:", circled)
            record_segment('L')
            zumi.turn_left(75)
            log_event(log_file_path,"ROUNDABOUT", "Exiting right roundabout after " + str(circled) + " round(s)")
            break


def left_roundabout(num_rounds):
    log_event(log_file_path,"ROUNDABOUT", "Entering left roundabout with " + str(num_rounds) + " rounds")
    print("left circle")
    zumi.forward(speed=10, duration=0.4)
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
                log_event(log_file_path,"ROUNDABOUT", "Completed " + str(circled) + " of " + str(num_rounds) + " circles")
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
            log_event(log_file_path,"ROUNDABOUT", "Exiting left roundabout after "+ str(circled) +"  rounds")
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
        log_event(log_file_path,"QR DETECTED", "'" + str(last_qr_text) + "'")
        print("QR detected. Action: {}".format(last_qr_text))
        return last_qr_text
    else:
        print("No QR detected, searching for Face...")
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
    loc   = vision.find_face(frame, scale_factor=1.05, min_neighbors=8, min_size=(40,40))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if loc:
        x,y,w,h = loc
        cv2.rectangle(frame, (x,y), (x+w,y+h), (255,0,0), 2)
        fname = "submissions/faces/face_{}.png".format(ts)
        cv2.imwrite(fname, frame)
        face_counter += 1
        log_event(log_file_path,"FACE DETECTED", "Total faces so far: " + str(face_counter) + "")

        # Gesicht begrüssen
        screen.clear_display()
        screen.draw_text_center("Hello Face!", font_size=15)
        time.sleep(2)
        screen.clear_display()

        msg = "{} – Face detected! Total faces: {}".format(ts, face_counter)
    else:
        msg = "{} – No QR or Face detected".format(ts)
        log_event(log_file_path,"DETECTION ATTEMPT", "No QR or Face detected")
    print(msg)
    return True if loc else False

# --- Main Loop ---
log_event(log_file_path,"MISSION", "Starting main loop")
while True:
    ir_readings = zumi.get_all_IR_data()
    bottom_right = ir_readings[1]
    bottom_left = ir_readings[3]
    front_right = ir_readings[0]
    front_left = ir_readings[5]
    threshold = 100

    # Wenn etwas im Weg ist (IR-Werte tief)
    if front_right < 40 and front_left < 40:
        # Segment beenden mit record_segment (kein Turn)
        record_segment(None)

        zumi.stop()

        object_detect_time = datetime.now()
        log_event(log_file_path,"OBJECT DETECTED", "Searching for QR or Face")
        
        zumi.brake_lights_on()
        zumi.play_note(Note.G5, 200)
        time.sleep(0.05)
        # zweiter Piepton
        zumi.play_note(Note.C6, 200)

        screen.draw_text_center('Object detected!',font_size=15)
        time.sleep(2)
        screen.happy()

        log_event(log_file_path,"DISPLAY", "Displaying 'Object detected!' message")
        log_event(log_file_path,"DISPLAY", "Displaying Happy emotion")
        print("Object detected – trying to detect QR-Code...")

        time.sleep(2)

        # Licht und Screen zurücksetzen
        zumi.brake_lights_off()
        screen.clear_display()

        time.sleep(5)

        qr_code = scan_qr()
        time.sleep(2)

        if qr_code:
            last_dir_change_time = time.time()
            cmd = qr_code.strip().lower()
            handler = qr_actions.get(cmd, cmd_unknown)
            result = handler()
            if result == "exit":
                last_dir_change_time = time.time()
                log_event(log_file_path,"MISSION", "Exiting main loop due to QR command")
                break
        else:
            # Kein QR -> zuerst Gesichtserkennung versuchen, sonst Objekt zählen
            face_found = detect_and_log_face()
            if not face_found:
                object_counter += 1
                log_event(log_file_path,"OBJECT COUNTER", object_counter)
                print("No QR or Face detected. object_counter:", object_counter)  
                
        # Log object interaction duration
        object_duration = (datetime.now() - object_detect_time).total_seconds()
        log_event(log_file_path,"OBJECT INTERACTION", "Duration: " + "{:.2f}".format(object_duration) + "s")

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
                log_event(log_file_path,"WARNING", "Timeout: Object remained too long")
                print("⚠️ Timeout: Objekt bleibt zu lange!")
                break
            time.sleep(0.2)

        last_dir_change_time = time.time()
        continue

    # --- Kurvenlogik / Linefollower ---
    if bottom_right < threshold and bottom_left < threshold:
        zumi.reverse(speed=15, duration=0.2)
        zumi.turn_right(75)
        zumi.forward(speed=10, duration=0.4)
        
        # Noch einmal IR auslesen, um zu prüfen, ob Linie direkt vorhanden
        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]

        if bottom_right < threshold or bottom_left < threshold:
            zumi.signal_left_on()
            record_segment('L')
            zumi.turn_left(150)
            time.sleep(0.3)
            zumi.signal_left_off()
        else:
            zumi.signal_right_on()
            record_segment('R')
            time.sleep(0.3)
            zumi.signal_right_off()

    else:
        linefolower_ir(bottom_right, bottom_left, threshold)

# --- Ende Logging ---
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

manhattan_result = (
    "Estimated Manhattan distance: {:.2f} units "
    "(horizontally: {:.2f} units, vertically: {:.2f} units)"
    .format(manhattan_dist, h_dist, v_dist)
)
print(manhattan_result)

# Abschliessendes Log in CSV (keeping this part for backward compatibility)
with open("manhattan_distance.csv", "a", newline="") as md_file:
    md_writer = csv.writer(md_file)
    md_writer.writerow([datetime.now().strftime("%Y%m%d_%H%M%S"),
                        round((manhattan_dist), 2)])

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

plt.title("Zumi Map")
plt.xlabel("X-shift from start [units]")
plt.ylabel("Y-shift from start [units]")
plt.grid(True)
plt.savefig("submissions/zumi_map.png", dpi=150)
log_event(log_file_path,"MAP GENERATED", "Map saved as 'zumi_map.png'")
print("Map saved as 'zumi_map.png'")

# Final summary in log file
with open(log_file_path, "a") as log_file:
    end_time = datetime.now()
    mission_duration_sec = (end_time - start_time).total_seconds()
    minutes = int(mission_duration_sec // 60)
    seconds = int(mission_duration_sec % 60)
    
    log_file.write("\n=== MISSION SUMMARY ===\n")
    log_file.write("Mission End: " + str(end_time.strftime('%Y-%m-%d %H:%M:%S')) + "\n")
    log_file.write("Mission Duration: " + str(minutes) + " minutes " + str(seconds) + " seconds" + "\n\n")
    
    log_file.write("--- OBJECT STATISTICS ---\n")
    log_file.write("Total Objects Detected: " + str(object_counter) + "\n")
    log_file.write("Total Faces Detected: " + str(face_counter) + "\n\n")
    
    log_file.write("--- PATH STATISTICS ---\n")
    log_file.write("Total Turns: " + str(len([t for _, _, t in movement_log if t is not None])) + "\n")
    log_file.write("Horizontal Distance: " + "{:.2f}".format(h_dist) + " units\n")
    log_file.write("Vertical Distance: " + "{:.2f}".format(v_dist) + " units\n")
    log_file.write("Manhattan Distance: " + "{:.2f}".format(manhattan_dist) + " units\n")

upload_submission()