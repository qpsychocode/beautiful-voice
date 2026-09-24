; Inno Setup script: turns dist\BeautifulVoice into BeautifulVoice-Setup.exe.
; Build after PyInstaller:  iscc /DAppVersion=0.2.0 packaging\installer.iss
;
; Installs per user (no administrator prompt) into %LOCALAPPDATA%\Programs,
; adds Start menu and optional desktop shortcuts with the app icon, and an
; entry in Settings -> Apps for uninstalling. Downloaded models and history
; are kept on uninstall unless the user asks to remove them.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Beautiful Voice"
#define AppExe "BeautifulVoice.exe"

[Setup]
AppId={{6F1C2B7E-5A4D-4C3B-9E2F-BEA07F1F0C11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=qpsycho
AppPublisherURL=https://beautiful-voice.vercel.app
AppSupportURL=https://github.com/qpsychocode/beautiful-voice/issues
AppUpdatesURL=https://github.com/qpsychocode/beautiful-voice/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=BeautifulVoice-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=wizard-1x.bmp,wizard-2x.bmp
WizardSmallImageFile=wizard-small-1x.bmp,wizard-small-2x.bmp
Compression=lzma2/ultra64
SolidCompression=yes
; The 32-bit compiler runs out of memory on ~400 MB at ultra64; a separate 64-bit process doesn't.
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=2
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=force
RestartApplications=no
ShowLanguageDialog=auto

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
en.AutoStart=Start Beautiful Voice with Windows
ru.AutoStart=Запускать Beautiful Voice вместе с Windows
de.AutoStart=Beautiful Voice mit Windows starten
fr.AutoStart=Lancer Beautiful Voice au démarrage de Windows
es.AutoStart=Iniciar Beautiful Voice con Windows
pt.AutoStart=Iniciar o Beautiful Voice com o Windows
ja.AutoStart=Windows の起動時に Beautiful Voice を開始する
en.RemoveData=Also delete downloaded speech models, history and settings?
ru.RemoveData=Удалить также скачанные модели, историю и настройки?
de.RemoveData=Auch heruntergeladene Sprachmodelle, Verlauf und Einstellungen löschen?
fr.RemoveData=Supprimer aussi les modèles téléchargés, l'historique et les paramètres ?
es.RemoveData=¿Eliminar también los modelos descargados, el historial y la configuración?
pt.RemoveData=Excluir também os modelos baixados, o histórico e as configurações?
ja.RemoveData=ダウンロードした音声モデル、履歴、設定も削除しますか？

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "{cm:AutoStart}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\BeautifulVoice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "qpsycho.BeautifulVoice"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "qpsycho.BeautifulVoice"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BeautifulVoice"; ValueData: """{app}\{#AppExe}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#AppExe} /F"; Flags: runhidden; RunOnceId: "StopApp"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox(CustomMessage('RemoveData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\BeautifulVoice'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\BeautifulVoice'), True, True, True);
    end;
  if CurUninstallStep = usPostUninstall then
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'BeautifulVoice');
end;
