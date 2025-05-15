from zumi.zumi import Zumi
import time

zumi = Zumi()

try:
    print("Starte IR-Test (Front Right = Index 0, Front Left = Index 5).")
    while True:
        ir = zumi.get_all_IR_data()
        front_right = ir[0]
        front_left = ir[5]
        print("Front Right:", front_right, " Front Left:", front_left)
        time.sleep(0.5)
except KeyboardInterrupt:
    print("IR-Test beendet.")
