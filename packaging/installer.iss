; 拾音 ShiYin 安装包脚本（Inno Setup 6）
; 前置：pyinstaller packaging\shiyin.spec --clean，产物位于 dist\ShiYin
; 编译：ISCC packaging\installer.iss /DAppVersion=0.1.0

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{8F2C41B7-3F1E-4C7A-9B62-5E3A2D8B7C11}
AppName=拾音
AppVerName=拾音 {#AppVersion}
AppVersion={#AppVersion}
AppPublisher=ShiYin
DefaultDirName={autopf}\ShiYin
DefaultGroupName=拾音
UninstallDisplayIcon={app}\ShiYin.exe
OutputDir=..\dist\installer
OutputBaseFilename=ShiYin-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
CloseApplications=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务：" ; Flags: unchecked

[Files]
Source: "..\dist\ShiYin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\拾音"; Filename: "{app}\ShiYin.exe"
Name: "{group}\卸载拾音"; Filename: "{app}\unins000.exe"
Name: "{autodesktop}\拾音"; Filename: "{app}\ShiYin.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ShiYin.exe"; Description: "启动拾音"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\ShiYin"
