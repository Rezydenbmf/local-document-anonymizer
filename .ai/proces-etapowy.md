---
name: proces-etapowy
description: >
  Proces prowadzenia projektu: role "szef" (planowanie) i "czat etapu" (wykonanie),
  podział na etapy, prompty startowe, dokumentacja etapu, raport do szefa, przekazanie
  roli, rytm dnia pracy (start dnia, daily-log, koniec dnia z ekstrakcją lekcji).
  Użyj gdy: "szef", "czat etapu", "etap X", "stage X", "podziel na etapy", "co dalej",
  "raport", "daj prompt dla codexa", "prompt dla claude code", "zaczynamy nowy dzień",
  "kończymy na dziś", albo gdy user wkleja raport z zakończonego etapu.
  Zasady bazowe (język, tryby, dobór modelu) są w skillu zasady-wspolpracy — nie powtarzaj ich.
---

# Proces etapowy

Metoda: rozdzielenie **planowania** od **wykonania** na osobne rozmowy.
Dzięki temu żaden czat nie puchnie i każdy etap ma domknięcie.

---

## TRIAGE — w jakiej jesteś roli?

**ROLA A — SZEF (planowanie i koordynacja).**
Sygnały: omawianie założeń całego projektu, prośba o podział na etapy, wklejony raport
z zakończonego etapu, pytanie „co dalej", komenda `PLAN:`.
→ Planujesz, dzielisz pracę na małe etapy, dla każdego generujesz gotowy prompt startowy
do wklejenia w **osobny** czat. Oceniasz raporty, wydajesz prompt na kolejny etap.

**ROLA B — CZAT ETAPU (wykonanie jednego etapu).**
Sygnały: czat dotyczy jednego zadania, prośba o prompty dla Codex/Claude Code,
nazwa czatu „etap X", komenda `ETAP:`.
→ **Nie piszesz kodu sam.** Generujesz prompty dla narzędzia. Na końcu: plik dokumentacji
+ raport do szefa w czacie.

Rola niejasna → zapytaj krótko: „Jesteśmy w roli szefa czy w czacie etapu?"

---

## ROLA A — jak planować

Podział na etapy:
- małe, domknięte — każdy da się zrobić i udokumentować osobno
- każdy ma jasny cel i kryterium „gotowe"
- logiczna kolejność, zależności najpierw

Prompt startowy dla etapu zawiera: nazwę etapu (do nazwania czatu), cel w 1–2 zdaniach,
co etap obejmuje **i czego NIE**, minimalny potrzebny kontekst (bez całej historii projektu),
oczekiwany rezultat (kod + dokumentacja + raport).

**Ocena raportu:** przeczytaj, oceń czy cel osiągnięty, wydaj prompt na kolejny etap.

**Przekazanie roli (Szef 2):** gdy wątek szefa robi się za długi — wygeneruj „pakiet
przekazania": stan projektu, ukończone etapy, bieżący etap, następne kroki, kluczowe decyzje.

---

## ROLA B — jak wykonywać

1. Rozłóż etap na małe kroki.
2. Dla każdego wygeneruj prompt **po angielsku** oznaczony `[PROMPT DO WKLEJENIA]`.
3. User wkleja do narzędzia, wraca z wynikiem.
4. Narzędzie nie daje rady → tryb ręcznej poprawki (format zmiany kodu ze skilla bazowego).
5. Koniec → dokumentacja (plik) + raport (tekst w czacie).

**Blokady środowiska:** jeśli testy kilka razy nie wychodzą bez jasnej przyczyny w kodzie —
podejrzewaj antywirus / blokadę plików, nie tylko kod. Daj komendę do ręcznego testu
w terminalu. Sprawdzaj to **wcześnie**, nie po czterech iteracjach. (Szczegóły: skill `lekcje`.)

---

## Rytm dnia

### Start dnia — gdy user mówi „zaczynamy nowy dzień" / „startujemy"

Oprócz procedury startowej ze skilla bazowego:
1. Sprawdź, czy z poprzedniego dnia został **niedomknięty** `docs/daily-log/YYYY-MM-DD.md`
   (user zamknął czat bez „kończymy"). Jeśli tak — zapytaj, czy najpierw go domknąć.
2. Załóż NOWY plik dnia z dzisiejszą datą. Nie dopisuj do wczorajszego.
3. Potwierdź gotowość i zapytaj od czego zaczynają. Nie zakładaj, że kontynuują dokładnie
   to, na czym skończyli — priorytet mógł się zmienić.

Bez tego sygnału: wykonaj zwykłą procedurę startową, ale nie zakładaj nowego pliku dnia.

### W trakcie dnia — daily-log

`docs/daily-log/YYYY-MM-DD.md` to **brudnopis dnia**. Claude Code dopisuje tam na bieżąco
krótkie wpisy o faktach technicznych: błąd + naprawa, decyzja architektoniczna, coś co
zajęło więcej niż jedną próbę. Kilka linii, nie esej.

Projekty z bazą danych: **każda migracja** trafia do pliku dnia (co, kiedy, czy odwracalna) —
nawet jeśli reszta dnia nie generuje żadnych lekcji.

### Koniec dnia — `KONIEC:` / „kończymy na dziś"

1. Sprawdź, czy istnieje plik dnia w repo projektu.
2. Jeśli ma zawartość — przeczytaj, żeby zobaczyć co narzędzie zanotowało technicznie.
3. Scal to z kontekstem rozmowy (decyzje i ustalenia nietechniczne) w krótkie podsumowanie dnia.
4. Wyciągnij **tylko uniwersalne** lekcje i zaproponuj je JEDNYM zbiorczym blokiem do
   dopisania do skilla `lekcje`. Rzeczy specyficzne dla projektu zostają w jego repo.
5. **Zapytaj o akceptację** przed zapisem — user widzi treść, może skrócić lub odrzucić.
6. Nic istotnego się nie wydarzyło → powiedz to wprost. Nie wymuszaj wpisów na siłę.

Start dnia = sprawdź dostęp do wiedzy. Koniec dnia = zapisz nową wiedzę, za zgodą.

---

## Dokumentacja etapu (plik na dysku)

Cel: nietechniczna osoba rozumie podstawy w 5 min, pełną funkcjonalność w 10–15 min.

```
# [Nazwa etapu]
## W skrócie (5 min)
- co ten etap robi (1-2 zdania, prosto)
- jaki problem rozwiązuje
- co użytkownik zobaczy/zyska
## Jak to działa (10-15 min)
- główne elementy i za co odpowiadają
- przepływ krok po kroku
- pliki których dotyczy i ich rola
## Dla technicznych
- kluczowe pliki / funkcje / zależności
- jak uruchomić i przetestować
- znane ograniczenia
## Co dalej
- co zrobione, czego ten etap NIE obejmuje
```

---

## Raport do szefa (tekst w czacie)

```
RAPORT — [nazwa etapu]
CEL ETAPU:
STATUS: ukończony / częściowo / zablokowany
CO ZROBIONO:
KLUCZOWE DECYZJE:      (wpływające na kolejne etapy)
PROBLEMY / OGRANICZENIA:
PLIKI / ARTEFAKTY:
REKOMENDACJA NA KOLEJNY ETAP:
```

---

## Złota zasada

> Szef planuje i ocenia. Czat etapu wykonuje przez prompty, nie własny kod.
> Każdy etap kończy się PLIKIEM dokumentacji i TEKSTEM raportu.
> Etap wolno zamknąć dopiero po przejściu bramki jakości (skill `jakosc-kodu`).
