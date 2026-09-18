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
- [ ] **Wersjonowanie wyboru kategorii w pliku JSON (2026-09-17,
      techniczna poprawka, trudna do bezpośredniego sprawdzenia)** —
      przy okazji poprzedniego punktu code-review znalazł powiązany,
      poważniejszy błąd: plik JSON zapamiętujący wybór kategorii przy
      pierwszej anonimizacji zapisywał tylko nazwy kategorii, a nie to,
      co dokładnie wtedy oznaczały. Gdyby ta zmiana (jak wyżej) trafiła
      do apki bez tej poprawki, otwarcie **starszego** dokumentu w oknie
      porównania i zapisanie jakiejkolwiek niepowiązanej ręcznej edycji
      mogłoby po cichu odsłonić wcześniej zanonimizowaną nazwę
      firmy/adres. Naprawione zanim to się mogło zdarzyć — plik JSON
      zapamiętuje teraz dokładny, zamrożony zestaw danych z momentu
      pierwszej anonimizacji, nie samą nazwę kategorii. Nie ma tu nic
      konkretnego do klikania — samo pilnowanie, żeby ręczna edycja
      starszego dokumentu w oknie porównania nigdy nie odsłaniała
      danych, które wcześniej były ukryte, jest wystarczającym testem
      na żywo.

