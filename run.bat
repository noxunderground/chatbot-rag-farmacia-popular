@echo off
setlocal

REM Configurações
set "HOST=0.0.0.0"
set "PORT=8000"
set "PYTHON=python"
set NGROK_AUTHTOKEN="35FzWlCFNOs8tP2iNEawVZGh2qm_oJkfRUYNykiLrfdFbQrB"

REM Opcional: defina NGROK_AUTHTOKEN para configurar automaticamente
if not "%NGROK_AUTHTOKEN%"=="" (
  ngrok config add-authtoken %NGROK_AUTHTOKEN%
)

REM Ativa venv se existir
if exist "venv\Scripts\activate.bat" (
  call "venv\Scripts\activate.bat"
)

REM Sobe o servidor Flask (app.py) em uma janela separada
start "PFPB Chat Server" cmd /c "%PYTHON% app.py"

REM Aguarda alguns segundos para o servidor iniciar
timeout /t 5 >nul

REM Abre túnel ngrok para a porta configurada
start "Ngrok Tunnel" cmd /c "ngrok http %PORT%"

echo.
echo Servidor iniciado em http://localhost:%PORT% (ngrok abrirá a URL pública na janela)
echo Pressione CTRL+C para encerrar este terminal.

REM Mantém esta janela aberta
pause
