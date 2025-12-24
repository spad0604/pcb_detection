# PowerShell script to run the server on Windows
Set-Location $PSScriptRoot

# Cloudinary credentials
$env:CLOUDINARY_URL = "cloudinary://919668245813367:UEkNEm7d4cUChmbtxYAOXequn3A@dhhdd4pkl"
$env:CLOUDINARY_FOLDER = "pcb-inspector"

# Use Python 3.12 from conda base
# Adjust the path to your Python installation if needed
$PYTHON_BIN = "$env:USERPROFILE\miniconda3\python.exe"

# Check if Python exists, otherwise try common locations
if (-not (Test-Path $PYTHON_BIN)) {
    Write-Host "Miniconda Python not found at $PYTHON_BIN"
    Write-Host "Trying to use 'python' from PATH..."
    $PYTHON_BIN = "python"
}

# Run uvicorn - tắt access log để không spam console
& $PYTHON_BIN -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level info --no-access-log
