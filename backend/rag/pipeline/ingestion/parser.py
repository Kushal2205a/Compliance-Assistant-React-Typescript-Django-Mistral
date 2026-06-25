import re


NON_PRINTABLE_RE = re.compile(r"[^\S\n]+")


def normalize_whitespace(text: str) -> str:
    return NON_PRINTABLE_RE.sub(" ", text).strip()


def clean_document(text: str) -> str:
    text = normalize_whitespace(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
