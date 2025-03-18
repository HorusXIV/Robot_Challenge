from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import os

zumi = Zumi()
screen = Screen()

# zumi.control_motors(5, 20)
# time.sleep(2)
# zumi.stop()

for i in range(0,100):
    ir_readings = zumi.get_all_IR_data()
    bottom_right = ir_readings[1]
    bottom_left = ir_readings[3]
    
    message = "    IR readings        "
    message = message + str(bottom_right) + ", " + str(bottom_left)
    screen.draw_text(message)
    time.sleep(0.1)
screen.draw_text_center("Done!")