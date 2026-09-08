# Project State

## Current Status

The project has a working local MVP. Stage 24 was completed, tested, committed,
and pushed as `52a62aa Implement Stage 24 layout-preserving PDF review`.
Stage 24 completed the public PDF review cleanup after Stage 23 by making
`_ANON_VISUAL.pdf` the main original-layout manual review artifact for
text-based PDFs. PDF input now creates anonymized TXT, `_ANON_VISUAL.pdf`, an
auxiliary `_ANON_REVIEW.pdf`, a privacy-safe per-file manual review checklist,
and a safe report by default. The legacy original-layout redaction output
remains available only as an explicit experimental mode. Stage 24 also narrowed
PDF redaction quality, improved a typo-shaped person-name pattern, added a
visible GUI processing status, and replaced manual LLM model-name typing with a
local Ollama model selector.

The Stage 0-13 MVP implementation contains a narrow regex-based engine that
accepts a Python string and returns anonymized text plus category counters. It
also contains optional private dictionary support with aliases,
case-insensitive matching, and whitespace-tolerant term matching, TXT file
readers and writers, basic DOCX readers and writers, text-based PDF text
extraction, small integration helpers for saving separate anonymized TXT, DOCX,
and PDF-to-TXT outputs, a simple Tkinter GUI for anonymizing selected
supported files into a chosen output folder, safe TXT report generation without
source values, a safe post-anonymization audit with category counters only,
batch processing, and manual review status tracking for generated output
folders.

Stage 10.1 fixes manual validation findings around the private dictionary flow.
The GUI stores the selected dictionary path, the workflow loads it centrally,
reports include safe dictionary status and label counters, and the audit checks
remaining dictionary terms when a dictionary loaded successfully. It did not
add OCR, AI, cloud services, APIs, local LLMs, databases, batch processing,
automatic replacement-map generation, source-value logging, or automatic
deletion of originals.

Stage 10.2 manually confirmed the Stage 10.1 dictionary fix with a GUI smoke
test using small synthetic UTF-8 files.

Stage 11 kept the existing local workflow and improved the private dictionary
foundation. Dictionary lines can contain multiple aliases separated by `|`,
matching is case-insensitive, excessive internal whitespace is tolerated, and
longer aliases are still applied before shorter aliases. Reports, GUI status,
audit metadata, and counters continue to expose labels and counts only.

Stage 12 adds a safe output workspace and batch processing. The GUI now lets
the user select multiple supported files and an output folder. `_ANON`,
`_RAPORT`, and `_BATCH_SUMMARY` files are written to that output folder with
collision-safe numbered names. Batch processing is sequential; an error for one
file is recorded in a safe form and does not stop later files. The batch
summary stores safe filenames, aggregate counters, audit status counts, and
controlled error descriptions only.

Stage 13 adds a manual review workflow for existing output folders. The app
detects generated `_ANON` files, pairs matching `_RAPORT` files when present,
lists `_BATCH_SUMMARY` files when present, lets the user mark outputs as
`approved`, `needs_review`, or `rejected`, and saves safe
`_REVIEW_STATUS.json` and collision-safe `_REVIEW_SUMMARY.txt` metadata.
`approved` is a manual user decision, not an automatic application decision,
and the workflow does not show, inspect, or store document contents.

Stage 15 improves the existing Tkinter GUI usability without changing the core
anonymization engine. The window is resizable with a smaller minimum size and a
scrollable main layout, the input selection is shown as a removable list with a
readable selected-file count, selected inputs can be cleared from the GUI
without deleting files, the anonymization button has a visible readiness hint
that explains missing input files or output folder, review statuses can be
applied to multiple selected review rows, and the manual review section can
open the selected generated `_ANON` output or matching `_RAPORT` report with
the operating system default application. The GUI still does not preview,
inspect, edit, or validate document contents inside the app.

Stage 16 strengthens the deterministic post-anonymization audit and adds safe
per-file risk levels for manual-review prioritization. The audit now returns
status, risk level, category counters, and manual review metadata only.
`_RAPORT.txt` includes audit status, risk level, warning counters, and manual
review requirement. `_BATCH_SUMMARY.txt` includes aggregate risk level counts
and aggregate audit category counters. The manual review workflow reads risk
levels from safe paired reports and the GUI shows a risk column with
`high_risk` items sorted first. The risk level is not an automatic approval or
safety guarantee; manual review remains required.

Stage 17 adds an approved workspace export for output folders with saved manual
review metadata. The export reads `_REVIEW_STATUS.json`, copies only `_ANON`
files marked `approved` into an `approved/` staging folder, optionally copies
matching `_RAPORT` files when present, and writes a safe
`_APPROVED_INDEX.txt` manifest using basenames and metadata only. Existing
approved workspace files are not overwritten; numbered suffixes such as `_2`
and `_3` are used. `approved` remains a manual user decision and the approved
workspace is a staging area, not a knowledge base or guarantee of complete
anonymization.

Stage 18 validates the complete local MVP workflow end to end with synthetic
tests and manual smoke-test documentation. It exercises source files, batch
anonymization, reports, post-anonymization audit risk levels, manual review
metadata, approved workspace export, and the safe approved index. It does not
add OCR, AI/API integration, local LLMs, databases, installer work, drag and
drop, document preview, split-screen review, highlighting, automatic approval,
or a knowledge base.

Stage 18 also includes a small dictionary stabilization fix: a leading UTF-8
BOM at the start of a dictionary file is ignored so the first alias on the
first line matches consistently with later aliases.

Stage 19 adds an optional local OCR foundation. It introduces controlled OCR
availability detection, image input OCR for PNG/JPG/JPEG/TIFF when local OCR
dependencies and Tesseract are installed, and scanned-PDF fallback only when a
PDF has no extractable text layer. OCR text feeds into the existing
anonymization, report, audit, batch, GUI, manual review, and approved export
workflow as anonymized TXT output. Reports and batch summaries include safe OCR
metadata only. Stage 19 does not add cloud OCR, API OCR, OpenAI API calls,
online processing, NER, local LLMs, split-screen review, preview,
highlighting, drag and drop, installer work, packaging, edited image output,
or scanned-PDF visual redaction.

Stage 20 adds an optional local NER/NLP foundation. It introduces controlled
spaCy availability detection, local Polish model loading without runtime
downloads, internal NER labels for people, organizations, locations, and safe
miscellaneous entities, and safe NER metadata in reports, batch summaries, and
the GUI status area. NER runs only when enabled and available, after private
dictionary and regex replacements, and skips existing placeholders to avoid
double replacement. Missing spaCy, missing local models, disabled NER, and
processing errors are controlled statuses and do not crash the application.
Stage 20.1 adds a conservative local PERSON left-expansion heuristic to reduce
partial person masking in simple adjacent-token cases. Stage 20 does not add
Ollama, Bielik, OpenAI API calls, cloud/API processing, online NLP, local LLMs,
candidate export files, document preview, highlighting, drag and drop,
databases, or model downloads at runtime.

