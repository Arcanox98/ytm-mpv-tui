import json
import subprocess
import time
import os

class UeberzugLayer:
    def __init__(self):
        self.process = subprocess.Popen(
            ["ueberzugpp", "layer", "--output", "wayland"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )

    def draw(self, path, x, y, width, height):
        command = {
            "action": "add",
            "identifier": "cover",
            "path": path,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "scaler": "contain"
        }
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()

    def clear(self):
        command = {"action": "remove", "identifier": "cover"}
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()

    def stop(self):
        self.process.terminate()

if __name__ == "__main__":
    layer = UeberzugLayer()
    # Prueba rápida si existe alguna imagen en tu sistema
    test_img = "/home/ragnarok/Downloads/image.png"
    if os.path.exists(test_img):
        print(f"Dibujando {test_img}...")
        layer.draw(test_img, 5, 5, 20, 20)
        time.sleep(3)
    layer.stop()
