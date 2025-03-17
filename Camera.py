import picamera
import cv2
import numpy as np

camera = picamera.PiCamera()
camera.rotation = 180
camera.capture('out_normal.jpg')

image = cv2.imread('out_normal.jpg')
# Convert to grayscale
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
cv2.imwrite('out_gray.jpg', gray_image)

# Convert to HSV
hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
cv2.imwrite('out_hsv.jpg', hsv_image)

# Convert to Inverted
inverted_image = cv2.bitwise_not(image)
cv2.imwrite('out_inverted.jpg', inverted_image)