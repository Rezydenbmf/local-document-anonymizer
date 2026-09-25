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

- [ ] **Okno samej aplikacji miga raz przy starcie (zgłoszone
      2026-09-22, niski priorytet — Twoja własna ocena)** — Twój
      feedback: „nie migaja terminale okno samej aplikacji raz miga -
      ale na tym etapie chyba nie jest to jakis wielki problem".
      Terminale (przyczyna naprawiona poprzednio) już nie migają —
      potwierdzone. To nowe, osobne zjawisko (samo okno GUI, nie
      terminal) zostaje odnotowane, ale świadomie odłożone na Twoją
      prośbę — nie coś, czym zajmuję się teraz.

- [ ] **Sugestie AI — tryb recenzji w oknie porównania (tylko PDF) —
      zbudowane 2026-09-23, gotowe do sprawdzenia NA ŻYWO** — to jest ten
      krok, na który czekały oba checkboxy „AI: …". Ekran w moim
      środowisku jest zablokowany, więc wyglądu nie widziałem: logikę
      sprawdziłem testami (44 nowe) i skryptem uruchamiającym prawdziwe
      okno w tle, ale układ, kolory i czytelność panelu musisz ocenić Ty.
      Potrzebujesz: działającej Ollamy z modelem, zaznaczonego
      przynajmniej jednego „AI: …" i syntetycznego/testowego PDF-a z
      czymś, co automat przepuszcza (np. imię i nazwisko w zdaniu,
      zawód + miejsce pracy). Sprawdź: (1) po anonimizacji otwórz
      porównanie — w pasku tytułu jest przycisk „✨ Sprawdź sugestię AI
      (N)", a u góry panelu bocznego sekcja „Sugestie AI"; (2) kliknij
      przycisk — oba panele przewijają się do właściwego zdania, wokół
      propozycji jest turkusowa przerywana ramka, w panelu: typ
      sugestii, „AI: uzasadnienie", cytat zdania, numer strony, ◀ 1/N ▶;
      (3) „Zatwierdź" na pominiętej danej — pojawia się czarny prostokąt
      z turkusową obwódką, okno samo przechodzi do następnej sugestii;
      (4) „Zmień ręcznie" — narysuj mniejszy prostokąt (np. samo
      nazwisko), sugestia liczy się jako zaakceptowana; (5) sugestia
      „kombinacja danych" — „Zatwierdź" prosi o ręczne zaznaczenie;
      (6) „zbędna redakcja" (jeśli się trafi) — „Zatwierdź" oznacza
      zielonymi ramkami redakcje w tym zdaniu do odznaczenia — sprawdź,
      czy nie łapie redakcji z sąsiedniej linii; (7) „Odrzuć" — ramka
      znika; Ctrl+Z przywraca; „Cofnij decyzję" cofa tylko tę jedną;
      (8) „Zastosuj wszystkie" — najpierw ostrzeżenie „AI może się
      mylić", potem zatwierdza tylko te z gotową ramką; (9) „Zaakceptuj
      edycję" — w podsumowaniu linia „Sugestie AI: zaakceptowane X,
      odrzucone Y"; po zapisie zaakceptowane są turkusowe, zgodnie z
      legendą „sugestia AI zaakceptowana"; zamknij i otwórz okno —
      sugestii już nie ma; (10) **bramka**: przy nierozstrzygniętych
      sugestiach „✓ Zatwierdź" na karcie pliku nie zatwierdza, tylko
      pyta, czy otworzyć porównanie; (11) folder otwarty z Historii
      (oryginał niedostępny) — pytanie „Zatwierdzić mimo to?".
      **Najważniejsze pytanie do Ciebie**: czy przepływ „jak śledzenie
      zmian w Wordzie" jest taki, jak chciałeś, i czy panel 200 px po
      prawej nie jest za ciasny. DOCX/TXT — celowo jeszcze bez sugestii
      (Twoja decyzja: osobną partią).

- [ ] **Usunięta stara, wyszarzona opcja „Dodatkowa weryfikacja AI
      (LLM)" (2026-09-23, na Twoją prośbę)** — to była inna, starsza
      funkcja (jedna ogólna ocena ryzyka całego dokumentu, bez wskazania
      miejsca), całkowicie zastąpiona przez „AI: porównanie
      oryginał/wynik". Sprawdź na żywo (2 minuty): (1) w Ustawieniach →
      zakładka wykrywania nie ma już wyszarzonej pozycji z plakietką
      „wkrótce”, są tylko dwie opcje „AI: …”; (2) to samo w panelu
      szybkich ustawień na ekranie głównym; (3) na liście statusu
      środowiska (tam, gdzie widać Tesseract/NER) pozycja Ollamy nazywa
      się teraz „Lokalny model AI (Ollama)” zamiast mylącego „Dodatkowa
      weryfikacja AI (LLM)”; (4) zwykła anonimizacja PDF-a działa jak
      wcześniej, a raport `_RAPORT.txt` nie ma już sekcji „Local LLM
      review”.

