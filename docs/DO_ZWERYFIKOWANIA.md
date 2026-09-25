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

- [ ] **Zakres stron per plik — przebudowane po Twoim live feedbacku
      (2026-09-22, gotowe do ponownego sprawdzenia)** — zgłosiłeś, że
      dymek podpowiedzi się ucinał (nieczytelny) i że pole w ogóle nie
      pokazywało żadnej podpowiedzi liczby stron. Drugie okazało się
      prawdziwym błędem, nie tylko brakiem: biblioteka GUI (customtkinter)
      ma błąd, przez który wbudowana „szara podpowiedź" pola tekstowego
      nigdy się nie aktywuje, gdy pole jest jednocześnie powiązane
      z żywą walidacją (a takie jest to pole od początku) — więc ta
      podpowiedź nigdy realnie nie działała, nawet zanim to przebudowałem.
      Naprawione własną, ręczną implementacją tego mechanizmu. Przy okazji,
      zgodnie z Twoimi uwagami: (a) dymek podpowiedzi łamie się teraz na
      kilka linii zamiast urywać; (b) pole samo w sobie od razu pokazuje
      szarym tekstem efektywny zakres, np. „3 z 3 stron” albo „1 z 1
      strony” (nie przykład, tylko prawdziwą wartość dla tego pliku);
      (c) pole jest domyślnie zablokowane (szare), aktywuje się dopiero
      po zaznaczeniu małego checkboxa obok (bez podpisu przy nim — najedź
      myszką, żeby zobaczyć „Ręczne oznaczenie stron do anonimizacji”);
      (d) pole zwężone, a cały układ przesunięty bliżej prawej krawędzi,
      żeby było więcej miejsca na nazwę pliku. Sprawdź na żywo: (1)
      wrzuć kilka PDF-ów o różnej liczbie stron — każdy pokazuje od razu
      poprawną szarą podpowiedź „X z X stron”, pole jest zablokowane;
      (2) zaznacz checkbox przy jednym pliku — pole się odblokowuje,
      podpowiedź nadal widoczna, aż zaczniesz pisać; (3) wpisz zakres
      spoza dokumentu (np. „99” na 3-stronicowym pliku) — obramowanie
      od razu robi się czerwone; (4) odznacz checkbox — pole wraca
      zablokowane z podpowiedzią „cały dokument”, żaden wpisany wcześniej
      zakres nie zostaje; (5) uruchom anonimizację z ręcznym zakresem na
      jednym pliku, a drugi zostaw bez zaznaczenia — pierwszy ma zamazane
      tylko wybrane strony, drugi cały dokument.

- [ ] **Okno samej aplikacji miga raz przy starcie (zgłoszone
      2026-09-22, niski priorytet — Twoja własna ocena)** — Twój
      feedback: „nie migaja terminale okno samej aplikacji raz miga -
      ale na tym etapie chyba nie jest to jakis wielki problem".
      Terminale (przyczyna naprawiona poprzednio) już nie migają —
      potwierdzone. To nowe, osobne zjawisko (samo okno GUI, nie
      terminal) zostaje odnotowane, ale świadomie odłożone na Twoją
      prośbę — nie coś, czym zajmuję się teraz.

