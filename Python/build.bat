@echo off
REM ===========================================================================
REM  build.bat — compile the Diocese Certificate Manager with Nuitka (standalone)
REM
REM  Prerequisites (one time):
REM    * Python 3.8.10 (64-bit)
REM    * Visual Studio 2019 Build Tools, "Desktop development with C++" workload
REM    * A virtual env with requirements installed:
REM        py -3.8 -m venv venv
REM        venv\Scripts\activate
REM        pip install -r requirements.txt
REM
REM  Output:  dist\main.dist\   (the whole folder is the portable app)
REM  Run:     dist\main.dist\main.exe
REM
REM  NOTE: We use --standalone (a folder), NOT --onefile. The folder build is
REM        flagged far less often by antivirus than a self-extracting onefile
REM        stub. Do NOT add UPX or any packer.
REM ===========================================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  Building Diocese Certificate Manager...
echo ============================================
echo.

python -m nuitka ^
  --standalone ^
  --assume-yes-for-downloads ^
  --enable-plugin=tk-inter ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=assets\app.ico ^
  --include-package-data=customtkinter ^
  --include-data-dir=assets=assets ^
  --company-name="Diocese of Madurai Ramnad CSI" ^
  --product-name="Diocese Certificate Manager" ^
  --file-version=1.0.0.0 ^
  --product-version=1.0.0.0 ^
  --file-description="Certificate data entry and printing" ^
  --copyright="Diocese of Madurai Ramnad CSI" ^
  --output-dir=dist ^
  main.py

echo.
if errorlevel 1 (
  echo BUILD FAILED. See the messages above.
) else (
  echo BUILD OK -^> dist\main.dist\main.exe
)
echo.

REM ---------------------------------------------------------------------------
REM  Why each flag matters:
REM    --enable-plugin=tk-inter        bundle Tcl/Tk correctly (required)
REM    --include-package-data=customtkinter   ship CustomTkinter theme JSON/assets (required)
REM    --include-data-dir=assets=assets       ship our logo.png / app.ico next to the exe
REM    --windows-console-mode=disable  no console window for a GUI app
REM    --windows-icon-from-ico         taskbar / explorer icon
REM    --company/product/file/...      embed version metadata (lowers AV suspicion)
REM ---------------------------------------------------------------------------

endlocal
