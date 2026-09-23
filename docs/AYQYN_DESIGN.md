# AYQYN — composition and source review

## Reference study and provenance

The existing Python + HTML/CSS/ES modules stack is retained. No framework migration, runtime CDN, analytics, font request or new dependency.

| Reference | Material studied | Adopted principle |
| --- | --- | --- |
| User-supplied AYQYN_frontend_source.zip | dist/index.html, style.css, app.js, assets/demo.json and C010 inputs | AYQYN mark, explicit Before/After sets, navigation and separate synthetic example. Its upload/export simulation was not substituted for the real API. |
| Armeta HTML inside the supplied ZIP | references/armeta-reference.html; heading scale/tracking, container widths, section spacing, navigation/footer structure | Restrained editorial rhythm, strict shared alignment and varied section proportions. No scripts, analytics, copy, graphic assets or brand colors were transferred. |
| KazPunct / maussym/girlygirl_1st_case | hero-section.tsx, glsl-hills.tsx, globals.css | Large typography, open spacing, prominent immediate actions. The WebGL scene was not copied. |
| freax_ds / maussym/freax_ds | App.module.css, index.css | Fine borders, a small amount of glass in navigation, coherent geometry and hover states. No lime palette or entrance screen. |
| freaxlab / maussym/freaxlab | HeroSection.tsx, index.css, App.css | Monospace section markers and a direct transition from product explanation to the working tool. No external scene dependency. |

The three team repositories were inspected in the preceding design iteration; their application code was not copied. No repository-root licenses were found, so this implementation only borrows visual principles. Lucide remains the locally vendored ISC dependency (vendor/lucide/LICENSE).

The user explicitly supplied and approved the prototype. `assets/ayqyn-mark.svg` is its mark, `assets/c010/demo.json` and four `assets/c010/inputs/C010/**/*.pdf` are its synthetic C010 example. The adapter resets all user review decisions; reference annotations are not analyst confirmations. PDF SHA-256 values in the copied JSON were computed from the exact served originals. No other case or Armeta asset is copied. The user-provided Kazakhtelecom SVG remains unchanged.

## Composition

The hero is a headline over one large readable comparison, not floating cards. Literal Russian source quotations show the transfer of purchasing responsibility; interface translations do not alter them. The next section studies the potential audit conflict, followed by a ruled change index, four compact workflow stages, an accessible native FAQ, a final action and a meaningful footer. Every example is visibly labeled synthetic.

Shared colors come from analyze.css: blue/cyan/navy/neutral, with independent light/dark contrasts. AYQYN-specific geometry and composition live in ayqyn.css and are scoped to public/editorial or workspace components. Dense tables and documents remain opaque. Segoe UI/system is the primary Russian/Kazakh-capable font; monospace is limited to IDs and small labels. Headings use moderate weight and tight tracking; mobile headlines keep readable phrases. No global horizontal-overflow masking.

The only pointer decoration is a small highlight on the comparison frame, disabled for touch and reduced motion. No hero animation gates access. Native hover/focus/open states communicate interaction. CloudLoader animates only while an actual request is pending. Timeline explains the stages; AgentTrace renders returned completed-stage counts/times. No simulated progress percentage, timed result or fake streaming trace.

## State and integration

Main upload/API contracts, backend parsing and model/research code are unchanged; server changes only extend the explicit static allowlist. The main UI continues to use /api/analyze. Independent Before/After multi-file inputs supplement mixed auto-assigned upload. Per-file format/size errors retain valid files, and server failures have a retry path.

Demo has its own result cache and real uploads have another. Opening C010 never runs /api/analyze, replaces selected files or claims that they produced its findings. Overview, departments, functions, risks and conclusion share source/review controls. Loss candidates display original evidence and the supplied After comparison scope with an explicit limitation. PDF pages are displayed only when present in C010 data; DOCX pages remain explicitly unavailable. Reviewer notes/status are memory-only and appear in the actual Markdown export.

The source dialog has independent document selectors, a keyboard resizer, explicit focus wrapping, Escape dismissal and focus restoration. It scrolls to the cited passage after opening. On mobile it fills the screen and stacks documents sequentially. Pages describing data reflect actual server upload, provider transmission and local run persistence.
