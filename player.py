import json
import socket
import subprocess
import os
import time
import threading

class Player:
    def __init__(self, on_progress=None, on_status_change=None):
        self.ipc_path = "/tmp/ytm-mpv-socket"
        self.on_progress = on_progress
        self.on_status_change = on_status_change
        self.mpv_process = None
        self._start_mpv()
        
        self.listener_thread = threading.Thread(target=self._listen_events, daemon=True)
        self.listener_thread.start()

    def _start_mpv(self):
        if os.path.exists(self.ipc_path):
            os.remove(self.ipc_path)
            
        env = os.environ.copy()
        env["LC_NUMERIC"] = "C"
        
        self.mpv_process = subprocess.Popen(
            [
                "mpv", "--idle", "--no-video", 
                f"--input-ipc-server={self.ipc_path}",
                "--volume=100",
                # Esto asegura que MPV responda a playerctl
                "--script-opts=mpris-enable=yes" 
            ],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        
        for _ in range(20):
            if os.path.exists(self.ipc_path): break
            time.sleep(0.1)

    def _send_command(self, *args):
        if not os.path.exists(self.ipc_path): return None
        try:
            command = {"command": list(args)}
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(self.ipc_path)
                s.sendall(json.dumps(command).encode() + b"\n")
                response = s.recv(4096)
                return json.loads(response.decode()) if response else None
        except Exception: return None

    def _listen_events(self):
        while True:
            try:
                if not os.path.exists(self.ipc_path):
                    time.sleep(1)
                    continue
                
                # Obtener info de reproducción
                pos = self._send_command("get_property", "time-pos")
                dur = self._send_command("get_property", "duration")
                vol = self._send_command("get_property", "volume")
                idle = self._send_command("get_property", "idle-active")

                if self.on_progress and pos and dur and pos.get("data") is not None:
                    self.on_progress(pos["data"], dur["data"])
                
                if self.on_status_change:
                    volume = vol.get("data", 100) if vol else 100
                    is_idle = idle.get("data", False) if idle else False
                    self.on_status_change(volume, is_idle)

                time.sleep(0.5) # Polleo más rápido para mayor respuesta
            except Exception:
                time.sleep(1)

    def play(self, video_id):
        url = f"https://www.youtube.com/watch?v={video_id}"
        self._send_command("loadfile", url, "replace")

    def toggle_pause(self):
        res = self._send_command("get_property", "pause")
        if res and "data" in res:
            self._send_command("set_property", "pause", not res["data"])

    def set_volume(self, value):
        self._send_command("set_property", "volume", max(0, min(100, value)))

    def stop(self):
        if self.mpv_process: self.mpv_process.terminate()
        if os.path.exists(self.ipc_path): os.remove(self.ipc_path)
