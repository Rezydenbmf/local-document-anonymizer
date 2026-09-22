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

- [ ] **Nowa strategia zakresu stron — kontrolka przy każdym pliku
      (zbudowane 2026-09-22, gotowe do sprawdzenia)** — zamiast jednego
      wspólnego pola „Strony" dla całego wsadu, każdy plik PDF na
      liście wybranych plików ma teraz **własne, małe pole obok nazwy**.
      Apka od razu po wczytaniu pliku wie, ile ma on stron, i pokazuje
      to w podpowiedzi pola (np. „np. 1-3 (z 5 str.)"). Jeśli wpiszesz
      numer strony, której dokument nie ma, obramowanie pola **od razu
      robi się czerwone** — nie trzeba czekać na uruchomienie
      anonimizacji, żeby się o tym dowiedzieć. Pliki TXT/DOCX/obraz nie
      mają tego pola w ogóle (jak dotychczas — dotyczy tylko PDF-a).
      Sprawdź na żywo: (1) wrzuć kilka PDF-ów o różnej liczbie stron
      (plus jeden TXT/DOCX) — każdy PDF ma własne pole z poprawną
      podpowiedzią liczby stron, plik TXT/DOCX nie ma żadnego pola;
      (2) wpisz w jednym polu zakres spoza dokumentu (np. „99" na
      3-stronicowym pliku) — tylko ta jedna kontrolka ma zrobić się
      czerwona, reszta bez zmian; (3) usuń plik z listy i dodaj go
      ponownie — pole ma wrócić puste; (4) uruchom anonimizację z
      różnymi zakresami na różnych plikach naraz — każdy wynik powinien
      mieć zamazane tylko swoje, wybrane strony.

- [ ] **Okno samej aplikacji miga raz przy starcie (zgłoszone
      2026-09-22, niski priorytet — Twoja własna ocena)** — Twój
      feedback: „nie migaja terminale okno samej aplikacji raz miga -
      ale na tym etapie chyba nie jest to jakis wielki problem".
      Terminale (przyczyna naprawiona poprzednio) już nie migają —
      potwierdzone. To nowe, osobne zjawisko (samo okno GUI, nie
      terminal) zostaje odnotowane, ale świadomie odłożone na Twoją
      prośbę — nie coś, czym zajmuję się teraz.

## W trakcie (2026-09-22 — Twoja decyzja: „to robimy 1 i 2 a potem na
ten tydzien zaczynamy z llm-em"; punkt 1 zrobiony, przeniesiony wyżej
do „Do sprawdzenia")

1. **Usuwanie podpisu elektronicznego z poziomu okna podglądu (magic
   pen).** Mechanizm „zamrożonego wyboru” już działa dla zakresu stron
   i kategorii — podpis dołączy do tego samego wzorca.

Po tym: początek prac nad wykorzystaniem lokalnego LLM (Ollama) —
osobny, większy temat, wymaga wcześniej ustalenia dokładnego zakresu
(patrz nasza wcześniejsza rozmowa o różnicy między dzisiejszą warstwą
przeglądu a kontekstowym wykrywaniem, o którym mówiłeś) i zaprojektowania
zabezpieczenia przed prompt injection, zanim treść dokumentu zacznie
trafiać do promptu.

## Potwierdzone

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
