# Bezpieczny skrypt diagnostyczny dla DocShield - sprawdza TYLKO, czy
# dolaczony silnik OCR (Tesseract) jest na miejscu i czy da sie go
# uruchomic. Nie czyta, nie wysyla i nie wyswietla zadnych dokumentow
# ani danych - tylko sciezki, statusy i komunikaty bledow samego
# Tesseracta. Wynik mozna bezpiecznie wkleic z powrotem do czatu.
#
# Uzycie:  powershell -ExecutionPolicy Bypass -File sprawdz_tesseract.ps1

Write-Host "=== DocShield - diagnostyka Tesseract OCR ===" -ForegroundColor Cyan
Write-Host ""

# --- 1. Znajdz folder instalacji ---------------------------------------

$candidates = @(
    "$env:LOCALAPPDATA\Programs\DocShield",
    "$env:ProgramFiles\DocShield",
    "${env:ProgramFiles(x86)}\DocShield"
)
$installDir = $candidates | Where-Object { Test-Path (Join-Path $_ "DocShield.exe") } | Select-Object -First 1

if (-not $installDir) {
    Write-Host "Nie znaleziono DocShield.exe w typowych lokalizacjach." -ForegroundColor Yellow
    Write-Host "Sprawdzone: $($candidates -join ', ')"
    $installDir = Read-Host "Podaj recznie folder instalacji DocShield (ten z DocShield.exe)"
}

if (-not (Test-Path (Join-Path $installDir "DocShield.exe"))) {
    Write-Host "BLAD: brak DocShield.exe w '$installDir'." -ForegroundColor Red
    exit 1
}

Write-Host "Folder instalacji: $installDir"

# --- 2. Sprawdz czy dolaczony Tesseract jest na miejscu -----------------

$tesseractExe = Join-Path $installDir "tesseract\tesseract.exe"
$tessdataDir = Join-Path $installDir "tesseract\tessdata"

Write-Host ""
Write-Host "--- Pliki dolaczonego Tesseracta ---"
if (Test-Path $tesseractExe) {
    Write-Host "tesseract.exe: OBECNY" -ForegroundColor Green
    $size = (Get-Item $tesseractExe).Length
    Write-Host "  Rozmiar: $([math]::Round($size / 1KB, 1)) KB"
} else {
    Write-Host "tesseract.exe: BRAK" -ForegroundColor Red
}

if (Test-Path $tessdataDir) {
    $langFiles = Get-ChildItem $tessdataDir -Filter "*.traineddata" -ErrorAction SilentlyContinue
    Write-Host "tessdata: OBECNY ($($langFiles.Count) plikow jezykowych: $($langFiles.Name -join ', '))"
} else {
    Write-Host "tessdata: BRAK" -ForegroundColor Red
}

$dllCount = (Get-ChildItem (Join-Path $installDir "tesseract") -Filter "*.dll" -ErrorAction SilentlyContinue).Count
Write-Host "Plikow .dll obok tesseract.exe: $dllCount"

# --- 3. Sprobuj faktycznie uruchomic tesseract.exe ----------------------

Write-Host ""
Write-Host "--- Proba uruchomienia tesseract.exe --version ---"
if (Test-Path $tesseractExe) {
    try {
        $output = & $tesseractExe --version 2>&1
        Write-Host "Wynik (kod wyjscia $LASTEXITCODE):"
        $output | ForEach-Object { Write-Host "  $_" }
    } catch {
        Write-Host "BLAD przy uruchomieniu: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "Pomijam - plik nie istnieje."
}

# --- 4. Czy system ma jakis Tesseract na PATH (niezalezny od paczki) ---

Write-Host ""
Write-Host "--- Tesseract w systemowym PATH ---"
$onPath = Get-Command tesseract -ErrorAction SilentlyContinue
if ($onPath) {
    Write-Host "Znaleziono: $($onPath.Source)"
} else {
    Write-Host "Brak (nic w PATH pod nazwa 'tesseract')."
}

# --- 5. Czy Windows Defender cos ostatnio wykryl/skasowal w tym folderze -

Write-Host ""
Write-Host "--- Historia wykryc Windows Defender (jesli dostepna) ---"
try {
    $threats = Get-MpThreatDetection -ErrorAction Stop |
        Where-Object { $_.Resources -match [regex]::Escape($installDir) } |
        Select-Object -First 5
    if ($threats) {
        $threats | ForEach-Object { Write-Host "  $($_.ThreatName) - $($_.Resources)" -ForegroundColor Yellow }
    } else {
        Write-Host "Brak wykryc dla tego folderu."
    }
} catch {
    Write-Host "Niedostepne bez uprawnien administratora - mozna pominac."
}

Write-Host ""
Write-Host "=== Koniec diagnostyki ===" -ForegroundColor Cyan
