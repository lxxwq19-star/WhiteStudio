Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int H, bool r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string t);
}
'@

$p = Get-Process -Name python -ErrorAction SilentlyContinue |
     Where-Object { $_.MainWindowTitle -like '*WhiteStudio*' } |
     Select-Object -First 1
if ($p) {
    $h = $p.MainWindowHandle
    Write-Host "Found window: PID=$($p.Id) hwnd=$h title='$($p.MainWindowTitle)'"
    [W]::MoveWindow($h, 60, 60, 1760, 1160, $true) | Out-Null
    [W]::SetForegroundWindow($h) | Out-Null
    Start-Sleep -Seconds 1
    Write-Host "Moved to (60,60,1760,1160)"
} else {
    Write-Host "No WhiteStudio window found"
}
