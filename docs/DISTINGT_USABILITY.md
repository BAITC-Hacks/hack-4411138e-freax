# Distingt — usability refinement, 2026-09-23

The approved blue palette, local Manrope, glass details, three languages and two themes remain. Production still uses Python and native HTML/CSS/JavaScript. No runtime dependency or API contract changed.

## User-facing changes

### Latest follow-up: individual finding pages

- Two glass hero cards now surround a readable HTML before/after comparison. All three open C010-F03. Floating motion pauses on hover/focus and is disabled on small screens and for reduced motion.
- Logo plates are transparent; the original blue symbol is retained and the SVG wordmark follows the image's explicit light/dark color scheme.
- Chat alone uses a 56px toolbar and smaller heading/tabs. The redundant local-history sentence was removed from the case header.
- Each finding has a dedicated `#/app/cases/<case>/findings/<finding>` page. Titles and source actions are links. `#/app/demo/findings/C010-F03` and the older `#/app/demo#finding-C010-F03` both work. Existing document selectors, original files, analyst decisions and comments are retained. Previous/next navigation updates the URL.
- Document headers and review fields are aligned. Browser Back restores list position/focus; chat drafts and reading state remain in the case. Mobile documents are sequential.

Follow-up checks, without screenshots: frontend checks passed with 424 translation keys × three locales; agent-state checks, JavaScript syntax and diff checks passed. Browser layout checks at 360/390/768/1024/1440px showed no horizontal overflow for hero and finding page in light/dark, or compact chat in light. Checked legacy and new demo URLs, title/source links, next finding, direct reload, Escape, Back/focus, draft preservation and comment persistence. RU/KK/EN leave source quotations unchanged. No console errors recorded. Full backend tests and screenshot review were not repeated for this frontend-only follow-up; the following verification list describes the preceding iteration.

### Previous iteration

- Official Kazakhtelecom logo with its original proportions; aligned navigation and mobile menu. Full-name language menu supports arrows, Home/End, selection, Escape and outside clicks.
- The hero's decorative eyebrow and raster artwork are replaced by a readable, explicitly synthetic C010-F03 comparison. Its link opens the actual finding and reserve-power quotation, with the inspected after-document scope.
- Desktop sidebar collapse persists; mobile drawer supports backdrop, Escape and focus return. Findings use a compact localized badge.
- Upload offers one Start analysis action. Advanced connection controls are available only from Data processing. The existing server configuration selects AI when a key or loopback provider is available; otherwise wording comparison is disclosed. Configuration loading cannot silently race with submission. Rules/AI/fallback responses remain distinct.
- Attachments sit above the input surface. Filenames retain extensions, remove buttons remain visible, textarea growth is bounded, and wide content scrolls internally.
- Per-case reading position uses a message anchor and offset. Draft, context, expanded actions and source position survive tab/source navigation and reload. New answers follow only when the reader is at the bottom; otherwise a New messages button appears.
- Source panels preserve the invoking citation and keyboard focus. Mobile sources use a fullscreen view; document comparison uses sequential panes on small screens.
- Shared guide, about and data-processing pages, compact workspace footer, consistent icons, thin scrollbars, short transitions and reduced-motion CSS. SVG/16px/32px/180px icons and localized browser title are included.

`distingt-approved.css` remains the original archive CSS. Targeted changes live in `distingt-public.css`, `distingt-usability.css`, `distingt-integration.css` and `workspace.css`.

## Verification performed

- Final full Python suite: 182 tests, one skipped, all remaining tests passed. An earlier research HTTP run had one intermittent failure; isolated HTTP suites and the final full rerun passed.
- `check-frontend.cjs`: 422 keys × three languages, placeholders, preferences, fixture source validation and report tests passed. Existing contrast checks cover their predefined pairs, not a complete accessibility audit of the new screens.
- `check-agent.cjs`: reader anchors/reflow/hidden views, filename extensions, case/reference validation, message/event consistency, cancellation/failure, immutable artifacts and demo restrictions passed. JavaScript syntax and `git diff --check` passed.
- Browser: landing, upload, chat, results, sources, guide, about and data-processing pages at 360/390/768/1024/1440px in both themes, without horizontal page overflow. Three UI languages, original quotation preservation, loaded fonts, mobile menus, visible keyboard focus, Escape/focus return and bounded long input checked.
- Keyboard file chooser accepted a long-named synthetic DOCX and reported an unsupported TXT beside its filename. Eight example DOCX passed through the actual rules backend. Results, empty-filter reset, source viewing, review/comment and conclusion were checked. A Markdown download was present in Downloads with the current run timestamp.
- Reading position survived reload at the same offset; source/tab navigation retained draft and attachment. A new local demo answer left the reader in place and showed the New messages action. No JavaScript console errors were recorded in the checked scenarios.
- `check-ui.cjs` language selectors were adapted and syntax checked; its standalone browser runner was not executed. Browser checks used the desktop browser tools. Reduced-motion rules were inspected; an actual mobile keyboard/IME device and full accessibility audit were not tested.

## Preserved boundaries

Real document analysis, original sources, human review and Markdown export remain connected. Live conversational analysis and document-edit proposals are still unavailable; the separate C010 chat performs clearly labeled local sample operations. Backend research quality has not been re-evaluated by this visual iteration. Browser-local case storage is not authenticated shared storage.
