param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$candidates = @('python', 'py', "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe")
$interpreter = $null
foreach ($candidate in $candidates) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        & $candidate -c 'import sys; assert sys.version_info >= (3,11)' 2>$null
        if ($LASTEXITCODE -eq 0) { $interpreter = $candidate; break }
    }
}
if (-not $interpreter) { throw 'Python 3.11+ is required. Install Python, reopen PowerShell, then run this script again.' }
& $interpreter -m shopflooriq serve --port $Port
