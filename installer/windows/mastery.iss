; XLRTE Mastery Setup (Inno Setup 6). Built by installer/build.py:
;   ISCC /DVersion=0.1.0 /DPayload=<folder> /DOutDir=<folder> /DOutName=<name> mastery.iss
#ifndef Version
  #define Version "dev"
#endif
#ifndef Payload
  #define Payload "payload"
#endif
#ifndef OutDir
  #define OutDir "."
#endif
#ifndef OutName
  #define OutName "XLRTE-Mastery-setup"
#endif

[Setup]
AppId={{E208BF5E-DCDE-44E1-8742-AFB845B9D868}
AppName=XLRTE Mastery
AppVersion={#Version}
AppPublisher=yslop
AppPublisherURL=https://github.com/yslop/xlrte-mastery
DefaultDirName={userdocs}\XLRTE Mastery
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutDir}
OutputBaseFilename={#OutName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UsePreviousAppDir=yes
Uninstallable=no
CreateUninstallRegKey=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; program files are replaced on update; your own data (config, learning state) is never overwritten
Source: "{#Payload}\*"; DestDir: "{app}"; Excludes: "config\*,_xlrte\config.json,_xlrte\data\*,_xlrte\state\*,_xlrte\journal\*,_xlrte\inbox\*,_xlrte\bridge\*,_xlrte\lab\*,_xlrte\_backup\*"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userdesktop}\XLRTE Mastery"; Filename: "{app}\mastery.cmd"; WorkingDir: "{app}"; Comment: "XLRTE Mastery Cockpit"
Name: "{userprograms}\XLRTE Mastery"; Filename: "{app}\mastery.cmd"; WorkingDir: "{app}"; Comment: "XLRTE Mastery Cockpit"

[Run]
Filename: "{app}\mastery.cmd"; WorkingDir: "{app}"; Flags: postinstall nowait shellexec skipifsilent; Description: "{cm:LaunchProgram,XLRTE Mastery}"
