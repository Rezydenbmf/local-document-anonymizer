# Builds the DocShield alpha demo installer end to end:
#   1. PyInstaller packages the app + its Python runtime (DocShield.spec)
#   2. A trimmed local Tesseract-OCR runtime is copied alongside it
#      (Tesseract is a native binary, not a Python library - PyInstaller
#      cannot pack it, so this script stages a real local install into
#      dist\DocShield\tesseract\ instead)
#   3. Inno Setup compiles installer\DocShield.iss into one
#      installer_output\DocShield-Setup-<version>.exe
#
# Requires locally: this project's venv (with pyinstaller installed -
# see requirements-dev.txt / `pip install pyinstaller`), a local
# Tesseract-OCR install (used only as the source to copy from - the
# people who receive the installer do NOT need Tesseract themselves),
# and Inno Setup 6 or 7 (https://jrsoftware.org/isinfo.php).
#
# Usage:  powershell -ExecutionPolicy Bypass -File build_installer.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

function Write-Step($text) {
    Write-Host ""
    Write-Host "=== $text ===" -ForegroundColor Cyan
}

function Remove-DirWithRetry($path) {
    # A freshly-built .exe can stay briefly locked (antivirus scan, search
    # indexer) even after nothing in this script is using it - PyInstaller's
    # own --clean hit exactly this once as a PermissionError. A few short
    # retries ride that out instead of failing the whole build over it.
    if (-not (Test-Path $path)) { return }
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            Remove-Item -Recurse -Force $path -ErrorAction Stop
            return
        } catch {
            if ($attempt -eq 5) { throw }
            Start-Sleep -Seconds 2
        }
    }
}

# --- 0. Locate tools -------------------------------------------------

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Nie znaleziono .venv\Scripts\python.exe - uruchom najpierw setup venv (patrz README)."
}

$isccCandidates = @(
    "C:\Program Files\Inno Setup 7\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    $found = Get-ChildItem "C:\Program Files*" -Filter ISCC.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $iscc = $found.FullName }
}
if (-not $iscc) {
    throw "Nie znaleziono ISCC.exe (Inno Setup). Zainstaluj z https://jrsoftware.org/isinfo.php i uruchom ponownie."
}

$tesseractCandidates = @(
    "C:\Program Files\Tesseract-OCR",
    "C:\Program Files (x86)\Tesseract-OCR"
)
$tesseractSrc = $tesseractCandidates | Where-Object { Test-Path (Join-Path $_ "tesseract.exe") } | Select-Object -First 1
if (-not $tesseractSrc) {
    throw "Nie znaleziono lokalnej instalacji Tesseract-OCR (potrzebna jako zrodlo do skopiowania do paczki)."
}

Write-Host "Python:    $python"
Write-Host "ISCC:      $iscc"
Write-Host "Tesseract: $tesseractSrc"

# --- 1. Read the app version straight from the source of truth -------

$version = & $python -c "import sys; sys.path.insert(0, 'src'); from gui_helpers import APP_VERSION; print(APP_VERSION)"
$version = $version.Trim()
if (-not $version) { throw "Nie udalo sie odczytac APP_VERSION z src/gui_helpers.py." }
Write-Host "Wersja:    $version"

# --- 2. PyInstaller ----------------------------------------------------

Write-Step "PyInstaller: pakowanie aplikacji"
Remove-DirWithRetry (Join-Path $root "dist")
Remove-DirWithRetry (Join-Path $root "build")
& $python -m PyInstaller "DocShield.spec" --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller zakonczyl sie bledem (kod $LASTEXITCODE)." }

$distDir = Join-Path $root "dist\DocShield"
if (-not (Test-Path (Join-Path $distDir "DocShield.exe"))) {
    throw "Brak dist\DocShield\DocShield.exe po buildzie - PyInstaller nie zakonczyl sie poprawnie."
}

# --- 3. Stage a trimmed Tesseract runtime next to the exe -------------

Write-Step "Dolaczanie Tesseract OCR (pol + eng)"
$tesseractDest = Join-Path $distDir "tesseract"
New-Item -ItemType Directory -Force -Path $tesseractDest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $tesseractDest "tessdata") | Out-Null

Copy-Item (Join-Path $tesseractSrc "tesseract.exe") $tesseractDest -Force
Get-ChildItem (Join-Path $tesseractSrc "*.dll") | Copy-Item -Destination $tesseractDest -Force

$languages = @("eng.traineddata", "pol.traineddata", "osd.traineddata")
foreach ($lang in $languages) {
    $src = Join-Path $tesseractSrc "tessdata\$lang"
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $tesseractDest "tessdata") -Force
    } else {
        Write-Warning "Brak pliku jezykowego $lang w zrodlowej instalacji Tesseract - pomijam."
    }
}

$tesseractSizeMb = [math]::Round(((Get-ChildItem $tesseractDest -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB), 1)
Write-Host "Tesseract dolaczony ($tesseractSizeMb MB)."

# --- 4. Inno Setup ------------------------------------------------------

Write-Step "Inno Setup: budowanie instalatora"
$outputDir = Join-Path $root "installer_output"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

& $iscc "installer\DocShield.iss" "/DMyAppVersion=$version"
if ($LASTEXITCODE -ne 0) { throw "ISCC zakonczyl sie bledem (kod $LASTEXITCODE)." }

$installerPath = Join-Path $outputDir "DocShield-Setup-$version.exe"
if (Test-Path $installerPath) {
    $installerSizeMb = [math]::Round(((Get-Item $installerPath).Length / 1MB), 1)
    Write-Step "Gotowe"
    Write-Host "Instalator: $installerPath ($installerSizeMb MB)" -ForegroundColor Green
} else {
    throw "Nie znaleziono instalatora pod spodziewana sciezka: $installerPath"
}
