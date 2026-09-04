---
name: lekcje
description: >
  Baza uniwersalnych lekcji z poprzednich projektów — objaw, przyczyna, rozwiązanie.
  Użyj gdy coś nie działa bez jasnej przyczyny, coś działa dziwnie wolno, narzędzie
  "nie radzi sobie" z czymś trywialnym, pliku nie da się usunąć, testy padają
  wielokrotnie, AI gubi ścieżkę repo, albo gdy user mówi "LEKCJA:" i chce coś zapisać.
---

# Lekcje

**Przeczytaj ten plik, zanim zaczniesz zgadywać przyczynę problemu.**
Objaw z tabeli poniżej często kieruje prosto do rozwiązania.

## Szybki indeks — objaw → sekcja

| Objaw | Sekcja |
|---|---|
| Testy/build padają wielokrotnie bez powodu w kodzie, wszystko dziwnie wolno | Antywirus |
| Folderu nie da się usunąć, „file is in use", nawet po restarcie | Serwer dev w trayu |
| AI raportuje inną ścieżkę repo niż ta, w której pracujesz | Dwa klony repo |
| Pliki „stworzone dzisiaj" nie widać w `git status` | Dwa klony repo |
| Workflow oparty na plikach zwraca fałszywe błędy | Kodowanie UTF-8 |
| `cd` zwraca „positional parameter" / „cannot find path" | Spacje w ścieżkach |
| AI działa tak, jakby znało plik, którego nie widzi | Wspominanie ≠ dostęp |
| Prompt trafił do złego folderu / złego repo | Niejednoznaczna ścieżka |
| Czat executor marnuje tokeny na powtórną analizę kontekstu | Executor nie powtarza |
| Prompt wdrożeniowy przepisywany po raz piąty | Nie pisz finalnego promptu za wcześnie |
| AI „poprawia" ścieżkę w dokumentacji, przestaje działać na drugim komputerze | Ścieżka bezwzględna w repo wiedzy |
| Git: „Unable to create index.lock: File exists" po sesji z agentem | Agent zostawia index.lock |
| Agent pokazuje całe repo jako zmienione, choć nic nie ruszał | Agent zostawia index.lock |

---

## Jak zapisywać nową lekcję (`LEKCJA:`)

Format — krótko, ale tak, żeby przyszły-Ty od razu wiedział co robić:

```
## [krótki tytuł objawu]
- OBJAW: po czym poznać, że to ten przypadek
- PRZYCZYNA: co było źródłem (jeśli wiadomo)
- ROZWIĄZANIE: co konkretnie zrobić / komenda do wpisania
- KONTEKST: kiedy i gdzie wystąpiło (1 zdanie)
```

Nowy wpis dopisujesz na końcu właściwej sekcji **oraz** jako wiersz w indeksie wyżej.

**Gdzie to trafia:**
- **Uniwersalne** (przyda się w innym projekcie) → tutaj
- **Specyficzne dla jednego projektu** → plik w repo tego projektu, **nie tutaj**

Pytanie rozstrzygające: *czy to przyda się też w INNYM projekcie?*

## ⚠️ Awans lekcji na zasadę

Gdy ta sama lekcja wraca **2–3 razy** w różnych projektach — przestaje być lekcją,
a staje się zasadą. Wtedy przenieś ją do właściwego skilla (`zasady-wspolpracy`,
`jakosc-kodu`, `git-i-repo`, `projekt-www`, `projekt-app`) i usuń stąd.

**Po co:** skill, który urósł, jest po cichu ignorowany przez AI. To jedyny realny
sposób, w jaki ten system może przestać działać. Przegląd pod tym kątem robi się
przy komendzie `AUDYT:`, nie na bieżąco.

---

# Środowisko (Windows / lokalne)

## Antywirus / ochrona w czasie rzeczywistym blokuje pracę
- **OBJAW:** operacje na plikach (zapis, build, testy, instalacja paczek) działają dziwnie
  wolno, niestabilnie, albo zadania „nie wychodzą" mimo poprawnego kodu. Codex/Claude Code
  wielokrotnie „nie radzi sobie" z czymś, co wygląda trywialnie.
- **PRZYCZYNA:** antywirus / Windows Defender skanuje pliki w czasie rzeczywistym albo
  blokuje skrypty, wydłużając lub przerywając operacje.
- **ROZWIĄZANIE:** sprawdź to **wcześnie**, nie po czterech iteracjach. Test ręczny —
  uruchom tę samą operację bezpośrednio w terminalu i zobacz ile trwa:
  ```powershell
  Measure-Command { python -c "open('test.txt','w').write('x')" }
  ```
  Jeśli to antywirus: dodaj folder projektu do wyjątków skanowania albo wyłącz ochronę
  w czasie rzeczywistym na czas testu.
- **KONTEKST:** wzorzec do zapamiętania — gdy testy kilka razy nie wychodzą bez jasnej
  przyczyny w kodzie, podejrzewaj blokadę środowiska, nie tylko kod.

