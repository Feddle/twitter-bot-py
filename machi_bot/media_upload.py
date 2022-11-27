"""Handles media upload in chunks"""

import os
import sys
import time
import requests
from requests_oauthlib import OAuth1 as oauth_helper
from .oauth import OAuth1

MEDIA_ENDPOINT_URL = "https://upload.twitter.com/1.1/media/upload.json"

oauth = OAuth1()
oauth.handle_oauth1()

auth_session = oauth_helper(
    client_key=oauth.twitter_api_key,
    client_secret=oauth.twitter_api_secret,
    resource_owner_key=oauth.oauth_token,
    resource_owner_secret=oauth.oauth_token_secret
)

class MediaTweet:
    """Media uploading"""

    def __init__(self, file_name):
        """
        Defines video tweet properties
        """
        self.video_filename = file_name
        self.total_bytes = os.path.getsize(self.video_filename)
        self.media_id = None
        self.processing_info = None


    def upload_init(self):
        """
        Initializes Upload
        """
        print("INIT")

        request_data = {
        "command": "INIT",
        "media_type": "video/mp4",
        "total_bytes": self.total_bytes,
        "media_category": "tweet_video"
        }

        req = requests.post(
            url=MEDIA_ENDPOINT_URL,
            data=request_data,
            auth=auth_session,
            timeout=10
        )
        media_id = req.json()["media_id"]

        self.media_id = str(media_id)

        print(f"Media ID: {str(media_id)}")

    def upload_append(self):
        """
        Uploads media in chunks and appends to chunks uploaded
        """
        segment_id = 0
        bytes_sent = 0
        with open(self.video_filename, "rb") as file:
            while bytes_sent < self.total_bytes:
                # Chunk must be < 5MB
                chunk = file.read(4*1024*1024)

                print("APPEND")

                request_data = {
                "command": "APPEND",
                "media_id": self.media_id,
                "segment_index": segment_id
                }

                files = {
                "media": chunk
                }

                req = requests.post(
                    url=MEDIA_ENDPOINT_URL,
                    data=request_data,
                    files=files,
                    auth=auth_session,
                    timeout=10
                )

                if req.status_code < 200 or req.status_code > 299:
                    print(req.status_code)
                    print(req.text)
                    sys.exit(0)

                segment_id = segment_id + 1
                bytes_sent = file.tell()

                print(f"{str(bytes_sent)} of {str(self.total_bytes)} bytes uploaded")

        print("Upload chunks complete.")


    def upload_finalize(self):
        """
        Finalizes uploads and starts video processing
        """
        print("FINALIZE")

        request_data = {
        "command": "FINALIZE",
        "media_id": self.media_id
        }

        req = requests.post(
            url=MEDIA_ENDPOINT_URL,
            data=request_data,
            auth=auth_session,
            timeout=10
        )
        print(req.json())

        self.processing_info = req.json().get("processing_info", None)
        self.check_status()


    def check_status(self):
        """
        Checks video processing status
        """
        if self.processing_info is None:
            return

        state = self.processing_info["state"]

        print(f"Media processing status is {state}")

        if state == "succeeded":
            return

        if state == "failed":
            sys.exit(0)

        check_after_secs = self.processing_info["check_after_secs"]

        print(f"Checking after {str(check_after_secs)} seconds")
        time.sleep(check_after_secs)

        print("STATUS")

        request_params = {
            "command": "STATUS",
            "media_id": self.media_id
        }

        req = requests.get(
            url=MEDIA_ENDPOINT_URL,
            params=request_params,
            auth=auth_session,
            timeout=10
        )

        self.processing_info = req.json().get("processing_info", None)
        print(req.json())
        self.check_status()

def upload_media(file_path) -> str:
    """Uploads file found in the path argument

    Args:
        file_path (str): Path to file

    Returns:
        str: Uploaded file media id
    """
    tweet = MediaTweet(file_path)
    tweet.upload_init()
    tweet.upload_append()
    tweet.upload_finalize()
    return tweet.media_id
