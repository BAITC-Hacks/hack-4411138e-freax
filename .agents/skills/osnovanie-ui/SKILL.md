---
name: osnovanie-ui
description: Design and refine the Osnovanie document-analysis frontend using 21st.dev references, preserving evidence, analyst review, and the existing vanilla HTML/CSS/JavaScript application. Use for layout, components, styling, responsive behavior, and frontend visual review.
---

# Osnovanie UI

Build a polished analyst workspace for comparing organizational documents. Prioritize readable evidence, clear changes, and a short path from upload to a reviewable conclusion.

## Start with the actual application

- Read the current README and REVIEW_HANDOFF; inspect the working tree and incoming team changes. These files describe implementation limits, not decorative text to remove.
- The initial stack is a Python server with vanilla HTML/CSS/JavaScript. Check whether teammates have changed it before acting. Do not introduce React, Next.js, Tailwind or a build pipeline only to paste a component.
- Main workspace: `analyze.html`, `analyze.css`, `analysis.js`, shared `styles.css`. `index.html` is a separate practice page. The server explicitly allows static files in `server.py`; adding a new stylesheet or script also requires updating that allowlist.
- Preserve DOM IDs and event contracts used by `analysis.js`, backend response fields, file limits, and download behavior. Coordinate schema changes with the backend/ML owner.

## Choose and adapt references

Read [the reference shortlist](references/21st-components.md) when choosing components or configuring 21st MCP. Read [the design direction](references/design-direction.md) when changing visual style or page structure.

If 21st MCP tools are connected, discover their actual names, search by the UI need, and retrieve only the selected components. Prefer read-only search/retrieval for this workflow. Do not send uploaded documents, API keys or internal source text to the design service; generic layout descriptions suffice.

If MCP requires login or a plan, continue with public previews, page markdown and original HTML/CSS implementation. Do not report a configured server as authenticated, or a reference as installed code. Hosted generation is optional and separate from component access.

Before copying source, verify the individual component's license and dependencies; the platform's or MCP package's license is not a blanket license for every component. Record copied/adapted source, author, license and local destination in the reference register. Unknown-license entries are preview references until clarified. Keep required notices with copied source.

When adopting React reference ideas into this app, implement native HTML/CSS/JavaScript equivalents. Preserve the visual interaction that helps the analyst; omit unrelated chat, billing, account menus, marketing sections and dashboards.

Use Context7 for actual library/API/CLI documentation questions: resolve the library ID, then query the relevant concept. It is unnecessary for editing ordinary CSS or reviewing application business logic.

## Evidence and state invariants

- Keep before/after versions explicit in uploads, findings and source views.
- Candidate count is not a count of confirmed violations. Source existence is not proof of a conclusion. Never add a fabricated confidence, accuracy, savings metric or compliance score.
- Show actual processing mode (AI, rules, fallback), warnings, empty results and failure states. A successful HTTP request with no findings does not establish absence of risks.
- Preserve analyst review controls. Status labels, not color alone, communicate meaning.
- A transfer must not look like a loss. A number change must not look like a deleted duty. Style the returned finding type without changing its meaning.
- Render document text safely as text, retaining quotation boundaries and source IDs; never inject source HTML to obtain formatting.

## Finish with the real workflow

Inspect desktop (around 1440 px) and mobile (around 390 px). Check keyboard focus and dialogs, long filenames, long Russian quotations, wrapping, reduced motion, and table scrolling within its container. Keep source text selectable.

Verify the changed behaviors: load examples or two DOCX, run analysis in the actual configured mode, filter, open evidence, set analyst review, export the report. Use synthetic UI fixtures only when clearly labeled; do not replace live results with attractive sample data.

Run relevant existing checks after functional changes. For CSS-only changes, prioritize browser inspection over tests that assert style strings. Preserve progress notes, document remaining limitations, and synchronize teammate changes before pushing. Report what was actually verified and whether 21st MCP was usable.
