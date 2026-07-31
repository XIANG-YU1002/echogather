# 把前端部署到 Cloudflare Workers（主要網址 www.echogather.workers.dev）。
#
# 用法：在專案根目錄執行
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-cloudflare.ps1
#
# 為什麼需要這支腳本：
# GitHub Pages 那份會在 push 後自動更新，但 Cloudflare 這份的自動部署
# （.github/workflows/deploy-cloudflare.yml）連續失敗、錯誤訊息又被吞掉，
# 因此改為手動。把步驟寫成腳本而不是要人記兩行指令，是為了避免漏掉
# 那兩個環境變數——漏了不會報錯，只會安靜地部署出壞掉的版本。

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$nodeDir = "C:\Program Files\nodejs"
if (Test-Path $nodeDir) { $env:PATH = "$nodeDir;$env:PATH" }

Write-Host "=== 1/3 建置前端 ===" -ForegroundColor Cyan
Set-Location (Join-Path $root "frontend")

# 這兩個變數缺一不可：
#   DEPLOY_BASE=/         Cloudflare 部署在網域根目錄；漏了會建置成 GitHub Pages
#                         用的 /echogather/，JS/CSS 全部 404
#   VITE_API_BASE_URL     漏了前端會退回 localhost:8000，線上抓不到任何資料
$env:DEPLOY_BASE = "/"
$env:VITE_API_BASE_URL = "https://wuwagroup-api.onrender.com/api/v1"
# 寫進 index.html 的 build-version meta，方便日後確認線上是哪一版
$env:VITE_BUILD_VERSION = (git rev-parse --short HEAD).Trim()

npm run build
if ($LASTEXITCODE -ne 0) { throw "前端建置失敗" }

Write-Host "`n=== 2/3 確認建置產物 ===" -ForegroundColor Cyan
$indexPath = Join-Path $root "frontend\dist\index.html"
$index = Get-Content $indexPath -Raw
if ($index -match '"/echogather/assets') {
    throw "建置產物指向 /echogather/，DEPLOY_BASE 沒有生效——部署上去會整站白畫面"
}
if ($index -notmatch 'src="/assets/') {
    throw "找不到預期的 /assets/ 路徑，請檢查建置結果"
}
Write-Host "  資源路徑為根目錄，正確"

Write-Host "`n=== 3/3 部署到 Cloudflare ===" -ForegroundColor Cyan
Set-Location $root
npx --yes wrangler deploy
if ($LASTEXITCODE -ne 0) { throw "Cloudflare 部署失敗" }

Write-Host "`n完成：https://www.echogather.workers.dev" -ForegroundColor Green
Write-Host "提醒：GitHub Pages 那份要另外 git push 才會更新。" -ForegroundColor Yellow
