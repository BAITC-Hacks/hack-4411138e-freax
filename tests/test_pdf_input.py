import hashlib
import io
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (DecodedStreamObject, DictionaryObject,
                           NameObject, NumberObject)

import pdf_input


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "osnovanie_dataset_v1" / "inputs"
REAL = ROOT / "osnovanie_all_materials" / "03_real_sources" / "original_pdfs"


def pdf(pages, password=None, image_only=False):
    """Build real PDF bytes, with independently positioned text drawing commands."""
    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    font_ref = writer._add_object(font)
    for lines in pages:
        page = writer.add_blank_page(width=600, height=800)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})})
        operations = []
        for index, line in enumerate(lines):
            x, y, value = line if isinstance(line, tuple) else (40, 740 - 16 * index, line)
            encoded = value.encode("ascii").hex()
            operations.append(f"BT /F1 12 Tf 1 0 0 1 {x} {y} Tm <{encoded}> Tj ET\n")
        if image_only:
            image = DecodedStreamObject()
            image.set_data(b"\x00\x80\xff")
            image.update({NameObject("/Type"): NameObject("/XObject"),
                          NameObject("/Subtype"): NameObject("/Image"),
                          NameObject("/Width"): NumberObject(1),
                          NameObject("/Height"): NumberObject(1),
                          NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                          NameObject("/BitsPerComponent"): NumberObject(8)})
            page["/Resources"][NameObject("/XObject")] = DictionaryObject({
                NameObject("/Im0"): writer._add_object(image)})
            operations.append("q 100 0 0 100 40 40 cm /Im0 Do Q\n")
        stream = DecodedStreamObject()
        stream.set_data("".join(operations).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    if password is not None:
        writer.encrypt(password, owner_password="owner-secret")
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


class ParsePdfTests(unittest.TestCase):
    def test_contract_exact_text_and_numbered_continuations(self):
        raw = pdf([["Document title", "2.1. Keep  double spaces and hyphen-",
                    "ated continuation.", "2.2", "Separate clause."]])
        result = pdf_input.parse_pdf(raw, "actual.pdf")
        self.assertEqual(result["name"], "actual.pdf")
        self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["format"], "pdf")
        self.assertEqual(result["page_count"], 1)
        self.assertIsInstance(result["warnings"], list)
        self.assertEqual(result["unread_pages"], [])
        self.assertEqual(result["layout_warning_pages"], [])
        self.assertEqual(result["paragraphs"], [
            {"id": "p1", "text": "Document title", "section": "", "page": 1,
             "printed_page": None},
            {"id": "p2", "text": "2.1. Keep  double spaces and hyphen-\nated continuation.",
             "section": "2.1", "page": 1, "printed_page": None},
            {"id": "p3", "text": "2.2\nSeparate clause.", "section": "2.2", "page": 1,
             "printed_page": None},
        ])

    def test_physical_pages_and_continuation_do_not_merge_pages(self):
        result = pdf_input.parse_pdf(pdf([["2.1. Starts here"],
                                          ["continues here", "2.2. Next clause"]]), "pages.pdf")
        self.assertEqual([p["page"] for p in result["paragraphs"]], [1, 2, 2])
        self.assertEqual([p["section"] for p in result["paragraphs"]], ["2.1", "2.1", "2.2"])
        self.assertEqual(result["paragraphs"][1]["text"], "continues here")

    def test_reject_invalid_truncated_and_broken_xref(self):
        raw = pdf([["Readable text"]])
        broken = re.sub(rb"startxref\s+\d+", b"startxref\n1", raw)
        for data in (None, "not bytes", b"", b"not a PDF", raw[:-30], broken):
            with self.subTest(data=str(data)[:30]), self.assertRaises(ValueError):
                pdf_input.parse_pdf(data, "invalid.pdf")

    def test_reject_encrypted_even_with_empty_user_password(self):
        for password in ("secret", ""):
            with self.subTest(password=password), self.assertRaisesRegex(ValueError, "Encrypted"):
                pdf_input.parse_pdf(pdf([["Hidden text"]], password=password), "encrypted.pdf")

    def test_reject_empty_and_actual_image_only_pdf(self):
        for raw in (pdf([]), pdf([[]]), pdf([[]], image_only=True)):
            with self.subTest(size=len(raw)), self.assertRaisesRegex(ValueError, "no extractable text"):
                pdf_input.parse_pdf(raw, "empty.pdf")

    def test_blank_page_warns_and_preserves_page_numbers(self):
        result = pdf_input.parse_pdf(pdf([["2.1. First"], [], ["Last page"]]), "mixed.pdf")
        self.assertEqual([p["page"] for p in result["paragraphs"]], [1, 3])
        self.assertEqual(result["paragraphs"][-1]["section"], "")
        self.assertEqual(result["unread_pages"], [2])
        self.assertEqual(result["layout_warning_pages"], [])
        self.assertTrue(any("Page 2: no extractable text" in w for w in result["warnings"]))

    def test_mixed_pdf_reports_unread_image_page_without_truncating_text(self):
        writer = PdfWriter()
        sources = [pdf([["2.1. First page", "Exact  continuation."]]),
                   pdf([[]], image_only=True),
                   pdf([["2.2. Last page", "Final  evidence."]])]
        for raw in sources:
            writer.add_page(PdfReader(io.BytesIO(raw)).pages[0])
        stream = io.BytesIO()
        writer.write(stream)
        result = pdf_input.parse_pdf(stream.getvalue(), "mixed.pdf")
        self.assertEqual(result["page_count"], 3)
        self.assertEqual(result["unread_pages"], [2])
        self.assertEqual(result["layout_warning_pages"], [])
        self.assertEqual([p["page"] for p in result["paragraphs"]], [1, 3])
        self.assertEqual([p["text"] for p in result["paragraphs"]],
                         ["2.1. First page\nExact  continuation.",
                          "2.2. Last page\nFinal  evidence."])
        self.assertTrue(any("Page 2: no extractable text" in w for w in result["warnings"]))

    def test_actual_page_limit_boundary(self):
        raw = pdf([["First page"]] + [[]] * 199)
        self.assertEqual(pdf_input.parse_pdf(raw, "200.pdf")["page_count"], 200)
        with self.assertRaisesRegex(ValueError, "200-page"):
            pdf_input.parse_pdf(pdf([["First page"]] + [[]] * 200), "201.pdf")

    def test_size_limit_boundary(self):
        raw = pdf([["Text"]])
        raw += b" " * (pdf_input.MAX_UPLOAD_BYTES - len(raw))
        self.assertEqual(pdf_input.parse_pdf(raw, "10mb.pdf")["page_count"], 1)
        with self.assertRaisesRegex(ValueError, "10 MB"):
            pdf_input.parse_pdf(raw + b" ", "large.pdf")

    def test_text_limit_is_cumulative_and_never_truncates(self):
        raw = pdf([["A" * 125_000], ["B" * 125_000]])
        self.assertEqual(sum(len(p["text"]) for p in
                             pdf_input.parse_pdf(raw, "exact.pdf")["paragraphs"]), 250_000)
        with self.assertRaisesRegex(ValueError, "250,000-character"):
            pdf_input.parse_pdf(pdf([["A" * 125_000], ["B" * 125_001]]), "too-long.pdf")

    def test_decoded_page_content_limit(self):
        with patch.object(pdf_input, "MAX_PAGE_CONTENT_BYTES", 1):
            with self.assertRaisesRegex(ValueError, "page content"):
                pdf_input.parse_pdf(pdf([["A small real stream"]]), "stream.pdf")

    def test_columns_keep_extraction_order_and_do_not_inherit_sections(self):
        raw = pdf([[(40, 740, "2.1. Left column heading"),
                    (330, 740, "Right column heading"),
                    (40, 720, "Left column continuation"),
                    (330, 720, "Right column continuation")], ["Later page text"]])
        result = pdf_input.parse_pdf(raw, "columns.pdf")
        self.assertEqual(result["unread_pages"], [])
        self.assertEqual(result["layout_warning_pages"], [1])
        self.assertTrue(any("Page 1: unsupported layout" in w for w in result["warnings"]))
        self.assertEqual([p["section"] for p in result["paragraphs"]], ["2.1", "", "", "", ""])
        self.assertEqual([p["text"] for p in result["paragraphs"]], [
            "2.1. Left column heading", " Right column heading", "Left column continuation",
            " Right column continuation", "Later page text"])


