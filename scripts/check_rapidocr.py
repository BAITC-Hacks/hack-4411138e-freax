"""Live LOCAL OCR smoke test using explicitly synthetic inputs only.

Run only after the RapidOCR runtime is ready, with a Python environment that
has Pillow, reportlab and the application's local OCR dependencies installed:
    python scripts/check_rapidocr.py [--font C:/Windows/Fonts/arial.ttf]

No paid API, package installation, Git operation or full test suite is used.
Artifacts are written to output/rapidocr-check. Passing checks cover these
synthetic fixtures only; they do not establish general OCR quality.
"""

import argparse
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "rapidocr-check"
SNIPPETS = (
    "\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c "
    "\u0438\u0441\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f "
    "\u0434\u043e\u0433\u043e\u0432\u043e\u0440\u043e\u0432",
    "\u042e\u0440\u0438\u0434\u0438\u0447\u0435\u0441\u043a\u0438\u0439 "
    "\u0434\u0435\u043f\u0430\u0440\u0442\u0430\u043c\u0435\u043d\u0442",
)
CASES = ("scanned", "native_only", "mixed")


def normalize(text):
    """Case and whitespace normalization only; no fuzzy matching."""
    return " ".join(text.casefold().split())


def save_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def build_fixtures(font_path):
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas

    OUTPUT.mkdir(parents=True, exist_ok=True)
    image_path = OUTPUT / "synthetic-page.png"
    width, height = 1600, 2000
    font = ImageFont.truetype(
        str(font_path), 58, layout_engine=ImageFont.Layout.BASIC
    )
    label_font = ImageFont.truetype(
        str(font_path), 30, layout_engine=ImageFont.Layout.BASIC
    )
    with Image.new("RGB", (width, height), "white") as image:
        draw = ImageDraw.Draw(image)
        draw.text(
            (100, 170), "SYNTHETIC LOCAL OCR FIXTURE",
            fill="black", font=label_font, anchor="lt",
        )
        for index, snippet in enumerate(SNIPPETS):
            position = (100, 350 + index * 150)
            left, top, right, bottom = draw.textbbox(
                position, snippet, font=font, anchor="lt"
            )
            if not (0 <= left < right <= width - 100 and 0 <= top < bottom <= height):
                raise ValueError("Selected font does not fit the synthetic page")
            draw.text(position, snippet, fill="black", font=font, anchor="lt")
        image.save(image_path, format="PNG")

    pdfmetrics.registerFont(TTFont("SyntheticOCRFont", str(font_path)))
    fixtures = {}
    for case in CASES:
        path = OUTPUT / (case + ".pdf")
        canvas = Canvas(str(path), pagesize=(600, 750), invariant=1, pageCompression=1)
        canvas.setTitle("Synthetic local OCR smoke test: " + case)
        canvas.setAuthor("AYQYN synthetic fixture generator")
        if case != "native_only":
            canvas.drawImage(str(image_path), 0, 0, width=600, height=750)
        if case != "scanned":
            canvas.setFont("SyntheticOCRFont", 12)
            canvas.drawString(38, 715, "SYNTHETIC NATIVE HEADER: " + case)
        if case == "native_only":
            canvas.setFont("SyntheticOCRFont", 20)
            for index, snippet in enumerate(SNIPPETS):
                canvas.drawString(38, 600 - index * 60, snippet)
        canvas.showPage()
        canvas.save()
        fixtures[case] = path
    return fixtures


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def valid_box(box):
    if not isinstance(box, list) or len(box) != 4:
        return False
    if all(finite_number(value) for value in box):
        return box[2] > box[0] and box[3] > box[1]
    if not all(
        isinstance(point, list) and len(point) == 2
        and all(finite_number(value) for value in point)
        for point in box
    ):
        return False
    return (
        max(point[0] for point in box) > min(point[0] for point in box)
        and max(point[1] for point in box) > min(point[1] for point in box)
    )