- [ ] **Anonimizacja w tle + licznik czasu + komunikat o AI (2026-09-25,
      Twoje zgłoszenie z testu)** — (1) uruchom anonimizację z włączonym
      AI: animacja ma się ruszać cały czas (ołówek zastąpiony animacją
      ASCII — osobna pozycja niżej), pod nią „Trwa już: N s”,
      niżej informacja, że analiza AI może potrwać kilka minut; okno nie
      może „zamarzać”; (2) w trakcie kliknij Historia / Ustawienia — nic
      nie powinno się stać, dopóki przetwarzanie trwa; (3) po zakończeniu
      otwórz porównanie — jeśli AI nie zgłosiło uwag albo nie zdążyło,
      w panelu bocznym jest ramka „Sugestie AI” z wyjaśnieniem, co się
      stało. Limit czasu na zapytanie do AI podniesiony z 30 s do 15 min.

- [ ] **Sugestie AI bez tekstu modelu + polskie polecenie (2026-09-25,
      Twoja decyzja)** — w panelu „Sugestie AI” nie ma już linii „AI:
      …” z uzasadnieniem modelu, tylko polski tytuł z kategorią (np.
      „Możliwa pominięta dana: osoba”) i cytat zdania z dokumentu.
      Sprawdź, czy bez uzasadnienia wiesz, o co chodzi w sugestii — jeśli
      nie, wymyślimy bezpieczny sposób, żeby to doprecyzować.

- [ ] **Maskotka (detektyw z lupą i markerem) na ekranie przetwarzania —
      zastąpiła animację ASCII (2026-09-25, budowana wspólnie z Tobą w
      czacie, grafika z ChatGPT)** — ten sam mechanizm co poprzednio
      (przycisk „Anuluj”, zamykanie okna, licznik „Dokument N z M”,
      wynik trzyma się na ekranie ok. 1 s) — te zachowania NIE zmieniły
      się i nie trzeba ich sprawdzać od nowa, były już potwierdzone.
      **Nowe do sprawdzenia**: (1) zamiast zamazującego się fikcyjnego
      dokumentu, animowany rysunkowy ludek szuka danych lupą, potem
      zaznacza markerem, w pętli (20 klatek, bez przeskoków rozmiaru ani
      obcych kawałków w kadrze — długo to poprawiałem w czacie, ale
      zawsze warto spojrzeć świeżym okiem); (2) po sukcesie ludek na
      chwilę pokazuje inną pozę — kciuk w górę; (3) przy błędzie/
      anulowaniu ludek zatrzymuje się na pierwszej klatce (bez animacji)
      — czy to czytelne, czy wolisz coś wyraźniejszego (np. czerwoną/
      szarą ramkę wokół); (4) licznik „Dokument N z M” jest teraz osobną
      linijką nad ludkiem, a komunikat („Analiza lokalna w toku”,
      „Anulowanie…” itd.) osobną linijką pod nim — wcześniej oba
      siedziały w jednym polu tekstowym. Poza samym wyglądem: to
      wyłącznie zamiana sposobu rysowania tej samej animacji (ten sam
      mechanizm stanu w kodzie), więc nie oczekuję niespodzianek
      w zachowaniu — ale nigdy tego nie widziałem na żywo, tylko
      w testach i podglądach GIF, które wysyłałem Ci w czacie.

## Znane, jeszcze NIE naprawione (odłożone na Twoją prośbę — wracamy do
   wdrożenia LLM)

- [ ] **Telefon z kropkami jako separatorem nie jest wykrywany** —
      na skanie protokołu (`llm_test_3_skan_protokol_2str.pdf`) numer
      „600.000.528” zostaje w pełni widoczny; wzorzec TELEFON łapie
      spacje/myślniki, ale nie kropki.
- [ ] **Nazwisko rozbite łamaniem wiersza w OCR (np. „Grze-gorz
      Pietrzak”) nie jest wykrywane** — w przeciwieństwie do nazwiska
      złamanego myślnikiem w jednej linii, które działa poprawnie.
      Widoczne na tym samym skanie protokołu, przy podpisie
      przesłuchującego funkcjonariusza.

