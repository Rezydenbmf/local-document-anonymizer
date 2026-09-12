; Inno Setup script for the DocShield alpha demo installer.
; Built by build_installer.ps1, which runs PyInstaller first (producing
; dist\DocShield\), stages a trimmed Tesseract runtime into
; dist\DocShield\tesseract\, then invokes ISCC on this script with
; /DMyAppVersion=<value read from src/gui_helpers.py> so the installer's
; version always matches the app's own APP_VERSION - never edit the
; version here directly.
;
; Result: one DocShield-Setup-<version>.exe that installs the app, its
; bundled Python runtime and its bundled OCR engine with no separate
; downloads and no internet access required during setup.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "DocShield"
#define MyAppPublisher "DocShield"
#define MyAppExeName "DocShield.exe"
#define MyDistDir "..\dist\DocShield"

[Setup]
AppId={{6F1E9B8B-7C2E-4C3A-9C7E-3E9E6C2C3A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=DocShield-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
InfoBeforeFile=przed_instalacja.txt
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz ikonę na pulpicie"; GroupDescription: "Dodatkowe skróty:"

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Odinstaluj {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom {#MyAppName}"; Flags: nowait postinstall skipifsilent
