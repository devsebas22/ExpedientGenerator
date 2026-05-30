; =============================================================================
; Expediente Digital — Inno Setup 6.x
;
; Qué genera este script:
;   dist\installer\ExpedienteDigital_Setup.exe  (~55 MB)
;
; Arquitectura de dos ejecutables:
;   ExpedienteDigital.exe      — Launcher (~7.6 MB): comprueba actualizaciones y
;                                lanza la app. Es el acceso directo del usuario.
;   ExpedienteDigital_app.exe  — App completa (~48 MB): FastAPI + PyMuPDF +
;                                frontend. Se actualiza silenciosamente via launcher.
;
; Para compilar:
;   1. Ejecutar build_all.bat (genera dist\ExpedienteDigital.exe y
;      dist\ExpedienteDigital_app.exe)
;   2. Abrir este archivo en Inno Setup Compiler → Ctrl+F9
; =============================================================================

#define AppName      "Expediente Digital"
#define AppVersion   "1.1.5"
#define AppPublisher "Sebastian Mogollon"
#define AppExeName   "ExpedienteDigital.exe"
; GUID único — no cambiar entre versiones del mismo producto
#define AppId        "{{8F2A1C7D-4E9B-4F03-A821-BCD1234567EA}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}

; ── Ubicación de instalación ─────────────────────────────────────────────────
DefaultDirName={localappdata}\ExpedienteDigital
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; Sin requisito de administrador
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

; ── Salida ───────────────────────────────────────────────────────────────────
OutputDir=..\dist\installer
OutputBaseFilename=ExpedienteDigital_Setup

; ── Ícono ────────────────────────────────────────────────────────────────────
SetupIconFile=..\assets\icono.ico
UninstallDisplayIcon={app}\{#AppExeName}

; ── Compresión ───────────────────────────────────────────────────────────────
Compression=lzma2/ultra64
SolidCompression=yes
DiskSpanning=no

; ── Apariencia ───────────────────────────────────────────────────────────────
WizardStyle=modern
WizardSizePercent=120

; ── Información en Programas instalados ──────────────────────────────────────
AppComments=Genera expedientes digitales con foliación automática
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName}
VersionInfoProductName={#AppName}
AppSupportURL=https://wa.me/573164698626

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
es.WelcomeLabel2=Este asistente instalará [name/ver] en su equipo.%n%nLa aplicación le permitirá unir archivos PDF, imágenes y Word, y foliarlos automáticamente para generar expedientes digitales.%n%nHaga clic en Instalar para continuar.
es.FinishedLabel=La instalación de [name] ha finalizado correctamente.%n%nHaga clic en Listo para salir.
es.ButtonFinish=Listo
es.ButtonInstall=Instalar

[Tasks]
Name: "desktopicon"; \
  Description: "Crear acceso directo en el escritorio"; \
  GroupDescription: "Accesos directos:"

[Files]
; Launcher — el ejecutable principal (~7.6 MB).
; Comprueba actualizaciones y lanza la app. Es el acceso directo del usuario.
Source: "..\dist\ExpedienteDigital.exe"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

; App completa (~48 MB).
; El launcher la reemplaza silenciosamente al haber actualizaciones.
Source: "..\dist\ExpedienteDigital_app.exe"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

; Versión instalada — evita que el launcher re-descargue en el primer arranque.
Source: "..\version.txt"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Dirs]
Name: "{app}\expedientes_generados"
Name: "{app}\logs"
Name: "{app}\temp"

[Icons]
Name: "{group}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  IconFilename: "{app}\{#AppExeName}"; \
  Comment: "Generador de expedientes digitales con foliado automático"

Name: "{group}\Desinstalar {#AppName}"; \
  Filename: "{uninstallexe}"

Name: "{autodesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  IconFilename: "{app}\{#AppExeName}"; \
  Comment: "Generador de expedientes digitales con foliado automático"; \
  Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
  Description: "Abrir {#AppName} ahora"; \
  Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}\temp"
; Los expedientes generados y logs NO se eliminan — son documentos del usuario
