"""Untrusted PDF/OCR input produces review material, never approved sales."""
import hashlib
import io
from pathlib import Path
from typing import Protocol
from pypdf import PdfReader


class OCRProvider(Protocol):
    def recognize(self, pdf: bytes, page_number: int) -> str:
        """Return page text for human review. Page numbers are one-based."""
        ...


class SidecarOCR:
    """Manual transcription or output from a future Ollama adapter."""
    def __init__(self, pages: dict[str, str]):
        self.pages = pages

    def recognize(self, pdf, page_number):
        return self.pages.get(str(page_number), '')


def intake(path, ocr: OCRProvider | None = None):
    path = Path(path)
    if path.stat().st_size > 25_000_000:
        raise ValueError('PDF limit: 25 MB')
    raw = path.read_bytes()
    if not raw.startswith(b'%PDF-'):
        raise ValueError('Not a PDF')
    reader = PdfReader(io.BytesIO(raw))
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are unsupported')
    if not 1 <= len(reader.pages) <= 100:
        raise ValueError('PDF limit: 100 pages')
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or '').strip()
        method = 'pdf_text'
        if not text:
            text = ocr.recognize(raw, i) if ocr else ''
            method = 'ocr_unverified' if text else 'needs_ocr'
        pages.append({'page': i, 'text': text, 'method': method, 'review_required': True})
    return {'source_name': path.name, 'source_hash': hashlib.sha256(raw).hexdigest(),
            'pages': pages, 'status': 'needs_review', 'sales_records': []}
