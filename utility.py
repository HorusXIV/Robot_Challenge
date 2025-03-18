import git
import os
from datetime import datetime

REPO_PATH = "/home/pi/Dashboard/user/RobotChallenge/My_Projects/Jupyter"
SUBMISSION_FOLDER = os.path.join(REPO_PATH, "submissions")
TEAM_NAME = "DaLuYaZe"
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