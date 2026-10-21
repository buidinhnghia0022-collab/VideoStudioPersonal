[Setup]
AppName=Video Studio Personal
AppVersion=0.1.0
DefaultDirName={localappdata}\VideoStudioPersonal
DefaultGroupName=Video Studio Personal
OutputDir=installer
OutputBaseFilename=VideoStudioPersonal_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=Video Studio Personal

[Files]
Source: "dist\VideoStudioPersonal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Video Studio Personal"; Filename: "{app}\VideoStudioPersonal.exe"
Name: "{autodesktop}\Video Studio Personal"; Filename: "{app}\VideoStudioPersonal.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài Desktop"; GroupDescription: "Biểu tượng bổ sung:"; Flags: unchecked

[Run]
Filename: "{app}\VideoStudioPersonal.exe"; Description: "Mở Video Studio Personal"; Flags: nowait postinstall skipifsilent
