"""Bounded PDF evidence extraction, without OCR or inferred reading order."""

import hashlib
import io
import re
import zlib

from pypdf import PdfReader
from pypdf.errors import PyPdfError


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
MAX_TEXT_CHARS = 250_000
MAX_PAGE_CONTENT_BYTES = 8 * 1024 * 1024

_CLAUSE = re.compile(r"^\s*(\d+(?:\.\d+)+)\.?(?=\s|$)")
_READ_ERRORS = (PyPdfError, OSError, ValueError, TypeError, KeyError,
                IndexError, AttributeError, OverflowError, RecursionError,
                zlib.error)
_EXTRACTION_WARNING = (
    "PDF text follows the embedded content stream. Paragraph boundaries and "
    "reading order are heuristic; headers and footers are retained. No OCR, "
    "printed-page mapping, or owner/function associations are inferred."
)


def _page_text(page):
    starts = []
    fragments = []
    rotated = False

    def visit(text, cm, tm, font, size):
        if text:
            fragments.append(text)

    def visit_operand(operator, operands, cm, tm):
        nonlocal rotated
        if operator not in (b"Tj", b"TJ", b"'", b'"'):
            return
        # Only use horizontal origins as a layout warning signal. In complex
        # PDFs visitor coordinates are approximate, not a reading-order oracle.
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        strings = operands[0] if operator == b"TJ" else operands[-1:]
        if sum(len(value) for value in strings if isinstance(value, (str, bytes))) >= 12:
            starts.append(x)
        b = tm[0] * cm[1] + tm[1] * cm[3]
        c = tm[2] * cm[0] + tm[3] * cm[2]
        rotated = rotated or abs(b) > 0.01 or abs(c) > 0.01

    try:
        contents = page.get_contents()
        if contents is not None and len(contents.get_data()) > MAX_PAGE_CONTENT_BYTES:
            raise _ContentLimitError
        text = page.extract_text(extraction_mode="plain", visitor_text=visit,
                                 visitor_operand_before=visit_operand)
        width = float(page.mediabox.width)
    except _ContentLimitError:
        raise ValueError("PDF page content exceeds the 8 MB extraction limit.") from None
    except _READ_ERRORS as exc:
        raise ValueError("Malformed or unsupported PDF page content.") from exc

    # Repeated distant origins suggest columns, a table, or a diagram. Sorting
    # these diagnostic coordinates never reorders the extracted evidence.
    clusters = []
    for x in sorted(starts):
        if clusters and x - clusters[-1][0] <= max(8, width * 0.035):
            clusters[-1][1] += 1
        else:
            clusters.append([x, 1])
    repeated = [x for x, count in clusters if count >= 2]
    columns = len(repeated) >= 2 and repeated[-1] - repeated[0] > width * 0.18
    return text, columns or rotated, fragments


class _ContentLimitError(Exception):
    pass


def _paragraphs(text, section, unsupported_layout, fragments):
    pending = []
    if unsupported_layout:
        # The extractor can concatenate columns on the same baseline. Split at
        # visitor boundaries as well as newlines, but only by slicing the final
        # extraction: form callbacks may repeat text or include nested content.
        boundaries = [0]
        cursor = 0
        for fragment in fragments:
            start = text.find(fragment, cursor)
            if start >= 0:
                cursor = start + len(fragment)
                boundaries.extend((start, cursor))
        boundaries.append(len(text))
        for start, end in zip(boundaries, boundaries[1:]):
            for line in text[start:end].splitlines(keepends=True):
                if line.strip():
                    match = _CLAUSE.match(line)
                    yield line.rstrip("\r\n"), match.group(1) if match else ""
        return

    for line in text.splitlines(keepends=True):
        match = _CLAUSE.match(line)
        if match or not line.strip():
            if pending:
                yield "".join(pending).rstrip("\r\n"), section
                pending = []
            if match:
                section = match.group(1)
        if not line.strip():
            continue
        if section:
            pending.append(line)
        else:
            yield line.rstrip("\r\n"), ""
    if pending:
        yield "".join(pending).rstrip("\r\n"), section


def parse_pdf(data: bytes, filename: str) -> dict:
    """Return DOCX-compatible paragraphs with physical PDF page provenance.

    Dotted clause numbers label subsequent lines on supported layouts, including
    continuations on later pages. A paragraph never spans physical pages. Text
    is an unchanged extraction substring: internal whitespace, line breaks and
    hyphenation survive; separating line endings and empty lines are not part
    of paragraph text. Unsupported layouts disable continuation grouping.
    unread_pages lists physical pages without extractable text;
    layout_warning_pages separately lists detected layout uncertainty. Neither
    list establishes complete visual or geometric reading of a page.

    Limits reject the whole input, never return a truncated result. These are
    input/output limits, not a process-level memory or execution-time sandbox.
    """
    if not isinstance(data, bytes) or not data:
        raise ValueError("Provide a non-empty PDF as bytes.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("PDF size exceeds the 10 MB limit.")
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
    except _READ_ERRORS as exc:
        raise ValueError("Malformed or unsupported PDF file.") from exc
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported.")
    try:
        page_count = len(reader.pages)
    except _READ_ERRORS as exc:
        raise ValueError("Malformed PDF page tree.") from exc
    if page_count > MAX_PAGES:
        raise ValueError("PDF exceeds the 200-page limit.")

    paragraphs = []
    warnings = [_EXTRACTION_WARNING]
    unread_pages = []
    layout_warning_pages = []
    section = ""
    text_chars = 0
    for index in range(page_count):
        try:
            page = reader.pages[index]
        except _READ_ERRORS as exc:
            raise ValueError("Malformed PDF page tree.") from exc
        text, unsupported, fragments = _page_text(page)
        text_chars += len(text)
        if text_chars > MAX_TEXT_CHARS:
            raise ValueError("PDF extracted text exceeds the 250,000-character limit.")
        page_number = index + 1
        if unsupported:
            layout_warning_pages.append(page_number)
            warnings.append(
                f"Page {page_number}: unsupported layout (possible columns, table, "
                "diagram, or rotated text). Extracted fragments are kept separate; "
                "reading order and owner/function associations are not established."
            )
            section = ""
        if not text.strip():
            unread_pages.append(page_number)
            warnings.append(f"Page {page_number}: no extractable text; OCR was not performed.")
            section = ""
        for value, label in _paragraphs(text, section, unsupported, fragments):
            paragraphs.append({
                "id": f"p{len(paragraphs) + 1}",
                "section": label,
                "text": value,
                "page": page_number,
                "printed_page": None,
            })
            section = label
        if unsupported:
            section = ""
    if not paragraphs:
        raise ValueError("PDF has no extractable text (empty or image-only); OCR is required.")
    return {
        "name": str(filename),
        "sha256": hashlib.sha256(data).hexdigest(),
        "paragraphs": paragraphs,
        "format": "pdf",
        "page_count": page_count,
        "warnings": warnings,
        "unread_pages": unread_pages,
        "layout_warning_pages": layout_warning_pages,
    }
