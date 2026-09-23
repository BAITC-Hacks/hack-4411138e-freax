"""Focused RapidOCR contracts; fake inference does not prove OCR quality."""
import importlib.util
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ayqyn.documents import ocr, ocr_worker
from test_pdf_input import pdf


@unittest.skipUnless(importlib.util.find_spec('pypdfium2'), 'Install requirements-ocr.txt for PDF image inspection tests.')
class LocalOcrTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pdf = self.root / "scan.pdf"
        self.pdf.write_bytes(pdf([[]], image_only=True))

    def test_capability_has_no_subprocess_and_reports_missing_models(self):
        with patch.object(ocr.importlib.util, "find_spec", return_value=object()), \
                patch.object(ocr, "model_files", side_effect=ValueError("missing")), \
                patch.object(ocr.subprocess, "run") as process:
            value = ocr.capability()
        self.assertEqual(value["engine"], "rapidocr")
        self.assertFalse(value["available"])
        self.assertFalse(value["models_ready"])
        process.assert_not_called()

    def test_no_images_skips_before_models_or_inference(self):
        self.pdf.write_bytes(pdf([["1. Native text remains native."]]))
        with patch.object(ocr_worker, "capability", side_effect=AssertionError("Do not load models.")), \
                patch.object(ocr_worker, "_recognize_image", side_effect=AssertionError("No OCR.")):
            value = ocr_worker.process_page(self.pdf, 1)
        self.assertEqual(value["status"], "skipped")
        self.assertEqual(value["reason"], "no_images")
        self.assertFalse(value["page_info"]["has_images"])
        self.assertGreater(value["page_info"]["native_text_chars"], 0)

    def test_image_and_mixed_pages_invoke_recognition(self):
        output = SimpleNamespace(txts=["Recognized text"], scores=[0.7],
                                 boxes=[[[0, 0], [200, 0], [200, 40], [0, 40]]])
        for lines in [[], ["A native header"]]:
            with self.subTest(mixed=bool(lines)):
                self.pdf.write_bytes(pdf([lines], image_only=True))
                with patch.object(ocr_worker, "capability", return_value={"available": True}), \
                        patch.object(ocr_worker, "_recognize_image", return_value=output) as engine:
                    value = ocr_worker.process_page(self.pdf, 1)
                self.assertEqual(value["status"], "success")
                self.assertTrue(value["page_info"]["has_images"])
                self.assertFalse(value["verified"])
                self.assertFalse(value["canonical"])
                self.assertEqual(value["recognition_status"], "completed")
                self.assertEqual(value["lines"][0]["confidence"], 0.7)
                self.assertTrue(value["lines"][0]["low_confidence"])
                engine.assert_called_once()

    def test_missing_models_is_not_faked_as_success(self):
        with patch.object(ocr_worker, "capability", return_value={"available": False, "reason": "missing_models"}), \
                patch.object(ocr_worker, "_recognize_image") as engine:
            value = ocr_worker.process_page(self.pdf, 1)
        self.assertEqual(value["status"], "unavailable")
        self.assertTrue(value["page_info"]["has_images"])
        engine.assert_not_called()

    def test_wrapper_timeout_and_invalid_arguments(self):
        for page in [0, 201, True, "1"]:
            self.assertEqual(ocr.recognize_page(self.pdf, page)["reason"], "invalid_page")
        for timeout in [0, -1, 61, True, float("nan")]:
            self.assertEqual(ocr.recognize_page(self.pdf, 1, timeout_seconds=timeout)["reason"], "invalid_timeout")
        with patch.object(ocr.subprocess, "run", side_effect=subprocess.TimeoutExpired("worker", 2)):
            self.assertEqual(ocr.recognize_page(self.pdf, 1, timeout_seconds=2)["reason"], "timeout")

    def test_wrapper_uses_bounded_process_and_removes_temporary_result(self):
        scratch = []
        def process(command, **kwargs):
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["timeout"], 4)
            self.assertIn("ayqyn.documents.ocr_worker", command)
            target = Path(command[-1])
            scratch.append(target.parent)
            target.write_text(json.dumps(ocr.result("success", 1, text="recognized")), encoding="utf-8")
        with patch.object(ocr.subprocess, "run", side_effect=process):
            value = ocr.recognize_page(self.pdf, 1, timeout_seconds=4)
        self.assertEqual(value["text"], "recognized")
        self.assertFalse(scratch[0].exists())

    def test_output_text_line_limits_and_score_validation(self):
        box = [[0, 0], [100, 0], [100, 30], [0, 30]]
        value = ocr_worker._format_output(SimpleNamespace(txts=["x"*13000], scores=[0.98], boxes=[box]))
        self.assertEqual(len(value["text"]), 12000)
        self.assertTrue(value["truncated"])
        value = ocr_worker._format_output(SimpleNamespace(txts=["x"]*250, scores=[0.98]*250, boxes=[box]*250))
        self.assertEqual(len(value["lines"]), 200)
        self.assertTrue(value["truncated"])
        for score in [float("nan"), -0.1, 1.1]:
            with self.assertRaises(ValueError):
                ocr_worker._format_output(SimpleNamespace(txts=["x"], scores=[score], boxes=[box]))

    def test_empty_ocr_is_explicit_and_has_no_invented_text(self):
        value = ocr_worker._format_output(SimpleNamespace(txts=None, scores=None, boxes=None))
        self.assertEqual(value["text"], "")
        self.assertEqual(value["lines"], [])

    def test_out_of_document_page_is_rejected_before_recognition(self):
        with patch.object(ocr_worker, "_recognize_image") as engine:
            value = ocr_worker.process_page(self.pdf, 2)
        self.assertEqual(value["reason"], "invalid_page")
        engine.assert_not_called()


if __name__ == "__main__":
    unittest.main()
