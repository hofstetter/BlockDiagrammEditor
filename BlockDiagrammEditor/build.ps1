# Baut eine einzelne BlockDiagrammEditor.exe, die ohne Python-Installation startet.
# Pillow wird mit eingepackt, damit „Auswahl als Grafik“ in der EXE funktioniert.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

py -3 -m pip install -r requirements-build.txt
py -3 -m PyInstaller --noconfirm --onefile --windowed --name BlockDiagrammEditor --hidden-import PIL.Image --hidden-import PIL.ImageDraw --hidden-import PIL.ImageFont --hidden-import PIL.PngImagePlugin --exclude-module numpy BlockDiagrammEditor.py

Write-Host "Fertig: $PSScriptRoot\dist\BlockDiagrammEditor.exe"
