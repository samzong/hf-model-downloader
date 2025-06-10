; HF Model Downloader Installer Script
!define APPNAME "HF Model Downloader"
!define COMPANYNAME "samzong"
!define DESCRIPTION "A cross-platform GUI application for downloading Hugging Face models"
; These three must be integers
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0
; These will be displayed by the "Click here for support information" link in "Add/Remove Programs"
; It is possible to use "mailto:" links in here to open the email client
!define HELPURL "https://github.com/samzong/hf-model-downloader" ; "Support Information" link
!define UPDATEURL "https://github.com/samzong/hf-model-downloader/releases" ; "Product Updates" link
!define ABOUTURL "https://github.com/samzong/hf-model-downloader" ; "Publisher" link

RequestExecutionLevel admin ;Require admin rights on NT6+ (When UAC is turned on)

InstallDir "$PROGRAMFILES64\${COMPANYNAME}\${APPNAME}"

; rtf or txt file - remember if it is txt, it must be in the DOS text format (\r\n)
; LicenseData "LICENSE"

; This will be in the installer/uninstaller's title bar
Name "${APPNAME}"
; Icon "assets\icon.ico"
outFile "hf-model-downloader-installer.exe"

!include LogicLib.nsh

; Just two pages - install location and installation (no license)
page directory
Page instfiles

!macro VerifyUserIsAdmin
UserInfo::GetAccountType
pop $0
${If} $0 != "admin" ;Require admin rights on NT4+
        messageBox mb_iconstop "Administrator rights required!"
        setErrorLevel 740 ;ERROR_ELEVATION_REQUIRED
        quit
${EndIf}
!macroend

function .onInit
	setShellVarContext all
	!insertmacro VerifyUserIsAdmin
functionEnd

section "install"
	; Files for the install directory - to build the installer, these should be in the same directory as the install script (this file)
	setOutPath $INSTDIR
	; Files added here should be removed by the uninstaller (see section "uninstall")
	file /r "dist\${APPNAME}-windows-*\*"
	
	; Add any other files for the install directory (license files, app data, etc) here
	
	; Uninstaller - See function un.onInit and section "uninstall" for configuration
	writeUninstaller "$INSTDIR\uninstall.exe"
	
	; Start Menu
	createDirectory "$SMPROGRAMS\${COMPANYNAME}"
	createShortCut "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk" "$INSTDIR\hf-model-downloader.exe" "" "$INSTDIR\hf-model-downloader.exe"
	
	; Desktop shortcut
	createShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\hf-model-downloader.exe" "" "$INSTDIR\hf-model-downloader.exe"
	
	; Registry information for add/remove programs
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "DisplayName" "${APPNAME}"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "InstallLocation" "$\"$INSTDIR$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "DisplayIcon" "$\"$INSTDIR\hf-model-downloader.exe$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "Publisher" "$\"${COMPANYNAME}$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "HelpLink" "$\"${HELPURL}$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "URLUpdateInfo" "$\"${UPDATEURL}$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "URLInfoAbout" "$\"${ABOUTURL}$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "DisplayVersion" "$\"${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}$\""
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "VersionMinor" ${VERSIONMINOR}
	# There is no option for modifying or repairing the install
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "NoModify" 1
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" "NoRepair" 1
sectionEnd

# Uninstaller

function un.onInit
	SetShellVarContext all
	
	#Verify the uninstaller - last chance to back out
	MessageBox MB_OKCANCEL "Permanently remove ${APPNAME}?" IDOK next
		Abort
	next:
	!insertmacro VerifyUserIsAdmin
functionEnd

section "uninstall"
	
	# Remove Start Menu launcher
	delete "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk"
	# Try to remove the Start Menu folder - this will only happen if it is empty
	rmDir "$SMPROGRAMS\${COMPANYNAME}"
	
	# Remove desktop shortcut
	delete "$DESKTOP\${APPNAME}.lnk"
	
	# Remove files
	rmDir /r "$INSTDIR"
	
	# Remove uninstaller information from the registry
	DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}"
sectionEnd