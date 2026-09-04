---
name: jakosc-kodu
description: >
  Standard jakości projektów budowanych z AI: architektura przed kodem, mały zakres zmiany,
  test razem ze zmianą, linter od pierwszego dnia, bramki jakości przed zamknięciem etapu
  i przed wydaniem, dług techniczny, audyt architektury, priorytety.
  Użyj gdy: powstaje nowy projekt lub moduł, user pyta "jak to zorganizować", "czy to
  dobrze zbudowane", "czy mogę zamknąć etap", "czy to gotowe do wydania", pojawia się
  refactor, testy, ruff/pytest/eslint/vitest, CI, porządek w kodzie, "działa ale...".
  Zasady bazowe są w skillu zasady-wspolpracy, Git i porządek repo w skillu git-i-repo.
---

# Jakość projektu

> „Działa" nie znaczy jeszcze „jest dobrze zbudowane".

Cel: po zakończeniu projektu inny programista (albo user za rok) nie musi najpierw
sprzątać kodu i odtwarzać z rozmów, dlaczego coś zostało zrobione.

**User nie zna standardów inżynierii oprogramowania.** Gdy widzisz monolit, brak testów,
złą nazwę modułu, niepotrzebną zależność albo ryzykowny refactor — powiedz to wprost
i wytłumacz krótko dlaczego. Uczysz procesu przy okazji prawdziwego zadania.

---

## 1. Architektura przed kodem

Przed większą aplikacją zaproponuj **strukturę, nie kod**. Określ: główne odpowiedzialności,
co jest osobnym modułem, jakie dane płyną między modułami, gdzie logika, gdzie GUI,
gdzie zapis plików, gdzie testy.

Dziel **według odpowiedzialności**, nie według liczby linii. Osobny moduł jest dobry, gdy
da się powiedzieć: „ten moduł odpowiada za X". Nazwa ma mówić za co odpowiada —
nie `helpers2.py`, `inne.py`.

**Nie przesadzaj.** Mały projekt nie potrzebuje kilkudziesięciu modułów. Najmniejsza
struktura, która ma jasne odpowiedzialności i może rosnąć bez chaosu.

Zamiast „napisz całą aplikację" → „zaproponuj minimalną architekturę, nie pisz kodu",
potem „zaimplementuj tylko moduł X wraz z testami, nie ruszaj reszty".

---

## 2. Mały zakres każdej zmiany

Dla każdej zmiany określ: cel, **dozwolone pliki**, **pliki których nie wolno ruszać**,
testy do wykonania, warunek zamknięcia.

> jedna funkcja / jeden bug / jeden etap → jedna kontrolowana zmiana

Żadnego refaktoru, aktualizacji bibliotek ani zmian stylistycznych „przy okazji".

---

## 3. Test razem ze zmianą

Nowa funkcja → test. Naprawiony bug → test, który **odtwarza błąd**.

⚠️ **Test naprawiający buga musi najpierw NIE przechodzić.** Uruchom go przed naprawą
i pokaż, że pada. Test, który przechodzi zawsze, wygląda na sukces, a nie sprawdza nic.

```
zmiana → test skupiony na zmianie → pełny zestaw testów → dopiero zamknięcie etapu
```

Zmiana dotyczy zapisu danych lub bezpieczeństwa → testuj też: błędne dane wejściowe,
brak pliku, brak uprawnień, istniejący plik wynikowy, przerwany zapis.

**Pokazuj realny output testów, nie deklarację.** „Testy przechodzą" bez outputu nie liczy się.

---

## 4. Linter od pierwszego dnia

| | Python | Web (Vite/React/TS) |
|---|---|---|
| testy | `pytest` | `vitest` / `npm test` |
| linter | `ruff check .` | `npx eslint .` |
| build | — | `npm run build` |

`pytest` = czy program działa poprawnie. `ruff`/`eslint` = czy kod nie zawiera typowych
problemów (nieużywane importy i zmienne, podejrzane konstrukcje, niespójności).

Nie dodawaj lintera po kilku tysiącach linii bez audytu — wygeneruje setki starych
problemów i sprowokuje ryzykowny masowy refactor.

