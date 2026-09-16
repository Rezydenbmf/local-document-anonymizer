# Do zweryfikowania przez użytkownika

Lista rzeczy zbudowanych i technicznie przetestowanych przeze mnie, które
czekają na Twoje potwierdzenie: czy to, co zrobiłem, faktycznie odpowiada
temu, czego chciałeś — nie tylko czy "działa" w sensie technicznym. Testy
i weryfikacja na żywym buildzie łapią błędy w kodzie; nie mogą sprawdzić,
czy dobrze zrozumiałem zadanie.

Gdy potwierdzisz pozycję (działa / nie działa, ewentualnie z poprawką) —
przenoszę ją do „Potwierdzone" albo usuwam. Jeśli lista urośnie powyżej
10 pozycji, przypomnę o niej sam, nawet bez pytania.

## Do sprawdzenia

- [ ] **Przycisk „Zakończ edycję" po zaakceptowaniu zmian w oknie
      porównania** (commit `b124ecd`, 2026-09-12) — zweryfikowane
      programowo (wszystkie 5 przejść stanu panelu), ale nie klikane
      ręcznie w realnej aplikacji. Sprawdź: po zaakceptowaniu edycji
      panel w prawym dolnym rogu powinien pokazać „✓ Zmiany zapisane" i
      przycisk „Zakończ edycję" zamiast po prostu zniknąć; kliknięcie
      przycisku powinno zamknąć okno porównania.

- [ ] **„Wyczyść historię" — dwuetapowy przepływ kasowania plików**
      (2026-09-15) — jeden przycisk zamiast osobnego per folder, kasuje
      pliki robocze od razu, o finalne wyniki pyta osobno. Sprawdź: czy
      treść i kolejność pytań ma sens, czy próg 30 dni dla przypomnienia
      w Historii jest dla Ciebie trafny, i czy zachowanie przy odmowie
      (nic się nie kasuje, licznik przypomnienia NIE resetuje się) jest
      zgodne z tym, czego oczekiwałeś.
- [ ] **Utracona możliwość przycinania starych generacji finalnych
      wyników** (2026-09-15, świadoma decyzja do potwierdzenia, nie
      błąd) — stara wersja „Wyczyść stare" usuwała nieaktualne generacje
      również wśród plików finalnych (zostawiała tylko najnowszy
      umowa_ANON_VISUAL_3.pdf, kasując _1/_2). Nowe „Wyczyść historię"
      tego nie robi — finalne wyniki albo zostają wszystkie, albo
      usuwasz je wszystkie naraz. Czy to Ci odpowiada, czy chcesz z
      powrotem możliwość „zostaw tylko najnowszy" dla finalnych wyników
      jako osobną opcję?
- [ ] **Eksport zatwierdzonych plików z wyborem lokalizacji**
      (2026-09-15) — okno wyboru folderu otwiera się teraz wewnątrz
      folderu, z którego eksportujesz. Sprawdź: czy to wygodny punkt
      startowy, czy wolisz inny (np. ostatnio używany folder eksportu,
      albo Dokumenty). Anulowanie okna teraz po cichu anuluje cały
      eksport (wcześniej zawsze lądowało w stałym podfolderze
      approved/) — potwierdź, że to oczekiwane zachowanie.
- [ ] **Magic pen — nowy system trybów interakcji myszy (Etap 3,
      2026-09-16)** — trzy tryby: „Domyślny" (LPM=zaznacz, PPM=przesuń
      widok, środkowy=przytrzymaj i kliknij/przeciągnij żeby odznaczyć),
      „Klasyczny" (LPM=zaznacz, PPM=odznacz — jak dotychczas — plus
      nowość: środkowy=przesuń widok), „Niestandardowy" (przypisujesz
      sam w Ustawienia > Ogólne, przypisanie tej samej akcji do innego
      przycisku zamienia je miejscami zamiast błędu). Stare przyciski
      „Dodaj/Usuń zaznaczenie" (przypinanie LPM) zniknęły z paska u góry
      — zastąpione małym opisem trybu obok Cofnij/Ponów. Sprawdź na
      żywo: czy PPM rzeczywiście przesuwa widok w trybie domyślnym (nie
      odznacza), czy przytrzymanie środkowego i przeciągnięcie po kilku
      zaznaczeniach naraz faktycznie je zdejmuje, czy tryb
      niestandardowy w Ustawieniach zapisuje się poprawnie między
      sesjami, i czy podpowiedź przy pierwszym otwarciu dokumentu
      (dialog „Co możesz zrobić z tym dokumentem?") poprawnie opisuje
      wybrany tryb.
- [ ] **Cache'owanie detekcji w oknie porównania (Etap 2, 2026-09-16)**
      — zapis po ręcznej edycji magic penem na skanie powinien być teraz
      wyraźnie szybszy (zmierzone: ~14s → ~1s na syntetycznym 6-stronicowym
      skanie) zamiast robić OCR od nowa za każdym razem. Sprawdź na
      prawdziwym, wielostronicowym skanie: czy zapis w oknie porównania
      faktycznie odczuwalnie przyspieszył, i czy edycja słownika wrażliwych
      terminów w trakcie otwartego okna porównania (ten sam plik, nowa
      zawartość) nadal poprawnie wpływa na kolejny zapis — to naprawiony w
      tej samej sesji błąd (code-review złapał go przed mergem), warto
      potwierdzić na żywo.

## Potwierdzone

*(pusto na razie)*
