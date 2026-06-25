import pdfplumber

from . import Document


def load_pdf(file) -> Document:
    with pdfplumber.open(file) as pdf:
        text_parts: list[str] = []
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    content = "\n".join(text_parts)
    filename = getattr(file, "name", "unknown")
    return Document(
        id=filename,
        content=content,
        metadata={"source": filename, "pages": len(pdf.pages)},
        source=filename,
    )
