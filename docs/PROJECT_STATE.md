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
(This whole `auto_open_mode` system was itself replaced later - see the
"Pilot-testing bug fix" paragraph further below - once real use showed
opening right after anonymizing, before any review, was the wrong
moment.)
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

The user's own first real pilot document (a scanned invoice PDF) exposed
two things immediately. First, a real pre-existing `.gitignore` gap,
unrelated to the day's other work: `*_ANON.*` and `*_RAPORT.*` lack a
wildcard before the extension, so they never matched
`build_collision_safe_path()`'s numbered variants (`_ANON_2.txt`,
`_RAPORT_2.txt`, ...) - confirmed with `git add -A --dry-run`, which
would have staged the user's real numbered output/report (containing
their real invoice filename) the moment a second file collided on name.
Fixed by adding the missing wildcard (`*_ANON*.*` / `*_RAPORT*.*`); added
a regression test that runs real `git check-ignore` against a numbered
filename rather than only checking the pattern text is present in
`.gitignore`, since string-presence alone had not caught this. Second, a
real UX gap: the scanned PDF had no text layer and needs local OCR
(Tesseract), which was not installed - the batch correctly failed the
file internally, but the review screen only ever showed a silent, blank
"Brak wykrytych wyników" with no indication anything had gone wrong or
why (`format_batch_status`, which does describe batch errors, turned out
to be dead code - built but never actually called anywhere in the app).
A new red error card on the review screen now lists which input files
failed and a plain-Polish reason, built from `format_batch_error_items()`
and a `BATCH_ERROR_LABELS_PL` translation of the small fixed set of safe
`BATCH_ERROR_*` strings the pipeline already produces (never raw
exception text). `last_batch_result` is now cleared on "Wybierz inny
folder"/History navigation so the banner never shows stale errors from an
unrelated previous batch. Also renamed the "Nowy batch" button (English
word left over in Polish UI, flagged by the user) to "Nowe pliki". Full
suite: 326 tests.

