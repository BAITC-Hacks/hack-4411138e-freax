# Distingt: integrated workspace and approved design

## Current implementation

The Python/vanilla JS application remains the canonical product. `/api/analyze`, `/api/packet/read` and the research APIs retain their existing contracts. The server change is limited to public static asset allowlists. No React dependency or bundler was added to the production app.

`ayqyn.js` now renders the supplied Distingt design: the markup from the archive's `reference-original` corresponds to `src/DistingtDemo.jsx`. `distingt-approved.css` preserves the supplied CSS declarations, including Manrope subsets, 1500/1050/750px breakpoints, glass artwork and animations. `distingt-integration.css` bridges the existing operational components to these tokens. The local font license is in `fonts/LICENSE`; existing Lucide ISC attribution remains. The original user-supplied images and educational assets are in `distingt-assets/`.

The hero and all landing section rectangles match the reference at 1440×900. The 360×800 hero uses the same 52px Manrope 500, 60.84px line height, -2.86px tracking and bounding rectangle. The original raster artwork still contains the old AYQYN wordmark; it was preserved rather than replacing the approved glass composition. Text UI uses Distingt.

Intentional functional differences from the reference:

- The landing describes actual DOCX upload/API behavior; it does not promise unimplemented XLSX support or that uploaded files never leave the browser. Decorative cards are marked DEMO / C010.
- The rail includes saved cases and model settings. Workspace tabs include Agent / Results / Documents / Conclusion.
- Upload keeps the mixed packet, case name, classification controls and real rules/AI actions. Limits come from the current API rather than the static prototype.
- Counts and findings come from the saved response. No invented retained-department rows or prepared analysis stages are added.
- The existing result source dialog remains wide enough for two independent document selectors. Chat uses the approved surface/typography in a 400px right panel, expandable on desktop and fullscreen on mobile.
- Existing Markdown export is retained; no text file is renamed PDF or DOCX.

## Case and conversation boundary

`case-store.js` persists case snapshots, original File objects, review decisions, structured messages, immutable Markdown artifacts, selected tab and selected source in IndexedDB on this origin. A draft is also mirrored to sessionStorage for immediate reload recovery. Language and theme use the previous preference keys. Model credentials are never stored in these records. This is a local single-browser implementation, not authenticated multi-user storage; clearing site data removes the history. Different ports/browsers have separate histories.

Cases use an immutable analysis-version ID; each new primary analysis creates a separate case. Human review updates the saved finding review fields and marks earlier conclusion artifacts outdated without rewriting their content. Backend document revisions/proposals are not implemented. Case writes use an IndexedDB transaction with a monotonic revision; another tab's stale write fails visibly instead of silently overwriting it.

After a successful analyze response the app enters Agent once if the user is still on the submitted route. Otherwise it displays an Analysis ready link. Reload never reruns analysis or automatically resends a question. Interrupted local demo operations remain interrupted with their partial messages; retry places the prior request in the composer for explicit submission.

`agent-model.js` stores text, tool, citation, finding/comparison, notice and artifact parts separately. IDs and analysis-version references are validated. Client message IDs and event IDs/sequence numbers are deduplicated; one active local run is allowed. Terminal runs reject late events. The reducer's checks are frontend consistency checks, not server authorization.

## Explicit local C010 adapter

`demo-agent.js` refuses all real uploaded-file cases. It re-fetches the static C010 fixture and validates quotations against the saved fragment IDs. Recheck reads the chosen finding's fragments and compares their literal shared wording; it is not a model or semantic research agent. Free text uses a clearly disclosed literal search. Draft builds real Markdown from the saved result, review decisions and separately labeled user clarifications.

Tool cards reflect these actual local operations and their completion/failure/cancellation. There are no decorative waits, random percentages, hidden question-to-canned-answer dispatches or fabricated server events. Stop aborts this local adapter; the UI does not call it server cancellation. Real cases show a disabled chat submit and explain the missing conversation API. Results, sources, analyst review and export remain available.

## Required backend adapter (not implemented endpoints)

The existing research run API is not a conversation API. Its existence does not establish message persistence, guest isolation, resumable chat events, cancellation or document proposals. Do not send client assertions of ownership as authorization.

A live adapter needs these agreed capabilities, with routes chosen by the backend team:

1. An opaque guest/server session and server-owned case access checks; persisted cases, document-version IDs, analysis-version IDs and conversation IDs.
2. Submit `{case_id, conversation_id, analysis_version_id, client_message_id, text, locale, context_refs}`. The server validates every ref's membership and original text. Reusing an idempotency ID returns the same message/run.
3. Authoritative typed events `{event_id, sequence, conversation_id, analysis_version_id, run_id, type, payload}` and replay from the last event cursor. Gap recovery must fetch/replay missing events, not silently advance.
4. Server execution of search/read/compare/recheck/draft tools, with scope, evidence and explicit partial/error states. Model keys and tool execution stay server-side.
5. Cancellation request acknowledged with a terminal run state before permitting another live run. Disconnection is distinct from cancellation.
6. Durable human review/artifact APIs. Artifact version/export response must refer to the selected immutable content and actual MIME/file format.
7. Proposal APIs that return original clause, proposed wording, basis and current revision; accept/reject uses optimistic version checks. Originals remain immutable. Applying edits creates a working document version and explicitly marks dependent analyses/artifacts stale.

The live backend still has its previously documented semantic R8/R9 evaluation limitations. This UI work does not change or validate model quality.

## Verification

- Python: 182 tests, one skipped, all remaining passed on the final functional run.
- `node scripts/check-agent.cjs`: reference isolation, duplicate messages/events, sequence gaps, single active run, late-event rejection, C010 quotations, cancellation/failure, reload interruption, artifact immutability and user-clarification export passed.
- `node scripts/check-frontend.cjs`: shared RU/KK/EN keys/placeholders, preferences, fixture references/hashes and Markdown passed. The script's historical color-pair checks are not a full accessibility audit of the supplied visual palette.
- Native browser: actual eight-DOCX rules API → new case → Results → source → human review → reload recovered the same decision and comment. Missing real chat remained explicit and disabled.
- C010: duplication question → actual fixture read → §2.2 / §2.7 citations → source → user clarification → Markdown V1 and V2. V1 became outdated after a review change, V2 included the change. Reload restored messages/artifacts without duplicates.
- Desktop 1440×900; mobile 390×844 and 360×800; light/dark; RU/KK/EN; visible keyboard focus, source Escape/focus return, mobile source focus trap, tab arrows, mobile navigation and source expansion checked. No captured JS error/warning in the tested current page.
- Composer fits within the mobile viewport; Shift+Enter and immediate draft recovery were checked. Physical mobile keyboard and IME composition were not device-tested; composition guards and visualViewport resize handling are implemented.
- Download action builds a Markdown Blob with `.md`; its exact content is previewable and tested. The in-app browser did not emit a native download event during this run, so browser-to-disk download completion is not claimed. An actual prepared demo artifact is separately saved with the review deliverables.
- `scripts/check-ui.cjs` was adapted and syntax-checked, not executed via a separate Playwright process. Browser validation used the permitted UI automation surface.

Temporary animation disabling was used only for comparable screenshots and is removed from production CSS. Original reduced-motion rules remain.
