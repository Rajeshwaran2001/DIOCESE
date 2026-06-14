; ===========================================================================
;  setup.iss — Inno Setup script for Diocese Certificate Manager
;
;  Wraps the Nuitka standalone folder (dist\main.dist) into a single installer.
;  * Installs per-user to %LOCALAPPDATA% (NO admin rights required).
;  * Creates Start Menu + optional desktop shortcut.
;  * Requires Windows 7 SP1 or newer (MinVersion=6.1sp1).
;  * Bundles & silently installs the VC++ 2015-2022 x64 redistributable
;    (Windows 7 may lack the Universal CRT that the Nuitka build needs).
;
;  Build the installer:
;    1) Run build.bat first so dist\main.dist exists.
;    2) Download vc_redist.x64.exe into installer\redist\
;    3) Open this file in Inno Setup and click Compile (or: iscc setup.iss)
;
;  Output: installer\Output\DioceseCertManager-Setup.exe
; ===========================================================================

#define MyAppName "Diocese Certificate Manager"
#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "Diocese of Madurai Ramnad CSI"
#define MyAppExeName "main.exe"

[Setup]
AppId={{B2D7F0C1-4E2A-4E6B-9A3F-DIOCESE000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\DioceseCertManager
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=DioceseCertManager-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Per-user install -> no UAC / admin prompt.
PrivilegesRequired=lowest
; Windows 7 SP1 and up only.
MinVersion=6.1sp1
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; The entire Nuitka standalone folder.
Source: "..\dist\main.dist\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; VC++ redistributable bundled as a prerequisite (place the exe here first).
Source: "redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VCRedistNeeded

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Silently install the VC++ redist if it's missing.
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; \
  StatusMsg: "Installing Microsoft Visual C++ runtime..."; Check: VCRedistNeeded; Flags: waituntilterminated
; Offer to launch the app at the end.
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function VCRedistNeeded(): Boolean;
var
  Installed: Cardinal;
begin
  // The VC++ 2015-2022 x64 redist writes this value when present.
  Result := True;
  if RegQueryDWordValue(HKLM,
       'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
       'Installed', Installed) then
  begin
    if Installed = 1 then
      Result := False;
  end;
end;
