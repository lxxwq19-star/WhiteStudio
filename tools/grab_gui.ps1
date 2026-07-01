Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int W, int H, bool bRepaint);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@

# 找 WhiteStudio
$ws = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*WhiteStudio*' } | Select-Object -First 1
if (-not $ws) { Write-Host "no WhiteStudio"; exit 1 }
$h = $ws.MainWindowHandle
Write-Host "WhiteStudio hwnd=$h"

# 1) 先把 WhiteStudio 移到主屏左上角，留出 1700x1100 区域 (主屏 0,0,2560,1440,留 100 边距)
[W]::MoveWindow($h, 60, 60, 1700, 1100, $true) | Out-Null
Start-Sleep -Milliseconds 1000

# 2) 读它真实位置
$r = New-Object W+RECT
[W]::GetWindowRect($h, [ref]$r) | Out-Null
$x = [Math]::Max(0, $r.L)
$y = [Math]::Max(0, $r.T)
$w = $r.R - $r.L
$hh = $r.B - $r.T
Write-Host "WhiteStudio rect after move: ($x,$y,$($r.R),$($r.B)) size=${w}x${hh} visible=$([W]::IsWindowVisible($h))"

# 3) 直接截这个矩形 (即使被 QClaw 挡也行——但我们先把它挪开了，应该能露出)
$bmp = New-Object System.Drawing.Bitmap $w, $hh
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($x, $y, 0, 0, (New-Object System.Drawing.Size $w, $hh))
$out = "C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\gui_layout_check.png"
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Host "screenshot saved: $out  size=${w}x${hh}"
