@echo off
REM ============================================================================
REM  iniciar-proyecto.bat  --  Natillera (full-stack)
REM  1) Prepara backend (venv) y frontend (node_modules) si faltan.
REM  2) Crea la BD de demo (migra + siembra) la primera vez.
REM  3) Arranca BACKEND (uvicorn) y FRONTEND (vite) en ventanas separadas.
REM  4) Abre el navegador en la app.
REM
REM  Credenciales de demo:  admin@natillera.co  /  demo1234
REM
REM  Uso:
REM    iniciar-proyecto.bat              prepara y arranca todo
REM    iniciar-proyecto.bat --validar    corre el gate (ruff/mypy/tests) y arranca
REM    iniciar-proyecto.bat --solo-validar   solo corre el gate, no arranca
REM    iniciar-proyecto.bat --reseed     recrea la BD de demo desde cero
REM ============================================================================
setlocal enableextensions
cd /d "%~dp0"

set "RAIZ=%~dp0"
set "BACK=%RAIZ%backend"
set "FRONT=%RAIZ%frontend"
set "PY=%BACK%\.venv\Scripts\python.exe"
set "LINTIMPORTS=%BACK%\.venv\Scripts\lint-imports.exe"
set "DB=%BACK%\natillera_demo.db"
set "BACK_PORT=8000"
set "FRONT_PORT=5173"

set "VALIDAR=0"
set "ARRANCAR=1"
set "RESEED=0"
if /i "%~1"=="--validar"      set "VALIDAR=1"
if /i "%~1"=="--solo-validar" ( set "VALIDAR=1" & set "ARRANCAR=0" )
if /i "%~1"=="--reseed"       set "RESEED=1"

echo.
echo ============================================================
echo  NATILLERA  --  inicio local (full-stack)
echo ============================================================

REM --- 1) Backend: entorno virtual -------------------------------------------
if exist "%PY%" goto :venv_ok
echo [setup] Creando entorno virtual del backend e instalando dependencias...
pushd "%BACK%"
python -m venv .venv
if errorlevel 1 goto :error_venv
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error_deps
popd
:venv_ok

REM --- 2) Frontend: dependencias ---------------------------------------------
if exist "%FRONT%\node_modules" goto :npm_ok
echo [setup] Instalando dependencias del frontend (npm install)...
pushd "%FRONT%"
call npm install
if errorlevel 1 goto :error_npm
popd
:npm_ok

REM --- 3) Validacion opcional -------------------------------------------------
if "%VALIDAR%"=="0" goto :despues_validar
pushd "%BACK%"
set "ENTORNO=test"
echo.
echo [1/5] Ruff...      & "%PY%" -m ruff check app tests   & if errorlevel 1 goto :fallo
echo [2/5] Mypy...      & "%PY%" -m mypy app               & if errorlevel 1 goto :fallo
echo [3/5] Imports...   & "%LINTIMPORTS%"                  & if errorlevel 1 goto :fallo
echo [4/5] Anti-float...& "%PY%" scripts\guard_anti_float.py & if errorlevel 1 goto :fallo
echo [5/5] Tests...     & "%PY%" -m pytest -m "not mysql" -q & if errorlevel 1 goto :fallo
popd
echo  VALIDACION OK
:despues_validar

if "%ARRANCAR%"=="0" goto :solo_validar

REM --- 4) BD de demo (migrar + sembrar) --------------------------------------
set "ENTORNO=local"
set "DATABASE_URL=sqlite+pysqlite:///./natillera_demo.db"
set "LOG_JSON=false"
if "%RESEED%"=="1" if exist "%DB%" del /q "%DB%"
if exist "%DB%" goto :db_ok
echo.
echo [setup] Creando BD de demo (migraciones + datos)...
pushd "%BACK%"
"%PY%" -m alembic upgrade head
if errorlevel 1 goto :error_db
set "PYTHONPATH=%BACK%"
"%PY%" scripts\seed_demo.py
set "PYTHONPATH="
popd
:db_ok

REM --- 5) Arrancar backend y frontend en ventanas separadas ------------------
echo.
echo ============================================================
echo  Backend :  http://127.0.0.1:%BACK_PORT%/api/v1/docs
echo  Frontend:  http://localhost:%FRONT_PORT%
echo  Login   :  admin@natillera.co  /  demo1234
echo  (cierra las 2 ventanas nuevas para detener)
echo ============================================================
start "Natillera Backend" /D "%BACK%" cmd /k "%PY% -m uvicorn app.main:app --host 127.0.0.1 --port %BACK_PORT% --reload"

set "VITE_API_TARGET=http://127.0.0.1:%BACK_PORT%"
start "Natillera Frontend" /D "%FRONT%" cmd /k "npm run dev"

REM --- 6) Abrir el navegador (tras un respiro para que vite levante) ---------
timeout /t 7 /nobreak >nul
start "" http://localhost:%FRONT_PORT%
goto :ok

:solo_validar
echo [i] Modo --solo-validar: no se arranca nada.
goto :ok

:fallo
popd
echo.
echo ============================================================
echo  VALIDACION FALLIDA  --  no se arranca (usa sin --validar para saltarla)
echo ============================================================
exit /b 1

:error_venv
echo [ERROR] No se pudo crear el venv. Verifica que Python este instalado.
exit /b 1
:error_deps
echo [ERROR] Fallo la instalacion de dependencias del backend.
exit /b 1
:error_npm
echo [ERROR] Fallo npm install. Verifica que Node.js este instalado.
exit /b 1
:error_db
echo [ERROR] Fallaron las migraciones de la BD de demo.
exit /b 1

:ok
endlocal
exit /b 0
