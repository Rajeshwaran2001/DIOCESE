@echo off
REM ===========================================================================
REM  Build script for Diocese Certificate Manager (Windows)
REM
REM  Requirements (one-time):
REM    1. Go 1.20.x  -> https://go.dev/dl/  (the LAST Go that supports Win7/8/8.1)
REM    2. goversioninfo:
REM         go install github.com/josephspurrier/goversioninfo/cmd/goversioninfo@v1.4.0
REM       (this puts goversioninfo.exe in %USERPROFILE%\go\bin — make sure that
REM        folder is on your PATH)
REM
REM  Output: DioceseCerts.exe in this folder (single file, no DLLs needed).
REM ===========================================================================

setlocal

echo.
echo [1/3] Embedding icon + manifest + version info (resource.syso)...
REM The .syso must live next to the main package (cmd\diocesecerts) so the Go
REM linker picks it up. Paths inside versioninfo.json are relative to this folder.
goversioninfo -64 -o cmd\diocesecerts\resource.syso resource\versioninfo.json
if errorlevel 1 (
    echo.
    echo  ERROR: goversioninfo failed. Is it installed and on your PATH?
    echo         go install github.com/josephspurrier/goversioninfo/cmd/goversioninfo@v1.4.0
    exit /b 1
)

echo [2/3] Building DioceseCerts.exe (pure Go, no CGO, no packer)...
set CGO_ENABLED=0
set GOOS=windows
set GOARCH=amd64
REM -H windowsgui = GUI subsystem (no stray console window pops up behind the app).
go build -ldflags "-s -w -H windowsgui" -o DioceseCerts.exe .\cmd\diocesecerts
if errorlevel 1 (
    echo.
    echo  ERROR: go build failed.
    exit /b 1
)

echo [3/3] Done.
echo.
for %%I in (DioceseCerts.exe) do echo  Built: %%~fI  (%%~zI bytes)
echo.
echo  DO NOT run UPX or any other packer on this file — it causes antivirus
echo  false-positives. To avoid flags entirely, Authenticode code-sign the exe
echo  (see README.md, "Avoiding antivirus false-positives").
echo.

endlocal
