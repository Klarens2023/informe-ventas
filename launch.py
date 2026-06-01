"""
Lanzador silencioso de la app. Ejecutar con: pythonw.exe launch.py
"""
import subprocess
import sys
import os
import time
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# Usa el Python del venv si existe
venv_python = os.path.join(BASE_DIR, 'venv', 'Scripts', 'python.exe')
python = venv_python if os.path.exists(venv_python) else sys.executable

proc = subprocess.Popen(
    [python, '-m', 'streamlit', 'run', 'app.py',
     '--server.port', '8501',
     '--server.headless', 'true',
     '--browser.gatherUsageStats', 'false'],
    cwd=BASE_DIR,
    creationflags=0x08000000,   # CREATE_NO_WINDOW (Windows)
)

time.sleep(3)
webbrowser.open('http://localhost:8501')
proc.wait()
