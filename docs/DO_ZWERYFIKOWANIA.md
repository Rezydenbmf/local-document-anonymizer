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

## Potwierdzone

*(pusto na razie)*
