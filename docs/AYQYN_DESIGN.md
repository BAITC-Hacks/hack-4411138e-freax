# AYQYN · freax visual system

## Reference study

No license was found at the reference repository roots. Their application code was not copied; the implementation uses original HTML/CSS/JS inspired by their visual principles.

| Reference | Components/styles read | AYQYN adaptation |
| --- | --- | --- |
| [KazPunct](https://github.com/maussym/girlygirl_1st_case) / [site](https://kazpunct.vercel.app/) | src/components/hero-section.tsx, glsl-hills.tsx, src/app/globals.css | Bold compact typography, open composition, clear two-button hero, atmospheric movement implemented as lightweight CSS gradients instead of its Three.js shader. |
| [freax_ds](https://github.com/maussym/freax_ds) / [site](https://freax-ds-3568.vercel.app/) | frontend/src/app/App.module.css, frontend/src/index.css | Layered glass cards, 1 px luminous edges, consistent rounded geometry, subtle hover and staggered entrance. Lime/serif fonts/splash were not transferred. |
| [freaxlab](https://github.com/maussym/freaxlab) / [site](https://freaxlab.vercel.app/) | frontend/src/components/HeroSection.tsx, frontend/src/index.css, frontend/src/App.css | Small monospace labels, technical graphic detail, direct transition into a working tool. Original CSS document composition instead of its external UnicornStudio scene. |

The public sites could not be fetched by the web text reader; repository source inspection was the basis of the study. These are inspirations, not copied components. Lucide remains the existing locally vendored ISC dependency (vendor/lucide/LICENSE).

## Shared tokens and components

- Blue #0085CF, cyan #42C9FF, navy #102A43, light #F4F7FB, dark #0B1220. Text/button colors use the existing contrast-safe theme variants. Semantic risk colors are reserved for actual statuses. Original Kazakhtelecom logo is byte-preserved.
- Segoe UI/system font supports Russian and Kazakh. Consolas/system monospace only for small labels, IDs and clause numbers. No runtime font/CDN request.
- Radii 10–16 px; 1 px borders; low-opacity blue shadows; transform/opacity animation around 260 ms. Documents and tables retain opaque readable backgrounds.
- Parallax: pointer translation up to 10/8 px and rotation 2.5/3 degrees; small scroll translation. Touch has a static simplified composition. Visibility and reduced-motion stop decorative work; requestAnimationFrame is event-driven, not a perpetual loop.
- CloudLoader reflects a pending real request. It does not decide when analysis finishes.
- Timeline explains upload, matching, source review and report, without years or unrelated photography.
- AgentTrace displays returned server milestones for a completed run with counts and elapsed time. It does not stream invented tool/model activity.
- Hero cards and compact interactive preview are explicitly labeled examples in ru/kk/en. The example upload is a separately labeled fictional eight-DOCX packet that runs through the actual backend.

## Main implementation files

analyze.html, ayqyn.css, ayqyn.js, analyze.css, analysis.js, i18n.js. The supplied Kazakhtelecom SVG is used as-is; AYQYN/freax marks use typography.
