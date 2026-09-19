[CmdletBinding()]
param(
    [string]$PythonLauncher = "py",
    [string[]]$PythonLauncherArguments = @("-3.14")
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvDirectory = Join-Path $projectRoot ".venv-build"
$venvPython = Join-Path $venvDirectory "Scripts\python.exe"
$requirementsFile = Join-Path $projectRoot "requirements-build.txt"
$entryPoint = Join-Path $projectRoot "outlook_commander.py"
$distDirectory = Join-Path $projectRoot "dist"
$workDirectory = Join-Path $projectRoot "build\pyinstaller"

Push-Location $projectRoot
try {
    & $PythonLauncher @PythonLauncherArguments -m venv $venvDirectory
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r $requirementsFile
    & $venvPython -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --console `
        --name OutlookCommander `
        --hidden-import socksio `
        --distpath $distDirectory `
        --workpath $workDirectory `
        --specpath $workDirectory `
        $entryPoint
}
finally {
    Pop-Location
}

Write-Host "Build complete: $distDirectory\OutlookCommander.exe"
