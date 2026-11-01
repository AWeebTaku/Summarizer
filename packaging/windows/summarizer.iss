; Per-user installer (no admin rights needed). Build: iscc /DVersion=2.0.0 packaging\windows\summarizer.iss
#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
AppId={{00EE90A8-D200-4A63-95CF-1A937C6D8D19}
AppName=Summarizer
AppVersion={#Version}
AppPublisher=Aditya Chaurasiya
AppPublisherURL=https://github.com/AWeebTaku/Summarizer
AppSupportURL=https://github.com/AWeebTaku/Summarizer/issues
DefaultDirName={autopf}\Summarizer
DefaultGroupName=Summarizer
DisableProgramGroupPage=yes
; Installs for the current user (no admin prompt). The dialog lets someone choose all users instead.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\release
OutputBaseFilename=Summarizer-setup
SetupIconFile=..\icons\icon.ico
UninstallDisplayIcon={app}\Summarizer.exe
LicenseFile=..\..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\..\dist\Summarizer\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Summarizer"; Filename: "{app}\Summarizer.exe"
Name: "{autodesktop}\Summarizer"; Filename: "{app}\Summarizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Summarizer.exe"; Description: "Open Summarizer"; Flags: nowait postinstall skipifsilent
