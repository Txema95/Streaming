import subprocess
import time
import os
import sys
def main():
    # 1. Lanzar el Backend (FastAPI)
    backend = subprocess.Popen(["uvicorn", "src.api.main_api:app", "--reload"])
    
    # 2. Esperar un par de segundos a que el backend suba
    time.sleep(2)
    
    # 3. Lanzar el Frontend (Streamlit)
    frontend = subprocess.Popen(["streamlit", "run", "src/frontend/app_ui.py"])

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()
        
def main_debug():
    # Obtenemos la ruta raíz del proyecto
    ruta_raiz = os.getcwd()
    
    # Preparamos el entorno para que los subprocesos vean la carpeta 'src'
    env_config = os.environ.copy()
    env_config["PYTHONPATH"] = os.path.join(ruta_raiz, "src")

    print("🚀 Iniciando Debug de Backend...")
    # Usamos sys.executable para asegurar que usen el MISMO venv que el main
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main_api:app", "--reload"],
        env=env_config
    )
    
    time.sleep(2)
    
    print("🎨 Iniciando Debug de Frontend...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/frontend/app_ui.py"],
        env=env_config
    )

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    #main()
    main_debug()
