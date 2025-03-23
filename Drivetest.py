from zumi.zumi import Zumi
import time

zumi = Zumi()

# zumi.reset_drive()

# #Zumi will take 500 samples/readings
# zumi.mpu.calibrate_MPU(count=500)

# #this is the order the offsets will be printed
# print("angular speed rad/sec Gx,Gy,Gz")
# print("linear acceleration   Ax,Ay,Az")

# #print the offsets of each Axis
# zumi.mpu.print_offsets()

zumi.control_motors(1, 5)
time.sleep(3)
zumi.control_motors(0, 0)