def has_no_true_evidence_flags(value):
    if isinstance(value, dict):
        return all(
            not (key in ("verified", "canonical") and item is True)
            and has_no_true_evidence_flags(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return all(has_no_true_evidence_flags(item) for item in value)
    return True


def inspect_result(case, result):
    data = result if isinstance(result, dict) else {}
    text = data.get("text")
    contains = {
        snippet: isinstance(text, str) and normalize(snippet) in normalize(text)
        for snippet in SNIPPETS
    }
    page_info = data.get("page_info")
    expects_images = case != "native_only"
    checks = {
        "result_is_object": isinstance(result, dict),
        "text_is_string": isinstance(text, str),
        "expected_status": data.get("status") == ("success" if expects_images else "skipped"),
        "expected_has_images": isinstance(page_info, dict)
        and page_info.get("has_images") is expects_images,
        "verified_false": data.get("verified") is False,
        "canonical_false": data.get("canonical") is False,
        "no_true_evidence_flags_anywhere": has_no_true_evidence_flags(result),
    }
    if expects_images:
        lines = data.get("lines")
        nonempty_lines = isinstance(lines, list) and bool(lines)
        checks.update({
            "engine_rapidocr": data.get("engine") == "rapidocr",
            "all_exact_contains": all(contains.values()),
            "nonempty_lines": nonempty_lines,
            "lines_have_text_boxes_scores": nonempty_lines and all(
                isinstance(line, dict)
                and isinstance(line.get("text"), str) and bool(line["text"].strip())
                and valid_box(line.get("box", line.get("bbox")))
                and finite_number(line.get("confidence")) and 0 <= line["confidence"] <= 1
                for line in lines
            ),
        })
    else:
        checks["reason_no_images"] = data.get("reason") == "no_images"
    return checks, contains


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font", type=Path, default=Path("C:/Windows/Fonts/arial.ttf"),
        help="Local TrueType font with Cyrillic glyphs (default: Windows Arial)",
    )
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error("Font not found; supply --font with a local Cyrillic TrueType font")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ROOT))
    from ayqyn.documents.ocr import recognize_page

    fixtures = build_fixtures(args.font.resolve())
    report = {
        "synthetic_inputs": True,
        "scope": "Local OCR smoke test only; not a general OCR quality assessment.",
        "font": str(args.font.resolve()),
        "normalization": "casefold, collapse whitespace, exact substring containment",
        "timeout_seconds_per_case": 20,
        "cases": [],
    }
    for case, pdf_path in fixtures.items():
        result = None
        error = None
        started = time.perf_counter()
        try:
            result = recognize_page(pdf_path, 1, timeout_seconds=20)
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
        elapsed = time.perf_counter() - started
        result_path = OUTPUT / (case + ".result.json")
        save_json(result_path, result)
        checks, contains = inspect_result(case, result)
        checks["call_returned"] = error is None
        passed = all(checks.values())
        entry = {
            "case": case, "synthetic_input": True, "pdf": str(pdf_path),
            "result_json": str(result_path), "elapsed_seconds": round(elapsed, 6),
            "error": error, "checks": checks, "exact_contains": contains,
            "passed": passed,
        }
        report["cases"].append(entry)
        save_json(OUTPUT / "report.json", report)
        print("{}: {} ({:.3f}s)".format(case, "PASS" if passed else "FAIL", elapsed))
        for snippet, found in contains.items():
            print("  exact_contains {!r}: {}".format(snippet, found))
        for name, ok in checks.items():
            if not ok:
                print("  FAILED: " + name)
        if error:
            print("  {}: {}".format(error["type"], error["message"]))
    report["passed"] = all(entry["passed"] for entry in report["cases"])
    report["total_ocr_seconds"] = round(sum(
        entry["elapsed_seconds"] for entry in report["cases"]
    ), 6)
    save_json(OUTPUT / "report.json", report)
    print(report["scope"])
    print("Report: " + str(OUTPUT / "report.json"))
    if not report["passed"]:
        raise AssertionError("Synthetic RapidOCR smoke checks failed; see report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
