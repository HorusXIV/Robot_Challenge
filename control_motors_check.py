from zumi.zumi import Zumi
import time
zumi = Zumi()
zumi.control_motors(1, 15)
time.sleep(3)
zumi.stop()