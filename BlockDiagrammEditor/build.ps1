# Baut eine einzelne BlockDiagrammEditor.exe, die ohne Python-Installation startet.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

py -3 -m pip install -r requirements-build.txt
py -3 -m PyInstaller --noconfirm --onefile --windowed --name BlockDiagrammEditor BlockDiagrammEditor.py

Write-Host "Fertig: $PSScriptRoot\dist\BlockDiagrammEditor.exe"
