---
name: projekt-app
description: >
  Wzorce i pułapki techniczne przy budowie aplikacji z logiką: dane i storage, API,
  migracje bazy, walidacja wejścia, autoryzacja, sekrety, logi, integracje.
  Użyj gdy: "aplikacja", "backend", "API", "baza danych", "storage", "autoryzacja",
  "endpoint", "migracja", "webhook", "logika biznesowa", "automatyzacja", "skrypt
  przetwarzający dane".
  NIE dla stron wizytówkowych/portfolio bez logiki — tam skill projekt-www.
  Zawiera TYLKO rzeczy specyficzne dla aplikacji. Proces → proces-etapowy,
  Git → git-i-repo, jakość → jakosc-kodu, zasady ogólne → zasady-wspolpracy.
---

# Aplikacje — wzorce techniczne

**Status: szkielet.** Sekcje poniżej wypełniają się przy kolejnych projektach.
Puste nagłówki są celowe — pokazują gdzie ma trafić nowa wiedza.

---

## Podwyższone ryzyko — kiedy zwolnić

Zadania dotyczące **autoryzacji, walidacji danych wejściowych, płatności i danych osobowych**
domyślnie dostają wyższy model i wyższy poziom rozumowania, nawet jeśli wyglądają prosto.
Koszt błędu jest tu wyższy niż w warstwie wizualnej.

---

## Migracje bazy danych

- **Checkpoint w gicie PRZED każdą migracją.** Zmianę schematu trudniej odwrócić niż zmianę kodu.
- Każda wykonana migracja trafia do pliku dnia (`docs/daily-log/`): co, kiedy, czy odwracalna.
  To zapis krytyczny dla bezpieczeństwa — robimy go nawet gdy reszta dnia jest nudna.
- Migracja na danych produkcyjnych → najpierw kopia zapasowa, potem test na kopii.

---

## Sekrety i konfiguracja

- Klucze API i hasła **tylko** w `.env`. `.env` w `.gitignore`. Do repo trafia `.env.example`
  z nazwami zmiennych bez wartości.
- Nigdy nie wklejaj prawdziwego klucza do promptu ani do rozmowy z AI.
- Gdy klucz przypadkiem trafił do commitu — samo usunięcie pliku nie wystarcza, klucz
  zostaje w historii. Trzeba go **unieważnić i wygenerować nowy**.

---

## Logi i obsługa błędów

Automatyzacja, która pada o 3 w nocy, musi zostawić ślad. Ustal na starcie projektu:
gdzie idą logi, co się w nich znajduje (data, operacja, wynik, treść błędu),
jak długo są trzymane. Logi nie mogą zawierać sekretów ani danych osobowych.

Zależność opcjonalna przestała działać → preferuj **degradację funkcji** zamiast awarii
całej aplikacji, jeśli ma to sens produktowy.

**Wzorzec: opcjonalne zależności lokalne (OCR, NER, lokalny LLM i podobne).**
Funkcja oparta o ciężką zależność lokalną (biblioteka, model, zewnętrzny lokalny
proces typu Ollama) zaczyna od **wykrywania dostępności**, nie zakłada że zależność
jest zainstalowana. Brak paczki, brak modelu, wyłączona funkcja, błąd przetwarzania →
zawsze kontrolowany status („niedostępne", „pominięto"), nigdy wyjątek pokazany
użytkownikowi. Testy dla takich funkcji mockują zależność — nie wymagają, żeby
prawdziwy model/silnik był zainstalowany, żeby testy przeszły. Pierwsze uruchomienie
lokalnego modelu bywa wolne (ładowanie do pamięci) — to osobny, obsłużony przypadek
(dłuższy timeout, retry), nie błąd do ukrycia.

---

## Zapis danych użytkownika

Najgroźniejsza operacja w aplikacji. Zasady:
- zapis atomowy (plik tymczasowy → podmiana) albo kopia przed nadpisaniem
- test na: brak pliku, brak uprawnień, istniejący plik wynikowy, przerwany zapis
- najpierw testy na danych **syntetycznych**, dopiero potem prawdziwe dane

### Dane wrażliwe (PII i podobne)

Aplikacja przetwarzająca dane osobowe, dokumenty, cokolwiek wrażliwego:

- **Nigdy nie przechowuj mapy oryginał → zamiennik.** Taka mapa to w praktyce druga
  kopia danych wrażliwych, tylko ukryta gdzie indziej. Raporty i logi pokazują
  **etykiety i liczniki** (np. `EMAIL: 3`), nigdy wykryte wartości źródłowe.
- Skróty/wygody w UI (czyszczenie listy, „otwórz wynik", usuwanie zaznaczenia) nie
  mogą przy okazji ujawnić treści dokumentu, pełnej ścieżki pliku ani sugerować
  automatycznej akceptacji tam, gdzie wymagana jest ręczna weryfikacja człowieka.
- Automatyczne wykrywanie (regex, NER, OCR) to **priorytetyzacja do przeglądu**,
  nie gwarancja. Nazwij to wprost w UI i w dokumentacji — nie obiecuj więcej,
  niż mechanizm faktycznie daje.

---

## Dane / storage / API

*(do uzupełnienia: wzorce walidacji, rate limiting, struktura endpointów, cache)*

---

## Testowanie logiki biznesowej

*(do uzupełnienia: testy jednostkowe vs e2e w tym workflow, weryfikacja zmian
w logice przed commitem)*

---

## Stack typowy

*(do uzupełnienia: framework backendowy, baza danych, hosting)*
