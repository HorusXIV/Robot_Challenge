import git
import os
from datetime import datetime
import time
from picamera.array import PiRGBArray
from picamera import PiCamera
from zumi.util.vision import Vision
import cv2
import numpy as np

REPO_PATH = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter"
SUBMISSION_FOLDER = os.path.join(REPO_PATH, "submissions")
TEAM_NAME = "Zumi3843"
FILE_NAME = "result.txt"
COMMIT_MESSAGE = "Submission by " + TEAM_NAME + " - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def upload_submission():
    try:
        repo = git.Repo(REPO_PATH)

        os.makedirs(SUBMISSION_FOLDER, exist_ok=True)

        team_file_path = os.path.join(SUBMISSION_FOLDER, "{}_{}".format(TEAM_NAME, FILE_NAME))
        # Add and commit the file
        repo.index.add([team_file_path])
        repo.index.commit(COMMIT_MESSAGE)
        # Push changes to GitHub
        origin = repo.remote(name='origin')
        origin.push()
        print("✅ {} successfully uploaded submission!".format(TEAM_NAME))
    except Exception as e:
        print("❌ Error: {}".format(e))

# --- Logging Function ---
def log_event(log_file_path, event_type, details=""):
    """Write an event to the log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, "a") as log_file:
        log_file.write("[" + str(timestamp) + "] "+ str(event_type) +" : " + str(details) + "\n")