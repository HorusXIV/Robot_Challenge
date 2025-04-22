from zumi.util.vision import Vision
from picamera import PiCamera
from picamera.array import PiRGBArray


camera = PiCamera()
camera.rotation = 180
camera.resolution = (320, 240)
camera.framerate = 30

vision = Vision()
raw_capture = PiRGBArray(camera, size=(320, 240))


camera.capture(raw_capture, format="bgr", use_video_port=True)
image = raw_capture.array

camera.close()
qr_code = vision.find_QR_code(image)
message = vision.get_QR_message(qr_code) # returns None if QR code was not detected
print(message)