Stage 21 adds an optional local Ollama LLM-assisted review foundation. It
introduces controlled Ollama availability detection, safe installed-model
listing where possible, configured model validation, strict JSON response
parsing, timeout/error handling, safe LLM metadata in reports and batch
summaries, and a minimal GUI checkbox plus model-name field. LLM review runs
after anonymization and receives already-anonymized output text only. It is an
extra quality-control layer, not the primary anonymizer, not an editor, not a
replacement for dictionary/regex/NER/audit/manual review, and not automatic
approval. Stage 21 does not add OpenAI API calls, cloud LLMs, external APIs,
online processing, RAG, vector databases, a chat UI, document rewriting,
runtime model downloads, or a required Ollama model.
Stage 21.1 hardens the local Ollama subprocess path for Windows UTF-8/BOM
handling by stripping BOM characters from already-anonymized review input,
forcing UTF-8 subprocess text handling, and converting encoding/subprocess
failures into controlled safe LLM statuses without exposing prompt text, raw
responses, snippets, or traceback details.
Stage 21.2 improves local Ollama JSON reliability by sending the review call
through the local Ollama generate API with a strict JSON schema request,
keeping strict parser rejection for invalid/unsafe output, and correcting
batch LLM counters so `timeout`, `invalid_response`, and `processing_error`
count as attempted safe failures instead of skipped/unavailable runs. The
parser also tolerates the narrow local-model behavior where the entire JSON
object is wrapped in a markdown code fence, while still rejecting prose outside
the fence and never storing the raw response.

Stage 22 adds a local Knowledge Assistant MVP for approved anonymized TXT
documents. It loads only approved `*_ANON.txt` files, preserves safe source
basenames only, chunks documents deterministically, writes a local generated
`_KNOWLEDGE_INDEX.json`, retrieves relevant chunks with a keyword fallback,
optionally uses local Ollama answer generation with a user-installed model such
as `gemma3:4b`, and always returns source chunk IDs. If Ollama is unavailable,
the model is missing, generation fails, or no relevant context is found, the
assistant returns controlled messages instead of crashing. Stage 22 does not
add embeddings, `bge-m3`, a vector database, a GUI, a web app, cloud APIs,
OpenAI API calls, online processing, document editing, authentication,
installer work, or automatic business-procedure generation.

Stage 22.1 improves the Local Knowledge Assistant CLI UX for local Ollama cold
starts. It adds `ollama-status` and `warmup` commands, lets `ask` accept a
local generation `--timeout`, and returns clearer timeout messages that tell
the user to warm up the model or retry with a longer timeout. Timeout fallback
still shows retrieved sources and does not pretend generation succeeded. Stage
22.1 remains CLI-only and does not add a GUI redesign.

Stage 23 added a layout-preserving true-redacted visual PDF companion for
text-based PDF inputs. Stage 24 pilot testing showed that broad text-search and
token fallback redaction could make real review PDFs unusable. The Stage 24
default for text-based PDF input is now `_ANON.txt`, `_ANON_VISUAL.pdf`,
`_ANON_REVIEW.pdf`, `_REVIEW_CHECKLIST.txt`, and `_RAPORT.txt`.
`_ANON_VISUAL.pdf` is the main manual review artifact: it preserves the source
PDF page layout and applies true PyMuPDF redaction annotations from detected
spans mapped to full word-coordinate rectangles. The rebuilt `_ANON_REVIEW.pdf`
is auxiliary, generated from anonymized text only, uses simple source-page
headers when page text is available, and does not embed original PDF pages.
The TXT output remains the source for approved-workspace indexing and the Local
Knowledge Assistant. Legacy `_ORIGINAL_REDACTED.pdf` remains an explicit
experimental output mode.

The default visual PDF redaction scope avoids broad substring search. It builds
internal non-persisted spans for deterministic identifiers, dictionary aliases,
`PERSON_NAME_TYPO`, high-confidence person spans, and exact NER org/location
spans after allowlist filtering, then maps those spans to whole PDF words. If a
span cannot be mapped safely to full word rectangles, it is skipped and
reported by category only. The previous broad token fallback remains disabled.
Stage 24 also adds conservative NER/PDF false-positive exclusions for public
institution/legal phrases, version-like strings, disease/microbiology and
vaccine terms, likely Latin binomials, selected ordinary Polish word false
positives, and single-token person-like detections without strong person
context, plus soft line-break handling for person names split across PDF text
lines. The NER allowlist matcher also normalizes case, non-breaking spaces,
soft hyphens, and common Unicode dash variants before visual PDF span
redaction. Grouped phone-like numbers now require contact context unless they
use a stronger phone format, reducing table/statistical false positives.
Reports, per-file review checklists, batch review checklists, and batch
summaries include safe PDF review/redaction status metadata, PDF text
extraction mode, visual PDF type/output, word-coordinate mapping mode, review
PDF type, true-redaction status, detected category counts, TXT anonymized
category counts, PDF-redacted category counts, detected-but-not-PDF-redacted
category counts, unmapped skipped categories, NER exclusion counters, and
weak phone-like skipped counts. The manual review open action
prefers `_ANON_VISUAL.pdf`, then `_ORIGINAL_REDACTED.pdf`, then
`_ANON_REVIEW.pdf`, then legacy `_ANON.pdf` when present, while review metadata
still tracks the `_ANON.txt` output and pairs `_REVIEW_CHECKLIST.txt` when
present. Stage 24 extends the
conservative
`PERSON_NAME_TYPO` pattern to cover malformed shapes such as
`Firstname-LastnamePart1 LastnamePart2`, Unicode dash variants, and simple
spacing around the dash while avoiding tested normal hyphenated non-person
phrases. Stage 24 also replaces the GUI's free-text LLM model field with a
refreshable local Ollama model selector based on `ollama list`; when no local
models are available, the GUI shows a clear install/pull-model hint. The GUI
also exposes the recommended visual PDF mode plus auxiliary rebuilt and legacy
experimental output modes, and supports mouse wheel/touchpad scrolling in the
tall main window. Stage 24 does not add scanned-PDF/OCR bounding-box redaction,
a PDF editor, split-screen review, drag and drop, vector databases, or broader
LLM features.

Stage 24.1 fixes two related bugs found during a real-use pilot of the
completed Stage 24 workflow, both caused by short PDF page text losing line
context before local NER analysis. First, `extract_pdf_word_pages` joined
every PDF word on a page with a plain space instead of a real line break,
which could make a short standalone label word on its own PDF line (for
example `PESEL` or `Data`) look like part of an organization name to the
local NER model; the word-coordinate visual redaction pass then wiped the
label word out of `_ANON_VISUAL.pdf` even though it was never flagged in the
TXT-level report. The fix inserts a real line break between PDF words when
the source line changes, matching how normal PDF text extraction already
behaves for the `_ANON.txt` output. Second, the existing NER line-break
bridging built to detect a person name split across a line (for example
`Jan` / `Kowalski`) does not know in advance what an entity will turn out to
be, so it could also bridge two unrelated capitalized words from separate
lines, such as two section headers, into a false organization or location
match; a synthetic two-line snippet reproduced this live with the real local
`pl_core_news_sm` model. The fix skips a detected entity when its label is
not `NER_PERSON` and its span only exists because of that line-break
bridging, reported under a new `LINEBREAK_NON_PERSON_SKIPPED` NER exclusion
category; the existing person line-break bridging behavior is unchanged and
still detects a genuine split person name. Both fixes ship with regression
tests confirmed to fail against the pre-fix code and pass after the fix; the
full test suite remains green (228 tests).

```text
da42c88 Fix PDF visual redaction over-wiping benign label words
a8fadfe Skip non-person NER entities that only exist via line-break bridging
```

