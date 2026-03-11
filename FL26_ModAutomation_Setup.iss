; FL26_ModAutomation_Setup.iss
; Inno Setup 6+ required — https://jrsoftware.org/isinfo.php
;
; HOW TO BUILD:
;   1. Run PyInstaller first:
;        pyinstaller FL26_ModAutomation.spec
;   2. The exe will be at: dist\FL26_ModAutomation.exe
;   3. Open this .iss file in Inno Setup Compiler and click Build > Compile
;   4. Output: dist\FL26_ModAutomation_Setup.exe

#define AppName "FL26 Mod Automation"
#define AppVersion "1.0.0"
#define AppPublisher "FL26 Mod Tools"
#define AppURL "https://github.com/YOUR_USERNAME/FL26-Mod-Automation"
#define AppExeName "FL26_ModAutomation.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; OutputDir is relative to the .iss file location
OutputDir=dist
OutputBaseFilename=FL26_ModAutomation_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Require admin so we can write to Program Files
PrivilegesRequired=admin
; Minimum Windows 10
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable (built by PyInstaller)
Source: "dist\{#AppExeName}";           DestDir: "{app}";  Flags: ignoreversion

; PowerShell backend scripts
Source: "Run-FL26-ModAutomation.ps1";   DestDir: "{app}";  Flags: ignoreversion
Source: "Assign-GripSox-Single.ps1";   DestDir: "{app}";  Flags: ignoreversion
Source: "Assign-GripSox-Brands.ps1";   DestDir: "{app}";  Flags: ignoreversion
Source: "Assign-Socks.ps1";            DestDir: "{app}";  Flags: ignoreversion
Source: "Assign-Pants.ps1";            DestDir: "{app}";  Flags: ignoreversion
Source: "Assign-Gloves.ps1";           DestDir: "{app}";  Flags: ignoreversion
Source: "Assign-Handtape.ps1";         DestDir: "{app}";  Flags: ignoreversion
Source: "Validate-Assignments.ps1";    DestDir: "{app}";  Flags: ignoreversion

; Config and player list (do NOT overwrite if user has already saved settings)
Source: "FL26_ModAutomation.config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "PlayerIds.csv";                  DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Optional Desktop shortcut (only if user ticked the task above)
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch the app after install
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up log CSVs and the generated PlayerIds.csv on uninstall
Type: filesandordirs; Name: "{app}\*_Assignments.csv"
Type: files;          Name: "{app}\PlayerIds.csv"