@unittest.skipUnless(DATASET.is_dir(), "Local PDF dataset is not present")
class DatasetPdfTests(unittest.TestCase):
    def test_all_40_actual_pdfs_preserve_text_pages_and_clauses(self):
        paths = sorted(DATASET.glob("C*/**/*.pdf"))
        self.assertEqual(len(paths), 40)
        for path in paths:
            with self.subTest(path=str(path.relative_to(DATASET))):
                raw = path.read_bytes()
                result = pdf_input.parse_pdf(raw, path.name)
                reader = PdfReader(io.BytesIO(raw), strict=True)
                self.assertEqual(result["page_count"], len(reader.pages))
                self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual([p["id"] for p in result["paragraphs"]],
                                 [f"p{i + 1}" for i in range(len(result["paragraphs"]))])
                self.assertFalse(any("unsupported layout" in w for w in result["warnings"]))
                for index, page in enumerate(reader.pages, 1):
                    source = page.extract_text()
                    paragraphs = [p for p in result["paragraphs"] if p["page"] == index]
                    self.assertEqual("\n".join(p["text"] for p in paragraphs), source.rstrip("\r\n"))
                    for paragraph in paragraphs:
                        self.assertIn(paragraph["text"], source)
                        self.assertIsNone(paragraph["printed_page"])
                        if paragraph["section"]:
                            self.assertTrue(paragraph["text"].startswith(paragraph["section"]))

    def test_c010_wrapped_clauses_are_single_evidence_paragraphs(self):
        for path in sorted((DATASET / "C010").glob("**/*.pdf")):
            with self.subTest(path=str(path)):
                raw = path.read_bytes()
                source = PdfReader(io.BytesIO(raw)).pages[0].extract_text()
                expected = re.findall(r"(?m)^\d+(?:\.\d+)+\.? .*(?:\n(?!\d+(?:\.\d+)+\.? ).+)*", source)
                result = pdf_input.parse_pdf(raw, path.name)
                clauses = [p["text"] for p in result["paragraphs"] if p["section"]]
                self.assertEqual(clauses, expected)
                self.assertGreater(len(clauses), 0)


