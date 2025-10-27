from google_play import GooglePlayEmulatorController
import numpy as np
from PIL import Image
import os
import time
from pathlib import Path


CONFIG = {
    "save_dir": str(Path(__file__).parent.parent / "data" / "training" / "images"),
    "save_rate": 1,  # in seconds
}


class Logger:
    def __init__(self):
        pass

    def log(self, message):
        print(message)

    def change_status(self, message):
        print(message)

    def show_temporary_action(self, message):
        print(message)


def save_numpy_image(screenshot_array):
    timestamp = get_timestamp()
    img = Image.fromarray(screenshot_array)
    os.makedirs(CONFIG["save_dir"], exist_ok=True)
    fp = os.path.join(CONFIG["save_dir"], f"screenshot_{timestamp}.png")
    print(fp)
    img.save(fp)

def get_timestamp():
    ts = int(time.time())
    return ts

def recorder_main():
    emulator = GooglePlayEmulatorController(Logger())
    emulator.start()
    input("Ready to record? Press Enter to continue...")

    while 1:
        image = emulator.screenshot()
        time.sleep(CONFIG["save_rate"])
        save_numpy_image(image)


if __name__ == "__main__":
    recorder_main()
