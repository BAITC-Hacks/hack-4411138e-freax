# AYQYN frontend verification — 2026-09-23

## Executed checks

- Existing stack: vanilla ES modules, no frontend build step. Node syntax checks for changed JavaScript and UI test script passed.
- `node scripts/check-frontend.cjs`: 322 keys in RU/KK/EN, placeholder parity, used labels, theme preference persistence/fallback, 12 established text contrast pairs. Also checks the C010 adapter, no implicit human confirmation, all evidence IDs, four exact PDF hashes and the production Markdown builder (demo label, review decision, note, page, quote, no undefined fields).
- Full Python suite: 182 tests, OK, 1 skipped. Earlier runs had intermittent `interrupted` responses in research HTTP tests (different cases each run); the focused 21-test retry and final full run passed. No research/backend behavior was changed to mask those failures. Final suite was run through unittest discovery with a diagnostic-only wrapper printing exception type on interrupted events.
- Static HTTP check: all 11 new/relevant resources return 200; four originals contain real PDF bytes.
- Browser execution: Codex in-app browser at 1440×1000, 390×844 and 360×800. Actual browser screenshots, not generated mockups. No document horizontal overflow at tested sizes. Console error logs empty in the primary and error-recovery test tabs.
- `scripts/check-ui.cjs` updated for the new landing/workspace route and overview tab; syntax-checked, **not executed through standalone Playwright**. Interactive checks below were performed through the browser tool.

## Actual browser scenarios

1. Open landing; launch workspace; select Before DOCX with Enter using the native file chooser. Add a PDF alongside it: the valid DOCX remains and the PDF gets a named inline rejection. Add After DOCX and run the real /api/analyze endpoint: rules mode, 4 candidates.
2. Load eight fictional DOCX and run the real endpoint: 6 candidates, 8 documents extracted/assigned; real stage times and evidence counts displayed in AgentTrace. This is live rule-based processing, not C010 substitution and not a model-quality test.
3. Filter the real department findings, open a quoted source, choose a human review decision and note, filter unreviewed results to an empty state, reset filters and open conclusion/export. DOCX shows that page numbers are unavailable rather than inventing them.
4. Open C010 separately: 4 PDF documents, 6 prepared candidates, none automatically human-confirmed. Inspect a potential loss: original function and both After documents in comparison scope with a caution against inferring organization-wide loss. Confirm a transfer, add a note and observe the labeled demo conclusion.
5. Demo → new upload → real result preserves the eight selected files and returns to rules mode. Guide and browser Back return to the real result. Direct #/app/new and #/app/demo load correctly. Clicking the logo on the current landing route returns to the top.
6. Source selectors change independently; keyboard resizer changes 50→45; Shift+Tab wraps from close to the last dialog action, Escape closes and restores the source button. Opening a source scrolls directly to the cited passage. Mobile dialog spans the viewport and stacks documents.
7. RU/KK/EN changed on landing and real results. Original Russian quotes, filenames, candidate rows and mode remain unchanged. Theme switches work on landing, workspace and sources. Native keyboard file selection and visible focus checked. Reduced motion/touch guards inspected in code; OS-level reduced-motion emulation was not performed.
8. Separate error-recovery tab: corrupted DOCX receives a real server error, visible details and Retry; replacing the packet with eight valid example files successfully returns rules results. Test tab closed afterwards.
9. Export button executed for demo and real results; UI confirms preparation. The exact production Markdown builder passed content assertions. The in-app browser did not expose a saved download path, so final OS-level file-save completion was **not independently verified**.

## Screenshot inventory

Captured under the task outputs/ayqyn-editorial folder, not committed as generated binary QA artifacts:
- landing-desktop-light.png / landing-desktop-dark.png — viewport 1440×1000
- landing-mobile-light.png / landing-mobile-dark.png — viewport 390×844
- workspace-upload-light.png — viewport 1440×1000
- workspace-results-light.png / workspace-results-dark.png — viewport 1440×1000, actual eight-DOCX rules response
- sources-desktop-dark.png — viewport 1440×1000
- source-mobile-light.png / source-mobile-dark.png — viewport 390×844, C010

## Remaining integration limits

- Main upload form accepts DOCX only. Text PDF and durable agentic research exist in separate /api/packet/read and /api/research endpoints; connecting their asynchronous state, trace and result contract to this UI remains separate work. OCR and Excel are absent.
- Current /api/analyze is a request/response operation, with no live stage stream. The waiting indicator is indeterminate; completed trace comes from the actual response. Nothing simulates completion.
- Semantic model quality is not established by these frontend tests. Existing R8/R9 research evaluation documents report missed and incorrect findings. No live provider call was made for this visual iteration.
- DOCX contract has paragraph/clause IDs but no physical page mapping or structured ownership fields for every finding. The UI labels missing pages/owners rather than synthesizing values.
- Review notes and decisions are tab-memory only; refresh loses them. Export is Markdown, not PDF/DOCX. Server AI-run persistence is disclosed, but UI retention/deletion controls are absent.
- An HTTP failure for the complete upload lacks a per-file error identifier; it is shown at request level with server details. Client format/size failures are shown next to each rejected filename.
