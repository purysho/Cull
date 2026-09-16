$ErrorActionPreference = 'Stop'
python -m pip install --upgrade pyinstaller pillow
python .\tools\make_icon.py
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Cull --icon assets/icon.ico cull_desktop.pyw
Write-Host "Built dist\Cull.exe"
