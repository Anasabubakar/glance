; ────────────────────────────────────────────────────────────────────
;  Glance for Windows — Inno Setup script
;
;  Builds a single Setup-Glance.exe from the PyInstaller dist folder.
;
;  Prerequisites:
;    1. Run PyInstaller:  python -m PyInstaller glance.spec --clean --noconfirm
;    2. Install Inno Setup 6 from https://jrsoftware.org/isdl.php
;    3. Run from repo root:  iscc installer.iss
;
;  Output:  dist\Setup-Glance.exe   (single-file installer, ~200-400 MB)
; ────────────────────────────────────────────────────────────────────

#define MyAppName        "Glance"
#define MyAppVersion     "0.2.0"
#define MyAppPublisher   "Anas Abubakar"
#define MyAppURL         "https://github.com/Anasabubakar/glance"
#define MyAppExeName     "Glance.exe"

[Setup]
AppId={{9A4E3F2C-7B1D-4A8F-9C6E-3D7F1B5E9A0C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=Setup-Glance
SetupIconFile=glance\shell\assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon";  Description: "Launch Glance when Windows &starts";  GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "installollama"; Description: "Also download && install Ollama (free local AI engine, ~700 MB) — needed for the no-API-key mode"; GroupDescription: "Free AI engine:"

[Files]
; Everything PyInstaller produced
Source: "dist\Glance\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";                    Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}";          Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$ErrorActionPreference='Stop'; $url='https://ollama.com/download/OllamaSetup.exe'; $dst=Join-Path $env:TEMP 'OllamaSetup.exe'; Invoke-WebRequest -Uri $url -OutFile $dst -UseBasicParsing; Start-Process -FilePath $dst -ArgumentList '/SILENT' -Wait"""; \
  StatusMsg: "Downloading and installing Ollama (this can take a few minutes)..."; \
  Tasks: installollama; \
  Flags: runhidden waituntilterminated

; Offer to launch Glance after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox(
      'Glance installed successfully!' #13#13
      'On first launch, Glance will walk you through downloading the AI models' #13
      'so it can answer your questions offline (free, no API keys needed).' #13#13
      'You can also use Claude / OpenAI / Gemini / GitHub Copilot — see' #13
      '.env.example inside the install folder for the template.',
      mbInformation, MB_OK
    );
  end;
end;
