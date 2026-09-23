"""Optional local RapidOCR; extracted text is not a human-verified quotation."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from ayqyn.paths import ROOT

MAX_PAGE = 200
MAX_PDF_BYTES = 10_000_000
MAX_RENDER_PIXELS = 2200
MAX_TEXT_CHARS = 12_000
MAX_LINES = 200
MAX_TIMEOUT_SECONDS = 60
MODEL_BASE = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/"
MODELS = {
    "Det": ("PP-OCRv5/det/ch_PP-OCRv5_det_mobile.onnx", "4d97c44a20d30a81aad087d6a396b08f786c4635742afc391f6621f5c6ae78ae"),
    "Cls": ("PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx", "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c"),
    "Rec": ("PP-OCRv5/rec/cyrillic_PP-OCRv5_rec_mobile.onnx", "90f761b4bfcce0c8c561c0cb5c887b0971d3ec01c32164bdf7374a35b0982711"),
}


def model_directory():
    return Path(os.environ.get("AYQYN_OCR_MODEL_DIR") or ROOT / "output" / "ocr-models").resolve()


def model_files():
    """Only explicitly prepared, hash-verified local models may reach inference."""
    paths = {}
    for kind, (relative, expected) in MODELS.items():
        path = model_directory() / Path(relative).name
        if (not path.is_file() or path.stat().st_size > 64_000_000
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError("missing_or_invalid_models")
        paths[kind] = path
    return paths


def capability():
    packages = {name: importlib.util.find_spec(name) is not None
                for name in ("rapidocr", "onnxruntime", "pypdfium2")}
    try:
        model_files()
        models_ready = True
    except (OSError, ValueError):
        models_ready = False
    available = all(packages.values()) and models_ready
    return {"status": "success" if available else "unavailable", "available": available,
            "engine": "rapidocr", "language": "cyrillic", "packages": packages,
            "models_ready": models_ready, "verified": False,
            "reason": "" if available else "missing_packages" if not all(packages.values()) else "missing_or_invalid_models"}


def result(status, page, *, reason="", **extra):
    return {"status": status, "page": page, "reason": reason, "text": "", "lines": [],
            "truncated": False, "source": "local_ocr", "engine": "rapidocr",
            "language": "cyrillic", "verified": False, "canonical": False,
            "review_status": "unreviewed", **extra}


def recognize_page(path, page, *, timeout_seconds=20):
    """Inspect and recognize one image-bearing PDF page in a killable process."""
    if type(page) is not int or not 1 <= page <= MAX_PAGE:
        return result("error", None, reason="invalid_page")
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS):
        return result("error", page, reason="invalid_timeout")
    try:
        original = Path(path).resolve(strict=True)
        if not original.is_file() or original.suffix.lower() != ".pdf" or original.stat().st_size > MAX_PDF_BYTES:
            return result("error", page, reason="invalid_pdf")
        with original.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                return result("error", page, reason="invalid_pdf")
        if importlib.util.find_spec("pypdfium2") is None:
            return result("unavailable", page, reason="missing_pdf_renderer")
        with TemporaryDirectory(prefix="ayqyn-ocr-") as directory:
            output = Path(directory) / "result.json"
            subprocess.run([sys.executable, "-m", "ayqyn.documents.ocr_worker", str(original), str(page), str(output)],
                           cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           shell=False, check=True, timeout=timeout_seconds,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            with output.open("r", encoding="utf-8") as stream:
                payload = stream.read(131_073)
            if len(payload) > 131_072:
                return result("error", page, reason="response_limit")
            return json.loads(payload)
    except subprocess.TimeoutExpired:
        return result("error", page, reason="timeout")
    except (OSError, ValueError, TypeError, subprocess.CalledProcessError):
        return result("error", page, reason="recognition_failed")
