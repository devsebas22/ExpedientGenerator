; =============================================================================
; Expediente Digital — Inno Setup 6.x
;
; Qué genera este script:
;   dist\installer\ExpedienteDigital_Setup_1.0.0.exe
;
; Qué hace el instalador:
;   - Instala ExpedienteDigital.exe en AppData del usuario (sin admin)
;   - Crea acceso directo en el escritorio (marcado por defecto)
;   - Crea acceso directo en el menú Inicio
;   - Crea las carpetas temp/, logs/, expedientes_generados/
;   - Instala desinstalador accesible desde Panel de Control
;   - No requiere Python instalado en el equipo del cliente
;
; Para compilar:
;   Abrir en Inno Setup Compiler → Ctrl+F9
; =============================================================================

#define AppName      "Expediente Digital"
#define AppVersion   "1.0.0"
#define AppPublisher "Tu Nombre o Empresa"
#define AppExeName   "ExpedienteDigital.exe"
; GUID único de la aplicación — no cambiar entre versiones del mismo producto
#define AppId        "{{8F2A1C7D-4E9B-4F03-A821-BCD1234567EA}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}

; ── Ubicación de instalación ─────────────────────────────────────────────────
; {localappdata} = C:\Users\<usuario>\AppData\Local
; No requiere permisos de administrador.
; Los expedientes generados también quedan aquí, accesibles para el usuario.
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; Sin requisito de administrador
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

; ── Salida ───────────────────────────────────────────────────────────────────
OutputDir=..\dist\installer
OutputBaseFilename=ExpedienteDigital_Setup_{#AppVersion}

; ── Compresión ───────────────────────────────────────────────────────────────
Compression=lzma2/ultra64
SolidCompression=yes
DiskSpanning=no

; ── Apariencia ───────────────────────────────────────────────────────────────
WizardStyle=modern
WizardSizePercent=120
; SetupIconFile=..\assets\icono.ico   ; descomentar si se tiene ícono .ico

; ── Información que aparece en Programas instalados ──────────────────────────
AppComments=Herramienta para generar expedientes digitales con foliado automático
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName}
VersionInfoProductName={#AppName}

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
es.WelcomeLabel2=Este asistente instalará [name/ver] en su equipo.%n%nLa aplicación le permitirá unir archivos PDF y foliarlos automáticamente para generar expedientes digitales.%n%nHaga clic en Siguiente para continuar.

[Tasks]
; Acceso directo en escritorio — marcado por defecto
Name: "desktopicon"; \
  Description: "Crear acceso directo en el escritorio"; \
  GroupDescription: "Accesos directos:"

[Files]
; El .exe generado por PyInstaller.
; Ya contiene Python embebido + FastAPI + PyMuPDF + frontend.
; El cliente NO necesita instalar nada más.
Source: "..\dist\{#AppExeName}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Dirs]
; Crear carpetas de trabajo al instalar.
; La app también las crea automáticamente al arrancar, esto es solo por si acaso.
Name: "{app}\expedientes_generados"
Name: "{app}\logs"
Name: "{app}\temp"

[Icons]
; Acceso directo en el menú Inicio
Name: "{group}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  Comment: "Generador de expedientes digitales con foliado automático"

; Desinstalador en el menú Inicio
Name: "{group}\Desinstalar {#AppName}"; \
  Filename: "{uninstallexe}"

; Acceso directo en el escritorio
Name: "{autodesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  Comment: "Generador de expedientes digitales con foliado automático"; \
  Tasks: desktopicon

[Run]
; Al terminar la instalación, ofrecer abrir la app
Filename: "{app}\{#AppExeName}"; \
  Description: "Abrir {#AppName} ahora"; \
  Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
; Al desinstalar: eliminar carpeta temporal (son archivos de trabajo efímeros)
Type: filesandordirs; Name: "{app}\temp"
; Los expedientes generados y logs NO se eliminan — son documentos del usuario
