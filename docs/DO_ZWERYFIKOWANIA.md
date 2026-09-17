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

- [ ] **Czy chcesz automatyczne kasowanie starych wersji tego samego
      pliku?** (2026-09-15, pytanie o funkcję, nie błąd) — konkretny
      przykład: anonimizujesz tę samą umowę trzy razy, więc w folderze
      masz `umowa_ANON_VISUAL.pdf`, `umowa_ANON_VISUAL_2.pdf` i
      `umowa_ANON_VISUAL_3.pdf` (trzy wersje, bo za każdym razem
      program dopisuje kolejny numer zamiast nadpisywać). Stara wersja
      przycisku „Wyczyść stare" umiała same to posprzątać: zostawiała
      tylko najnowszą (`_3`), kasując automatycznie `_1` i `_2`. Obecny
      „Wyczyść historię” tego nie robi — albo zostają wszystkie trzy
      wersje, albo kasujesz je wszystkie naraz ręcznie. Pytanie: chcesz,
      żebym przywrócił automatyczne „zostaw tylko najnowszą wersję" jako
      osobną opcję, czy obecne zachowanie (Ty decydujesz ręcznie, nic
      nie znika samo) Ci odpowiada?
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

- [ ] **Magic pen — czytelność trybu interakcji myszy (2026-09-17,
      zaktualizowane po Twoim teście — realne błędy znalezione)** —
      odpowiedź na feedback „graficznie nie widać co się robi": 3 kolorowe
      plakietki z ikonką zamiast jednego szarego napisu (LPM/PPM/ŚPM +
      ikonka akcji), strzałki Cofnij/Ponów teraz kolorują się na
      niebiesko gdy faktycznie klikalne, kursor nad dokumentem miał
      odzwierciedlać co zrobi dany przycisk, nowa ikonka ⚙ w oknie
      porównania otwiera Ustawienia > Ogólne. **Twój feedback (ze
      screenshotem plakietek):** „ppm zmienia się w kółko a na ikonce
      jest inny symbol, a lpm zostaje jakiś celownik a nie taka ikonka
      jak na indykatorach, spm też nie zgadza się z indykatorem i kolor
      się też w żadnym nie zmienia" — czyli kursor nad dokumentem nie
      odpowiada wizualnie plakietkom (inny symbol niż na plakietce), a
      kolor kursora/wskaźnika nie zmienia się tak jak powinien. To
      wymaga doprecyzowania ode mnie w czacie, zanim to naprawię —
      pytania czekają w rozmowie.

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
