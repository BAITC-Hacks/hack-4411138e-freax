"""Pure source-text normalization shared by validation and storage."""

def normalized(value):
    return " ".join(value.split())