**CI:** dla repo rozwijanych dłużej niż jednorazowy skrypt rozważ GitHub Actions, które
po każdej zmianie uruchamia linter + testy. Nie dla drobnego skryptu.

---

## 5. Zależności i typowanie

Przed dodaniem biblioteki sprawdź: czy naprawdę potrzebna, czy utrzymywana, czy nie da
się prościej standardową biblioteką. **Nie aktualizuj tylko dlatego, że jest nowsza wersja** —
aktualizacja to zmiana wymagająca testów.

W nowych modułach stosuj adnotacje typów konsekwentnie. Nie dodawaj ich masowo do
stabilnego starego kodu tuż przed wydaniem.

---

## 6. Bezpieczeństwo danych

- **Sekrety** — tylko `.env`, nigdy w kodzie, nigdy w promptcie. Do repo `.env.example`.
- **Nadpisywanie plików użytkownika** to najgroźniejsza operacja w całym projekcie.
  Zapis atomowy (najpierw plik tymczasowy, potem podmiana) albo kopia zapasowa przed zapisem.
- **Logi** — automatyzacja, która pada o 3 w nocy, musi zostawić ślad. Ustal na starcie
  gdzie idą logi i co się w nich znajduje.
- Przed większą zmianą określ: co może się zepsuć, jakie zachowanie musi zostać takie samo,
  które testy są regresyjne, **jak cofnąć zmianę** (checkpoint w gicie — skill `git-i-repo`).
- Projekt już używany produkcyjnie: **stabilność ma pierwszeństwo przed kosmetycznym refaktorem.**

---

## 7. Dług techniczny

Rozwiązanie działa, ale powinno być kiedyś poprawione → zapisz, nie poprawiaj od razu:

```
TECH DEBT: main.py ma kilka odpowiedzialności.
Nie refaktoryzować przed 1.0. Po stabilizacji rozważyć wydzielenie validation.py.
```

Dług techniczny to świadoma decyzja, nie automatycznie błąd.

---

## 8. Bramka jakości — przed zamknięciem etapu

**Kod:** czy zmiana ma mały zakres? czy nie doszła niepotrzebna zależność?
czy odpowiedzialność trafiła do właściwego modułu? czy nie powstał kolejny „worek na wszystko"?
**Testy:** czy jest test nowej funkcji/buga? czy skupiony przechodzi? czy pełny zestaw przechodzi?
**Jakość:** czy linter przechodzi? czy nie ma nieużywanych importów/zmiennych?
**Repo:** czy `git status` pokazuje tylko oczekiwane pliki?
**Dokumentacja:** czy zmiana wymaga aktualizacji dokumentacji technicznej? dziennika?
czy powstała lekcja do dopisania?

Dopiero wtedy etap jest zamknięty.

---

## 9. Bramka jakości — przed wydaniem

```
1. porządek repo (skill git-i-repo)   5. smoke test na prawdziwym buildzie
2. linter                              6. kontrola dokumentacji
3. pełne testy                         7. kontrola zależności
4. build                               8. git status → commit / tag
```

Smoke test = krótki **ręczny** test najważniejszej ścieżki aplikacji po prawdziwym buildzie.

---

## 10. Okresowy audyt architektury (`AUDYT:`)

Po kilku większych etapach — przegląd **tylko do odczytu**: odpowiedzialności modułów,
rosnące monolity, zależności między modułami, duplikacja logiki, stan testów, stan lintera,
porządek repo, dokumentacja, dług techniczny.

**Nie zmieniaj kodu w tym samym kroku.** Najpierw raport, potem osobna decyzja o refaktorze.

Sygnał, że moduł stał się monolitem: robi wiele różnych rzeczy, istnieje wiele niezależnych
powodów żeby go zmienić, testowanie jednej części wymaga uruchamiania niepowiązanych elementów,
nowe funkcje lądują tam tylko dlatego, że „już tam jest logika".

---

## Priorytety

```
1. poprawność
2. bezpieczeństwo danych
3. testowalność
4. czytelność i utrzymywalność
5. prostota
6. wydajność, jeśli faktycznie ma znaczenie
7. kosmetyka
```

Nie komplikuj projektu dla „profesjonalnego wyglądu". Cel: kod, który działa dziś i za rok
nadal da się bezpiecznie zrozumieć oraz rozwijać.
