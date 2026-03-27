import time
import os
import boto3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

s3 = boto3.client("s3")
BUCKET = os.environ["S3_BUCKET_NAME"]
WATCH_DIR = os.path.expanduser("~/Desktop")
                                                                                           
class ScreenshotHandler(FileSystemEventHandler):                                         
    def on_created(self, event):                                                         
        if event.is_directory:                                                           
            return                                                                     
        if event.src_path.lower().endswith((".png", ".jpg", ".jpeg")):
            filename = os.path.basename(event.src_path)
            if filename.startswith("Screenshot"):                                        
                time.sleep(1)
                date_folder = datetime.now().strftime("%Y-%m-%d")                        
                s3_key = f"{date_folder}/{filename}"                                   
                s3.upload_file(event.src_path, BUCKET, s3_key)                           
                print(f"Uploaded: {s3_key}")


if __name__ == "__main__":
    observer = Observer()
    observer.schedule(ScreenshotHandler(), WATCH_DIR, recursive=False)
    observer.start()
    print(f"Watching {WATCH_DIR} for screenshots...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