Oba powyżej odłożone świadomie 2026-09-25 (Twoja decyzja: „ogólnie
pamiętaj że teraz duże wdrożenie tego LLM mamy dokończyć") — nie
naprawiane teraz, tylko odnotowane do zaplanowania później.

## Potwierdzone

- [x] **Zakres stron per plik (checkbox + szara podpowiedź „X z X
      stron”)** (potwierdzone 2026-09-25) — Twój feedback: „ad 7 działa”.
- [x] **Usuwanie podpisu elektronicznego z okna podglądu** (potwierdzone
      2026-09-25) — Twój feedback: „ad 8 działa”.
- [x] **Foldery wynikowe wg daty + podfolder `txt`** (potwierdzone
      2026-09-25) — Twój feedback: „ad 9 działa”.
- [x] **Ustawienia: checkboxy AI synchronizują się z ekranem głównym +
      wybór modelu AI** (potwierdzone 2026-09-25) — Twój feedback:
      „ad 2 działa”.
- [x] **System testów: wzorce i klucz odpowiedzi** (potwierdzone
      2026-09-25) — Twój feedback: „reszta wydaje się ok”; zasady oceny
      (daty dokumentów, numery faktur/umów, opisowe adresy, nazwy urzędów
      jako „obojętne”, znak sprawy jak sygnatura) zostają. Jedyna uwaga:
      w ciasnym bloku (opinia lekarska, notatka z wizyty) czarny
      prostokąt na wzorcu nachodzi na szare pola linii obok — to tylko
      rysunek wzorca (linie są celowo ciaśniej niż wysokość liter);
      ocena liczy środek każdej litery osobno, więc wynik jest poprawny.

- [x] **Redakcja nie zjada już tekstu z sąsiedniej linii + słowo
      w polskim cudzysłowie zamazane** (potwierdzone 2026-09-25, zrzutem
      z żywego okna porównania na `llm_test_2`) — Twój feedback: „tym
      razem nie zanonimizowało tego ciasnego fragmentu, czyli poprawka
      działa". Na zrzucie też „Lipami” w „Przychodnia pod Lipami”
      zamazane. Otwarte do klucza testów: sygnatury akt i „PWZ 1234567”
      widoczne; „Zagórze Wąskie” zamazane tylko w połowie („Wąskie”
      widoczne).
- [x] **AI włączone z ekranu głównego samo dobiera model** (potwierdzone
      2026-09-25, ten sam przebieg) — plik wyniku AI: gemma3:4b, obie
      analizy „completed”, 7 pominiętych danych + 4 kombinacje = 11
      sugestii. Twoje pytanie „11 u góry, a Zastosuj wszystkie (7)”:
      kombinacje wymagają ręcznego zaznaczenia, więc „Zastosuj wszystkie”
      ich nie obejmuje — do poprawienia opisu przycisku w nowym
      przepływie recenzji.

- [x] **Skany: akapity nie sklejają się już w jedną linię** (potwierdzone
      2026-09-25, zrzutem ekranu z żywego okna porównania na
      `llm_test_3_skan_protokol_2str.pdf`) — telefon „+48 600 000 519”
      w pełni zamazany w jednym pasku, żadna ramka nie obejmuje już
      kilku linii naraz.
- [x] **Skan formularza: numer domu w tabeli nie zostaje już odkryty**
      (potwierdzone 2026-09-25, zrzutem ekranu z żywego okna porównania
      na `skan-do-testow-poz-4.pdf`) — cały wiersz „Adres Ogrodowa 22”
      zamazany jednym paskiem, wiersz „NIP” też w pełni zamazany
      (wcześniej widoczny bez żadnej redakcji).
- [x] **Miganie okien terminala przy starcie — naprawione** (potwierdzone
      2026-09-22) — Twój feedback: „nie migaja terminale".
- [x] **„Eksportuj zatwierdzone” kopiuje i otwiera właściwy PDF**
      (potwierdzone 2026-09-22) — Twój feedback: „dziala - zatwierdzam".
- [x] **Ostrzeżenie o zakresie stron spoza dokumentu — widoczne na
      ekranie wyników** (potwierdzone 2026-09-22, zrzutem ekranu) —
      Twój feedback: „traci na znaczeniu ze wzgledu na nowe podejscie,
      ale jest komunikat". Sam mechanizm ostrzegania działa; zostanie
      zastąpiony nowym podejściem per-plik opisanym wyżej w „W trakcie”.

- [x] **Ustawienia — wolne ładowanie naprawione** (potwierdzone
      2026-09-20) — Twój feedback: „ustawienie dzialaja juz dobrze".
- [x] **Etap 7 — usuwanie podpisów elektronicznych z PDF-a: usuwanie
      naprawdę działa** (potwierdzone 2026-09-20) — Twój feedback:
      „usuwanie podpisu jak rozumiem dziala bo zniklo to pomarańczowe
      pole sign", potwierdzone przeze mnie bezpośrednio w przesłanym
      pliku (0 pól podpisu, plik przestał być formularzem PDF).
      **Wciąż otwarte**: prośba o wygodę (usuwanie z poziomu okna
      podglądu) — patrz „W trakcie” wyżej.
- [x] **Wersjonowanie wyboru kategorii w pliku JSON — nie wymaga
      osobnego testu z Twojej strony** (2026-09-20) — Twój feedback:
      „z jsopne to nie czaje w ogóle co mam sprawdzić". Masz rację, że
      to było niejasne — bo w praktyce **nie da się tego przetestować
      przez samo klikanie w apce**: to zabezpieczenie chroni przed
      sytuacją, która mogłaby wystąpić tylko po **aktualizacji kodu**
      apki między dwoma anonimizacjami tego samego dokumentu (np. gdy ja
      zmienię, co dokładnie oznacza dana kategoria) — nie da się tego
      wywołać z poziomu samego interfejsu. Pilnują tego automatyczne
      testy w kodzie (uruchamiane przy każdej zmianie), nie Ty na żywo.
      Zdejmuję to z Twojej listy na stałe — to była moja pomyłka, że w
      ogóle prosiłem Cię o to sprawdzenie.
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
