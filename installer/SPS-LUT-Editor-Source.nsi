Unicode True
!include "MUI2.nsh"

!define APP_NAME "SPS LUT Editor"
!define APP_VERSION "0.1.8"
!define LAUNCHER "Start SPS LUT Editor.cmd"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "..\release\SPS-LUT-Editor-Setup.exe"
InstallDir "$LOCALAPPDATA\SPS LUT Editor"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File "..\Start SPS LUT Editor.cmd"

  SetOutPath "$INSTDIR\source"
  File /r /x "__pycache__" "..\source\*.*"

  SetOutPath "$INSTDIR\.venv"
  File /r /x "__pycache__" "..\.venv\*.*"

  CreateShortcut "$DESKTOP\SPS LUT Editor.lnk" "$INSTDIR\${LAUNCHER}" "" "$INSTDIR\source\assets\sps-lut-editor.ico" 0
  WriteUninstaller "$INSTDIR\Uninstall SPS LUT Editor.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "UninstallString" '"$INSTDIR\Uninstall SPS LUT Editor.exe"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "NoRepair" 1
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\SPS LUT Editor.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor"
  RMDir /r "$INSTDIR"
SectionEnd
