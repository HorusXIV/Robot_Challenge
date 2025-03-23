from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import os
import cv2
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import datetime

from utility import upload_submission

def linefolower(bottom_right, bottom_left, threshold):
        if bottom_right > threshold and bottom_left > threshold:
            zumi.control_motors(1, 15)
        
        elif bottom_right < threshold:
            zumi.control_motors(5, 0)  # Slight right turn
        
        elif bottom_left < threshold:
            zumi.control_motors(0, 5)  # Slight left turn

def right_roundabout(obj_det):
    zumi.forward(speed=10, duration=0.2)
    zumi.turn_right(75)
    turns_taken = 1
    circled = 0

    while True:
        print(turns_taken)


        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]

        # Threshold for detecting black (190-200) vs grey (100-120)
        threshold = 100
        
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=10, duration=0.2)
            if turns_taken % 4 == 0:
                turns_taken = 0
                circled +=1
            else:
                zumi.turn_right(75)
                turns_taken += 1
        else:
            linefolower(bottom_right,bottom_left, threshold)

        if (circled == obj_det) and ((bottom_right < threshold )and (bottom_left < threshold)):
            print(circled)
            break
    


def left_roundabout(obj_det):
    zumi.turn(180)
    turns_taken = 1
    circled = 0
    left_roundabout_bool = False
    

    while True:
        print(turns_taken)

        ir_readings = zumi.get_all_IR_data()
        bottom_right = ir_readings[1]
        bottom_left = ir_readings[3]

        # Threshold for detecting black (190-200) vs grey (100-120)
        threshold = 100

        if turns_taken % 4 == 0:
                turns_taken = 0
                circled += 1

        if circled == obj_det:
            print(circled)
            print(turns_taken)
            break
        
        if bottom_right < threshold and bottom_left < threshold:
            zumi.reverse(speed=10, duration=0.2)
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
                    linefolower(bottom_right, bottom_left, threshold)
                zumi.turn_left(75)
                turns_taken += 1
                ir_readings = zumi.get_all_IR_data()
                bottom_right = ir_readings[1]
                bottom_left = ir_readings[3]
                if bottom_left < threshold:
                    zumi.forward(speed=10, duration=0.5)
            else:
                linefolower(bottom_right, bottom_left, threshold)

        




# Initialize Zumi and Screen
zumi = Zumi()
left_roundabout(2)
# zumi.turn_left(80)
zumi.stop()