## Serwer dev przeżywa restart komputera w zasobniku
- **OBJAW:** folderu projektu nie da się usunąć ani przenieść („file is in use by another
  process") mimo zamknięcia terminala i **pełnego restartu komputera**. `Remove-Item -Force`
  zwraca `RemoveFileSystemItemIOError`.
- **PRZYCZYNA:** proces serwera dev (Vite/node) zminimalizował się do zasobnika (tray)
  i przetrwał restart, bo coś go odtwarza przy starcie systemu.
- **ROZWIĄZANIE:** sprawdź ikony w zasobniku (strzałka „^" przy zegarze) i zamknij tam
  ręcznie wszystko związane z serwerem deweloperskim. Dopiero potem usuwaj folder.
  Pomocne: `Get-Process node, claude -ErrorAction SilentlyContinue | Select Id, ProcessName, Path`
  — ale proces w trayu może nie być widoczny w Menedżerze zadań bez „Więcej szczegółów".
- **KONTEKST:** projekt fotograficzny, czerwiec 2026.

## Pliki tworzone z PowerShell zapisuj jako UTF-8
- **OBJAW:** workflow oparty na plikach „nie działa" albo zwraca fałszywe błędy, mimo że
  ta sama funkcja działa z plikami przygotowanymi inaczej.
- **PRZYCZYNA:** niekompatybilne kodowanie znaków przy tworzeniu plików z PowerShell.
- **ROZWIĄZANIE:** zapisuj jako UTF-8, szczególnie pliki testowe i syntetyczne.

## Ścieżki ze spacją wymagają cudzysłowu
- **OBJAW:** `cd` albo inna komenda zwraca „positional parameter" / „cannot find path".
- **ROZWIĄZANIE:** `cd "H:\folder z spacją\..."`. Bezpieczna zasada: **zawsze** cudzysłów
  wokół całej ścieżki — nie zaszkodzi nawet bez spacji.

---

# Praca z AI

## Wspominanie pliku ≠ dostęp do pliku
- **OBJAW:** AI działa tak, jakby znało treść dokumentu wiedzy, którego faktycznie nie widzi.
- **PRZYCZYNA:** czat (Claude.ai / ChatGPT) nie widzi automatycznie plików z dysku ani z repo.
  Łatwo o fałszywe wrażenie ciągłości, gdy AI wcześniej „wspominało" ten plik.
- **ROZWIĄZANIE:** na starcie sesji AI **sprawdza** czy plik jest realnie widoczny, a nie
  zakłada. Nie widzi → prosi o wgranie. (Procedura startowa w skillu `zasady-wspolpracy`.)
- **KONTEKST:** czerwiec 2026 — Claude napisał cały skill na podstawie historii czatów,
  zakładając że odzwierciedla plik kompendium. Plik był pusty i nigdy nie trafił do bazy wiedzy.

## Niejednoznaczna ścieżka w promptcie = ryzyko pomyłki repo
- **OBJAW:** zmiana trafiła do innego folderu niż zamierzony.
- **PRZYCZYNA:** prompt opisywał cel słownie („folder portfolio, nie produkcyjny") zamiast
  podać dosłowną ścieżkę. Przy dwóch podobnych repo AI trafiło w produkcyjne.
- **ROZWIĄZANIE:** (1) prompty modyfikujące pliki zawsze podają pełną ścieżkę, (2) przy
  dwóch podobnych repo prompt zawiera `git remote -v` PRZED zmianą, (3) przy niejasności —
  STOP i pytanie, nigdy zgadywanie.
- **KONTEKST:** 2026-07-20. Szkody nie było, bo Claude Code sam sprawdził `git remote -v`,
  rozpoznał niezgodność i zatrzymał się z pytaniem.

## Dwa klony tego samego repo
- **OBJAW:** AI raportuje inną ścieżkę repo niż ta, w której pracujesz; pliki „stworzone
  dzisiaj" nie pojawiają się w `git status`; dwa foldery mają różne branche i historię.
- **PRZYCZYNA:** dwa osobne skopiowane foldery tego samego projektu istnieją równolegle.
- **ROZWIĄZANIE:** jeden projekt = jeden folder roboczy, zawsze. Szczegółowa procedura
  rozplątywania duplikatu — w skillu `git-i-repo`.
- **KONTEKST:** projekt fotograficzny — masonry i 324 przetworzone zdjęcia wylądowały
  w „duplicate" repo, bo Claude Code był odpalany raz w jednym folderze, raz w drugim.

## Czat executor nie powtarza weryfikacji kontekstu planisty
- **OBJAW:** czat etapu zaczyna od „czytam schemat bazy, czytam historię, czytam
  architekturę..." mimo że dostał gotowy prompt od szefa.
- **ROZWIĄZANIE:** executor czyta gotowy prompt, weryfikuje że rozumie **zadanie**,
  i działa. Nie powtarza metodologii — planista już to zrobił, to podwójny koszt tokenów.

## Nie pisz finalnego promptu, dopóki ustalasz fakty
- **OBJAW:** długi prompt wdrożeniowy przepisywany po raz piąty, bo każda odpowiedź
  usera zmienia założenie.
- **ROZWIĄZANIE:** (1) najpierw ustal wszystkie fakty bez pisania finalnego promptu —
  notatki, listy, pytania i odpowiedzi, (2) gdy fakty są domknięte, napisz prompt **raz**,
  porządnie. Brudnopis ≠ dokument finalny.

## Potwierdź katalog docelowy przed tworzeniem projektu
- **ZASADA:** przed stworzeniem nowego repo, szkieletu projektu albo dużego zestawu plików —
  poproś o potwierdzenie dokładnej ścieżki lokalnej. Poprawna struktura w złym katalogu
  to i tak praca do posprzątania.

## Ścieżka bezwzględna w repo wiedzy = wojna dwóch komputerów
- **OBJAW:** AI „naprawia" ścieżkę w dokumentacji, twierdząc że stara jest martwa.
  Po zmianie repo pasuje do jednego komputera, a przestaje pasować do drugiego.
- **PRZYCZYNA:** repo wiedzy używane na dwóch maszynach miało w README, AGENTS.md
  i komentarzach wpisaną ścieżkę JEDNEJ z nich. Dla AI wygląda to na wiążącą
  konfigurację, a nie notatkę — więc „poprawia" ją pod maszynę, na której akurat jest.
- **ROZWIĄZANIE:** (1) w repo zero ścieżek bezwzględnych — skrypty na `$PSScriptRoot`
  („folder, w którym leżę"), działają z dowolnej lokalizacji; (2) jedna tabela
  „Gdzie stoi to repo" w README, wymieniająca WSZYSTKIE maszyny; (3) odwołania między
  plikami względne (`.ai\nazwa.md` w projekcie), nigdy absolutne.
- **KONTEKST:** wrzesień 2026, przeniesienie bazy wiedzy z PC domowego na laptop.
  AI uznało ścieżkę PC za błąd i podmieniło ją na ścieżkę laptopa — czyli zamieniło
  problem na dokładnie ten sam problem w drugą stronę.

## Agent bez prawa kasowania zostawia index.lock i blokuje gita
- **OBJAW:** po sesji z agentem mającym dostęp do folderu, git w PowerShellu odmawia
  pracy: `Unable to create index.lock: File exists`. Wcześniej `git status` uruchomiony
  przez agenta pokazywał CAŁE repo jako zmienione, mimo że agent nic nie ruszał.
- **PRZYCZYNA:** agent uruchomił komendę gita zapisującą indeks (`status`, `add`,
  `commit`). Git zakłada `.git/index.lock` i kasuje go na końcu — a środowisko agenta
  nie ma prawa usuwania plików na dysku użytkownika. Blokada zostaje.
- **ROZWIĄZANIE:** (1) komendy gita uruchamia UŻYTKOWNIK w PowerShellu — agent czyta
  i edytuje pliki, gita nie dotyka; (2) jeśli blokada już jest, agent może ją przenieść
  (`mv`) — zmiana nazwy działa tam, gdzie kasowanie nie; (3) ręcznie:
  `Remove-Item "<repo>\.git\index.lock"`.
- **KONTEKST:** wrzesień 2026, porządkowanie repo _wiedza-ai z Cowork. Dodatkowo agent
  widzi końce linii inaczej niż Windows, więc jego `git status` fałszywie pokazuje
  wszystkie pliki jako zmienione — drugi powód, żeby gita zostawić użytkownikowi.

---

# Podejście do projektu

## Wąski działający MVP > szeroki niedokończony system
- **ZASADA:** mały działający przepływ łatwiej przejrzeć, przetestować i zabezpieczyć niż
  szeroki, niegotowy. Duże i ryzykowne funkcje dodawać **po** ustabilizowaniu rdzenia.

## Repo jest źródłem prawdy, nie czat
- **ZASADA:** decyzje projektowe, status i szczegóły modułów muszą żyć w plikach repo.
  Kontekst czatu może zniknąć albo się zdezaktualizować.
- **KONSEKWENCJA:** coś ważnego ustalone w czacie → zapisz w pliku repo od razu.

## Pliki stanu czytaj live, nie wgrywaj do czatu
- **ZASADA:** pliki stanowe (`PROJECT_STATE.md`, dziennik, status) zmieniają się między
  sesjami. Wgrany snapshot zawsze rozjedzie się z rzeczywistością w kolejnej sesji.
- **ROZWIĄZANIE:** zapamiętaj że plik istnieje, ale czytaj go **live** każdą sesję
  (PowerShell, `cat`, edytor). Wtedy czat zawsze widzi bieżący stan.