- [ ] **Kategorie do anonimizacji — czytelność etykiet checkboxów
      (2026-09-17, zaktualizowane po Twoim teście — realny błąd
      znaleziony i naprawiony)** — poprzednia poprawka (przeniesienie
      na górę panelu) działa, ale **Twój feedback ze screenshotem**:
      dłuższe etykiety („Kategorie do anonimizacj[i]", „Numer konta
      bankowego (I...)", „Adres (ulica, miejscowość, k...)", „Dane
      firmy (nazwa, NIP, REG...)") były ucinane, nie zawijały się.
      Przyczyna: CTkCheckBox (widget checkboxa) w ogóle nie obsługuje
      zawijania tekstu — długa etykieta po prostu wychodziła poza wąski
      panel „Szybkie akcje" i była wizualnie ucinana. Naprawione:
      etykiety skrócone do samej nazwy kategorii („Dane firmy", „Adres",
      „IBAN"...), a pełny opis (co dokładnie kryje się pod daną
      kategorią) przeniesiony do dymka po najechaniu myszką na
      checkbox. Też skrócony i zawijany tytuł karty. Sprawdź na żywo:
      czy wszystkie 8 etykiet mieści się teraz w całości bez ucinania,
      i czy najechanie myszką na checkbox pokazuje dymek z pełnym
      opisem.

- [ ] **Etykieta pola (np. „Adres”) już nie znika z tabelarycznych
      dokumentów (2026-09-17)** — to była przyczyna tego dziwnego
      zamalowania, które zauważyłeś na screenshocie z pisma urzędowego.
      Nie był to błąd współrzędnych/rysowania — wzorzec wykrywający
      nietypowe nazwiska (i podobne dla ulicy/miejscowości) „połykał”
      pierwsze słowo z następnego wiersza tabeli, traktując je jakby
      było częścią nazwiska w wierszu poprzednim. Naprawione w 3
      miejscach na raz (kod miał osobne kopie tych samych wzorców):
      `src/anonymizer.py`, `src/pdf_redaction.py` (tryb PDF
      „oryginalny układ”) i `src/audit.py` (skaner pozostałości).
      Sprawdź na żywo: zanonimizuj ponownie `3_pismo_urzedowe.pdf`
      (albo inny dokument z tabelą, gdzie etykieta pola sąsiaduje z
      nazwiskiem z myślnikiem albo z miejscowością) — etykiety pól
      („Adres”, „Numer” itp.) powinny zostać na miejscu, nie znikać.

- [ ] **NIP/REGON wykrywane, gdy etykieta i wartość są w osobnych
      komórkach tabeli (2026-09-18)** — to była pierwsza konkretna
      przyczyna „Dane firmy działa gorzej”: `NIP\nREGON\n526-000-12-46\n
      012345678` (etykiety osobno, wartości osobno — typowy układ
      faktury) w ogóle nie było wykrywane, mimo zaznaczonej kategorii.
      Naprawione — program teraz paruje etykietę z najbliższą pasującą
      wartością (do 4 linijek dalej), nie ruszając samej etykiety.
      Sprawdź na żywo: zanonimizuj ponownie `2_faktura_vat.pdf` z
      zaznaczoną tylko kategorią „Dane firmy” — NIP i REGON powinny
      zniknąć z wyniku, mimo że w oryginale etykieta i numer nie są
      obok siebie.

- [ ] **Ogólna jakość wykrywania przez AI poprawiona — nie tylko nazwy
      firm z formą prawną (2026-09-18)** — po Twoim potwierdzeniu
      poprawki „Sp. z o.o./S.A." wybrałeś dalej „ogólną jakość NER dla
      nazw firm". Znaleziona przyczyna: mechanizm AI, który miał
      sklejać nazwisko rozdzielone łamaniem wiersza w PDF-ie (np.
      "Jan\nKowalski"), sklejał też przypadkiem niepowiązane słowa z
      sąsiednich wierszy/komórek tabeli w jeden fałszywy twór, który
      potem był odrzucany w całości — razem z prawdziwą, samodzielną
      nazwą firmy czy miejscowości, jeśli akurat sąsiadowała ze
      sklejeniem. Naprawione przebudową mechanizmu (dwuprzebiegowa
      analiza) — dotyczy nie tylko nazw firm, ale też lokalizacji i
      innych kategorii wykrywanych przez AI. Przy naprawie code-review
      znalazł i naprawił dodatkowo realny błąd (mógłby ujawnić fragment
      nazwiska, gdyby nie złapany przed wydaniem). Sprawdź na żywo:
      zanonimizuj ponownie `2_faktura_vat.pdf` (samo AI, bez włączania
      wzorca z formy prawnej — np. sprawdź na dokumencie, gdzie nazwa
      firmy nie kończy się na „Sp. z o.o."/„S.A.") i dokumenty z
      nazwiskiem rozdzielonym na dwa wiersze — czy nazwy nadal są
      wykrywane w całości, nie tylko fragmentami.

- [ ] **Nazwisko z myślnikiem w PDF-ie już nie znika w całości
      (2026-09-18)** — to zauważyłeś sam na screenshocie z
      `5_pismo_nazwisko_dwa_wiersze.pdf`: pierwsze wystąpienie
      „Bartlomiej Zaremba-Wojciechowski" nie było zamazane w ogóle, ani
      trochę. Przyczyna była głębsza niż samo AI: PDF traktuje
      „Zaremba-Wojciechowski" (bez spacji wokół myślnika) jako jedno
      słowo, a mechanizm rysujący ramki odrzucał całe dopasowanie, gdy
      AI wskazało tylko część słowa („Zaremba") — więc całe nazwisko
      zostawało bez żadnej ochrony, gorzej niż zwykłe pominięcie.
      Naprawione — teraz taki przypadek rozszerza zaznaczenie na całe
      słowo. Sprawdź na żywo: zanonimizuj ponownie
      `5_pismo_nazwisko_dwa_wiersze.pdf` — oba wystąpienia nazwiska
      powinny być teraz w pełni zamazane (nie tylko drugie, w podpisie).

## Potwierdzone

- [x] **Eksport zatwierdzonych plików z wyborem lokalizacji** (2026-09-15,
      potwierdzone 2026-09-17) — Twój feedback: „eksport i otwieranie się
      gotowego pdf działają". Uwaga: to potwierdza, że mechanizm działa
      ogólnie — nie było osobnego komentarza o wygodzie punktu
      startowego folderu ani o zachowaniu po Anuluj, więc jeśli coś z
      tych dwóch szczegółów Ci przeszkadza, daj znać, wrócę do tego
      punktu.
- [x] **Przycisk „Zakończ edycję" po zaakceptowaniu zmian w oknie
      porównania** (commit `b124ecd`, 2026-09-12, potwierdzone
      2026-09-17) — Twój feedback: „działa".
- [x] **„Wyczyść historię" — dwuetapowy przepływ kasowania plików**
      (2026-09-15, potwierdzone 2026-09-17) — Twój feedback: treść i
      kolejność pytań, próg 30 dni i zachowanie przy odmowie „działa z
      wyjątkiem starych folderów" — wyjątek, na który trafiłeś (foldery
      pokazujące „folder nie istnieje"), to osobny błąd, opisany niżej.
- [x] **„Wyczyść historię" usuwa też wpis z listy, w tym „foldery-duchy"
      spoza dysku** (2026-09-17, potwierdzone 2026-09-17) — Twój
      feedback: „ad5 - zatwierdzam". Dwa stare foldery pokazujące
      „folder nie istnieje" (bo skasowane spoza apki) teraz też znikają
      z listy Historia po kliknięciu „Wyczyść historię", tak jak
      normalne, opróżnione z plików tej apki foldery.
- [x] **Status recenzji nie „pamięta” już starego odrzucenia po
      ponownym przetworzeniu** (2026-09-17, potwierdzone 2026-09-17) —
      Twój feedback: „ad4 - zatwierdzam".
- [x] **Uruchamianie bez widocznej konsoli** (2026-09-17, potwierdzone
      2026-09-17) — Twój feedback: „ad6 zatwierdzam".
- [x] **Cache'owanie detekcji w oknie porównania (Etap 2, 2026-09-16)**
      (potwierdzone 2026-09-17) — Twój feedback: „tak potwierdzam".
- [x] **Wybór kategorii do anonimizacji — mechanizm poszerzonego zakresu
      (Etap 4, 2026-09-17)** — Twój feedback: „ad1 - zatwierdzam". Sam
      mechanizm (odznaczenie „Adres"/„Dane firmy" faktycznie zostawia
      te dane widoczne, łącznie z tym co wykrywa AI) działa. Osobna
      uwaga z tego samego testu — jakość/precyzja wykrywania „Dane
      firmy" ("działało gorzej" niż PESEL/e-mail) — przeniesiona z tej
      listy do `docs/PROJECT_STATE.md` jako zadanie do głębszych testów,
      nie błąd do jednorazowego potwierdzenia.
- [x] **Nazwa firmy wykrywana niezależnie od AI, na podstawie formy
      prawnej (Sp. z o.o., S.A., ...)** (2026-09-18, potwierdzone
      2026-09-18) — Twój feedback: „tak zatwierdzam poprawkę/
      funkcjonalność" (po zrzucie z żywego okna porównania: obie nazwy
      firm, sprzedawca i nabywca, oraz powtórzona nazwa sprzedawcy w
      stopce, w pełni fioletowo zamazane, nie tylko częściowo jak
      wcześniej). Druga połowa „Dane firmy działa gorzej” — pierwsza
      (NIP/REGON w tabelach) potwierdzona wyżej. **Wciąż otwarte, osobny
      wątek**: samo rozpoznawanie nazw firm przez AI (gdy nazwa nie ma
      na końcu „Sp. z o.o.”/„S.A.” — inna forma prawna, brak formy
      prawnej w ogóle, albo literówka) — poza tym nowym wzorcem nie
      zostało poprawione.
- [x] **Magic pen — kursor/plakietki: zostawiamy jak jest na razie**
      (2026-09-17) — Twój feedback: „magic pen zostaje - tak jak jest
      teraz (ogólnie to estetycznie będę chciał dopracować) ale nie
      będę się nad tym teraz skupiał bo to polerowanie tylko, a my
      musimy dopieścić logikę i funkcje". Świadomie odłożone, nie
      „potwierdzone jako idealne" — kursor `pencil`/`hand2`/`X_cursor`
      i plakietki zostają w obecnym kształcie; dalsza estetyczna
      dopieszczka (własna grafika kursora, ewentualny drugi wątek z
      plakietkami LPM/PPM/ŚPM) czeka, aż wrócisz do tego tematu.
