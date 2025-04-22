from zumi.zumi import Zumi
import time

# Initialize Zumi
zumi = Zumi()



# while True:
#     ir_readings = zumi.get_all_IR_data()
#     front_right = ir_readings[0]
#     bottom_right = ir_readings[1]
#     bottom_left  = ir_readings[3]
#     front_left   = ir_readings[5]
#     print(bottom_left, bottom_right)
#     time.sleep(2)

zumi.forward_step(-1, -1)