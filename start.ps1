param([int]$Port = 8502)
$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$runtimePath = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Codex\sb312'
$pythonPath = Join-Path $runtimePath 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'بيئة التشغيل غير موجودة. راجع LOCAL_STATUS.md لإعداد Python 3.12 في Documents\Codex\sb312.'
}
Set-Location -LiteralPath $projectPath
$env:MPLCONFIGDIR = Join-Path $projectPath '.runtime\mpl'
& $pythonPath -m streamlit run (Join-Path $projectPath 'app.py') --server.address 127.0.0.1 --server.port $Port --server.headless true --browser.gatherUsageStats false
exit $LASTEXITCODE