- [ ] **Usuwanie podpisu elektronicznego z poziomu okna podglądu
      (magic pen) — zbudowane 2026-09-22, gotowe do sprawdzenia** —
      punkt 2 z Twojej decyzji „to robimy 1 i 2 a potem na ten tydzien
      zaczynamy z llm-em". W panelu bocznym „Korekta anonimizacji"
      (obok kategorii danych) pojawia się teraz osobny, żółty checkbox
      „Usuń podpisy elektroniczne" — ale **tylko** dla dokumentów,
      których oryginał faktycznie ma pole podpisu elektronicznego w
      zasięgu wybranego wcześniej zakresu stron (dla reszty checkbox
      się w ogóle nie pojawia, żeby nie zaśmiecać panelu). Zmiana tego
      wyboru sama w sobie liczy się jako „niezapisana zmiana" — przycisk
      „Zaakceptuj edycję" aktywuje się nawet bez żadnego ręcznego
      zaznaczenia. Sprawdź na żywo: (1) otwórz w oknie porównania
      dokument z prawdziwym podpisem elektronicznym — checkbox powinien
      się pojawić, odznaczony lub zaznaczony zgodnie z tym, co wybrałeś
      przed anonimizacją; (2) otwórz dokument bez podpisu — checkboxa
      nie powinno być w ogóle; (3) zaznacz/odznacz checkbox bez żadnej
      innej edycji i kliknij „Zaakceptuj edycję" — PDF powinien się
      przebudować z (lub bez) polem podpisu, zgodnie z nowym wyborem;
      (4) zamknij i otwórz okno ponownie dla tego samego pliku —
      checkbox ma pokazywać już zapisany wybór, nie domyślny; (5)
      zaznacz checkbox i kliknij „Anuluj" zamiast zapisywać — wybór ma
      wrócić do poprzedniego stanu.

