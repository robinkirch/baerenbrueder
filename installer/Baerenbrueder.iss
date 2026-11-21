; Inno-Setup-Skript (Inno Setup 7, kompatibel mit 6) fuer die Windows-11-Fassung von "Disneys Baerenbrueder".
; Quelle: dist\Baerenbrueder\ (vorher bauen mit: python tools/build_dist.py)
; Kompilieren: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\Baerenbrueder.iss
;              oder python tools/build_dist.py --installer
; Ergebnis:    dist\Baerenbrueder-Win11-Setup.exe
;
; Das Spiel braucht keine Registry-Eintraege und kein DirectX-Setup. Benutzerdaten (Game.ini, User.ini, Spielstaende)
; legt es selbst unter %ProgramData%\Disney Interactive\Bärenbrüder\System an. Bei Installation fuer alle Benutzer wird
; dieser Ordner vorab mit Schreibrecht fuer alle Benutzer angelegt (sonst gehoert er dem ersten Spieler allein).

#define AppName "Disneys Bärenbrüder"
#define AppVersion "1.0-win11"
#define DataDir "{commonappdata}\Disney Interactive\Bärenbrüder"

[Setup]
AppId={{9CF6F9AF-D90B-42EE-8A78-12A9AC5E829C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} (Windows-11-Fassung)
AppComments=Inoffizielle Windows-11-Anpassung (Community-Patch)
DefaultDirName={autopf}\Bärenbrüder
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x86compatible
MinVersion=10.0
SourceDir=..\dist\Baerenbrueder
OutputDir=..
OutputBaseFilename=Baerenbrueder-Win11-Setup
SetupIconFile=compiler:SetupClassicIcon.ico
UninstallDisplayIcon={app}\system\Game.exe
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4
WizardStyle=modern
ShowLanguageDialog=no

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\Save"
Name: "{#DataDir}"; Permissions: users-modify; Check: IsAdminInstallMode
Name: "{#DataDir}\System"; Permissions: users-modify; Check: IsAdminInstallMode

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\system\Game.exe"; WorkingDir: "{app}\system"
Name: "{group}\Liesmich"; Filename: "{win}\notepad.exe"; Parameters: """{app}\README.md"""
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\system\Game.exe"; WorkingDir: "{app}\system"; Tasks: desktopicon

[Run]
Filename: "{app}\system\Game.exe"; WorkingDir: "{app}\system"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent unchecked

; Spielstaende und Einstellungen unter %ProgramData% bleiben bei der Deinstallation absichtlich erhalten.
