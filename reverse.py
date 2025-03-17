from zumi.zumi import Zumi
from zumi.util.screen import Screen
import csv
import time
import os

zumi = Zumi()
screen = Screen()

zumi.reverse(speed = 10, duration = 0.3)
time.sleep(1)
zumi.reverse(speed = 15, duration = 0.2)
