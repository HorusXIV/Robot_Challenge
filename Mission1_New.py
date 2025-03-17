from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import os

zumi = Zumi()
screen = Screen()

start_time = time.time()
zumi.reset_gyro()
turns = 0
turn_detected = False

while True:
    ir_readings = zumi.get_all_IR_data()
    bottom_right = ir_readings[1]
    bottom_left = ir_readings[3]
    front_right = ir_readings[0]
    front_left = ir_readings[5]

    # Threshold for detecting black (190-200) vs grey (100-120)
    threshold = 150  # Adjust as needed

    if bottom_right < threshold and bottom_left < threshold:
        zumi.reverse(speed = 15, duration = 0.2)
        time.sleep(0.5)
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
        zumi.control_motors(5,18)
        if not turn_detected and (zumi.read_z_angle() > 40 or zumi.read_z_angle() < -40):
            print(turns, zumi.read_z_angle())
            zumi.reset_gyro()
            turns += 1
            turn_detected = True

    elif bottom_right < threshold:
        # Both sensors detect black → Go straight
        zumi.control_motors(20,0)
    
    elif bottom_left < threshold:
        # Left sensor on black, right on grey → Slight left turn
        zumi.control_motors(0,20)  # Left wheel slower

    if -40 < zumi.read_z_angle() < 40:
        turn_detected = False

    if front_right < 15 and front_left < 15:
        zumi.stop()
        break
        
# Record end time
end_time = time.time()

# Open and write to the CSV file
csv_filename = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter/zumi_runtime.csv"

with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow([start_time, end_time, turns])