@unittest.skipUnless((REAL / "report_2022.pdf").is_file(), "Local real report is not present")
class RealLayoutTests(unittest.TestCase):
    def test_report_size_rejected_and_actual_page_121_warns(self):
        raw = (REAL / "report_2022.pdf").read_bytes()
        with self.assertRaisesRegex(ValueError, "10 MB"):
            pdf_input.parse_pdf(raw, "report_2022.pdf")
        reader = PdfReader(io.BytesIO(raw), strict=True)
        writer = PdfWriter()
        # Keep physical page 121 for the source page; no sidecar or gold data.
        for _ in range(120):
            writer.add_blank_page(width=600, height=800)
        writer.add_page(reader.pages[120])
        stream = io.BytesIO()
        writer.write(stream)
        result = pdf_input.parse_pdf(stream.getvalue(), "real-page-121.pdf")
        self.assertEqual(result["unread_pages"], list(range(1, 121)))
        self.assertEqual(result["layout_warning_pages"], [121])
        self.assertTrue(any("Page 121: unsupported layout" in w for w in result["warnings"]))
        self.assertTrue(all(p["page"] == 121 for p in result["paragraphs"]))
        self.assertTrue(all(p["printed_page"] is None for p in result["paragraphs"]))
        self.assertTrue(all("\n" not in p["text"] for p in result["paragraphs"]))
        source = reader.pages[120].extract_text()
        self.assertEqual("".join(p["text"] for p in result["paragraphs"]),
                         source.replace("\n", ""))
        cursor = 0
        for paragraph in result["paragraphs"]:
            start = source.find(paragraph["text"], cursor)
            self.assertGreaterEqual(start, cursor)
            cursor = start + len(paragraph["text"])


if __name__ == "__main__":
    unittest.main()
