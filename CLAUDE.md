# DocShield — jak z tym pracować

Ten projekt korzysta z bazowych zasad współpracy zdefiniowanych w
`.ai\zasady-wspolpracy.md` (mirror ze wspólnego repo `_wiedza-ai`) —
wczytaj ten plik na starcie każdej sesji dotyczącej tego projektu.

## Odstępstwa uzgodnione dla tego projektu (2026-09-15)

Użytkownik ma teraz ograniczony czas na bieżący nadzór (inne obowiązki
poza AI), więc dla DocShield te reguły zastępują domyślną granularność
z `zasady-wspolpracy`:

- **Tryb domyślny: autonomiczny.** Nie wymagaj ręcznego `PLAN:`/`ZRÓB:`
  przy każdej pojedynczej zmianie — stosuj ten podział na poziomie
  większych zadań (~20-30 min pracy), nie mikro-edycji. Pełna ręczna
  kontrola (`PLAN:` z zatrzymaniem na każdym kroku) zostaje rzadkim
  wyjątkiem, tylko gdy user jawnie o nią poprosi.
- **Rutynowe merge do `main` — bez pytania**, o ile testy i lint
  przechodzą, a zakres mieści się w zleconym zadaniu. Wyjątki, które
  ZAWSZE wymagają zatrzymania i pytania: cokolwiek dotyczące
  bezpieczeństwa/danych, cokolwiek nieodwracalne, cokolwiek wysyłane
  lub publikowane na zewnątrz.
- **`docs/DO_ZWERYFIKOWANIA.md` zastępuje wymóg natychmiastowego
  ręcznego testowania.** Po każdej sesji pracy dopisuj tam, co user
  powinien sam sprawdzić — nie tylko czy coś działa technicznie, ale
  czy odpowiada temu, czego faktycznie chciał. Odznaczaj pozycje po
  jego potwierdzeniu. Jeśli lista przekroczy 10 pozycji, przypomnij mu
  o tym wprost, nawet bez pytania.
- **Raport zbiorczy wystarczy w czacie** — nie trzeba osobnego pliku
  dziennika dla tego projektu.

Reszta zasad z `zasady-wspolpracy` (bezpieczeństwo, format zmian,
dokumentacja, dobór modelu) obowiązuje bez zmian.
