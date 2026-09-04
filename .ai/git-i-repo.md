---
name: git-i-repo
description: >
  Git w praktyce (rytuał sesji, checkpointy, cofanie zmian, pułapki push/pull, selektywne
  commity) oraz porządek repozytorium (co ma prawo tam być, .gitignore, dane testowe,
  jeden folder na projekt).
  Użyj gdy: "git", "commit", "push", "pull", "branch", "cofnij zmianę", "checkpoint",
  "gitignore", "porządek w repo", "co usunąć z repo", "git status pokazuje", albo przed
  ryzykowną zmianą i przed wydaniem.
  To JEDYNE miejsce z zasadami Gita — inne skille tylko tu odsyłają.
---

# Git i porządek repo

---

## Rytuał sesji

```powershell
git pull                    # ZAWSZE na początku sesji, przed pracą
git status --short          # krótka lista zmian (M / ?? / A / D)
git add -A                  # albo git add <konkretny plik/folder>
git commit -m "opis po polsku"
git push
```

`git pull` na starcie jest ważny szczególnie gdy repo dzielisz z innym narzędziem
(Lovable, drugi komputer) — mogło coś wypchnąć bez Twojej wiedzy.

**Operacje tylko do odczytu** (`git status`, `git log`, `git branch`, szukanie plików)
user robi sam w PowerShellu z gotową komendą. Nie zlecaj ich Claude Code — to
marnowanie kredytów na czysty odczyt.

---

## Pułapki

**`push` rejected („fetch first")** → na zdalnym repo jest zmiana, której nie masz lokalnie.
Rozwiązanie: `git pull`, potem `git push` jeszcze raz.

**`git add -A` dodaje WSZYSTKO.** Gdy narzędzie poprawiło też coś nieplanowanego —
`git add <ścieżka>` dla wybranych plików albo `git add -p` do wyboru fragment po fragmencie.

**`??` vs `D` przy czyszczeniu repo:**
- `??` = plik nigdy niezacommitowany → artefakt tymczasowy → bezpieczny do usunięcia
- `D` = plik JEST w historii, ktoś go świadomie dodał → usunięcie to **istotna decyzja** →
  domyślnie przywróć (`git checkout -- ścieżka`), nie usuwaj od razu

**Praca z eksportami / wgrywaniem partii plików** → `git status` **po każdej partii**,
nie na koniec. Eksporty (Figma, ChatGPT) lądują obok plików docelowych i po pięciu partiach
nie da się już rozpoznać co jest czym.

---

## Cofanie i checkpointy

```powershell
git checkout <hash> -- sciezka/do/pliku    # przywróć JEDEN plik z commitu
git revert <hash>                          # cofnij commit zachowując historię
git switch -c checkpoint/opis-zmiany       # punkt powrotu przed ryzykowną zmianą
```

**Checkpoint przed ryzykowną zmianą to zasada, nie opcja.** Branch nazwany opisowo
(`checkpoint/przed-migracja-bazy`) jest czytelniejszy niż sam numer commitu.

Szczególnie ważne przed: migracją bazy danych, masowym przetwarzaniem plików,
zmianą struktury folderów. Trudniej odwrócić zmianę schematu niż zmianę CSS.

---

## Porządek repo

Każdy plik w repo musi mieć powód, żeby tam być. Przed ważnym wydaniem przejrzyj repo
pod kątem: przypadkowych plików testowych, plików „do skasowania", starych ZIP-ów i buildów,
plików tymczasowych, cache, `.venv`, `build`/`dist`, przypadkowych danych użytkowników,
**sekretów, tokenów i haseł**.

Pliki lokalne, które nie należą do repo → `.gitignore`.

Przykładowy root:
```
app.py    src/    tests/    assets/    docs/
requirements.txt    README.md    .gitignore    .env.example
```

**Nie używaj katalogu głównego projektu jako pulpitu roboczego.**

---

## Dane testowe

Anonimowe, sztuczne, minimalne, jasno nazwane — w `tests/fixtures/` albo `samples/`.
Nigdy prawdziwe dokumenty produkcyjne w repozytorium.

---

## Jeden projekt = jeden folder roboczy

⚠️ **Nigdy nie pracuj na dwóch klonach tego samego repo równocześnie.**

Objaw: AI raportuje inną ścieżkę niż ta, w której pracujesz; pliki „stworzone dzisiaj"
nie pojawiają się w `git status`; dwa foldery mają różne branche i różną historię.

Gdy wykryjesz duplikat: (1) zdecyduj który jest „ten jedyny" (zwykle podłączony do
właściwego brancha na GitHubie), (2) zleć AI **wyłącznie** inwestygację różnic, bez zmian,
(3) przejrzyj raport, (4) przenieś tylko brakujące pliki, (5) usuń duplikat dopiero po
potwierdzeniu, że wszystko działa.

**Prompty modyfikujące pliki zawsze podają pełną, dosłowną ścieżkę folderu** — nigdy
opisowo („folder portfolio", „ten drugi projekt"). Przy dwóch podobnych repo prompt
zawiera krok weryfikacji (`git remote -v`) PRZED zmianą.
