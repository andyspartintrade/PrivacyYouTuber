# Φέρνει το PrivacyYouTuber στο προσκήνιο (και το μεγιστοποιεί).
param([string]$WindowTitle = "Privacy-YouTuber")

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@

# Βρες το παράθυρο
$h = [Win32]::FindWindow($null, $WindowTitle)
if ($h -eq [IntPtr]::Zero) {
    # Δοκίμασε με wildcard μέσω Get-Process
    $p = Get-Process -Name "PrivacyYouTuber" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($p) { $h = $p.MainWindowHandle }
}
if ($h -ne [IntPtr]::Zero) {
    [Win32]::ShowWindow($h, 3) | Out-Null   # 3 = SW_MAXIMIZE
    [Win32]::SetForegroundWindow($h) | Out-Null
    Write-Output "OK: focused (hWnd=$h)"
} else {
    Write-Output "FAIL: window not found"
}
