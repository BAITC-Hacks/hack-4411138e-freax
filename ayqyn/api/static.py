"""Explicit public frontend assets; never expose runtime data or package sources."""
from ayqyn.paths import ROOT
STATIC = {'index.html','analyze.html','styles.css','analyze.css','app.js','analysis.js','cases.js','sources.js'}
STATIC.update({
    'assets/kazakhtelecom-logo.svg',
    'i18n.js', 'ayqyn.js', 'ayqyn.css', 'demo-sources.js', 'demo.js','report.js','workspace.js','workspace.css','distingt-approved.css','distingt-integration.css','case-store.js','agent-model.js','demo-agent.js',
    'assets/ayqyn-mark.svg', 'assets/c010/demo.json',
    'assets/c010/inputs/C010/before/org.pdf', 'assets/c010/inputs/C010/before/functions.pdf',
    'assets/c010/inputs/C010/after/org.pdf', 'assets/c010/inputs/C010/after/functions.pdf',
    'icons.js',
    'preferences.js',
    'vendor/lucide/createElement.mjs',
    'vendor/lucide/defaultAttributes.mjs',
    'vendor/lucide/icons/arrow-right.mjs',
    'vendor/lucide/icons/building.mjs',
    'vendor/lucide/icons/check.mjs',
    'vendor/lucide/icons/chevron-left.mjs',
    'vendor/lucide/icons/chevron-right.mjs',
    'vendor/lucide/icons/circle-check.mjs',
    'vendor/lucide/icons/download.mjs',
    'vendor/lucide/icons/external-link.mjs',
    'vendor/lucide/icons/file-text.mjs',
    'vendor/lucide/icons/files.mjs',
    'vendor/lucide/icons/git-compare-arrows.mjs',
    'vendor/lucide/icons/info.mjs',
    'vendor/lucide/icons/list-checks.mjs',
    'vendor/lucide/icons/loader-circle.mjs',
    'vendor/lucide/icons/menu.mjs',
    'vendor/lucide/icons/monitor.mjs',
    'vendor/lucide/icons/moon.mjs',
    'vendor/lucide/icons/plus.mjs',
    'vendor/lucide/icons/search.mjs',
    'vendor/lucide/icons/settings.mjs',
    'vendor/lucide/icons/shield-check.mjs',
    'vendor/lucide/icons/sun.mjs',
    'vendor/lucide/icons/trash.mjs',
    'vendor/lucide/icons/triangle-alert.mjs',
    'vendor/lucide/icons/upload.mjs',
    'vendor/lucide/icons/x.mjs',
})

STATIC.update({'distingt-public.css','distingt-usability.css','assets/favicon.svg','assets/favicon-16x16.png','assets/favicon-32x32.png','assets/apple-touch-icon.png','research-client.js','live-chat.js','integration.css'})
# These directories contain only the supplied public artwork, samples and fonts.
for folder, extensions in [('distingt-assets', {'.svg', '.png', '.json', '.pdf'}), ('fonts', {'.woff2'})]:
    STATIC.update(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob('*')
                  if p.is_file() and p.suffix in extensions)
