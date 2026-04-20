import os
import requests
import tempfile
import base64
import sys

class UeberzugManager:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()

    def draw(self, url, x, y, width, height):
        if not url: return
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                # Codificar imagen en Base64 para el protocolo de Kitty
                img_data = base64.b64encode(response.content).decode('ascii')
                
                # Protocolo de Kitty: Escapes para cargar y colocar imagen
                # a=T (transferencia inmediata), t=d (datos base64)
                # q=2 (silencioso), f=100 (formato automático)
                # X, Y (celdas), W, H (celdas)
                sys.stdout.write(f"\033_Ga=T,t=d,f=100,x={x},y={y},w={width},h={height};{img_data}\033\\")
                sys.stdout.flush()
        except Exception:
            pass

    def clear(self):
        # Limpiar todas las imágenes de Kitty
        sys.stdout.write("\033_Ga=d\033\\")
        sys.stdout.flush()

    def stop(self):
        self.clear()
