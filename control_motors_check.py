from zumi.zumi import Zumi
import time
zumi = Zumi()
zumi.control_motors(10, 8)
time.sleep(3)
zumi.stop()