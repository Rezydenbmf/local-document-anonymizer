# Builds the DocShield alpha demo installer end to end:
#   1. PyInstaller packages the app + its Python runtime (DocShield.spec)
#   2. A trimmed local Tesseract-OCR runtime is packed into ONE zip file
#      alongside it (Tesseract is a native binary, not a Python library -
#      PyInstaller cannot pack it; it's a single zip and not loose files
#      so the installer never bulk-drops ~60 unsigned binaries at once -
#      see the comment above the zip-staging step for why that matters).
#      The app itself unpacks it on first use (ocr.py).
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

# --- 3. Stage a trimmed Tesseract runtime as ONE zip next to the exe ---
#
# Deliberately one .zip file in [Files], not ~60 loose .exe/.dll files -
# see the docstring on ocr.py's _extract_bundled_tesseract_zip() for the
# full story: a real install once appeared to lose the tesseract folder
# after setup, which turned out to be test-environment contamination
# (a stale remembered install path, a Program Files permissions check
# issue) rather than a confirmed problem with loose binaries as such.
# Kept as a zip anyway - fewer individually-named unsigned binaries for
# third-party security software to react to is a reasonable default
# even without a proven case of it happening. ocr.py's
# _extract_bundled_tesseract_zip() unpacks it on first use, from
# DocShield.exe's own already-running process.

Write-Step "Pakowanie Tesseract OCR do jednego pliku (pol + eng)"
$tesseractStageDir = Join-Path $env:TEMP "docshield_tesseract_stage"
Remove-DirWithRetry $tesseractStageDir
New-Item -ItemType Directory -Force -Path $tesseractStageDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $tesseractStageDir "tessdata") | Out-Null

Copy-Item (Join-Path $tesseractSrc "tesseract.exe") $tesseractStageDir -Force
Get-ChildItem (Join-Path $tesseractSrc "*.dll") | Copy-Item -Destination $tesseractStageDir -Force

$languages = @("eng.traineddata", "pol.traineddata", "osd.traineddata")
foreach ($lang in $languages) {
    $src = Join-Path $tesseractSrc "tessdata\$lang"
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $tesseractStageDir "tessdata") -Force
    } else {
        Write-Warning "Brak pliku jezykowego $lang w zrodlowej instalacji Tesseract - pomijam."
    }
}

$zipPath = Join-Path $distDir "tesseract_runtime.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $tesseractStageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-DirWithRetry $tesseractStageDir

$tesseractZipSizeMb = [math]::Round(((Get-Item $zipPath).Length / 1MB), 1)
Write-Host "Tesseract spakowany ($tesseractZipSizeMb MB): $zipPath"

# --- 3b. Sprawdz, co NAPRAWDE trafilo do paczki -------------------------
#
# Nie pomijaj tego kroku. Pierwsza wydana paczka miala martwe OCR, bo
# PyInstaller nie widzi importow przez import_module() i po cichu nie
# dolaczyl pytesseract - aplikacja startowala normalnie i raportowala
# "Silnik Tesseract nie jest zainstalowany". Testy na kodzie zrodlowym
# tego nie wykryja, bo venv ma wszystkie biblioteki zainstalowane;
# jedyne wiarygodne sprawdzenie to zajrzenie do zbudowanego pliku.

Write-Step "Weryfikacja zawartosci zbudowanej paczki"
& $python (Join-Path $root "installer\verify_bundle.py") (Join-Path $distDir "DocShield.exe")
if ($LASTEXITCODE -ne 0) {
    throw "Paczka jest niekompletna - patrz lista powyzej. Instalator NIE zostal zbudowany."
}

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
