"""Cross-platform local bootstrap. Reads .env as data; never executes its text."""
import importlib.metadata
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def read_env(path):
    if not path.is_file():
        raise ValueError("Missing .env. Copy .env.example to .env and fill in your model settings first.")
    values = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
        if not match:
            raise ValueError(f"Invalid .env assignment on line {number}; expected KEY=value.")
        key, raw = match.groups()
        if raw.startswith(("'", '"')):
            quote, characters, position = raw[0], [], 1
            while position < len(raw) and raw[position] != quote:
                char = raw[position]
                if char == "\\" and position + 1 < len(raw) and raw[position + 1] in (quote, "\\"):
                    position += 1
                    char = raw[position]
                characters.append(char)
                position += 1
            if position == len(raw) or (raw[position + 1:].strip() and not raw[position + 1:].lstrip().startswith("#")):
                raise ValueError(f"Invalid quotes in .env on line {number}.")
            value = "".join(characters)
        else:
            value = "" if raw.startswith("#") else re.split(r"\s+#", raw, maxsplit=1)[0].rstrip()
        if "\x00" in value:
            raise ValueError(f"Invalid character in .env on line {number}.")
        values[key] = value
    return values


def requirements_ready():
    """The repository currently uses exact pins; other syntax goes through pip."""
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if not match:
            return False
        try:
            if importlib.metadata.version(match[1]) != match[2]:
                return False
        except importlib.metadata.PackageNotFoundError:
            return False
    return True


def main():
    if sys.version_info < (3, 10):
        raise ValueError("Python 3.10 or newer is required: https://www.python.org/downloads/")
    settings = read_env(ROOT / ".env")
    venv = ROOT / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        if venv.exists():
            raise ValueError("Existing .venv is incomplete or belongs to another OS. Rename it and run again; it was left unchanged.")
        print("Creating local Python environment (.venv)...", flush=True)
        result = subprocess.run([sys.executable, "-m", "venv", str(venv)], cwd=ROOT)
        if result.returncode:
            raise ValueError("Cannot create .venv. On Debian/Ubuntu install python3-venv; on Windows use Python from python.org. Rename an incomplete .venv before retrying.")
    if Path(sys.prefix).resolve() != venv.resolve():
        return subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT)
    if not requirements_ready():
        print("Installing required project packages into .venv...", flush=True)
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / "requirements.txt")], cwd=ROOT)
        if result.returncode:
            raise ValueError("Dependency installation failed. Check network access and retry; model settings were not sent to pip.")
    environment = os.environ.copy()
    environment.update(settings)
    print("Starting AYQYN (local access only). Stop with Ctrl+C.", flush=True)
    return subprocess.call([sys.executable, str(ROOT / "server.py"), *sys.argv[1:]], cwd=ROOT, env=environment)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print("Launch error: " + str(exc), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
