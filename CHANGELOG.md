# Co nowego w DocShield

## 0.2.0-alpha (2026-09-22)

Druga wersja demo, od pierwszego instalatora. Nadal wersja ALPHA — każdy
wynik anonimizacji wymaga ręcznej weryfikacji.

### Nowe funkcje

- **Wybór kategorii do anonimizacji per zadanie** — przed uruchomieniem
  możesz odznaczyć np. „Adres" lub „Dane firmy", jeśli te dane mają
  zostać widoczne w wyniku. Dowód osobisty, PESEL i nietypowe nazwiska
  zostają chronione zawsze, niezależnie od wyboru.
- **Ograniczenie automatycznej anonimizacji PDF-a do wybranych stron** —
  nowe pole „Strony" pozwala wskazać, że zamazywanie ma dotyczyć tylko
  konkretnych stron dokumentu (np. „1-3,5"), reszta zostaje nietknięta.
  Gdy wpisany zakres w ogóle nie pasuje do dokumentu, aplikacja teraz to
  wykrywa i pokazuje wyraźne ostrzeżenie zamiast cichego braku efektu.
- **Usuwanie podpisów elektronicznych z PDF-a** — nowa, osobna opcja
  (domyślnie WYŁĄCZONA, trzeba ją świadomie zaznaczyć), usuwa pole
  podpisu elektronicznego razem z jego widoczną treścią. Nieodwracalne
  w wyniku, stąd domyślne wyłączenie i wyraźne oznaczenie w interfejsie.
- **Nowy system trybów obsługi myszy w edytorze ręcznym (magic pen)** —
  tryb domyślny, klasyczny i w pełni konfigurowalny własny, ustawiane w
  Ustawieniach.
- **Szybsze działanie okna porównania** — wyniki wykrywania są teraz
  zapamiętywane w ramach sesji zamiast liczone od nowa przy każdej
  akcji.

### Poprawki jakości wykrywania

- Nazwiska z myślnikiem (np. „Zaremba-Wojciechowski") już nie znikają
  częściowo w PDF-ie.
- Nazwy firm wykrywane teraz również niezależnie od AI, na podstawie
  formy prawnej (Sp. z o.o., S.A. itd.) — dodatkowa, deterministyczna
  siatka bezpieczeństwa obok wykrywania AI.
- NIP i REGON wykrywane nawet wtedy, gdy etykieta i wartość znajdują
  się w osobnych komórkach tabeli (typowy układ faktury).
- Etykiety pól (np. „Adres", „Numer") już nie znikają razem z sąsiadującą
  wartością w dokumentach tabelarycznych.
- Ogólna poprawa jakości wykrywania przez AI (przebudowany mechanizm
  analizy) — dotyczy nazw firm, lokalizacji i innych kategorii
  wykrywanych automatycznie.

### Poprawki stabilności i wygody

- Eksport zatwierdzonych plików rzeczywiście kopiuje teraz kolorowy PDF
  wynikowy do wybranego folderu (wcześniej kopiował tylko sam plik
  tekstowy).
- Zniknęły migające okna terminala pojawiające się kilka sekund po
  starcie aplikacji.
- Ustawienia otwierają się teraz znacznie szybciej.
- Czytelniejsze etykiety kategorii w panelu „Szybkie akcje" (pełne opisy
  przeniesione do podpowiedzi po najechaniu myszką).
- „Wyczyść historię" usuwa teraz też wpisy folderów skasowanych spoza
  aplikacji.
- Status recenzji (zatwierdzony/odrzucony/do przejrzenia) nie „pamięta"
  już nieaktualnego stanu po ponownym przetworzeniu tego samego pliku.
- Aplikacja uruchamia się bez widocznego okna konsoli w tle.

## 0.1.0-alpha (2026-09-12)

Pierwsza wersja demo — samodzielny instalator Windows, zawierający
wszystko potrzebne do uruchomienia (środowisko + silnik OCR), bez
konieczności osobnej instalacji Pythona.