- [ ] **Foldery wynikowe wg daty + rozdzielenie PDF/TXT — zbudowane
      2026-09-22, gotowe do sprawdzenia** — Twoje zgłoszenie: folder
      „approved" (nigdy nie czyszczony, bo traktujesz go jak własną bazę)
      zbierał bałagan — PDF plus dwa pliki TXT (wynik i raport) na
      dokument, bez porządku. Teraz: **w obu miejscach** (folder wyników
      i „approved") każdy dzień anonimizacji dostaje własny podfolder w
      formacie `DD.MM.RRRR`, a wewnątrz niego podfolder `txt` — PDF-y
      zostają bezpośrednio w folderze daty, wszystkie pliki TXT
      (wynikowe i raporty) trafiają do `txt`. Kilka osobnych anonimizacji
      tego samego dnia trafia do jednego folderu daty. „Wyczyść
      historię" w folderze wyników nadal kasuje wszystko, łącznie z tymi
      podfolderami; „approved" zostaje nietykalny jak dziś. Stare,
      istniejące już wyniki w płaskiej strukturze **zostają nietknięte**
      — apka rozpoznaje oba układy naraz, bez żadnej migracji. Przy
      okazji poprawiony też prawdziwy błąd, który złapałaby dopiero Twoja
      własna próba: otwarcie starszego folderu z historii pokazywało
      pusty ekran „Brak plików", mimo że wyniki tam realnie są — teraz
      apka sama trafia do najnowszego podfolderu daty. Sprawdź na żywo:
      (1) uruchom dwie osobne anonimizacje tego samego dnia — oba
      trafiają do jednego `DD.MM.RRRR`, PDF-y bezpośrednio w nim, pliki
      TXT w `txt/`; (2) ekran recenzji po anonimizacji pokazuje wszystkie
      pliki normalnie (i PDF-owe, i czysto tekstowe źródła); (3) zamknij
      apkę i otwórz ją ponownie, potem w Historii kliknij folder, w
      którym coś anonimizowałeś wcześniej — ekran recenzji ma pokazać
      wyniki, nie „Brak plików"; (4) zatwierdź plik i wyeksportuj do
      folderu „approved" (nowego albo tego, którego już używasz) —
      sprawdź, że tam też powstaje podfolder `DD.MM.RRRR` z PDF-em w
      środku i `txt/` z plikiem wynikowym i raportem; (5) „Wyczyść
      historię" na folderze wyników z nowymi podfolderami dat — ma
      usunąć wszystko tak jak dotychczas na starym, płaskim folderze.

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

- [ ] **Ustawienia: checkboxy AI synchronizują się z ekranem głównym +
      wybór modelu AI (2026-09-25, Twoje zgłoszenie z testu)** — (1)
      włącz oba „AI: …” w Ustawieniach, zapisz — na ekranie głównym oba
      checkboxy mają być zaznaczone (i odwrotnie przy wyłączeniu); (2)
      w Ustawieniach → wykrywanie, pod dwoma opcjami „AI: …”, jest nowa
      sekcja „Model AI (Ollama)” z listą zainstalowanych modeli — wybierz
      Bielika, zapisz, otwórz Ustawienia ponownie: wybór ma zostać.
      Uwaga: ustawienia nadal obowiązują tylko do zamknięcia apki (tak
      było zawsze) — po ponownym uruchomieniu AI jest wyłączone.

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

- [ ] **System testów: wzorce i klucz odpowiedzi (2026-09-25, etap 2
      planu)** — wygeneruj korpus (`.venv\Scripts\python.exe -m
      benchmark.generate`) i otwórz kilka plików `*_WZORZEC.pdf`
      w `benchmark\corpus\` (tylko u Ciebie na dysku, nigdy na GitHubie).
      Czarne = musi być zamazane, szare = obojętne, zielona ramka = ma
      zostać widoczne. Sprawdź, czy **tak chcesz** oceniać: szczególnie
      (1) daty dokumentów (data wizyty, wystawienia faktury) jako
      „obojętne”; (2) numery umów/faktur/próbek jako „obojętne”;
      (3) opisowe adresy („żółty dom obok apteki”) i cechy typu „jedyna
      sokolniczka w powiecie” jako „obojętne” — łapać je ma dopiero AI;
      (4) nazwy urzędów/sądów („Sądem Rejonowym”, „Urzędem Skarbowym”)
      jako „obojętne”, ale miejscowość w ich nazwie — „musi”; (5) znak
      sprawy urzędowej („GK.6220.14.2026”) potraktowany jak sygnatura
      akt (czyli opcjonalna kategoria). Każdą z tych decyzji zmieniam
      jedną linią w `benchmark\policy.json`, bez generowania od nowa.

- [ ] **Animacja ASCII na ekranie przetwarzania + przycisk „Anuluj”
      (2026-09-25, Twój prototyp)** — ekran „w trakcie” pokazuje teraz
      ramkę z fikcyjnym dokumentem (JAN KOWALSKI, PESEL…), który zamazuje
      się linijka po linijce, i napis „Dokument 1 z 3”. Świadome zmiany
      wobec starego ekranu — oceń, czy tak chcesz: (a) **zniknął pasek
      postępu** — i tak nie mierzył postępu, tylko numer pliku; (b)
      **zniknęła nazwa pliku** pod paskiem — animacja nie pokazuje nazw
      ani ścieżek, zgodnie z Twoim wymaganiem; (c) wynik końcowy zostaje
      na ekranie ok. 1 s (zielony = sukces, czerwony = błąd, szary =
      anulowano), potem apka przechodzi dalej; (d) przy błędzie
      i anulowaniu fikcyjne dane w ramce zostają **niezamazane** — tak
      zachowuje się Twój prototyp („nie zanonimizowano”); jeśli wolisz
      inaczej, to jedna linijka. Sprawdź na żywo: (1) jeden plik; (2)
      trzy pliki — numer rośnie 1→2→3; (3) „Anuluj” w trakcie pierwszego
      z kilku plików — przycisk zmienia się na „Anulowanie...”, **bieżący
      plik kończy się normalnie** (przy AI może to trwać minuty — nie da
      się przerwać pliku w połowie bez ruszania silnika), potem powrót na
      ekran główny z napisem „Anulowano po 1 z 3 dokumentów”; (4)
      zamknięcie okna krzyżykiem w trakcie — pyta „Anonimizacja trwa…
      Zamknąć mimo to?”, „Nie” = nic się nie dzieje, „Tak” = zamyka.
      Przy zamknięciu bieżący plik jest przerywany w połowie — jego wynik
      w folderze może być niepełny (tak było też wcześniej, tylko bez
      pytania).

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
