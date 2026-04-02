"""Extract text from the first page of a PDF using PyMuPDF."""


def extract_first_page(file_path: str) -> str:
    """Return text content of the first page, or empty string on failure."""
    try:
        import pymupdf
        doc = pymupdf.open(file_path)
        if len(doc) > 0:
            text = doc[0].get_text()
            doc.close()
            return text
        doc.close()
    except Exception:
        pass
    return ""
