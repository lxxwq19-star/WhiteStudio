# WhiteStudio GitHub 仓库创建和推送脚本
# 运行方法: 在 PowerShell 中执行 .\setup_github.ps1

Write-Host "=== WhiteStudio GitHub 仓库设置 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 获取 GitHub 信息
$username = Read-Host "请输入你的 GitHub 用户名"
$token = Read-Host "请输入你的 GitHub Personal Access Token (创建方法见下方)" -AsSecureString
$tokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($token))

Write-Host ""
Write-Host "正在创建 GitHub 仓库..." -ForegroundColor Yellow

# 2. 通过 GitHub API 创建仓库
$headers = @{
    "Authorization" = "token $tokenPlain"
    "Accept" = "application/vnd.github.v3+json"
}

$body = @{
    "name" = "WhiteStudio"
    "description" = "BiRefNet 一键批量扣图加白底 - WhiteStudio"
    "private" = $false
    "auto_init" = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "✓ 仓库创建成功: $($response.html_url)" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode -eq 422) {
        Write-Host "⚠ 仓库已存在，继续..." -ForegroundColor Yellow
    } else {
        Write-Host "✗ 创建失败: $_" -ForegroundColor Red
        Write-Host "请手动在 https://github.com/new 创建仓库" -ForegroundColor Yellow
        exit 1
    }
}

# 3. 推送代码
Write-Host ""
Write-Host "正在推送代码..." -ForegroundColor Yellow

Set-Location "C:\Users\23107\.qclaw\workspace\birefnet_whitestudio"

# 配置 git remote
git remote remove origin 2>$null
git remote add origin "https://$username`:$tokenPlain@github.com/$username/WhiteStudio.git"

# 推送
git branch -M main
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ 代码推送成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Cyan
    Write-Host "1. 访问 https://github.com/$username/WhiteStudio/actions" -ForegroundColor White
    Write-Host "2. 等待 GitHub Actions 编译完成 (约 15-30 分钟)" -ForegroundColor White
    Write-Host "3. 在 Artifacts 区域下载 WhiteStudio-macOS.zip" -ForegroundColor White
} else {
    Write-Host "✗ 推送失败，请检查错误信息" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
