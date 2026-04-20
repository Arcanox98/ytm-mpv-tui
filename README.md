# YTM-MPV-TUI

Un reproductor de YouTube Music para la terminal basado en Python, Textual y MPV.

## Características
- Interfaz TUI moderna y ligera.
- Control global mediante señales (ideal para Hyprland/Wayland).
- Integración con `playerctl`.

## Atajos de Teclado (Configuración Hyprland)
- `SUPER + F12`: Abrir/Cerrar reproductor (Scratchpad).
- `CTRL + ALT + Home`: Siguiente canción.
- `CTRL + ALT + Insert`: Canción anterior.
- `CTRL + ALT + PgUp/PgDn`: Control de volumen.

## Instalación
1. Clonar el repositorio.
2. Crear un entorno virtual: `python -m venv venv`.
3. Instalar dependencias: `pip install -r requirements.txt`.
4. Ejecutar: `python main.py`.