Stage 24.2 extends the deterministic anonymization engine with several
identifier categories observed as gaps during the Stage 24.1 pilot, plus one
more NER exclusion. `pesel`, `nip`, and `regon` join the local NER
false-positive exclusion list so the model no longer occasionally mistakes
these label words for an organization or location when a number does not
follow them. The `DATA` pattern now also matches dash-separated
(`dd-mm-yyyy`) and slash-separated (`dd/mm/yyyy`) numeric dates and
written-month-name dates (`4 września 2026`), the most common date-of-birth
format in Polish formal documents. A new `POSTAL_CODE` category (`dd-ddd`)
promotes the pattern already used audit-only in `audit.py` into the actual
anonymization engine, kept under the same name for consistency. A new
`MIEJSCOWOSC` category detects a town/city name immediately after a postal
code, including compound names. A new `ULICA` category detects a street name
after `ul./al./pl.` (with or without a period, either case) or the inflected
full words `ulica/ulicy/aleja/alei/aleje/plac/placu`, with an optional
building/apartment number, adapted from `audit.py`'s audit-only
`ADDRESS_LIKE`/`STREET_LIKE` patterns. New `NIP` and `REGON` categories
detect the actual identifier number, gated on the literal keyword
immediately before it, the same keyword-context convention `audit.py`'s
`ID_LIKE_NUMBER` pattern already uses; previously only the label word was
excluded from NER false positives, the number itself was not detected.
Every new category ships with regression tests confirmed to fail against
the pre-change code and pass after; two pre-existing tests whose fixtures
happened to rely on addresses/postal codes not being detected yet were
updated to keep testing their original intent instead of a gap this change
closes. Full suite: 240 tests.

