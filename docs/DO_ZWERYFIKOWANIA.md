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
- [ ] **Wybór kategorii do anonimizacji per zadanie (Etap 4, 2026-09-16,
      zaktualizowane 2026-09-17 po Twoim teście)** — 8 checkboxów w
      „Szybkie akcje" (PESEL, imię i nazwisko/AI, telefon, e-mail, IBAN,
      adres, dane firmy, data), wszystkie domyślnie zaznaczone.
      **Znaleziony realny błąd, na żywo, ze screenshotami:** odznaczyłeś
      wszystko poza PESEL, a program dalej anonimizował nazwę firmy i
      fragmenty adresu. Przyczyna: „Adres"/„Dane firmy" kontrolowały
      tylko pola wykryte regexem (NIP/REGON, ulica/miejscowość/kod
      pocztowy) — nazwy firm i lokalizacje wykryte przez AI były zawsze
      włączone, niezależnie od checkboxów. Naprawione: „Adres" i „Dane
      firmy" teraz wyłączają też odpowiadające im dane wykryte przez AI.
      Reszta (dowód osobisty, nietypowe nazwiska, pozostałe dane
      wykryte przez AI, własny słownik, ręczne magic-pen) nadal zawsze
      się anonimizuje. **Sprawdź dokładnie ten sam scenariusz co
      ostatnio**: odznacz wszystko poza PESEL na dokumencie z nazwą
      firmy i adresem (np. faktura VAT) — nazwa firmy i adres powinny
      teraz zostać widoczne, tylko PESEL zanonimizowany.

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

- [ ] **Uruchamianie bez widocznej konsoli (2026-09-17)** — `uruchom.vbs`
      zastępuje `uruchom.bat` do codziennego użytku: uruchamia apkę przez
      `pythonw.exe` bez żadnego okienka terminala w tle. `uruchom.bat`
      zostaje, ale tylko do debugowania (pokazuje konsolę). Sprawdź: czy
      dwuklik na `uruchom.vbs` faktycznie pokazuje tylko interfejs apki,
      bez żadnego mignięcia czarnego okna; i (trudniejsze do
      zasymulowania) czy w razie realnego błędu startowego plik
      `%USERPROFILE%\.anonimizer\ostatni_blad.log` faktycznie się pojawia
      z sensowną treścią zamiast apka po prostu nie startowała bez śladu.

- [ ] **Magic pen — czytelność trybu interakcji myszy (2026-09-17)** —
      odpowiedź na feedback „graficznie nie widać co się robi": 3 kolorowe
      plakietki z ikonką zamiast jednego szarego napisu (LPM/PPM/ŚPM +
      ikonka akcji), strzałki Cofnij/Ponów teraz kolorują się na
      niebiesko gdy faktycznie klikalne (wcześniej zawsze wyglądały tak
      samo szaro), kursor nad dokumentem odzwierciedla co zrobi LPM w
      spoczynku i zmienia się na żywo w trakcie trzymania innego
      przycisku, nowa ikonka ⚙ w oknie porównania otwiera Ustawienia >
      Ogólne bez zamykania podglądu, a sekcja trybu w Ustawieniach ma
      teraz wyróżnioną ramkę + ikonkę 🖱, żeby nie zlewała się z resztą.
      Sprawdź na żywo: czy plakietki i kolor strzałek faktycznie rzucają
      się w oczy bez tłumaczenia, czy zmiana trybu przez nową ikonkę ⚙ w
      oknie porównania działa i od razu widać efekt bez zamykania okna,
      i czy kursor nad dokumentem faktycznie wygląda inaczej dla
      zaznaczania/odznaczania/przesuwania.

- [ ] **Kategorie do anonimizacji — przeniesione na górę panelu
      (2026-09-17)** — odpowiedź na „nie wiem jak mam zaznaczać
      odznaczać w GUI to": 8 checkboxów z Etapu 4 przeniesione z dołu
      panelu „Szybkie akcje" na sam początek, zaraz pod nagłówkiem, w
      wyróżnionej ramce. Przy okazji naprawione: legenda kolorów w
      oknie porównania mogła się ucinać przy zmniejszeniu okna (teraz
      przewijalna). Sprawdź: czy checkboxy kategorii faktycznie rzucają
      się w oczy od razu po otwarciu panelu, bez przewijania w dół; i
      czy legenda kolorów w oknie porównania nie ucina się już przy
      zmniejszaniu okna.

- [ ] **„Wyczyść historię" usuwa też wpis z listy (2026-09-17, zaktualizowane
      po Twoim teście z 2026-09-17)** — odpowiedź na „foldery zostają, po co
      tam cała lista". Wybrane zachowanie (potwierdzone przez Ciebie): folder
      znika z listy Historia, gdy nie zostaje w nim już nic, co ta apka
      rozpoznaje jako swój plik — sam folder na dysku zostaje nietknięty.
      **Doszedł drugi, powiązany błąd, który złapałeś na żywo ze
      screenshotem** — dwa stare foldery („Anonimizer - wyniki",
      „070926") pokazywały „folder nie istnieje" i nie znikały z listy
      mimo klikania „Wyczyść historię". Przyczyna: te foldery zostały
      skasowane spoza apki (np. przez Eksplorator) — stary kod w ogóle
      pomijał foldery, które już nie istnieją na dysku, więc nigdy nie
      miały szansy zniknąć z listy. Naprawione w `src/gui_app.py`
      (`clean_history`): taki wpis znika z listy Historia teraz zawsze,
      przy każdym kliknięciu „Wyczyść historię", niezależnie od tego, czy
      coś innego zostało tego dnia skasowane. Sprawdź na żywo: czy oba
      foldery ze screenshota faktycznie znikają z listy po kliknięciu
      „Wyczyść historię"; i normalny przypadek — folder z plikami
      roboczymi i finalnymi powinien zniknąć z listy (ale nie z dysku)
      dopiero gdy nie zostanie w nim nic, co ta apka rozpoznaje jako swój
      plik.

- [ ] **Status recenzji nie „pamięta” już starego odrzucenia po ponownym
      przetworzeniu (2026-09-17)** — znalazłeś na żywo ze screenshotem:
      odrzuciłeś plik, usunąłeś go, wgrałeś ten sam dokument źródłowy i
      zanonimizowałeś ponownie — nowy plik (ta sama nazwa) dalej
      pokazywał „odrzucony", mimo że nigdy go nie widziałeś. Przyczyna:
      status recenzji zapisywany był po nazwie pliku, bez sprawdzania,
      czy to ten sam plik czy nowy o tej samej nazwie. Naprawione w
      `restrict_review_items_to_batch` — świeżo przetworzony plik zawsze
      zaczyna od „wymaga przeglądu", nigdy nie dziedziczy starego
      statusu. Sprawdź: powtórz dokładnie ten scenariusz (odrzuć,
      usuń, wgraj to samo źródło, zanonimizuj) — nowy plik powinien
      pokazać „wymaga przeglądu", nie „odrzucony".

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
      pokazujące „folder nie istnieje"), to osobny błąd, opisany i
      naprawiony w pozycji „Wyczyść historię usuwa też wpis z listy"
      poniżej.
- [x] **Cache'owanie detekcji w oknie porównania (Etap 2, 2026-09-16)**
      (potwierdzone 2026-09-17) — Twój feedback: „tak potwierdzam".
