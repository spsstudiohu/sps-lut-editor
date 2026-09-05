Unicode True
!include "MUI2.nsh"

!define APP_NAME "SPS LUT Editor"
!define APP_VERSION "0.2.0"

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
  File /r "..\dist\SPS-LUT-Editor\*.*"
  CreateShortcut "$DESKTOP\SPS LUT Editor.lnk" "$INSTDIR\SPS-LUT-Editor.exe" "" "$INSTDIR\SPS-LUT-Editor.exe" 0
  WriteUninstaller "$INSTDIR\Uninstall SPS LUT Editor.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor" "UninstallString" '"$INSTDIR\Uninstall SPS LUT Editor.exe"'
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\SPS LUT Editor.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SPSLUTEditor"
  RMDir /r "$INSTDIR"
SectionEnd
