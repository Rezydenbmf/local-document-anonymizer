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

- [ ] **Etap 7 — usuwanie podpisów elektronicznych z PDF-a, osobna
      opcja, domyślnie WYŁĄCZONA (2026-09-18).** Realny przypadek z
      Twoich notatek: dokument z podpisem elektronicznym, którego
      wizualnej „ramki” (imię i nazwisko podpisującego) nasz mechanizm
      w ogóle nie widział — bo to nie jest zwykły tekst na stronie,
      tylko osobny obiekt formularza PDF (pole podpisu). Twój feedback
      po pierwszej wersji: „usuwanie podpisu to osobna opcja - nie
      dziala automatycznie” — zrobione. W panelu „Kategorie do
      anonimizacji” pojawiło się nowe, osobno oznaczone (żółta ramka,
      inna niż reszta) pole „Usuń podpisy elektroniczne (PDF)” —
      **domyślnie odznaczone**, nic nie usuwa dopóki sam go nie
      zaznaczysz dla konkretnego zadania. Code-review złapał i
      naprawiłem po drodze realny błąd: pierwsza wersja psuła się
      (program się wywalał) na dokumencie podpisanym przez dwie osoby
      na tej samej stronie — naprawione, przetestowane bezpośrednio na
      takim przypadku. Sprawdź na żywo: (1) domyślnie, bez zaznaczania
      niczego, podpis w PDF-ie ma zostać nietknięty po anonimizacji;
      (2) po zaznaczeniu pola i ponownej anonimizacji tego samego
      dokumentu podpis (razem z widoczną „ramką”) ma zniknąć; (3) dymek
      po najechaniu na pole powinien jasno tłumaczyć, że to nieodwracalne.

      **Twoja uwaga po teście (2026-09-18)**: „czy nie mozemy dac opcji
      usun podpis na oknie podgladu? bo tak troche na okolo ze trzba od
      poczatku anonimizowac i zaznaczyc podpis - mniej wygodnie”. To
      rozsądna prośba o wygodę, ale **jeszcze niezrobiona w tej turze** —
      dziś rzeczywiście trzeba zaznaczyć pole przed pierwszym
      uruchomieniem anonimizacji; nie da się dodać usuwania podpisu z
      poziomu okna porównania/magic pena bez ponownego przetworzenia
      całego dokumentu od zera. Jest to technicznie wykonalne (mechanizm
      "zamrożonego wyboru" już działa dla zakresu stron i kategorii),
      ale to osobny kawałek pracy — powiedz, czy mam się tym zająć w
      następnej kolejności.

- [ ] **Ustawienia ładowały się 3-5 sekund po powrocie z okna podglądu
      (zgłoszone 2026-09-18, przyczyna znaleziona i naprawiona)** —
      Twój feedback: „odkrylem ze jak mam okno podgladu wracam do
      glownego i wlaczam ustawienia, to strasznie dlugo sie laduja (3-5
      SEK)". Przyczyna: okno Ustawień za każdym otwarciem od nowa
      pytało silnik OCR (Tesseract) o listę zainstalowanych języków —
      osobny, realny proces uruchamiany na nowo przy każdym kliknięciu
      w Ustawienia, mimo że ta sama informacja jest już policzona raz
      przy starcie aplikacji. Naprawione: wynik jest teraz zapamiętywany
      po pierwszym otwarciu Ustawień w danej sesji i tylko odświeżany na
      świeżo po realnym dograniu nowego pakietu językowego. Sprawdź na
      żywo: otwórz Ustawienia dwa razy pod rząd (najlepiej po powrocie z
      okna podglądu, tak jak zgłosiłeś) — drugie i kolejne otwarcie
      powinno być zauważalnie szybsze niż pierwsze.

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