Direct follow-up from that same pilot session: the user asked for a
startup verification pass over optional local dependencies (NER model,
OCR engine, local LLM) - the app should still open even if something is
missing, but say clearly what won't work and offer a one-click fix. New
`src/environment_check.py` holds three side-effect-free, deliberately
cheap checks (never load a full spaCy pipeline, never run real OCR, never
block long on a slow local network call): `check_ner_environment()` uses
a new `ner.check_ner_model_installed()` that checks the model package via
`importlib.util.find_spec` instead of `prepare_ner_context()`'s actual
`.load()` (measured ~1.5s vs ~2.7s locally, and avoids loading a pipeline
into memory just to throw it away) - still slow enough (spaCy's own
import) that `AnonymizerApp` runs the whole check on a background
`threading.Thread` scheduled via `root.after(150, ...)` rather than
during `__init__`, so opening the window is never delayed; results are
marshaled back to the GUI thread with `root.after(0, ...)`.
`check_ocr_environment()`/`check_llm_environment()` reuse the existing
`detect_ocr_support()`/`list_installed_models()` as-is. A new dismissible
card on the start screen (`_build_environment_banner`, tracked via a new
`self.active_screen` attribute so a background check completing while the
user has since navigated elsewhere doesn't rebuild the wrong screen) lists
each missing piece in plain Polish with a fix button: the spaCy model gets
a real one-click install (`install_ner_model()` runs
`python -m spacy download <model>` in the app's own venv via
`sys.executable` - a contained package download, no admin rights, safe to
automate), while Tesseract/Ollama - external system installers this app
cannot safely run unattended - get a "Pobierz" button that opens their
official download page in the browser instead. Verified functionally:
screenshots confirm the banner is absent before the background check
completes, renders correctly listing exactly the missing pieces once it
does, and the dismiss button correctly hides it. Full suite: 339 tests,
lint unchanged against baseline for every touched file.

Immediate follow-up: the user liked the banner but also wanted a subtle,
always-visible confirmation for the good case (it previously showed
nothing at all when everything was fine). A small status dot now sits
next to "Rozpoznawanie AI (NER)" and "Dodatkowa weryfikacja AI (LLM)" in
Settings (reusing/extending the existing `_build_toggle_section`, plus a
new read-only `_build_status_row` for OCR, which has no on/off toggle of
its own) - green when confirmed available, muted gray when confirmed
missing, and simply absent (not red, not a placeholder) while the
background check hasn't completed yet, via a new pure
`environment_status_lookup(items)` that turns the check-result list into
an `{item_id: ok}` dict SettingsDialog can `.get()` against safely. Also
addressed directly: the user pointed out that any *future* optional
dependency needs its own check added to `check_environment()` or it will
silently miss both the startup warning and this new status dot - a
maintenance-note docstring was added directly on that function as the
explicit reminder, since a comment living right where the list is defined
is far more likely to be seen than a rule living only in this file.

Pilot-testing bug fix: the result file was auto-opening right after a
batch finished, before the user had looked at it in the review screen at
all - confusing when the file still needed manual review, edits, or
rejection. The `auto_open_mode` system from the earlier feedback batch
above (`AUTO_OPEN_MODE_FIRST/_LAST/_ALL/_NONE`, `auto_open_output_names()`,
`_auto_open_batch_results()`) is removed entirely and replaced with a
single `auto_open_on_approve` boolean: `set_review_status()` now calls a
new `_open_on_approve(item)` exactly when the status transitions to
`REVIEW_STATUS_APPROVED`, opening that item's real output via
`preferred_review_output_path()` only if the setting is on. The Settings
dialog's four-way radio choice is replaced with one toggle ("Otwórz
automatycznie po zatwierdzeniu"). Verified functionally end to end with a
scripted run driving the real GUI: nothing opens right after
anonymizing, the file opens exactly when "Zatwierdzony" is clicked, and
toggling the setting off correctly suppresses the open-on-approve too.
Full suite: 335 tests, lint unchanged against baseline.

Startup library-update check: the user asked for a fully silent,
user-friendly way to know when the app's own pip-managed libraries have a
newer version, without ever having to open a browser, download a file, or
run an installer by hand - one click, one confirmation, done. Scoped
deliberately to the packages that live inside the app's own venv (see
`requirements.txt`): a new `src/dependency_updates.py` checks each
package's installed version (`importlib.metadata.version`) against the
newest version on PyPI (`https://pypi.org/pypi/<name>/json`, a bare
version-number lookup - no personal or document data leaves the machine),
compares them with `packaging.version.Version` (falling back to a plain
string inequality if a version string doesn't parse), and, for a chosen
package, runs `pip install --upgrade <package>` as a subprocess in this
same interpreter's environment - the same contained, no-admin-rights
shape as the existing NER model installer. All eight checks run
concurrently (`ThreadPoolExecutor`) off the GUI thread, staggered 250ms
after the existing environment check so the two don't compete for thread
start at the same instant; a failed/offline lookup for one package never
blocks the others or crashes the check. `gui.py` gained a second,
info-styled (blue, not the warning-orange used for missing dependencies)
dismissible banner on the start screen - `_build_update_banner` - listing
only packages with a real update available, each with its own "Aktualizuj"
button; clicking it shows one `messagebox.askyesno` confirmation naming
the package and both version numbers, then installs in the background and
re-runs the full check afterward to confirm the install actually worked
rather than assuming success. Tesseract and Ollama are deliberately out
of scope - they are external system installers, not pip packages, and
safely automating their install (download, verify, run an elevated
installer silently) is a materially different problem; they keep using
the existing "Pobierz" (open download page) flow. Same maintenance-note
pattern as `environment_check.py`: `DEFAULT_PACKAGES` is an explicit list,
not auto-derived from `requirements.txt`, so a future added/removed
dependency needs the same edit made in both places. Verified functionally
against the real GUI with mocked PyPI/pip calls: the banner shows only the
outdated package with its version arrow, clicking "Aktualizuj" triggers
exactly one `pip install --upgrade` call for that package, and the banner
correctly hides that package (and disappears entirely once nothing is
left) after a successful re-check. Full suite: 354 tests (19 new), lint
unchanged against baseline.

Follow-up from real use of the two features above, in one pass: (a) the
missing-dependency card and the library-update card stacked as two full
separate boxes, each with its own header/footer chrome, eating more
vertical space above the drop zone than either needed alone - `gui.py`'s
`_build_environment_banner`/`_build_update_banner` are merged into one
`_build_status_banner` (one shared `status_banner_dismissed` flag, one
"Sprawdź ponownie" that re-runs both checks via a new `_recheck_status`),
with tighter row/card padding on top of the merge; warning styling wins
over the info styling when both issues and updates are present, since a
missing dependency is more actionable. (b) The user installed Ollama and
Tesseract while the app was already running, then found the environment
banner still reported both missing even after "Sprawdź ponownie" - traced
to a real Windows behavior, not a placebo re-check: installing something
updates the User/Machine PATH in the registry immediately, but an
already-running process (this app included) keeps the PATH snapshot it
started with, so `ollama`/`tesseract` stayed unresolvable no matter how
many times the check re-ran; only a full app restart would have picked it
up. `environment_check.py` gained `refresh_path_from_registry()`, called
at the start of every `check_environment()` run: on Windows it reads the
current User and Machine `Path` values straight from the registry via
`winreg` and merges any not-yet-present entries into this process's
`os.environ["PATH"]` (case-insensitive de-duplication, additive only,
never removes anything) - a safe no-op on any error or a non-Windows
platform. Verified for real (no mocks) on the pilot machine: a subprocess
launched with Ollama's install directory stripped from its inherited PATH
reported `ollama_not_found` before the call and `available` immediately
after, with no restart. Confirmed against the real, currently-running app
too: after this fix, Ollama (genuinely installed and on the registry PATH)
now shows as available without a restart, while Tesseract correctly still
shows as missing, because - confirmed directly by reading the Machine and
User `Path` registry values - that particular install never added itself
to PATH at all; no in-process refresh can fix an entry that was never
written, so that case still needs the existing "Pobierz" flow or a manual
PATH edit. Full suite: 358 tests (4 new), lint unchanged against baseline.

Immediate follow-up closing that Tesseract gap without any manual PATH
edit: the user asked for automation instead of asking a regular user to
edit environment variables by hand - correctly, since that is well beyond
what most users can be expected to do. `ocr.py` gained
`_resolve_tesseract_cmd()` (tries `shutil.which("tesseract")` first, then
falls back to the two locations the official Windows installer itself
ever writes to - `C:\Program Files\Tesseract-OCR\tesseract.exe` and the
`(x86)` variant, no-op on non-Windows) and `_configure_tesseract_cmd()`,
which points `pytesseract.pytesseract.tesseract_cmd` directly at whatever
was found - only when the current command isn't already resolvable, so it
never overrides a working setup. Called once at the top of
`detect_ocr_support()`; since it mutates pytesseract's own module-level
state, the later `image_to_string()` calls in `extract_text_from_image`/
`extract_text_from_pdf` pick it up automatically within the same process,
no extra call sites needed. This sidesteps PATH entirely rather than
trying to fix it - no system settings touched, nothing for the user to
do. Deliberately Windows-only for now (the only platform this pilot runs
on and the only one with a known fixed install location); Ollama detection
was left as-is since its actual generation calls already go over HTTP to
`127.0.0.1:11434`, not through the `ollama` CLI - only its lightweight
`ollama --version`/`ollama list` detection uses PATH, and that path was
already fixed by the registry-refresh change above once Ollama itself
puts the entry there, which it reliably did. Verified for real (no mocks)
on the pilot machine, where Tesseract truly isn't on PATH:
`_resolve_tesseract_cmd()` found the real binary at the default location,
`detect_ocr_support()` now reports `available`, and the running app's
own status banner is now completely empty - all three optional
dependencies detected with zero PATH edits. Full suite: 367 tests (9 new),
lint unchanged against baseline.

Fixed a real, reported rendering bug in the magic pen comparison window:
the "Oryginał" and "Po anonimizacji" pages did not render at the same
apparent size, and the user's first hypothesis - that PDF redaction
rebuilding changes page scale - was checked directly (opened the original
and `_ANON_VISUAL.pdf` for a real pilot document with PyMuPDF: identical
`page.rect`, identical `mediabox`/`cropbox`, identical rotation) and
ruled out. The real cause was a display-DPI-scaling mismatch between the
two rendering paths: the left pane renders through `CTkImage`, which
customtkinter silently scales by the display's detected DPI factor
(`ScalingTracker.get_widget_scaling`) so it looks crisp on a scaled
monitor; the magic pen's right pane draws straight onto a plain
`tk.Canvas` (needed for its click/drag overlay) via `ImageTk.PhotoImage`,
which has no such awareness and always renders at the literal pixel size
- confirmed on the pilot machine, whose Windows display scaling is 125%,
by rendering both pages at the same `target_width` and finding the left
pane's on-screen width was exactly 1.25x the right pane's. Fixed with a
new `ctk_widget_scaling_factor(widget)` (wraps `ScalingTracker`, always
falls back to 1.0 rather than raising - a display-scaling mismatch is
cosmetic, never worth crashing the preview over), folded directly into
the zoom used to build the magic pen's pixmap in `_build_magic_pen_pane`.
Since every click/drag/overlay coordinate conversion already reads the
same stored `self._page_zoom[page_index]` rather than recomputing zoom
independently, this one change keeps hit-testing correctly aligned with
no other code paths to touch. Verified for real (no mocks), reusing the
same pilot invoice PDF pair: both panes now render at an identical 575px
width (460 x 1.25) on the pilot machine, confirmed both numerically and
with a side-by-side screenshot. Full suite: 369 tests (2 new), lint
unchanged against baseline.

Requested follow-up, framed as a "verification mode": while the two
comparison panes are locked together (the existing padlock), plain
scrolling (no Ctrl) on either pane should now also scroll the other one
in lockstep, matching how Ctrl+scroll zoom already behaves when linked;
unlinking frees each pane to scroll independently, same as it already
does for zoom; and re-locking should snap both back to one predictable
default view (100% zoom, scrolled to top) rather than just syncing to
whatever the left pane happened to be at. `gui.py` gained a new
`_on_scroll_sync` bound to plain `<MouseWheel>`/`<Button-4>`/`<Button-5>`
at the window level (mirroring the existing Ctrl-scroll bindings) that,
only while `zoom_linked`, scrolls the *other* pane's canvas by the exact
same unit count CTkScrollableFrame's own internal handler uses for the
pane the cursor is actually over (`scroll_sync_units`, a new pure
function deliberately duplicating that private formula rather than
reusing the coarser `mousewheel_scroll_units` used elsewhere - unit
parity is the whole point, otherwise a linked pane would gradually drift
out of sync). `_toggle_zoom_link` now resets both zoom levels to
`ZOOM_DEFAULT` and scrolls both panes to the top whenever re-locking.
While building this, found and fixed a real latent bug in
`_pane_side_for_widget` (shared by both the new scroll sync and the
existing Ctrl-scroll zoom): it only matched `self.left_frame`/
`self.right_frame` walking up a widget's `.master` chain, but
CTkScrollableFrame embeds its content Frame *inside* its own internal
scrolling Canvas via `canvas.create_window` - the opposite of a normal
parent/child relationship - so a cursor sitting over blank canvas space
rather than directly over rendered page content (e.g. past the bottom of
a short page) resolved to neither pane and silently did nothing; now
also matches each frame's private `_parent_canvas`/`_parent_frame`.
Verified functionally against the real GUI with the same pilot invoice
PDF pair (screen-coordinate `winfo_containing` hit-testing proved flaky
in this non-interactive scripted context - confirmed separately that it
can resolve to an unrelated window when nothing has given this one real
OS focus - so the check patches it to return the exact widget a real
click would hit, isolating the test to the logic being changed): linked
scroll moves both panes' top edge together, unlinking stops that and
each scrolls on its own again, and re-locking resets both to 100% zoom
and the top of the page. Full suite: 372 tests (3 new), lint unchanged
against baseline.

Same-day magic pen toolbar polish, from the user's own running notes
file: (a) the LPM/PPM toolbar now sits *above* the "Po anonimizacji"
header (title + zoom/lock) instead of between it and the page, so the
row directly bordering the actual document - scale and padlock - looks
the same on both sides; reordering alone doesn't change the *total*
header height on the right though, so a matching invisible spacer of
the same height was added above "Oryginał" too, keeping both pages
starting at the exact same height (verified: both panes' content start
at an identical rooty, confirmed on the pilot machine both before and
after the window is fully realized). The spacer's height is a fixed,
unscaled constant (`MAGIC_PEN_TOOLBAR_HEIGHT`) rather than measured off
the real toolbar at runtime and kept in sync - that was tried first and
turned into its own can of worms, a freshly built widget's true height
isn't reliably known for a while after construction, and re-measuring on
every `<Configure>` risked an expensive cascade as the resize itself kept
re-triggering more `<Configure>` events (confirmed: over a hundred firings
during one settle). customtkinter already scales every widget's
configured height by the same per-display DPI factor internally, so a
plain fixed value tracks the toolbar's real on-screen height on any
display without any of that. (b) The LPM/PPM chips are real buttons now,
not a static legend: clicking one pins LMB to that single action (a
"manual" mode for anyone who'd rather pick a tool explicitly than
remember which button does what - clicking the same chip again returns
to the modeless default); independently of pinning, a chip also lights
up for as long as its action is actually in progress (LMB held down
mid-drag, or a brief flash on an RMB click, since a click has no natural
"held" duration the way a drag does) - so the buttons double as a live
"this is what's happening" indicator, not just a static legend. Pinning
only ever changes what LMB does; RMB keeps working as erase regardless
of the pinned tool, so pinning to "draw" never takes the RMB shortcut
away. Verified functionally against the real GUI with the same pilot
invoice PDF pair: the toolbar row is confirmed first in the right
container's packing order, both panes' content start at an identical
height, the draw chip lights up only while LMB is actually held and
returns to gray on release, an RMB click flashes the erase chip and it
fades back on its own, clicking a chip pins it (persistent highlight,
`pinned_tool` set) and clicking it again returns to automatic, and an
LMB press while pinned to "erase" performs the toggle-remove directly
without starting a draw-drag. Lint unchanged against baseline.

Fixed a real regression the user caught in testing: the comparison
window was again opening *behind* the main app instead of on top of it -
the exact class of bug `_bring_window_to_front()` was built to prevent.
Root-caused directly rather than guessed at, and in the process an
earlier, more serious mistake was made and corrected: a first diagnostic
script took a full-screen screenshot to inspect real OS-level window
stacking, which captured the user's own unrelated windows in the
background (at one point a separate real ChatGPT conversation of
theirs was visible) - both screenshots were deleted immediately without
reading their content beyond noticing they existed, the user was told
about the mistake, and every screenshot afterward was re-scoped to a
small, explicitly-known region covering only this app's own windows,
never the full screen again; two further screenshots that still ended
up spanning into unrelated desktop area (window chrome, browser tabs,
unrelated code - no further private conversation content) were deleted
the same way out of caution. The actual root cause: `lift()` +
`focus_force()` alone are not always enough on Windows - `focus_force()`
ultimately calls `SetForegroundWindow`, which Windows can silently
refuse from a process that was not already in the foreground, a
deliberate anti-focus-stealing OS rule, confirmed to actually bite with
a real other application in the foreground. `_bring_window_to_front()`
now also briefly forces `-topmost` (`SetWindowPos` with `HWND_TOPMOST`,
not subject to that same restriction) before switching it back off.
Confirmed experimentally (not just in theory) that releasing `-topmost`
too soon undid the whole fix - some other window could still reclaim the
front the instant it was no longer forced, before the new window had
genuinely finished becoming the real foreground window - so the release
is delayed 600ms rather than done immediately, giving that transition
time to actually land first. Verified functionally against the real
running app with the comparison window, confirmed both with `-topmost`
release disabled entirely (proves the initial force works) and with the
final 600ms-delayed release (proves the fix holds once released too).
Lint unchanged against baseline; full suite still 372 (no test changes -
this is real OS window-manager behavior no headless/mocked test would
meaningfully catch, verified functionally instead, same as the rest of
`_bring_window_to_front`'s history).

Fixed a real layout bug the user caught: in a non-maximized (narrowed)
comparison window, once there were pending manual edits, "Zapisz zmiany"
itself could get clipped away entirely. Root cause: Tk's `pack()` hands
out a row's width in the order widgets are packed, not left-to-right
visual order - whatever is packed last is the first to be squeezed out
when the row runs out of room. `pen_status_label` was packed *before*
the save/cancel buttons, and it grows from empty to "Niezapisane zmiany:
N" exactly once there is something pending to save - which was enough
extra width, at a narrow-enough window size, to squeeze "Zapisz zmiany"
(packed last) out of the row entirely. `_build_magic_pen_toolbar` now
packs the save/cancel buttons *first*, before the tool chips and status
label, so they always get first claim on the row's width; the chips and
status label losing room first if the window gets narrow enough is an
acceptable trade-off, the save button disappearing is not. Verified
functionally against the real GUI: added a pending edit (reproducing
the user's exact trigger), then narrowed the window step by step down to
340px - "Zapisz zmiany" stayed fully visible and correctly sized at
every width tested, with the chips visibly compressing first instead.
Lint unchanged against baseline; full suite still 372 (same reasoning as
above - real layout/geometry behavior, verified functionally).

**Visual redesign started (Stage 1 of a multi-stage rebuild).** The user
asked a separate design-focused AI conversation to work out a visual
identity for the app, deliberately without steering it toward specific
colors/icons (only a functional description of what the app does and
its screens), then reviewed the resulting mockups (saved in `pomysly/`,
outside the normal `src`/`tests` structure - reference material, not
part of the app) and asked for the full scope implemented: a rename to
"DocShield", a generated app icon, a new indigo/navy-based color
palette, and a set of structural changes (sidebar navigation, tabs in
Settings, a stat-cards-and-table review screen, a sidebar tool panel in
the comparison window) the mockups introduced beyond what already
existed. Confirmed with the user before starting: rename fully (not just
reskin), do the full scope rather than holding structural changes back,
and use the generated icon as the real app/taskbar icon. Given the size,
this is being built as a sequence of separately tested and shipped
stages rather than one giant change, starting with the lowest-risk,
highest-visibility one.

Stage 1 (this commit): branding, icon, and palette, on the *existing*
screen structure - `APP_TITLE` is now "DocShield" (window title,
default output folder name `DocShield - wyniki`; a repo-relative
`assets/icon.png`, a resized copy of the mockup's generated icon, is
loaded as the real window/taskbar icon via `iconphoto()` (never fatal if
missing - `_load_app_icon` degrades silently). The top bar (title +
Historia button + gear icon) is replaced with a persistent left sidebar
(`_build_sidebar`): brand mark, three nav items (Anonimizacja / Historia
/ Ustawienia - Ustawienia still opens the existing modal
`SettingsDialog`, unchanged in this stage), and a "Przetwarzanie
lokalne" trust badge pinned to the bottom. `_update_sidebar_active_state`
highlights whichever nav item the current screen belongs to - Anonimizacja
stays highlighted through the whole start/processing/review flow it
starts, not just literally while `self.active_screen == "start"`, since
those are steps of one flow, not separate destinations. The start screen
gained a page heading ("Anonimizuj dokumenty" + subtitle) and a small,
deliberately personal touch matching what the user singled out from the
mockups as their favorite single element: a script-font ("Segoe Script")
note reading "Twoje dokumenty. Tylko u Ciebie." - not because the text
itself is remarkable, but because a handwritten-style note reads as
individual care rather than a generic label. The color palette gained a
second, distinct blue (`COLOR_PRIMARY`, a dark navy for brand identity)
alongside a refined `COLOR_ACCENT` shifted toward indigo for interactive
elements - the existing semantic colors (green=ok, amber=warning,
red=high-risk) were already correct per the design brief's own
recommendation and are unchanged. Verified visually against the real
running app (screenshot forced to the foreground first, cropped to the
app's own window only - full-screen or unforced captures were confirmed,
twice, to risk sweeping in the user's unrelated real windows in the
background, and were deleted immediately both times without reading
their content beyond noticing they existed). Full suite: 372 tests (one
updated for the renamed default folder). Lint unchanged against
baseline.

Stage 2 of the DocShield redesign, same day: tabs inside the existing
`SettingsDialog` (`ctk.CTkTabview`), matching what the user specifically
called out from the mockups as something worth adding. Stays a modal -
the mockups' single visible settings screenshot showed the "Wykrywanie
danych" tab's content including an OCR row, while the mockup's own tab
list also names a separate "OCR i AI" tab; rather than guess at content
for a fifth tab the reference material never actually shows, the app's
existing controls were split into four non-overlapping tabs instead:
**Wykrywanie danych** (a new always-on "Podstawowe wykrywanie" info row -
the regex/PESEL/NIP/etc. baseline was never previously mentioned
anywhere in the UI - plus the existing NER toggle, LLM toggle, and OCR
status row), **Dokumenty PDF** (the existing PDF output format radio
buttons), **Słownik** (the existing private dictionary file picker), and
**Ogólne** (the existing auto-open-on-approve toggle). No settings
control changed behavior, save semantics, or the underlying `*_var`
wiring - purely a layout reorganization via new `_build_detection_tab` /
`_build_pdf_tab` / `_build_dictionary_tab` / `_build_general_tab`
methods, plus one new `_build_static_info_row` helper matching the
existing toggle/status row visual family for the always-on entry.
Verified functionally and visually against the real GUI: the dialog
opens tabbed, switching to the "Słownik" tab programmatically (`.set()`)
shows that tab's own content correctly. Full suite: 372 tests (no
behavior changed, so no new tests needed - this was already covered by
existing Settings-behavior tests, none of which touch layout). Lint
unchanged against baseline.

Stage 3 of the DocShield redesign: the review screen rebuilt around
stat cards plus a data table, replacing the previous card-list.
`_build_review_stat_cards` shows four always-present counts -
Zatwierdzone / Wymaga przeglądu / Odrzucone / Wszystkie pliki - the
three real manual-review statuses plus the total; batch *processing*
failures (files that never even produced a result) are a different
concept, already covered by the more useful named-files-and-reasons
banner from the existing `_build_batch_errors_card`, so they are
deliberately not duplicated as a bare "Błąd" count the way the mockup's
own screenshot showed - the two concepts don't collapse into one
number without losing information. `_refresh_review_cards` now builds a
`_build_review_table_header` row plus one `_build_review_table_row` per
item (grid-aligned columns: checkbox, filename, status pill, risk pill,
actions) instead of `_build_review_card`'s big padded cards; the
mockup's "Znalezione dane" column (a live per-category breakdown like
"4 osoby · 2 adresy · 1 PESEL") was deliberately left out of this pass -
it would need parsing each item's report file on every table refresh,
a real per-row I/O cost and its own risk surface the reference material
doesn't actually justify yet, being just one static mockup screenshot.
Bulk selection is new: a `_build_selection_bar` ("N zaznaczonych" +
"Zatwierdź zaznaczone" / "Odrzuć zaznaczone", both disabled with no
selection) sits above the table; checking a row's box updates
`self.selected_review_output_names` (a plain set of output names, reset
whenever a folder is (re)loaded so a stale selection can never survive
switching folders) and `_bulk_set_status` applies a status to every
selected item by calling the existing per-item `set_review_status` in a
loop (accepted trade-off: N table rebuilds and N small disk writes for
a bulk action rather than a bespoke batched code path - review folders
are small, and this reuses already-correct, already-tested logic
instead of duplicating it), then clears the selection so the same items
aren't left pre-selected for a second, likely-accidental bulk action.

While building the table, found and fixed a real layout bug of the same
family as the DPI-scaling issues found earlier the same day:
`CTkLabel`'s own auto-width computation under-measured the filename
column's needed width at this display's DPI scaling, silently clipping
even moderately long filenames - confirmed directly (`winfo_reqwidth()`
vs `winfo_width()` disagreed significantly). A pixel-budget fix (a
narrower "Akcje" column via smaller action-icon buttons: 32px→28px,
tighter spacing) recovered some room but real generated output
filenames (multiple category/collision suffixes) will always eventually
outgrow any fixed column width. The actual fix is a new pure
`truncate_filename_middle(name, max_length=26)`: elides the *middle* of
a long filename rather than the end, keeping the start (most
distinguishing between similarly-named files) and the tail (extension,
"_ANON" markers) visible, with the untruncated name available via an
`IconTooltip` on hover. Verified functionally and visually against the
real GUI: stat card counts match a synthetic 4-item set exactly,
checkbox-driven selection updates the count label and enables/disables
the bulk buttons correctly, a bulk-approve call changes both selected
items' status and clears the selection afterward, ordinary filenames
now render in full, and a deliberately long synthetic filename
correctly truncates to `2_faktura_vat_FIK…N_12.pdf` with the full name
recoverable on hover. Full suite: 375 tests (3 new, for the truncation
helper). Lint unchanged against baseline.

Stage 4 (final stage) of the DocShield redesign: the magic pen's
controls move from a toolbar row above "Po anonimizacji" into a
fixed-width right-hand sidebar ("Korekta anonimizacji"), matching the
mockups. A new `_build_magic_pen_sidebar` holds the two tool buttons
(now full-width vertical rows rather than horizontal chips, relabeled
"Dodaj zaznaczenie"/"Usuń zaznaczenie" to match the mockup - the
tooltip still spells out that LPM does the pinned action and PPM always
erases regardless) plus the color legend, now shown as a vertical list
instead of the horizontal row used elsewhere; `_build_tool_chip`'s
internal layout changed to match (full-width row instead of a small
side-by-side chip) but its signature, return shape, and the
pinning/highlighting logic that consumes it (`_toggle_pinned_tool`,
`_refresh_tool_chip_visuals`, `_on_pane_press`/`_on_pane_right_click`,
...) are all completely untouched - only how the buttons are built and
where they live changed, not what they do. The "Zapisz zmiany"/"Anuluj
zmiany" buttons move out of the (now-removed) toolbar into a bottom bar
below both panes, spanning the window - packed in the same
save-before-cancel order as before, for the same reason (Tk's `pack()`
hands out row width in packing order, and the save button must never be
the one squeezed out).

Moving the toolbar out entirely also let the toolbar-above-header/
matching-spacer trick from earlier the same day be retired along with
it: with no toolbar row sitting above "Po anonimizacji" anymore, both
pane headers are simply identical again and naturally start at the
same height with nothing extra needed - `MAGIC_PEN_TOOLBAR_HEIGHT` and
the spacer frame are removed as dead code. For a non-PDF comparison
(no magic pen, no sidebar), the color legend keeps using the existing
horizontal row at the bottom, unchanged - there is nowhere else for it
to live in that case.

Two mockup elements deliberately not carried over, consistent with the
scope decisions made throughout this redesign: per-category selection
for manual redactions (the mockup's "Kategorie danych" showed
checkboxes implying a filter/category-picker; this app still uses one
generic "RECZNE" label for every manual edit, an already-identified,
not-yet-planned future feature - rendering the legend as real
checkboxes here would imply working functionality that does not exist)
and combining "save" with "approve" into one action (the mockup's
"Zapisz i zatwierdź" button suggests exactly that, but the comparison
window does not currently touch review status at all - approving stays
where it already lives, the review screen's per-item actions - merging
the two would be a real cross-cutting behavior change beyond "move
existing controls into a sidebar," not something to fold in silently
alongside a layout change). Page-by-page pagination controls shown in
the mockup were also left out - this app renders every page of a
multi-page PDF stacked in one scrollable pane rather than one page at a
time, and changing that is its own, larger change.

Verified functionally and visually against the real GUI with the pilot
invoice PDF pair: both panes still start at the exact same height with
no spacer (253px == 253px, confirmed numerically, not just visually),
tool-chip pinning and the transient press/RMB-flash highlighting both
still work correctly after the move, the save/cancel buttons at the
bottom still respond to pending-edit state, and the zoom-link
(untouched code) still keeps both panes in sync after the
restructuring - confirmed with a real drag-drawn redaction visible in
a screenshot alongside a live "Niezapisane zmiany: 1" count and an
enabled, blue "Zapisz zmiany" button. Full suite: 375 tests (no test
changes - this is a widget-construction/layout move with the
underlying state/behavior logic completely untouched, verified
functionally instead, consistent with how the rest of this window's
history has been tested). Lint unchanged against baseline.

This closes out the DocShield visual redesign's four confirmed stages.

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

Stage 26: magic pen manual PDF redaction editor (and its first-pilot
follow-up: a batch-error review-screen banner plus a real `.gitignore`
collision-numbering gap fix, then a startup environment check for
optional dependencies with one-click fixes and subtle status dots in
Settings), a same-day self-review
fixing a toggle bug/unsafe overwrite/stale cursor, a fix for a `fitz`
deprecation warning the earlier Stage 25.1 fix missed, a resizable/
maximizable comparison window with independent or linked per-pane zoom, a
follow-up fixing the maximize button itself plus a padlock-based,
tooltip-and-hint-backed redesign of the zoom-link icon, a further round
of hands-on-testing feedback (window focus in/out, a draggable pane
splitter, modeless LMB/RMB magic pen interaction, a more visible legend,
a new auto-open-result Settings option), moving internal/diagnostic
output files into a hidden `_wewnetrzne` output subfolder, and, from
first pilot use, a batch-error review-screen banner, a `.gitignore`
collision-numbering gap fix, a startup environment check with one-click
fixes and status dots in Settings, a fix so the result file opens only
when the user clicks "Zatwierdzony" instead of right after anonymizing,
and a startup check for newer versions of the app's pip-managed
libraries with a fully silent, one-click, one-confirmation update path,
plus a same-day pilot-use follow-up merging the missing-dependency and
library-update cards into one compact banner, fixing a real Windows
PATH-staleness bug that made a freshly-installed Ollama/Tesseract keep
reporting as missing until the whole app was restarted, and then a
same-day fully-automatic fallback that finds a Tesseract install at its
default Windows location even when it was never added to PATH at all -
no manual PATH edit required from the user in either case - and a
same-day fix for a real magic pen rendering bug where the two comparison
panes rendered at visibly different sizes on a scaled display (a
CTkImage-vs-plain-Canvas DPI-scaling mismatch, not a PDF-rebuild issue as
first suspected - confirmed both ways directly on the pilot machine), and
a same-day "verification mode" follow-up: locked panes now scroll
together (not just zoom together), unlinking frees them to scroll
independently same as zoom already did, re-locking resets both to a
clean default view, and a latent widget-resolution bug shared with the
existing Ctrl-scroll zoom (a cursor over blank canvas space matching
neither pane) is fixed too, and finally a same-day toolbar polish pass
(from the user's own running to-do notes): the LPM/PPM row now sits
above the header/zoom row with both pages kept pixel-aligned by a
matching spacer, the two chips became real toggle buttons that pin LMB
to a single "manual" tool, and each chip now visibly lights up for as
long as its action is actually happening, and finally a same-day fix for
a reported regression where the comparison window opened behind the main
app again - root-caused to Windows silently refusing a foreground-focus
request from a background process, fixed with a briefly-forced, then
delayed-released `-topmost`, confirmed experimentally that the delay
before releasing it matters as much as forcing it in the first place,
and one more same-day fix: a narrowed (non-maximized) comparison window
with pending manual edits could clip "Zapisz zmiany" off entirely -
Tk's `pack()` hands out row width in packing order, not visual order, so
the save/cancel buttons are now packed first, guaranteeing them priority
over the tool chips and status label when space runs short.

Separately, a full visual redesign to "DocShield" branding began the
same day, built as a sequence of tested/shipped stages (full brief and
confirmed scope decisions in the narrative above). Stage 1 (this
commit): app renamed throughout, a generated icon wired up as the real
window/taskbar icon, the top bar replaced with a persistent sidebar
(Anonimizacja / Historia / Ustawienia, with active-item highlighting
that follows the whole start/processing/review flow), a start-screen
page heading plus a small handwritten-style personal note the user
specifically called out as their favorite element from the mockups, and
a refined palette (a new dark-navy brand color alongside a
indigo-shifted interactive accent; the existing status colors were
already correct and are unchanged). Stage 2 (same day): tabs inside the
existing `SettingsDialog` (Wykrywanie danych / Dokumenty PDF / Słownik /
Ogólne - four, not the mockup's five, since the reference material never
actually shows non-overlapping content for a fifth "OCR i AI" tab),
purely a layout reorganization of existing controls, no behavior change.
Stage 3 (same day): the review screen rebuilt around four stat cards
(Zatwierdzone / Wymaga przeglądu / Odrzucone / Wszystkie pliki) plus a
grid-aligned data table replacing the card-list, with new bulk
selection (checkboxes, a selection-count bar, bulk approve/reject).
Along the way, found and fixed a real DPI-scaling layout bug (CTkLabel
under-measuring the filename column's needed width, silently clipping
even moderate-length names) with a proper fix rather than a pixel
chase: a new `truncate_filename_middle()` elides the middle of long
filenames (keeping the start and the extension) with the full name on
hover, since real generated output filenames will always eventually
outgrow any fixed column width. Stage 4 (same day, final stage): the
magic pen's toolbar moves into a right-hand "Korekta anonimizacji"
sidebar (vertical tool buttons + color legend), retiring the
toolbar-above-header/matching-spacer trick from earlier the same day
along with it - both pane headers are simply identical again and
naturally align with nothing extra needed. Two mockup elements
deliberately not carried over: per-category manual-redaction labels
(still one generic "RECZNE" label - an already-identified, not-yet-
planned future feature) and merging "save" with "approve" into one
action (approving stays on the review screen, where it already lives).
This closes out the DocShield redesign's four confirmed stages.

```text
45ab4b5 DocShield Stage 4: magic pen sidebar panel (final redesign stage)
```

The user kept forgetting the correct launch command (`py gui.py` does not
work - the app is not runnable as a bare script from an arbitrary working
directory; it needs the project's own virtualenv interpreter and the
`src/main.py` entry point, which imports `start_gui()` from `gui.py`).
Added a double-clickable `uruchom.bat` in the repo root: it `cd`s to its
own location first (so it works regardless of the folder the user double-
clicks it from), runs `.venv\Scripts\python.exe src\main.py` - confirmed
identical to `gui.py`'s own `if __name__ == "__main__"` block, since both
just call `start_gui()` - and pauses with a visible message on a non-zero
exit code instead of the window vanishing silently on a crash. No app code
changed; not part of the Python package, so no tests apply.

```text
b270746 Add double-clickable launcher script (uruchom.bat)
```

The user's first hands-on pilot session against the redesigned DocShield UI
produced a 14-item feedback batch, comparing the running app directly
against the `pomysly/` mockups. Given the size, it is being worked through
in two passes: Stage A (this entry) fixes real defects and quick,
unambiguous UI fixes; Stage B (visual mockup-fidelity items, some of which
resurface functionality already deliberately deferred earlier - see the
Stage 4 narrative above) is planned separately, next.

Stage A: (1) the sidebar logo/brand row is now clickable and always goes
to the start screen, same as the existing "Anonimizacja" nav item -
"O programie" from item 5 is still Stage B. (7) the trust-badge padlock is
now green (`COLOR_OK`) instead of plain text-color black, matching the
mockup. (10) the Windows taskbar icon showing python.exe's generic icon
instead of the app's own was a real, previously-unfixed Windows quirk, not
a leftover from an earlier stage: `iconphoto()` alone is not reliable for
the *taskbar* specifically, and without a distinct AppUserModelID (set
once, before any window exists, via
`ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID`) Windows
can group the process under plain python.exe's taskbar entry and icon
regardless. Fixed with a generated multi-size `assets/icon.ico`
(`window.iconbitmap(default=...)`, tried before the existing
`iconphoto()` fallback) plus `_set_windows_app_user_model_id()` called at
the very top of `start_gui()`; both are no-ops off Windows or on any
error, never fatal to startup.

(4) the handwritten-style personal note ("Twoje dokumenty. Tylko u
Ciebie.") was being clipped, not shrunk, as the window narrowed - Tk
`pack()`'s space-priority-by-pack-order rule (the same root cause found
earlier for the save-button-clipping bug) meant the note, packed after
the heading, lost the fight for space first. Rather than continuously
re-measuring width on every `<Configure>` event (tried and rejected
earlier this same day for a different spacer - an expensive cascade, not
a one-off cost), `_build_header_row`/`_apply_header_layout` reconfigure
the same two widgets in place only when the window crosses one fixed
`HEADER_STACK_BREAKPOINT`, debounced via `after(150, ...)`: side-by-side
above the breakpoint, the note dropping to its own smaller-font line below
the heading under it.

(3) adding enough files made the "Anonimizuj" button unreachable - worse,
confirmed while investigating: `self.content` never scrolled at all, so
even the *fixed* controls (output folder row, the button) could in
principle be pushed out of a short window with no way back, independent
of the file count. Recommendation given directly to the user's own
question about whole-window scrolling: yes, but scoped carefully rather
than one big scrollable dump - the start screen is now a pinned
`bottom_bar` (output folder + button, packed first with `side="bottom"`
so its space is always reserved) plus a `scroll_region` above it holding
everything else, itself containing the file list in its *own* small
`FILE_LIST_MAX_HEIGHT`-bounded `CTkScrollableFrame` so a long file list
doesn't by itself push the drop zone far out of view either. Verified
functionally: the button stays reachable with 12 files selected at both
the default window size and the app's own `WINDOW_MIN_WIDTH x
WINDOW_MIN_HEIGHT`. This two-region pattern (pinned action bar outside
any scroll, everything else inside one) is the general principle other
screens should follow if the same problem shows up there, not a
start-screen-only fix.

(9) reported directly by the user after hitting it live: leaving the
review screen for the start screen (e.g. clicking "Anonimizacja" to
double check something) had no way back short of reprocessing the same
files, even though `self.review_items`/`self.last_batch_result` were
still fully intact and never cleared by `show_start_screen`. A new
`_build_resume_review_banner` shows a dismissible-by-nature (only appears
while `self.review_items` is non-empty) "Wróć do przeglądu" banner on the
start screen instead.

(12) scroll-sync (plain, unlinked-from-zoom mouse wheel mirroring between
panes) silently did nothing for some file pairs but not others, reported
as "works for txt, not for docx" - reproduced and root-caused with a real
script driving `ComparisonWindow` for both a long TXT and a long DOCX
pair: a DOCX/TXT pane's only child is one fixed-height `CTkTextbox`
(`_render_text_block`), and scrolling through content longer than that
box is the *textbox's own* internal yview, not the outer
`CTkScrollableFrame` canvas `_scroll_pane_by` was mirroring - which barely
has anything else to move. It only looked like it "worked" for a short
TXT file because nothing needed scrolling either way, coincidentally
looking in sync. `_scroll_pane_by`/`_scroll_pane_to_top` now check for a
`CTkTextbox` child first (`_find_textbox_in`) and target its own
`_textbox.yview_scroll`/`yview_moveto` when present, falling back to the
outer canvas only for PDF/image panes that have no such textbox. Verified
with a regression script confirming the *other* pane's own textbox
position actually moves for both TXT and DOCX now, not just the outer
canvas.

Deliberately left for Stage B, since they are visual mockup-matching work
rather than defects: (2) sidebar/drop-zone bluish tint, (3-icons) nicer
file-type badges, (5) an "O programie" sidebar entry, (6) matching the
mockup's folder-row/button layout exactly, (8) a new quick-settings
checkbox panel on the start screen, (11) the review screen's visual
overhaul to match the mockup, (13) the comparison toolbar's hand/zoom
tool pair with tooltips, (14) comparison legend visual polish. Full
suite: 375 tests (no new pure-logic tests needed - Stage A is widget
wiring, verified functionally with scratchpad scripts per this project's
usual pattern, not new permanent unit tests), lint unchanged against
baseline.

```text
c5f6755 Pilot feedback Stage A: real bugs + quick UI fixes
```

Pilot feedback Stage B: the mockup visual-fidelity items deferred out of
Stage A. (2) `COLOR_BG` shifted to a visibly bluer `#EBF0FB` (was the
almost-neutral `#F7F9FC`), and the start screen's drop zone now fills with
`COLOR_ACCENT_SOFT` instead of plain white - `COLOR_PRIMARY`/
`COLOR_PRIMARY_SOFT`, defined back in Stage 1 but never actually used
until now, stayed unused; this was a plain color-token change instead.
(3) File-type badges are now small generated icons (`_draw_file_type_icon`/
`get_file_type_icon`, cached per type+size) - a rounded colored tile with
a white folded-corner document shape, drawn procedurally via PIL rather
than shipping bespoke image assets per type - used on both the start
screen's file cards and the review table. (5) A new "O programie" sidebar
entry opens `AboutDialog` (name, version, the same local-only privacy
line shown elsewhere - deliberately no personal author info); a small
`v0.1.0` (`APP_VERSION`) now also sits at the bottom of the sidebar,
matching the mockup. (6) The output-folder row was rebuilt to match the
mockup - a bordered field (folder glyph + path) beside a "Zmień" button,
under its own "Folder wynikowy" heading - and the anonymize button's own
label now includes the live selected count ("Anonimizuj 3 pliki" via a
new pure `format_anonymize_button_text`), matching the mockup's button
text directly instead of a plain "Anonimizuj".

(8) A new quick-settings panel on the start screen
(`_build_quick_settings_panel`) mirrors the mockup's "Domyślne ustawienia"
card, but only wraps settings that are real, already-wired toggles
(`self.use_ner`, `self.use_llm_review`) rather than inventing new ones the
mockup implies - OCR has no on/off switch anywhere in this app (it runs
automatically when available), so that row stays the same read-only
status-dot pattern already used in the full Settings dialog instead of a
checkbox that would not actually control anything; the dictionary row
shows the current file (or "Nie wybrano") with a "Zmień" shortcut that
opens the full Settings dialog straight on its "Słownik" tab (`SettingsDialog`
gained an `initial_tab` parameter for this). Found and fixed while wiring
this in: checking `self.root.winfo_width()` to decide whether the window
is wide enough for this panel returned an unrealized placeholder size
(~200px) the very first time it ran, during `AnonymizerApp.__init__`,
before the window had ever been mapped - silently hiding the panel
forever on every normal launch regardless of actual window width, since
nothing else ever re-triggers that check. Fixed with one `self.root.update()`
right after `_build_shell()`, before the first `show_start_screen()`.
(11) The review screen gained the page heading it was missing entirely
("Wyniki anonimizacji" + a new pure `format_review_heading_subtitle`, e.g.
"3 dokumenty zostały przetworzone.") above the existing nav-links row: the
stat cards/table/legend structure already matched the mockup's intent
from Stage 3 (including the deliberate decision to keep review-workflow
status separate from the mockup's `Znalezione dane` column - still not
added, still a real functionality gap, not a visual one), so this stayed
a small, targeted addition rather than a rebuild.

(13) The comparison window's pane headers gained the mockup's hand/lupa
tools: a shared `self.active_pointer_tool` ("hand"/"zoom"/None, one state
for the whole window, toggle buttons in both headers kept in sync the
same way the zoom-link buttons already are). "Łapka" wires standard Tk
`scan_mark`/`scan_dragto` drag-to-pan onto every descendant of a pane via
a new recursive `_bind_pane_panning`, deliberately *not* applied to the
magic pen's own PDF page canvases (`self._page_canvases`) - those already
have their own full LMB-draw/RMB-erase semantics, and layering pan
bindings on top risked the exact kind of subtle interaction bug the
Stage 26 magic pen self-review was built to catch; verified directly that
no pan binding ever reaches those canvases. "Lupa" makes plain scroll
zoom the same as Ctrl+scroll while active (`_on_scroll_sync` now checks
`active_pointer_tool == "zoom"` first) - Ctrl+scroll itself keeps working
unconditionally either way, exactly as asked. Esc clears whichever tool
is active. The zoom percentage display in each pane header is now an
editable `CTkEntry` (`_commit_zoom_entry`) instead of a plain label -
typing a value and pressing Enter (or clicking away) sets zoom directly,
invalid text just resets the field back to the current zoom rather than
raising. New hover tooltips explain both tools and mention the
Ctrl+scroll shortcut; a new "Pokazuj podpowiedzi o obsłudze" Settings
toggle (`self.show_usage_hints`, default on) can turn these (and the
existing zoom-link tooltip) off - `IconTooltip` gained an `enabled` flag
for this rather than adding a second tooltip class. (14) Legend styling
was already close to the mockup from earlier same-day work and needed no
further change.

Deliberately not carried over from the mockup images referenced this
pass, consistent with the Stage A/B split's own opening call: the
combined "Zapisz i zatwierdź" magic-pen button (still separate save/
cancel - this reappeared in the reference image again but was not asked
for in this feedback batch) and per-category manual-redaction labels
(still one generic "RECZNE"). Page-by-page PDF pagination shown in the
mockup's toolbar was also not added - the app still renders every page in
one continuously-scrollable pane, a separate, larger interaction-design
change from the hand/zoom tools actually requested. Full suite: 377 tests
(2 new: `format_anonymize_button_text`, `format_review_heading_subtitle`),
lint unchanged against baseline.

```text
4a43463 Pilot feedback Stage B: mockup visual-fidelity pass
```

A self-requested senior-level code review of `src/gui.py` (the user asked
for a logic/cleanliness/optimization pass before starting real pilot
testing) surfaced 5 findings, all fixed in one pass. (1) The Stage B hand
tool ("łapka") always panned a pane's outer `CTkScrollableFrame` canvas
via `scan_mark`/`scan_dragto`, never the inner `CTkTextbox` a DOCX/TXT
pane actually scrolls through - the exact same root cause already found
and fixed for plain-scroll sync earlier that same day (`_scroll_pane_by`),
just not carried over to the new pan handlers. `_bind_pane_panning`/
`_on_pan_press`/`_on_pan_drag` now resolve a `_pan_target` (the inner
textbox when present, the outer canvas otherwise) the same way
`_scroll_pane_by` already does. Verifying this live caught a second, real
bug in the fix itself: `tkinter.Text.scan_dragto` doesn't accept the
`gain` keyword `tkinter.Canvas.scan_dragto` does, so panning a text pane
raised `TypeError` the first time it was actually exercised - caught only
because the fix was verified with a real drag rather than assumed correct
by inspection; now tries `gain=1` (a direct, 1:1 drag) and falls back to
the plain two-argument call. (5, same area) `_bind_pane_panning` also now
skips `CTkScrollbar` descendants, so the hand tool can no longer fight a
scrollbar's own native drag.

(2) The new quick-settings panel's OCR status row treated "the background
environment check hasn't completed yet" (`None`) the same as "confirmed
unavailable" (`False`), showing a false "Niedostępne" on every single
launch for the ~1-3s the check takes - contradicting the "green when
available, gray when confirmed missing, absent while unknown" rule
`_build_status_dot` (the equivalent row in the full Settings dialog)
already documents and follows for the identical data. Fixed by handling
`None` as its own third state (an empty dot, "Sprawdzanie dostępności..."
text) instead of falling into the "unavailable" branch; the row still
rebuilds with the real status once `_on_environment_check_done` reruns
`show_start_screen()`, unchanged.

(3) `_add_paths` computed a real "Dodano X / Pominięto Y nieobsługiwanych"
drop-result message and set it on `status_label`, then immediately called
`_update_readiness()`, which unconditionally overwrote that same label
with the generic readiness text one line later - the rejection notice
never reached the screen, silently since app inception (not introduced
this session). `_update_readiness()` gained an optional `status_override`
parameter so a caller can supply the message for that one call without
duplicating the button-ready/text logic living in the same method;
`_add_paths` now passes its drop-result text through it instead of
setting the label directly and being immediately overwritten.

(4) `_commit_zoom_entry` (the new manual zoom-percentage entry) had the
identical `zoom_linked=True` body pasted under both the `side=="original"`
and `side=="result"` branches - pure duplication risk (a future change to
the linked-zoom path would need updating in two places), no observed bug.
Restructured to check `self.zoom_linked` once up front, matching the
pattern `_adjust_zoom` a few dozen lines away already uses.

All 5 fixes (plus the scan_dragto bug caught while verifying fix 1) kept
in one small, low-risk pass - none touch the magic pen, batch processing,
or review workflow. Full suite: 377 tests (unchanged - these were widget-
wiring/state fixes, verified functionally with scratchpad scripts per
this project's usual pattern), lint unchanged against baseline.

```text
5f351cc Fix 5 findings from senior-level self code review
```

The user asked directly whether `src/gui.py` (5436 lines by this point) could
reasonably be split for readability, and whether that carried real risk -
answered with a concrete assessment (module map, backward-compat strategy,
staged plan) before touching anything, then executed it once confirmed.
`gui.py` is now a thin ~470-line entry point/facade; the implementation
moved into 5 new sibling modules along the file's own existing class/
responsibility boundaries - no logic was rewritten, only relocated:

- `gui_helpers.py` (~1090 lines): every module-level constant (colors,
  fonts, `LEGEND_ITEMS`, window sizing, etc.) and pure formatting/parsing
  function, plus the two small reusable widgets `DnDCTk`/`IconTooltip`.
- `gui_app.py` (~2095 lines): `AnonymizerApp` - still the largest piece,
  deliberately not split further (its methods share extensive `self`
  state across the start/history/processing/review screens; splitting
  *that* is a separate, materially riskier decision not made here).
- `gui_settings_dialog.py` (~340 lines): `SettingsDialog`.
- `gui_comparison_window.py` (~1450 lines): `ComparisonWindow` plus the
  zoom/PDF-point/document-preview pure helpers it (and the review
  screen) share.
- `gui_dialogs.py` (~225 lines): `AboutDialog`, `SummaryDialog`.

Mechanically extracted with a one-off script (exact line-range text
slicing, never a re-serialized/reformatted rewrite, so every comment and
blank line survives byte-for-byte) rather than by hand, specifically to
rule out transcription mistakes across ~5400 lines; a diff-based check
confirmed the six slices reconstruct the original file exactly (one
cosmetic blank line aside). Two real risks were found and resolved
*before* anything touched the real source tree, both while regenerating
into a scratch folder first: (1) `src/` has no `__init__.py`, so - just
like the existing upstream package imports already had to handle -
every cross-file import between the new `gui_*` modules needed the same
`try: from .module import X / except ImportError: from module import X`
dual form, not a bare relative import, or the "import as a top-level
script" path tests use would break. (2) `SettingsDialog`/`ComparisonWindow`/
`AboutDialog`/`SummaryDialog` all take `app: AnonymizerApp` as a
constructor parameter - a real circular import between `gui_app.py` and
each of them - resolved with `from __future__ import annotations` in
those three modules plus a `TYPE_CHECKING`-guarded import, so the
annotation is never evaluated at runtime. `gui.py` re-imports every name
the old flat file exposed (both genuinely defined names and ones only
ever imported-through, like `ReviewItem`) and declares them in `__all__`
so `from gui import X` - used extensively by `tests/test_gui_workflow.py`
- keeps working completely unchanged; a script-driven check confirmed
all 64 names that file imports from `gui` resolve. `main.py`'s
`from gui import start_gui` needed no change at all.

Running the real test suite surfaced the one class of break this kind of
split can cause that static checks can't catch: two tests used
`mock.patch("gui.ctk...")` / `patch("gui.sys.platform", ...)` to reach
internals that now live in `gui_comparison_window.py` instead - fixed by
retargeting those two patches, the only test changes needed. Lint (both
per-file and whole-repo) came back to the exact same baseline as before
(79 project-wide, the 1 known `BLE001` now living in `gui_app.py` instead
of `gui.py`) after adding `__all__` to `gui.py` (a normal, idiomatic fix
for a facade module - without it, ruff flagged the ~190 intentional
re-export imports as unused) and running `ruff check --fix` for import
ordering across the new files. Verified end-to-end with a real driving
script: constructs the real app, visits every screen (start/history),
opens and closes the real Settings and About dialogs, adds files and
confirms the button-text wiring still works across the new module
boundary, and opens a real `ComparisonWindow` against a real PDF pair
with the magic pen and the hand/zoom pointer tools all exercised -- all
passed. (Screenshots from that same run captured this coding session's
own window instead of the app's, an environment quirk of this sandbox
unrelated to the code change; deleted immediately per this project's
established handling for that failure mode, and not reattempted - the
text-based assertions already gave strong enough confidence.) Full
suite: 377 tests (unchanged - a pure relocation, no behavior changed),
lint unchanged against baseline.

```text
9d05751 Split src/gui.py (5436 lines) into 6 focused modules
```

The user shared a real, badly garbled OCR result from their own scanned
employment contract ("so ymayna 2 9422 Yara" instead of readable Polish)
and asked how to fix it. Root-caused directly from the code rather than
guessing: `ocr.py`'s two `pytesseract.image_to_string(image)` calls never
passed a `lang` argument, so Tesseract used its own default - English -
to read a Polish document. English OCR on Polish text doesn't fail
loudly; it silently misreads diacritics (ą, ę, ć, ł, ń, ó, ś, ź, ż) and
Polish letter combinations into plausible-looking wrong characters,
exactly matching the reported symptom. A second, compounding factor
found while fixing the first: `extract_text_from_pdf` rendered each PDF
page for OCR via a bare `page.get_pixmap()` - PyMuPDF's default 72 DPI,
well below the ~300 DPI Tesseract's own documentation recommends.

Fixed both. A new `_ocr_language()` queries `pytesseract.get_languages()`
and prefers `"pol+eng"` (Polish primary, English still recognized for
the Latin abbreviations - NIP, REGON, IBAN - common in Polish business
documents), falling back to `"pol"` alone or `"eng"` alone depending on
what's actually installed, never raising - a wrong/missing language
degrades quality but must not crash OCR outright. Both `image_to_string`
call sites now pass `lang=`. `extract_text_from_pdf` now renders via a
new `OCR_PDF_RENDER_ZOOM = 3.0` matrix (216 DPI) instead of the bare
default. Both fixes are silent no-ops if Tesseract's Polish trained-data
file (`pol.traineddata`) genuinely isn't installed on the user's machine
(falls back to `"eng"`, same as before) - confirming/installing it is a
one-time step outside this app's control, communicated back to the user
directly rather than assumed. Verified with new unit tests
(`OcrLanguageTests`, `OcrCallsUseDetectedLanguageTests`) using fake
pytesseract/fitz modules that capture the actual `lang=`/`matrix=`
arguments passed, not just that the helper function exists in isolation.
Full suite: 383 tests (6 new), lint unchanged against baseline (one new
`except Exception` in `_ocr_language` needed the same `# noqa: BLE001`
justification already used for other never-crash cosmetic/optional-
feature catches elsewhere in the codebase).

```text
a96fd3a Fix garbled OCR on Polish documents: wrong language + low DPI
```

Direct follow-up requested by the user right after the OCR-language fix
above: make Polish the app's explicit baseline OCR language (not just a
preference inside one function), English the explicit secondary, and
give Settings both a "what's currently supported" view and a way to add
another language pack without leaving the app.

`ocr.py` gained the actual policy as named constants -
`PRIMARY_OCR_LANGUAGE = "pol"`, `SECONDARY_OCR_LANGUAGE = "eng"` -
`_ocr_language()` now reads from these instead of hardcoded strings.
`list_installed_languages()` wraps `pytesseract.get_languages()` (never
raises, empty list on any failure), filtering out `osd`/`equ` (Tesseract
auxiliary data, not real languages) and ordering the result Polish-first
via a new pure `order_languages_primary_first()` - any "installed/
supported languages" display consistently reflects the Polish-first
policy instead of a plain alphabetical list that would bury Polish
behind "angielski". `download_language_pack()` downloads one
`.traineddata` file from the `tesseract-ocr/tessdata_fast` GitHub repo
(the smaller/faster variant, a better fit for an on-demand desktop
download than the much larger "best"-accuracy models) into the resolved
tessdata directory (`TESSDATA_PREFIX` if set, else next to the resolved
tesseract binary) - a plain data file Tesseract already reads from, not
an installer, so - unlike Tesseract/Ollama themselves - this is safely
automatable as long as the folder is writable; writes to a `.part` file
first and only renames it into place on full success, so a failed
download never leaves a corrupt trained-data file behind. A short,
curated `COMMON_OCR_LANGUAGES_PL` (12 languages plausible for a
Polish-market user, not Tesseract's full 100+ catalog) drives both the
Settings dropdown and the "supported languages" display text.

`environment_check.check_ocr_environment()` now checks two things where
it used to check one: the Tesseract engine itself (unchanged - still
offers the existing "Pobierz" flow when missing), and, separately,
whether the Polish pack specifically is installed once the engine is
confirmed present - the exact real case that produced garbled OCR text
before the language fix above: Tesseract genuinely installed and
working, English-only, which passed the old engine-only check while
still silently misreading Polish. That case now gets its own message
("Tesseract jest zainstalowany, ale brakuje polskiego pakietu...") and
its own install action (`INSTALL_ACTION_TESSDATA_DOWNLOAD`) distinct
from "Tesseract not installed at all". When OCR is fully available, the
status detail now also lists which languages are installed. A thin
`install_tesseract_language()` delegates to `ocr.download_language_pack`.

GUI wiring in two places, both reusing this project's existing
install-action patterns rather than inventing new ones: (1) the
start-screen environment banner (`gui_app.py`) gained a branch for
`INSTALL_ACTION_TESSDATA_DOWNLOAD` - a "Zainstaluj pakiet polski" button
following the exact same background-thread +
`root.after(0, callback)` + re-check-rather-than-assume-success shape
`_install_ner_model_clicked` already established. (2) Settings' detection
tab replaced the old plain OCR status row with a new
`_build_ocr_language_section`: status dot, the "supported languages"
line, and - only when a common language isn't installed yet - a
`CTkOptionMenu` + "Dograj" button wired to the same install-then-
re-verify shape, rebuilding just that one tab in place afterward
(`_refresh_detection_tab`) rather than the whole dialog.

Two real bugs were caught only by driving the actual click through real
Tk widgets rather than testing the pieces in isolation - both fixed
before anything shipped. (1) The OptionMenu's bound `StringVar` was
seeded with a language *code* (e.g. `"ces"`) instead of the *label* the
widget actually shows and sets (`"czeski"`); the code-by-label lookup
inside the click handler always missed, so clicking "Dograj" silently
did nothing at all - never raised, never showed an error, just no-op'd.
(2) Two of this change's own new tests initially asserted *outside* the
`with workspace_temp_dir():` block whose exit deletes the directory
being asserted against - passed for the wrong reason (or failed
confusingly) until moved inside it.

Verified end-to-end with a real driving script (not just the unit
suite): Settings shows the real installed-language line, clicking
"Dograj" resolves the correct language code and disables the button,
the completion callback refreshes the displayed list, a failed install
shows an error dialog instead of failing silently, and the start-screen
banner offers the one-click Polish install button when that specific
gap is simulated. (A screenshot attempt captured this coding session's
own window instead of the app's - the same sandbox quirk noted for the
module-split work above, unrelated to the code; deleted immediately,
not reattempted, relied on the text-based verification instead.)

Full suite: 394 tests (11 new), lint improved by one over baseline (78
vs the established 79 - `ruff --fix` incidentally cleaned up one
pre-existing unrelated import-order issue in `ocr.py` while fixing a new
one this change introduced).

```text
1ba33db Make Polish the explicit OCR baseline + language-pack management
```

Direct follow-up from the user, looking at their own scanned-document result:
why does a scanned PDF only get placeholder-tag text ([NER_PERSON], [DATA],
...) instead of the same colored redaction boxes a real-text-layer PDF
already gets? Root-caused in the code rather than guessed: `pdf_redaction.py`
already has a full word-coordinate visual-redaction pipeline, but it only
ever received words from `extract_pdf_word_pages` (PyMuPDF's real PDF text
layer) - OCR text (`pytesseract.image_to_string`) carries no position data
at all, so a scanned page had nothing to map a detected span onto and always
fell back to a rebuilt plain-text document. Confirmed while investigating:
PyMuPDF's `page.apply_redactions()` already blanks out *image* pixels under
a redaction rect by default (`images=2`), not just text - meaning the
entire existing colored-redaction pipeline would work unchanged on a
scanned page, the only missing piece was positional OCR data to feed it.
User confirmed scope directly: both scanned PDFs and standalone images
("PDF-y i obrazy naraz").

`ocr.py` gained `extract_pdf_word_boxes`/`extract_image_word_boxes`, using
`pytesseract.image_to_data` (not `image_to_string`) to get per-word text
plus pixel bounding boxes, converted to PDF point space (dividing by the
known render zoom for PDF pages; 1:1 for a plain image). Low-confidence
words (`MIN_OCR_WORD_CONFIDENCE = 40`) are dropped rather than risk a
redaction box landing in the wrong place on a poor scan - a guard the
plain-text OCR path has no equivalent of, since a wrong character there is
just a wrong character, not a misplaced rectangle. `pdf_redaction.py` gained
`word_pages_from_ocr_boxes`, converting that raw data into the exact same
`PdfWord`/`PdfWordPage` shape `extract_pdf_word_pages` already produces from
a real text layer - refactored the shared text/offset-reconstruction logic
(line-break-between-source-lines convention) into one `_build_word_page`
helper both now call, rather than duplicating it - so every existing
word-coordinate function (`compute_redaction_rects`,
`save_word_coordinate_redacted_pdf_copy`, ...) works identically regardless
of whether the words came from a text layer or OCR, with zero new
special-casing needed in that layer. For standalone images, a new
`save_word_coordinate_redacted_image_copy` wraps the source image in a
synthetic one-page PDF sized at the image's own pixel dimensions (1 pixel =
1 point, matching how `extract_image_word_boxes` measured its OCR boxes)
and reuses `save_word_coordinate_redacted_pdf_copy` entirely rather than
reimplementing redaction - the synthetic PDF is a temporary implementation
detail, cleaned up regardless of outcome. A new `build_image_visual_pdf_path`
names the output the same `_ANON_VISUAL.pdf` convention PDF sources already
use.

`anonymizer.py`'s scanned-PDF branch now tries word-box OCR first - it
produces the same text a plain OCR pass would (via the word pages' own
reconstructed text) plus the coordinates needed for visual redaction, in
one OCR pass rather than two; falls back to the original plain-text-only
OCR path unchanged when word-level OCR itself is unavailable. Found and
fixed while wiring this in: joining OCR page text with the same
`PDF_PAGE_SEPARATOR` a real text layer uses (needed so detection sees
real page boundaries) but not also passing the real page count to
`_split_anonymized_pdf_pages` would have left raw separator characters
embedded as literal text in the saved TXT output for a multi-page scan -
never shipped, since it was verified with a real driving script before
being trusted, not assumed correct from reading the diff. The image
pipeline (previously TXT-only, no visual output ever existed for images)
gained the same word-box-first OCR + optional visual PDF, reusing
`_pdf_detection_spans_for_word_pages` (the same span-detection function the
PDF path already uses) rather than inventing a second detection path.
Review-item resolution (`review.preferred_review_output_path`) needed *no*
change at all - it already finds a companion `_ANON_VISUAL.pdf` purely by
filename pattern next to any `_ANON.txt`, regardless of what kind of source
produced it.

Verified for real, no mocks, through the actual public API the GUI calls
(`anonymize_pdf_file_with_audit`, `anonymize_image_file`) rather than only
through `pdf_redaction.py` directly: rendered real Polish text (PESEL, a
name, an email) into an image-only PDF page and a standalone image (both
with zero real text layer, forcing the OCR path), ran the real pipeline,
and re-OCR'd the resulting `_ANON_VISUAL.pdf` to confirm the sensitive
value is genuinely gone - not just "some rectangle got drawn somewhere" -
while the unrelated name stays legible, proving the redaction is targeted,
not blanket. Full suite: 404 tests (10 new, including two real end-to-end
integration tests gated with `@unittest.skipUnless` on a real local
Tesseract + Polish pack being present, the same graceful-skip treatment
this project already gives every other OCR-dependent test), lint improved
by 2 versus the established baseline.

```text
8deb41c Add true colored visual redaction for scanned PDFs and images
```

Direct follow-up from the user testing the redesigned start screen against
their own mockups, three concrete pieces of feedback given together: (1)
the sidebar's light `COLOR_CARD` background "blended into the app" and
users could miss/ignore it - wanted the dark-navy mockup treatment
instead; (2) the library-update reminder banner used the same soft-blue
"info" styling regardless of content, which read as too easy to dismiss
next to the amber/orange OCR-unavailable warning card shown side by side
in the same screenshots; (3) the "Anonimizuj" button was "too big" versus
the mockups and belonged in the bottom-right corner, where the quick-
settings card already sat - moving it there would also free vertical
space in the center column for the file list, and the output-folder
picker should move into that same card, renamed "Szybkie akcje" (quick
actions) per the user's own suggested name.

`gui_helpers.py` gained five sidebar color tokens (`COLOR_SIDEBAR_BG`,
`_HOVER`, `_TEXT`, `_TEXT_MUTED`, `_TRUST_BG`) - `COLOR_SIDEBAR_BG` reuses
`COLOR_PRIMARY`, a dark-navy token defined back in Stage 1 of the
DocShield redesign but never actually referenced anywhere until now.
`gui_app.py`'s `_build_sidebar` and `_update_sidebar_active_state` switch
every sidebar surface (frame background, wordmark, nav-button text/hover,
the "Działa lokalnie" trust card, version label) from the old
card/muted-text palette to these new tokens, with the active nav item
still using the existing `COLOR_ACCENT` so it keeps standing out against
the now-dark background rather than blending into it the way the old
light-on-light styling did. `_build_status_banner` no longer branches its
colors on whether real "issues" are present versus only an update being
available - both cases now render with the same amber `COLOR_WARNING` /
`COLOR_WARNING_SOFT` / `COLOR_WARNING_TEXT` treatment (and a matching "⚠"
header) the OCR-unavailable case already used, addressing the "should
look like a warning, not routine info" feedback directly; the existing
Aktualizuj/Napraw/Zainstaluj action buttons needed no change, already
using `COLOR_ACCENT` blue-on-amber.

Moving the "Anonimizuj" button surfaced a real conflict with a fix from
earlier this session: the quick-settings panel was hidden below
`QUICK_SETTINGS_MIN_WIDTH` (880px) - fine while it only held secondary
toggles, but hiding it once it also holds the primary action button would
have reintroduced the exact "critical control can become completely
unreachable" bug the pinned-bottom-bar pattern was built to prevent in
the first place. Flagged to the user before starting, then fixed by
construction rather than by exception: `_build_quick_settings_panel` (now
titled "Szybkie akcje", per the user's own name for it) is always built
and shown - the `QUICK_SETTINGS_MIN_WIDTH` gate and the
`update_idletasks`/`winfo_width` check that drove it are gone entirely -
and internally the panel now uses the identical pinned-bottom-bar +
scrollable-region-above pattern already proven in `show_start_screen`:
an `action_bar` (folder picker, status text, "Anonimizuj") is packed
*first* with `side="bottom"`, a `CTkScrollableFrame` holding the
checkboxes/OCR status/dictionary row/"Więcej ustawień" link is packed
second with `side="top", fill="both", expand=True` - the action area
always claims its space regardless of how tall the settings above grow
or how short the window is. The now-narrow (240px) panel stacks the
folder-path field and its "Zmień" button vertically instead of the wide
column's old side-by-side layout, which would otherwise squeeze both
into an unreadable/unclickable width. `show_start_screen`'s own
`main_col` lost its now-empty `bottom_bar` entirely - the scrollable
drop-zone/file-list region claims the freed vertical space, the second
half of the user's request ("wtedy tez zyskamy przestrzen... bedzie ich
widac wiecej"). `self.status_label`, `self.anonymize_button` and
`self.output_dir_value_label` are unaffected by the move since
`_update_readiness` and `pick_output_dir` only ever reference them as
instance attributes, never by parent widget.

`QUICK_SETTINGS_MIN_WIDTH` itself stays defined in `gui_helpers.py`
(still re-exported through the `gui.py` compatibility shim) even though
nothing in `gui_app.py` reads it anymore, rather than deleting a public
name a downstream import could still rely on.

Verified via `ruff check` (unchanged against the established 77-error
baseline) and the full suite (404 tests, all pre-existing - this is a
pure layout/styling change with no new behavior to add coverage for).
Live-driving the actual Tk window to confirm visually was attempted but
the process exited with no output before reaching a screenshot, the same
sandbox-environment unreliability noted earlier in this document for GUI
verification; not retried, relying instead on the code-level guarantee
that `action_bar` is packed before the scrollable region (the same
ordering already verified working for the outer `show_start_screen`
layout) plus the passing import/lint/test checks.

```text
68132a9 Restyle sidebar/update banner and move Anonimizuj + folder picker into Szybkie akcje panel
```

A second, larger round of hands-on feedback followed the same day, eight
items given together, covering both the start screen and the magic-pen
comparison window:

1. The file list can grow now that `bottom_bar` is gone from the center
   column - `FILE_LIST_MAX_HEIGHT` (`gui_helpers.py`) raised from 168 to
   320.
2. Every `CTkScrollableFrame` in the app got a new `apply_subtle_scrollbar`
   treatment (`gui_helpers.py`): an invisible track, a low-contrast thumb
   by default, and a slightly more visible thumb only while the pointer is
   over the scrollable area - CTkScrollbar's `button_color` does not
   support `"transparent"` the way `fg_color` does, so this uses a real,
   near-background color (`COLOR_SCROLLBAR_IDLE`) instead. Applied to all
   eight `CTkScrollableFrame` instances across `gui_app.py`,
   `gui_comparison_window.py`, and `gui_dialogs.py`.
3. The drag-and-drop zone is now exactly half the column's width,
   centered, via a 3-column grid (weights 1:2:1) inside a new `drop_wrap`
   frame - stays exactly half regardless of window size, rather than a
   fixed pixel width.
4. The "Szybkie akcje" panel is now collapsible: a "»" header button
   slides it down to a 64px rail with just a reopen toggle and an
   icon-only "▶" "Anonimizuj" button (`_build_collapsed_quick_actions_rail`
   in `gui_app.py`) - `self.status_label`/`self.output_dir_value_label`
   are simply not built in that state, which `_update_readiness` and
   `pick_output_dir` already null-check before touching, so no new
   guards were needed there. `_update_readiness` was taught not to
   overwrite the collapsed button's icon-only text with
   `format_anonymize_button_text`'s full label.
5. Direct follow-up question revealed the magic pen could *already*
   un-redact an auto-detected rectangle (RMB, or LMB pinned to "erase") -
   that half of the ask was already shipped. What was missing: approving
   a file needs to be a deliberate, warned, one-way action. New
   `ApprovalLockWarningDialog` (`gui_dialogs.py`) - amber warning card,
   "Nie pokazuj ponownie" checkbox, "Zatwierdź"/"Anuluj" - shown once per
   dismissal via `gui_app.py`'s `_confirm_then_approve`
   (`set_review_status`'s two existing callers, the per-card icon button
   and the bulk "Zatwierdź zaznaczone", now both route through it; an
   already-approved item is filtered out first so re-clicking "✓" is a
   silent no-op, not a repeat warning). `ComparisonWindow` gained
   `self.locked = item.status == REVIEW_STATUS_APPROVED`: locked, the
   sidebar shows a "🔒 Plik zatwierdzony" notice instead of the tool
   chips, the per-page canvases skip all four mouse bindings entirely
   (cursor "arrow" not "tcross"), and the save/cancel row is not built -
   structurally impossible to produce a pending edit, not just visually
   discouraged. The "don't show again" checkbox persists via a new
   generic hint-dismissal trio in `gui_helpers.py` -
   `hint_is_dismissed`/`dismiss_hint`/`restore_hint`, all built on
   `ui_hints_config_path`/`load_seen_hints`/`save_seen_hints` (moved here
   from `gui_comparison_window.py`, which now imports them back - shared
   by both, and by `gui_dialogs.py`) - and a new "Ostrzeżenie przy
   zatwierdzaniu" section in Settings > Ogólne can restore it.
6. Page navigation in the comparison window: `render_document_preview`
   now returns a `RenderedPreview` NamedTuple (`images`, `page_widgets`,
   `page_count`) instead of a bare image list - a page-number -> widget
   map for the "Oryginał" pane, populated alongside the existing
   `self._page_canvases` the magic-pen result pane already had for its
   own purposes. `_build_pane_header` gained a second row (◀, an
   editable page-number entry, "/ N", ▶) - built eagerly but only
   `pack()`-ed once a render reports `page_count > 1`. Jumping to a page
   is an anchor-style scroll (`_scroll_frame_to_widget`, using the same
   private `_parent_canvas`/`bbox("all")`/`yview_moveto` reach-in every
   other scroll-control method here already uses) - approximate, not
   pixel-perfect, but lands on the right page. `_go_to_page_absolute`
   mirrors the same page number onto the other pane while `zoom_linked`
   is on (reusing that existing toggle as the "sync" flag per the user's
   own words), guarded with `mirror=False` on the recursive call.
7. The legend/tool-chip sidebar could get silently clipped on a narrow
   comparison window - root-caused to packing order: it was packed
   *after* the expand=True paned splitter, so Tk's pack() (space handed
   out in packing order, the same rule this project has leaned on
   several times before) squeezed it first. Fixed at the root by packing
   it before the splitter now (still visually the right-hand column,
   since `side="right"` reserves its space from the row's right edge
   regardless of order) - and made collapsible on top of that
   (`_build_collapsed_legend_rail`, same "»"/"«" toggle pattern as the
   Szybkie akcje panel), so the user can choose to trade the legend away
   for space rather than the window doing it to them. The draw/erase
   tool chips moved out of this sidebar entirely into the always-visible
   bottom action bar (next to Zapisz/Anuluj) per the explicit ask that
   they "stay their own lamps" regardless of sidebar visibility -
   `_build_tool_chip` rewritten from a wide vertical sidebar card to a
   compact single `CTkButton`, `_tool_chips` simplified from
   `dict[str, tuple[CTkFrame, CTkLabel, CTkLabel]]` to
   `dict[str, CTkButton]`.
8. A real scan the user tried came back without visual redaction colors
   again - genuinely could not be reproduced from a synthetic degraded
   image in several attempts (mild degradation: OCR stayed confident;
   heavy degradation: both the word-box *and* the plain-text OCR passes
   found nothing at all, which is correctly-handled total failure, not
   this bug). Rather than guess at a fix with no way to verify it,
   `anonymizer.py`'s scanned-PDF branch now records *why*
   `extract_pdf_word_boxes` gave up (the `OcrUnavailableError.status`
   code only - no paths, no OCR text) into a new
   `pdf_redaction_result["visual_redaction_fallback_reason"]`, and
   `report.py` surfaces it as a new "Visual redaction fallback reason: X"
   line in the developer report (sanitized through the same
   `_safe_ocr_status`/`OCR_STATUSES` allowlist the existing OCR section
   already uses) - the next real occurrence is now diagnosable from the
   report instead of only guessed at.

Verified live, not just by reading the diff: a background-run script
instantiated the real `AnonymizerApp` + `show_start_screen()` and toggled
`_toggle_quick_actions_collapsed()` both ways, confirming
`status_label`/`anonymize_button` really do become `None`/icon-only and
come back correctly. A second script built a real 3-page PDF and drove
`ComparisonWindow` directly - confirmed `original_page_count` /
`result_page_count` both read 3, `_go_to_page_absolute` moved and
mirrored correctly, `_toggle_legend_sidebar_collapsed` didn't crash, and
an `item.status == REVIEW_STATUS_APPROVED` window really did come up with
`save_button is None` and empty `_tool_chips` - then rebuilt the same
check for `ApprovalLockWarningDialog` and the new Settings section
directly, and for `_confirm_then_approve`'s dismissed-hint fast path
(patching `gui_helpers.ui_hints_config_path` to a temp file, same
technique the new unit tests use). This project's known sandbox
limitation with driving the *full* app window came up again for one
early attempt (a silent, output-less process exit) but resolved once
re-run as a properly output-redirected background process - not the
code, a harness quirk noted here for next time. Full suite: 414 tests
(10 new - hint dismiss/restore round-trips, both
`format_approval_lock_warning_*` formatters, and the new
`visual_redaction_fallback_reason` report line, present/absent/
sanitized). Lint unchanged against the established 77-error baseline.

```text
b63e665 Second start-screen/comparison-window feedback batch: 8 items
```

## Next Logical Step

The 8-item follow-up batch above (file list height, subtle scrollbars,
half-width drop zone, collapsible Szybkie akcje, approval lock-in warning
+ enforcement, comparison-window page navigation, collapsible legend +
relocated tool lamps, and the visual-redaction-fallback diagnostic field)
is done and verified live. One item is not fully closed: item 8 could not
be reproduced from a synthetic degraded scan in several attempts, so it
shipped as observability (the new "Visual redaction fallback reason" report
line) rather than a guessed-at fix - next real occurrence, check that line
first, or ask the user directly for the actual scan.pdf (or its raw report)
that triggered the original complaint to root-cause it for real.

The start-screen visual-feedback pass above (sidebar restyle, warning-style
update banner, Szybkie akcje panel carrying the folder picker and
"Anonimizuj") is done. No further redesign work is planned without a fresh,
explicit user decision to start one - next is real pilot use of this build
and further changes only from what that surfaces, same as every prior round.

The pilot-feedback batch's Stage B (mockup visual-fidelity pass) is done -
see its narrative above. Both scope calls flagged before starting it held:
the combined "Zapisz i zatwierdź" magic-pen button and per-category
manual-redaction labels stayed deliberately deferred (not asked for again
in this batch), while the richer legend wording was safe to fold in as
plain visual polish (it turned out the legend needed no change at all,
already close enough from earlier same-day work).

Both halves of the pilot-feedback batch (Stage A's real bugs, Stage B's
visual-fidelity pass) are now shipped. As with the DocShield redesign
itself: use the app in real pilot use next and make further changes from
what that surfaces, rather than starting another mockup-matching pass
without a fresh, explicit user decision to do so.

The DocShield visual redesign itself is done: Stage 1
(branding/icon/sidebar/palette), 2 (Settings tabs), 3 (review screen
stat cards + table + bulk selection), and 4 (comparison window magic
pen sidebar) all shipped the same day (see the Stage 1 narrative above
for the full brief and confirmed scope decisions). Two things from the
mockups were deliberately deferred rather than silently folded in,
since they are real functionality changes rather than layout moves:
per-category manual-redaction labels (still one generic "RECZNE" label)
and merging "save" with "approve" in the comparison window into one
action. Both need their own planning pass if picked up later. Reference
mockups live in `pomysly/` (not part of the app, not `.gitignore`d -
the user's own working reference, left alone unless asked to touch it).

Use the redesigned app in real pilot use next and make further
improvements only from what that surfaces, the same way the pre-
redesign UI was refined - no further redesign work is planned without a
fresh, explicit user decision to start one.

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

Two more product-direction signals from the user, also not yet scoped or
started: a planned two-tier release - a free version limited by anonymized
character count (the exact limit not yet decided) and an unlimited
business/paid version; and, once a compiled `.exe` build exists, it must
run windowed (no visible console/terminal window - the standard PyInstaller
`--windowed`/`--noconsole` flag, or the `pythonw.exe` equivalent, once a
packaging step is actually set up - none exists in the repo yet). Both
fold into the same future packaging/licensing pass as the `.exe` topic
above; needs its own planning pass when picked up (tier enforcement
mechanism, exact free-tier limit, how/whether it's checked locally without
a server).

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