The anonymization engine's regex patterns are still duplicated across three
places (`anonymizer.py`'s `_PATTERNS`, `pdf_redaction.py`'s
`PDF_REDACTION_PATTERNS`, and `audit.py`'s audit-only `_AUDIT_PATTERNS`);
Stage 24.2 kept new patterns consistent by hand across all three but did not
unify them into one shared source. A local database matching general
town/city names without postal-code context remains deliberately deferred;
see Roadmap.

Stage 24.3 adds two more deterministic categories. `DOWOD_OSOBISTY` detects
a Polish ID card number by its official shape alone (3 uppercase letters
immediately followed by 6 digits, no separator), with no keyword context
required, the same shape-only approach already used for `PESEL`. `IBAN`
detects a Polish IBAN (`PL` plus 26 digits), matched whether written as one
continuous run or grouped in 4s with spaces; a bare 26-digit domestic
account number without the `PL` prefix stays out of scope as too ambiguous
to redact safely without a country-code anchor. Both ship with regression
tests, including their negative cases (wrong case/length ID-like code,
malformed IBAN grouping), confirmed to fail before and pass after the
change. Full suite: 244 tests.

Stage 24.4 fixes a written-month date gap found live while testing a
fictional 5-person meeting transcript with sensitive data embedded in
natural conversation rather than labeled fields: dates like "15 wrzesnia
2026" (missing the Polish diacritics in "wrzesnia"/"pazdziernika") were not
detected at all, while the correctly-accented spelling already was. Text
without Polish diacritics is common in real automatic speech-to-text
transcripts and some OCR output, so this was a real coverage gap. The
`DATA` pattern's written-month alternative now matches both the accented
and unaccented spelling of the two affected month names (the other ten
Polish month names used in dates are already plain ASCII). Full suite: 245
tests.

Stage 25 replaces the single dense Tkinter/ttk main window with a guided,
modern `CustomTkinter` interface (new dependencies: `customtkinter`,
`tkinterdnd2`), designed from mockups the user approved beforehand and then
refined against feedback from hands-on testing of the real app. Only the
presentation layer in `src/gui.py` changed; every anonymization/review
backend module is untouched. The app is now four screens instead of one
scrolling form: a drag-and-drop start screen (native OS drag-and-drop, a
click-to-pick fallback, file cards, and an output folder pre-filled with a
created-on-first-launch default under `~/Documents`), a separate settings
modal for NER/LLM/dictionary/PDF-mode options that used to always be
visible, a processing screen with a live progress bar, and a card-based
review screen. Review cards use icon-only status buttons (preview/approve/
needs-review/reject) with real hover tooltips and autosave the status on
each click instead of requiring a separate save step; a distinct color
(not the risk-warning amber) is used for the needs-review action so it is
not confused with the risk badge. A new "Szczegoly" dialog parses the
existing safe `_RAPORT.txt` (via `parse_report_summary`) into a short,
human-readable risk badge plus colored category chips instead of asking
the user to read a plain-text log; the raw report/checklist stay reachable
through small developer-labeled links inside that dialog. A color legend
matching the existing `PDF_REDACTION_COLORS` scheme is shown on the review
screen. A new `ComparisonWindow` renders the original file and the
preferred anonymized review artifact side by side (PDF pages via PyMuPDF,
TXT/DOCX as text, images directly) for visual verification; it only knows
the original path for files processed in the current session (via the
batch's own `input_name`/`output_name` pairing) and shows a clear
"original not available" message otherwise, consistent with the review
workspace's existing design of not persisting source paths. This
comparison view is deliberately read-only for now - interactive manual
redaction ("magic pen": click to add or undo a redaction and regenerate
the file) was explicitly scoped out as a separate, later stage together
with the user, since it is substantially more work (page-to-canvas
rendering, click-to-region hit-testing, span remapping, output
regeneration) than a visual redesign. All existing pure formatting
functions and their tests are unchanged; the new screens use new
Polish-language equivalents instead of putting the old English strings on
screen. Full suite: 261 tests.

While preparing this stage's commit, found and fixed a `.gitignore` gap:
several newer generated file types (`_ANON_VISUAL*.pdf`, `_ANON_REVIEW*.pdf`,
`_ORIGINAL_REDACTED*.pdf`, `_REVIEW_CHECKLIST*.txt`,
`_BATCH_REVIEW_CHECKLIST*.txt`) were never added, so a real manual-test
output folder was one `git add -A` away from being committed by accident.

Stage 25.1 is a small batch of fixes and one addition from hands-on testing
of the Stage 25 GUI. `import fitz` is replaced with `import pymupdf as fitz`
everywhere (8 call sites) to drop PyMuPDF's own deprecation warning printed
on every launch; every existing `fitz.*` reference is unchanged since the
module is imported under the same local name. Reprocessing files into an
output folder that already held older generated files (collision-safe
naming never overwrites them) showed the same-looking file twice in the
review screen and reported the original as unavailable for the stale
duplicate; `restrict_review_items_to_batch` now scopes the post-batch
review screen to only the outputs the batch just produced, while opening
an existing folder for review deliberately still shows everything in it.
Dragging files onto the drop zone also opened an unrelated file-picker
dialog right after the drop, because the drop-target widget and the
"click to pick files" binding were the same widget and a drop's mouse-up
was also read as a click; a short debounce after a real drop now
suppresses that spurious dialog. Finally, a "History" screen (top-bar
button, kept separate from the current-session workflow per explicit
request) lists recently used output folders - path and timestamp only,
never document content - backed by a small local JSON file at
`~/.anonimizer/recent_folders.json`, not a database; the user explicitly
did not want a database or password-protected store for this, consistent
with the project's existing "no database" scope decisions. Full suite:
273 tests.

Stage 26 implements the "magic pen" manual redaction editor inside
`ComparisonWindow` that Stage 25 deliberately scoped out, for PDF outputs
only (DOCX/TXT have no word coordinates to draw on and are left for a
possible later stage). The right ("Po anonimizacji") pane becomes an
interactive `tk.Canvas` per page with three modes: view, add
(drag a rectangle over visible text the automatic pass missed), and remove
(click an existing black rectangle to undo it). Nothing is written until
"Zapisz zmiany" - edits are staged locally first and shown as a live
overlay, with "Anuluj zmiany" available to discard them. The key design
constraint, from a direct user security question mid-planning: since
`page.apply_redactions()` physically deletes the underlying text (not a
colored box drawn over it), an "undo" cannot edit the already-redacted
output file - the only correct way to reveal a wrongly hidden fragment
again is to regenerate the true-redacted PDF from the original source file
with that one rectangle excluded. `save_word_coordinate_redacted_pdf_copy`
in `pdf_redaction.py` gained optional `output_path` (overwrite in place
instead of picking a fresh collision-safe name), `removed_span_keys`
(exclude specific auto-detected rectangles, identified by a deterministic
`manual_edit_span_key(page, label, rect)`), and `extra_redaction_rects`
(burn in manually drawn rectangles labelled `RECZNE`) - all optional and
defaulting to a no-op, so every existing caller and test is unaffected. Its
rect-resolution logic was extracted into a new pure `compute_redaction_rects`
so the GUI can ask "what would currently be hidden" for click hit-testing
without writing any file. A new `src/manual_redaction.py` module holds the
small `_MANUAL_EDITS.json` sidecar (removed-rectangle keys plus added
rectangles, never document content) next to each visual PDF output, the
`regenerate_pdf_with_manual_overrides`/`compute_visible_redaction_rects`
orchestration, a pure `apply_pending_overrides` reconciler (this-session
staged changes folded into a new `ManualEdits`, fully unit-tested without
any GUI or Tk dependency), and `apply_manual_redaction_count_to_report_text`,
which appends/updates/removes a clearly separate, delimited "Magic pen"
note in the existing `_RAPORT.txt` rather than silently rewriting the
original detection counts it never re-ran. Per explicit user decision,
saving edits always resets that item's review status back to
"wymaga przeglądu", even if it was already approved, and every manual
addition uses one general `RECZNE` label/color rather than a
user-chosen category. Verified functionally end-to-end with a synthetic
PDF (real spaCy NER, real PyMuPDF text extraction): un-redacting an
auto-detected email restored it in the regenerated PDF's extracted text,
and a manually added rectangle removed its covered line's text entirely,
with the review status flipping back to needs-review and the report
gaining the new note - all as designed. Full suite: 301 tests.

A self-review of Stage 26 right after landing it found three real issues,
fixed immediately rather than left as a follow-up: (1) `_toggle_pending_remove`
only ever added a key to `pending_remove_keys`, and `_effective_rects()`
filtered out anything already staged for removal, so a rectangle a user
clicked to undo became un-clickable - the only way to change your mind
about that one click was "Anuluj zmiany", discarding every other pending
change too; hit-testing now uses a `_hit_test_pool()` that keeps
staged-for-removal rects targetable, and the toggle now actually toggles.
(2) `_save_pending_changes` regenerated the true-redacted PDF by writing
directly over the live output path; an interruption mid-write (disk full,
process killed) could have corrupted or truncated the existing good file,
and even on success a failed sidecar write right after could leave
`_MANUAL_EDITS.json` out of sync with what the PDF actually contains. It
now regenerates to a `*.tmp.pdf` staging file first and only `os.replace()`s
it over the live output once that fully succeeds, with the sidecar written
last (the smallest, least failure-prone step) and the staging file cleaned
up on any failure - plus a "Zapisywanie..." status shown before the
synchronous work starts, addressing a related no-feedback concern from the
same review. (3) `_reload_pdf_pane()` always rebuilt canvases with a plain
arrow cursor regardless of the active mode; it now matches the current
mode like the original build does. Verified with a regression script that
exercises the toggle-twice-cancels path and confirms no leftover staging
file after save. Full suite: 301 tests.

The Stage 25.1 `fitz`-deprecation fix above only covered static
`import fitz` statements; the user reported still seeing the warning on
every "Anonimizuj" click. `ocr.py`'s OCR-availability detection did a
dynamic `import_module("fitz")` (missed by that earlier text search since
it never appears as a literal `import fitz` line), which still loads
PyMuPDF's deprecated compat shim and prints its warning on every
`detect_ocr_support()` call for a PDF input - i.e. on every batch run, not
just when OCR fallback actually runs. Fixed by importing `"pymupdf"`
instead (identical API). Full suite: 301 tests.

The user reported `ComparisonWindow` needed to be resizable/maximizable
and each preview independently zoomable - without it they could not test
the magic pen with any precision. `window.resizable(True, True)` plus a
sane `minsize` now make the comparison window a normal resizable/
maximizable window. Each pane ("Oryginał"/"Po anonimizacji") got its own
small header with "－ / percent / ＋" zoom controls plus a "🔗" link
toggle, described to the user as working "like dual-zone climate control":
linked (the default) keeps both panes at the same zoom and changing either
one moves both together; unlinking lets each side be sized independently.
Ctrl+scroll over either pane zooms that pane the same way (routed through
one `<Control-MouseWheel>` binding on the window plus
`_pane_side_for_widget()`, which walks up from the widget under the cursor
to find which scrollable frame it belongs to, so it keeps working across
pane rebuilds without needing to rebind every child widget). Zoom applies
uniformly to every preview type - PDF pages, images, and now also DOCX/TXT
text blocks (font size and box size scale with `target_width`, reusing the
same `render_document_preview(target_width=...)` path). Rebuilding a pane
for a zoom change reuses the same `_rebuild_original_pane`/
`_rebuild_result_pane`/`_reload_pdf_pane` helpers a magic pen save already
used; a related gap surfaced while wiring this in and was fixed in the
same pass: `_reload_pdf_pane()` destroyed and recreated the magic pen's
canvases without repainting any still-pending (unsaved) overlay, so simply
zooming while mid-edit made an in-progress selection look like it had been
discarded even though the underlying `pending_remove_keys`/
`pending_add_rects` state was untouched. Verified functionally (resize
actually changes window dimensions; linked zoom mirrors both panes;
unlinking makes them diverge; a pending overlay's rect count is unchanged
across a zoom-triggered rebuild) and visually via screenshot. Full suite:
306 tests.

Two follow-up reports from the user's own hands-on testing of the above:
the window still would not maximize, and the 🔗 link icon was not
intuitive without already knowing the convention. The real cause of the
first was `window.transient(app.root)`: on Windows, a transient window is
treated as a dialog of its parent and loses the native maximize button
even with `resizable(True, True)` set, regardless of anything else in the
window's configuration - removing that one call (this window does not
need dialog-parenting behavior) fixed it, confirmed by `wm_transient()`
now reporting empty and a programmatic resize actually changing the
window's dimensions. For the icon, swapped the static 🔗 for a padlock
that changes glyph with state (🔒 linked / 🔓 independent - closer to the
"lock together" convention used for paired values in other tools, and the
glyph itself now hints at the meaning instead of relying on color alone)
plus a hover tooltip describing the *current* state and what clicking does
next, sourced from new pure `zoom_link_glyph`/`zoom_link_tooltip_text`
functions. Also added a lightweight one-time onboarding hint: the first
time `ComparisonWindow` is ever opened, the link tooltip auto-flashes for
a few seconds without needing a hover; a small local `IconTooltip.flash()`
helper drives it, and a tiny local JSON file
(`~/.anonimizer/ui_hints_seen.json`, hint ids only - same "no database,
just a small local file" pattern as the History tab's recent-folders
list) remembers it has been shown so it never repeats. Verified
end-to-end (`wm_transient` empty, glyph codepoint changes between the two
padlock states, the hint fires on a first-ever open and is confirmed
suppressed on a second, separate window instance once already recorded as
seen) and visually via screenshot. Full suite: 312 tests.

A batch of hands-on-testing feedback (7 items) covering both `ComparisonWindow`
polish and two bigger topics: (1) a new preview window opened behind the
one already on screen - `ComparisonWindow` now calls `.lift()`/
`.focus_force()` once fully built, and the "Zamknij" button plus the
native close (X) now route through one `_close()` that also brings
`app.root` back to front, via a new shared `_bring_window_to_front()`
helper also applied to `SettingsDialog`/`SummaryDialog` for consistency.
(2) A fixed 50/50 split between the two panes - replaced with a real
`tk.PanedWindow` (draggable sash) so one pane can be resized at the
other's expense, like a normal split view; `_build_pane_header`/
`_build_magic_pen_toolbar` were unchanged internally (they just return a
frame) and only their call sites moved from `.grid()` to `.pack()` inside
the paned window's two container frames. (3) The magic pen's ➕/➖ mode
buttons were confusing (had to switch modes before you could act) -
replaced with a modeless interaction: left mouse button always draws a
new redaction, right mouse button always toggles the rectangle under the
cursor, no mode to pick first; the toolbar now shows a static "✏ LPM /
🧹 PPM" legend instead of clickable mode buttons, and `self.mode`/
`_mode_buttons`/`_set_mode` were removed entirely rather than left dead.
(4) (same fix as item 1's `_close()`). (5) The color legend was barely
readable (small muted-gray text on transparent background) - rebuilt as
a bordered card with a bold "Legenda kolorów:" label, larger dots, and
full-contrast text, shared by both the review screen and the comparison
window. (6a) Confirmed with the user: the "leftover original PDF" they
were seeing is `_ANON_REVIEW.pdf`, a rebuilt-from-text fallback PDF
generated *in addition to* the true `_ANON_VISUAL.pdf` whenever visual
mode is used (`anonymizer.py` around `save_rebuilt_review_pdf_from_text`) -
now redundant given the interactive comparison view; not yet removed/
relocated (see below). Also added, well-scoped and requested outright:
auto-opening the finished output in the OS default application right
after a batch completes - a new `auto_open_mode` Settings choice
(`AUTO_OPEN_MODE_FIRST`/`_LAST`/`_ALL`/`_NONE`, default `_LAST`) drives a
new pure `auto_open_output_names()` (batch order in,
capped at `AUTO_OPEN_ALL_MAX = 10` for `_ALL`) called from
`start_anonymize()` via `_auto_open_batch_results()`, resolving each
chosen item's real file through the existing `preferred_review_output_path()`.
Verified functionally (PanedWindow with 2 panes exists; a plain LMB drag
adds a pending rect and a plain RMB click toggles a removal with no mode
ever set; `_close()` destroys the window without raising;
`_auto_open_batch_results` resolves and would open the correct file).
Full suite: 318 tests.

Two items from that same feedback batch are deliberately NOT done yet and
need their own planning pass before touching code, given their size and
the number of existing files they would touch (mirroring how the magic
pen itself was planned before implementation): (6b) splitting each
output folder into a small set of user-facing deliverables versus
internal/diagnostic artifacts (report, checklist, rebuilt review PDF,
`_MANUAL_EDITS.json`, review status/summary json) that only the app (and
the user's own future re-opens) need - the user's own preference leans
toward a separate location outside the output folder entirely (e.g.
`%APPDATA%`), while the recommendation offered back was a same-folder
hidden subfolder (far less invasive - `review.py`'s folder scanning,
`gui.py`'s report/checklist open paths, and the History/approved-export
flows would all need updating either way, but a hidden subfolder needs
less of them to change) plus a "debug/developer mode" toggle in Settings
that reveals both that subfolder and the existing "(deweloperskie)" raw
report/checklist links (currently always shown) - not yet decided between
the two locations. (7) User/IP protection is intentionally deferred
almost entirely: packaging as a compiled `.exe` once the feature work is
mostly done, and hiding the "(deweloperskie)" links for non-debug users
(folds into the same debug-mode toggle as 6b) are the only concrete asks
so far; the rest was flagged by the user as "a signal, not a spec yet."

Item 6b above is now done: the user confirmed same-folder hidden subfolder
over `%APPDATA%` (simpler, and the recommended tradeoff held: internal
files stay physically with their output, no cross-session path mapping to
maintain). A new `internal_artifacts_dir(output_dir)` in `file_writers.py`
returns (creating and Windows-hiding on first use) `output_dir/_wewnetrzne`.
Per-file/batch path *builders* were redirected there directly - `build_report_path`,
`build_review_checklist_path`, `build_batch_summary_path`,
`build_batch_review_checklist_path` in `file_writers.py`, and
`build_review_status_path`/`build_review_summary_path` in `review.py` -
which meant zero changes to `anonymizer.py`'s per-file/per-mode generation
branching (the fragile, heavily-branched part of the pipeline was never
touched). `manual_redaction.py`'s `manual_edits_path` was redirected the
same way. On the read side, `review.py`'s `_report_names_by_stem`/
`_checklist_names_by_stem`/`_detect_batch_summary_names`/
`_detect_batch_review_checklist_names`/`_risk_level_from_report` and
`export_approved_workspace`'s report-copy source now all resolve through
that same internal folder; `gui.py` got a dedicated
`_open_internal_review_file()` (report/checklist) kept separate from the
existing `_open_review_file()` (the deliverable itself, unaffected, stays
in the main folder), reused by `open_summary`/
`_patch_report_with_manual_count`. Deliberately scoped down from the
original mapping discussed: the `_ANON.txt` plain-text companion that
PDF sources always also produce was *not* relocated, because it is the
same file `detect_review_workspace` uses as its discovery anchor for
PDF-derived review items (the whole review system currently only scans
for `.txt`/`.docx` matching `_ANON(_N)?` in the main folder - PDF variants
like `_ANON_VISUAL.pdf` are only resolved afterward, for display, via
`preferred_review_output_path`); relocating it would have required
redesigning that discovery mechanism, judged too risky for this pass.
`_ANON_REVIEW.pdf` (the auxiliary rebuilt-PDF copy) was left visible for
the same reason: whether it is a deliverable (`REBUILT_REVIEW` mode) or an
auxiliary copy (`VISUAL` mode) depends on `anonymize_pdf_file`'s branching,
and distinguishing the two cases safely needs its own pass. Fixed one
concrete bug caught while updating tests: a pre-existing
`test_manual_edits_path_is_named_after_visual_output` used a fabricated,
never-created path (`C:/out/...`) as a stand-in for "some PDF path" -
harmless before this change, but `manual_edits_path` now creates its
parent internal folder as a side effect, so running that test had been
silently creating a real `C:\out\_wewnetrzne\` folder outside the repo
sandbox; found this by inspecting the disk after a test run, deleted the
stray empty folder, and rewrote the test to use a real temp directory (plus
a new test asserting the internal-subfolder location explicitly). Verified
functionally end-to-end with a real batch run: main output folder holds
only the deliverables (`_ANON.txt`, `_ANON_REVIEW.pdf`, `_ANON_VISUAL.pdf`),
`_wewnetrzne` holds the report/checklist/batch files and is confirmed
Windows-hidden via `GetFileAttributesW`, `open_summary()` reads correctly,
the magic pen sidecar resolves into the internal folder, and approve+export
still correctly copies the deliverable and report into `approved/`. All
~50 existing tests that had hardcoded the old flat-folder assumption were
updated to match, not reverted. Full suite: 321 tests, lint unchanged (84
pre-existing errors, same before and after).

## What Exists

- Repository structure.
- Regex-based plain text anonymization in `src/anonymizer.py`.
- Supported Stage 1 categories: `PESEL`, `EMAIL`, `TELEFON`, and `DATA`.
- UTF-8 TXT reading in `src/file_readers.py`.
- UTF-8 TXT anonymized copy writing in `src/file_writers.py`.
- TXT integration helper `anonymize_txt_file(...)`.
- Basic local DOCX paragraph and simple table text reading in
  `src/file_readers.py`.
- Basic DOCX anonymized copy writing in `src/file_writers.py`.
- DOCX integration helper `anonymize_docx_file(...)`.
- Text-based PDF extraction in `src/file_readers.py`.
- PDF integration helper `anonymize_pdf_file(...)`, which saves anonymized PDF
  text as `_ANON.txt`.
- Optional local OCR support in `src/ocr.py` with controlled statuses:
  `available`, `unavailable`, `dependency_missing`, `engine_not_found`, and
  `unsupported_input`.
- Optional local NER support in `src/ner.py` with controlled statuses:
  `available`, `unavailable`, `dependency_missing`, `model_missing`,
  `disabled`, and `processing_error`.
- Optional local Ollama LLM review support in `src/llm_review.py` with
  controlled statuses: `disabled`, `available`, `unavailable`,
  `ollama_not_found`, `service_unavailable`, `no_model_configured`,
  `model_missing`, `timeout`, `invalid_response`, `processing_error`, and
  `completed`.
- Windows-safe UTF-8 local Ollama subprocess handling with BOM stripping for
  already-anonymized review text before prompt construction.
- Local Ollama review requests sent through the local generate API with
  `stream=false`, `temperature=0`, and a strict JSON schema request format.
- Strict local LLM response parsing that accepts a whole-response markdown
  JSON fence but rejects prose-wrapped or unsafe output as `invalid_response`.
- Local Knowledge Assistant support in `src/knowledge_assistant.py` for
  loading approved anonymized TXT files, chunking them, writing/loading
  `_KNOWLEDGE_INDEX.json`, keyword retrieval fallback, source-cited answers,
  controlled optional local Ollama answer generation, local Ollama/model
  status checks, and local model warm-up.
- CLI support in `src/knowledge_cli.py` for building a local knowledge index
  asking questions against it, checking Ollama/model status, warming up a
  local model, and setting an answer generation timeout.
- Optional spaCy NER model loading with no automatic model download and no
  committed model files.
- Conservative NER false-positive exclusions for selected public
  institution/legal phrases, version-like strings, and selected scientific
  names, reported as label-only counters.
- Original-layout visual PDF output in `src/pdf_redaction.py` for text-based
  PDF inputs, creating `_ANON_VISUAL.pdf` with true redaction annotations
  mapped from detected spans to full PDF word coordinates.
- Auxiliary rebuilt PDF review output in `src/pdf_redaction.py` for PDF inputs,
  creating `_ANON_REVIEW.pdf` from anonymized text only without embedding
  original PDF pages.
- Privacy-safe review checklist generation in `src/checklist.py`, creating
  per-file `_REVIEW_CHECKLIST.txt` files and batch `_BATCH_REVIEW_CHECKLIST.txt`
  files from safe metadata plus anonymized output labels only.
- Optional experimental original-layout true-redacted PDF output in
  `src/pdf_redaction.py` for text-based PDFs using PyMuPDF redaction
  annotations and `apply_redactions()`.
- PDF review/redaction metadata that separates text extraction mode, visual PDF
  type/output, word-coordinate mapping mode, review PDF type, true-redaction
  status, detected categories, TXT anonymized categories, PDF-redacted
  categories, detected-but-not-PDF-redacted categories, and unmapped skipped
  categories.
- Conservative `PERSON_NAME_TYPO` replacement/audit category for typo-shaped
  person names such as `Firstname-Lastname Lastname` and
  `Firstname-LastnamePart1 LastnamePart2`.
- GUI processing status updates between batch files, for example
  `Processing 1/3: filename.pdf` plus `Please wait...`.
- GUI local Ollama model selector that loads installed models with
  `ollama list`, supports models such as `gemma3:4b` when installed, and shows
  a clear no-models-found hint instead of requiring manual typing.
- Internal NER labels: `NER_PERSON`, `NER_ORG`, `NER_LOCATION`, and
  `NER_MISC`.
- Optional image OCR workflow for `.png`, `.jpg`, `.jpeg`, `.tif`, and `.tiff`
  inputs, saving anonymized OCR text as `_ANON.txt`.
- Optional scanned PDF OCR fallback when a PDF has no extractable text and
  local OCR dependencies are available.
- Safe OCR metadata in per-file `_RAPORT.txt` reports and aggregate
  `_BATCH_SUMMARY.txt` reports.
- Safe NER metadata in per-file `_RAPORT.txt` reports and aggregate
  `_BATCH_SUMMARY.txt` reports.
- Safe LLM review metadata in per-file `_RAPORT.txt` reports and aggregate
  `_BATCH_SUMMARY.txt` reports. Metadata is limited to review used/status,
  safe model name, LLM risk level, possible residual category names, and
  manual-review requirement.
- Single-file application dispatcher `anonymize_file(...)`, with optional
  output directory support.
- Batch workflow `anonymize_batch(...)`.
- Simple Tkinter GUI in `src/gui.py` for selecting multiple input files, an
  output folder, an optional private dictionary, and an output folder for
  manual review status tracking.
- Scrollable Tkinter GUI layout with a readable selected-file count.
- GUI actions to remove selected inputs or clear the input list without
  deleting files from disk.
- GUI readiness hint that explains whether input files or an output folder are
  still needed before anonymization can start.
- GUI file selection for implemented OCR-capable image inputs and safe
  aggregate OCR status display in the existing audit/status area.
- GUI checkbox for optional local LLM review and a refreshable local Ollama
  model selector. The GUI shows aggregate LLM review status metadata only.
- Manual review GUI actions to open a selected `_ANON` output or matching
  `_RAPORT` report with the operating system default application.
- Default GUI entry point in `src/main.py`.
- Safe report text generation in `src/report.py`.
- Safe manual review checklist text generation in `src/checklist.py`.
- Report path helper `build_report_path(...)`, which can target the selected
  output folder.
- Collision-safe path helper for `_ANON`, `_RAPORT`, and `_BATCH_SUMMARY`
  outputs.
- Private sensitive terms parsing and replacement in `src/sensitive_terms.py`.
- Dictionary alias parsing with `alias | alias = [LABEL]` support.
- Case-insensitive and whitespace-tolerant private dictionary matching.
- Post-anonymization audit in `src/audit.py`.
- Optional `sensitive_terms_path` arguments in the TXT, DOCX, PDF, and
single-file dispatcher and batch workflows, while the plain text engine still
accepts preloaded `sensitive_terms`.
- `_with_audit` TXT, DOCX, PDF, and dispatcher helpers that return safe audit
  metadata while existing helpers keep their Stage 2-5 return shape.
- Optional GUI selection of a private sensitive terms file path without
  displaying dictionary contents.
- GUI display of post-anonymization audit status, risk counts, and category
  counters only.
- GUI display of safe dictionary status: not selected, loaded, invalid, or
  loaded with no dictionary matches.
- Safe report counters for dictionary labels only.
- Safe report dictionary section with used/status/matches-found metadata.
- Safe report section for post-anonymization audit status, risk level, and
  counters only.
- Safe report section for local LLM review metadata only. Reports do not store
  raw prompts, raw LLM responses, source text, document snippets, detected
  values, raw OCR text, dictionary terms, dictionary aliases, or replacement
  maps.
- Shared dictionary matching semantics for anonymization and audit dictionary
  checks.
- TXT, DOCX, PDF, and dispatcher flows that create safe reports after
  successful anonymization.
- Batch summary report generation with safe filenames, aggregate risk counts,
  aggregate audit category counters, aggregate LLM review status/risk/category
  counters, aggregate PDF redaction status counts, and no private paths.
- Manual review workflow in `src/review.py` for detecting generated `_ANON`
  outputs, pairing safe report and review-checklist basenames, reading safe
  report risk levels,
  applying manual statuses, and saving safe review metadata.
- GUI support for assigning `approved`, `needs_review`, or `rejected` statuses
  without previewing or editing document contents.
- GUI support for showing safe manual-review risk levels and sorting
  `high_risk` outputs first.
- GUI manual-review open action preference for companion `_ANON_VISUAL.pdf`
  files, then experimental `_ORIGINAL_REDACTED.pdf`, then `_ANON_REVIEW.pdf`,
  then legacy `_ANON.pdf`, when a PDF-derived `_ANON.txt` item has a PDF review
  artifact next to it.
- Safe `_REVIEW_STATUS.json` review manifest output.
- Collision-safe `_REVIEW_SUMMARY.txt` review summary output.
- Approved workspace export in `src/review.py` that reads
  `_REVIEW_STATUS.json`, copies only approved `_ANON` basenames into
  `approved/`, optionally copies matching `_RAPORT` files, and writes a safe
  `_APPROVED_INDEX.txt` manifest.
- GUI `Export approved` action in the manual review section.
- Runtime dependency on `python-docx`.
- Runtime dependency on `pypdf`.
- Unit tests for the Stage 1 anonymizer using synthetic values only.
- Unit tests for Stage 2 TXT input/output using synthetic temporary files only.
- Unit tests for Stage 3 DOCX input/output using synthetic temporary files only.
- Unit tests for Stage 4 text-based PDF input/output using generated
  synthetic temporary PDFs only.
- Unit tests for the Stage 5 single-file dispatcher using synthetic temporary
  TXT files only.
- Unit tests for Stage 6 safe report generation and TXT/DOCX/PDF report
  integration using synthetic temporary files only.
- Unit tests for Stage 8 private dictionary parsing, replacement order,
  integration, and report safety using synthetic values only.
- Unit tests for Stage 9 post-anonymization audit detection, report safety,
  workflow integration, and GUI/dispatcher audit metadata safety using
  synthetic values only.
- Unit tests for Stage 10.1 dictionary path flow, dictionary report status,
  invalid dictionary handling, loaded-without-matches status, and TXT/DOCX/PDF
  dictionary-path compatibility using synthetic values only.
- Unit tests for Stage 11 dictionary aliases, backward compatibility,
  case-insensitive matching, whitespace normalization, longer aliases before
  shorter aliases, label-only counters, safe alias reports, and audit
  dictionary matching using synthetic values only.
- Unit tests for Stage 12 collision-safe naming, output workspace behavior,
  batch TXT/DOCX/PDF processing, safe error continuation, and safe batch
  summary content using synthetic values only.
- Unit tests for Stage 13 generated output detection, report pairing, missing
  report handling, manual statuses, safe review status JSON, safe review
  summary text, collision-safe review summary naming, Stage 12 regression, and
  report/audit regression using synthetic values only.
- Unit tests for Stage 17 approved workspace export, missing review status,
  no-approved handling, optional report copying, missing reports,
  collision-safe export naming, and safe approved index contents using
  synthetic values only.
- Unit tests for Stage 18 end-to-end MVP workflow validation, including simple
  low-risk TXT approval/export, mixed-risk review prioritization, dictionary
  aliases, DOCX and text-based PDF participation, safe metadata, and generated
  output ignore coverage using synthetic values only.
- Unit tests for Stage 19 OCR availability detection, missing-dependency and
  missing-engine behavior, mocked image OCR, text-based PDF non-OCR
  regression, scanned PDF OCR fallback, safe OCR report metadata, and safe OCR
  batch summary errors using synthetic inputs only.
- Unit tests for Stage 20 NER availability detection, missing spaCy behavior,
  missing local model behavior, mocked entity detection, PERSON/ORG/location
  anonymization, NER counters, safe report metadata, safe batch summary
  metadata, DOCX workflow integration, and no-crash fallback using synthetic
  inputs only.
- Unit tests for Stage 21 Ollama availability detection, missing command,
  service unavailable, no model configured, missing model, mocked successful
  LLM review, timeout handling, invalid response handling, structured response
  parsing including fenced JSON, risk-level mapping, residual category
  aggregation, safe report and batch summary metadata, no-crash unavailable
  fallback, and review input policy using synthetic/mocked data only.
- Unit tests for Stage 22 approved document loading, ignoring non-ANON files,
  deterministic chunk metadata, index creation, keyword retrieval fallback,
  source references, controlled no-context behavior, controlled
  Ollama-unavailable behavior, mocked local generation, CLI behavior, and
  generated knowledge index ignore coverage using synthetic data only.
- Unit tests for Stage 22.1 local Ollama status checks, installed-but-not-loaded
  model status, warm-up unavailable/timeout handling, ask-timeout behavior, and
  CLI status/warm-up commands using mocked local behavior only.
- Unit tests for Stage 23 text-based PDF redaction output, hidden-text removal
  checks on generated synthetic PDFs, safe report/batch redaction metadata,
  manual-review PDF open preference, and the `PERSON_NAME_TYPO` pattern.
- Unit tests for Stage 24 pilot corrections covering rebuilt review PDF output,
  reduced broad PDF redaction of ordinary address words, safe and strict
  experimental original-layout PDF redaction scopes, conservative safe-scope
  `NER_PERSON` PDF redaction, malformed hyphenated
  person-name detection in TXT/DOCX/PDF flows including Unicode dash variants,
  punctuation, non-breaking spaces, Polish letters, and split DOCX runs, a
  non-person hyphenated phrase regression, NER false-positive exclusions,
  line-break person detection, privacy-safe per-file and batch review
  checklist creation, checklist/report/manual-review pairing, batch progress
  callback formatting, local Ollama model list parsing, and GUI model selector
  fallback behavior.
- Manual MVP smoke-test checklist in `docs/MVP_MANUAL_TEST_CHECKLIST.md`.
- Synthetic sample text files in `tests/sample_data/`.
- Synthetic example dictionary in `examples/sensitive_terms.example.txt`.
- Synthetic seed dictionary example in `examples/sensitive_terms.seed.example.txt`.
- Synthetic manual-review candidate file in
  `examples/dictionary_candidates.example.txt`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.
- Stage 7 portfolio/release review documentation updates for README quality,
  user guidance, technical flow clarity, roadmap status, security assumptions,
  and honest portfolio text.

## What Does Not Exist Yet

- Advanced GUI preview or editing workflow.
- Drag and drop.
- AI/API calls, cloud services, cloud LLMs, online processing, databases, RAG,
  vector databases, or local LLM use beyond the optional post-anonymization
  Ollama review metadata layer.
- Edited image output or scanned-PDF/OCR visual redaction.
- Bundled Tesseract binaries, OCR language models, or OCR installers.
- Detailed report generation beyond safe counters, safe audit metadata, and
  manual review notes.
- Automatic approval based on audit results or report contents.
- Moving rejected or needs-review files into separate folders.
- Embedding-based retrieval, `bge-m3` embeddings, or a vector database.
- Knowledge Assistant GUI or chat history.
- Scanned-PDF/OCR bounding-box visual redaction.
- NER span coordinate mapping back into PDF pages.
- Production-grade names, surnames, cities, organizations, or context-based
  detection.
- Production-grade OCR quality handling.
- LLM-based primary anonymization, document rewriting, chat UI, prompt logging,
  raw response logging, or automatic approval.

## How to Run

Run the GUI entry point:

```bash
python src/main.py
```

The GUI module launch is also supported:

```bash
python -m src.gui
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Current Limitations

- The core engine processes only a plain Python string.
- File input/output supports `.txt` files, basic `.docx` files, `.pdf` files
  with extractable text or optional OCR fallback, and OCR-capable image inputs.
- TXT outputs are written to the selected output folder with an `_ANON` suffix.
- DOCX outputs are written to the selected output folder with an `_ANON` suffix.
- PDF input is extracted as text and saved as `_ANON.txt`; the default manual
  review package also includes `_ANON_VISUAL.pdf` as the main original-layout
  review artifact, `_ANON_REVIEW.pdf` as an auxiliary rebuilt-text review PDF,
  and `_REVIEW_CHECKLIST.txt`.
- Experimental original-layout text-based PDF redaction can create
  `_ORIGINAL_REDACTED.pdf` when explicitly selected and when PyMuPDF can locate
  supported matches.
- Image input is OCR-extracted and saved as `_ANON.txt`; no edited image is
  created.
- Existing output files are not overwritten silently; numbered suffixes such as
  `_2` and `_3` are used when needed.
- Batch processing is sequential and records per-file errors in the safe batch
  summary.
- Per-file reports contain only safe metadata, category counters, and manual
  review notices. They do not contain source values, full input paths,
  filenames, dictionary source aliases or terms, or replacement maps.
- Date detection is limited to high-confidence numeric formats.
- Phone detection is intentionally conservative.
- Broader address and identifier detection remains conservative and
  audit-only; it is not full entity detection.
- DOCX formatting preservation is basic only.
- DOCX headers, footers, comments, footnotes, form fields, text in images, and
  advanced elements are not handled.
- OCR is optional, local, and dependency-dependent. Scanned PDF fallback and
  image OCR require local Python OCR libraries plus the Tesseract executable
  and language data installed outside the repository.
- NER is optional, local, and dependency/model-dependent. It requires spaCy and
  a local Polish model installed outside the repository.
- NER can miss or misclassify people, organizations, locations, and other
  entities.
- OCR can be inaccurate. OCR output still goes through deterministic
  anonymization and must be manually reviewed.
- Rebuilt PDF review output is readable but not layout-preserving. It is
  generated from anonymized text only. Experimental original-layout redaction
  can miss unusual encodings, fragmented glyphs, rotated text, form fields,
  annotations, or text in images, and can still over-redact when strict NER
  scope is selected.
- The GUI processes selected files sequentially. Document preview, drag and
  drop, and a side-by-side comparison view exist; manual redaction editing
  ("magic pen") exists only for PDF outputs and only for true-redacted
  rectangles - DOCX/TXT outputs and other kinds of editing are not
  supported.
- The manual review workflow tracks statuses and, for PDF outputs, manual
  redaction rectangles only. It does not inspect, validate, or automatically
  approve anonymized document contents beyond that. Opening a selected
  output or report delegates to the operating system default application
  and does not add an in-app viewer for non-preview actions.
- Review status and summary files contain safe generated basenames and status
  counts only, not full paths, source data, document excerpts, private
  dictionary terms, aliases, tracebacks, or replacement maps.
- Approved workspace indexes contain safe basenames, copied report counts,
  missing-report basenames, safe risk levels when already available, and
  manual-decision disclaimers only. They do not contain document text, source
  values, private dictionary terms, aliases, full paths, tracebacks, or
  replacement maps.
- Report files are plain TXT only and do not include a detailed audit trail.
- Reports and batch summaries include safe OCR metadata only; they do not
  include raw OCR text.
- Reports and batch summaries include safe NER metadata only; they do not
  include detected entity text.
- Reports and batch summaries include safe LLM review metadata only; they do
  not include raw prompts, raw LLM responses, source text, document snippets,
  detected entity values, dictionary terms, dictionary aliases, raw OCR text,
  or replacement maps.
- Private dictionary matching is deterministic, case-insensitive, and tolerant
  of extra internal spaces, but it is not fuzzy matching, inflection handling,
  automatic entity recognition, AI, or NER.
- The real private dictionary must stay outside git, either outside the
  repository or inside an ignored folder such as `private/`.
- Post-anonymization audit matching is conservative and regex-based. It can
  miss sensitive data and can warn on harmless text.
- Audit status `ok` and risk level `ok` do not prove complete anonymization.
  Manual review is still required.
- Audit risk levels are prioritization helpers only. They are not automatic
  approval decisions.
- Audit results and reports include only categories, counters, status, risk
  level, and manual review metadata, never source values, snippets,
  dictionary terms, full document text, or replacement maps.

## Last Completed Committed Stage

Stage 26: magic pen manual PDF redaction editor, a same-day self-review
fixing a toggle bug/unsafe overwrite/stale cursor, a fix for a `fitz`
deprecation warning the earlier Stage 25.1 fix missed, a resizable/
maximizable comparison window with independent or linked per-pane zoom, a
follow-up fixing the maximize button itself plus a padlock-based,
tooltip-and-hint-backed redesign of the zoom-link icon, a further round
of hands-on-testing feedback (window focus in/out, a draggable pane
splitter, modeless LMB/RMB magic pen interaction, a more visible legend,
a new auto-open-result Settings option), and moving internal/diagnostic
output files into a hidden `_wewnetrzne` output subfolder.

```text
07f273b Move internal/diagnostic artifacts into a hidden output subfolder
```

## Next Logical Step

The next candidates, not yet started: (a) relocating the PDF-derived
`_ANON.txt` companion and `_ANON_REVIEW.pdf` into the internal folder too
(deliberately left out of the pass above - see the narrative for why:
review discovery currently anchors on `_ANON.txt`, and `_ANON_REVIEW.pdf`
is sometimes a deliverable depending on PDF output mode); (b) a
"debug/developer mode" Settings toggle revealing the internal folder and
the existing always-on "(deweloperskie)" report/checklist links; (c) the
still-open user/IP-protection topic (packaging as a compiled `.exe` once
feature work is mostly done; hiding the dev links folds into (b); the
rest was flagged by the user as "a signal, not a spec yet").

Use the completed Stage 26 GUI (including the magic pen) in real local
pilot/use and make future improvements only from observed needs otherwise.
A possible later stage is extending manual redaction editing to DOCX/TXT
outputs, which have no word coordinates and would need a different,
text-selection-based mechanism - deliberately left out of Stage 26.

Idea proposed by the user, not yet scoped or started: a fully manual
"start to finish" mode, where the user opens the original document and
does all redaction with the magic pen from the start, instead of running
automatic detection first. In that mode, NER/regex/dictionary detection
would run only *after* the manual pass as an optional verification step,
surfacing anything it thinks was missed as suggestions the user can accept
or dismiss - never auto-redacting on its own in that mode. Also proposed:
letting the scroll wheel cycle through the magic pen's category
colors/labels (the same set shown in the legend) while adding a manual
rectangle, instead of everything defaulting to one generic "RECZNE" label.
Needs its own planning pass (interaction design, how a "start to finish"
document's report/counters should look, whether per-category manual labels
change the existing single-`RECZNE`-label design) before implementation.

Other potential future work still requires an explicit project decision,
especially OCR quality improvements, NER candidate export, installer work,
AI/API integration, broader LLM features, databases, broad NLP/entity
detection, packaging, release automation, embedding retrieval with
`bge-m3`, or a general town/city name database.

## Warning

This repository is still an early-stage portfolio MVP. Do not use it to
anonymize real documents without manual review and project-specific safety
checks.