- [ ] **Ograniczenie automatycznej anonimizacji PDF-a do wybranych stron
      (Etap 5) — ostrzeżenie o zakresie spoza dokumentu (ad7 z
      2026-09-18, zgłoszone jako niedziałające — przyczyna znaleziona i
      naprawiona 2026-09-18)** — Twój test: 3-stronicowy dokument,
      zakres „6-7”, „mnie puściło” (bez żadnego ostrzeżenia). Sprawdziłem
      bezpośrednio w kodzie: ostrzeżenie **technicznie już wtedy
      powstawało** poprawnie, ale trafiało tylko do ukrytego pliku
      wewnętrznego (`_wewnetrzne/..._RAPORT.txt` / `_BATCH_SUMMARY.txt`)
      — miejsca, do którego normalnie nikt nie zagląda. Poza tym w
      poprzedniej instrukcji podałem Ci zresztą złą nazwę pliku do
      szukania (`_ANON_raport_deweloperski.txt` — taki plik w ogóle nie
      istnieje), więc nawet ktoś, kto by szukał, by go nie znalazł. To
      był realny błąd UX, nie tylko pomyłka w opisie — samo ostrzeżenie
      było praktycznie niewidoczne. Naprawione: po przetworzeniu wsadu
      na ekranie „Wyniki anonimizacji” pojawia się teraz żółta karta z
      ostrzeżeniem wprost na liście plików (ten sam styl co istniejąca
      czerwona karta „Nie udało się przetworzyć..."), więc nie trzeba
      niczego szukać w ukrytych folderach. Sprawdź na żywo: wczytaj
      `6_umowa_trzy_strony.pdf`, wpisz w polu „Strony” zakres spoza
      dokumentu (np. „6-7”), zanonimizuj — na ekranie wyników powinna od
      razu pojawić się żółta karta ostrzeżenia z nazwą pliku i treścią
      mówiącą, że podany zakres nie pasuje do żadnej strony dokumentu.
      **Nadal do sprawdzenia z poprzedniej tury** (nie testowane w tej
      rundzie): dymek po najechaniu na pole „Strony” — czy jasno
      tłumaczy format (przecinek/myślnik/kombinacja).
      **Wciąż otwarte, świadomie odłożone**: zmiana zakresu stron już w
      trakcie pracy w edytorze magic pen (dziś trzeba ustawić zakres
      przed uruchomieniem anonimizacji, nie da się go zmienić bez
      ponownego przetworzenia całego dokumentu).

## Potwierdzone

- [x] **Magic pen — nowy system trybów interakcji myszy (Etap 3)**
      (potwierdzone 2026-09-18) — Twój feedback: „wszystkie tryby
      magicc pena dzialaj". Podczas tego testu znalazłeś osobny,
      niezwiązany problem (Ustawienia ładujące się 3-5 sek) — opisany
      wyżej w „Do sprawdzenia".
- [x] **Kategorie do anonimizacji — czytelność etykiet checkboxów**
      (potwierdzone 2026-09-18) — Twój feedback: „ad 4 - wszystko ok,
      zatwierdzam".
- [x] **Etykieta pola (np. „Adres") już nie znika z tabelarycznych
      dokumentów** (potwierdzone 2026-09-18) — Twój feedback: „ad 5
      dziala".
- [x] **NIP/REGON wykrywane, gdy etykieta i wartość są w osobnych
      komórkach tabeli** (potwierdzone 2026-09-18) — Twój feedback:
      „ad 6 dziala" (potwierdzone też zrzutem z żywego okna porównania:
      `2_faktura_vat.pdf`, obie nazwy firm, NIP i REGON w pełni
      zamazane).
- [x] **Ogólna jakość wykrywania przez AI poprawiona — nie tylko nazwy
      firm z formą prawną** (2026-09-18, potwierdzone 2026-09-18) —
      Twój feedback: „tyak zatwierdzam" (po zrzucie z żywego okna
      porównania: `2_faktura_vat.pdf` z obiema nazwami firm w pełni
      zamazanymi, NIP/REGON zniknięte). Przyczyna była w mechanizmie
      AI sklejającym nazwisko rozdzielone łamaniem wiersza w PDF-ie,
      który przypadkiem sklejał też niepowiązane słowa z sąsiednich
      wierszy/komórek tabeli w jeden fałszywy twór, odrzucany potem w
      całości razem z prawdziwą nazwą firmy czy miejscowości.
      Naprawione przebudową mechanizmu (dwuprzebiegowa analiza) —
      dotyczy nie tylko nazw firm, ale też lokalizacji i innych
      kategorii wykrywanych przez AI.
- [x] **Nazwisko z myślnikiem w PDF-ie już nie znika w całości**
      (2026-09-18, potwierdzone 2026-09-18) — Twój feedback: „tyak
      zatwierdzam" (po zrzucie z żywego okna porównania:
      `5_pismo_nazwisko_dwa_wiersze.pdf`, oba wystąpienia „Bartlomiej
      Zaremba-Wojciechowski" w pełni zamazane, nie tylko drugie w
      podpisie jak wcześniej). Przyczyna: PDF traktuje
      „Zaremba-Wojciechowski" (bez spacji wokół myślnika) jako jedno
      słowo, a mechanizm rysujący ramki odrzucał całe dopasowanie, gdy
      AI wskazało tylko część słowa — całe nazwisko zostawało bez
      żadnej ochrony. Naprawione rozszerzaniem zaznaczenia na całe
      słowo w takim przypadku.
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
