"""Isolated local OCR worker: image inspection precedes all model loading."""
import json
import math
from pathlib import Path
import sys

from ayqyn.documents.ocr import MAX_LINES, MAX_PAGE, MAX_RENDER_PIXELS, MAX_TEXT_CHARS, capability, model_files, result


def _page_info(page):
    import pypdfium2.raw as pdfium_c
    image_count = 0
    # Traverse forms as well as direct images, with a bounded object walk.
    for number, obj in enumerate(page.get_objects(max_depth=15), 1):
        if number > 10_000:
            raise ValueError("page_object_limit")
        if obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
            image_count += 1
    textpage = page.get_textpage()
    try:
        text_chars = textpage.count_chars()
    finally:
        textpage.close()
    return {"has_images": image_count > 0, "image_count": image_count, "native_text_chars": text_chars}


def _recognize_image(image):
    import numpy as np
    from rapidocr import RapidOCR, LangRec, ModelType, OCRVersion

    paths = model_files()
    params = {kind + ".model_path": str(path) for kind, path in paths.items()}
    params.update({"Det.ocr_version": OCRVersion.PPOCRV5, "Det.model_type": ModelType.MOBILE,
                   "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE,
                   "Rec.lang_type": LangRec.CYRILLIC, "Global.log_level": "error",
                   "Global.max_side_len": MAX_RENDER_PIXELS, "Global.text_score": 0.0,
                   "EngineConfig.onnxruntime.intra_op_num_threads": 2,
                   "EngineConfig.onnxruntime.inter_op_num_threads": 1})
    engine = RapidOCR(params=params)
    return engine(np.asarray(image.convert("RGB"))[:, :, ::-1].copy())


def _format_output(output):
    texts = [] if output.txts is None else output.txts
    scores = [] if output.scores is None else output.scores
    boxes = [] if output.boxes is None else output.boxes
    if not (len(texts) == len(scores) == len(boxes)):
        raise ValueError("inconsistent_ocr_output")
    lines, used, truncated = [], 0, False
    for text, score, box in zip(texts, scores, boxes):
        remaining = MAX_TEXT_CHARS - used - (1 if lines else 0)
        if len(lines) >= MAX_LINES or remaining <= 0:
            truncated = True
            break
        score = float(score)
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("invalid_ocr_score")
        points = [[round(float(x), 2), round(float(y), 2)] for x, y in box]
        if len(points) != 4 or any(not math.isfinite(v) for p in points for v in p):
            raise ValueError("invalid_ocr_box")
        value = str(text)[:remaining]
        truncated = truncated or len(value) < len(str(text))
        lines.append({"text": value, "confidence": round(score, 4), "box": points,
                      "low_confidence": score < 0.8})
        used += len(value) + (1 if len(lines) > 1 else 0)
    return {"text": "\n".join(line["text"] for line in lines), "lines": lines, "truncated": truncated,
            "confidence_notice": "Recognition score is not the probability that the source or conclusion is correct."}


def process_page(path, page_number):
    import pypdfium2 as pdfium
    if type(page_number) is not int or not 1 <= page_number <= MAX_PAGE:
        return result("error", None, reason="invalid_page")
    document = pdfium.PdfDocument(str(path))
    try:
        if page_number > len(document):
            return result("error", page_number, reason="invalid_page")
        page = document[page_number - 1]
        try:
            info = _page_info(page)
            if not info["has_images"]:
                return result("skipped", page_number, reason="no_images", page_info=info)
            ready = capability()
            if not ready["available"]:
                return result("unavailable", page_number, reason=ready["reason"], page_info=info)
            width, height = page.get_size()
            if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                return result("error", page_number, reason="invalid_page_size", page_info=info)
            scale = min(3, MAX_RENDER_PIXELS / max(width, height))
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil()
                output = _recognize_image(image)
                formatted = _format_output(output)
                render_size = [image.width, image.height]
            finally:
                bitmap.close()
            return result("success", page_number, page_info=info, **formatted,
                          coordinate_space="render_pixels_top_left", render_size=render_size,
                          page_size_points=[width, height], recognition_status="completed",
                          scope="Full rendered page containing images, including any native text.")
        finally:
            page.close()
    finally:
        document.close()


def main():
    original, page, output = sys.argv[1:]
    try:
        value = process_page(original, int(page))
    except Exception as exc:
        value = result("error", int(page), reason="recognition_failed", error_type=type(exc).__name__)
    Path(output).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    main()
