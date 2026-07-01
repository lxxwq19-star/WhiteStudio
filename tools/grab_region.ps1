param(
    [int]$X = 60,
    [int]$Y = 60,
    [int]$W = 1760,
    [int]$H = 1160,
    [string]$Out = "C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\tools\gui_v3_layout.png"
)
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($X, $Y, 0, 0, (New-Object System.Drawing.Size($W, $H)))
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$g.Dispose()
Write-Host "Saved: $Out  ($W x $H at $X,$Y)"
