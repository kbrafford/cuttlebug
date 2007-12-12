; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{66D5A814-2B31-4667-A248-6B0ED0E2D710}
AppName=Cuttlebug
AppVerName=Cuttlebug 0.1
AppPublisher=Ryan Sturmer
AppPublisherURL=http://www.example.org
AppSupportURL=http://www.example.org
AppUpdatesURL=http://www.example.org
DefaultDirName={pf}\Cuttlebug
DefaultGroupName=Cuttlebug
AllowNoIcons=yes
OutputDir=C:\Documents and Settings\rsturmer\My Documents\Projects\Home\Cuttlebug\install
OutputBaseFilename=setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Documents and Settings\rsturmer\My Documents\Projects\Home\Cuttlebug\dist\cuttlebug.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Documents and Settings\rsturmer\My Documents\Projects\Home\Cuttlebug\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\Cuttlebug"; Filename: "{app}\cuttlebug.exe"
Name: "{group}\{cm:UninstallProgram,Cuttlebug}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Cuttlebug"; Filename: "{app}\cuttlebug.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Cuttlebug"; Filename: "{app}\cuttlebug.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\cuttlebug.exe"; Description: "{cm:LaunchProgram,Cuttlebug}"; Flags: nowait postinstall skipifsilent
