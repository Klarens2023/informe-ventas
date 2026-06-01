@echo off
chcp 65001 > nul
echo ============================================
echo   ABAD - Informe de Ventas :: Instalacion
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Creando entorno virtual Python...
python -m venv venv
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual.
    echo Asegurate de tener Python 3.10 o superior instalado.
    pause
    exit /b 1
)

echo [2/3] Instalando dependencias...
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo [3/3] Creando archivo de configuracion...
if not exist .env (
    copy .env.example .env > nul
    echo Archivo .env creado. Configura tus credenciales en la app.
)

echo.
echo ============================================
echo   Instalacion completada exitosamente!
echo ============================================
echo.
echo Para iniciar la app:
echo   Doble clic en "Iniciar.vbs"
echo.
echo La primera vez que abras la app, ve a
echo "Importar Data" para configurar Supabase.
echo ============================================
pause
