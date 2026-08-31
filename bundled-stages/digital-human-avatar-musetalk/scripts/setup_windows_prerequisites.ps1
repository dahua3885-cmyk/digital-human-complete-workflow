param(
    [switch]$AcceptSystemChanges
)

$ErrorActionPreference = 'Stop'

if (-not $AcceptSystemChanges) {
    Write-Error '该脚本会通过 winget 安装缺少的 Python 3.10 与 FFmpeg。请使用 -AcceptSystemChanges 明确同意。'
    exit 2
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error '没有找到 winget。请先安装 Microsoft App Installer，再重新运行。'
    exit 2
}

$python310Ready = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.10 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 10) else 1)' 2>$null
    $python310Ready = ($LASTEXITCODE -eq 0)
}
if (-not $python310Ready) {
    & winget install --id Python.Python.3.10 --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 安装没有成功。' }
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    & winget install --id Gyan.FFmpeg --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg 安装没有成功。' }
}

Write-Output 'Windows 公共运行依赖已准备完成。NVIDIA 驱动仍需由显卡厂商安装程序负责。'
