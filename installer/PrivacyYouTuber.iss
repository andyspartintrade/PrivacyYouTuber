; Privacy YouTuber — Windows installer script (Inno Setup 6).
; Χρήση: κατέβασε το Inno Setup (jrsoftware.org), άνοιξε αυτό το αρχείο, πάτα Compile.
;
; ΑΠΑΙΤΕΙ: να έχεις ήδη χτίσει το dist/PrivacyYouTuber.exe (python build_exe.py).

[Setup]
AppName=Privacy YouTuber
AppVersion=0.1.0
AppPublisher=You
DefaultDirName={localappdata}\PrivacyYouTuber
DefaultGroupName=Privacy YouTuber
OutputBaseFilename=PrivacyYouTuber-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Δεν χρειάζεται admin — εγκαθιστά στο προφίλ του χρήστη.
PrivilegesRequired=lowest

[Files]
Source: "..\dist\PrivacyYouTuber.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Privacy YouTuber"; Filename: "{app}\PrivacyYouTuber.exe"
Name: "{group}\Κατάργηση εγκατάστασης"; Filename: "{uninstallexe}"
Name: "{autostart}\Privacy YouTuber"; Filename: "{app}\PrivacyYouTuber.exe"; Tasks: autostart

[Tasks]
Name: "autostart"; Description: "Να ξεκινά αυτόματα με τα Windows"; GroupDescription: "Εκκίνηση:"

[Run]
Filename: "{app}\PrivacyYouTuber.exe"; Description: "Εκκίνηση τώρα"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
