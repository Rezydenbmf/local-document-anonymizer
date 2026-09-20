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

- [ ] **Miganie 2-3 okien terminala kilka sekund po starcie apki
      (zgłoszone 2026-09-20, przyczyna znaleziona i naprawiona)** —
      Twój feedback: „po 2-3 sek migaja jakies 2-3 okna terminala...
      juz chce cos kliknac a tu nagle mryga okno terminala". Przyczyna:
      apka zaraz po starcie w tle sprawdza dostępność Tesseracta,
      aktualizacji bibliotek i modelu AI — każde z tych sprawdzeń
      uruchamia osobny, krótki proces w tle, a żaden z nich (łącznie z
      wbudowaną biblioteką do obsługi OCR, której kodu nie edytujemy)
      nie mówił Windowsowi „nie pokazuj dla mnie okna" — stąd te
      błyski. Naprawione dla wszystkich takich procesów naraz, w jednym
      miejscu (nie osobno dla każdego sprawdzenia). Sprawdź na żywo:
      uruchom apkę na czysto i obserwuj pierwsze kilka sekund — okna
      terminala nie powinny się już pojawiać wcale. Pasek postępu/
      informacja „apka się jeszcze ładuje” to osobny, dodatkowy pomysł
      z Twojej wiadomości — nie zrobiłem go w tej turze (naprawa okien
      terminala powinna już wystarczyć, ale daj znać, jeśli nadal wolisz
      jawny wskaźnik ładowania).

- [ ] **„Eksportuj zatwierdzone” — głębszy problem niż wybór folderu:
      wizualny PDF w ogóle nie był kopiowany (zgłoszone 2026-09-20,
      poprzednia poprawka niewystarczająca, prawdziwa przyczyna
      znaleziona i naprawiona)** — pierwsza poprawka (otwieranie pliku
      z nowego folderu) naprawiła *który folder*, ale Twój kolejny test
      pokazał, że otwiera się TXT zamiast PDF-a. Kopanie głębiej
      pokazało prawdziwy problem: eksport **nigdy w ogóle nie kopiował**
      kolorowego, zamazanego PDF-a do wybranego folderu — kopiował
      tylko sam plik tekstowy (`_ANON.txt`) i raport, nawet gdy
      oryginałem był PDF. To działało tak od zawsze, nie coś, co
      zepsuła poprzednia poprawka. Naprawione: eksport teraz kopiuje
      też towarzyszący plik `_ANON_VISUAL.pdf`, jeśli istnieje, i to
      właśnie jego otwiera po zakończeniu. Sprawdź na żywo: zatwierdź
      jeden plik pochodzący z PDF-a, kliknij „Eksportuj zatwierdzone”,
      wybierz folder — w tym folderze powinien wylądować zarówno plik
      `_ANON.txt`, jak i `_ANON_VISUAL.pdf`, a po eksporcie powinien się
      otworzyć ten drugi (kolorowy PDF), nie plik tekstowy.

- [ ] **Ograniczenie anonimizacji do wybranych stron — NOWA strategia
      UX zamiast obecnego pola „Strony” (zgłoszone 2026-09-20, jeszcze
      NIE zaplanowane ani rozpoczęte)** — obecne ostrzeżenie o zakresie
      spoza dokumentu już działa (potwierdziłeś to zrzutem ekranu —
      przenoszę do „Potwierdzone”), ale zgłosiłeś, że chcesz zmienić
      całe podejście: zamiast jednego wspólnego pola „Strony” dla
      całego wsadu, chcesz kontrolkę **przy każdym pliku z osobna** (na
      liście wybranych plików, obok nazwy), z domyślnym „wszystkie
      strony”, i z **walidacją opartą o rzeczywistą liczbę stron danego
      pliku** wczytaną zaraz po przeciągnięciu go do apki (żeby nie dało
      się wpisać strony, której dokument w ogóle nie ma). To osobny,
      spory kawałek pracy architektonicznej — opisany dokładniej niżej w
      „Do zaplanowania”, nie coś, co już zrobiłem.

## Do zaplanowania (dwie prośby, jeszcze nierozpoczęte — czekają na Twoje
„tak, zaczynamy”)

- **Nowa strategia zakresu stron, per plik.** Twój opis (2026-09-20):
  kontrolka przy nazwie każdego pliku zamiast jednego wspólnego pola
  „Strony”; domyślnie cały dokument; zakres wpisywany jako numer-myślnik-
  numer, kilka zakresów/stron oddzielonych przecinkami (np. „1-2, 4-7”
  albo „3,6,9,11” — dokładnie ta sama składnia co dziś, więc to się nie
  zmienia); apka po wczytaniu pliku (drag&drop) ma znać jego rzeczywistą
  liczbę stron i nie pozwalać wpisać nic spoza niej. To realna zmiana
  architektury — dziś jeden zakres stron dotyczy całego wsadu naraz, a
  to by znaczyło osobny zakres na plik, plus odczyt liczby stron w
  momencie wczytania (nie dopiero przy anonimizacji). Zanim zacznę
  kodować, wolę to porządnie zaplanować (tak jak przy Etapie 5) —
  napiszę osobny plan i pokażę Ci go do akceptacji, zamiast zgadywać
  szczegóły UI.

- **Usuwanie podpisu elektronicznego z poziomu okna podglądu (magic
  pen).** Twój feedback (2026-09-18): „czy nie mozemy dac opcji usun
  podpis na oknie podgladu? bo tak troche na okolo". Technicznie
  wykonalne — mechanizm „zamrożonego wyboru” już działa dla zakresu
  stron i kategorii, podpis mógłby działać tak samo — ale to osobny
  kawałek pracy, nie zacząłem bez Twojego potwierdzenia.

Powiedz, od którego (jeśli w ogóle, i w jakiej kolejności) mam zacząć —
albo czy wolisz najpierw dokończyć testowanie tego, co już jest gotowe.

## Potwierdzone

- [x] **Ustawienia — wolne ładowanie naprawione** (potwierdzone
      2026-09-20) — Twój feedback: „ustawienie dzialaja juz dobrze".
- [x] **Etap 7 — usuwanie podpisów elektronicznych z PDF-a: usuwanie
      naprawdę działa** (potwierdzone 2026-09-20) — Twój feedback:
      „usuwanie podpisu jak rozumiem dziala bo zniklo to pomarańczowe
      pole sign", potwierdzone przeze mnie bezpośrednio w przesłanym
      pliku (0 pól podpisu, plik przestał być formularzem PDF).
      **Wciąż otwarte**: prośba o wygodę (usuwanie z poziomu okna
      podglądu) — patrz „Do zaplanowania” wyżej.
- [x] **Ostrzeżenie o zakresie stron spoza dokumentu — teraz widoczne
      na ekranie wyników** (potwierdzone 2026-09-20) — Twój feedback:
      „wychwytywanie zakresu z poza stron dokumentu niby dziala"
      (potwierdzone zrzutem ekranu z żółtą kartą ostrzeżenia). Sama
      **strategia** pola „Strony” się zmienia — patrz „Do zaplanowania”
      wyżej — ale to jest osobna sprawa od tego, czy ostrzeżenie się w
      ogóle pokazuje, co teraz działa.
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
