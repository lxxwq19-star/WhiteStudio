Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowPlacement(IntPtr hWnd, out WINDOWPLACEMENT lpwndpl);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpfn, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int W, int H, bool bRepaint);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndAfter, int X, int Y, int cx, int cy, uint uFlags);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] public struct WINDOWPLACEMENT {
        public uint length; public uint flags; public uint showCmd; public POINT ptMinPosition; public POINT ptMaxPosition; public RECT rcNormalPosition;
    }
}
"@

# 1) 找所有 WhiteStudio 进程
$ws_procs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*WhiteStudio*' }
Write-Host "=== WhiteStudio processes ==="
$ws_procs | ForEach-Object {
    $h = $_.MainWindowHandle
    $r = New-Object W+RECT
    [W]::GetWindowRect($h, [ref]$r) | Out-Null
    $cls = New-Object System.Text.StringBuilder 256
    [W]::GetClassName($h, $cls, 256) | Out-Null
    $wp = New-Object W+WINDOWPLACEMENT
    $wp.length = 44
    [W]::GetWindowPlacement($h, [ref]$wp) | Out-Null
    Write-Host ("pid={0} hwnd={1} class={2} title='{3}' visible={4} iconic={5} showCmd={6} rect=({7},{8},{9},{10}) size={11}x{12} norm=({13},{14},{15},{16})" -f `
        $_.Id, $h, $cls.ToString(), $_.MainWindowTitle, `
        [W]::IsWindowVisible($h), [W]::IsIconic($h), $wp.showCmd, `
        $r.L, $r.T, $r.R, $r.B, ($r.R-$r.L), ($r.B-$r.T), `
        $wp.rcNormalPosition.L, $wp.rcNormalPosition.T, $wp.rcNormalPosition.R, $wp.rcNormalPosition.B)
}

# 2) 列举所有可见顶层窗口（看 WhiteStudio 到底在哪/被谁挡）
Write-Host "`n=== All top-level visible windows ==="
$script:idx = 0
$cb = [W+EnumWindowsProc]{
    param($h, $l)
    $script:idx++
    $len = [W]::GetWindowTextLength($h)
    if ($len -gt 0 -and [W]::IsWindowVisible($h)) {
        $t = New-Object System.Text.StringBuilder ($len + 2)
        [W]::GetWindowText($h, $t, $len + 2) | Out-Null
        $r = New-Object W+RECT
        [W]::GetWindowRect($h, [ref]$r) | Out-Null
        $cls = New-Object System.Text.StringBuilder 256
        [W]::GetClassName($h, $cls, 256) | Out-Null
        Write-Host ("  [{0}] hwnd={1} class={2} rect=({3},{4},{5},{6}) size={7}x{8} title='{9}'" -f `
            $script:idx, $h, $cls.ToString(), $r.L, $r.T, $r.R, $r.B, ($r.R-$r.L), ($r.B-$r.T), $t.ToString())
    }
    return $true
}
[W]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
