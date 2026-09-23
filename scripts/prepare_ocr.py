"""Explicit one-time model preparation; never called by the research agent."""
import hashlib
import os
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ayqyn.documents.ocr import MODELS, MODEL_BASE, model_directory


def main():
    directory = model_directory()
    directory.mkdir(parents=True, exist_ok=True)
    for relative, digest in MODELS.values():
        target = directory / Path(relative).name
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
            print(target.name + ": cached and verified")
            continue
        temporary = target.with_suffix(".download")
        try:
            total = 0
            with urllib.request.urlopen(MODEL_BASE + relative, timeout=60) as response, temporary.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 64_000_000:
                        raise ValueError("OCR model exceeds download limit")
                    stream.write(chunk)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
                raise ValueError("OCR model checksum mismatch")
            os.replace(temporary, target)
            print(target.name + ": downloaded and verified")
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
