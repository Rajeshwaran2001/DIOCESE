; ============================================================================
;  Inno Setup script for Diocese Certificate Manager
;
;  Build the installer:
;    1. Build DioceseCerts.exe first (run ..\build.bat).
;    2. Install Inno Setup 6  ->  https://jrsoftware.org/isdl.php
;    3. Open this file in the Inno Setup Compiler and press Compile (F9),
;       or from a command prompt:
;         "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
;
;  Output: installer\Output\DioceseCerts-Setup.exe
;
;  Inno produces small, well-trusted installers that run on Windows 7+.
;  To avoid antivirus flags, also Authenticode-sign BOTH DioceseCerts.exe and
;  the produced setup .exe (see README.md and the [Setup] SignTool note below).
; ============================================================================

#define MyAppName "Diocese Certificate Manager"
#define MyAppShortName "DioceseCerts"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Diocese of Madurai Ramnad, Church of South India"
#define MyAppExeName "DioceseCerts.exe"

[Setup]
AppId={{B7B1F1B0-6E2A-4C7E-9E2A-DCE5A2A0F001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppShortName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename={#MyAppShortName}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Minimum OS: Windows 7 SP1 (version 6.1.7601).
MinVersion=6.1.7601

; 64-bit application.
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; If you install to Program Files you need admin rights. To install WITHOUT any
; admin prompt, switch the two lines below: comment out PrivilegesRequired and
; uncomment the lowest+localappdata pair, then change DefaultDirName above to
; {localappdata}\{#MyAppShortName}.
PrivilegesRequired=admin
;PrivilegesRequired=lowest
;PrivilegesRequiredOverridesAllowed=dialog

; --- Authenticode signing (uncomment after configuring a SignTool in the IDE) ---
; SignTool=signtool
; SignedUninstaller=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; The single executable. (Built by ..\build.bat — adjust path if needed.)
Source: "..\DioceseCerts.exe"; DestDir: "{app}"; Flags: ignoreversion
; A default empty config is intentionally NOT shipped: the app creates a
; sensible config.json on first run, and on Program Files it falls back to
; %APPDATA%\DioceseCerts automatically.

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
